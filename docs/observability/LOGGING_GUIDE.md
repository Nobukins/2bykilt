# Logging Guide

最終更新: 2025-08-26

## 概要

2bykilt プロジェクトの統一ログ標準とベストプラクティスを定義します。構造化ログと効果的な運用監視を実現します。

## ログ設計原則

### 1. 構造化ログ
- JSON 形式での出力
- 一貫したフィールド構造
- 機械読み取り可能な形式

### 2. ディレクトリ構造標準化
- **ルートログディレクトリ**: `./logs/` (リポジトリルート基準)
- **廃止ディレクトリ**: `src/logs/` (互換性維持期間終了後は削除)
- **カテゴリ別ログファイル**:
  - `logs/app.log`: 全般アプリケーションイベント
  - `logs/error.log`: ERROR/CRITICAL レベルのみ
  - `logs/audit.log`: セキュリティ/監査関連イベント
  - `logs/runner.log`: 実行関連イベント
  - `logs/artifacts.log`: アーティファクト関連イベント

### 3. ログカテゴリ定義
```python
LOG_CATEGORIES = {
    'runner': '実行制御・スクリプト実行関連',
    'artifacts': '録画・スクリーンショット・ファイル生成関連', 
    'browser': 'ブラウザ操作・Playwright関連',
    'config': '設定読み込み・Flag関連',
    'metrics': 'パフォーマンス計測・統計情報',
    'security': '認証・認可・機密情報処理',
    'batch': 'CSV処理・バッチ実行関連',
    'api': '外部API連携関連',
    'system': 'インフラ・環境関連'
}
```

### 4. コンテキスト情報
- Request ID による追跡
- User ID やセッション情報
- 実行環境とバージョン情報

### 5. セキュリティ配慮
- 機密情報のマスキング
- PII データの除外
- 適切なログレベル設定

## ログレベル定義

### 1. レベル別用途
```python
import logging

# CRITICAL: システム停止レベルの致命的エラー
logger.critical("Database connection completely failed", extra={
    "error_code": "DB_FATAL",
    "component": "database",
    "action": "shutdown_required"
})

# ERROR: 機能に支障をきたすエラー
logger.error("Failed to process user request", extra={
    "user_id": "user123",
    "request_id": "req456",
    "error": str(exception),
    "component": "request_processor"
})

# WARNING: 注意が必要だが継続可能な状況
logger.warning("API rate limit approaching", extra={
    "api_provider": "openai",
    "current_usage": 80,
    "limit": 100,
    "reset_time": "2025-08-26T12:00:00Z"
})

# INFO: 重要な業務イベント
logger.info("User authentication successful", extra={
    "user_id": "user123",
    "login_method": "oauth",
    "ip_address": "192.168.1.100",
    "session_id": "sess789"
})

# DEBUG: 開発・診断用の詳細情報
logger.debug("Processing batch item", extra={
    "batch_id": "batch123",
    "item_index": 5,
    "total_items": 10,
    "processing_time": 0.234
})
```

### 2. 環境別設定 & LOG_LEVEL 環境変数
```yaml
# development環境
logging:
  level: DEBUG
  console: true
  file: false

# staging環境  
logging:
  level: INFO
  console: true
  file: true
  
# production環境
logging:
  level: WARNING
  console: false
  file: true
  structured: true
```

#### LOG_LEVEL 環境変数設定
```bash
# 環境変数でのログレベル制御
export LOG_LEVEL=DEBUG    # DEBUG, INFO, WARNING, ERROR, CRITICAL
export LOG_BASE_DIR=./logs  # ログ出力ディレクトリ（デフォルト: ./logs）

# 実行例
LOG_LEVEL=ERROR python bykilt.py  # ERROR以上のログのみ出力
LOG_LEVEL=DEBUG python bykilt.py  # 全てのログレベルを出力
```

#### 初期化順序の重要性
- 環境変数 `LOG_LEVEL` はロガー初期化時に一度だけ読み込まれます
- 初期化後の動的変更は `logging.getLogger().setLevel()` を使用してください
- 推奨: アプリケーション起動直後に `init_logging()` 関数を呼び出す

## ログ構造標準

### 1. 共通フィールド
```json
{
  "timestamp": "2025-08-26T12:34:56.789Z",
  "level": "INFO",
  "message": "Human readable message",
  "logger": "src.module.component",
  "request_id": "req-12345678",
  "session_id": "sess-87654321",
  "user_id": "user-98765432",
  "environment": "production",
  "version": "1.2.3",
  "component": "authentication",
  "action": "login_attempt",
  "duration_ms": 234,
  "success": true
}
```

### 2. カテゴリ別拡張フィールド

#### 認証・認可
```json
{
  "category": "authentication",
  "user_id": "user123",
  "login_method": "oauth2",
  "provider": "google",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "success": true,
  "failure_reason": null
}
```

#### API リクエスト
```json
{
  "category": "api_request",
  "method": "POST",
  "endpoint": "/api/v1/process",
  "status_code": 200,
  "response_time_ms": 150,
  "request_size": 1024,
  "response_size": 512,
  "api_version": "v1"
}
```

#### バッチ処理
```json
{
  "category": "batch_processing",
  "batch_id": "batch_20250127_001",
  "total_items": 100,
  "processed_items": 75,
  "failed_items": 2,
  "progress_percent": 75.0,
  "estimated_completion": "2025-08-26T13:45:00Z"
}
```

#### エラー情報
```json
{
  "category": "error",
  "error_code": "VALIDATION_FAILED",
  "error_type": "ValidationError",
  "error_message": "Invalid input format",
  "stack_trace": "Traceback (most recent call last)...",
  "context": {
    "input_file": "data.csv",
    "line_number": 15,
    "validation_rule": "email_format"
  }
}
```

## ログ実装パターン

### 1. 基本ロガー設定
```python
import logging
import json
import datetime
from typing import Dict, Any, Optional

class StructuredLogger:
    """構造化ログ出力"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}
        
    def add_context(self, **kwargs):
        """コンテキスト情報追加"""
        self.context.update(kwargs)
        
    def info(self, message: str, **extra):
        """INFO レベルログ"""
        self._log("INFO", message, extra)
        
    def error(self, message: str, **extra):
        """ERROR レベルログ"""
        self._log("ERROR", message, extra)
        
    def warning(self, message: str, **extra):
        """WARNING レベルログ"""
        self._log("WARNING", message, extra)
        
    def debug(self, message: str, **extra):
        """DEBUG レベルログ"""
        self._log("DEBUG", message, extra)
        
    def _log(self, level: str, message: str, extra: Dict[str, Any]):
        """ログ出力実装"""
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            "logger": self.logger.name,
            **self.context,
            **extra
        }
        
        # 機密情報マスキング
        log_entry = self._mask_sensitive_data(log_entry)
        
        # 出力
        getattr(self.logger, level.lower())(json.dumps(log_entry, ensure_ascii=False))
```

### 2. コンテキストマネージャー
```python
from contextlib import contextmanager
import uuid

@contextmanager
def log_context(**context):
    """ログコンテキスト管理"""
    # 既存コンテキストを保存
    old_context = getattr(logging, '_context', {})
    
    # 新しいコンテキストを設定
    new_context = {**old_context, **context}
    logging._context = new_context
    
    try:
        yield
    finally:
        # コンテキストを復元
        logging._context = old_context

# 使用例
with log_context(request_id=str(uuid.uuid4()), user_id="user123"):
    logger.info("Processing request")
    process_user_request()
    logger.info("Request completed")
```

### 3. パフォーマンス測定
```python
import time
from functools import wraps

def log_performance(component: str = None):
    """パフォーマンス測定デコレータ"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__name__}"
            
            logger.debug("Function started", extra={
                "function": func_name,
                "component": component or func.__module__,
                "action": "function_start"
            })
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info("Function completed", extra={
                    "function": func_name,
                    "component": component or func.__module__,
                    "action": "function_complete",
                    "duration_ms": round(duration * 1000, 2),
                    "success": True
                })
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error("Function failed", extra={
                    "function": func_name,
                    "component": component or func.__module__,
                    "action": "function_error",
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "success": False
                })
                
                raise
                
        return wrapper
    return decorator

# 使用例
@log_performance(component="batch_processor")
def process_batch_file(file_path: str):
    """バッチファイル処理"""
    pass
```

## セキュリティ配慮

### 1. 機密情報マスキング
```python
import re
from typing import Any

class SensitiveDataMasker:
    """機密データマスキング"""
    
    # マスキング対象パターン
    PATTERNS = {
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'\b\d{3}-\d{3,4}-\d{4}\b'),
        'credit_card': re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
        'api_key': re.compile(r'\b[Aa]pi[_-]?[Kk]ey["\']?\s*[:=]\s*["\']?([A-Za-z0-9]{20,})["\']?'),
    }
    
    SENSITIVE_KEYS = [
        'password', 'secret', 'token', 'key', 'credential',
        'auth', 'session', 'cookie', 'private'
    ]
    
    def mask_data(self, data: Any) -> Any:
        """データマスキング"""
        if isinstance(data, dict):
            return {k: self.mask_data(v) if not self._is_sensitive_key(k) 
                   else "***MASKED***" for k, v in data.items()}
        elif isinstance(data, list):
            return [self.mask_data(item) for item in data]
        elif isinstance(data, str):
            return self._mask_string_patterns(data)
        else:
            return data
    
    def _is_sensitive_key(self, key: str) -> bool:
        """機密キー判定"""
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS)
    
    def _mask_string_patterns(self, text: str) -> str:
        """文字列パターンマスキング"""
        for name, pattern in self.PATTERNS.items():
            text = pattern.sub(f"***{name.upper()}***", text)
        return text
```

### 2. PII データ除外
```python
class PIIFilter:
    """PII データフィルタ"""
    
    PII_FIELDS = [
        'ssn', 'social_security_number', 'passport_number',
        'drivers_license', 'birth_date', 'full_name',
        'home_address', 'personal_email', 'phone_number'
    ]
    
    def filter_pii(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """PII データ除外"""
        filtered_data = {}
        
        for key, value in log_data.items():
            if key.lower() in self.PII_FIELDS:
                filtered_data[key] = "***PII_REMOVED***"
            elif isinstance(value, dict):
                filtered_data[key] = self.filter_pii(value)
            else:
                filtered_data[key] = value
                
        return filtered_data
```

## ログ収集・分析

### 1. ログ集約設定
```python
import logging.handlers
import json

class JSONFormatter(logging.Formatter):
    """JSON フォーマッター"""
    
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # extra フィールド追加
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
            
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging(config: Dict[str, Any]):
    """ログ設定セットアップ"""
    
    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.get('level', 'INFO')))
    
    # コンソール出力
    if config.get('console', True):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(console_handler)
    
    # ファイル出力
    if config.get('file', False):
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.get('file_path', 'logs/app.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # 外部ログ収集システム（オプション）
    if config.get('external_logging', {}).get('enabled', False):
        setup_external_logging(config['external_logging'])
```

### 2. メトリクス連携
```python
class LogMetricsCollector:
    """ログメトリクス収集"""
    
    def __init__(self):
        self.counters = {}
        self.timers = {}
        
    def count_log_event(self, level: str, component: str, action: str):
        """ログイベントカウント"""
        key = f"log.{level.lower()}.{component}.{action}"
        self.counters[key] = self.counters.get(key, 0) + 1
        
    def time_operation(self, component: str, action: str, duration_ms: float):
        """操作時間記録"""
        key = f"operation.{component}.{action}"
        if key not in self.timers:
            self.timers[key] = []
        self.timers[key].append(duration_ms)
        
    def get_metrics(self) -> Dict[str, Any]:
        """メトリクス取得"""
        return {
            "counters": self.counters,
            "timers": {
                key: {
                    "count": len(times),
                    "avg": sum(times) / len(times) if times else 0,
                    "max": max(times) if times else 0,
                    "min": min(times) if times else 0
                }
                for key, times in self.timers.items()
            }
        }
```

## ログ運用

### 1. ログローテーション
```python
import logging.handlers
from pathlib import Path

def setup_log_rotation(log_dir: str, max_bytes: int = 10*1024*1024, backup_count: int = 5):
    """ログローテーション設定"""
    
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # アプリケーションログ
    app_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    
    # エラーログ（ERROR以上）
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    
    # 監査ログ（重要イベント）
    audit_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "audit.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    
    return app_handler, error_handler, audit_handler
```

### 2. ログ監視・アラート
```python
import time
from collections import defaultdict
from threading import Thread, Event

class LogMonitor:
    """ログ監視"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.warning_counts = defaultdict(int)
        self.stop_event = Event()
        
    def start_monitoring(self):
        """監視開始"""
        monitor_thread = Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
    def _monitor_loop(self):
        """監視ループ"""
        while not self.stop_event.is_set():
            time.sleep(60)  # 1分間隔
            self._check_error_rates()
            self._check_warning_patterns()
            
    def _check_error_rates(self):
        """エラー率チェック"""
        total_errors = sum(self.error_counts.values())
        if total_errors > 10:  # 閾値
            self._send_alert(f"High error rate detected: {total_errors} errors in last minute")
            
    def _check_warning_patterns(self):
        """警告パターンチェック"""
        # 特定パターンの警告が多発している場合
        for pattern, count in self.warning_counts.items():
            if count > 5:  # 閾値
                self._send_alert(f"Warning pattern '{pattern}' occurred {count} times")
                
    def _send_alert(self, message: str):
        """アラート送信"""
        logger.critical("Log monitor alert", extra={
            "alert_message": message,
            "component": "log_monitor",
            "action": "alert_triggered"
        })
```

## 開発ガイドライン

### 1. ログ出力ガイドライン
```python
# ✅ 良い例
logger.info("User login successful", extra={
    "user_id": user.id,
    "login_method": "oauth2",
    "ip_address": request.remote_addr,
    "session_id": session.id,
    "component": "authentication",
    "action": "login_success"
})

# ❌ 悪い例
logger.info(f"User {user.name} logged in from {request.remote_addr}")
```

### 2. エラーログガイドライン
```python
# ✅ 良い例
try:
    result = risky_operation()
except SpecificException as e:
    logger.error("Operation failed", extra={
        "error": str(e),
        "error_type": type(e).__name__,
        "component": "data_processor",
        "action": "process_data",
        "input_size": len(data),
        "traceback": traceback.format_exc()
    })
    raise ProcessingError("Data processing failed") from e

# ❌ 悪い例
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Error: {e}")
    raise
```

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-08-26 | 初期ドラフト作成 | Copilot Agent |

---

統一されたログ標準により、効果的な運用監視と問題解決を実現してください。