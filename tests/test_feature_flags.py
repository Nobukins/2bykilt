#!/usr/bin/env python3
"""Tests for Feature Flag Framework (Issue #64).

Focus: resolution precedence, type coercion, runtime overrides, TTL expiry,
and undefined flag behavior.
"""
import os
import pytest
import time
import unittest
from pathlib import Path

from src.config.feature_flags import FeatureFlags


@pytest.mark.local_only
class TestFeatureFlags(unittest.TestCase):
    def setUp(self):  # noqa: D401
        # Ensure clean state each test
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()

    def test_file_default_resolution(self):
        self.assertIsInstance(FeatureFlags.is_enabled("engine.cdp_use"), bool)
        self.assertTrue(FeatureFlags.is_enabled("engine.cdp_use"))  # default true

    def test_env_override_precedence_over_file(self):
        os.environ["BYKILT_FLAG_ENGINE_CDP_USE"] = "false"
        try:
            FeatureFlags.reload()  # reload not strictly necessary for env
            self.assertFalse(FeatureFlags.is_enabled("engine.cdp_use"))
        finally:
            del os.environ["BYKILT_FLAG_ENGINE_CDP_USE"]

    def test_runtime_override_highest_precedence(self):
        os.environ["BYKILT_FLAG_ENGINE_CDP_USE"] = "false"
        try:
            FeatureFlags.set_override("engine.cdp_use", True)
            self.assertTrue(FeatureFlags.is_enabled("engine.cdp_use"))  # runtime wins
        finally:
            del os.environ["BYKILT_FLAG_ENGINE_CDP_USE"]

    def test_undefined_flag_defaults(self):
        # Expect False for bool when undefined
        self.assertFalse(FeatureFlags.is_enabled("nonexistent.flag"))
        # Provide explicit default for int
        self.assertEqual(FeatureFlags.get("another.missing", expected_type=int, default=5), 5)

    def test_ttl_override_expires(self):
        FeatureFlags.set_override("ui.experimental_panel", True, ttl_seconds=1)
        self.assertTrue(FeatureFlags.is_enabled("ui.experimental_panel"))
        time.sleep(1.2)
        # Next access should prune expiration and fallback to file default (False)
        self.assertFalse(FeatureFlags.is_enabled("ui.experimental_panel"))

    def test_type_coercion(self):
        os.environ["ENGINE_CDP_USE"] = "true"  # alternate env naming
        try:
            self.assertTrue(FeatureFlags.get("engine.cdp_use", expected_type=bool))
        finally:
            del os.environ["ENGINE_CDP_USE"]

    def test_get_override_source(self):
        # Test no override (file default)
        self.assertIsNone(FeatureFlags.get_override_source("engine.cdp_use"))

        # Test environment override
        os.environ["BYKILT_FLAG_ENGINE_CDP_USE"] = "false"
        try:
            FeatureFlags.reload()
            self.assertEqual(FeatureFlags.get_override_source("engine.cdp_use"), "environment")
        finally:
            del os.environ["BYKILT_FLAG_ENGINE_CDP_USE"]
            FeatureFlags.reload()

        # Test runtime override takes precedence
        FeatureFlags.set_override("engine.cdp_use", True)
        self.assertEqual(FeatureFlags.get_override_source("engine.cdp_use"), "runtime")

        # Test undefined flag
        self.assertIsNone(FeatureFlags.get_override_source("nonexistent.flag"))

    def test_get_override_source_env_parsing(self):
        """Test environment variable parsing in get_override_source."""
        # Test boolean parsing
        os.environ["BYKILT_FLAG_TEST_BOOL"] = "true"
        try:
            FeatureFlags.reload()
            self.assertEqual(FeatureFlags.get_override_source("test_bool"), "environment")
        finally:
            del os.environ["BYKILT_FLAG_TEST_BOOL"]
            FeatureFlags.reload()

        # Test integer parsing
        os.environ["BYKILT_FLAG_TEST_INT"] = "42"
        try:
            FeatureFlags.reload()
            self.assertEqual(FeatureFlags.get_override_source("test_int"), "environment")
        finally:
            del os.environ["BYKILT_FLAG_TEST_INT"]
            FeatureFlags.reload()

        # Test string parsing
        os.environ["BYKILT_FLAG_TEST_STR"] = "custom_value"
        try:
            FeatureFlags.reload()
            self.assertEqual(FeatureFlags.get_override_source("test_str"), "environment")
        finally:
            del os.environ["BYKILT_FLAG_TEST_STR"]
            FeatureFlags.reload()

    def test_coerce_method_coverage(self):
        """Test _coerce method edge cases for better coverage."""
        # Test boolean coercion from string
        self.assertTrue(FeatureFlags._coerce("true", bool, "test"))
        self.assertTrue(FeatureFlags._coerce("1", bool, "test"))
        self.assertTrue(FeatureFlags._coerce("yes", bool, "test"))
        self.assertTrue(FeatureFlags._coerce("on", bool, "test"))
        self.assertFalse(FeatureFlags._coerce("false", bool, "test"))
        self.assertFalse(FeatureFlags._coerce("0", bool, "test"))
        self.assertFalse(FeatureFlags._coerce("no", bool, "test"))
        self.assertFalse(FeatureFlags._coerce("off", bool, "test"))

        # Test integer coercion
        self.assertEqual(FeatureFlags._coerce("42", int, "test"), 42)
        self.assertEqual(FeatureFlags._coerce(42, int, "test"), 42)

        # Test string coercion
        self.assertEqual(FeatureFlags._coerce(123, str, "test"), "123")
        self.assertEqual(FeatureFlags._coerce("test", str, "test"), "test")

        # Test None type (no coercion)
        self.assertEqual(FeatureFlags._coerce("value", None, "test"), "value")

    def test_prune_expired_overrides(self):
        """Test _prune_expired method coverage."""
        from datetime import datetime, timezone, timedelta

        # Set an expired override
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        FeatureFlags._overrides["test.expired"] = ("value", expired_time)

        # Call prune (should remove expired override)
        FeatureFlags._prune_expired()

        # Verify expired override was removed
        self.assertNotIn("test.expired", FeatureFlags._overrides)

    def test_is_llm_enabled_function(self):
        """Test is_llm_enabled backward compatibility function."""
        from src.config.feature_flags import is_llm_enabled

        # Test with feature flag
        original_value = FeatureFlags.is_enabled("enable_llm")
        try:
            FeatureFlags.set_override("enable_llm", True)
            self.assertTrue(is_llm_enabled())

            FeatureFlags.set_override("enable_llm", False)
            self.assertFalse(is_llm_enabled())
        finally:
            # Reset to original state
            if original_value:
                FeatureFlags.set_override("enable_llm", True)
            else:
                FeatureFlags.clear_override("enable_llm")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
