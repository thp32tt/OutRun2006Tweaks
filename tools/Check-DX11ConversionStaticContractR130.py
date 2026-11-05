#!/usr/bin/env python3
"""DX11 conversion static guard for fixed-function handoff artifacts.

This offline check intentionally does not enable the native draw path.  It verifies
that conversion evidence and source contracts keep activation boundaries explicit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_KEYS = (
    "branch",
    "lane",
    "runtime_validation",
    "native_draw_path_activation_changed",
)


def check_manifest(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise SystemExit(f"missing manifest keys: {', '.join(missing)}")
    if data["lane"] != "DX11":
        raise SystemExit("manifest lane must remain DX11")
    if data["runtime_validation"] != "UNTESTED":
        raise SystemExit("offline guard cannot claim runtime validation")
    if data["native_draw_path_activation_changed"]:
        raise SystemExit("activation boundary changed by static-only transaction")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    return check_manifest(args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
