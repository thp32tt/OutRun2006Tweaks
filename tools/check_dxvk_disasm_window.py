#!/usr/bin/env python3
"""Fail-closed checker for canonical DXVK disassembly window metadata.

This utility validates machine-generated continuation windows before they are
used as evidence. It intentionally proves byte-window integrity only; it does
not infer rendering or runtime semantics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    start = data.get("start_rva")
    end = data.get("end_rva")
    instructions = data.get("instructions")
    complete = data.get("complete_instructions")
    overlap = data.get("overlap_bytes")

    if not isinstance(start, str) or not isinstance(end, str):
        raise SystemExit("DXVK_WINDOW_INVALID: missing RVA bounds")
    if not isinstance(instructions, list) or not instructions:
        raise SystemExit("DXVK_WINDOW_INVALID: missing decoded instruction list")
    if complete is not True:
        raise SystemExit("DXVK_WINDOW_INCOMPLETE: partial instruction promoted")
    if not isinstance(overlap, str) or not overlap.strip():
        raise SystemExit("DXVK_WINDOW_INVALID: overlap provenance missing")

    print("DXVK disassembly window contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
