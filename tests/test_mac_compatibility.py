#!/usr/bin/env python3
"""
Mac互換性検証テストスイート - Windows対応のPRの検証
"""

import os
import pytest
import sys
import asyncio
import subprocess
import tempfile
import time
from pathlib import Path

# プロジェクトディレクトリを設定
PROJECT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

class MacCompatibilityTest:
    def __init__(self):
        self.results = []
        self.python_exec = self._detect_python_exec()

    def _detect_python_exec(self) -> str:
        candidates = [
            PROJECT_DIR / 'venv' / 'bin' / 'python',
            PROJECT_DIR.parent / 'venv' / 'bin' / 'python',
            Path(sys.executable)
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return sys.executable
        
    def log_result(self, test_name, success, message):
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status}: {test_name} - {message}"
        print(result)
        self.results.append((test_name, success, message))
        
    def test_basic_imports_llm_false(self):
        """基本モジュールのインポートテスト (LLM=false)"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'false'
            
            test_code = '''
import sys
import os
os.environ["ENABLE_LLM"] = "false"

try:
    from src.utils import utils
    from src.browser.browser_manager import initialize_browser
    from src.config.standalone_prompt_evaluator import pre_evaluate_prompt_standalone
    print("SUCCESS: All basic modules imported")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.log_result("基本モジュールインポート(LLM=false)", True, "正常にインポート完了")
            else:
                self.log_result("基本モジュールインポート(LLM=false)", False, f"stderr: {result.stderr}")
                
        except Exception as e:
            self.log_result("基本モジュールインポート(LLM=false)", False, str(e))
    
    def test_basic_imports_llm_true(self):
        """基本モジュールのインポートテスト (LLM=true)"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'true'
            
            test_code = '''
import sys
import os
os.environ["ENABLE_LLM"] = "true"

try:
    from src.config.llms_parser import pre_evaluate_prompt
    from src.agent.agent_manager import stop_agent
    from src.ui.stream_manager import run_with_stream
    print("SUCCESS: All LLM modules imported")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.log_result("LLMモジュールインポート(LLM=true)", True, "正常にインポート完了")
            else:
                self.log_result("LLMモジュールインポート(LLM=true)", False, f"stderr: {result.stderr}")
                
        except Exception as e:
            self.log_result("LLMモジュールインポート(LLM=true)", False, str(e))
    
    def test_playwright_browser(self):
        """Playwrightブラウザの動作テスト"""
        try:
            test_code = '''
import asyncio
from playwright.async_api import async_playwright

@pytest.mark.ci_safe
async def test_browser():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://example.com")
            title = await page.title()
            await browser.close()
            print(f"SUCCESS: Browser test completed. Title: {title}")
            return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

result = asyncio.run(test_browser())
if not result:
    exit(1)
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.log_result("Playwrightブラウザ動作", True, "ブラウザの起動・操作・終了が正常完了")
            else:
                self.log_result("Playwrightブラウザ動作", False, f"stderr: {result.stderr}")
                
        except Exception as e:
            self.log_result("Playwrightブラウザ動作", False, str(e))
    
    def test_app_startup_llm_false(self):
        """アプリケーション起動テスト (LLM=false)"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'false'
            root = Path(__file__).resolve().parents[1]
            bykilt_path = root / 'bykilt.py'
            cmd = [self.python_exec, str(bykilt_path), '--help'] if bykilt_path.exists() else [self.python_exec, '-m', 'bykilt', '--help']
            result = subprocess.run(
                cmd,
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and "Gradio UI for 2Bykilt Agent" in result.stdout:
                self.log_result("アプリ起動(LLM=false)", True, "ヘルプメッセージが正常表示")
            else:
                self.log_result("アプリ起動(LLM=false)", False, f"stderr: {result.stderr}")
                
        except Exception as e:
            self.log_result("アプリ起動(LLM=false)", False, str(e))
    
    def test_app_startup_llm_true(self):
        """アプリケーション起動テスト (LLM=true)"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'true'
            root = Path(__file__).resolve().parents[1]
            bykilt_path = root / 'bykilt.py'
            cmd = [self.python_exec, str(bykilt_path), '--help'] if bykilt_path.exists() else [self.python_exec, '-m', 'bykilt', '--help']
            result = subprocess.run(
                cmd,
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and "Gradio UI for 2Bykilt Agent" in result.stdout:
                self.log_result("アプリ起動(LLM=true)", True, "ヘルプメッセージが正常表示")
            else:
                self.log_result("アプリ起動(LLM=true)", False, f"stderr: {result.stderr}")
                
        except Exception as e:
            self.log_result("アプリ起動(LLM=true)", False, str(e))
    
    def test_cross_platform_paths(self):
        """クロスプラットフォーム対応のパス処理テスト"""
        try:
            test_code = '''
import os
import platform
from pathlib import Path

# Test cross-platform path handling
project_dir = Path.cwd()
temp_file = project_dir / 'test_path.tmp'

# Create and remove test file
temp_file.touch()
if temp_file.exists():
    temp_file.unlink()
    print("SUCCESS: Cross-platform path handling works")
else:
    print("ERROR: Failed to create test file")
    exit(1)

print(f"Platform: {platform.system()}")
print(f"Project dir: {project_dir}")
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.log_result("クロスプラットフォームパス処理", True, "パス処理が正常動作")
            else:
                self.log_result("クロスプラットフォームパス処理", False, f"stderr: {result.stderr}")
                
        except Exception as e:
            self.log_result("クロスプラットフォームパス処理", False, str(e))
    
    def run_all_tests(self):
        """全テストを実行"""
        print("=" * 60)
        print("Mac互換性検証テスト開始 - Windows対応PRの検証")
        print("=" * 60)
        
        tests = [
            self.test_basic_imports_llm_false,
            self.test_basic_imports_llm_true,
            self.test_playwright_browser,
            self.test_app_startup_llm_false,
            self.test_app_startup_llm_true,
            self.test_cross_platform_paths,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                test_name = test.__name__
                self.log_result(test_name, False, f"テスト実行エラー: {e}")
        
        print("\n" + "=" * 60)
        print("テスト結果サマリー")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        for test_name, success, message in self.results:
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {message}")
        
        print(f"\n通過: {passed}/{total} テスト")
        
        if passed == total:
            print("🎉 全テストが通過しました！Mac環境でのWindows対応PRは正常に動作します。")
            return True
        else:
            print("⚠️ 一部のテストが失敗しました。詳細を確認してください。")
            return False

if __name__ == "__main__":
    tester = MacCompatibilityTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
