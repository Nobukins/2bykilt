"""Recordings service facade (Issue #304).

Wraps the recordings scanner utility to provide a stable API surface for
callers (UI/server). Handles pagination metadata, flag-aware fallback, and
input validation before delegating to the scanner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Iterable, List, Sequence, TypeVar

from src.config.feature_flags import FeatureFlags
from src.recordings.recordings_scanner import DEFAULT_EXTENSIONS, RecordingItem, scan_recordings
from src.utils.recording_dir_resolver import create_or_get_recording_dir

T = TypeVar("T")

_FLAG_RECURSIVE_SCAN = "artifacts.recursive_recordings_enabled"
_MAX_LIMIT = 200


@dataclass(frozen=True, slots=True)
class RecordingsPage(Generic[T]):
    """Generic pagination container for recordings service responses."""

    items: List[T]
    limit: int
    offset: int
    has_next: bool


@dataclass(frozen=True, slots=True)
class RecordingItemDTO:
    """DTO consumed by UI/API layers."""

    path: str
    size_bytes: int
    modified_at: float
    run_id: str | None


@dataclass(frozen=True, slots=True)
class ListParams:
    """Input schema for ``list_recordings``."""

    root: Path | None = None
    limit: int = 50
    offset: int = 0
    allow_extensions: Sequence[str] | None = None
    allowed_roots: Sequence[Path] | None = None


def list_recordings(params: ListParams | None = None) -> RecordingsPage[RecordingItemDTO]:
    """Return a page of recordings ordered by newest first."""

    params = params or ListParams()

    limit = params.limit
    offset = params.offset

    if limit < 0:
        raise ValueError("limit must be non-negative")
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if limit > _MAX_LIMIT:
        raise ValueError(f"limit must not exceed {_MAX_LIMIT}")

    root = (params.root or create_or_get_recording_dir()).expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"Recordings root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Recordings root is not a directory: {root}")

    allow_extensions = params.allow_extensions or DEFAULT_EXTENSIONS

    if params.allowed_roots is None:
        allowed_roots: Sequence[Path] = (root,)
    else:
        allowed_roots = tuple(Path(p).resolve() for p in params.allowed_roots)

    _ensure_within_allowed_roots(root, allowed_roots)

    fetch_limit = limit + 1 if limit > 0 else 1

    if not FeatureFlags.is_enabled(_FLAG_RECURSIVE_SCAN):
        iterator = _scan_flat(root, allow_extensions, limit=fetch_limit, offset=offset)
    else:
        iterator = scan_recordings(
            root,
            allow_extensions=allow_extensions,
            limit=fetch_limit,
            offset=offset,
            allowed_roots=allowed_roots,
        )

    items = list(iterator)
    has_next = _has_next(items, limit)
    slice_limit = min(limit, len(items))
    window = items[:slice_limit]

    dto_items = [_to_dto(item) for item in window]

    return RecordingsPage(items=dto_items, limit=limit, offset=offset, has_next=has_next)


def _scan_flat(root: Path, allow_extensions: Sequence[str], *, limit: int, offset: int) -> Iterable[RecordingItem]:
    """Basic non-recursive listing used when the flag is disabled."""

    extensions = _normalise_extensions(allow_extensions)
    entries: list[RecordingItem] = []

    for entry in root.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in extensions:
            continue
        stats = entry.stat()
        entries.append(RecordingItem(path=entry, size_bytes=stats.st_size, modified_at=stats.st_mtime))

    entries.sort(key=lambda item: item.modified_at, reverse=True)
    end = offset + limit if limit else None
    window = entries[offset:end]
    return window


def _has_next(items: Sequence[RecordingItem], limit: int) -> bool:
    if limit == 0:
        return bool(items)
    return len(items) > limit


def _to_dto(item: RecordingItem) -> RecordingItemDTO:
    return RecordingItemDTO(
        path=str(item.path),
        size_bytes=item.size_bytes,
        modified_at=item.modified_at,
        run_id=_infer_run_id(item.path),
    )


def _infer_run_id(path: Path) -> str | None:
    parts = path.parts
    for index, part in enumerate(parts):
        if part == "runs" and index + 1 < len(parts):
            candidate = parts[index + 1]
            if candidate and candidate != "validation":
                return candidate
    return None


def _ensure_within_allowed_roots(root: Path, allowed_roots: Sequence[Path]) -> None:
    resolved = root.resolve()
    for candidate in allowed_roots:
        try:
            if resolved.is_relative_to(candidate):
                return
        except ValueError:
            continue
    raise ValueError("root path escapes allowed roots whitelist")


def _normalise_extensions(values: Sequence[str]) -> set[str]:
    normalised: set[str] = set()
    for ext in values:
        if not ext:
            continue
        value = ext.lower()
        if not value.startswith("."):
            value = f".{value}"
        normalised.add(value)
    return normalised or {ext.lower() for ext in DEFAULT_EXTENSIONS}
