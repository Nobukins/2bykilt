#!/usr/bin/env python3
"""
Generate a Mermaid dependency graph from ISSUE_DEPENDENCIES.yml.

Default behavior (CHANGED):
    - Legend is now INCLUDED by default (unless --no-legend given).
    - Previously you needed --legend to include it.

Usage examples:
  python scripts/gen_mermaid.py docs/roadmap/ISSUE_DEPENDENCIES.yml > docs/roadmap/DEPENDENCY_GRAPH.md
  python scripts/gen_mermaid.py --no-legend docs/roadmap/ISSUE_DEPENDENCIES.yml > out.md
  python scripts/gen_mermaid.py --raw-mermaid docs/roadmap/ISSUE_DEPENDENCIES.yml > graph.mmd

Notes:
- Edge direction is dependency --> dependent (左が前提 / 右が従属)
- Mermaid classDef syntax: property:value (NOT property=value)
"""
import sys
import yaml
import datetime
from argparse import ArgumentParser
from typing import Dict, Any

RANK_GROUP_PREFIX = "R"

STYLE_CLASSDEFS = {
    "highrisk": "fill:#ffe6e6,stroke:#d40000,stroke-width:2px,color:#000",
    "progress": "fill:#e6f4ff,stroke:#0366d6,stroke-width:2px,color:#000",
}

def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_rank_groups(issues: Dict[str, Any]):
    groups = {}
    for issue_id, meta in issues.items():
        rank = meta.get("critical_path_rank", 1)
        groups.setdefault(rank, []).append(issue_id)
    return dict(sorted(groups.items(), key=lambda x: -x[0]))

def short_label(title: str, max_len=20):
    t = (title or "").replace('"', "'")
    return t if len(t) <= max_len else t[: max_len - 1] + "…"

def render_mermaid(data: Dict[str, Any],
                   show_legend: bool = True,
                   add_code_fence: bool = True,
                   raw_mermaid: bool = False,
                   stable: bool = False) -> str:
    issues = data["issues"]
    summary = data.get("summary", {})
    high_risk = set(summary.get("high_risk", []))
    progress_nodes = {i for i, m in issues.items() if "progress" in m}

    rank_groups = build_rank_groups(issues)
    out = []

    if raw_mermaid:
        out.append("%% Auto-generated dependency graph")
        out.append("%% Edge方向: dependency --> dependent")
        out.append("graph LR")
        out.append("")
        out.append("%% Subgraphs by critical_path_rank (higher = earlier in chain)")
    else:
        if add_code_fence:
            out.append("```mermaid")
        out.append("%% Auto-generated dependency graph")
        ts = "STABLE" if stable else datetime.datetime.now(datetime.UTC).isoformat()
        out.append(f"%% Generated at: {ts}")
        out.append("%% Edge方向: dependency --> dependent")
        out.append("graph LR")
        out.append("")

    for rank, ids in rank_groups.items():
        out.append(f"subgraph {RANK_GROUP_PREFIX}{rank}[Rank {rank}]")
        for iid in sorted(ids, key=lambda s: int(s) if str(s).isdigit() else s):
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

    out.append("")
    out.append("%% Edges (depends --> dependent)")
    for iid, meta in issues.items():
        for dep in meta.get("depends") or []:
            out.append(f"{dep} --> {iid}")

    out.append("")
    out.append("%% Styling definitions (Mermaid syntax uses colon)")
    for cname, style in STYLE_CLASSDEFS.items():
        out.append(f"classDef {cname} {style};")

    out.append("")
    out.append("%% Class assignments")
    if high_risk:
        out.append("class " + ",".join(sorted(high_risk, key=lambda s: int(s) if str(s).isdigit() else s)) + " highrisk;")
    if progress_nodes:
        out.append("class " + ",".join(sorted(progress_nodes, key=lambda s: int(s) if str(s).isdigit() else s)) + " progress;")

    if show_legend:
        out.append("")
        out.append("%% Legend (pseudo nodes)")
        out.append("subgraph Legend[Legend]")
        out.append("  L1[水色: progress付き Issue]")
        out.append("  L2[薄赤: High Risk]")
        out.append('  L3["Edge: 依存(左) → 従属(右)"]')
        out.append("end")
        out.append("style Legend fill:#fafafa,stroke:#ccc,stroke-dasharray:3 3;")

    if (not raw_mermaid) and add_code_fence:
        out.append("```")

    return "\n".join(out) + "\n"

def main():
    parser = ArgumentParser()
    parser.add_argument("yaml_path")
    parser.add_argument("--legend", action="store_true", help="Force include legend in raw mode")
    parser.add_argument("--no-legend", action="store_true", help="Suppress legend output")
    parser.add_argument("--no-fence", action="store_true", help="Do not wrap with ```mermaid fences")
    parser.add_argument("--raw-mermaid", action="store_true", help="Output raw Mermaid (no fences, minimal header)")
    parser.add_argument("--stable", action="store_true", help="Use stable timestamp to enable idempotent diff")
    args = parser.parse_args()

    data = load_yaml(args.yaml_path)
    if args.raw_mermaid:
        show_legend = args.legend and not args.no_legend
    else:
        show_legend = not args.no_legend

    text = render_mermaid(
        data,
        show_legend=show_legend,
        add_code_fence=not args.no_fence and not args.raw_mermaid,
        raw_mermaid=args.raw_mermaid,
        stable=args.stable,
    )
    print(text, end="")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: gen_mermaid.py [--no-legend] [--legend] [--no-fence] [--raw-mermaid] docs/roadmap/ISSUE_DEPENDENCIES.yml", file=sys.stderr)
        sys.exit(1)
    main()
    