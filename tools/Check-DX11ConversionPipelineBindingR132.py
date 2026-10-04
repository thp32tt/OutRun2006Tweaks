#!/usr/bin/env python3
"""DX11 conversion static guard for pipeline binding evidence.

This check is intentionally offline. It verifies that a conversion evidence record
keeps resource binding decisions explicit and does not accidentally claim runtime
activation or HMD validation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_KEYS = (
    "lane",
    "runtime_validation",
    "native_draw_path_activation_changed",
    "bindings",
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

    if not isinstance(data["bindings"], list):
        raise SystemExit("bindings must be a list")

    seen = set()
    for item in data["bindings"]:
        if not isinstance(item, dict):
            raise SystemExit("binding entries must be objects")
        if "resource" not in item or "stage" not in item:
            raise SystemExit("binding entries require resource and stage")

        key = (item["resource"], item["stage"])
        if key in seen:
            raise SystemExit("duplicate resource/stage binding evidence")
        seen.add(key)

        if "slot" in item and not isinstance(item["slot"], int):
            raise SystemExit("binding slot must be an integer when present")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    return validate(args.evidence)


if __name__ == "__main__":
    raise SystemExit(main())
