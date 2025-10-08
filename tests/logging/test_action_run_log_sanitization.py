import re
from pathlib import Path
from src.utils.app_logger import AppLogger


def _extract_slug(path: Path) -> str:
    """Extract sanitized slug from filename.

    Filename pattern: YYYYMMDD-HHMMSS-<slug>.log
    We remove the leading date-time components and isolate <slug>.
    """
    name = path.name
    stem = name[:-4] if name.endswith('.log') else name
    # Split into at most 3 parts: date, time, slug
    parts = stem.split('-', 2)
    if len(parts) == 3:
        return parts[2]
    return stem


def test_persist_action_run_log_sanitization(tmp_path, monkeypatch):
    # Force logger to use temp dir
    AppLogger._instance = None  # reset singleton
    al = AppLogger(log_dir=str(tmp_path / 'logs'))

    cases = [
        ("demo.artifact.capture", r"^demo_artifact_capture$"),
        (".hidden", r"^hidden$"),
        ("multi..dot..name", r"^multi_dot_name$"),
        ("name--with__chars", r"^name-with_chars$"),
        ("***", r"^unnamed$"),
        ("", r"^unnamed$"),
    ]

    for raw, pattern in cases:
        p = al.persist_action_run_log(raw, "output")
        slug = _extract_slug(p)
        assert re.match(pattern, slug), f"slug '{slug}' != pattern {pattern} (raw={raw})"
        # ensure no leading dot
        assert not slug.startswith('.'), f"slug should not start with dot: {slug}"
        # ensure only allowed chars
        assert re.match(r"^[A-Za-z0-9_-]+$", slug), f"invalid chars present: {slug}"

