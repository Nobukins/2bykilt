from __future__ import annotations

import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.recordings.recordings_scanner import DEFAULT_EXTENSIONS, scan_recordings
from src.config.feature_flags import FeatureFlags

_FLAG = "artifacts.recursive_recordings_enabled"


@pytest.fixture(autouse=True)
def _reset_flag_state() -> Iterator[None]:
    FeatureFlags.reload()
    FeatureFlags.clear_override(_FLAG)
    yield
    FeatureFlags.clear_override(_FLAG)


def _touch(path: Path, *, mtime: float) -> None:
    path.write_bytes(b"binary")
    os.utime(path, (mtime, mtime))


def test_missing_root_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "runs" / "missing"
    result = list(scan_recordings(missing))
    assert result == []


def test_flag_disabled_scans_only_flat_directory(tmp_path: Path) -> None:
    # Explicitly disable recursive scanning for this test
    FeatureFlags.set_override(_FLAG, False)
    
    root = tmp_path / "runs"
    nested = root / "nested"
    nested.mkdir(parents=True)
    top_file = root / "root.webm"
    nested_file = nested / "nested.webm"
    _touch(top_file, mtime=time.time())
    _touch(nested_file, mtime=time.time())

    result = list(scan_recordings(root))

    assert [item.path for item in result] == [top_file]


def test_flag_enabled_returns_newest_first(tmp_path: Path) -> None:
    FeatureFlags.set_override(_FLAG, True)

    root = tmp_path / "runs"
    nested = root / "nested"
    nested.mkdir(parents=True)

    old_file = root / "older.mp4"
    new_file = nested / "newer.webm"
    now = time.time()
    _touch(old_file, mtime=now - 10)
    _touch(new_file, mtime=now)

    result = list(scan_recordings(root))

    assert [item.path for item in result] == [new_file, old_file]


def test_limit_and_offset_window(tmp_path: Path) -> None:
    FeatureFlags.set_override(_FLAG, True)

    root = tmp_path / "runs"
    root.mkdir(parents=True)

    files = []
    base = time.time()
    for index in range(6):
        current = root / f"file_{index}.webm"
        _touch(current, mtime=base + index)
        files.append(current)

    # Expect newest first, skip top item, take next two
    result = list(scan_recordings(root, limit=2, offset=1))

    expected = [files[-2], files[-3]]
    assert [item.path for item in result] == expected


def test_allowed_roots_guard(tmp_path: Path) -> None:
    FeatureFlags.set_override(_FLAG, True)

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    root = tmp_path / "runs"
    root.mkdir()

    with pytest.raises(ValueError):
        list(scan_recordings(root, allowed_roots=[allowed]))


def test_invalid_pagination_parameters(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()

    with pytest.raises(ValueError):
        list(scan_recordings(root, limit=-1))
    with pytest.raises(ValueError):
        list(scan_recordings(root, offset=-5))


def test_extension_filtering_case_insensitive(tmp_path: Path) -> None:
    FeatureFlags.set_override(_FLAG, True)

    root = tmp_path / "runs"
    root.mkdir()

    good = root / "match.WEBM"
    ignored = root / "skip.txt"
    _touch(good, mtime=time.time())
    _touch(ignored, mtime=time.time())

    result = list(scan_recordings(root))

    assert [item.path for item in result] == [good]
    assert {f.lower() for f in DEFAULT_EXTENSIONS} >= {".webm", ".mp4", ".ogg"}


def test_zero_limit_returns_no_items(tmp_path: Path) -> None:
    FeatureFlags.set_override(_FLAG, True)

    root = tmp_path / "runs"
    root.mkdir()
    sample = root / "sample.webm"
    _touch(sample, mtime=time.time())

    result = list(scan_recordings(root, limit=0))

    assert result == []


def test_root_must_be_directory(tmp_path: Path) -> None:
    file_root = tmp_path / "runs.log"
    file_root.write_text("noop", encoding="utf-8")

    with pytest.raises(ValueError):
        list(scan_recordings(file_root))


def test_custom_extension_normalisation(tmp_path: Path) -> None:
    FeatureFlags.set_override(_FLAG, True)

    root = tmp_path / "runs"
    root.mkdir()
    sample = root / "sample.custom"
    _touch(sample, mtime=time.time())

    result = list(scan_recordings(root, allow_extensions=["CUSTOM", "mp4"]))

    assert [item.path for item in result] == [sample]
