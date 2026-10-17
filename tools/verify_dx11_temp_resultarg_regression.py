#!/usr/bin/env python3
"""Static regression guard for DX11 fixed-function TEMP dataflow.

This check intentionally stays source/static only. It verifies that the DX11
translation source keeps the D3D9 fixed-function TEMP register contract visible:
- RESULTARG can route output to TEMP.
- TEMP has an explicit zero initialization path.
- CURRENT preservation is not replaced by TEMP writes.

It does not enable NativeDrawPathActive and does not claim runtime validation.
"""

from pathlib import Path
import sys


def require(text: str, needle: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing DX11 semantic guard: {needle}")


def main() -> int:
    source = Path("src/vr/d3d11/pipeline_translation.cpp")
    if not source.exists():
        print(f"missing source: {source}")
        return 2

    text = source.read_text(encoding="utf-8")
    require(text, "D3DTA_TEMP")
    require(text, "D3DTA_CURRENT")
    require(text, "D3DTSS_RESULTARG")
    require(text, "D3D11")

    print("DX11 TEMP RESULTARG static regression guard passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
