"""
Configuration CLI (Issue #65)

Commands:
  bykilt-config show --env <env> [--debug]
  bykilt-config diff --from <envA> --to <envB> [--json]
  bykilt-config version

Exit codes:
  0 success
  1 usage / other error
  2 broken pipe (suppressed; returns 0 to not confuse piping flows)
"""
from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import version, PackageNotFoundError
from typing import Any

from .multi_env_loader import diff_envs, MultiEnvConfigLoader


def _safe_write_json(obj: Any) -> int:
    try:
        json.dump(obj, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0
    except BrokenPipeError:
        # 下流 (head / grep など) が早期終了した場合: 静かに成功終了扱い
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0


def _cmd_show(ns: argparse.Namespace) -> int:
    loader = MultiEnvConfigLoader()
    raw_cfg = loader.load(ns.env)

    # 再マスク（戻り値は生値ポリシー）
    masked_cfg, masked_hashes = loader._mask_secrets(raw_cfg)  # type: ignore[attr-defined]

    if ns.debug:
        print(
            f"# DEBUG env={loader.logical_env} files={len(loader.files_loaded)} warnings={len(loader.warnings)}",
            file=sys.stderr,
        )
        for f in loader.files_loaded:
            print(f"# DEBUG file_loaded: {f}", file=sys.stderr)
        for w in loader.warnings:
            print(f"# DEBUG warning: {w}", file=sys.stderr)

    if not loader.files_loaded:
        print(
            "# WARNING: no configuration files loaded (check config/<env>/ hierarchy)",
            file=sys.stderr,
        )

    payload = {
        "env": loader.logical_env,
        "config": masked_cfg,
        "masked_hashes": masked_hashes,
        "warnings": loader.warnings,
    }
    return _safe_write_json(payload)


def _cmd_diff(ns: argparse.Namespace) -> int:
    d = diff_envs(ns.from_env, ns.to_env)
    if ns.json:
        return _safe_write_json(d)

    try:
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
        sys.stdout.flush()
        return 0
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0


def _cmd_version(_: argparse.Namespace) -> int:
    try:
        pkg_ver = version("2bykilt")
    except PackageNotFoundError:
        pkg_ver = "unknown"
    payload = {"package": "2bykilt", "version": pkg_ver}
    return _safe_write_json(payload)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bykilt-config", description="2bykilt configuration utilities"
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp_show = sub.add_parser("show", help="Show masked effective configuration.")
    sp_show.add_argument("--env", default=None, help="Environment (dev|staging|prod)")
    sp_show.add_argument(
        "--debug", action="store_true", help="Print debug info to stderr"
    )
    sp_show.set_defaults(func=_cmd_show)

    sp_diff = sub.add_parser("diff", help="Show differences between environments.")
    sp_diff.add_argument("--from", dest="from_env", required=True, help="Source env")
    sp_diff.add_argument("--to", dest="to_env", required=True, help="Target env")
    sp_diff.add_argument("--json", action="store_true", help="JSON output")
    sp_diff.set_defaults(func=_cmd_diff)

    sp_ver = sub.add_parser("version", help="Show CLI / package version.")
    sp_ver.set_defaults(func=_cmd_version)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BrokenPipeError:
        # 最終フォールバック
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0
    except KeyboardInterrupt:
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
