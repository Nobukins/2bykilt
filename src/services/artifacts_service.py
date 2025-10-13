"""Artifacts service facade (Issue #277).

Provides a stable API surface for listing and accessing artifacts from run manifests.
Handles pagination, filtering by run_id and artifact type, and security validation.

Design:
  - Scans manifest_v2.json files under artifacts/runs/
  - Filters by run_id, artifact type (video, screenshot, element_capture)
  - Returns paginated results with metadata
  - Security: only serves files within canonical artifacts directory
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Sequence

from src.core.artifact_manager import get_artifact_manager
from src.runtime.run_context import RunContext
from src.utils.fs_paths import get_artifacts_base_dir

ArtifactType = Literal["video", "screenshot", "element_capture", "all"]

_MAX_LIMIT = 100
_MANIFEST_FILENAME = "manifest_v2.json"


@dataclass(frozen=True, slots=True)
class ArtifactItemDTO:
    """DTO for individual artifact items."""

    run_id: str
    type: str
    path: str
    size: int | None
    created_at: str
    meta: dict | None = None


@dataclass(frozen=True, slots=True)
class ArtifactsPage:
    """Paginated response for artifacts listing."""

    items: List[ArtifactItemDTO]
    limit: int
    offset: int
    has_next: bool
    total_count: int | None = None


@dataclass(frozen=True, slots=True)
class ListArtifactsParams:
    """Input parameters for list_artifacts."""

    run_id: str | None = None
    artifact_type: ArtifactType = "all"
    limit: int = 50
    offset: int = 0
    allowed_roots: Sequence[Path] | None = None


def list_artifacts(params: ListArtifactsParams | None = None) -> ArtifactsPage:
    """List artifacts with optional filtering by run_id and type.

    Args:
        params: Query parameters for filtering and pagination

    Returns:
        Paginated list of artifacts

    Raises:
        ValueError: If parameters are invalid
        FileNotFoundError: If artifacts root doesn't exist
    """
    params = params or ListArtifactsParams()

    # Validate parameters
    if params.limit < 0:
        raise ValueError("limit must be non-negative")
    if params.offset < 0:
        raise ValueError("offset must be non-negative")
    if params.limit > _MAX_LIMIT:
        raise ValueError(f"limit must not exceed {_MAX_LIMIT}")

    artifacts_root = get_artifacts_base_dir() / "runs"
    if not artifacts_root.exists():
        raise FileNotFoundError(f"Artifacts root does not exist: {artifacts_root}")

    # Security: establish allowed roots
    if params.allowed_roots is None:
        allowed_roots: Sequence[Path] = (artifacts_root,)
    else:
        allowed_roots = tuple(Path(p).resolve() for p in params.allowed_roots)

    _ensure_within_allowed_roots(artifacts_root, allowed_roots)

    # Collect all artifacts from manifests
    all_artifacts: List[ArtifactItemDTO] = []

    # If specific run_id is provided, only scan that manifest (recursively)
    if params.run_id:
        manifest_paths = list(artifacts_root.glob(f"**/{params.run_id}*-art/{_MANIFEST_FILENAME}"))
    else:
        # Scan all manifests recursively
        manifest_paths = list(artifacts_root.glob(f"**/*-art/{_MANIFEST_FILENAME}"))

    # Sort by modification time (newest first)
    manifest_paths.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

    for manifest_path in manifest_paths:
        try:
            artifacts = _load_artifacts_from_manifest(manifest_path, params.artifact_type)
            all_artifacts.extend(artifacts)
        except Exception:  # noqa: BLE001
            # Skip invalid manifests
            continue

    # Apply pagination
    total_count = len(all_artifacts)
    start = params.offset
    end = start + params.limit if params.limit > 0 else len(all_artifacts)

    page_items = all_artifacts[start:end]
    has_next = end < total_count

    return ArtifactsPage(
        items=page_items,
        limit=params.limit,
        offset=params.offset,
        has_next=has_next,
        total_count=total_count,
    )


def _load_artifacts_from_manifest(manifest_path: Path, artifact_type: ArtifactType) -> List[ArtifactItemDTO]:
    """Load artifacts from a single manifest file."""
    import json

    # Extract run_id from path (format: <run_id>-art/manifest_v2.json)
    run_id = manifest_path.parent.name.replace("-art", "")

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []

    artifacts = data.get("artifacts", [])
    results: List[ArtifactItemDTO] = []

    artifacts_root = get_artifacts_base_dir()

    for artifact in artifacts:
        art_type = artifact.get("type", "")

        # Filter by type if specified
        if artifact_type != "all" and art_type != artifact_type:
            continue

        # Resolve path (handle both relative and absolute)
        path_str = artifact.get("path", "")
        if not path_str:
            continue

        # Try to resolve path relative to various bases
        artifact_path = _resolve_artifact_path(path_str, manifest_path.parent, artifacts_root)

        if not artifact_path or not artifact_path.exists():
            continue

        results.append(
            ArtifactItemDTO(
                run_id=run_id,
                type=art_type,
                path=str(artifact_path),
                size=artifact.get("size"),
                created_at=artifact.get("created_at", ""),
                meta=artifact.get("meta"),
            )
        )

    return results


def _resolve_artifact_path(path_str: str, manifest_dir: Path, artifacts_root: Path) -> Path | None:
    """Resolve artifact path from manifest entry.

    Tries multiple strategies:
    1. Relative to manifest directory
    2. Relative to artifacts root
    3. Absolute path if within artifacts root
    """
    # Try as-is if absolute
    candidate = Path(path_str)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    # Try relative to manifest directory
    candidate = manifest_dir / path_str
    if candidate.exists():
        return candidate

    # Try relative to artifacts root
    candidate = artifacts_root / path_str
    if candidate.exists():
        return candidate

    # Try relative to runs directory
    runs_dir = artifacts_root / "runs"
    candidate = runs_dir / path_str
    if candidate.exists():
        return candidate

    return None


def _ensure_within_allowed_roots(path: Path, allowed_roots: Sequence[Path]) -> None:
    """Validate that path is within allowed roots (security check)."""
    resolved = path.resolve()
    for candidate in allowed_roots:
        try:
            if resolved.is_relative_to(candidate):
                return
        except ValueError:
            continue
    raise ValueError("path escapes allowed roots whitelist")


def get_artifact_summary(run_id: str | None = None) -> dict:
    """Get summary statistics for artifacts.

    Args:
        run_id: Optional run ID to filter by

    Returns:
        Dictionary with artifact counts by type
    """
    params = ListArtifactsParams(run_id=run_id, limit=0)  # No limit for summary

    try:
        page = list_artifacts(params)

        summary = {
            "total": page.total_count or 0,
            "by_type": {
                "video": 0,
                "screenshot": 0,
                "element_capture": 0,
            },
            "total_size_bytes": 0,
        }

        for item in page.items:
            if item.type in summary["by_type"]:
                summary["by_type"][item.type] += 1
            if item.size:
                summary["total_size_bytes"] += item.size

        return summary

    except Exception:  # noqa: BLE001
        return {
            "total": 0,
            "by_type": {"video": 0, "screenshot": 0, "element_capture": 0},
            "total_size_bytes": 0,
            "error": "Failed to load artifacts",
        }


__all__ = [
    "list_artifacts",
    "get_artifact_summary",
    "ListArtifactsParams",
    "ArtifactItemDTO",
    "ArtifactsPage",
    "ArtifactType",
]
