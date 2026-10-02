#!/usr/bin/env python3
"""Static DX11 conversion source-boundary checker.

Checks that the DX11 lane keeps activation disabled while requiring the
conversion evidence markers needed for offline review. This does not prove
Quest 3/VDXR runtime behavior.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN = (
    "NativeDrawPathActive=true",
    "ENABLE_NATIVE_DRAW_PATH=1",
    "native_draw_path_activation=true",
)
REQUIRED = (
    "runtime_validation",
    "UNTESTED",
)


def check_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    compact = text.replace(" ", "").replace("\t", "")
    bad = [token for token in FORBIDDEN if token.replace(" ", "") in compact]
    missing = [token for token in REQUIRED if token not in text]
    if bad or missing:
        if bad:
            print("FORBIDDEN=" + ",".join(bad))
        if missing:
            print("MISSING=" + ",".join(missing))
        return 1
    print("DX11_SOURCE_BOUNDARY=PASS_STATIC")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    args = parser.parse_args()
    raise SystemExit(check_file(args.state))
