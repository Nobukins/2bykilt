#!/usr/bin/env python3
"""Tests for llms.txt schema validator (Issue #63).

Focus areas:
  * Successful validation of existing repo llms.txt
  * Duplicate action name detection
  * Missing required keys per action type
  * Strict vs non-strict behavior (strict raises)
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from src.config.llms_schema_validator import (
    validate_llms_content,
    LLMSSchemaValidationError,
)


LLMS_PATH = Path("llms.txt").resolve()


class TestLLMSSchemaValidation(unittest.TestCase):
    def test_repo_llms_file_valid_non_strict(self):
        text = LLMS_PATH.read_text(encoding="utf-8")
        # Should not raise in non-strict mode
        data = validate_llms_content(text, strict=False)
        self.assertIn("actions", data)
        self.assertIsInstance(data["actions"], list)

    def test_duplicate_action_name_detection_strict(self):
        sample = """
actions:
  - name: a
    type: script
    command: echo 1
  - name: a
    type: script
    command: echo 2
"""
        with self.assertRaises(LLMSSchemaValidationError):
            validate_llms_content(sample, strict=True)

    def test_missing_required_git_fields(self):
        sample = """
actions:
  - name: fetch-data
    type: git-script
    script_path: run.py
"""
        # strict -> error (missing git field)
        with self.assertRaises(LLMSSchemaValidationError):
            validate_llms_content(sample, strict=True)

    def test_script_requires_command_or_script(self):
        sample = """
actions:
  - name: incomplete
    type: script
"""
        with self.assertRaises(LLMSSchemaValidationError):
            validate_llms_content(sample, strict=True)

    def test_strict_env_toggle(self):
        sample = """
actions:
  - name: ok
    type: script
    command: echo hi
"""
        # strict should pass
        validate_llms_content(sample, strict=True)
        # simulate env toggle usage for parser (not raising)
        os.environ["BYKILT_LLMS_STRICT"] = "1"
        try:
            validate_llms_content(sample, strict=os.getenv("BYKILT_LLMS_STRICT") == "1")
        finally:
            del os.environ["BYKILT_LLMS_STRICT"]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
