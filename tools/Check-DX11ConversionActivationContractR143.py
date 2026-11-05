#!/usr/bin/env python3
"""Static guard for DX11 conversion activation contracts.

This check validates source policy boundaries only. It does not prove runtime
behavior on Quest 3/VDXR hardware.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


FORBIDDEN = (
    "NativeDrawPathActive=true",
    "ENABLE_NATIVE_DRAW_PATH=1",
    "native_draw_path_activation=true",
    "activate_native_draw_path: true",
)
REQUIRED = (
    "runtime_validation",
    "UNTESTED",
)


_TRUE_ASSIGNMENT = re.compile(r"(?:native[_-]?draw[_-]?path|NativeDrawPathActive)\s*[:=]\s*true", re.IGNORECASE)


def check_contract(text: str) -> tuple[list[str], list[str]]:
    normalized = text.replace(" ", "").replace("\t", "")
    failures = [token for token in FORBIDDEN if token in normalized]
    if _TRUE_ASSIGNMENT.search(text):
        failures.append("normalized_native_draw_path_true_assignment")
    missing = [token for token in REQUIRED if token not in text]
    return failures, missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path, help="conversion state or evidence file")
    args = parser.parse_args()

    failures, missing = check_contract(args.state.read_text(encoding="utf-8"))

    if failures:
        print("activation boundary violation:", ", ".join(failures))
        return 1
    if missing:
        print("missing runtime evidence markers:", ", ".join(missing))
        return 1

    print("DX11 activation contract: PASS_STATIC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
