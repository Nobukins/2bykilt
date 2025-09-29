import os
from pathlib import Path
from src.utils.fs_paths import get_artifacts_base_dir
from src.runtime.run_context import RunContext
from src.config.multi_env_loader import MultiEnvConfigLoader
from src.config.feature_flags import FeatureFlags
from tests.fixtures.feature_flags_fixtures import ensure_flags_artifact_helper


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

    # Use helper to ensure flags artifact exists (more reliable than direct access)
    ensure_flags_artifact_helper(tmp_path)

    dirs = [p.name for p in (get_artifacts_base_dir() / "runs").iterdir() if p.is_dir()]
    cfg_dir = next(d for d in dirs if d.endswith("-cfg"))
    flags_dir = next(d for d in dirs if d.endswith("-flags"))

    # Ensure both artifacts use the same timestamp prefix (YYYYMMDDHHMMSS)
    assert cfg_dir[:14] == base[:14], f"cfg dir {cfg_dir} timestamp not matching base {base}"
    assert flags_dir[:14] == base[:14], f"flags dir {flags_dir} timestamp not matching base {base}"
