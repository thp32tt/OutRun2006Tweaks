#!/usr/bin/env python3
"""Static regression checks for DXVK disassembly frontier records.

This test intentionally validates the contract shape rather than runtime behavior.
The conversion lane must not silently promote incomplete disassembly windows into
semantic conclusions.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


REQUIRED_KEYS = {
    "provenance_start_rva",
    "probe_end_rva",
    "overlap_bytes",
    "provenance_status",
}


def validate_frontier(record: dict) -> None:
    missing = REQUIRED_KEYS.difference(record)
    if missing:
        raise AssertionError(f"missing frontier keys: {sorted(missing)}")
    if not str(record["provenance_start_rva"]).startswith("0x"):
        raise AssertionError("frontier start must be an RVA")
    if not str(record["probe_end_rva"]).startswith("0x"):
        raise AssertionError("frontier end must be an RVA")
    if not record["overlap_bytes"]:
        raise AssertionError("partial instruction overlap must be retained")


def main() -> int:
    fixture = {
        "provenance_start_rva": "0x00182F7E",
        "probe_end_rva": "0x00182FBE",
        "overlap_bytes": "66 0f 54 1d 20 91 61",
        "provenance_status": "EXACT_EXE_182F7E_TO_182FBE_PROVENANCE_CAPTURED",
    }
    with tempfile.TemporaryDirectory(prefix="dxvk-frontier-") as temp:
        path = Path(temp) / "frontier.json"
        path.write_text(json.dumps(fixture), encoding="utf-8")
        validate_frontier(json.loads(path.read_text(encoding="utf-8")))
    print("DXVK disassembly frontier contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
