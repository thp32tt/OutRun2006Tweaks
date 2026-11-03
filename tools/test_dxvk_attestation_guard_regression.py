#!/usr/bin/env python3
"""Static regression checks for DXVK provider attestation guard fixtures."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "analyze_dxvk_session.py"


def main() -> int:
    source = ANALYZER.read_text(encoding="utf-8")

    required_guards = [
        "DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID",
        "creation_attestation_ids_valid",
        "ProviderAttestationSequence is process-global and strictly increasing",
        "max(creation_probes, key=lambda probe: probe[\"attestation\"])",
    ]

    missing = [item for item in required_guards if item not in source]
    if missing:
        raise AssertionError(f"missing DXVK attestation guard contract: {missing}")

    print("DXVK attestation guard static regression: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
