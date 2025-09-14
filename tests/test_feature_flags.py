#!/usr/bin/env python3
"""Tests for Feature Flag Framework (Issue #64).

Focus: resolution precedence, type coercion, runtime overrides, TTL expiry,
and undefined flag behavior.
"""
import os
import time
import unittest
from pathlib import Path

from src.config.feature_flags import FeatureFlags


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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
