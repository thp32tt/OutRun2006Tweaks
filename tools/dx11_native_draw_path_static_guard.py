#!/usr/bin/env python3
"""Static guard for DX11 native conversion sources.

Checks source snapshots without requiring a Windows runtime. The analyzer is
intentionally conservative: it reports evidence that needs review rather than
activating any rendering path.
"""

from __future__ import annotations

import argparse
from pathlib import Path


SUSPICIOUS_MARKERS = (
    "NativeDrawPathActive",
    "EnableNativeDrawPath",
    "D3D11_CREATE_DEVICE",
)


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".cpp", ".hpp", ".h", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in SUSPICIOUS_MARKERS:
            if marker in text:
                findings.append(f"{path}:{marker}")
    return sorted(findings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    findings = scan(Path(args.root))
    if findings:
        print("DX11_STATIC_GUARD_FINDINGS")
        print("\n".join(findings))
        return 1
    print("DX11_STATIC_GUARD_CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
