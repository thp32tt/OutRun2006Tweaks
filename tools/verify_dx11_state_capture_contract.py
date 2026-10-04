#!/usr/bin/env python3
"""Fail closed when DX11 conversion state capture contracts lose D3D9 provenance."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = (ROOT / "src" / "vr" / "d3d11" / "state_translation.cpp").read_text(encoding="utf-8")
CAPTURE = (ROOT / "src" / "vr" / "d3d9" / "stereo_renderer_r7.inc").read_text(encoding="utf-8")


def require(token: str, source: str, label: str) -> None:
    if token not in source:
        raise SystemExit(f"DX11 state capture contract drift: {label}")


def main() -> None:
    contracts = [
        ("D3DRS_ALPHATESTENABLE", CAPTURE, "alpha test capture"),
        ("D3DRS_ZENABLE", CAPTURE, "depth enable capture"),
        ("D3DRS_CULLMODE", CAPTURE, "cull mode capture"),
        ("source.", STATE, "state translation consumes captured source"),
    ]
    for token, source, label in contracts:
        require(token, source, label)

    if CAPTURE.count("read(") == 0:
        raise SystemExit("DX11 state capture contract drift: no D3D9 state reads")

    print("DX11 state capture static contract: PASS")


if __name__ == "__main__":
    main()
