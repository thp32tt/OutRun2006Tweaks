#!/usr/bin/env python3
"""DX11 conversion activation boundary guard.

Checks that static conversion evidence does not accidentally turn the dormant
native draw path into an active runtime path.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_KEYS = (
    "lane",
    "runtime_validation",
    "native_draw_path_activation_changed",
    "activation_boundary",
)


def check_manifest(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise SystemExit(f"missing manifest keys: {', '.join(missing)}")
    if data["lane"] != "DX11":
        raise SystemExit("activation guard requires DX11 lane")
    if data["runtime_validation"] != "UNTESTED":
        raise SystemExit("static guard cannot claim runtime validation")
    if data["native_draw_path_activation_changed"]:
        raise SystemExit("static conversion evidence cannot activate native draw path")
    if data["activation_boundary"] != "DORMANT":
        raise SystemExit("activation boundary must remain dormant")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    return check_manifest(args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
