import os
import pytest
from pathlib import Path
from src.utils.app_logger import AppLogger


@pytest.mark.ci_safe
def test_app_logger_prefers_repo_root(monkeypatch, tmp_path):
    # Simulate running from repo root: ensure a pyproject.toml exists in repo root
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pyproject.toml").write_text("[tool.poetry]\n")

    # Place the app_logger module under src in that repo layout
    src_dir = repo_root / "src" / "utils"
    src_dir.mkdir(parents=True)

    # Change CWD to the fake repo so _find_repo_root scans it and finds pyproject.toml
    monkeypatch.chdir(repo_root)
    # Monkeypatch the file location used by AppLogger to simulate the package path
    monkeypatch.setenv("PYTHONPATH", str(repo_root))

    # Ensure fresh singleton so initialization runs with our CWD
    AppLogger._instance = None  # type: ignore[attr-defined]
    # Create AppLogger instance and check _log_dir uses repo_root/logs
    al = AppLogger()
    assert hasattr(al, "_log_dir")
    assert Path(al._log_dir).name == "logs"
    assert Path(al._log_dir).parent.resolve() == repo_root.resolve()


@pytest.mark.ci_safe
def test_app_logger_falls_back_to_package_dir(monkeypatch, tmp_path):
    # No repo markers; AppLogger should fall back to package's parent logs dir
    # Change CWD to tmp_path so no project markers are found in parents.
    monkeypatch.chdir(tmp_path)
    AppLogger._instance = None  # type: ignore[attr-defined]
    al = AppLogger()
    assert hasattr(al, "_log_dir")
    assert Path(al._log_dir).exists()
