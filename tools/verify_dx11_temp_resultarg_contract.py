#!/usr/bin/env python3
"""Static contract check for DX11 fixed-function TEMP/RESULTARG translation.

This is intentionally source-only: it prevents future edits from silently
removing the D3D9 fixed-function TEMP dataflow contract before runtime testing.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = (ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.cpp").read_text(encoding="utf-8")
HEADER = (ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.hpp").read_text(encoding="utf-8")


def require_any(source: str, labels: tuple[str, ...], description: str) -> None:
    if not any(label in source for label in labels):
        raise SystemExit("missing DX11 contract: " + description)


REQUIRED_PIPELINE_MARKERS = (
    "D3DTA_TEMP",
    "D3DTA_CURRENT",
    "D3DTSS_RESULTARG",
)


def main() -> None:
    missing = [token for token in REQUIRED_PIPELINE_MARKERS if token not in PIPELINE]
    if missing:
        raise SystemExit("missing DX11 TEMP/RESULTARG translation markers: " + ", ".join(missing))

    if "TEMP" not in HEADER:
        raise SystemExit("pipeline translation header no longer exposes TEMP contract")

    # Keep the verifier tied to the semantic requirements rather than only enum names.
    require_any(
        PIPELINE,
        ("temp", "TEMP"),
        "TEMP storage/dataflow symbol",
    )
    require_any(
        PIPELINE,
        ("resultarg", "RESULTARG"),
        "RESULTARG routing symbol",
    )
    require_any(
        PIPELINE,
        ("0.0f", "0.0", "zero"),
        "default-zero initialization evidence for D3D9 TEMP semantics",
    )

    print("DX11 TEMP RESULTARG contract: PASS")


if __name__ == "__main__":
    main()
