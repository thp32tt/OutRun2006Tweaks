#!/usr/bin/env python3
"""
Small offline DX11 conversion-lane static guard.

This checker intentionally does not enable the native draw path. It only verifies
that conversion worktrees keep activation guarded and that known dormant-path
symbols are not accidentally flipped during static edits.
"""
from pathlib import Path
import sys

FORBIDDEN_ENABLE_TOKENS = (
    "NativeDrawPathActive = true",
    "native_draw_path_active = true",
    "ENABLE_NATIVE_DRAW_PATH 1",
)


def check_tree(root: Path) -> int:
    failures = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".cpp", ".hpp", ".h", ".json", ".md", ".txt", ".ini"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for token in FORBIDDEN_ENABLE_TOKENS:
            if token in text:
                failures.append(f"{path}: {token}")

    if failures:
        print("DX11_STATIC_CONTRACT_FAIL")
        print("\n".join(failures))
        return 1

    print("DX11_STATIC_CONTRACT_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(check_tree(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
