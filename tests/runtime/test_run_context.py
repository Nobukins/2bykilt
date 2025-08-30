import os
from pathlib import Path
from src.runtime.run_context import RunContext
from src.config.multi_env_loader import MultiEnvConfigLoader
from src.config.feature_flags import FeatureFlags


def test_run_context_unifies_artifact_prefix(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Ensure clean artifacts root
    (Path("artifacts") / "runs").mkdir(parents=True, exist_ok=True)

    rc = RunContext.get()
    base = rc.run_id_base

    # Trigger config artifact
    loader = MultiEnvConfigLoader()
    os.environ["BYKILT_ENV"] = "dev"
    loader.load()

    # Trigger flags artifact
    FeatureFlags.is_enabled("nonexistent.flag.for.test")  # will write artifact

    dirs = [p.name for p in (Path("artifacts") / "runs").iterdir() if p.is_dir()]
    cfg_dir = next(d for d in dirs if d.endswith("-cfg"))
    flags_dir = next(d for d in dirs if d.endswith("-flags"))

    assert cfg_dir.startswith(base), f"cfg dir {cfg_dir} not using run_id_base {base}"
    assert flags_dir.startswith(base), f"flags dir {flags_dir} not using run_id_base {base}"
