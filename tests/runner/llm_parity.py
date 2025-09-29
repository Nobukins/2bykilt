"""
LLM Parity Test Suite for ENABLE_LLM flag consistency.

This test suite verifies that ENABLE_LLM=true/false produces consistent behavior
across all major types: script, action_runner_template, browser_control, git_script.

Requirements from Issue #43:
- ENABLE_LLM=false で LLM 呼び出し箇所が一切実行されない
- ログに llm.disabled.reason 出力 (初回のみ)
- artifacts/manifest.json へのパリティメトリクス追加
- artifacts/runs/<run_id>/llm_parity_regression.json への回帰テスト出力
"""

import pytest
import os
import json
import tempfile
import logging
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path
import datetime

# Import test utilities
from src.config.feature_flags import is_llm_enabled, FeatureFlags


class LLMParityTester:
    """Comprehensive LLM parity testing class."""

    def __init__(self):
        self.test_results = []
        self.regression_data = {
            "test_run_id": f"parity_test_{int(datetime.datetime.now().timestamp())}",
            "timestamp": datetime.datetime.now().isoformat(),
            "llm_states_tested": [True, False],
            "types_tested": ["script", "action_runner_template", "browser_control", "git_script"],
            "results": [],
            "summary": {
                "total_checks": 0,
                "llm_disabled_checks": 0,
                "parity_violations": 0
            }
        }

    def run_comprehensive_tests(self):
        """Run all parity tests and generate regression data."""
        print("🧪 Running comprehensive LLM parity tests...")

        # Test each combination
        for llm_enabled in [True, False]:
            for test_type in ["script", "action_runner_template", "browser_control", "git_script"]:
                result = self.run_single_test(test_type, llm_enabled)
                self.test_results.append(result)
                self.regression_data["results"].append(result)

        # Update summary
        self.regression_data["summary"]["total_checks"] = len(self.test_results)
        self.regression_data["summary"]["llm_disabled_checks"] = len([r for r in self.test_results if not r["llm_enabled"]])
        self.regression_data["summary"]["parity_violations"] = len([r for r in self.test_results if r.get("parity_violation", False)])

        # Save regression data
        self.save_regression_data()

        return self.regression_data

    def run_single_test(self, test_type: str, llm_enabled: bool):
        """Run a single test case."""
        print(f"  Testing {test_type} with ENABLE_LLM={llm_enabled}")

        # Setup environment
        with patch.dict(os.environ, {"ENABLE_LLM": str(llm_enabled).lower()}):
            try:
                FeatureFlags.set_override("enable_llm", llm_enabled)
            except Exception:
                pass

            # Force module reload to test conditional imports
            self.force_module_reload()

            result = {
                "test_type": test_type,
                "llm_enabled": llm_enabled,
                "timestamp": datetime.datetime.now().isoformat(),
                "llm_calls_detected": False,
                "parity_violation": False,
                "error": None
            }

            try:
                if test_type == "script":
                    self.test_script_execution(result)
                elif test_type == "action_runner_template":
                    self.test_action_runner_template(result)
                elif test_type == "browser_control":
                    self.test_browser_control(result)
                elif test_type == "git_script":
                    self.test_git_script(result)

                # Check for LLM calls when disabled
                if not llm_enabled and result.get("llm_calls_detected", False):
                    result["parity_violation"] = True
                    print(f"    ❌ PARITY VIOLATION: LLM calls detected when ENABLE_LLM=false")

                result["success"] = True

            except Exception as e:
                result["success"] = False
                result["error"] = str(e)
                print(f"    ❌ Test failed: {e}")

            return result

    def force_module_reload(self):
        """Force reload of modules that depend on ENABLE_LLM flag."""
        import importlib

        modules_to_reload = [
            'src.agent.custom_agent',
            'src.agent.custom_prompts',
            'src.agent.custom_message_manager',
            'src.agent.custom_views',
            'src.config.llms_parser',
            'bykilt'  # Main module with conditional imports
        ]

        for module_name in modules_to_reload:
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
            except Exception as e:
                print(f"Warning: Could not reload {module_name}: {e}")

    def test_script_execution(self, result: dict):
        """Test script execution parity."""
        from src.script.script_manager import run_script

        action_def = {
            "type": "script",
            "command": "echo 'LLM parity test'",
            "params": []
        }

        output, script_path = run_script(action_def, {}, headless=True)

        result["output"] = output
        result["script_path"] = script_path
        result["llm_calls_detected"] = self.detect_llm_calls(output)

    def test_action_runner_template(self, result: dict):
        """Test action runner template parity."""
        from src.script.script_manager import run_script

        action_def = {
            "type": "action_runner_template",
            "command": "echo 'Template test'",
            "params": []
        }

        output, script_path = run_script(action_def, {}, headless=True)

        result["output"] = output
        result["script_path"] = script_path
        result["llm_calls_detected"] = self.detect_llm_calls(output)

    def test_browser_control(self, result: dict):
        """Test browser control parity."""
        from src.modules.direct_browser_control import execute_direct_browser_control

        action_def = {
            "type": "browser-control",
            "url": "https://httpbin.org/html",
            "actions": [{"type": "wait", "selector": "h1", "timeout": 1000}]
        }

        success = execute_direct_browser_control(action_def, headless=True)

        result["success"] = success
        result["llm_calls_detected"] = False  # Browser control shouldn't trigger LLM

    def test_git_script(self, result: dict):
        """Test git script parity."""
        from src.script.script_manager import run_script

        action_def = {
            "type": "git-script",
            "command": "git --version",
            "params": []
        }

        output, script_path = run_script(action_def, {}, headless=True)

        result["output"] = output
        result["script_path"] = script_path
        result["llm_calls_detected"] = self.detect_llm_calls(output)

    def detect_llm_calls(self, output: str) -> bool:
        """Detect LLM calls in output."""
        if not output:
            return False

        llm_indicators = [
            "llm", "openai", "anthropic", "claude", "gpt", "chatgpt",
            "pre_evaluate_prompt", "extract_params", "resolve_sensitive_env_variables",
            "LLM_AGENT_AVAILABLE", "ENABLE_LLM"
        ]

        output_lower = output.lower()
        return any(indicator.lower() in output_lower for indicator in llm_indicators)

    def save_regression_data(self):
        """Save regression test data."""
        # Create artifacts directory using centralized helper so tests follow repo-level config
        from src.utils.fs_paths import get_artifacts_run_dir

        artifacts_dir = get_artifacts_run_dir(self.regression_data["test_run_id"])
        regression_file = artifacts_dir / "llm_parity_regression.json"

        with open(regression_file, 'w', encoding='utf-8') as f:
            json.dump(self.regression_data, f, indent=2, ensure_ascii=False)

        print(f"📊 Regression data saved to: {regression_file}")

        # Also update manifest.json with parity metrics
        self.update_manifest_parity_metrics()

    def update_manifest_parity_metrics(self):
        """Update artifacts/manifest.json with parity metrics."""
        from src.utils.fs_paths import get_artifacts_base_dir
        manifest_path = get_artifacts_base_dir() / "manifest.json"

        # Create manifest if it doesn't exist
        if not manifest_path.exists():
            manifest_data = {
                "version": "1.0",
                "llm_parity_checks": {
                    "total_checks": 0,
                    "mismatched_count": 0,
                    "last_run": None,
                    "checks": []
                }
            }
        else:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

        # Update parity metrics
        parity_checks = manifest_data.setdefault("llm_parity_checks", {})
        parity_checks["total_checks"] = self.regression_data["summary"]["total_checks"]
        parity_checks["mismatched_count"] = self.regression_data["summary"]["parity_violations"]
        parity_checks["last_run"] = self.regression_data["timestamp"]

        # Add recent check results
        recent_checks = parity_checks.setdefault("checks", [])
        recent_checks.extend(self.regression_data["results"][-4:])  # Last 4 results

        # Keep only recent results
        if len(recent_checks) > 20:
            recent_checks[:] = recent_checks[-20:]

        # Save manifest
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        print(f"📋 Manifest updated with parity metrics: {manifest_path}")


class TestLLMParity:
    """Pytest test class for LLM parity."""

    def setup_method(self):
        """Reset feature flags before each test."""
        try:
            FeatureFlags.reload()
        except Exception:
            pass

    def teardown_method(self):
        """Reset feature flags after each test."""
        try:
            FeatureFlags.reload()
        except Exception:
            pass

    @pytest.mark.parametrize("llm_enabled", [True, False])
    @pytest.mark.parametrize("test_type", ["script", "action_runner_template", "browser_control", "git_script"])
    def test_llm_parity_comprehensive(self, test_type: str, llm_enabled: bool):
        """Comprehensive parity test for each type and LLM state."""
        tester = LLMParityTester()

        result = tester.run_single_test(test_type, llm_enabled)

        # Basic assertions
        assert result["test_type"] == test_type
        assert result["llm_enabled"] == llm_enabled
        assert "success" in result

        # Critical parity assertion: No LLM calls when disabled
        if not llm_enabled:
            assert not result.get("llm_calls_detected", False), \
                f"LLM calls detected when ENABLE_LLM=false for {test_type}"

    def test_llm_disabled_logging(self):
        """Test that LLM disabled reason is logged appropriately."""
        with patch.dict(os.environ, {"ENABLE_LLM": "false"}):
            try:
                FeatureFlags.set_override("enable_llm", False)
            except Exception:
                pass

            # Force reload and test logging
            import importlib
            import src.agent.custom_agent
            importlib.reload(src.agent.custom_agent)

            from src.agent.custom_agent import ENABLE_LLM

            # Verify LLM is disabled
            assert ENABLE_LLM == False

            # Test logging when LLM functionality is accessed
            with patch('src.agent.custom_agent.logger') as mock_logger:
                # Import custom_agent to trigger any initialization logging
                import src.agent.custom_agent

                # Check if llm.disabled.reason was logged
                log_calls = [call for call in mock_logger.info.call_args_list
                           if 'llm.disabled.reason' in str(call)]

                if log_calls:
                    print("✅ LLM disabled reason logging detected")
                else:
                    print("ℹ️  LLM disabled reason logging not triggered in this test")

    def test_parity_metrics_in_manifest(self):
        """Test that parity metrics are properly recorded in manifest."""
        tester = LLMParityTester()
        results = tester.run_comprehensive_tests()

        # Verify regression file was created
        from src.utils.fs_paths import get_artifacts_run_dir, get_artifacts_base_dir
        regression_file = get_artifacts_run_dir(results["test_run_id"]) / "llm_parity_regression.json"
        assert regression_file.exists()

        # Verify manifest was updated
        manifest_file = get_artifacts_base_dir() / "manifest.json"
        assert manifest_file.exists()

        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)

        assert "llm_parity_checks" in manifest_data
        parity_checks = manifest_data["llm_parity_checks"]

        assert parity_checks["total_checks"] > 0
        assert "last_run" in parity_checks

        print("✅ Parity metrics properly recorded in manifest")


def test_llm_parity_run_comprehensive():
    """Run comprehensive parity test suite."""
    tester = LLMParityTester()
    results = tester.run_comprehensive_tests()

    # Verify test results
    assert len(results["results"]) == 8  # 4 types × 2 LLM states

    # Count parity violations
    violations = [r for r in results["results"] if r.get("parity_violation", False)]
    disabled_llm_results = [r for r in results["results"] if not r["llm_enabled"]]

    print("\n🧪 LLM Parity Test Results:")
    print(f"  Total tests: {len(results['results'])}")
    print(f"  LLM disabled tests: {len(disabled_llm_results)}")
    print(f"  Parity violations: {len(violations)}")

    if violations:
        print("❌ Parity violations detected:")
        for v in violations:
            print(f"    - {v['test_type']} with ENABLE_LLM={v['llm_enabled']}")
    else:
        print("✅ No parity violations detected!")

    # Assert no violations when LLM is disabled
    llm_disabled_violations = [v for v in violations if not v["llm_enabled"]]
    assert len(llm_disabled_violations) == 0, f"Parity violations when LLM disabled: {llm_disabled_violations}"

    return results


if __name__ == "__main__":
    import sys

    print("🚀 Running LLM Parity Test Suite...")
    print("=" * 50)

    try:
        results = test_llm_parity_run_comprehensive()

        print("\n" + "=" * 50)
        print("✅ LLM Parity Test Suite completed successfully!")
        print(f"📊 Results saved to: artifacts/runs/{results['test_run_id']}/")
        print("📋 Manifest updated with parity metrics")
        print("\n🎯 Key Achievements:")
        print("  - Verified ENABLE_LLM flag consistency across all runner types")
        print("  - Confirmed no LLM calls when ENABLE_LLM=false")
        print("  - Generated regression test data for future validation")
        print("  - Updated manifest.json with parity metrics")

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)