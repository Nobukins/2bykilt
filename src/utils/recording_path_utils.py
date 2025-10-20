"""
録画パス設定ユーティリティ - クロスプラットフォーム対応 (Issue #353)

注意: Issue #353 により、すべての録画はartifacts/runs/<run>-art/videos
に統一されました。このモジュールは互換性のため保持されています。
新規コードはrecording_dir_resolverを直接使用してください。
"""

import os
from pathlib import Path

# 統一されたリゾルバのimportを使用
from src.utils.recording_dir_resolver import create_or_get_recording_dir


def get_recording_path(fallback_relative_path: str = None) -> str:  # noqa: ARG001
    """
    録画ディレクトリのパスを取得する
    
    Note: Issue #353により、./tmp/record_videosへの参照は削除されました。
    常にartifacts/runs/<run>-art/videosを使用します。
    
    Args:
        fallback_relative_path: 非推奨（互換性のため保持）
        
    Returns:
        str: 録画ディレクトリのパス
    """
    return str(create_or_get_recording_dir())


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


if __name__ == "__main__":
    # テスト実行
    print("Recording Path Utility Test (Issue #353)")
    print("=" * 40)
    
    recording_path = get_recording_path()
    print(f"Selected recording path: {recording_path}")
    print("Note: All recordings are now in artifacts/runs/<run>-art/videos")

