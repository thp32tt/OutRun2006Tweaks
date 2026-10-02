#!/usr/bin/env python3
"""Static guard for DX11 conversion activation boundaries.

This check intentionally does not enable native draw paths.  It verifies that
conversion evidence/configuration keeps activation opt-in until runtime parity
is available.
"""

from pathlib import Path
import sys


def scan(root: Path) -> int:
    needles = (
        "NativeDrawPathActive = true",
        "NativeDrawPathActive=true",
        "ENABLE_NATIVE_DRAW_PATH=1",
    )
    ignored = {".git", "build", "out"}
    hits = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in ignored for part in path.parts):
            continue
        if path.suffix.lower() not in {".cpp", ".hpp", ".h", ".json", ".md", ".txt", ".py"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for needle in needles:
            if needle in text:
                hits.append(f"{path}: {needle}")
    if hits:
        print("DX11 native draw activation boundary violation:")
        print("\n".join(hits))
        return 1
    print("DX11 native draw activation boundary PASS")
    return 0


if __name__ == "__main__":
    sys.exit(scan(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")))
