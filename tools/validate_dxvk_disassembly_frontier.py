#!/usr/bin/env python3
"""Static guard for DXVK disassembly frontier evidence.

This intentionally does not decode instructions or promote runtime semantics.
It only validates the immutable shape of a captured continuation window:
- RVA range ordering
- overlap bytes retained from the previous capture edge
- explicit UNTESTED runtime state

Used by GitHub-only conversion evidence checks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path



def validate(record: dict) -> list[str]:
    errors: list[str] = []
    start = record.get("provenance_start_rva")
    end = record.get("probe_end_rva")
    if not isinstance(start, str) or not isinstance(end, str):
        errors.append("missing_rva_range")
    else:
        if int(end, 16) <= int(start, 16):
            errors.append("invalid_rva_range")

    if record.get("overlap_bytes") in (None, ""):
        errors.append("missing_overlap_bytes")

    if record.get("runtime_validation") != "UNTESTED":
        errors.append("runtime_claim_not_allowed")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()

    data = json.loads(args.record.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}))
        return 1

    print(json.dumps({"status": "PASS", "runtime_validation": "UNTESTED"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
