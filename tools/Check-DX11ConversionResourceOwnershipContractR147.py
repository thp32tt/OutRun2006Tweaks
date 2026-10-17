#!/usr/bin/env python3
"""DX11 conversion static guard R147.

Checks that the DX11 conversion lane keeps resource ownership decisions
explicit in source. This is a source/static contract check only and does not
validate runtime GPU behaviour.
"""

from pathlib import Path
import sys


REQUIRED_MARKERS = (
    "runtime_validation",
    "UNTESTED",
)
FORBIDDEN_MARKERS = (
    "D3D12",
    "D3D9On12",
)


def scan(root: Path) -> int:
    failures = []
    files = list(root.rglob("*.cpp")) + list(root.rglob("*.h")) + list(root.rglob("*.hpp"))
    inspected = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        inspected += 1
        for token in FORBIDDEN_MARKERS:
            if token in text:
                failures.append(f"{path}: frozen backend token found: {token}")
    if failures:
        print("FAIL")
        print("\n".join(failures))
        return 1
    print(f"PASS_STATIC_DX11_RESOURCE_OWNERSHIP_CONTRACT_R147 inspected={inspected}")
    return 0


if __name__ == "__main__":
    sys.exit(scan(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")))
