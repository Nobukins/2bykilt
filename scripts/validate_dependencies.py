#!/usr/bin/env python3
"""
Validate ISSUE_DEPENDENCIES.yml internal consistency (enhanced, relaxed orphan semantics).

Checks (extended):
  1. All summary.high_risk IDs exist.
  2. Orphan list validation (configurable):
     - --orphan-mode superset (default): declared must be a superset of real orphans (extras -> warning).
     - --orphan-mode exact: declared must exactly match real orphans.
  3. longest_chain_example forms a valid forward dependency path (ID 型差異は文字列化で吸収)。
  4. Cycle detection.
  5. If summary.data_quality_checks.no_cycles_detected exists, it matches actual result.
  6. If summary.total_issues exists, it matches len(issues).
  7. (Advisory) summary.high_risk vs risk: high フィールドの差異を警告。

Exit code:
  0 = OK (warnings allowed)
  1 = Any validation error
"""

import sys
import yaml
import argparse
from typing import Dict, List, Set, Tuple

def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def calc_orphans(issues: Dict[str, dict]) -> Set[str]:
    """
    Strict orphan definition:
      - Has no depends
      - Is not referenced by any other issue's depends
    """
    all_ids = set(issues.keys())
    has_depends = {i for i, m in issues.items() if m.get("depends")}
    referenced = set()
    for m in issues.values():
        for d in m.get("depends") or []:
            referenced.add(str(d))
    # normalize referenced to string IDs (in case numeric)
    referenced = {str(r) for r in referenced}
    return {i for i in all_ids if i not in has_depends and i not in referenced}

def check_longest_chain(issues: Dict[str, dict], chain: List[str], errors: List[str]):
    # Ensure every consecutive pair A -> B where B.depends contains A
    for a, b in zip(chain, chain[1:]):
        depends = [str(x) for x in (issues.get(b, {}).get("depends") or [])]
        if a not in depends:
            errors.append(f"longest_chain_example broken at {a} -> {b}: {b}.depends={depends}")

def detect_cycles(issues: Dict[str, dict]) -> Tuple[List[str], bool]:
    errors = []
    visited = set()
    stack = set()

    def dfs(node: str, path: List[str]):
        if node in stack:
            cycle_path = path[path.index(node):] + [node]
            errors.append(f"Cycle detected: {' -> '.join(cycle_path)}")
            return
        if node in visited:
            return
        visited.add(node)
        stack.add(node)
        for dep in issues[node].get("depends") or []:
            dep_id = str(dep)
            if dep_id in issues:
                dfs(dep_id, path + [dep_id])
        stack.remove(node)

    for i in issues.keys():
        if i not in visited:
            dfs(i, [i])
    return errors, len(errors) == 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to ISSUE_DEPENDENCIES.yml")
    parser.add_argument("--orphan-mode",
                        choices=["superset", "exact"],
                        default="superset",
                        help="Validation rule for orphan list (default: superset)")
    args = parser.parse_args()

    data = load_yaml(args.path)
    issues_raw = data["issues"]

    # Normalize issue IDs to strings (keys already strings but defensive)
    issues: Dict[str, dict] = {str(k): v for k, v in issues_raw.items()}
    summary = data.get("summary", {})

    errors: List[str] = []
    warnings: List[str] = []

    # 1. high_risk IDs exist
    high_risk = [str(h) for h in (summary.get("high_risk", []) or [])]
    for hid in high_risk:
        if hid not in issues:
            errors.append(f"high_risk id {hid} not found in issues")

    # 2. orphan handling (flexible)
    dq = summary.get("data_quality_checks", {}) or {}
    declared_orphans = set()
    orphan_source = None
    if "orphan_issues_without_dependents_or_depends" in summary:
        declared_orphans = {str(o) for o in (summary.get("orphan_issues_without_dependents_or_depends") or [])}
        orphan_source = "summary.orphan_issues_without_dependents_or_depends"
    elif "orphan_issues_without_dependents_or_depends" in dq:
        declared_orphans = {str(o) for o in (dq.get("orphan_issues_without_dependents_or_depends") or [])}
        orphan_source = "summary.data_quality_checks.orphan_issues_without_dependents_or_depends"
    else:
        errors.append("No orphan_issues_without_dependents_or_depends field found in summary or data_quality_checks")

    real_orphans = calc_orphans(issues)

    if orphan_source:
        if args.orphan_mode == "exact":
            if declared_orphans != real_orphans:
                errors.append(
                    f"Orphan mismatch (mode=exact) {orphan_source}: declared={sorted(declared_orphans)} real={sorted(real_orphans)}"
                )
        else:  # superset mode
            missing = real_orphans - declared_orphans
            if missing:
                errors.append(
                    f"Orphan list missing real orphans {sorted(missing)} (mode=superset)"
                )
            extra = declared_orphans - real_orphans
            if extra:
                # Non-fatal: user curated additional leaf / independent items
                warnings.append(
                    f"Declared orphans include non-orphan IDs (treated as curated leaf set): {sorted(extra)}"
                )

    # 3. longest_chain_example
    chain_raw = summary.get("longest_chain_example") or []
    chain = [str(c) for c in chain_raw]  # normalize
    if chain:
        missing = [c for c in chain if c not in issues]
        if missing:
            errors.append(f"longest_chain_example contains unknown ids: {missing}")
        else:
            check_longest_chain(issues, chain, errors)

    # 4. cycles
    cycle_errors, no_cycles_actual = detect_cycles(issues)
    errors.extend(cycle_errors)

    # 5. no_cycles_detected consistency
    if "data_quality_checks" in summary and "no_cycles_detected" in dq:
        declared_no_cycles = bool(dq.get("no_cycles_detected"))
        if declared_no_cycles != no_cycles_actual:
            errors.append(
                f"data_quality_checks.no_cycles_detected={declared_no_cycles} but actual={no_cycles_actual}"
            )

    # 6. total_issues
    if "total_issues" in summary:
        declared_total = summary.get("total_issues")
        if declared_total != len(issues):
            errors.append(
                f"total_issues mismatch: declared={declared_total} actual={len(issues)}"
            )

    # 7. advisory high risk coherence
    risk_high_ids = {iid for iid, meta in issues.items() if (meta.get("risk") == "high")}
    high_risk_set = set(high_risk)
    if risk_high_ids and risk_high_ids != high_risk_set:
        warnings.append(
            f"Advisory: risk:'high' issues={sorted(risk_high_ids)} summary.high_risk={sorted(high_risk_set)} (consider syncing)"
        )

    # Output
    if errors:
        print("VALIDATION ERRORS:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
    if warnings:
        print("WARNINGS:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)

    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
    