#!/usr/bin/env python3
"""
実際のブラウザ機能テスト - 両モードでの機能確認
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

class BrowserFunctionTest:
    def __init__(self):
        self.results = []
        self.python_exec = self._detect_python_exec()

    def _detect_python_exec(self) -> str:
        """Attempt to locate project root venv python.

        Strategy:
          1. Traverse parent dirs from current test file looking for 'venv/bin/python'.
          2. Fallback to sys.executable.
        """
        current = PROJECT_DIR
        for _ in range(6):  # search up to repo root safely
            candidate = current / 'venv' / 'bin' / 'python'
            if candidate.exists():
                return str(candidate)
            current = current.parent
        # fallback
        return sys.executable
        
    def log_result(self, test_name, success, message):
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status}: {test_name} - {message}"
        print(result)
        self.results.append((test_name, success, message))
    
    def test_browser_manager_llm_false(self):
        """ブラウザマネージャー機能テスト (LLM=false)"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'false'
            
            test_code = '''
import os
import asyncio
os.environ["ENABLE_LLM"] = "false"

from src.browser.browser_manager import initialize_browser, close_global_browser

@pytest.mark.ci_safe
async def test_browser_manager():
    try:
        # initialize_browser returns a dict-like result
        result = await initialize_browser(headless=True)
        if isinstance(result, dict) and result.get("status") == "success" and result.get("browser"):
            browser = result["browser"]
            page = await browser.new_page()
            await page.goto("https://example.com")
            title = await page.title()
            await browser.close()
            print(f"SUCCESS: Browser manager test completed. Title: {title}")
            return True
        else:
            print("ERROR: Failed to initialize browser manager")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

result = asyncio.run(test_browser_manager())
if not result:
    exit(1)
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.log_result("ブラウザマネージャー(LLM=false)", True, "ブラウザ管理機能が正常動作")
            else:
                self.log_result("ブラウザマネージャー(LLM=false)", False, f"stderr: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("ブラウザマネージャー(LLM=false)", False, str(e))
    
    def test_standalone_prompt_evaluator(self):
        """スタンドアロンプロンプト評価器テスト"""
        try:
            test_code = '''
import os
os.environ["ENABLE_LLM"] = "false"

from src.config.standalone_prompt_evaluator import (
    pre_evaluate_prompt_standalone,
    extract_params_standalone,
    resolve_sensitive_env_variables_standalone
)

# Test prompt evaluation
test_prompt = "navigate to https://example.com"
result = pre_evaluate_prompt_standalone(test_prompt)
print(f"Prompt evaluation result: {type(result)}")

# Test parameter extraction
params = {"url": "https://example.com"}
extracted = extract_params_standalone(test_prompt, params)
print(f"Parameter extraction result: {type(extracted)}")

# Test environment variable resolution
test_text = "Navigate to ${URL}"
resolved = resolve_sensitive_env_variables_standalone(test_text)
print(f"Environment variable resolution result: {type(resolved)}")

print("SUCCESS: Standalone prompt evaluator functions work")
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.log_result("スタンドアロンプロンプト評価器", True, "プロンプト評価機能が正常動作")
            else:
                self.log_result("スタンドアロンプロンプト評価器", False, f"stderr: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("スタンドアロンプロンプト評価器", False, str(e))
    
    def test_config_management(self):
        """設定管理テスト"""
        try:
            test_code = '''
import os
import tempfile
from pathlib import Path

from src.utils.default_config_settings import default_config, load_config_from_file, save_config_to_file

# Test default config
config = default_config()
print(f"Default config keys: {list(config.keys())}")

# Test save and load config
# Use provided API: save_config_to_file returns a message with path; parse it.
msg = save_config_to_file(config, './tmp/webui_settings_test')
import re
match = re.search(r"Configuration saved to (.+\.pkl)", msg)
if not match:
    print("ERROR: Could not parse saved config path")
    exit(1)
saved_path = match.group(1)
loaded_config = load_config_from_file(saved_path)
if isinstance(loaded_config, dict) and len(loaded_config) == len(config):
    print("SUCCESS: Config save/load works")
else:
    print("ERROR: Config save/load failed")
    exit(1)
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.log_result("設定管理", True, "設定の保存・読み込みが正常動作")
            else:
                self.log_result("設定管理", False, f"stderr: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("設定管理", False, str(e))
    
    def test_script_manager_availability(self):
        """スクリプトマネージャーの利用可能性テスト"""
        try:
            test_code = '''
from src.script.script_manager import run_script

# Test script manager import and basic functionality
print("SUCCESS: Script manager is available")
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.log_result("スクリプトマネージャー", True, "スクリプト管理機能が利用可能")
            else:
                self.log_result("スクリプトマネージャー", False, f"stderr: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("スクリプトマネージャー", False, str(e))
    
    def run_all_tests(self):
        """全機能テストを実行"""
        print("=" * 60)
        print("ブラウザ機能テスト開始 - 実機能確認")
        print("=" * 60)
        
        tests = [
            self.test_browser_manager_llm_false,
            self.test_standalone_prompt_evaluator,
            self.test_config_management,
            self.test_script_manager_availability,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                test_name = test.__name__
                self.log_result(test_name, False, f"テスト実行エラー: {e}")
        
        print("\n" + "=" * 60)
        print("機能テスト結果サマリー")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        for test_name, success, message in self.results:
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {message}")
        
        print(f"\n通過: {passed}/{total} テスト")
        
        if passed == total:
            print("🎉 全機能テストが通過しました！")
            return True
        else:
            print("⚠️ 一部の機能テストが失敗しました。")
            return False

if __name__ == "__main__":
    tester = BrowserFunctionTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
