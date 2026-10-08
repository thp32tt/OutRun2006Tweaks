#!/usr/bin/env python3
"""Static DXVK disassembly contract guard.

Checks that continuation evidence remains explicit and fail-closed:
- every decode window must declare an origin RVA;
- byte evidence must not be empty;
- semantic labels cannot replace raw decode evidence.

This is intentionally repository-only validation and does not claim runtime proof.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_KEYS = ("rva", "bytes")
FORBIDDEN_KEYS = ("assumed_opcode", "guessed_instruction")


def validate_window(window: dict) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in window:
            errors.append(f"missing:{key}")
    if "bytes" in window and not window["bytes"]:
        errors.append("empty:bytes")
    for key in FORBIDDEN_KEYS:
        if key in window:
            errors.append(f"forbidden:{key}")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_dxvk_decode_contract_guard.py <json>")
        return 2

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    windows = data.get("windows", [])
    errors = [f"window[{i}]:{e}" for i, w in enumerate(windows) for e in validate_window(w)]
    if errors:
        print("FAIL")
        print("\n".join(errors))
        return 1
    print(f"PASS windows={len(windows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
