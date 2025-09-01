"""Artifact Manager (Wave A3 Issues #28 #30 #33 #35 #36 #34 #37 #38)

Responsibilities (initial increment):
  * Unified recording path resolution (flag gated) (#28)
  * Screenshot capture utility wrapper (#33)
  * Manifest v2 generation (JSON) (#35)
  * Element value capture helper (#34 - foundational hook only)
  * Artifact listing API support (#36)
  * Video retention enforcement (#37)
  * Hooks for regression test suite (#38) - placeholder

Design Notes:
  - Backward compatibility: existing tests reference ./tmp/record_videos. We keep
    legacy path unless feature flag artifacts.unified_recording_path=true.
  - Manifest v2 schema (subject to doc update when #35 closes):
        {
          "schema": "artifact-manifest-v2",
          "run_id": <run_id_base>,
          "generated_at": <utc iso>,
          "artifacts": [
             {"type": "video", "path": "...", "size": int, "created_at": iso},
             {"type": "screenshot", "path": "...", "size": int, "created_at": iso, "meta": {"format": "png"}},
             {"type": "element_capture", "path": "...", "selector": "...", "text": "...", "created_at": iso}
          ]
        }
  - Each run writes its manifest under artifacts/runs/<run_id>-art/manifest_v2.json
  - Listing API will aggregate manifests (lightweight scan) and optionally filter by type.

Future:
  * Add hashing/integrity, streaming updates, metrics (#58) integration.
"""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext

_ARTIFACT_COMPONENT = "art"
_MANIFEST_FILENAME = "manifest_v2.json"

@dataclass
class ArtifactEntry:
    type: str
    path: str
    created_at: str
    size: int | None = None
    meta: Dict[str, Any] | None = None

@dataclass
class ElementCapture:
    selector: str
    text: str | None
    value: str | None

class ArtifactManager:
    def __init__(self) -> None:
        self.rc = RunContext.get()
        self.dir = self.rc.artifact_dir(_ARTIFACT_COMPONENT)
        self.manifest_path = self.dir / _MANIFEST_FILENAME
        self._manifest_cache: Dict[str, Any] | None = None

    # ---------------- Internal path serializer -----------------
    @staticmethod
    def _to_portable_relpath(p: Path) -> str:
        """Return a POSIX relative path string for manifest storage.

        Strategy:
          1. Try relative to CWD
          2. Else try relative to artifacts/ root
          3. Else fallback to basename
        Always uses '/' separators (portable) to avoid Windows '\\'.
        """
        cwd = Path.cwd()
        try:
            rel = p.relative_to(cwd)
            return rel.as_posix()
        except Exception:  # noqa: BLE001
            pass
        artifacts_root = Path("artifacts")
        try:
            rel = p.relative_to(artifacts_root)
            return rel.as_posix()
        except Exception:  # noqa: BLE001
            return p.name

    # ---------------- Path Logic -----------------
    @staticmethod
    def resolve_recording_dir(explicit: Optional[str] = None) -> Path:
        """Resolve recording directory considering feature flag (#28).

        Precedence:
          1. explicit path (if provided)
          2. flag artifacts.unified_recording_path -> use run artifact dir/videos
          3. legacy default ./tmp/record_videos
        """
        if explicit:
            p = Path(explicit).expanduser().resolve()
            p.mkdir(parents=True, exist_ok=True)
            return p
        if FeatureFlags.is_enabled("artifacts.unified_recording_path"):
            p = RunContext.get().artifact_dir(_ARTIFACT_COMPONENT) / "videos"
            p.mkdir(parents=True, exist_ok=True)
            return p
        # legacy
        p = Path("./tmp/record_videos").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ---------------- Manifest -------------------
    def _load_manifest(self) -> Dict[str, Any]:
        if self._manifest_cache is not None:
            return self._manifest_cache
        if self.manifest_path.exists():
            try:
                self._manifest_cache = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                return self._manifest_cache
            except Exception:
                pass
        self._manifest_cache = {
            "schema": "artifact-manifest-v2",
            "run_id": self.rc.run_id_base,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "artifacts": [],
        }
        return self._manifest_cache

    def _persist_manifest(self) -> None:
        data = self._load_manifest()
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        tmp = self.manifest_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.manifest_path)

    def add_entry(self, entry: ArtifactEntry) -> None:
        manifest = self._load_manifest()
        manifest["artifacts"].append(asdict(entry))
        self._persist_manifest()

    # ---------------- Video Handling (#30) -------------------
    def register_video_file(self, video_path: Path) -> Path:
        """Register a video artifact. Optionally transcode to target container.

        Feature flags:
          artifacts.video_target_container: 'auto' (keep) or 'mp4'
          artifacts.video_transcode_enabled: bool (if true and source != target)
        Transcoding requires `ffmpeg` on PATH. Failures are logged silently (no raise).
        """
        target_container = FeatureFlags.get("artifacts.video_target_container", expected_type=str, default="auto")
        transcode_enabled = FeatureFlags.is_enabled("artifacts.video_transcode_enabled")
        src = video_path
        final_path = src
        try:
            if target_container and target_container != "auto":
                desired_ext = f".{target_container.lower()}"
                if src.suffix.lower() != desired_ext and transcode_enabled:
                    # attempt transcode webm->mp4 only (current scope)
                    if desired_ext == ".mp4" and src.suffix.lower() in {".webm", ".mp4"}:
                        out_path = src.with_suffix(desired_ext)
                        # avoid overwriting existing good file
                        if not out_path.exists():
                            import subprocess
                            cmd = ["ffmpeg", "-y", "-i", str(src), str(out_path)]
                            try:
                                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                final_path = out_path
                            except Exception:
                                final_path = src  # fallback keep original
                        else:
                            final_path = out_path
        except Exception:
            final_path = src

        try:
            self.add_entry(ArtifactEntry(
                type="video",
                path=self._to_portable_relpath(final_path),
                created_at=datetime.now(timezone.utc).isoformat(),
                size=final_path.stat().st_size if final_path.exists() else None,
                meta={
                    "original_ext": src.suffix.lower(),
                    "final_ext": final_path.suffix.lower(),
                    "transcoded": final_path != src,
                },
            ))
        except Exception:
            pass
        return final_path

    # ---------------- Capture Helpers ----------------
    def save_screenshot_bytes(self, data: bytes, prefix: str = "screenshot") -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        fname = f"{prefix}_{ts}.png"
        out_dir = self.dir / "screenshots"
        out_dir.mkdir(parents=True, exist_ok=True)
        fpath = out_dir / fname
        fpath.write_bytes(data)
        self.add_entry(ArtifactEntry(
            type="screenshot",
            path=self._to_portable_relpath(fpath),
            created_at=datetime.now(timezone.utc).isoformat(),
            size=fpath.stat().st_size,
            meta={"format": "png"},
        ))
        return fpath

    def save_base64_screenshot(self, b64: str, prefix: str = "screenshot") -> Path:
        try:
            raw = base64.b64decode(b64)
            return self.save_screenshot_bytes(raw, prefix=prefix)
        except Exception:
            return Path()

    def save_element_capture(self, selector: str, text: str | None, value: str | None) -> Path:
        out_dir = self.dir / "elements"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S%f")
        fname = f"element_{ts}.json"
        fpath = out_dir / fname
        payload = {
            "selector": selector,
            "text": text,
            "value": value,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        fpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.add_entry(ArtifactEntry(
            type="element_capture",
            path=self._to_portable_relpath(fpath),
            created_at=datetime.now(timezone.utc).isoformat(),
            size=fpath.stat().st_size,
            meta={"selector": selector},
        ))
        return fpath

    # ---------------- Listing / Query --------------
    @staticmethod
    def list_manifests(limit: int | None = None) -> List[Dict[str, Any]]:
        root = Path("artifacts") / "runs"
        manifests: List[Dict[str, Any]] = []
        for p in sorted(root.glob("*-art"), reverse=True):
            m = p / _MANIFEST_FILENAME
            if m.exists():
                try:
                    data = json.loads(m.read_text(encoding="utf-8"))
                    manifests.append(data)
                except Exception:
                    continue
            if limit and len(manifests) >= limit:
                break
        return manifests

    # ---------------- Retention (#37) --------------
    def enforce_video_retention(self) -> int:
        days = FeatureFlags.get("artifacts.video_retention_days", expected_type=int, default=0)
        if not days or days <= 0:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        videos_dir = self.dir / "videos"
        if not videos_dir.exists():
            return 0
        removed = 0
        for f in videos_dir.glob("*.mp4"):
            try:
                stat = f.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    f.unlink(missing_ok=True)
                    removed += 1
            except Exception:
                continue
        return removed

# Convenience singleton (lazy)
_default_manager: ArtifactManager | None = None

def get_artifact_manager() -> ArtifactManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = ArtifactManager()
    return _default_manager

__all__ = [
    "ArtifactManager",
    "ArtifactEntry",
    "get_artifact_manager",
]
