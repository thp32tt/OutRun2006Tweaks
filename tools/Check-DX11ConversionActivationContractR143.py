#!/usr/bin/env python3
"""Static guard for DX11 conversion activation contracts.

This check intentionally validates source policy boundaries only. It does not
prove runtime behavior on Quest 3/VDXR hardware.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN = (
    "NativeDrawPathActive=true",
    "ENABLE_NATIVE_DRAW_PATH=1",
)
REQUIRED = (
    "runtime_validation",
    "UNTESTED",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path, help="conversion state or evidence file")
    args = parser.parse_args()

    text = args.state.read_text(encoding="utf-8")
    failures = [token for token in FORBIDDEN if token in text]
    missing = [token for token in REQUIRED if token not in text]

    if failures:
        print("activation boundary violation:", ", ".join(failures))
        return 1
    if missing:
        print("missing runtime evidence markers:", ", ".join(missing))
        return 1

    print("DX11 activation contract: PASS_STATIC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
