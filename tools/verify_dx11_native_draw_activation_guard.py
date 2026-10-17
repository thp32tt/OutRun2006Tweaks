#!/usr/bin/env python3
"""Fail closed if dormant DX11 conversion work accidentally enables native draw routing.

This is a source/static guard for the DX11 conversion lane. Runtime activation remains
separate and requires Quest 3/VDXR evidence; this check only protects the dormant gate.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    (
        ROOT / "src" / "vr" / "d3d11" / "native_backend.cpp",
        r"NativeDrawPathActive",
        "native draw activation symbol must remain explicitly reviewed",
    ),
    (
        ROOT / "src" / "vr" / "d3d11" / "native_backend.hpp",
        r"NativeDrawPathActive",
        "native draw activation declaration must remain present for gate checks",
    ),
]


def main() -> None:
    for path, token, reason in CHECKS:
        if not path.exists():
            raise SystemExit(f"missing DX11 guard input: {path}")
        text = path.read_text(encoding="utf-8")
        if token not in text:
            raise SystemExit(f"DX11 activation guard input drift: {reason}")

    backend = (
        ROOT / "src" / "vr" / "d3d11" / "native_backend.cpp"
    ).read_text(encoding="utf-8")
    active_assignments = re.findall(
        r"NativeDrawPathActive\s*=\s*(true|1)",
        backend,
    )
    if active_assignments:
        raise SystemExit(
            "DX11 dormant activation guard failed: NativeDrawPathActive enabled"
        )

    print("DX11 native draw activation guard: PASS")


if __name__ == "__main__":
    main()
