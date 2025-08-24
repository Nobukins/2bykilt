#!/usr/bin/env python3
"""
Generate a Mermaid dependency graph from ISSUE_DEPENDENCIES.yml.

Usage:
  python scripts/gen_mermaid.py docs/roadmap/ISSUE_DEPENDENCIES.yml > docs/roadmap/DEPENDENCY_GRAPH.mmd
  python scripts/gen_mermaid.py --legend docs/roadmap/ISSUE_DEPENDENCIES.yml > graph.mmd

Notes:
- Mermaid classDef syntax: property:value (NOT property=value)
- Edge direction: dependency --> dependent
"""

import sys
import yaml
import datetime
from argparse import ArgumentParser

RANK_GROUP_PREFIX = "R"

STYLE_CLASSDEFS = {
    "highrisk": "fill:#ffe6e6,stroke:#d40000,stroke-width:2px,color:#000",
    "progress": "fill:#e6f4ff,stroke:#0366d6,stroke-width:2px,color:#000",
}

def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_rank_groups(issues: dict):
    groups = {}
    for issue_id, meta in issues.items():
        rank = meta.get("critical_path_rank", 1)
        groups.setdefault(rank, []).append(issue_id)
    # Sort ranks high->low so earlier ranks appear left-ish in LR layout
    return dict(sorted(groups.items(), key=lambda x: -x[0]))

def short_label(title: str, max_len=16):
    t = title.replace('"', "'")
    return t if len(t) <= max_len else t[: max_len - 1] + "…"

def render_mermaid(data: dict, show_legend: bool = False) -> str:
    issues = data["issues"]
    high_risk = set(data.get("summary", {}).get("high_risk", []))
    progress_nodes = {i for i, m in issues.items() if "progress" in m}

    rank_groups = build_rank_groups(issues)

    out = []
    out.append("graph LR")
    out.append(f"%% Generated: {datetime.datetime.utcnow().isoformat()}Z")
    out.append("%% Edge direction: dependency --> dependent")

    # Rank subgraphs
    for rank, ids in rank_groups.items():
        out.append(f"subgraph {RANK_GROUP_PREFIX}{rank}[Rank {rank}]")
        for iid in sorted(ids, key=lambda s: int(s) if s.isdigit() else s):
            meta = issues[iid]
            title = meta.get("title", "")
            label = short_label(title)
            extra = []
            if iid in progress_nodes:
                prog = meta.get("progress", {})
                coverage = prog.get("coverage")
                if coverage:
                    extra.append(coverage)
            full_label = f"{iid} {label}"
            if extra:
                full_label += f" ({', '.join(extra)})"
            out.append(f'  {iid}["{full_label}"]')
        out.append("end")

    # Edges
    out.append("\n%% Edges (depends --> dependent)")
    for iid, meta in issues.items():
        depends = meta.get("depends") or []
        for dep in depends:
            out.append(f"{dep} --> {iid}")

    # Styling
    out.append("\n%% Styling definitions")
    for cname, style in STYLE_CLASSDEFS.items():
        out.append(f"classDef {cname} {style};")

    out.append("\n%% Class assignments")
    if high_risk:
        out.append("class " + ",".join(sorted(high_risk)) + " highrisk;")
    if progress_nodes:
        out.append("class " + ",".join(sorted(progress_nodes, key=lambda s: int(s))) + " progress;")

    # Legend
    if show_legend:
        out.append("\n%% Legend (pseudo nodes)")
        out.append("subgraph Legend[Legend]")
        out.append("  L1[水色: progress付き Issue]")
        out.append("  L2[薄赤: High Risk]")
        out.append('  L3["Edge: 依存(左) → 従属(右)"]')
        out.append("end")
        out.append("style Legend fill:#fafafa,stroke:#ccc,stroke-dasharray:3 3;")

    return "\n".join(out)

def main():
    parser = ArgumentParser()
    parser.add_argument("yaml_path")
    parser.add_argument("--legend", action="store_true", help="Include legend subgraph")
    args = parser.parse_args()

    data = load_yaml(args.yaml_path)
    print(render_mermaid(data, show_legend=args.legend))

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: gen_mermaid.py [--legend] docs/roadmap/ISSUE_DEPENDENCIES.yml", file=sys.stderr)
        sys.exit(1)
    main()