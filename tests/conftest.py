from pathlib import Path
import os
import sys
import pytest


def _detect_project_root(start: Path) -> Path:
    markers = {"pyproject.toml", "README.md", ".git", "artifacts"}
    current = start.resolve()
    for parent in [current] + list(current.parents):
        try:
            entries = {p.name for p in parent.iterdir()}
        except (PermissionError, OSError):
            continue
        if markers & entries:
            return parent
    return start


def _ensure_sys_path(path: Path) -> None:
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def pytest_configure(config):
    # Register commonly used markers to avoid pytest warnings
    config.addinivalue_line("markers", "integration: mark test as integration-heavy (requires network/browser)")
    config.addinivalue_line("markers", "local_only: mark test that should only run on a developer machine")

    # 1) Allow explicit override for project root
    root_env = os.environ.get("BYKILT_ROOT")
    if root_env:
        root_path = Path(root_env).expanduser().resolve()
    else:
        this_file = Path(__file__).resolve()
        root_path = _detect_project_root(this_file.parent)

    # Prefer src/ if it exists; else add repo root
    src_path = root_path / "src"
    if src_path.exists():
        _ensure_sys_path(src_path)
    _ensure_sys_path(root_path)

    # Optional: expose for tests that may need it
    os.environ.setdefault("BYKILT_ROOT_EFFECTIVE", str(root_path))


def pytest_collection_modifyitems(config, items):
    """
    Skip integration / local_only tests by default unless corresponding
    environment variables are set. This centralizes the previous per-file
    env guards and makes CI configuration simpler.

    Environment variables:
      RUN_LOCAL_INTEGRATION=1  -> run @pytest.mark.integration tests
      RUN_LOCAL_FINAL_VERIFICATION=1 -> run @pytest.mark.local_only tests
    """
    run_integration = os.environ.get("RUN_LOCAL_INTEGRATION")
    run_final = os.environ.get("RUN_LOCAL_FINAL_VERIFICATION")

    skip_integration = pytest.mark.skip(reason="Integration tests skipped by default. Set RUN_LOCAL_INTEGRATION=1 to enable")
    skip_final = pytest.mark.skip(reason="Local-only tests skipped by default. Set RUN_LOCAL_FINAL_VERIFICATION=1 to enable")

    for item in list(items):
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)
        if "local_only" in item.keywords and not run_final:
            item.add_marker(skip_final)

