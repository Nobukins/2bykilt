"""Tests for unified recording dir resolver (Issue #28 incremental refactor)."""
from pathlib import Path
import pytest
from src.utils.recording_dir_resolver import create_or_get_recording_dir
from src.config.feature_flags import FeatureFlags, _reset_feature_flags_for_tests
from src.runtime.run_context import RunContext


def _reset(monkeypatch, run_id: str):
    monkeypatch.setenv("BYKILT_RUN_ID", run_id)
    # Ensure any external or previously set recording path env is cleared so tests
    # that expect "no env" state are deterministic even if developer shell or other
    # tests provided one. (Full-suite flake fix)
    monkeypatch.delenv("RECORDING_PATH", raising=False)
    RunContext.reset()
    _reset_feature_flags_for_tests()
    FeatureFlags.clear_all_overrides()


@pytest.mark.ci_safe
def test_explicit_precedence(tmp_path, monkeypatch):
    _reset(monkeypatch, "R1")
    FeatureFlags.set_override("artifacts.unified_recording_path", True)
    target = tmp_path / "explicit_dir"
    p = create_or_get_recording_dir(str(target))
    assert p == target
    assert p.exists()


@pytest.mark.ci_safe
def test_env_precedence_over_flag(tmp_path, monkeypatch):
    _reset(monkeypatch, "R2")
    FeatureFlags.set_override("artifacts.unified_recording_path", True)
    env_dir = tmp_path / "env_dir"
    monkeypatch.setenv("RECORDING_PATH", str(env_dir))
    p = create_or_get_recording_dir()
    assert p == env_dir
    assert p.exists()


@pytest.mark.ci_safe
def test_flag_path_when_no_env(monkeypatch):
    _reset(monkeypatch, "R3")
    FeatureFlags.set_override("artifacts.unified_recording_path", True)
    p = create_or_get_recording_dir()
    # Should be artifacts/runs/<run>-art/videos
    assert p.name == "videos"
    assert "artifacts" in str(p)


@pytest.mark.ci_safe
def test_legacy_when_flag_disabled(monkeypatch):
    _reset(monkeypatch, "R4")
    FeatureFlags.set_override("artifacts.unified_recording_path", False)
    p = create_or_get_recording_dir()
    assert p.name == "record_videos"  # resolved absolute path
    assert "tmp" in str(p)


@pytest.mark.ci_safe
def test_empty_env_ignored(monkeypatch):
    _reset(monkeypatch, "R5")
    monkeypatch.setenv("RECORDING_PATH", " ")  # whitespace ignored
    FeatureFlags.set_override("artifacts.unified_recording_path", True)
    p = create_or_get_recording_dir()
    assert p.name == "videos"


@pytest.mark.ci_safe
def test_force_migration_overrides_legacy(monkeypatch):
    _reset(monkeypatch, "R6")
    FeatureFlags.set_override("artifacts.unified_recording_path", False)
    FeatureFlags.set_override("artifacts.force_recording_migration", True)
    p = create_or_get_recording_dir()
    assert p.name == "videos"
