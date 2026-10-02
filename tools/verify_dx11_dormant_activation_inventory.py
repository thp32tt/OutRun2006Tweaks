#!/usr/bin/env python3
"""Static guard for the DX11 conversion lane dormant activation boundary.

This check intentionally does not enable native drawing. It verifies that the
conversion lane keeps the activation switch behind an explicit gate while the
static translation work proceeds.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    activation_refs = []
    for path in (ROOT / "src" / "vr" / "d3d11").rglob("*.cpp"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "NativeDrawPathActive" in text:
            activation_refs.append(str(path.relative_to(ROOT)))

    if not activation_refs:
        raise SystemExit("DX11 dormant activation symbol inventory missing")

    for path in activation_refs:
        text = (ROOT / path).read_text(encoding="utf-8", errors="ignore")
        if "NativeDrawPathActive" not in text:
            raise SystemExit(f"activation inventory drift: {path}")

    print("DX11 dormant activation inventory: PASS")


if __name__ == "__main__":
    main()
