#!/usr/bin/env python3
"""Validate bounded DXVK disassembly evidence windows without promoting semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalize_bytes(value: str) -> str:
    return " ".join(value.lower().split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--start-rva", required=True)
    parser.add_argument("--end-rva", required=True)
    parser.add_argument("--bytes", required=True)
    args = parser.parse_args()

    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    checks = {
        "start_rva_matches": str(evidence.get("proof_start_rva", "")).lower() == args.start_rva.lower(),
        "end_rva_matches": str(evidence.get("proof_end_rva", "")).lower() == args.end_rva.lower(),
        "overlap_bytes_matches": normalize_bytes(str(evidence.get("overlap_bytes", ""))) == normalize_bytes(args.bytes),
        "runtime_validation": evidence.get("runtime_validation") == "UNTESTED",
    }

    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
