# Recording Path Migration (Issue #91)

Status: Complete (2025-09-04)

Applies to: Feature flag `artifacts.unified_recording_path`

## Summary

The default recording directory has migrated from the legacy `./tmp/record_videos` location to the run‑scoped unified artifacts hierarchy:

```text
artifacts/
  runs/<run_id>-art/
    videos/  <-- new default target
    manifest_v2.json
```

## Motivation

- Eliminate ad‑hoc temp directory (`./tmp/record_videos`) outside the artifact ID namespace.
- Ensure video artifacts participate in retention policies (#37) & manifest v2 catalog (#35).
- Simplify cleanup and enable future metrics aggregation (#58).

## Behavior Matrix

| Scenario | Flag Value | Effective Path | Notes |
|----------|------------|----------------|-------|
| Default (no override) | true (default) | `artifacts/runs/<run_id>-art/videos` | Unified path; manifest aware |
| Explicit override arg/env | n/a | user supplied | Always respected (created if missing) |
| Flag explicitly disabled | false | `./tmp/record_videos` | Emits one-time legacy warning (will be removed) |

## Deprecation Timeline

| Phase | Date (target) | Action |
|-------|---------------|--------|
| Phase 1 | 2025-09 (now) | Default enabled, legacy path still works w/ warning |
| Phase 2 | 2025-10 | Add startup warning if flag forced false in CI / tests |
| Phase 3 | 2025-11 | Remove legacy branch & warning; flag removal scheduled |

## Migration Guidance

1. Remove any hard-coded references to `./tmp/record_videos` in scripts / CI configs.
2. If consuming recordings programmatically, enumerate via manifest v2 instead of globbing the directory.
3. For custom pipelines needing a stable external path, pass an explicit `--recording-dir` (or env var) which still overrides both strategies.
4. Avoid persisting run-specific IDs; treat paths as ephemeral and resolve per run via `ArtifactManager.resolve_recording_dir()`.

## One-Time Warning

When the flag is explicitly disabled (via runtime override or environment variable):

```text
Legacy recording path explicitly forced; consider enabling artifacts.unified_recording_path
```

Logged with event key: `artifact.recording.legacy_path.forced`.

**Note**: As of Issue #106 (Phase 2 enforcement), warnings are only emitted when the flag is explicitly overridden to `false`. Default behavior (flag = `true`) produces no warnings.

## Test Coverage

- `tests/test_unified_recording_path_rollout.py` validates default path and legacy warning behavior.
- `tests/artifacts/test_recording_dir_override_warning.py` validates override source detection and conditional warnings (Issue #106).
- Full suite (174 passed, 1 skipped, 1 xfailed on 2025-09-04) confirms no regressions post-migration.

## Future Enhancements

- Integrate video size & retention counters into metrics exporter (#58).
- Optional compression / transcoding policy flag (auto mp4) after retention enforcement maturation.
- Remove `artifacts.unified_recording_path` flag once legacy path code is deleted (Phase 3) — replace with static behavior.

## Changelog Entry

Added in roadmap revision 1.0.13 (#91 complete).
Updated in roadmap revision 1.0.26 (#106 Phase 2 enforcement complete).
