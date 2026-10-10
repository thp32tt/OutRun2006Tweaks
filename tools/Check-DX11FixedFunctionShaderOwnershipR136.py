#!/usr/bin/env python3
"""Static guard for the DX11 fixed-function shader ownership bridge.

This check intentionally does not enable the native draw path. It verifies that
shader-owned fixed-function state remains behind the observed/generated shader
boundary introduced by the conversion lane.
"""

from pathlib import Path
import sys


REQUIRED = {
    "src/vr/d3d11/fixed_function_pipeline.hpp": [
        "fixedFunctionObserved",
        "pixelShader.generated()",
        "alpha_test_transfer_allowed",
    ],
    "src/vr/d3d11/fixed_function_pipeline.cpp": [
        "if (!fixedFunctionObserved)",
        "if (!out.pixelShader.generated())",
        "alphaTestOwnedByPixelShader = true",
    ],
}


def main(root: Path) -> int:
    for rel, needles in REQUIRED.items():
        text = (root / rel).read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                print(f"missing: {rel}: {needle}")
                return 1

    print("DX11 fixed-function shader ownership guard: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(__file__).resolve().parents[1]))
