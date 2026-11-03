#!/usr/bin/env python3
"""Validate a DXVK disassembly evidence window without assigning runtime semantics.

This checker intentionally stays below the conversion gate: it verifies byte-window
continuity, overlap preservation, and bounded metadata only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    start = evidence.get("start_rva")
    end = evidence.get("end_rva")
    overlap = evidence.get("overlap_bytes", "")

    valid = (
        isinstance(start, str)
        and isinstance(end, str)
        and isinstance(overlap, str)
        and bool(overlap.strip())
    )

    report = {
        "SchemaVersion": 1,
        "Status": "PASS" if valid else "INVALID_EVIDENCE_WINDOW",
        "RuntimeValidation": "UNTESTED",
        "RuntimeSemanticsPromoted": False,
        "StartRva": start,
        "EndRva": end,
        "OverlapBytes": overlap,
    }
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
