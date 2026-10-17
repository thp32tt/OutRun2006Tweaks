#!/usr/bin/env python3
"""Check R84 fast DDS loader respects caller format/mip requests; fail closed."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/hooks_textures.cpp"
HEADER = ROOT / "src/vr/game/dds_fast_loader_request.hpp"

def check(source: str, policy: str) -> bool:
    create = source.find("pDevice->CreateTexture(")
    mip = source.find("DdsFastLoad::RequestedMipCountSupported(")
    fmt = source.find("DdsFastLoad::RequestedFormatSupported(")
    return (mip > 0 and fmt > mip and create > fmt and
            "return E_FAIL;" in source[mip:source.find("MipLevels =", mip)] and
            "return E_FAIL;" in source[fmt:create] and
            "requested > 0u && requested <= available" in policy and
            "requested == resolved" in policy and
            "requested == fromFile" in policy and
            "kD3dxFromFile = 0xfffffffdu" in policy and
            "DdsFastLoad::kD3dxFromFile" in source and
            "D3DX_FROM_FILE" not in source)

if __name__ == "__main__":
    text, policy = SRC.read_text(encoding="utf-8"), HEADER.read_text(encoding="utf-8")
    assert check(text, policy), "missing physical fast-loader request guard"
    assert not check(text.replace("RequestedMipCountSupported", "MipGuardRemoved"), policy)
    assert not check(text.replace("RequestedFormatSupported", "FormatGuardRemoved"), policy)
    assert not check(text, policy.replace("requested == resolved", "false"))
    assert not check(text.replace("DdsFastLoad::kD3dxFromFile", "D3DX_FROM_FILE"), policy)
    assert not check(text, policy.replace("kD3dxFromFile = 0xfffffffdu", "kD3dxFromFile = 0"))
    print("PASS: requested mip/format preserved or native D3DX fallback")
