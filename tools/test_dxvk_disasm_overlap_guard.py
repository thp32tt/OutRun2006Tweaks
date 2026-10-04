#!/usr/bin/env python3
"""Regression checks for DXVK disassembly overlap validation."""

from __future__ import annotations

from pathlib import Path

from dxvk_disasm_overlap_guard import validate_window


def main() -> int:
    assert validate_window(bytes.fromhex("66 0f 54 1d 20 91 61 aa"), bytes.fromhex("66 0f 54 1d 20 91 61"))["overlap_present"]
    assert not validate_window(bytes.fromhex("90 90 90"), bytes.fromhex("66 0f"))["overlap_present"]
    print("DXVK overlap guard regression: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
