#!/usr/bin/env python3
"""Static DX11 conversion lane audit helper.

This tool intentionally performs source-only checks. It does not enable the
native draw path and it does not claim runtime validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_GUARDS = (
    "NativeDrawPathActive",
    "D3D11",
)



def audit_tree(root: Path) -> int:
    text_files = [p for p in root.rglob("*") if p.is_file() and p.suffix in {".cpp", ".hpp", ".h", ".md", ".json"}]
    corpus = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore") for p in text_files
    )

    missing = [token for token in REQUIRED_GUARDS if token not in corpus]
    if missing:
        print("DX11_STATIC_AUDIT=FAIL")
        print("MISSING=" + ",".join(missing))
        return 1

    print("DX11_STATIC_AUDIT=PASS")
    print(f"FILES_SCANNED={len(text_files)}")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    raise SystemExit(audit_tree(Path(args.root)))
