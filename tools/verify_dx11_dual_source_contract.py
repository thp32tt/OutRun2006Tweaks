#!/usr/bin/env python3
"""Fail closed when DX11 dual-source blend claims exceed shader output evidence."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "src" / "vr" / "d3d11" / "state_translation.cpp"
SHADER = ROOT / "tools" / "dx11_fixed_function_shader_semantics.cpp"


def main() -> None:
    state = STATE.read_text(encoding="utf-8")
    shader = SHADER.read_text(encoding="utf-8")

    required_fail_closed = [
        "D3DBLEND_SRCCOLOR2",
        "D3DBLEND_INVSRCCOLOR2",
        "false",
        "D3D11_BLEND_SRC1_COLOR",
        "D3D11_BLEND_INV_SRC1_COLOR",
    ]
    missing = [token for token in required_fail_closed if token not in state]
    if missing:
        raise SystemExit("dual-source blend fail-closed contract missing: " + ", ".join(missing))

    if "SV_Target1" in shader:
        raise SystemExit("unexpected second pixel output evidence requires review")

    print("DX11 dual-source blend contract: PASS (fail-closed)")


if __name__ == "__main__":
    main()
