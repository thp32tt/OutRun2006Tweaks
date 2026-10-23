#!/usr/bin/env python3
"""DX11 conversion static guard R202.

Verifies that the dormant fixed-function TEMP semantic bridge remains wired
into the DX11 translation source after the R201 correction. This is a source
contract check only and does not claim GPU/runtime validation.
"""

from pathlib import Path
import sys


REQUIRED_TOKENS = (
    "D3DTA_TEMP",
    "D3DTSS_RESULTARG",
    "tempRegister",
    "NativeDrawPathActive",
)

FORBIDDEN_TOKENS = (
    "D3DTA_TEMP = 1",
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
)


def scan(root: Path) -> int:
    source = root / "src" / "vr" / "d3d11" / "pipeline_translation.cpp"
    if not source.exists():
        print("FAIL missing DX11 translation source")
        return 1

    text = source.read_text(encoding="utf-8", errors="ignore")
    failures = []

    for token in REQUIRED_TOKENS:
        if token not in text:
            failures.append(f"missing required token: {token}")

    for token in FORBIDDEN_TOKENS:
        if token in text:
            failures.append(f"forbidden activation token: {token}")

    if failures:
        print("FAIL")
        print("\n".join(failures))
        return 1

    print("PASS_STATIC_DX11_TEMP_SEMANTIC_CONTRACT_R202")
    return 0


if __name__ == "__main__":
    sys.exit(scan(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")))
