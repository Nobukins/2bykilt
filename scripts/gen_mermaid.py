#!/usr/bin/env python3
"""
Generate a Mermaid dependency graph from ISSUE_DEPENDENCIES.yml.

Usage (Markdown with code fence, default):
  python scripts/gen_mermaid.py docs/roadmap/ISSUE_DEPENDENCIES.yml > docs/roadmap/DEPENDENCY_GRAPH.md

Raw Mermaid (.mmd) without code fences:
  python scripts/gen_mermaid.py --raw-mermaid docs/roadmap/ISSUE_DEPENDENCIES.yml > graph.mmd

Include legend:
  python scripts/gen_mermaid.py --legend docs/roadmap/ISSUE_DEPENDENCIES.yml

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
    # Higher rank first (視覚的に左寄せになることを期待)
    return dict(sorted(groups.items(), key=lambda x: -x[0]))

def short_label(title: str, max_len=20):
    t = (title or "").replace('"', "'")
    return t if len(t) <= max_len else t[: max_len - 1] + "…"

def render_mermaid(data: Dict[str, Any],
                   show_legend: bool = False,
                   add_code_fence: bool = True,
                   raw_mermaid: bool = False) -> str:
    """
    add_code_fence: Markdown ```mermaid フェンスを付与する (raw_mermaid=True の場合は強制無効)
    raw_mermaid: 純粋な Mermaid (先頭コメント最小限 / フェンス無し) を出したい場合
    """
    issues = data["issues"]
    high_risk = set(data.get("summary", {}).get("high_risk", []))
    progress_nodes = {i for i, m in issues.items() if "progress" in m}

    rank_groups = build_rank_groups(issues)

    out = []

    if raw_mermaid:
        # 最小構成: オリジナル期待行を出したいが code fence は不要
        out.append("%% Auto-generated dependency graph")
        out.append("%% Edge方向: dependency --> dependent")
        out.append("graph LR")
        out.append("")
        out.append("%% Subgraphs by critical_path_rank (higher = earlier in chain)")
    else:
        if add_code_fence:
            out.append("```mermaid")
        out.append("%% Auto-generated dependency graph")
        out.append("%% Edge方向: dependency --> dependent")
        out.append("graph LR")
        out.append("")
        out.append("%% Subgraphs by critical_path_rank (higher = earlier in chain)")
        out.append(f"%% Generated: {datetime.datetime.utcnow().isoformat()}Z")

    # Rank subgraphs
    for rank, ids in rank_groups.items():
        out.append(f"subgraph {RANK_GROUP_PREFIX}{rank}[Rank {rank}]")
        # 数字としてソート (非数字混在時は文字列)
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
    out.append("")
    out.append("%% Edges (depends --> dependent)")
    for iid, meta in issues.items():
        depends = meta.get("depends") or []
        for dep in depends:
            out.append(f"{dep} --> {iid}")

    # Styling
    out.append("")
    out.append("%% Styling definitions (Mermaid syntax uses colon)")
    for cname, style in STYLE_CLASSDEFS.items():
        out.append(f"classDef {cname} {style};")

    out.append("")
    out.append("%% Class assignments")
    if high_risk:
        out.append("class " + ",".join(sorted(high_risk, key=lambda s: int(s) if s.isdigit() else s)) + " highrisk;")
    if progress_nodes:
        out.append("class " + ",".join(sorted(progress_nodes, key=lambda s: int(s) if s.isdigit() else s)) + " progress;")

    # Legend
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
    parser.add_argument("--legend", action="store_true", help="Include legend subgraph")
    parser.add_argument("--no-fence", action="store_true", help="(Markdownモード時) ```mermaid フェンスを出力しない")
    parser.add_argument("--raw-mermaid", action="store_true", help="純粋な .mmd 用出力 (フェンス/追加コメント最小)")
    args = parser.parse_args()

    data = load_yaml(args.yaml_path)
    text = render_mermaid(
        data,
        show_legend=args.legend,
        add_code_fence=not args.no_fence,
        raw_mermaid=args.raw_mermaid,
    )
    print(text, end="")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: gen_mermaid.py [--legend] [--no-fence] [--raw-mermaid] docs/roadmap/ISSUE_DEPENDENCIES.yml", file=sys.stderr)
        sys.exit(1)
    main()
    