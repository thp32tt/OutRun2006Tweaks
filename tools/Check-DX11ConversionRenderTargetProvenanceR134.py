#!/usr/bin/env python3
"""DX11 conversion static guard for render target provenance evidence.

Keeps offline conversion evidence explicit about resource intent while native
DX11 draw activation remains disabled. This check does not claim runtime or GPU
validation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_KEYS = (
    "lane",
    "runtime_validation",
    "native_draw_path_activation_changed",
    "render_targets",
)

ALLOWED_ROLES = {
    "color",
    "depth",
    "reflection",
    "ui",
    "transport",
}


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

    if not isinstance(data["render_targets"], list):
        raise SystemExit("render_targets must be a list")

    seen = set()
    for target in data["render_targets"]:
        if not isinstance(target, dict):
            raise SystemExit("render target entries must be objects")
        name = target.get("name")
        role = target.get("role")
        if not name or role not in ALLOWED_ROLES:
            raise SystemExit("render target requires valid name and role")
        if name in seen:
            raise SystemExit("duplicate render target evidence name")
        seen.add(name)

        if target.get("fp16_promotion") not in (None, True, False):
            raise SystemExit("fp16_promotion must be boolean when present")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    return validate(args.evidence)


if __name__ == "__main__":
    raise SystemExit(main())
