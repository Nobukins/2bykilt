from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Iterator

import pytest

from src.config.feature_flags import FeatureFlags
from src.services import recordings_service
from src.services import ListParams, list_recordings

_FLAG = "artifacts.recursive_recordings_enabled"


@pytest.fixture(autouse=True)
def _reset_flag_state() -> Iterator[None]:
    FeatureFlags.reload()
    FeatureFlags.clear_override(_FLAG)
    yield
    FeatureFlags.clear_override(_FLAG)


def _touch(path: Path, *, mtime: float) -> None:
    path.write_bytes(b"data")
    os.utime(path, (mtime, mtime))


def test_missing_root_raises_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "runs" / "missing"
    params = ListParams(root=missing)
    with pytest.raises(FileNotFoundError):
        list_recordings(params)


def test_limit_upper_bound_validation(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()
    params = ListParams(root=root, limit=recordings_service._MAX_LIMIT + 1)
    with pytest.raises(ValueError):
        list_recordings(params)


def test_flag_disabled_uses_flat_listing(tmp_path: Path) -> None:
    # Explicitly disable recursive scanning for this test
    FeatureFlags.set_override(_FLAG, False)
    
    root = tmp_path / "runs"
    nested = root / "nested"
    nested.mkdir(parents=True)

    top_file = root / "top.webm"
    nested_file = nested / "nested.webm"
    now = time.time()
    _touch(top_file, mtime=now)
    _touch(nested_file, mtime=now + 5)

    page = list_recordings(ListParams(root=root, limit=10))

    assert [Path(item.path) for item in page.items] == [top_file]
    assert not page.has_next


def test_flag_enabled_lists_recursive(tmp_path: Path) -> None:
    FeatureFlags.set_override(_FLAG, True)

    root = tmp_path / "runs"
    nested = root / "nested"
    nested.mkdir(parents=True)

    older = root / "older.mp4"
    newer = nested / "newer.webm"
    now = time.time()
    _touch(older, mtime=now)
    _touch(newer, mtime=now + 30)

    page = list_recordings(ListParams(root=root, limit=10))

    assert [Path(item.path) for item in page.items] == [newer, older]
    assert not page.has_next


def test_pagination_reports_more_items(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()

    base = time.time()
    files = []
    for index in range(5):
        current = root / f"file_{index}.webm"
        _touch(current, mtime=base + index)
        files.append(current)

    page = list_recordings(ListParams(root=root, limit=2, offset=0))

    assert [Path(item.path) for item in page.items] == files[-1:-3:-1]
    assert page.has_next


def test_zero_limit_returns_no_items_but_indicates_more(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()

    sample = root / "sample.webm"
    _touch(sample, mtime=time.time())

    page = list_recordings(ListParams(root=root, limit=0))

    assert page.items == []
    assert page.has_next


def test_extension_filtering(tmp_path: Path) -> None:
    FeatureFlags.set_override(_FLAG, True)

    root = tmp_path / "runs"
    root.mkdir()

    keep = root / "keep.CUSTOM"
    drop = root / "drop.mp4"
    now = time.time()
    _touch(keep, mtime=now + 1)
    _touch(drop, mtime=now)

    page = list_recordings(ListParams(root=root, allow_extensions=("custom",)))

    assert [Path(item.path) for item in page.items] == [keep]


def test_allowed_roots_validation(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()
    other = tmp_path / "other"
    other.mkdir()

    params = ListParams(root=root, allowed_roots=(other,))

    with pytest.raises(ValueError):
        list_recordings(params)


def test_permission_error_bubbles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Disable recursive scanning so that _scan_flat is used
    FeatureFlags.set_override(_FLAG, False)
    
    root = tmp_path / "runs"
    root.mkdir()

    def _raise(*_args, **_kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(recordings_service, "_scan_flat", _raise)

    with pytest.raises(PermissionError):
        list_recordings(ListParams(root=root, limit=1))


def test_run_id_inference(tmp_path: Path) -> None:
    FeatureFlags.set_override(_FLAG, True)

    base = tmp_path / "artifacts" / "runs" / "20240101-abcd" / "videos"
    base.mkdir(parents=True)
    target = base / "clip.webm"
    _touch(target, mtime=time.time())

    params = ListParams(root=tmp_path / "artifacts" / "runs", limit=5)
    page = list_recordings(params)

    assert page.items[0].run_id == "20240101-abcd"
