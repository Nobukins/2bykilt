"""
ProfileManager - Chrome/Edge 2024+ Browser Profile Management
Implements the new profile handling method for stable automation
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    2024年5月以降のChrome/Edge新作法対応プロファイル管理クラス
    
    主な機能:
    - SeleniumProfile サブディレクトリの作成
    - 重要なプロファイルファイルの選択的コピー
    - プロファイル競合の回避
    - 安全なクリーンアップ機能
    """
    
    # 2024年5月以降の新作法で必要な重要ファイル
    ESSENTIAL_FILES = [
        "Default/Preferences",
        "Default/Secure Preferences", 
        "Default/Login Data",
        "Default/Web Data",
        "Default/Cookies",
        "Default/Bookmarks",
        "Default/History",
        "Local State"
    ]
    
    # コピーを避けるべきディレクトリ・ファイル（パフォーマンス・安定性のため）
    SKIP_PATTERNS = [
        "Cache",
        "Service Worker", 
        "GPUCache",
        "ShaderCache",
        "logs",
        "Crashpad",
        "tmp",
        "temp"
    ]
    
    def __init__(self, source_profile_dir: str):
        """
        ProfileManager を初期化
        
        Args:
            source_profile_dir: 元のブラウザプロファイルディレクトリ
            
        Raises:
            FileNotFoundError: ソースプロファイルディレクトリが存在しない場合
        """
        self.source_profile_dir = Path(source_profile_dir)
        if not self.source_profile_dir.exists():
            raise FileNotFoundError(f"Source profile directory not found: {source_profile_dir}")
        
        logger.info(f"🔧 ProfileManager initialized for: {source_profile_dir}")
    
    def create_selenium_profile(self, target_base_dir: str) -> str:
        """
        SeleniumProfile ディレクトリを作成し、重要なファイルをコピー
        
        Args:
            target_base_dir: SeleniumProfileを作成する親ディレクトリ
            
        Returns:
            作成されたSeleniumProfileディレクトリのパス
        """
        selenium_profile, _ = self.create_selenium_profile_with_stats(target_base_dir)
        return selenium_profile
    
    def create_selenium_profile_with_stats(self, target_base_dir: str) -> Tuple[str, int]:
        """
        SeleniumProfile ディレクトリを作成し、統計情報も返す
        
        Args:
            target_base_dir: SeleniumProfileを作成する親ディレクトリ
            
        Returns:
            (SeleniumProfileディレクトリのパス, コピーされたファイル数)
        """
        target_base = Path(target_base_dir)
        selenium_profile = target_base / "SeleniumProfile"
        
        # 既存のSeleniumProfileを削除して新規作成（新作法では上書き推奨）
        if selenium_profile.exists():
            logger.info(f"🗑️ Removing existing SeleniumProfile: {selenium_profile}")
            shutil.rmtree(selenium_profile, ignore_errors=True)
        
        # SeleniumProfileディレクトリの作成
        selenium_profile.mkdir(parents=True, exist_ok=True)
        selenium_default = selenium_profile / "Default"
        selenium_default.mkdir(exist_ok=True)
        
        logger.info(f"🔧 Creating Selenium profile: {selenium_profile}")
        
        # 重要ファイルのコピー
        copied_files = []
        for file_path in self.ESSENTIAL_FILES:
            source_file = self.source_profile_dir / file_path
            target_file = selenium_profile / file_path
            
            if source_file.exists():
                try:
                    # 親ディレクトリを作成
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # ファイルサイズチェック（大きすぎるファイルはスキップ）
                    if source_file.is_file() and source_file.stat().st_size > 100 * 1024 * 1024:  # 100MB
                        logger.warning(f"⚠️ Skipping large file {file_path}: {source_file.stat().st_size / 1024 / 1024:.1f}MB")
                        continue
                    
                    # ファイルコピー実行
                    if source_file.is_file():
                        shutil.copy2(source_file, target_file)
                    else:
                        # ディレクトリの場合は中身も含めてコピー
                        shutil.copytree(source_file, target_file, dirs_exist_ok=True)
                    
                    copied_files.append(file_path)
                    logger.debug(f"✅ Copied: {file_path}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to copy {file_path}: {e}")
            else:
                logger.debug(f"⏭️ Skipped (not found): {file_path}")
        
        logger.info(f"✅ Selenium profile created with {len(copied_files)} files copied")
        return str(selenium_profile), len(copied_files)
    
    def cleanup_selenium_profile(self, selenium_profile_dir: str) -> bool:
        """
        SeleniumProfileディレクトリを安全に削除
        
        Args:
            selenium_profile_dir: 削除するSeleniumProfileディレクトリ
            
        Returns:
            削除成功の可否
        """
        try:
            profile_path = Path(selenium_profile_dir)
            
            # 安全性チェック: SeleniumProfileディレクトリのみ削除可能
            if not profile_path.exists():
                logger.info(f"⏭️ SeleniumProfile already deleted: {selenium_profile_dir}")
                return True
                
            if profile_path.name != "SeleniumProfile":
                logger.error(f"❌ Safety check failed: Not a SeleniumProfile directory: {profile_path.name}")
                return False
            
            # 削除実行
            shutil.rmtree(profile_path, ignore_errors=True)
            logger.info(f"🗑️ Selenium profile cleaned up: {selenium_profile_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup selenium profile: {e}")
            return False
    
    def is_profile_locked(self) -> bool:
        """
        プロファイルがロックされているかチェック
        
        Returns:
            プロファイルロック状態
        """
        lock_files = [
            "SingletonLock",
            "lockfile",
            ".lock"
        ]
        
        for lock_file in lock_files:
            if (self.source_profile_dir / lock_file).exists():
                logger.warning(f"🔒 Profile lock detected: {lock_file}")
                return True
        
        return False
    
    def get_profile_info(self) -> dict:
        """
        プロファイル情報を取得
        
        Returns:
            プロファイル情報の辞書
        """
        info = {
            "source_path": str(self.source_profile_dir),
            "exists": self.source_profile_dir.exists(),
            "is_locked": self.is_profile_locked(),
            "essential_files_found": [],
            "missing_files": []
        }
        
        for file_path in self.ESSENTIAL_FILES:
            full_path = self.source_profile_dir / file_path
            if full_path.exists():
                info["essential_files_found"].append(file_path)
            else:
                info["missing_files"].append(file_path)
        
        return info
    
    def validate_selenium_profile(self, selenium_profile_dir: str) -> bool:
        """
        SeleniumProfileの整合性をチェック
        
        Args:
            selenium_profile_dir: チェックするSeleniumProfileディレクトリ
            
        Returns:
            プロファイルが有効かどうか
        """
        try:
            profile_path = Path(selenium_profile_dir)
            
            if not profile_path.exists():
                logger.error(f"❌ SeleniumProfile does not exist: {selenium_profile_dir}")
                return False
            
            if profile_path.name != "SeleniumProfile":
                logger.error(f"❌ Invalid profile directory name: {profile_path.name}")
                return False
            
            # 最低限必要なファイルの存在確認
            required_files = ["Default/Preferences", "Local State"]
            missing_files = []
            
            for file_path in required_files:
                if not (profile_path / file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                logger.error(f"❌ Missing required files in SeleniumProfile: {missing_files}")
                return False
            
            logger.info(f"✅ SeleniumProfile validation passed: {selenium_profile_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ SeleniumProfile validation failed: {e}")
            return False


class ChromeProfileManager(ProfileManager):
    """Chrome専用のProfileManager"""
    
    def __init__(self, source_profile_dir: Optional[str] = None):
        if source_profile_dir is None:
            # macOSのデフォルトChromeプロファイルパス
            source_profile_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        super().__init__(source_profile_dir)


class EdgeProfileManager(ProfileManager):
    """Edge専用のProfileManager"""
    
    def __init__(self, source_profile_dir: Optional[str] = None):
        if source_profile_dir is None:
            # macOSのデフォルトEdgeプロファイルパス
            source_profile_dir = os.path.expanduser("~/Library/Application Support/Microsoft Edge")
        super().__init__(source_profile_dir)
