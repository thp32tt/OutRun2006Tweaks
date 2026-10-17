#!/usr/bin/env python3
"""DX11 static guard for TEMP semantic mapping coverage.

This repository-only probe checks that DX11 translation keeps the fixed-function
TEMP/RESULT argument bridge explicit. It intentionally does not enable native
render routing and does not replace runtime GPU validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    translation = (ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.cpp").read_text(encoding="utf-8")
    header = (ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.hpp").read_text(encoding="utf-8")

    combined = translation + "\n" + header
    required = (
        "D3DTA_TEMP",
        "D3DTA_CURRENT",
        "RESULTARG",
    )
    missing = [token for token in required if token not in combined]
    if missing:
        raise SystemExit("DX11 texture combiner semantic bridge drift: " + ", ".join(missing))

    print("DX11 texture combiner semantic bridge R203: PASS")


if __name__ == "__main__":
    main()
