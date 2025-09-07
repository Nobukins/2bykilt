"""
Unit tests for GitScriptAutomator subprocess execution and parameter substitution
"""
import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import subprocess

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.utils.git_script_automator import GitScriptAutomator


class TestGitScriptAutomatorSubprocess:
    """GitScriptAutomator の subprocess 実行とパラメータ置換のテスト"""

    @pytest.fixture
    def temp_workspace(self):
        """テスト用の作業ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_edge_profile(self):
        """モックのEdgeプロファイルを作成"""
        temp_base = tempfile.mkdtemp()
        edge_profile = Path(temp_base) / "Microsoft Edge"

        # モックプロファイル構造を作成
        default_profile = edge_profile / "Default"
        default_profile.mkdir(parents=True)

        # 重要なファイルを作成
        essential_files = {
            "Default/Preferences": '{"profile":{"name":"Test User","avatar_index":0}}',
            "Default/Secure Preferences": '{"protection":{"macs":{"profile":{"name":"secure_data"}}}}',
            "Default/Login Data": 'SQLite format 3\x00login_data_mock',
            "Default/Cookies": 'SQLite format 3\x00cookies_mock',
            "Local State": '{"browser":{"check_default_browser":false}}'
        }

        for file_path, content in essential_files.items():
            full_path = edge_profile / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')

        yield str(edge_profile)

        import shutil
        shutil.rmtree(temp_base, ignore_errors=True)

    def create_test_script(self, workspace, script_name="test_script.py"):
        """テスト用のPythonスクリプトを作成"""
        script_path = Path(workspace) / script_name
        script_content = '''#!/usr/bin/env python3
import sys
import json

def main():
    print("git_script_start")
    args = sys.argv[1:]
    result = {"args": args, "success": True}

    # 引数をパース
    query = None
    for arg in args:
        if arg.startswith("--query="):
            query = arg.split("=", 1)[1]
            break

    if query:
        result["query"] = query
        print(f"Query: {query}")

    print("git_script_end")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''
        script_path.write_text(script_content)
        script_path.chmod(0o755)  # 実行権限を付与
        return str(script_path)

    @pytest.mark.asyncio
    async def test_execute_git_script_workflow_with_subprocess(self, mock_edge_profile, temp_workspace):
        """subprocess を使用した git_script ワークフローのテスト"""
        # テストスクリプトを作成
        script_path = self.create_test_script(temp_workspace)

        # GitScriptAutomator を作成
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # プロファイル検証をモック化
        with patch.object(automator, 'validate_source_profile', return_value=True):
            # ワークフローを実行
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path=script_path,
                command='python ${script_path} --query=${params.query}',
                params={'query': 'test_value'}
            )

            # 結果を検証
            assert result["success"] is True
            assert "stdout" in result
            assert "git_script_start" in result["stdout"]
            assert "git_script_end" in result["stdout"]
            assert "test_value" in result["stdout"]

    @pytest.mark.asyncio
    async def test_parameter_substitution_script_path(self, mock_edge_profile, temp_workspace):
        """${script_path} パラメータ置換のテスト"""
        script_path = self.create_test_script(temp_workspace)

        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        with patch.object(automator, 'validate_source_profile', return_value=True):
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path=script_path,
                command='python ${script_path}',
                params={}
            )

            assert result["success"] is True
            # パラメータ置換が機能していることをstdoutで確認
            assert "git_script_start" in result["stdout"]

    @pytest.mark.asyncio
    async def test_parameter_substitution_params(self, mock_edge_profile, temp_workspace):
        """${params.*} パラメータ置換のテスト"""
        script_path = self.create_test_script(temp_workspace)

        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        with patch.object(automator, 'validate_source_profile', return_value=True):
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path=script_path,
                command='python ${script_path} --query=${params.query} --count=${params.count}',
                params={'query': 'search_term', 'count': '10'}
            )

            assert result["success"] is True
            # パラメータ置換が機能していることを確認
            assert "search_term" in result["stdout"]
            assert "10" in result["stdout"]

    @pytest.mark.asyncio
    async def test_script_execution_error_handling(self, mock_edge_profile, temp_workspace):
        """スクリプト実行エラーのハンドリングテスト"""
        # エラーを発生させるスクリプトを作成
        error_script = Path(temp_workspace) / "error_script.py"
        error_script.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(1)")
        error_script.chmod(0o755)

        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        with patch.object(automator, 'validate_source_profile', return_value=True):
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path=str(error_script),
                command='python ${script_path}',
                params={}
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_script_timeout_handling(self, mock_edge_profile, temp_workspace):
        """スクリプトタイムアウトのハンドリングテスト"""
        # タイムアウト機能は実装されていないので、通常の実行をテスト
        timeout_script = Path(temp_workspace) / "timeout_script.py"
        timeout_script.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(1)")  # 短時間実行
        timeout_script.chmod(0o755)

        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # タイムアウトパラメータなしで実行
        with patch.object(automator, 'validate_source_profile', return_value=True):
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path=str(timeout_script),
                command='python ${script_path}',
                params={}
            )

            # 正常に実行されることを確認
            assert result["success"] is True
            assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_invalid_script_path(self, mock_edge_profile, temp_workspace):
        """無効なスクリプトパスのテスト"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        with patch.object(automator, 'validate_source_profile', return_value=True):
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path="/nonexistent/path/script.py",
                command='python ${script_path}',
                params={}
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_parameters(self, mock_edge_profile, temp_workspace):
        """空のパラメータでのテスト"""
        script_path = self.create_test_script(temp_workspace)

        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        with patch.object(automator, 'validate_source_profile', return_value=True):
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path=script_path,
                command='python ${script_path}',
                params={}
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_complex_parameter_substitution(self, mock_edge_profile, temp_workspace):
        """複雑なパラメータ置換のテスト"""
        # シンプルなパラメータを持つスクリプト
        complex_script = Path(temp_workspace) / "complex_script.py"
        complex_script.write_text('''#!/usr/bin/env python3
import sys
import json

def main():
    print("git_script_start")
    args = sys.argv[1:]
    result = {"args": args}

    # シンプルな引数をパース
    for arg in args:
        if arg.startswith("--output="):
            result["output_file"] = arg.split("=", 1)[1]
        elif arg.startswith("--value="):
            result["value"] = arg.split("=", 1)[1]

    print("git_script_end")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
''')
        complex_script.chmod(0o755)

        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        with patch.object(automator, 'validate_source_profile', return_value=True):
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path=str(complex_script),
                command='python ${script_path} --output=${params.output} --value=${params.value}',
                params={
                    'output': 'result.json',
                    'value': 'test_data'
                }
            )

            assert result["success"] is True
            # 複雑なパラメータ置換が機能していることを確認
            assert "result.json" in result["stdout"]
            assert "test_data" in result["stdout"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
