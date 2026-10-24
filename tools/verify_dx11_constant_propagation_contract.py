#!/usr/bin/env python3
"""Static guard for DX11 fixed-function semantic preservation.

This verifier intentionally stays offline: it checks source invariants that
must remain true before NativeDrawPathActive can ever be enabled.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def require(path: Path, needles: list[str], errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            errors.append(f"{path.relative_to(ROOT)} missing: {needle}")


def main() -> int:
    errors: list[str] = []

    translation = ROOT / "src/vr/d3d11/pipeline_translation.cpp"
    require(
        translation,
        [
            "D3DTA_TEMP",
            "D3DTSS_RESULTARG",
        ],
        errors,
    )

    semantics = ROOT / "tools/dx11_fixed_function_shader_semantics.cpp"
    require(
        semantics,
        [
            "TEMP",
            "default",
        ],
        errors,
    )

    if errors:
        for error in errors:
            print(error)
        return 1

    print("DX11_CONSTANT_PROPAGATION_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
