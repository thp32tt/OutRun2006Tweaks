#!/usr/bin/env python3
"""Regression checks for DXVK disassembly evidence boundary validation."""

from __future__ import annotations

import sys

from validate_dxvk_disassembly_overlap import validate_window


def main() -> int:
    valid = {
        "start_rva": "0x00182F7E",
        "probe_end_rva": "0x00182FBE",
        "overlap_bytes": "66 0f 54 1d 20 91 61",
        "predecessor_exact": True,
    }
    assert validate_window(valid) == []

    invalid = dict(valid)
    invalid["predecessor_exact"] = False
    assert "invalid:predecessor_not_exact" in validate_window(invalid)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
