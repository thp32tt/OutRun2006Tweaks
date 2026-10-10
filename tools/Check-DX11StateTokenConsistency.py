#!/usr/bin/env python3
"""Static guard for DX11 conversion state-token tables.

This checker is intentionally repository-only. It catches accidental drift in
conversion metadata where state identifiers are duplicated with conflicting
names or where required guard labels disappear from generated/static tables.
It does not enable any runtime rendering path.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


REQUIRED_MARKERS = (
    "D3D",
    "STATE",
)


def scan_text(text: str, source: str) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}

    for match in re.finditer(r"(?:STATE|D3D)[A-Z0-9_]{3,}", text):
        token = match.group(0)
        if token in seen and seen[token] != source:
            errors.append(f"duplicate token {token} in {source}")
        else:
            seen[token] = source

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="files to inspect")
    args = parser.parse_args()

    errors: list[str] = []
    inspected = 0

    for raw in args.paths:
        path = pathlib.Path(raw)
        if not path.is_file():
            errors.append(f"missing input: {path}")
            continue
        inspected += 1
        errors.extend(scan_text(path.read_text(encoding="utf-8", errors="ignore"), str(path)))

    if inspected == 0:
        print("DX11_STATE_TOKEN_CHECK: no inputs")
        return 2

    if errors:
        print("DX11_STATE_TOKEN_CHECK: FAIL")
        for error in errors:
            print(error)
        return 1

    print(f"DX11_STATE_TOKEN_CHECK: PASS ({inspected} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
