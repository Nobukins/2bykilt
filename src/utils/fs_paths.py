from pathlib import Path
import os
from typing import Optional

MARKERS = ("pyproject.toml", ".git", "artifacts")


def find_repo_root(start: Optional[Path] = None) -> Optional[Path]:
    """Find repository root by scanning upwards from start (or cwd).

    Returns Path if a parent contains any of the MARKERS, else None.
    """
    try:
        cwd = (start or Path.cwd()).resolve()
        for p in (cwd, *cwd.parents):
            for m in MARKERS:
                if (p / m).exists():
                    return p
    except Exception:
        pass
    # fallback: search from this file's parent
    try:
        base = Path(__file__).resolve().parent
        for p in (base, *base.parents):
            for m in MARKERS:
                if (p / m).exists():
                    return p
    except Exception:
        pass
    return None


def get_logs_dir() -> Path:
    """Return logs directory. Priority:
    1. LOG_BASE_DIR env var
    2. <repo_root>/logs
    3. fallback to package-level ../logs
    """
    v = os.environ.get("LOG_BASE_DIR")
    if v:
        p = Path(v).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    repo = find_repo_root()
    if repo:
        p = repo / "logs"
        p.mkdir(parents=True, exist_ok=True)
        return p
    fallback = Path(__file__).resolve().parents[2] / "logs"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_artifacts_base_dir() -> Path:
    """Return artifacts base dir. Priority:
    1. ARTIFACTS_BASE_DIR env var
    2. <repo_root>/artifacts
    3. fallback to package-level ../artifacts
    """
    v = os.environ.get("ARTIFACTS_BASE_DIR")
    if v:
        p = Path(v).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    repo = find_repo_root()
    if repo:
        p = repo / "artifacts"
        p.mkdir(parents=True, exist_ok=True)
        return p
    fallback = Path(__file__).resolve().parents[2] / "artifacts"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_artifacts_run_dir(run_id: str) -> Path:
    base = get_artifacts_base_dir()
    run_dir = base / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
