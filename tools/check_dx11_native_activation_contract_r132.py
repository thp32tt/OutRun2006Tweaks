#!/usr/bin/env python3
"""Static DX11 conversion contract check R132.

Purpose: keep the native DX11 activation boundary explicit while conversion work
continues. This check is repository-only and does not claim runtime validation.
"""
from pathlib import Path
import sys


FORBIDDEN_ACTIVATION_TOKENS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
    "native_draw_path_activation_changed=true",
)
REQUIRED_CONTRACT_TOKENS = (
    "NativeDrawPath",
    "DX11",
)


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".cpp", ".hpp", ".h", ".py", ".json", ".md"}:
            yield path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    hits = []
    saw_contract = False

    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if all(token in text for token in REQUIRED_CONTRACT_TOKENS):
            saw_contract = True
        for token in FORBIDDEN_ACTIVATION_TOKENS:
            if token in text:
                hits.append((path, token))

    if not saw_contract:
        print("FAIL: DX11 contract markers not found")
        return 1

    if hits:
        print("FAIL: native DX11 activation contract violation")
        for path, token in hits:
            print(f"{path}: {token}")
        return 1

    print("PASS: DX11 native activation contract R132")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
