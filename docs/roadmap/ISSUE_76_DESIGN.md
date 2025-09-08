# Issue #76 Design: Automated Enrichment & Sync Workflow for `ISSUE_DEPENDENCIES.yml`

## 1. Goals (What & Why)

Automate metadata enrichment and consistency between the single-source dependency file (`ISSUE_DEPENDENCIES.yml`) and live GitHub Issues to:

- Reduce drift (labels / new issues / strict orphans) — currently manual & error-prone.
- Provide reviewable, minimal diffs via bot PRs instead of silent pushes.
- Preserve curated human judgment fields (depends, critical_path_rank, longest_chain_example) while auto-updating purely derivative metadata (priority / phase / area / risk / stability etc.).
- Establish a foundation for later automation layers (proposal logic, metrics, predictive ranking).

## 2. Non‑Goals

- Inferring or rewriting `depends` / `dependents` relationships.
- Auto-updating `critical_path_rank` or `longest_chain_example` (future proposal mode only).
- Closing / reopening GitHub issues.
- Auto-labeling (only consuming existing labels).

## 3. Source of Truth & Data Model

Primary source for dependency topology: `docs/roadmap/ISSUE_DEPENDENCIES.yml` (curated). GitHub Issues API is authoritative only for:

- Existence of issue IDs, titles, state.
- Labels (mapped to structured fields).

Round‑trip YAML must retain: ordering, comments, untouched scalar formatting. Use `ruamel.yaml` (round-trip loader/dumper). Add minimal machine markers as line comments: `# updated-by: enrich-script` only on modified scalar lines.

## 4. Label Mapping Strategy

Deterministic, idempotent mapping (example; configurable table in script):

| Label Pattern | Field        | Extraction Rule                               |
|---------------|--------------|-----------------------------------------------|
| `priority/PX` | meta.priority| Direct (P0..P4).                              |
| `phase/<slug>`| meta.phase   | Direct slug.                                  |
| `area/<slug>` | meta.area    | Direct slug.                                  |
| `risk/high`   | risk         | `high` (else keep existing unless overwritten)|
| `stability/*` | meta.stability| Direct slug.                                 |
| `automation`  | meta.area?   | (No – ignore; used for classification)        |

Rules:

1. By default: enrich only if field missing OR `--force-label` flag present.
2. Unmapped labels collected -> warning list.
3. Multiple conflicting labels (e.g., two priority labels) => warning, choose highest severity (lowest P number) deterministically.

## 5. Orphan Logic

Strict orphan recomputation (depends empty & no inbound references). Any strict orphan missing from curated orphan list is appended to curated list block (`summary.data_quality_checks.orphan_issues_without_dependents_or_depends`) with comment marker. Extra curated entries retained (treated as intentional) but surfaced as WARN.

## 6. New Issues Handling

Issues present in GitHub but absent from YAML:

- Listed under `pending_issues:` (new block) in dry-run summary.
- If `--auto-add-new` specified: inserted into `issues:` map with minimal scaffold:

```yaml
<id>:
  title: <title>
  meta: {priority: Px, phase: <phase?>, area: <area?>}
  depends: []
  dependents: []
  # added-by: enrich-script
```

Insertion order: numeric ascending at end.

## 7. CLI Interface

```bash
python scripts/enrich_issue_dependencies.py \
  --input docs/roadmap/ISSUE_DEPENDENCIES.yml \
  --output docs/roadmap/ISSUE_DEPENDENCIES.yml \
  --repo Nobukins/2bykilt \
  --token-env GITHUB_TOKEN \
  --dry-run

# Optional:
  --apply                 # Persist changes
  --auto-add-new          # Scaffold unknown issues
  --force-label           # Overwrite existing mapped fields
  --recompute-orphans-only# Skip label sync & new issue detection
  --json-summary FILE     # Emit machine-readable summary
  --fail-on-warn          # Escalate WARN to non-zero exit
```

## 8. Output Artifacts

1. Updated YAML (apply mode).
2. Markdown diff summary (stdout) — includes counts & lists.
3. Optional JSON summary for CI annotation.
4. GitHub Workflow PR branch with updated YAML + regenerated derived artifacts (graph, dashboard, queue) to ensure coherence.

## 9. Workflow (`.github/workflows/update-issue-dependencies.yml`)

Triggers:

- `schedule`: daily (cron early UTC hour)
- `workflow_dispatch`
- `issues`, `label`, `milestone` events (debounced via concurrency group)

Steps:

1. Checkout.
2. Setup Python deps (pyproject).
3. Run enrichment dry-run; if no diff -> job summary "no changes" & exit 0.
4. Run enrichment apply.
5. Re-run validation (`scripts/validate_dependencies.py`).
6. Regenerate artifacts (mermaid, dashboard, queue).
7. Git diff; create/update PR via GH CLI or `peter-evans/create-pull-request` action.
8. Attach JSON summary artifact.

Naming:

- Branch: `bot/roadmap-sync/<YYYYMMDD-HHMM>`
- PR title: `chore(roadmap): auto enrich ISSUE_DEPENDENCIES <YYYY-MM-DD>`

## 10. Validation & Idempotency

Repeat run with unchanged upstream issues must produce zero diff (idempotent). Key strategies:

- Canonical ordering (numeric issue id ascending) when inserting.
- Stable serialization (ruamel preserves existing order; avoid reflowing scalars).
- Only mutate lines for changed fields; maintain microstructure.

## 11. Error Handling / Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0    | Success / no diff | Normal exit |
| 3    | Diff detected (dry-run mode) | Still success (PR decision external) |
| 10   | Validation failure | Stop workflow |
| 11   | GitHub API error | Retry/backoff |
| 12   | YAML parse error | Manual fix required |

## 12. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Comment loss | ruamel round-trip loader/dumper |
| Race (simultaneous label edit) | Git fetch & rebase + second dry-run confirm before apply |
| API rate limit | Use conditional Accept + only needed fields, schedule low frequency |
| False orphan due to transient creation | Multi-event debounce concurrency group |

## 13. Phase Plan (Mapping to Issue Checklist)

Phase 1: Script MVP (dry-run/apply, label mapping, orphan recompute, diff summary).  
Phase 2: Workflow integration & PR opening.  
Phase 3: Extended validations (reverse dependents integrity, high_risk set consistency).  
Phase 4: Proposal hints (future) – not in initial acceptance.

## 14. Acceptance Traceability

Each acceptance criterion in issue mapped to script option or workflow step (see table in original issue; all covered except future proposals intentionally deferred).

## 15. Test Plan

- Unit-ish: run script against fixture YAML + mocked API payload (recorded JSON) verifying:
  - No change when labels already aligned.
  - Adds missing strict orphan.
  - Adds new issue to pending list (dry-run) and scaffolds with --auto-add-new.
  - Idempotency after apply.
  - Force overwrite when existing priority differs but `--force-label` set.
- Integration: GitHub workflow dry-run (push to temp branch) verifying PR creation and artifact regeneration.

## 16. Rollback Strategy

Revert bot PR (no destructive external effects). Disable workflow by renaming file or adding `if: false` guard. Manual restore from Git history if corruption occurs.

## 17. Open Questions / Future Enhancements

- Caching / ETag for large org scaling (not needed now).
- Metrics emission (#58) for enrichment latency & diff size.
- Suggesting `depends` via commit message or PR references.

---

Status: Draft v1 (initial commit for review).  
Author: Automation Design (Issue #76)

