#!/usr/bin/env python3
"""Static DX11 census contract guard for conversion-lane diagnostics.

Repository-only validation. This guard verifies that census telemetry keeps the
identity fields required for offline analysis. It does not enable native routing
and does not claim Quest 3/VDXR runtime validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    census = (
        ROOT / "src" / "vr" / "d3d11" / "runtime_census.cpp"
    ).read_text(encoding="utf-8")

    required = [
        "runtime census",
        "hash_mix",
        "signature.",
    ]
    missing = [token for token in required if token not in census]
    if missing:
        raise SystemExit(
            "DX11 census identity contract drift: " + ", ".join(missing)
        )

    print("DX11 census identity contract R131: PASS")


if __name__ == "__main__":
    main()
