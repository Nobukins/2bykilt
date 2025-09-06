#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate TASK_DASHBOARD.md from docs/roadmap/ISSUE_DEPENDENCIES.yml.

要点:
  - 依存グラフの単一ソース (ISSUE_DEPENDENCIES.yml) から、運用向けダッシュボード Markdown を再生成
  - 新規の補助ファイルは作成せず、既存ファイルのみを入力に利用する想定
  - Orphan (strict) / curated orphan の差異を表示
  - 各種集計 (priority / phase / area / risk など)
  - クリティカルパス (最長距離) 推定: depends の有向非循環前提 (validator が no_cycles を保証する前提)
  - summary.longest_chain_example に存在しない ID が含まれていても無視 (例示として扱う)

使用方法:
  python scripts/generate_task_dashboard.py
  (オプション)
    --input docs/roadmap/ISSUE_DEPENDENCIES.yml
    --output docs/roadmap/TASK_DASHBOARD.md
    --sort critical_path_rank (他: priority, phase, area, id)
    --show-internal (内部診断セクションも出力)

出力内容(主):
  1. メタサマリー
  2. 分布 (priority / phase / area / risk)
  3. リスク一覧 (high など)
  4. Orphans (strict と curated の比較)
  5. クリティカルパス推定 (自動算出)
  6. テーブル (指定ソート)
  7. 依存詳細 (Fan-in / Fan-out)
  8. 内部診断 (オプション)

依存:
  - PyYAML (yaml)
    無い場合は簡易失敗メッセージを表示
"""

from __future__ import annotations
import argparse
import collections
import datetime as dt
import json
import os
import sys
from typing import Dict, List, Set, Tuple, Optional

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML (yaml) が見つかりません。 pip install pyyaml を実行してください。", file=sys.stderr)
    sys.exit(1)


# ---------------------------
# Data Structures
# ---------------------------

class Issue:
    def __init__(self, iid: str, data: dict):
        self.id = iid
        self.title: str = data.get("title", "")
        self.meta: dict = data.get("meta", {}) or {}
        self.depends: List[str] = list(data.get("depends", []) or [])
        self.dependents: List[str] = list(data.get("dependents", []) or [])
        self.progress: dict = data.get("progress", {}) or {}
        self.risk: Optional[str] = data.get("risk")
        self.critical_path_rank: Optional[int] = data.get("critical_path_rank")
        # Derived later
        self.longest_distance: Optional[int] = None  # for critical path calc


# Priority ordering (P0 highest)
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


# ---------------------------
# Loading
# ---------------------------

def load_issue_dependencies(path: str) -> Tuple[Dict[str, Issue], dict]:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    issues_raw = raw.get("issues", {}) or {}
    issues: Dict[str, Issue] = {}
    for iid, data in issues_raw.items():
        issues[iid] = Issue(iid, data or {})
    summary = raw.get("summary", {}) or {}
    return issues, summary


# ---------------------------
# Orphan Calculation
# ---------------------------

def compute_strict_orphans(issues: Dict[str, Issue]) -> Set[str]:
    # Strict orphan: depends == [] and nobody references it
    referenced = set()
    for issue in issues.values():
        for d in issue.depends:
            referenced.add(d)
    strict = {iid for iid, issue in issues.items() if not issue.depends and iid not in referenced}
    return strict


# ---------------------------
# Longest Path / Critical Path Estimation
# ---------------------------

def topological_order(issues: Dict[str, Issue]) -> List[str]:
    # Edge: B -> A (A.depends contains B)
    indeg = {iid: 0 for iid in issues}
    for issue in issues.values():
        for dep in issue.depends:
            if dep in indeg:
                indeg[issue.id] += 1
    queue = collections.deque([iid for iid, d in indeg.items() if d == 0])
    order = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for child in issues[n].dependents:
            if child in indeg:
                indeg[child] -= 1
                if indeg[child] == 0:
                    queue.append(child)
    # If cycle -> order length mismatch; we ignore here (validator should block) but still return partial
    return order


def compute_longest_distances(issues: Dict[str, Issue]) -> List[str]:
    """
    longest_distance = 依存の根 (indegree 0) を距離0 とし、進む毎に +1
    もっとも距離の大きいノード群から 1 つを最終点とし、逆トレースでパスを取り出す
    """
    order = topological_order(issues)
    for iid in issues:
        issues[iid].longest_distance = 0

    # Build adjacency (B->A edges)
    forward = {iid: [] for iid in issues}
    for issue in issues.values():
        for dep in issue.depends:
            if dep in forward:
                forward[dep].append(issue.id)

    # DP
    parent = {iid: None for iid in issues}
    for node in order:
        base_dist = issues[node].longest_distance or 0
        for child in forward[node]:
            cand = base_dist + 1
            if cand > (issues[child].longest_distance or 0):
                issues[child].longest_distance = cand
                parent[child] = node

    # Pick farthest
    farthest = max(issues.values(), key=lambda x: x.longest_distance or 0)
    path = []
    cur = farthest.id
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path


# ---------------------------
# Aggregations
# ---------------------------

def aggregate_by(issues: Dict[str, Issue], key: str) -> Dict[str, int]:
    counter = collections.Counter()
    for issue in issues.values():
        val = issue.meta.get(key)
        if val is None:
            val = "(none)"
        counter[str(val)] += 1
    return dict(sorted(counter.items(), key=lambda x: x[0]))


def aggregate_risk(issues: Dict[str, Issue]) -> Dict[str, int]:
    counter = collections.Counter()
    for issue in issues.values():
        counter[str(issue.risk) if issue.risk else "none"] += 1
    return dict(sorted(counter.items(), key=lambda x: x[0]))


# ---------------------------
# Formatting Helpers
# ---------------------------

def format_priority(pri: Optional[str]) -> str:
    if pri is None:
        return ""
    return pri


def issue_sort_key(issue: Issue, mode: str):
    if mode == "critical_path_rank":
        # 小さいほど左側 (= 早期) とのコメントがあるため降順化せずそのまま
        return (-(issue.critical_path_rank or -9999), issue.id)
    if mode == "priority":
        pri = issue.meta.get("priority", "P9")
        return (PRIORITY_ORDER.get(pri, 99), issue.id)
    if mode == "phase":
        return (issue.meta.get("phase", ""), issue.id)
    if mode == "area":
        return (issue.meta.get("area", ""), issue.id)
    if mode == "id":
        return (int(issue.id) if issue.id.isdigit() else issue.id,)
    return (int(issue.id) if issue.id.isdigit() else issue.id,)


def markdown_table(rows: List[List[str]], header: List[str]) -> str:
    out = []
    out.append("| " + " | ".join(header) + " |")
    out.append("| " + " | ".join(["---"] * len(header)) + " |")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def percent(part: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{(part / total * 100):.1f}%"

# ---------------------------
# Dashboard Generation
# ---------------------------

def generate_dashboard(issues: Dict[str, Issue],
                       summary: dict,
                       *,
                       sort_mode: str,
                       include_internal: bool) -> str:
    total = len(issues)
    # Use timezone-aware UTC (PEP 495 / aware datetime best practice)
    now = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()

    strict_orphans = compute_strict_orphans(issues)
    curated_orphans = set(summary.get("data_quality_checks", {}).get("orphan_issues_without_dependents_or_depends", []))
    missing_in_curated = strict_orphans - curated_orphans
    extra_in_curated = curated_orphans - strict_orphans

    auto_cp_path = compute_longest_distances(issues)

    high_risk_list = summary.get("high_risk", [])
    high_risk_actual = [iid for iid in high_risk_list if iid in issues]

    # Aggregations
    by_priority = aggregate_by(issues, "priority")
    by_phase = aggregate_by(issues, "phase")
    by_area = aggregate_by(issues, "area")
    risk_dist = aggregate_risk(issues)

    # Table rows
    sorted_issues = sorted(issues.values(), key=lambda x: issue_sort_key(x, sort_mode))

    table_rows = []
    for issue in sorted_issues:
        pri = issue.meta.get("priority", "")
        phase = issue.meta.get("phase", "")
        area = issue.meta.get("area", "")
        depends_count = len(issue.depends)
        dependents_count = len(issue.dependents)
        risk = issue.risk or ""
        cp_rank = str(issue.critical_path_rank) if issue.critical_path_rank is not None else ""
        ld = str(issue.longest_distance) if issue.longest_distance is not None else ""
        pr_link = ""
        if issue.progress.get("primary_pr"):
            pr_link = f"#{issue.progress['primary_pr']}"
        table_rows.append([
            issue.id,
            issue.title.replace("|", "\\|"),
            pri,
            phase,
            area,
            risk,
            cp_rank,
            ld,
            str(depends_count),
            str(dependents_count),
            pr_link
        ])

    table_md = markdown_table(
        table_rows,
        ["ID","Title","Pri","Phase","Area","Risk","CP Rank","LongestDist","Depends","Dependents","PrimaryPR"]
    )

    def kv_block(counter: Dict[str, int]) -> str:
        lines = []
        total_local = sum(counter.values())
        for k, v in counter.items():
            lines.append(f"- {k}: {v} ({percent(v, total_local)})")
        return "\n".join(lines)

    # Critical path explanation
    cp_explain = (
        "Critical Path (自動算出): depends の有向エッジ (B→A) を距離 0 起点から最長距離でトレースしたパス。"
        " 実際の期間や見積りを考慮せず、依存段数のみで推定。"
    )

    # Build markdown
    md = []
    md.append("# TASK DASHBOARD")
    md.append("")
    md.append(f"Generated at (UTC): {now}")
    md.append("")
    md.append("## 1. メタサマリー")
    md.append("")
    md.append(f"- Total Issues: {total}")
    md.append(f"- High Risk (declared): {len(high_risk_actual)} → {', '.join(high_risk_actual) if high_risk_actual else '(none)'}")
    if summary.get("data_quality_checks", {}).get("no_cycles_detected") is False:
        md.append("- Cycle Detected: TRUE (要調査)")
    else:
        md.append("- Cycle Detected: false (none)")
    md.append(f"- Strict Orphans: {len(strict_orphans)}")
    md.append(f"- Curated Orphan List Count: {len(curated_orphans)}")
    md.append("")

    md.append("## 2. 分布 (Distribution)")
    md.append("")
    md.append("### Priority")
    md.append(kv_block(by_priority) or "(none)")
    md.append("")
    md.append("### Phase")
    md.append(kv_block(by_phase) or "(none)")
    md.append("")
    md.append("### Area")
    md.append(kv_block(by_area) or "(none)")
    md.append("")
    md.append("### Risk")
    md.append(kv_block(risk_dist) or "(none)")
    md.append("")

    md.append("## 3. リスク詳細 (High / Medium / etc.)")
    md.append("")
    if high_risk_actual:
        md.append("High Risk Issues:")
        for iid in high_risk_actual:
            issue = issues[iid]
            md.append(f"- {iid}: {issue.title} (area={issue.meta.get('area')}, priority={issue.meta.get('priority')})")
    else:
        md.append("(no high risk issues declared)")
    md.append("")

    md.append("## 4. Orphans")
    md.append("")
    md.append("Strict Orphans (自動抽出 = 依存なし & 参照されず):")
    if strict_orphans:
        for iid in sorted(strict_orphans, key=lambda x: int(x) if x.isdigit() else x):
            md.append(f"- {iid}: {issues[iid].title}")
    else:
        md.append("- (none)")
    md.append("")
    md.append("Curated Orphan List (summary.data_quality_checks.orphan_issues_without_dependents_or_depends):")
    if curated_orphans:
        for iid in sorted(curated_orphans, key=lambda x: int(x) if x.isdigit() else x):
            title = issues[iid].title if iid in issues else "(not present)"
            md.append(f"- {iid}: {title}")
    else:
        md.append("- (none)")
    md.append("")
    if missing_in_curated:
        md.append(f"Missing Strict Orphans in curated list (ERROR if validator runs): {', '.join(sorted(missing_in_curated))}")
    else:
        md.append("Missing Strict Orphans in curated list: (none)")
    if extra_in_curated:
        md.append(f"Extra non-strict entries in curated list (WARNING only): {', '.join(sorted(extra_in_curated))}")
    else:
        md.append("Extra non-strict entries in curated list: (none)")
    md.append("")

    md.append("## 5. クリティカルパス推定")
    md.append("")
    md.append(cp_explain)
    md.append("")
    md.append("Auto Estimated Path (Longest Distance):")
    md.append(" → ".join(auto_cp_path))
    md.append("")
    # (Optional) Provided example chain (only existing IDs)
    example_chain = summary.get("longest_chain_example", [])
    existing_example = [iid for iid in example_chain if iid in issues]
    if existing_example:
        md.append("Provided Example (existing IDs only):")
        md.append(" → ".join(existing_example))
        md.append("")
    else:
        if example_chain:
            md.append("Provided Example references no valid existing IDs (all skipped).")
            md.append("")

    md.append("## 6. Issues Table (sorted)")
    md.append("")
    md.append(f"Sorted By: {sort_mode}")
    md.append("")
    md.append(table_md)
    md.append("")

    md.append("## 7. 依存詳細 (Fan-in / Fan-out)")
    md.append("")
    for issue in sorted_issues:
        md.append(f"### Issue {issue.id}: {issue.title}")
        md.append(f"- Priority: {issue.meta.get('priority')}, Phase: {issue.meta.get('phase')}, Area: {issue.meta.get('area')}")
        md.append(f"- Risk: {issue.risk or '(none)'}")
        md.append(f"- CriticalPathRank: {issue.critical_path_rank}")
        md.append(f"- LongestDistance: {issue.longest_distance}")
        md.append(f"- Depends ({len(issue.depends)}): {', '.join(issue.depends) if issue.depends else '(none)'}")
        md.append(f"- Dependents ({len(issue.dependents)}): {', '.join(issue.dependents) if issue.dependents else '(none)'}")
        if issue.progress:
            md.append(f"- Progress: {json.dumps(issue.progress, ensure_ascii=False)}")
        md.append("")

    if include_internal:
        md.append("## 8. INTERNAL (Diagnostics)")
        md.append("")
        md.append("Raw Aggregations (JSON-like):")
        diagnostics = {
            "by_priority": by_priority,
            "by_phase": by_phase,
            "by_area": by_area,
            "risk_dist": risk_dist,
            "strict_orphans": sorted(strict_orphans),
            "curated_orphans": sorted(curated_orphans),
            "missing_in_curated": sorted(missing_in_curated),
            "extra_in_curated": sorted(extra_in_curated),
        }
        md.append("```json")
        md.append(json.dumps(diagnostics, indent=2, ensure_ascii=False))
        md.append("```")
        md.append("")

    return "\n".join(md) + "\n"


# ---------------------------
# CLI
# ---------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Generate TASK_DASHBOARD.md from ISSUE_DEPENDENCIES.yml")
    p.add_argument("--input", default="docs/roadmap/ISSUE_DEPENDENCIES.yml")
    p.add_argument("--output", default="docs/roadmap/TASK_DASHBOARD.md")
    p.add_argument("--sort", dest="sort_mode", default="critical_path_rank",
                   choices=["critical_path_rank", "priority", "phase", "area", "id"],
                   help="ソート基準 (default: critical_path_rank)")
    p.add_argument("--show-internal", action="store_true", help="内部診断情報を付与")
    return p.parse_args()


def main():
    args = parse_args()
    if not os.path.exists(args.input):
        print(f"[ERROR] Input file not found: {args.input}", file=sys.stderr)
        sys.exit(2)

    issues, summary = load_issue_dependencies(args.input)
    md = generate_dashboard(issues, summary,
                            sort_mode=args.sort_mode,
                            include_internal=args.show_internal)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[OK] Generated {args.output} (issues={len(issues)})")


if __name__ == "__main__":
    main()
    