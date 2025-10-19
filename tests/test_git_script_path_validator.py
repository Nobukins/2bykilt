"""
Unit tests for GitScriptPathValidator
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.utils.git_script_path import GitScriptPathValidator, GitScriptPathValidationResult


@pytest.mark.ci_safe
class TestGitScriptPathValidator:
    """GitScriptPathValidator の単体テスト"""

    @pytest.fixture
    def temp_workspace(self):
        """テスト用の作業ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_valid_path(self, temp_workspace):
        """有効なパスの検証"""
        # 有効なPythonスクリプトファイルを作成
        script_path = Path(temp_workspace) / "test_script.py"
        script_path.write_text("#!/usr/bin/env python3\nprint('test')")

        validator = GitScriptPathValidator(repo_root=temp_workspace)
        result = validator.validate_and_normalize_path(str(script_path))

        assert result.is_valid is True
        assert result.normalized_path == str(script_path.resolve())
        assert result.error_message is None

    def test_validate_nonexistent_file(self, temp_workspace):
        """存在しないファイルのパス検証"""
        nonexistent_path = os.path.join(temp_workspace, "nonexistent.py")

        validator = GitScriptPathValidator(repo_root=temp_workspace)
        result = validator.validate_and_normalize_path(nonexistent_path)

        assert result.is_valid is False
        assert "not found" in result.error_message

    def test_validate_directory_traversal_attack(self, temp_workspace):
        """ディレクトリトラバーサル攻撃の検証"""
        # 攻撃的なパス
        attack_path = os.path.join(temp_workspace, "../../../etc/passwd")

        validator = GitScriptPathValidator(repo_root=temp_workspace)
        result = validator.validate_and_normalize_path(attack_path)

        assert result.is_valid is False
        assert "escapes repository root" in result.error_message

    def test_validate_non_python_file(self, temp_workspace):
        """Pythonファイル以外の検証"""
        # テキストファイルを作成
        text_file = Path(temp_workspace) / "test.txt"
        text_file.write_text("This is not a Python file")

        validator = GitScriptPathValidator(repo_root=temp_workspace)
        result = validator.validate_and_normalize_path(str(text_file))

        assert result.is_valid is False
        assert "not allowed" in result.error_message

    def test_validate_python_file_without_shebang(self, temp_workspace):
        """shebangなしのPythonファイルの検証"""
        # shebangなしのPythonファイル
        script_path = Path(temp_workspace) / "no_shebang.py"
        script_path.write_text("print('hello world')")

        validator = GitScriptPathValidator(repo_root=temp_workspace)
        result = validator.validate_and_normalize_path(str(script_path))

        assert result.is_valid is True  # shebangは必須ではない

    def test_validate_empty_path(self):
        """空のパスの検証"""
        validator = GitScriptPathValidator(repo_root="/tmp")
        result = validator.validate_and_normalize_path("")

        assert result.is_valid is False
        assert "escapes repository root" in result.error_message

    def test_validate_none_path(self):
        """Noneパスの検証"""
        validator = GitScriptPathValidator(repo_root="/tmp")
        result = validator.validate_and_normalize_path(None)

        assert result.is_valid is False
        assert "Path validation failed" in result.error_message

    def test_path_normalization(self, temp_workspace):
        """パスの正規化テスト"""
        # まずsubdirを作成
        subdir = Path(temp_workspace) / "subdir"
        subdir.mkdir(parents=True)
        
        # 相対パスを作成 (.. を使用)
        script_path = subdir / ".." / "test_script.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("#!/usr/bin/env python3\nprint('test')")

        validator = GitScriptPathValidator(repo_root=temp_workspace)
        result = validator.validate_and_normalize_path(str(script_path))

        assert result.is_valid is True
        # 正規化されたパスが返されることを確認
        assert os.path.isabs(result.normalized_path)
        assert result.normalized_path == str(script_path.resolve())

    def test_validate_executable_permissions(self, temp_workspace):
        """実行権限の検証"""
        script_path = Path(temp_workspace) / "test_script.py"
        script_path.write_text("#!/usr/bin/env python3\nprint('test')")

        # 実行権限を付与
        script_path.chmod(0o755)

        validator = GitScriptPathValidator(repo_root=temp_workspace)
        result = validator.validate_and_normalize_path(str(script_path))

        assert result.is_valid is True
        assert result.normalized_path == str(script_path.resolve())

    @pytest.mark.skipif(os.name != 'posix', reason="Unix-like systems only")
    def test_validate_no_execute_permissions(self, temp_workspace):
        """実行権限なしの検証（Unix系のみ）"""
        script_path = Path(temp_workspace) / "test_script.py"
        script_path.write_text("#!/usr/bin/env python3\nprint('test')")

        # 実行権限を削除
        script_path.chmod(0o644)

        validator = GitScriptPathValidator(repo_root=temp_workspace)
        result = validator.validate_and_normalize_path(str(script_path))

        # 実行権限なしでもPythonファイルとして有効（pythonコマンドで実行可能）
        assert result.is_valid is True
        assert result.normalized_path == str(script_path.resolve())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
