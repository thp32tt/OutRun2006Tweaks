#!/usr/bin/env python3
"""DX11 conversion static guard for shader constant evidence.

The guard keeps offline evidence honest while dormant DX11 activation remains
protected. It validates constant mapping records without requiring a local GPU
or runtime execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_KEYS = (
    "lane",
    "runtime_validation",
    "native_draw_path_activation_changed",
    "constants",
)


def validate(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))

    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise SystemExit(f"missing evidence keys: {', '.join(missing)}")

    if data["lane"] != "DX11":
        raise SystemExit("evidence lane must remain DX11")

    if data["runtime_validation"] != "UNTESTED":
        raise SystemExit("static evidence cannot claim runtime validation")

    if data["native_draw_path_activation_changed"]:
        raise SystemExit("static evidence cannot enable native draw activation")

    if not isinstance(data["constants"], list):
        raise SystemExit("constants must be a list")

    seen = set()
    for item in data["constants"]:
        if not isinstance(item, dict):
            raise SystemExit("constant entries must be objects")
        if "name" not in item or "source" not in item:
            raise SystemExit("constant entries require name and source")
        if item["name"] in seen:
            raise SystemExit("duplicate constant evidence name")
        seen.add(item["name"])

        if "slot" in item and not isinstance(item["slot"], int):
            raise SystemExit("constant slot must be an integer when present")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    return validate(args.evidence)


if __name__ == "__main__":
    raise SystemExit(main())
