#!/usr/bin/env python3
"""
Validate ISSUE_DEPENDENCIES.yml internal consistency.

Checks:
  1. All summary.high_risk IDs exist.
  2. Orphan list matches recalculated orphans.
  3. longest_chain_example forms a valid forward dependency path.
  4. Detect cycles.

Exit code:
  0 = OK
  1 = Any validation error
"""

import sys
import yaml
from typing import Dict, List, Set

def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def calc_orphans(issues: Dict[str, dict]) -> Set[str]:
    all_ids = set(issues.keys())
    has_depends = {i for i, m in issues.items() if m.get("depends")}
    referenced = set()
    for m in issues.values():
        for d in m.get("depends") or []:
            referenced.add(d)
    # Orphan = not referencing others AND not referenced by others
    return {i for i in all_ids if i not in has_depends and i not in referenced}

def check_longest_chain(issues: Dict[str, dict], chain: List[str], errors: List[str]):
    # Ensure every consecutive pair has edge A -> B (i.e. B depends on A)
    for a, b in zip(chain, chain[1:]):
        depends = issues.get(b, {}).get("depends") or []
        if a not in depends:
            errors.append(f"longest_chain_example broken at {a} -> {b}: {b}.depends={depends}")

def detect_cycles(issues: Dict[str, dict], errors: List[str]):
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
            if dep in issues:
                dfs(dep, path + [dep])
        stack.remove(node)

    for i in issues.keys():
        if i not in visited:
            dfs(i, [i])

def main():
    if len(sys.argv) < 2:
        print("Usage: validate_dependencies.py docs/roadmap/ISSUE_DEPENDENCIES.yml", file=sys.stderr)
        return 1
    path = sys.argv[1]
    data = load_yaml(path)
    issues = data["issues"]
    summary = data.get("summary", {})

    errors: List[str] = []

    # 1. high_risk IDs exist
    for hid in summary.get("high_risk", []):
        if hid not in issues:
            errors.append(f"high_risk id {hid} not found in issues")

    # 2. orphans
    declared_orphans = set(summary.get("orphan_issues_without_dependents_or_depends", []))
    calc = calc_orphans(issues)
    if declared_orphans != calc:
        errors.append(f"Orphan mismatch: declared={sorted(declared_orphans)} recalculated={sorted(calc)}")

    # 3. longest_chain_example
    chain = summary.get("longest_chain_example") or []
    if chain:
        missing = [c for c in chain if c not in issues]
        if missing:
            errors.append(f"longest_chain_example contains unknown ids: {missing}")
        else:
            check_longest_chain(issues, chain, errors)

    # 4. cycle detection
    detect_cycles(issues, errors)

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(" - " + e)
        return 1
    print("VALIDATION OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
    