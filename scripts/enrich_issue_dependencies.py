#!/usr/bin/env python3
"""Enrich ISSUE_DEPENDENCIES.yml with GitHub Issue metadata (Phase 1 MVP for Issue #76).

Features (Phase 1):
  - Dry-run vs apply mode
  - Fetch issues (title, labels, state) via GitHub REST API
  - Label -> field mapping (priority / phase / area / risk / stability)
  - Optional forced overwrite of existing mapped fields
  - Strict orphan recomputation & augmentation of curated list
  - New issue detection (pending list) & optional auto-add scaffolding
  - JSON summary artifact output
  - Idempotent round-trip preserving comments/order (ruamel.yaml)

Exit Codes:
  0: Success (no diff OR applied)
  3: Diff detected (dry-run, no apply)
 10: Validation / processing error
 11: GitHub API error
 12: YAML parse / write error

Limitations:
  - No depend/dependent inference
  - No PR automation (handled in workflow phase)
"""
from __future__ import annotations
import argparse
import dataclasses
import json
import os
import re
import sys
import textwrap
from typing import Dict, List, Any, Optional, Tuple

try:
    from ruamel.yaml import YAML  # type: ignore
except ImportError:  # pragma: no cover
    # Provide an explicit remediation command for faster developer action.
    print("[ERROR] Missing dependency 'ruamel.yaml'. Install it via: pip install ruamel.yaml", file=sys.stderr)
    sys.exit(12)

import urllib.request
import urllib.error

LABEL_PRIORITY_RE = re.compile(r"^priority/(P[0-4])$")
LABEL_PHASE_RE = re.compile(r"^phase/([a-zA-Z0-9_-]+)$")
LABEL_AREA_RE = re.compile(r"^area/([a-zA-Z0-9_-]+)$")
LABEL_STABILITY_RE = re.compile(r"^stability/([a-zA-Z0-9_-]+)$")


@dataclasses.dataclass
class EnrichConfig:
    input_path: str
    output_path: str
    repo: str
    token: Optional[str]
    dry_run: bool
    force_label: bool
    auto_add_new: bool
    recompute_orphans_only: bool
    json_summary: Optional[str]
    fail_on_warn: bool


@dataclasses.dataclass
class DiffSummary:
    modified_fields: int = 0
    added_issues: List[str] = dataclasses.field(default_factory=list)
    pending_issues: List[str] = dataclasses.field(default_factory=list)
    added_orphans: List[str] = dataclasses.field(default_factory=list)
    warnings: List[str] = dataclasses.field(default_factory=list)
    errors: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self):
        return dataclasses.asdict(self)


def parse_args() -> EnrichConfig:
    p = argparse.ArgumentParser(description="Enrich ISSUE_DEPENDENCIES.yml with GitHub metadata")
    p.add_argument("--input", default="docs/roadmap/ISSUE_DEPENDENCIES.yml")
    p.add_argument("--output", default="docs/roadmap/ISSUE_DEPENDENCIES.yml")
    p.add_argument("--repo", required=True, help="GitHub repo (owner/name)")
    p.add_argument("--token-env", default="GITHUB_TOKEN", help="Env var containing token")
    p.add_argument("--dry-run", action="store_true", help="Dry-run (no file write)")
    p.add_argument("--apply", action="store_true", help="Apply changes (override dry-run)")
    p.add_argument("--force-label", action="store_true", help="Force overwrite existing mapped fields")
    p.add_argument("--auto-add-new", action="store_true", help="Auto scaffold new issues")
    p.add_argument("--recompute-orphans-only", action="store_true", help="Only recompute orphans")
    p.add_argument("--json-summary", help="Write JSON summary to file")
    p.add_argument("--fail-on-warn", action="store_true", help="Treat warnings as errors exit !=0")
    args = p.parse_args()
    token = os.environ.get(args.token_env)
    dry = args.dry_run and not args.apply
    return EnrichConfig(
        input_path=args.input,
        output_path=args.output,
        repo=args.repo,
        token=token,
        dry_run=dry,
        force_label=args.force_label,
        auto_add_new=args.auto_add_new,
        recompute_orphans_only=args.recompute_orphans_only,
        json_summary=args.json_summary,
        fail_on_warn=args.fail_on_warn,
    )


def load_yaml_round_trip(path: str):
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.load(f)
    return yaml, data


def save_yaml_round_trip(yaml: YAML, data, path: str):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def github_request(repo: str, token: Optional[str], page: int = 1, per_page: int = 100):
    url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page={per_page}&page={page}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:  # pragma: no cover
        # Read body once (reading multiple times can yield empty content)
        try:
            error_body = e.read().decode('utf-8', 'ignore')
        except Exception:
            error_body = getattr(e, 'reason', '') or 'NO_BODY'
        raise RuntimeError(f"GitHub API HTTPError {e.code}: {error_body}")
    except urllib.error.URLError as e:  # pragma: no cover
        raise RuntimeError(f"GitHub API URLError: {e}")


def fetch_all_issues(repo: str, token: Optional[str]) -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []
    page = 1
    while True:
        items = github_request(repo, token, page=page)
        if not items:
            break
        # Filter out pull requests (GitHub returns PRs in issues API; they have 'pull_request' key)
        real_issues = [it for it in items if 'pull_request' not in it]
        all_items.extend(real_issues)
        if len(items) < 100:
            break
        page += 1
    return all_items


def calc_strict_orphans(issues: Dict[str, Any]) -> List[str]:
    referenced = set()
    for iid, meta in issues.items():
        for d in meta.get('depends') or []:
            referenced.add(str(d))
    strict = [iid for iid, meta in issues.items() if not meta.get('depends') and iid not in referenced]
    # stable numeric ordering
    return sorted(strict, key=lambda x: int(x) if x.isdigit() else x)


def map_labels_to_fields(labels: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    priorities = []
    for lab in labels:
        if (m := LABEL_PRIORITY_RE.match(lab)):
            priorities.append(m.group(1))
        elif (m := LABEL_PHASE_RE.match(lab)):
            out.setdefault('meta', {})['phase'] = m.group(1)
        elif (m := LABEL_AREA_RE.match(lab)):
            out.setdefault('meta', {})['area'] = m.group(1)
        elif (m := LABEL_STABILITY_RE.match(lab)):
            out.setdefault('meta', {})['stability'] = m.group(1)
        elif lab == 'risk/high':
            out['risk'] = 'high'
    if priorities:
        # Pick highest (P0 < P1 ...) while tolerating unexpected formats (e.g., P10)
        def prio_key(label: str) -> int:
            m = re.search(r"\d+", label)
            if not m:
                return 99  # push unknown to end
            try:
                return int(m.group(0))
            except ValueError:
                return 99
        priorities.sort(key=prio_key)
        out.setdefault('meta', {})['priority'] = priorities[0]
    return out


def enrich(config: EnrichConfig) -> Tuple[DiffSummary, int]:
    yaml, data = load_yaml_round_trip(config.input_path)
    if 'issues' not in data:
        return DiffSummary(errors=['Missing issues map']), 12
    issues = data['issues']
    summary = data.setdefault('summary', {})
    dq = summary.setdefault('data_quality_checks', {})

    ds = DiffSummary()

    # Fetch issues unless recompute-orphans-only
    gh_issues: List[Dict[str, Any]] = []
    if not config.recompute_orphans_only:
        try:
            gh_issues = fetch_all_issues(config.repo, config.token)
        except Exception as e:
            ds.errors.append(str(e))
            return ds, 11

    gh_index = {str(item['number']): item for item in gh_issues}
    existing_ids = set(issues.keys())
    gh_ids = set(gh_index.keys())

    new_ids = sorted(list(gh_ids - existing_ids), key=lambda x: int(x) if x.isdigit() else x)
    if new_ids:
        ds.pending_issues = new_ids
        if config.auto_add_new and not config.dry_run:
            for nid in new_ids:
                node = gh_index[nid]
                labels = [lab['name'] for lab in node.get('labels', [])]
                mapped = map_labels_to_fields(labels)
                issues[nid] = {
                    'title': node.get('title', ''),
                    'meta': mapped.get('meta', {}),
                    'risk': mapped.get('risk'),
                    'depends': [],
                    'dependents': [],
                }
                ds.added_issues.append(nid)

    # Label enrichment
    if not config.recompute_orphans_only:
        for iid, node in issues.items():
            gh = gh_index.get(iid)
            if not gh:
                continue
            labels = [lab['name'] for lab in gh.get('labels', [])]
            mapped = map_labels_to_fields(labels)
            # title sync if missing or empty
            if not node.get('title') and gh.get('title'):
                node['title'] = gh['title']
                ds.modified_fields += 1
            # apply mapped
            if mapped:
                meta_target = node.setdefault('meta', {})
                mapped_meta = mapped.get('meta', {})
                for k, v in mapped_meta.items():
                    if config.force_label or k not in meta_target or not meta_target.get(k):
                        if meta_target.get(k) != v:
                            meta_target[k] = v
                            ds.modified_fields += 1
                if 'risk' in mapped:
                    if config.force_label or not node.get('risk'):
                        if node.get('risk') != mapped['risk']:
                            node['risk'] = mapped['risk']
                            ds.modified_fields += 1
                # mark updated lines later by comment injection unsupported in simple ruamel approach (skipped Phase1)

    # Strict orphan recompute
    strict = calc_strict_orphans(issues)
    curated_list = set(dq.get('orphan_issues_without_dependents_or_depends', []) or [])
    missing = [i for i in strict if i not in curated_list]
    if missing:
        if not config.dry_run:
            dq['orphan_issues_without_dependents_or_depends'] = sorted(curated_list.union(strict), key=lambda x: int(x) if x.isdigit() else x)
        ds.added_orphans = missing

    # Summaries
    summary['total_issues'] = len(issues)
    # high_risk auto sync (advisory) - keep union of declared + risk=high
    risk_high = [iid for iid, m in issues.items() if m.get('risk') == 'high']
    declared_hr = set(summary.get('high_risk', []) or [])
    union_hr = sorted(set(risk_high).union(declared_hr), key=lambda x: int(x) if x.isdigit() else x)
    if union_hr != summary.get('high_risk'):
        if not config.dry_run:
            summary['high_risk'] = union_hr
        ds.modified_fields += 1

    # Decide if diff
    if config.dry_run:
        # Re-dump to string to see if differences would apply (simulate) skipped for speed; rely on counters
        code = 0 if (ds.modified_fields == 0 and not ds.added_issues and not ds.added_orphans) else 3
        return ds, code
    else:
        try:
            save_yaml_round_trip(yaml, data, config.output_path)
        except Exception as e:  # pragma: no cover
            ds.errors.append(f"Write failed: {e}")
            return ds, 12
        return ds, 0


def main():
    config = parse_args()
    ds, code = enrich(config)
    # Output human summary
    print("ENRICH SUMMARY")
    print(f"modified_fields={ds.modified_fields} added_issues={ds.added_issues} added_orphans={ds.added_orphans} pending={ds.pending_issues}")
    if ds.warnings:
        print("WARNINGS:")
        for w in ds.warnings:
            print(f" - {w}")
    if ds.errors:
        print("ERRORS:")
        for e in ds.errors:
            print(f" - {e}")
    if config.json_summary:
        with open(config.json_summary, 'w', encoding='utf-8') as f:
            json.dump(ds.to_dict(), f, indent=2, ensure_ascii=False)
    if ds.errors or (config.fail_on_warn and ds.warnings):
        # escalate
        sys.exit(10)
    sys.exit(code)


if __name__ == "__main__":  # pragma: no cover
    main()
