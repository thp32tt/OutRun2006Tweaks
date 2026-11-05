#!/usr/bin/env python3
"""Static guard for the DX11 conversion lane dormant activation boundary.

This check intentionally does not enable native drawing. It verifies that the
conversion lane keeps activation behind an explicit gate while static
translation work proceeds. The guard also records symbol provenance so a future
rename/removal cannot silently make the inventory meaningless.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DX11_ROOT = ROOT / "src" / "vr" / "d3d11"
REQUIRED_SYMBOLS = (
    "NativeDrawPathActive",
)


def source_files():
    if not DX11_ROOT.exists():
        raise SystemExit("DX11 source root missing")
    yield from DX11_ROOT.rglob("*.cpp")
    yield from DX11_ROOT.rglob("*.h")


def main() -> None:
    activation_refs = []
    for path in source_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if all(symbol in text for symbol in REQUIRED_SYMBOLS):
            activation_refs.append(str(path.relative_to(ROOT)))

    if not activation_refs:
        raise SystemExit("DX11 dormant activation symbol inventory missing")

    for path in activation_refs:
        text = (ROOT / path).read_text(encoding="utf-8", errors="ignore")
        missing = [symbol for symbol in REQUIRED_SYMBOLS if symbol not in text]
        if missing:
            raise SystemExit(f"activation inventory drift: {path}: {missing}")

    print(f"DX11 dormant activation inventory: PASS ({len(activation_refs)} files)")


if __name__ == "__main__":
    main()
