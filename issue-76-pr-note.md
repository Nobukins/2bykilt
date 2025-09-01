# Draft PR Note (Issue #76)

## Title
chore(roadmap): auto enrich ISSUE_DEPENDENCIES initial workflow (Issue #76)

## Summary
Implements Phase 1 design groundwork for Issue #76 – adds design doc & timezone-aware datetime fix (avoids utcnow deprecation noise) preparing codebase for enrichment script integration.

## Included Changes

- docs/roadmap/ISSUE_76_DESIGN.md (design goals, workflow plan, acceptance mapping)
- scripts/gen_mermaid.py (aware UTC timestamp)
- scripts/generate_task_dashboard.py (aware UTC timestamp)

## Not Yet Included (next commits planned)

- enrich_issue_dependencies.py implementation
- GH workflow update-issue-dependencies.yml
- README_ROADMAP_AUTOMATION.md documentation

## Validation Performed

- Local script edits only (no functional diff expected besides timestamp format removal of trailing 'Z').
- Downstream regeneration expected to be stable.

## Test / Verification Plan

1. Run gen_mermaid & ensure timestamp format now ends with '+00:00'.
2. Run dashboard generator; confirm Generated at (UTC) line unchanged semantically.
3. Confirm no other diffs in artifacts beyond timestamp line when regenerated.

## Rollout & Next Steps
Proceed with enrichment script (Phase 1) then integrate workflow (Phase 2). After merging, enable daily schedule.

## Risks
Minimal – timestamp format change benign; consumers treat as comment / plain text.

---

This file is intentionally uncommitted until bundled with further implementation or used to author the PR description.
