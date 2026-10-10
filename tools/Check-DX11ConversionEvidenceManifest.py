#!/usr/bin/env python3
"""Validate DX11 conversion evidence manifests without requiring runtime hardware.

This intentionally checks repository-side evidence contracts only. It does not
claim Quest 3/VDXR runtime validation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REQUIRED_KEYS = (
    "branch",
    "lane",
    "runtime_validation",
    "independent_static_next_action",
)


def validate(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"INVALID_JSON: {exc}")
        return 2

    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        print("MISSING_KEYS:" + ",".join(missing))
        return 3

    if data.get("lane") != "DX11":
        print("INVALID_LANE")
        return 4

    runtime = str(data.get("runtime_validation", ""))
    if runtime not in {"UNTESTED", "PASSED", "FAILED"}:
        print("INVALID_RUNTIME_VALIDATION")
        return 5

    print("DX11_CONVERSION_EVIDENCE_MANIFEST_OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    return validate(args.manifest)


if __name__ == "__main__":
    sys.exit(main())
