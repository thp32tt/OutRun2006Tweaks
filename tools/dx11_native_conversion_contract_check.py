#!/usr/bin/env python3
"""Static contract checks for the DX11 native conversion lane.

This tool intentionally performs repository-source checks only. It does not
claim D3D11 runtime or Quest 3/VDXR validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REQUIRED_MARKERS = (
    "NativeDrawPathActive",
    "RUNTIME_VALIDATION",
)



def check_tree(root: Path) -> int:
    missing = []
    files = list(root.rglob("*.cpp")) + list(root.rglob("*.hpp")) + list(root.rglob("*.h"))
    text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore") for p in files
    )
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            missing.append(marker)

    if missing:
        print("DX11_CONTRACT_FAIL missing=" + ",".join(missing))
        return 1

    print("DX11_CONTRACT_PASS scanned_files=" + str(len(files)))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    sys.exit(check_tree(Path(args.root)))
