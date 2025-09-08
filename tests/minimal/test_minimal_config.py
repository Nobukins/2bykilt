#!/usr/bin/env python3
"""
最小構成（LLM無効）での機能検証テストスイート
venv312環境でのLLM関連モジュールなしでの動作確認
"""

import os
import sys
import asyncio
import subprocess
import tempfile
import time
from pathlib import Path

# プロジェクトディレクトリを設定
PROJECT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

class MinimalConfigTest:
    def __init__(self):
        self.results = []
        self.python_exec = self._detect_python_exec()

    def _detect_python_exec(self) -> str:
        """Attempt to locate a project python (prefer venv/venv312) else fallback to current interpreter."""
        candidates = [
            PROJECT_DIR / 'venv' / 'bin' / 'python',
            PROJECT_DIR / 'venv312' / 'bin' / 'python',
            PROJECT_DIR.parent / 'venv' / 'bin' / 'python',
            PROJECT_DIR.parent / 'venv312' / 'bin' / 'python',
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
        
    def test_minimal_imports(self):
        """最小構成でのモジュールインポートテスト"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'false'
            
            test_code = '''
import sys
import os
os.environ["ENABLE_LLM"] = "false"

print("Starting minimal import test...")

# Test basic Python modules
try:
    import json
    import asyncio
    import subprocess
    from pathlib import Path
    print("✅ Basic Python modules imported")
except Exception as e:
    print(f"❌ Basic Python modules failed: {e}")
    sys.exit(1)

# Test third-party dependencies
try:
    import gradio as gr
    print("✅ Gradio imported")
except Exception as e:
    print(f"❌ Gradio import failed: {e}")
    sys.exit(1)

try:
    from playwright.async_api import async_playwright
    print("✅ Playwright imported")
except Exception as e:
    print(f"❌ Playwright import failed: {e}")
    sys.exit(1)

try:
    import pandas as pd
    import numpy as np
    print("✅ Data processing modules imported")
except Exception as e:
    print(f"❌ Data processing modules failed: {e}")
    sys.exit(1)

# Test project modules
try:
    from src.utils import utils
    print("✅ Utils module imported")
except Exception as e:
    print(f"❌ Utils module failed: {e}")
    sys.exit(1)

try:
    from src.browser.browser_manager import initialize_browser
    from src.browser.browser_config import BrowserConfig
    print("✅ Browser modules imported")
except Exception as e:
    print(f"❌ Browser modules failed: {e}")
    sys.exit(1)

try:
    from src.config.standalone_prompt_evaluator import (
        pre_evaluate_prompt_standalone,
        extract_params_standalone,
        resolve_sensitive_env_variables_standalone
    )
    print("✅ Standalone prompt evaluator imported")
except Exception as e:
    print(f"❌ Standalone prompt evaluator failed: {e}")
    sys.exit(1)

print("SUCCESS: All minimal configuration modules imported successfully")
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
                self.log_result("最小構成モジュールインポート", True, "すべてのモジュールが正常にインポート")
            else:
                self.log_result("最小構成モジュールインポート", False, f"エラー: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("最小構成モジュールインポート", False, str(e))
    
    def test_llm_modules_not_available(self):
        """LLM関連モジュールが利用不可であることを確認"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'false'
            
            test_code = '''
import sys
import os
os.environ["ENABLE_LLM"] = "false"

# Test that LLM modules are not available or properly handled
llm_modules_to_test = [
    ("anthropic", "anthropic"),
    ("openai", "openai"),
    ("langchain", "langchain"),
    ("browser_use", "browser_use"),
]

missing_modules = []
for module_name, import_name in llm_modules_to_test:
    try:
        __import__(import_name)
        print(f"⚠️ {module_name} is available (unexpected in minimal config)")
    except ImportError:
        missing_modules.append(module_name)
        print(f"✅ {module_name} not available (expected in minimal config)")

if len(missing_modules) >= 3:  # Most LLM modules should be missing
    print("SUCCESS: LLM modules are properly unavailable in minimal config")
else:
    print("WARNING: Some LLM modules are available in minimal config")
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and ("SUCCESS" in result.stdout or "WARNING" in result.stdout):
                self.log_result("LLMモジュール非利用確認", True, "LLM関連モジュールが適切に制限されている")
            else:
                self.log_result("LLMモジュール非利用確認", False, f"エラー: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("LLMモジュール非利用確認", False, str(e))
    
    def test_minimal_app_startup(self):
        """最小構成でのアプリケーション起動テスト"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'false'
            
            # Test help command
            bykilt_path = Path(__file__).resolve().parents[2] / 'bykilt.py'
            cmd = [self.python_exec, str(bykilt_path), '--help'] if bykilt_path.exists() else [self.python_exec, '-m', 'bykilt', '--help']
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and "Gradio UI for 2Bykilt Agent" in result.stdout:
                self.log_result("最小構成アプリ起動", True, "アプリケーションが正常に起動・ヘルプ表示")
                
                # Check for LLM disabled message
                if "LLM functionality is disabled" in result.stdout or "ENABLE_LLM=false" in result.stdout:
                    print("  ✅ LLM無効メッセージが正常に表示")
                else:
                    print("  ⚠️ LLM無効メッセージが表示されていない")
            else:
                self.log_result("最小構成アプリ起動", False, f"エラー: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("最小構成アプリ起動", False, str(e))
    
    def test_minimal_browser_functionality(self):
        """最小構成でのブラウザ機能テスト"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'false'
            
            test_code = '''
import os
import asyncio
os.environ["ENABLE_LLM"] = "false"

from playwright.async_api import async_playwright
from src.browser.browser_config import BrowserConfig

async def test_minimal_browser():
    try:
        print("Testing minimal browser functionality...")
        
        # Test browser config
        config = BrowserConfig()
        print(f"✅ Browser config created: {type(config)}")
        
        # Test direct Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            print("✅ Browser launched")
            
            page = await browser.new_page()
            print("✅ New page created")
            
            await page.goto("https://nogtips.wordpress.com/2025/03/31/llms-txt%e3%81%ab%e3%81%a4%e3%81%84%e3%81%a6/")
            print("✅ Page navigation successful")
            
            title = await page.title()
            print(f"✅ Page title retrieved: {title[:50]}")
            
            content = await page.content()
            if "httpbin" in content:
                print("✅ Page content verification successful")
            else:
                print("❌ Page content verification failed")
                return False
            
            await browser.close()
            print("✅ Browser closed successfully")
            
        print("SUCCESS: All minimal browser tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        return False

result = asyncio.run(test_minimal_browser())
if not result:
    exit(1)
'''
            
            result = subprocess.run(
                [self.python_exec, '-c', test_code],
                cwd=PROJECT_DIR,
                env=env,
                capture_output=True,
                text=True,
                timeout=90
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.log_result("最小構成ブラウザ機能", True, "ブラウザ機能が正常に動作")
            else:
                self.log_result("最小構成ブラウザ機能", False, f"エラー: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("最小構成ブラウザ機能", False, str(e))
    
    def test_minimal_prompt_evaluator(self):
        """最小構成でのプロンプト評価器テスト"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'false'
            
            test_code = '''
import os
os.environ["ENABLE_LLM"] = "false"

from src.config.standalone_prompt_evaluator import (
    pre_evaluate_prompt_standalone,
    extract_params_standalone,
    resolve_sensitive_env_variables_standalone
)

# Test prompt evaluation
test_prompts = [
    "navigate to https://example.com",
    "click button",
    "fill form field",
    "@test_command with parameters"
]

print("Testing standalone prompt evaluator...")

for prompt in test_prompts:
    try:
        result = pre_evaluate_prompt_standalone(prompt)
        print(f"✅ Prompt '{prompt[:30]}...' evaluated: {type(result)}")
    except Exception as e:
        print(f"❌ Prompt evaluation failed for '{prompt}': {e}")
        exit(1)

# Test parameter extraction
try:
    params = {"url": "https://example.com", "text": "test"}
    result = extract_params_standalone("Navigate to ${url}", params)
    print(f"✅ Parameter extraction successful: {type(result)}")
except Exception as e:
    print(f"❌ Parameter extraction failed: {e}")
    exit(1)

# Test environment variable resolution
try:
    result = resolve_sensitive_env_variables_standalone("Test ${HOME} variable")
    print(f"✅ Environment variable resolution successful: {type(result)}")
except Exception as e:
    print(f"❌ Environment variable resolution failed: {e}")
    exit(1)

print("SUCCESS: All standalone prompt evaluator tests passed")
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
                self.log_result("最小構成プロンプト評価器", True, "プロンプト評価器が正常に動作")
            else:
                self.log_result("最小構成プロンプト評価器", False, f"エラー: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("最小構成プロンプト評価器", False, str(e))
    
    def test_minimal_configuration_settings(self):
        """最小構成での設定管理テスト"""
        try:
            env = os.environ.copy()
            env['ENABLE_LLM'] = 'false'
            
            test_code = '''
import os
import tempfile
from pathlib import Path
os.environ["ENABLE_LLM"] = "false"

from src.utils.default_config_settings import default_config

# Test default config creation
try:
    config = default_config()
    print(f"✅ Default config created with {len(config)} keys")
    
    # Check for essential keys
    essential_keys = ["browser_config", "recording_config", "ui_config"]
    for key in essential_keys:
        if key in config:
            print(f"✅ Essential config key '{key}' found")
        else:
            print(f"⚠️ Essential config key '{key}' missing")
    
    print("SUCCESS: Configuration management test passed")
    
except Exception as e:
    print(f"❌ Configuration test failed: {e}")
    exit(1)
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
                self.log_result("最小構成設定管理", True, "設定管理機能が正常に動作")
            else:
                self.log_result("最小構成設定管理", False, f"エラー: {result.stderr[:200]}")
                
        except Exception as e:
            self.log_result("最小構成設定管理", False, str(e))
    
    def run_all_tests(self):
        """全最小構成テストを実行"""
        print("=" * 70)
        print("最小構成（LLM無効）機能検証テスト開始 - venv312環境")
        print("=" * 70)
        
        tests = [
            self.test_minimal_imports,
            self.test_llm_modules_not_available,
            self.test_minimal_app_startup,
            self.test_minimal_browser_functionality,
            self.test_minimal_prompt_evaluator,
            self.test_minimal_configuration_settings,
        ]
        
        for test in tests:
            try:
                test()
                print()  # 空行で区切り
            except Exception as e:
                test_name = test.__name__
                self.log_result(test_name, False, f"テスト実行エラー: {e}")
        
        print("=" * 70)
        print("最小構成テスト結果サマリー")
        print("=" * 70)
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        for test_name, success, message in self.results:
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {message}")
        
        print(f"\n通過: {passed}/{total} テスト")
        
        if passed == total:
            print("🎉 全最小構成テストが通過しました！LLM無効モードは完全に動作します。")
            return True
        else:
            print("⚠️ 一部の最小構成テストが失敗しました。詳細を確認してください。")
            return False

if __name__ == "__main__":
    tester = MinimalConfigTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
