from pathlib import Path

from src.config.feature_flags import FeatureFlags


def test_flags_dump_snapshot_creates_artifact(tmp_path, monkeypatch):
    # Force artifacts to tmp dir by changing CWD (RunContext uses relative paths)
    monkeypatch.chdir(tmp_path)

    # Ensure clean
    FeatureFlags.clear_all_overrides()
    FeatureFlags.reload()

    out_dir = FeatureFlags.dump_snapshot()
    assert isinstance(out_dir, Path)
    # Should write under artifacts/runs/<run>/flags/
    assert (out_dir / "feature_flags_resolved.json").exists()
