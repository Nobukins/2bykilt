"""
Memory monitoring utilities for browser automation
メモリ監視とブラウザ最適化のためのユーティリティ
"""

import psutil
import logging
import os
import json
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

class MemoryMonitor:
    """システムメモリ状況の監視とブラウザ最適化"""
    
    def __init__(self):
        self.min_available_mb = 500  # 最小必要メモリ (MB)
        self.memory_pressure_threshold = 80  # メモリ圧迫しきい値 (%)
        
    def get_memory_status(self) -> Dict[str, Any]:
        """現在のメモリ状況を取得"""
        try:
            memory = psutil.virtual_memory()
            return {
                'total_mb': round(memory.total / (1024 * 1024)),
                'available_mb': round(memory.available / (1024 * 1024)),
                'used_percent': memory.percent,
                'pressure_level': self._calculate_pressure_level(memory.percent),
                'is_low_memory': memory.available < (self.min_available_mb * 1024 * 1024)
            }
        except Exception as e:
            logger.warning(f"Failed to get memory status: {e}")
            return {
                'total_mb': 0,
                'available_mb': 0,
                'used_percent': 0,
                'pressure_level': 'unknown',
                'is_low_memory': False
            }
    
    def _calculate_pressure_level(self, used_percent: float) -> str:
        """メモリ圧迫レベルを計算"""
        if used_percent >= 95:
            return 'critical'
        elif used_percent >= self.memory_pressure_threshold:
            return 'high'
        elif used_percent >= 60:
            return 'medium'
        else:
            return 'low'
    
    def is_safe_for_browser(self, browser_type: str = 'chrome') -> Tuple[bool, str]:
        """ブラウザ起動に安全なメモリ状況かチェック"""
        status = self.get_memory_status()
        
        # Edgeは特にメモリを多く使用するため、より厳しい条件
        if browser_type.lower() in ['edge', 'msedge']:
            min_required = 1200  # Edge用最小必要メモリを増加 (V8 OOM対策)
            if status['available_mb'] < min_required:
                return False, f"Edge requires at least {min_required}MB free memory, but only {status['available_mb']}MB available (V8 OOM prevention)"
            if status['pressure_level'] in ['critical', 'high']:
                return False, f"Memory pressure too high ({status['used_percent']:.1f}%) for Edge (V8 OOM risk)"
            # Edge用の追加チェック: 使用率75%を超えると危険
            if status['used_percent'] > 75:
                return False, f"Memory usage ({status['used_percent']:.1f}%) too high for Edge stability"
        else:
            if status['available_mb'] < self.min_available_mb:
                return False, f"Insufficient memory: {status['available_mb']}MB available (minimum {self.min_available_mb}MB required)"
            if status['pressure_level'] == 'critical':
                return False, f"Critical memory pressure ({status['used_percent']:.1f}%)"
        
        return True, "Memory status OK"
    
    def get_optimized_browser_args(self, browser_type: str = 'chrome') -> list:
        """メモリ状況に応じた最適化されたブラウザ引数を取得（macOS対応）"""
        status = self.get_memory_status()
        base_args = [
            '--disable-setuid-sandbox',
            '--disable-accelerated-2d-canvas',
            '--no-zygote',
            '--single-process',
            '--window-position=50,50',
            '--window-size=1280,720'
        ]
        
        # メモリ圧迫レベルに応じた最適化
        if status['pressure_level'] in ['high', 'critical']:
            logger.info(f"🔧 Applying memory optimization for {status['pressure_level']} pressure")
            memory_optimized_args = [
                '--memory-pressure-off',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-breakpad',
                '--disable-component-extensions-with-background-pages',
                '--disable-default-apps',
                '--disable-hang-monitor',
                '--disable-ipc-flooding-protection',
                '--disable-popup-blocking',
                '--disable-prompt-on-repost',
                '--disable-renderer-backgrounding',
                '--max_old_space_size=1024',  # V8メモリ制限
            ]
            base_args.extend(memory_optimized_args)
            
        # Edge固有の最適化 (V8 OOM対策)
        if browser_type.lower() in ['edge', 'msedge']:
            edge_args = [
                '--memory-pressure-off',
                '--max_old_space_size=512',  # V8メモリ制限をより厳しく (Edge V8 OOM完全対策)
                '--js-flags=--max_old_space_size=512',  # V8フラグレベルでも制限
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # 画像無効化でメモリ節約
                # '--disable-javascript'は削除 - V8設定と競合するため
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor,AudioServiceSandbox,TranslateUI',
                '--force-fieldtrials=ReduceMemory/Enabled',  # メモリ削減フィールドトライアル
                '--enable-low-res-tiling',  # 低解像度タイリング
                '--disable-background-media-suspension=false',  # バックグラウンドメディア一時停止
                '--renderer-process-limit=1',  # レンダラープロセス制限
                '--disable-site-isolation-trials',  # サイト分離無効化
            ]
            # 重複を避けて追加
            for arg in edge_args:
                if arg not in base_args:
                    base_args.append(arg)
                    
            # Edge使用時はより積極的にメモリ最適化引数を追加
            if status['pressure_level'] in ['medium', 'high', 'critical']:
                additional_edge_args = [
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-gpu-sandbox',
                    '--disable-features=TranslateUI',
                    '--disable-background-networking',
                    '--js-flags=--max_old_space_size=256',  # 緊急時はさらに制限
                    '--js-flags=--max_semi_space_size=16',  # セミスペースも制限
                    '--single-process',  # 強制シングルプロセス
                ]
                for arg in additional_edge_args:
                    if arg not in base_args:
                        base_args.append(arg)
        
        # 問題のある引数を除外（ページ開きを指定する引数）
        filtered_args = []
        problematic_patterns = [
            '--app=',
            '--new-window',
            '--incognito',
            'http://',
            'https://',
            'file://',
            'data:',
            'chrome://',
            'edge://'
        ]
        
        for arg in base_args:
            is_problematic = False
            for pattern in problematic_patterns:
                if pattern in arg:
                    logger.warning(f"⚠️ Filtering out problematic browser argument: {arg}")
                    is_problematic = True
                    break
            if not is_problematic:
                filtered_args.append(arg)
        
        return filtered_args
    
    def suggest_fallback_browser(self, requested_browser: str) -> str:
        """メモリ状況に基づいて代替ブラウザを提案"""
        status = self.get_memory_status()
        
        # Edge用のより厳しいフォールバック戦略
        if requested_browser.lower() in ['edge', 'msedge']:
            if status['pressure_level'] in ['high', 'critical'] or status['used_percent'] > 75:
                logger.warning(f"⚠️ Edge not recommended with {status['pressure_level']} memory pressure ({status['used_percent']:.1f}% used)")
                if status['pressure_level'] == 'critical':
                    return 'headless'  # 危険レベルではheadlessモード
                else:
                    return 'chrome'  # 高い圧迫ではChromeにフォールバック
        
        if status['pressure_level'] == 'critical':
            logger.warning("⚠️ Critical memory pressure - recommending headless mode")
            return 'headless'
        
        return requested_browser
    
    def log_memory_status(self):
        """現在のメモリ状況をログに出力"""
        status = self.get_memory_status()
        logger.info(f"🧠 Memory Status: {status['available_mb']}MB available / {status['total_mb']}MB total ({status['used_percent']:.1f}% used)")
        logger.info(f"🎯 Pressure Level: {status['pressure_level']}")
        if status['is_low_memory']:
            logger.warning("⚠️ Low memory condition detected")


# グローバルインスタンス
memory_monitor = MemoryMonitor()
