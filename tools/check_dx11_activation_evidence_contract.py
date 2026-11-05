#!/usr/bin/env python3
"""Static DX11 conversion activation evidence contract checker.

This tool intentionally checks source evidence only. It does not enable the
native draw path and it does not claim runtime validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_MARKERS = (
    "NativeDrawPathActive",
    "RUNTIME_VALIDATION=UNTESTED",
)

FORBIDDEN_ACTIVATION_MARKERS = (
    "ForceNativeDrawPath",
    "EnableNativeDrawPathOverride",
)


class ContractError(RuntimeError):
    pass


def check_text(text: str) -> None:
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    if missing:
        raise ContractError("missing required evidence markers: " + ", ".join(missing))

    enabled = [m for m in FORBIDDEN_ACTIVATION_MARKERS if m in text]
    if enabled:
        raise ContractError("unexpected activation bypass markers: " + ", ".join(enabled))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    for path in args.paths:
        check_text(path.read_text(encoding="utf-8"))

    print("DX11_ACTIVATION_EVIDENCE_CONTRACT=PASS")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
