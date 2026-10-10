#!/usr/bin/env python3
"""Static guard for the DX11 conversion lane.

Ensures source/configuration evidence does not accidentally enable the native
DX11 draw path while conversion semantics are still gated by runtime evidence.
This is a repository-only check and does not claim Quest 3/VDXR validation.
"""

from pathlib import Path
import sys


FORBIDDEN = (
    "NativeDrawPathActive=true",
    "native_draw_path_active=true",
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "OutRun2006Tweaks.ini",
        root / "src",
    ]

    scanned = []
    for item in candidates:
        if item.is_file():
            scanned.append(item)
        elif item.is_dir():
            scanned.extend(item.rglob("*.cpp"))
            scanned.extend(item.rglob("*.hpp"))
            scanned.extend(item.rglob("*.ini"))

    violations = []
    for path in scanned:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for token in FORBIDDEN:
            if token in text:
                violations.append(f"{path}: {token}")

    if violations:
        print("DX11 dormant activation guard failed")
        print("\n".join(violations))
        return 1

    print(f"DX11 dormant activation guard passed ({len(scanned)} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
