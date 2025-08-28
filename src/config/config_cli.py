"""
Configuration CLI (Issue #65)
Commands:
  bykilt-config show --env <env>
  bykilt-config diff --from <envA> --to <envB> [--json]

Note:
  - show outputs MASKED config (read from effective artifact if present, otherwise regenerates)
  - diff outputs added / removed / changed
Exit codes:
  0 success
  1 error
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .multi_env_loader import load_config, diff_envs, MultiEnvConfigLoader


def _cmd_show(ns: argparse.Namespace) -> int:
    # Load to ensure artifact generation (masked stored there)
    loader = MultiEnvConfigLoader()
    raw_cfg = loader.load(ns.env)
    # Re-mask for stdout (avoid accidental secret exposure)
    masked_cfg, masked_hashes = loader._mask_secrets(raw_cfg)  # type: ignore[attr-defined]
    payload = {
        "env": loader.logical_env,
        "config": masked_cfg,
        "masked_hashes": masked_hashes,
        "warnings": loader.warnings,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _cmd_diff(ns: argparse.Namespace) -> int:
    d = diff_envs(ns.from_env, ns.to_env)
    if ns.json:
        print(json.dumps(d, indent=2, ensure_ascii=False))
        return 0

    if d["added"]:
        print("Added:")
        for k in d["added"]:
            print(f"  + {k}")
    if d["removed"]:
        print("Removed:")
        for k in d["removed"]:
            print(f"  - {k}")
    if d["changed"]:
        print("Changed:")
        for k, ch in d["changed"].items():
            print(f"  * {k}: {d['from']}={ch['from']} -> {d['to']}={ch['to']}")
    if not (d["added"] or d["removed"] or d["changed"]):
        print("No differences.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bykilt-config", description="2bykilt configuration utilities")
    sub = p.add_subparsers(dest="command", required=True)

    sp_show = sub.add_parser("show", help="Show masked effective configuration.")
    sp_show.add_argument("--env", default=None, help="Environment (dev|staging|prod)")
    sp_show.set_defaults(func=_cmd_show)

    sp_diff = sub.add_parser("diff", help="Show differences between environments.")
    sp_diff.add_argument("--from", dest="from_env", required=True, help="Source environment")
    sp_diff.add_argument("--to", dest="to_env", required=True, help="Target environment")
    sp_diff.add_argument("--json", action="store_true", help="JSON output")
    sp_diff.set_defaults(func=_cmd_diff)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
