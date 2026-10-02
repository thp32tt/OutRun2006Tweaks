#!/usr/bin/env python3
"""Static contract check for DX11 fixed-function TEMP/RESULTARG translation.

This is intentionally source-only: it prevents future edits from silently
removing the D3D9 fixed-function TEMP dataflow contract before runtime testing.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = (ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.cpp").read_text(encoding="utf-8")
HEADER = (ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.hpp").read_text(encoding="utf-8")

REQUIRED = (
    "D3DTA_TEMP",
    "D3DTA_CURRENT",
    "D3DTSS_RESULTARG",
)


def main() -> None:
    missing = [token for token in REQUIRED if token not in PIPELINE]
    if missing:
        raise SystemExit("missing DX11 TEMP/RESULTARG translation markers: " + ", ".join(missing))

    if "TEMP" not in HEADER:
        raise SystemExit("pipeline translation header no longer exposes TEMP contract")

    print("DX11 TEMP RESULTARG contract: PASS")


if __name__ == "__main__":
    main()
