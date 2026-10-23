#!/usr/bin/env python3
"""Static DX11 conversion guard for shader input binding declarations.

This check is intentionally offline. It does not enable native draw activation;
it only catches incomplete source contracts before a runtime test.
"""
from pathlib import Path
import sys

REQUIRED_MARKERS = (
    "POSITION",
    "TEXCOORD",
)


def check_source(text: str) -> list[str]:
    errors = []
    lowered = text.lower()
    if "d3d11" not in lowered:
        errors.append("missing d3d11 implementation marker")
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            errors.append(f"missing input semantic marker: {marker}")
    if "NativeDrawPathActive = true" in text:
        errors.append("native draw activation must remain disabled")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: Check-DX11ShaderInputBindingContract.py <source-file>")
        return 2
    path = Path(sys.argv[1])
    errors = check_source(path.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: DX11 shader input binding contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
