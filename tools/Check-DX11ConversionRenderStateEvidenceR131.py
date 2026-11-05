#!/usr/bin/env python3
"""DX11 conversion render-state evidence guard.

This static-only check protects the DX11 conversion lane from accidentally
recording incomplete render-state evidence as activation-ready. Runtime remains
separate and must never be inferred from this check.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_KEYS = (
    "branch",
    "lane",
    "render_state_evidence",
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
    if not data["render_state_evidence"]:
        raise SystemExit("render state evidence is required")
    if data["runtime_validation"] != "UNTESTED":
        raise SystemExit("static guard cannot claim runtime validation")
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
