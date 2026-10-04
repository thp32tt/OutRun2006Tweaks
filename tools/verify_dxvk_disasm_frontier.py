#!/usr/bin/env python3
"""Validate a bounded DXVK disassembly frontier manifest.

This is a static-only guard: it verifies that recorded provenance windows do
not silently regress or claim a runtime semantic interpretation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HEX_BYTES = re.compile(r"^(?:[0-9a-fA-F]{2})(?: [0-9a-fA-F]{2})*$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    start = data.get("proof_start_rva") or data.get("provenance_start_rva")
    end = data.get("proof_end_rva") or data.get("probe_end_rva")
    runtime = data.get("runtime_validation")
    capture_edge = data.get("capture_edge_matches")
    overlap_required = data.get("overlap_required")
    overlap_bytes = data.get("overlap_bytes")

    if not isinstance(start, str) or not isinstance(end, str):
        raise SystemExit("missing exact RVA frontier")
    if runtime != "UNTESTED":
        raise SystemExit("runtime claim must remain UNTESTED")
    if capture_edge is False:
        raise SystemExit("capture edge mismatch")
    if overlap_required is True and not isinstance(overlap_bytes, str):
        raise SystemExit("required overlap evidence missing")
    if isinstance(overlap_bytes, str) and not HEX_BYTES.fullmatch(overlap_bytes.strip()):
        raise SystemExit("invalid overlap byte encoding")

    start_value = int(start, 16)
    end_value = int(end, 16)
    if end_value <= start_value:
        raise SystemExit("invalid decreasing RVA frontier")

    if isinstance(data.get("instruction_count"), int) and data["instruction_count"] <= 0:
        raise SystemExit("invalid empty instruction frontier")

    print(
        "DXVK disassembly frontier verified: "
        f"{start}->{end} runtime={runtime} capture={capture_edge}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
