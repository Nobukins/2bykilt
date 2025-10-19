"""Tests for component name validation logic in JsonlLogger.get().

These tests intentionally target the design-phase validation introduced to avoid
silent normalization risks noted in PR #80 review.
"""
from __future__ import annotations

import pytest

from src.logging.jsonl_logger import JsonlLogger, _design_phase_ping


@pytest.mark.ci_safe
def test_design_phase_ping():
    assert _design_phase_ping() is True


@pytest.mark.ci_safe
def test_component_valid():
    logger = JsonlLogger.get("worker_1")
    assert logger is not None


@pytest.mark.parametrize("bad", [
    "", "  ", "Worker", "bad-name", "name.with.dot", "upperCASE", "dash-", " space", "x/y", "*", "MiXeD",
])
@pytest.mark.ci_safe
def test_component_invalid(bad: str):
    with pytest.raises(ValueError):
        JsonlLogger.get(bad)
