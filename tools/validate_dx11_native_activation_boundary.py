#!/usr/bin/env python3
"""Static guard for the DX11 native activation boundary.

This check intentionally does not enable native draw routing. It prevents
future conversion work from silently changing the dormant activation contract
without updating the evidence gate.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REQUIRED_MARKERS = (
    "NativeDrawPath",
    "activation",
    "RUNTIME_VALIDATION",
)

FORBIDDEN_MARKERS = (
    "FORCE_NATIVE_DRAW",
    "ENABLE_NATIVE_DRAW_UNSAFE",
)


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors: list[str] = []

    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            errors.append(f"forbidden activation override marker: {marker}")

    if "NativeDrawPath" in text and "activation" not in text:
        errors.append("NativeDrawPath reference without activation contract")

    if "RUNTIME_VALIDATION=PASS" in text:
        errors.append("runtime validation cannot be asserted by static tooling")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failures = []
    for path in args.paths:
        failures.extend(f"{path}: {item}" for item in check_file(path))

    if failures:
        print("DX11_NATIVE_ACTIVATION_BOUNDARY_FAIL")
        print("\n".join(failures))
        return 1

    print("DX11_NATIVE_ACTIVATION_BOUNDARY_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
