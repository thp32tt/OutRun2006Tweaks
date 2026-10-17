#!/usr/bin/env python3
"""Static DX11 conversion lane hygiene check.

This is a source-only guard. It does not prove runtime behavior.
It verifies that the conversion lane keeps activation gated and avoids
accidental promotion markers in source evidence.
"""

from pathlib import Path
import sys

FORBIDDEN = (
    "NATIVE_DRAW_PATH_ACTIVATED=true",
    "NativeDrawPathActive=true",
    "NativeDrawPathActivation=ENABLED",
)

REQUIRED = (
    "RUNTIME_VALIDATION=UNTESTED",
    "NativeDrawPathActive",
)

EXTENSIONS = {".cpp", ".hpp", ".h", ".json", ".md", ".ps1", ".py"}


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix in EXTENSIONS]

    found_required = set()
    forbidden = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in REQUIRED:
            if marker in text:
                found_required.add(marker)
        for marker in FORBIDDEN:
            if marker in text:
                forbidden.append((str(path.relative_to(root)), marker))

    print("DX11_CONVERSION_SOURCE_HYGIENE")
    print(f"FilesScanned={len(files)}")
    print(f"RequiredMarkers={len(found_required)}/{len(REQUIRED)}")
    print(f"ForbiddenActivationMarkers={len(forbidden)}")

    if found_required != set(REQUIRED):
        raise SystemExit("Missing DX11 dormant activation evidence markers")
    if forbidden:
        raise SystemExit("Forbidden DX11 activation marker detected")

    print("RESULT=PASS_STATIC_SOURCE_HYGIENE")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
