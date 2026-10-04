#!/usr/bin/env python3
"""DX11 conversion static guard R148.

Ensures the conversion lane keeps runtime activation isolated from the
source-only conversion work. This guard is intentionally static and does not
claim Quest 3/VDXR runtime validation.
"""

from pathlib import Path
import sys


FORBIDDEN_RUNTIME_ENABLE = (
    "NativeDrawPathActive=true",
    "native_draw_path_active = true",
    "ENABLE_NATIVE_DRAW_PATH=1",
)

REQUIRED_SAFETY_MARKERS = (
    "UNTESTED",
    "runtime_validation",
)


def scan(root: Path) -> int:
    failures = []
    inspected = 0
    files = list(root.rglob("*.py")) + list(root.rglob("*.json")) + list(root.rglob("*.md"))
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        inspected += 1
        for token in FORBIDDEN_RUNTIME_ENABLE:
            if token in text:
                failures.append(f"{path}: forbidden runtime activation marker: {token}")

    if failures:
        print("FAIL")
        print("\n".join(failures))
        return 1

    print(f"PASS_STATIC_DX11_RUNTIME_ACTIVATION_ISOLATION_R148 inspected={inspected}")
    return 0


if __name__ == "__main__":
    sys.exit(scan(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")))
