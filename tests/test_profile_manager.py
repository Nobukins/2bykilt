"""
ProfileManager の単体テスト
TDD approach for Chrome/Edge 2024+ profile management
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.utils.profile_manager import ProfileManager


@pytest.mark.ci_safe
class TestProfileManager:
    """ProfileManager の完全なテストスイート"""
    
    @pytest.fixture
    def temp_dirs(self):
        """テスト用の一時ディレクトリを作成"""
        temp_base = tempfile.mkdtemp()
        source_profile = Path(temp_base) / "source_profile"
        target_base = Path(temp_base) / "target_base"
        
        # ソースプロファイルのモックデータを作成
        source_default = source_profile / "Default"
        source_default.mkdir(parents=True)
        
        # 重要なファイルを作成（実際のChrome/Edgeファイル構造）
        essential_files = {
            "Default/Preferences": '{"profile":{"name":"Test User","avatar_index":0},"session":{"restore_on_startup":1}}',
            "Default/Secure Preferences": '{"protection":{"macs":{"profile":{"name":"secure_data"}}}}',
            "Default/Login Data": 'SQLite format 3\x00login_data_mock',
            "Default/Web Data": 'SQLite format 3\x00web_data_mock',
            "Default/Cookies": 'SQLite format 3\x00cookies_mock',
            "Default/Bookmarks": '{"roots":{"bookmark_bar":{"children":[],"date_added":"13347388949470112","date_modified":"0","id":"1","name":"ブックマーク バー","type":"folder"}}}',
            "Default/History": 'SQLite format 3\x00history_mock',
            "Local State": '{"browser":{"enabled_labs_experiments":[],"check_default_browser":false}}'
        }
        
        for file_path, content in essential_files.items():
            full_path = source_profile / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
        
        # 不要なファイルも作成（コピーされないことを確認）
        (source_default / "Cache").mkdir(exist_ok=True)
        (source_default / "Cache" / "temp_file").write_text("cache_data")
        (source_default / "Service Worker").mkdir(exist_ok=True)
        
        yield source_profile, target_base
        
        # クリーンアップ
        shutil.rmtree(temp_base, ignore_errors=True)
    
    def test_create_selenium_profile_directory_structure(self, temp_dirs):
        """SeleniumProfileディレクトリ構造が正しく作成される"""
        source_profile, target_base = temp_dirs
        
        manager = ProfileManager(str(source_profile))
        selenium_profile = manager.create_selenium_profile(str(target_base))
        
        # 基本構造の確認
        selenium_path = Path(selenium_profile)
        assert selenium_path.exists(), "SeleniumProfile directory should exist"
        assert selenium_path.name == "SeleniumProfile", "Directory name should be SeleniumProfile"
        assert (selenium_path / "Default").exists(), "Default subdirectory should exist"
        
        # パスの確認
        expected_path = target_base / "SeleniumProfile"
        assert selenium_path == expected_path, f"Expected {expected_path}, got {selenium_path}"
    
    def test_copy_essential_profile_files(self, temp_dirs):
        """重要なプロファイルファイルが正しくコピーされる"""
        source_profile, target_base = temp_dirs
        
        manager = ProfileManager(str(source_profile))
        selenium_profile = manager.create_selenium_profile(str(target_base))
        
        selenium_path = Path(selenium_profile)
        
        # 重要ファイルの存在確認
        essential_checks = [
            "Default/Preferences",
            "Default/Secure Preferences", 
            "Default/Login Data",
            "Default/Web Data",
            "Default/Cookies",
            "Default/Bookmarks",
            "Default/History",
            "Local State"
        ]
        
        for file_path in essential_checks:
            target_file = selenium_path / file_path
            assert target_file.exists(), f"Essential file {file_path} should be copied"
            
            # ファイル内容の確認
            if file_path == "Default/Preferences":
                content = target_file.read_text(encoding='utf-8')
                assert "Test User" in content, "Preferences content should be preserved"
    
    def test_skip_non_essential_files(self, temp_dirs):
        """不要なファイルがコピーされないことを確認"""
        source_profile, target_base = temp_dirs
        
        manager = ProfileManager(str(source_profile))
        selenium_profile = manager.create_selenium_profile(str(target_base))
        
        selenium_path = Path(selenium_profile)
        
        # キャッシュファイルがコピーされていないことを確認
        cache_dir = selenium_path / "Default" / "Cache"
        service_worker_dir = selenium_path / "Default" / "Service Worker"
        
        assert not cache_dir.exists(), "Cache directory should not be copied"
        assert not service_worker_dir.exists(), "Service Worker directory should not be copied"
    
    def test_handle_missing_source_profile(self):
        """元プロファイルが存在しない場合の適切な処理"""
        with pytest.raises(FileNotFoundError) as exc_info:
            ProfileManager("/nonexistent/path")
        
        assert "Source profile directory not found" in str(exc_info.value)
    
    def test_handle_existing_selenium_profile(self, temp_dirs):
        """既存のSeleniumProfileがある場合の処理（上書き）"""
        source_profile, target_base = temp_dirs
        
        manager = ProfileManager(str(source_profile))
        
        # 初回作成
        selenium_profile1 = manager.create_selenium_profile(str(target_base))
        
        # 既存ファイルを変更
        test_file = Path(selenium_profile1) / "Default" / "test_marker"
        test_file.write_text("first_creation")
        
        # 2回目作成（既存の場合は上書き）
        selenium_profile2 = manager.create_selenium_profile(str(target_base))
        
        assert selenium_profile1 == selenium_profile2
        assert Path(selenium_profile2).exists()
        
        # 上書きされたことを確認（test_markerが存在しない）
        assert not test_file.exists(), "Existing profile should be recreated"
    
    def test_cleanup_selenium_profile(self, temp_dirs):
        """SeleniumProfileディレクトリの削除"""
        source_profile, target_base = temp_dirs
        
        manager = ProfileManager(str(source_profile))
        selenium_profile = manager.create_selenium_profile(str(target_base))
        
        # 作成確認
        assert Path(selenium_profile).exists()
        
        # クリーンアップ実行
        result = manager.cleanup_selenium_profile(selenium_profile)
        
        assert result == True, "Cleanup should succeed"
        assert not Path(selenium_profile).exists(), "SeleniumProfile should be deleted"
    
    def test_cleanup_non_selenium_profile_safety(self, temp_dirs):
        """SeleniumProfile以外のディレクトリは削除しない安全機能"""
        source_profile, target_base = temp_dirs
        
        manager = ProfileManager(str(source_profile))
        
        # 通常のディレクトリを作成
        normal_dir = target_base / "NormalDirectory"
        normal_dir.mkdir(parents=True)
        (normal_dir / "important_file").write_text("important_data")
        
        # クリーンアップ試行（失敗するべき）
        result = manager.cleanup_selenium_profile(str(normal_dir))
        
        assert result == False, "Should not cleanup non-SeleniumProfile directories"
        assert normal_dir.exists(), "Normal directory should remain intact"
        assert (normal_dir / "important_file").exists(), "Files should be preserved"
    
    def test_is_profile_locked_detection(self, temp_dirs):
        """プロファイルロック状態の検出"""
        source_profile, target_base = temp_dirs
        
        manager = ProfileManager(str(source_profile))
        
        # ロック状態ではない
        assert not manager.is_profile_locked(), "Profile should not be locked initially"
        
        # ロックファイルを作成
        lock_file = source_profile / "SingletonLock"
        lock_file.write_text("locked")
        
        # ロック状態の検出
        assert manager.is_profile_locked(), "Profile should be detected as locked"
    
    def test_get_copied_files_count(self, temp_dirs):
        """コピーされたファイル数の報告"""
        source_profile, target_base = temp_dirs
        
        manager = ProfileManager(str(source_profile))
        selenium_profile, copied_count = manager.create_selenium_profile_with_stats(str(target_base))
        
        # 作成した8つのessentialファイルがコピーされることを確認
        assert copied_count == 8, f"Expected 8 files copied, got {copied_count}"
        assert Path(selenium_profile).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
