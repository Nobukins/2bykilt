"""Recursive recordings discovery utility (Issue #303).

Provides a flag-gated iterator that walks `artifacts/runs` (or a caller
specified root) to collect video artifacts safely without loading the entire
 tree into memory. The newest recordings are returned first and callers can
page through results via `limit` and `offset`.
"""

from __future__ import annotations

from itertools import islice
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

from src.config.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


DEFAULT_EXTENSIONS = (".webm", ".mp4", ".ogg")
_FLAG_RECURSIVE_SCAN = "artifacts.recursive_recordings_enabled"


@dataclass(frozen=True, slots=True)
class RecordingItem:
    """Lightweight DTO for a discovered recording."""

    path: Path
    size_bytes: int
    modified_at: float  # POSIX timestamp


def scan_recordings(
    root: Path,
    *,
    allow_extensions: Sequence[str] | None = None,
    limit: int = 50,
    offset: int = 0,
    allowed_roots: Sequence[Path] | None = None,
) -> Iterator[RecordingItem]:
    """Yield recording entries ordered by newest first.

    Args:
        root: Base directory that will be traversed. Must resolve within one of
            the `allowed_roots` entries (defaults to itself).
        allow_extensions: Optional overrides for video suffixes. Compared in a
            case-insensitive manner. Defaults to ``DEFAULT_EXTENSIONS``.
        limit: Maximum number of items to return. ``limit=0`` yields nothing.
        offset: Number of newest items to skip before yielding results.
        allowed_roots: Whitelisted parent directories. Each entry is resolved
            before comparison. Defaults to ``(root,)``.

    Returns:
        Iterator over ``RecordingItem`` instances. Consumers may convert to a
        list if random access is needed.

    Raises:
        ValueError: If parameters are invalid or the root escapes the whitelist.
    """

    _validate_pagination(limit, offset)

    if allow_extensions is None:
        extensions = {ext.lower() for ext in DEFAULT_EXTENSIONS}
    else:
        extensions = _normalise_extensions(allow_extensions)

    root_resolved = root.resolve()

    if allowed_roots is None:
        allowed_roots = (root_resolved,)
    else:
        allowed_roots = tuple(Path(r).resolve() for r in allowed_roots)

    if not _is_within_allowed_roots(root_resolved, allowed_roots):
        raise ValueError("root path escapes allowed roots whitelist")

    if not root_resolved.exists():
        logger.debug(
            "Recordings root does not exist",
            extra={"event": "recordings.scan.missing_root", "root": str(root_resolved)},
        )
        return iter(())

    if not root_resolved.is_dir():
        raise ValueError("root must be a directory")

    if not FeatureFlags.is_enabled(_FLAG_RECURSIVE_SCAN):
        return _scan_flat(root_resolved, extensions, limit=limit, offset=offset)

    return _scan_recursive(
        root_resolved,
        extensions,
        limit=limit,
        offset=offset,
        allowed_roots=allowed_roots,
    )


def _scan_flat(root: Path, extensions: set[str], *, limit: int, offset: int) -> Iterator[RecordingItem]:
    candidates: list[RecordingItem] = []

    for entry in root.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in extensions:
            continue
        stats = entry.stat()
        candidates.append(
            RecordingItem(path=entry, size_bytes=stats.st_size, modified_at=stats.st_mtime)
        )

    if not candidates:
        return iter(())

    candidates.sort(key=lambda item: item.modified_at, reverse=True)
    window = islice(candidates, offset, offset + limit if limit else None)
    return iter(window)


def _scan_recursive(
    root: Path,
    extensions: set[str],
    *,
    limit: int,
    offset: int,
    allowed_roots: Sequence[Path],
) -> Iterator[RecordingItem]:
    target_count = offset + limit if limit else offset
    heap: list[tuple[float, RecordingItem]] = []

    for entry in _walk(root, allowed_roots):
        if not entry.is_file(follow_symlinks=False):
            continue
        if entry.name.startswith("."):
            continue
        suffix = entry.name.rsplit(".", 1)[-1] if "." in entry.name else ""
        if suffix and f".{suffix.lower()}" not in extensions:
            continue
        try:
            stats = entry.stat(follow_symlinks=False)
        except FileNotFoundError:  # file vanished mid-scan
            continue

        item = RecordingItem(path=Path(entry.path), size_bytes=stats.st_size, modified_at=stats.st_mtime)

        if target_count == 0:
            continue

        if len(heap) < target_count:
            heap.append((item.modified_at, item))
            if len(heap) == target_count:
                heap.sort(key=lambda pair: pair[0])
            continue

        if item.modified_at <= heap[0][0]:
            continue

        heap[0] = (item.modified_at, item)
        _sift_down(heap)

    if not heap:
        return iter(())

    heap.sort(key=lambda pair: pair[0], reverse=True)
    ordered_items = [item for _, item in heap]
    window = islice(ordered_items, offset, offset + limit) if limit > 0 else iter(())
    return iter(window)


def _walk(root: Path, allowed_roots: Sequence[Path]) -> Iterator[os.DirEntry[str]]:
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    path = Path(entry.path)

                    if entry.is_dir(follow_symlinks=False):
                        resolved = path.resolve()
                        if not _is_within_allowed_roots(resolved, allowed_roots):
                            logger.warning(
                                "Skipping directory outside allowed roots",
                                extra={
                                    "event": "recordings.scan.disallowed_dir",
                                    "dir": str(resolved),
                                    "roots": [str(r.resolve()) for r in allowed_roots],
                                },
                            )
                            continue
                        stack.append(resolved)
                    yield entry
        except FileNotFoundError:
            continue


def _validate_pagination(limit: int, offset: int) -> None:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if offset < 0:
        raise ValueError("offset must be non-negative")


def _normalise_extensions(values: Sequence[str]) -> set[str]:
    normalised: set[str] = set()
    for ext in values:
        if not ext:
            continue
        ext = ext.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        normalised.add(ext)
    return normalised or {ext.lower() for ext in DEFAULT_EXTENSIONS}


def _is_within_allowed_roots(path: Path, allowed_roots: Sequence[Path]) -> bool:
    path_resolved = path.resolve()
    for root in allowed_roots:
        try:
            if path_resolved.is_relative_to(root):
                return True
        except ValueError:
            continue
    return False


def _sift_down(heap: list[tuple[float, RecordingItem]]) -> None:
    # Manual heapify for small heaps to avoid import-level dependency.
    index = 0
    size = len(heap)

    while True:
        left = 2 * index + 1
        right = left + 1
        smallest = index

        if left < size and heap[left][0] < heap[smallest][0]:
            smallest = left
        if right < size and heap[right][0] < heap[smallest][0]:
            smallest = right

        if smallest == index:
            break

        heap[index], heap[smallest] = heap[smallest], heap[index]
        index = smallest
