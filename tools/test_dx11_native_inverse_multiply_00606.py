#!/usr/bin/env python3
"""00606 actual D3D9 Draw/DrawIndexed blend state to distinct DX11 OM paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")


def section(s, start, end):
    a = s.find(start)
    b = s.find(end, a + len(start))
    return s[a:b] if a >= 0 and b > a else ""


def connected(s):
    capture = section(s, "bool supported_game_state(", "bool translate_vertices(")
    pipe = section(s, "bool ensure_pipeline(", "bool supported_game_state(")
    draw = section(s, "bool submit(", "void observe(")
    om = section(pipe, "// Menu/vehicle/race complement modulation.",
                 "D3D11_BUFFER_DESC constants{}")
    dest = section(om, "target.SrcBlend = D3D11_BLEND_INV_DEST_COLOR;",
                   "target.SrcBlend = D3D11_BLEND_ZERO;")
    source = section(om, "target.SrcBlend = D3D11_BLEND_ZERO;",
                     "D3D11_BUFFER_DESC constants{}") or om[om.find("target.SrcBlend = D3D11_BLEND_ZERO;"):]
    return all((
        "bool inverseDestMultiplyBlend = false;" in s,
        "bool inverseSourceMultiplyBlend = false;" in s,
        "ComPtr<ID3D11BlendState> inverseDestMultiplyBlend;" in s,
        "ComPtr<ID3D11BlendState> inverseSourceMultiplyBlend;" in s,
        "s.inverseDestMultiplyBlend && s.inverseSourceMultiplyBlend &&" in pipe,
        "target.SrcBlend = D3D11_BLEND_INV_DEST_COLOR;" in dest,
        "target.DestBlend = D3D11_BLEND_ZERO;" in dest,
        "target.SrcBlendAlpha = D3D11_BLEND_INV_DEST_ALPHA;" in dest,
        "target.DestBlendAlpha = D3D11_BLEND_ZERO;" in dest,
        "dev->CreateBlendState(&blend, s.inverseDestMultiplyBlend.GetAddressOf())" in om,
        "target.SrcBlend = D3D11_BLEND_ZERO;" in source,
        "target.DestBlend = D3D11_BLEND_INV_SRC_COLOR;" in source,
        "target.SrcBlendAlpha = D3D11_BLEND_ZERO;" in source,
        "target.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;" in source,
        "dev->CreateBlendState(&blend, s.inverseSourceMultiplyBlend.GetAddressOf())" in om,
        "src == D3DBLEND_INVDESTCOLOR && dst == D3DBLEND_ZERO" in capture,
        "src == D3DBLEND_ZERO && dst == D3DBLEND_INVSRCCOLOR" in capture,
        "if ((inverseDestMultiply || inverseSourceMultiply) &&" in capture,
        "blendOp != D3DBLENDOP_ADD) return false;" in capture,
        "if (inverseDestMultiply || inverseSourceMultiply) {" in capture,
        "output.inverseDestMultiplyBlend = inverseDestMultiply;" in capture,
        "output.inverseSourceMultiplyBlend = inverseSourceMultiply;" in capture,
        "s.inverseDestMultiplyMaskedBlends[output.colorWriteMask]" in draw,
        "s.inverseSourceMultiplyMaskedBlends[output.colorWriteMask]" in draw,
        "s.inverseDestMultiplyBlend->GetDesc(&desc);" in draw,
        "s.inverseSourceMultiplyBlend->GetDesc(&desc);" in draw,
        "ctx->OMSetBlendState(s.inverseDestMultiplyBlend.Get(), nullptr, 0xffffffffu);" in draw,
        "ctx->OMSetBlendState(s.inverseSourceMultiplyBlend.Get(), nullptr, 0xffffffffu);" in draw,
        "ctx->DrawIndexed(indexCount, 0, 0);" in draw,
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in draw,
        s.count("s.inverseDestMultiplyBlend.Reset();") == 2,
        s.count("s.inverseSourceMultiplyBlend.Reset();") == 2,
        s.count("for (auto& masked : s.inverseDestMultiplyMaskedBlends) masked.Reset();") == 2,
        s.count("for (auto& masked : s.inverseSourceMultiplyMaskedBlends) masked.Reset();") == 2,
        "return optedIn;" in s,
    ))


assert connected(SRC), "00606 complement OM not connected to actual game Draw/DrawIndexed"
# Mutate each new capture, native descriptor, per-mask cache and dispatch.
mutants = (
    ("bool inverseDestMultiplyBlend = false;", "bool badDest = false;"),
    ("bool inverseSourceMultiplyBlend = false;", "bool badSource = false;"),
    ("s.inverseDestMultiplyBlend && s.inverseSourceMultiplyBlend &&", "s.multiplyBlend &&"),
    ("target.SrcBlend = D3D11_BLEND_INV_DEST_COLOR;", "target.SrcBlend = D3D11_BLEND_DEST_COLOR;"),
    ("target.SrcBlendAlpha = D3D11_BLEND_INV_DEST_ALPHA;", "target.SrcBlendAlpha = D3D11_BLEND_DEST_ALPHA;"),
    ("target.DestBlend = D3D11_BLEND_INV_SRC_COLOR;", "target.DestBlend = D3D11_BLEND_SRC_COLOR;"),
    ("target.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;", "target.DestBlendAlpha = D3D11_BLEND_SRC_ALPHA;"),
    ("dev->CreateBlendState(&blend, s.inverseDestMultiplyBlend.GetAddressOf())", "dev->CreateBlendState(&blend, s.multiplyBlend.GetAddressOf())"),
    ("dev->CreateBlendState(&blend, s.inverseSourceMultiplyBlend.GetAddressOf())", "dev->CreateBlendState(&blend, s.multiplyBlend.GetAddressOf())"),
    ("src == D3DBLEND_INVDESTCOLOR && dst == D3DBLEND_ZERO", "src == D3DBLEND_DESTCOLOR && dst == D3DBLEND_ZERO"),
    ("src == D3DBLEND_ZERO && dst == D3DBLEND_INVSRCCOLOR", "src == D3DBLEND_ZERO && dst == D3DBLEND_SRCCOLOR"),
    ("if (inverseDestMultiply || inverseSourceMultiply) {", "if (false) {"),
    ("output.inverseDestMultiplyBlend = inverseDestMultiply;", "output.inverseDestMultiplyBlend = false;"),
    ("output.inverseSourceMultiplyBlend = inverseSourceMultiply;", "output.inverseSourceMultiplyBlend = false;"),
    ("s.inverseDestMultiplyMaskedBlends[output.colorWriteMask]", "s.multiplyMaskedBlends[output.colorWriteMask]"),
    ("s.inverseSourceMultiplyMaskedBlends[output.colorWriteMask]", "s.multiplyMaskedBlends[output.colorWriteMask]"),
    ("s.inverseDestMultiplyBlend->GetDesc(&desc);", "s.multiplyBlend->GetDesc(&desc);"),
    ("s.inverseSourceMultiplyBlend->GetDesc(&desc);", "s.multiplyBlend->GetDesc(&desc);"),
    ("ctx->OMSetBlendState(s.inverseDestMultiplyBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
    ("ctx->OMSetBlendState(s.inverseSourceMultiplyBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
)
for old, wrong in mutants:
    assert old in SRC, old
    if old.startswith("target."):
        # Mutate only the new complement OM descriptors. Earlier valid
        # source-over states have the same INV_SRC_ALPHA alpha factor.
        begin = SRC.index("// Menu/vehicle/race complement modulation.")
        end = SRC.index("D3D11_BUFFER_DESC constants{}", begin)
        block = SRC[begin:end]
        assert old in block
        mutant = SRC[:begin] + block.replace(old, wrong, 1) + SRC[end:]
    else:
        mutant = SRC.replace(old, wrong, 1)
    assert not connected(mutant), "undetected 00606 destructive regression: " + old

# D3D9 equation and native color/alpha blend factors must agree independently.
cases = 0
for src in range(0, 257, 8):
    for dst in range(0, 257, 8):
        a, b = src / 256.0, dst / 256.0
        # INVDESTCOLOR/ZERO: source*(1-destination); ZERO/INVSRCCOLOR: destination*(1-source).
        d3d9_src = a * (1 - b)
        dx11_src = a * (1 - b) + b * 0
        d3d9_dst = b * (1 - a)
        dx11_dst = a * 0 + b * (1 - a)
        assert abs(d3d9_src - dx11_src) < 1e-12
        assert abs(d3d9_dst - dx11_dst) < 1e-12
        cases += 1
assert cases == 1089
print("00606 live DX11 inverse modulation: 20 source mutants, 1089 RGBA factor pairs PASS")
