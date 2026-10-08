#!/usr/bin/env python3
"""Fail-closed verifier for canonical DXVK disassembly evidence windows.

This tool intentionally verifies byte-window provenance only. It does not infer
function meaning or runtime behavior from a partial disassembly window.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, help="JSON evidence file")
    parser.add_argument("--start-rva", required=True)
    parser.add_argument("--end-rva", required=True)
    args = parser.parse_args()

    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    start = str(evidence.get("proof_start_rva") or evidence.get("provenance_start_rva") or "").lower()
    end = str(evidence.get("proof_end_rva") or evidence.get("probe_end_rva") or "").lower()

    requested_start = args.start_rva.lower()
    requested_end = args.end_rva.lower()

    if start != requested_start or end != requested_end:
        raise SystemExit(
            "DXVK disassembly window mismatch: evidence provenance does not "
            "match the requested exact RVA window"
        )

    if evidence.get("capture_edge_matches") is False or evidence.get("overlap_matches") is False:
        raise SystemExit("DXVK disassembly overlap/capture edge verification failed")

    print(
        "DXVK disassembly window verified: "
        f"{requested_start}..{requested_end}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
