#!/usr/bin/env python3
"""Static DX11 shader interface contract checker.

This offline validator catches accidental activation of incomplete shader-path
metadata before runtime testing. It intentionally does not enable native draw
path behavior; it only verifies evidence files when supplied.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REQUIRED_FIELDS = (
    "schema_version",
    "backend",
    "runtime_validation",
    "activation_allowed",
)


def validate_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid json: {exc}"]

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing field: {field}")

    if data.get("backend") != "DX11":
        errors.append("backend must be DX11")

    if data.get("runtime_validation") != "UNTESTED":
        errors.append("runtime_validation must remain UNTESTED for offline checks")

    if data.get("activation_allowed") is True:
        errors.append("native activation cannot be enabled by static contract")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    errors = validate_manifest(args.manifest)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: DX11 shader interface contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
