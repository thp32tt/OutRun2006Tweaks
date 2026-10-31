#!/usr/bin/env python3
"""Static integrity guard for the DX11 native conversion lane.

This check intentionally does not activate the native draw path.  It verifies
that conversion work remains behind the explicit gate and that the branch does
not accidentally drift into runtime promotion through config/source changes.
"""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_DISABLED_TOKENS = (
    "NativeDrawPathActive=true",
    "native_draw_path_active = true",
)

FORBIDDEN_AUTOPROMOTION_TOKENS = (
    "auto_enable_native_draw",
    "force_native_draw_activation",
)


def scan(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for token in REQUIRED_DISABLED_TOKENS:
            if token in text:
                findings.append(f"native activation enabled token found: {path}:{token}")
        for token in FORBIDDEN_AUTOPROMOTION_TOKENS:
            if token in text:
                findings.append(f"forbidden promotion path found: {path}:{token}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(".")])
    args = parser.parse_args()

    files = []
    for root in args.paths:
        if root.is_file():
            files.append(root)
        elif root.exists():
            files.extend(p for p in root.rglob("*") if p.is_file())

    findings = scan(files)
    if findings:
        for finding in findings:
            print(finding)
        return 1

    print("DX11_CONVERSION_LANE_INTEGRITY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
