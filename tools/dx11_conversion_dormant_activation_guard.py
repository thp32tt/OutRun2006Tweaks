#!/usr/bin/env python3
"""Static guard for DX11 conversion lane activation boundaries.

This intentionally does not inspect runtime state. It verifies that source/config
artifacts keep the native draw activation switch in a disabled state unless an
explicit evidence token is supplied by a future validation flow.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN_ACTIVE_MARKERS = (
    "NativeDrawPathActive=true",
    "NATIVE_DRAW_PATH_ACTIVE=1",
    "DX11_NATIVE_DRAW_ENABLED=1",
)


def validate(path: Path, allow_activation_token: bool) -> int:
    text = path.read_text(encoding="utf-8")
    failures = [m for m in FORBIDDEN_ACTIVE_MARKERS if m in text]
    if failures and not allow_activation_token:
        for item in failures:
            print(f"FAIL: forbidden dormant-boundary activation marker: {item}")
        return 1

    print("PASS: DX11 dormant activation boundary preserved")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument(
        "--evidence-token",
        action="store_true",
        help="Reserved for a future evidence-gated activation workflow.",
    )
    args = parser.parse_args()
    return validate(args.file, args.evidence_token)


if __name__ == "__main__":
    raise SystemExit(main())
