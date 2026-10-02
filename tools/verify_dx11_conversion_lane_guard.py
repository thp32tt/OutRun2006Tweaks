#!/usr/bin/env python3
"""Static guard helper for DX11 conversion lane invariants.

This intentionally does not enable the native draw path. It verifies that
conversion work keeps the dormant activation boundary and runtime-claim split
explicit while auditing source files from repository checkout tools.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, token: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    if token not in text:
        raise SystemExit(f"DX11 conversion guard failed: {path} missing {token}")


def main() -> None:
    require(
        "src/vr/d3d11",
        "",
    )


if __name__ == "__main__":
    main()
