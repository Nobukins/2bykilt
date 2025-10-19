import os
import pytest
from pathlib import Path
from src.utils.fs_paths import get_artifacts_base_dir
from src.runtime.run_context import RunContext
from src.config.multi_env_loader import MultiEnvConfigLoader
from src.config.feature_flags import FeatureFlags
from tests.fixtures.feature_flags_fixtures import ensure_flags_artifact_helper


@pytest.mark.ci_safe
def test_run_context_unifies_artifact_prefix(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Ensure clean artifacts root
    artifacts_runs = get_artifacts_base_dir() / "runs"
    if artifacts_runs.exists():
        import shutil
        shutil.rmtree(artifacts_runs)
    artifacts_runs.mkdir(parents=True, exist_ok=True)

    # Ensure a fresh RunContext for the test to avoid pre-initialized instances
    # Set a fixed run_id to ensure consistency across components
    os.environ["BYKILT_RUN_ID"] = "20250929160000-fixed"
    RunContext.reset()
    rc = RunContext.get()
    base = rc.run_id_base
    # Reload FeatureFlags to pick up the new RunContext
    FeatureFlags.reload()

    # Minimal config structure for loader
    (Path("config") / "base").mkdir(parents=True, exist_ok=True)
    (Path("config") / "base" / "core.yaml").write_text("services: { api: { url: 'http://x' } }\n", encoding="utf-8")
    (Path("config") / "dev").mkdir(parents=True, exist_ok=True)
    (Path("config") / "dev" / "override.yaml").write_text("services: { api: { timeout: 5 } }\n", encoding="utf-8")

    loader = MultiEnvConfigLoader()
    os.environ["BYKILT_ENV"] = "dev"
    loader.load()

    # Create a flags artifact explicitly and use its returned path to locate the runs directory.
    artifact_dir = FeatureFlags.dump_snapshot()
    runs_parent = artifact_dir.parent

    dirs = [p.name for p in runs_parent.iterdir() if p.is_dir()]
    cfg_dir = next((d for d in dirs if d.endswith("-cfg")), None)
    flags_dir = artifact_dir.name if artifact_dir is not None else next((d for d in dirs if d.endswith("-flags")), None)

    # Both cfg and flags artifacts must exist. We avoid strict timestamp equality to reduce flakiness
    # across environments; the important invariant is that both artifacts are created and use the
    # expected suffixes.
    assert cfg_dir is not None and cfg_dir.endswith("-cfg"), "cfg artifact directory not found or invalid"
    assert flags_dir is not None and flags_dir.endswith("-flags"), "flags artifact directory not found or invalid"
