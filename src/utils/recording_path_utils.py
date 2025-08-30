"""
録画パス設定ユーティリティ - クロスプラットフォーム対応
"""

import os
import platform
import tempfile
from pathlib import Path

def get_recording_path(fallback_relative_path: str = "./tmp/record_videos") -> str:
    """
    録画ディレクトリのパスを取得する（クロスプラットフォーム対応）
    
    Args:
        fallback_relative_path: フォールバック時の相対パス
        
    Returns:
        str: 録画ディレクトリのパス
    """
    # 環境変数から取得
    recording_dir = os.environ.get("RECORDING_PATH", "").strip()
    
    # 空文字列や無効なパスの場合のフォールバック処理
    if not recording_dir or recording_dir == "":
        if platform.system() == "Windows":
            # Windows用デフォルトパス
            recording_dir = os.path.join(
                os.path.expanduser("~"), 
                "Documents", 
                "2bykilt", 
                "recordings"
            )
        else:
            # macOS/Linux用デフォルトパス
            recording_dir = fallback_relative_path
    
    # パスの正規化
    recording_dir = os.path.abspath(recording_dir)
    
    # ディレクトリ作成
    try:
        os.makedirs(recording_dir, exist_ok=True)
        print(f"✅ Recording directory prepared: {recording_dir}")
        return recording_dir
    except Exception as e:
        print(f"⚠️ Warning: Could not create recording directory {recording_dir}: {e}")
        # フォールバック: 一時ディレクトリを使用
        fallback_dir = tempfile.gettempdir()
        print(f"Using temporary directory as fallback: {fallback_dir}")
        return fallback_dir

def ensure_recording_directory_exists(recording_path: str) -> bool:
    """
    録画ディレクトリの存在を確認し、必要に応じて作成する
    
    Args:
        recording_path: 録画ディレクトリのパス
        
    Returns:
        bool: 成功した場合True、失敗した場合False
    """
    try:
        if not recording_path or recording_path.strip() == "":
            return False
            
        Path(recording_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"❌ Failed to create recording directory {recording_path}: {e}")
        return False

def get_platform_specific_recording_path() -> str:
    """
    プラットフォーム固有のデフォルト録画パスを取得
    
    Returns:
        str: プラットフォーム固有のデフォルトパス
    """
    system = platform.system()
    
    if system == "Windows":
        return os.path.join(
            os.path.expanduser("~"), 
            "Documents", 
            "2bykilt", 
            "recordings"
        )
    elif system == "Darwin":  # macOS
        return os.path.join(
            os.path.expanduser("~"), 
            "Documents", 
            "2bykilt", 
            "recordings"
        )
    else:  # Linux and others
        return os.path.join(
            os.path.expanduser("~"), 
            ".local", 
            "share", 
            "2bykilt", 
            "recordings"
        )

if __name__ == "__main__":
    # テスト実行
    print("Recording Path Utility Test")
    print("=" * 40)
    
    recording_path = get_recording_path()
    print(f"Selected recording path: {recording_path}")
    
    platform_path = get_platform_specific_recording_path()
    print(f"Platform-specific path: {platform_path}")
    
    # ディレクトリ存在確認
    exists = ensure_recording_directory_exists(recording_path)
    print(f"Directory creation successful: {exists}")
