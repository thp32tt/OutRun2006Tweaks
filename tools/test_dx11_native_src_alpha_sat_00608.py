#!/usr/bin/env python3
"""00608: D3D9 SRCALPHASAT ZERO/ONE through real native DX11 game Draw."""
from pathlib import Path
from itertools import product

S = (Path(__file__).resolve().parents[1] /
     "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")

def section(s, a, b):
    i = s.find(a)
    j = s.find(b, i + len(a))
    if i < 0 or j <= i: raise ValueError(a)
    return s[i:j]

def integrated(s):
    try:
        cap = section(s, "bool supported_game_state(", "bool translate_vertices(")
        pipe = section(s, "bool ensure_pipeline(", "bool supported_game_state(")
        desc = section(pipe, "// Game D3D9 SRCALPHASAT", "D3D11_BUFFER_DESC constants{}")
        draw = section(s, "bool submit(", "void observe(")
        blocks = desc.split("    target.SrcBlend = D3D11_BLEND_SRC_ALPHA_SAT;")
        if len(blocks) != 3: return False
        if not all(
            "target.DestBlend = " + factor + ";" in part and
            "target.SrcBlendAlpha = D3D11_BLEND_ONE;" in part and
            "target.DestBlendAlpha = " + factor + ";" in part and
            "s." + name + ".GetAddressOf()" in part
            for part, factor, name in [
                (blocks[1], "D3D11_BLEND_ZERO", "sourceAlphaSaturateCopyBlend"),
                (blocks[2], "D3D11_BLEND_ONE", "sourceAlphaSaturateAddBlend")
            ]): return False
        required = [
            ("bool sourceAlphaSaturateCopyBlend = false;", s),
            ("bool sourceAlphaSaturateAddBlend = false;", s),
            ("s.sourceAlphaSaturateCopyBlend && s.sourceAlphaSaturateAddBlend &&", pipe),
            ("src == D3DBLEND_SRCALPHASAT && dst == D3DBLEND_ZERO", cap),
            ("src == D3DBLEND_SRCALPHASAT && dst == D3DBLEND_ONE", cap),
            ("sourceAlphaSaturateCopy || sourceAlphaSaturateAdd) {", cap),
            ("if (blendOp != D3DBLENDOP_ADD) return false;", cap),
            ("output.sourceAlphaSaturateCopyBlend = sourceAlphaSaturateCopy;", cap),
            ("output.sourceAlphaSaturateAddBlend = sourceAlphaSaturateAdd;", cap),
            ("s.sourceAlphaSaturateCopyMaskedBlends[output.colorWriteMask]", draw),
            ("s.sourceAlphaSaturateAddMaskedBlends[output.colorWriteMask]", draw),
            ("s.sourceAlphaSaturateCopyBlend->GetDesc(&desc);", draw),
            ("s.sourceAlphaSaturateAddBlend->GetDesc(&desc);", draw),
            ("ctx->OMSetBlendState(s.sourceAlphaSaturateCopyBlend.Get(), nullptr, 0xffffffffu);", draw),
            ("ctx->OMSetBlendState(s.sourceAlphaSaturateAddBlend.Get(), nullptr, 0xffffffffu);", draw),
            ("ctx->DrawIndexed(indexCount, 0, 0);", draw),
            ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", draw),
            ("return optedIn;", s),
        ]
        return all(term in block for term, block in required) and all(
            s.count(term) == 2 for term in (
                "s.sourceAlphaSaturateCopyBlend.Reset();",
                "s.sourceAlphaSaturateAddBlend.Reset();",
                "for (auto& masked : s.sourceAlphaSaturateCopyMaskedBlends) masked.Reset();",
                "for (auto& masked : s.sourceAlphaSaturateAddMaskedBlends) masked.Reset();"))
    except ValueError:
        return False

assert integrated(S), "00608 D3D9->DX11 native OM integration incomplete"
mutations = [
    ("bool sourceAlphaSaturateCopyBlend = false;", "bool noCopy = false;"),
    ("bool sourceAlphaSaturateAddBlend = false;", "bool noAdd = false;"),
    ("s.sourceAlphaSaturateCopyBlend && s.sourceAlphaSaturateAddBlend &&", "s.alphaBlend &&"),
    ("src == D3DBLEND_SRCALPHASAT && dst == D3DBLEND_ZERO", "src == D3DBLEND_SRCALPHA && dst == D3DBLEND_ZERO"),
    ("src == D3DBLEND_SRCALPHASAT && dst == D3DBLEND_ONE", "src == D3DBLEND_SRCALPHA && dst == D3DBLEND_ONE"),
    ("sourceAlphaSaturateCopy || sourceAlphaSaturateAdd) {", "false) {"),
    ("output.sourceAlphaSaturateCopyBlend = sourceAlphaSaturateCopy;", "output.sourceAlphaSaturateCopyBlend = false;"),
    ("output.sourceAlphaSaturateAddBlend = sourceAlphaSaturateAdd;", "output.sourceAlphaSaturateAddBlend = false;"),
    ("s.sourceAlphaSaturateCopyMaskedBlends[output.colorWriteMask]", "s.maskedBlends[output.colorWriteMask]"),
    ("s.sourceAlphaSaturateAddMaskedBlends[output.colorWriteMask]", "s.maskedBlends[output.colorWriteMask]"),
    ("s.sourceAlphaSaturateCopyBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);"),
    ("s.sourceAlphaSaturateAddBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);"),
    ("ctx->OMSetBlendState(s.sourceAlphaSaturateCopyBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
    ("ctx->OMSetBlendState(s.sourceAlphaSaturateAddBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
    ("s.sourceAlphaSaturateCopyBlend.Reset();", "s.alphaBlend.Reset();"),
    ("s.sourceAlphaSaturateAddBlend.Reset();", "s.alphaBlend.Reset();"),
    ("for (auto& masked : s.sourceAlphaSaturateCopyMaskedBlends) masked.Reset();", "for (auto& masked : s.maskedBlends) masked.Reset();"),
    ("for (auto& masked : s.sourceAlphaSaturateAddMaskedBlends) masked.Reset();", "for (auto& masked : s.maskedBlends) masked.Reset();"),
]
for old, bad in mutations:
    assert old in S, "lost mutation anchor " + old
    assert not integrated(S.replace(old, bad, 1)), "undetected mutation " + old
start = S.index("// Game D3D9 SRCALPHASAT")
end = S.index("D3D11_BUFFER_DESC constants{}", start)
for old,bad in [
    ("target.SrcBlend = D3D11_BLEND_SRC_ALPHA_SAT;", "target.SrcBlend = D3D11_BLEND_SRC_ALPHA;"),
    ("target.DestBlend = D3D11_BLEND_ZERO;", "target.DestBlend = D3D11_BLEND_ONE;"),
    ("target.SrcBlendAlpha = D3D11_BLEND_ONE;", "target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;"),
    ("target.DestBlendAlpha = D3D11_BLEND_ZERO;", "target.DestBlendAlpha = D3D11_BLEND_ONE;"),
    ("s.sourceAlphaSaturateCopyBlend.GetAddressOf()", "s.alphaBlend.GetAddressOf()"),
    ("s.sourceAlphaSaturateAddBlend.GetAddressOf()", "s.alphaBlend.GetAddressOf()"),
]:
    frag = S[start:end]
    assert old in frag, "lost descriptor mutation " + old
    assert not integrated(S[:start] + frag.replace(old,bad,1) + S[end:]), "descriptor escaped mutation " + old
start2 = S.index("    target.SrcBlend = D3D11_BLEND_SRC_ALPHA_SAT;", start + 50)
assert not integrated(S[:start2] + S[start2:].replace(
    "target.DestBlend = D3D11_BLEND_ONE;", "target.DestBlend = D3D11_BLEND_ZERO;", 1))
grid = [x / 16 for x in range(17)]
cases = 0
for sa, da, rgb, dst in product(grid, repeat=4):
    sat = min(sa, 1.0-da)
    for d in (0.0, 1.0):
        rgb9 = rgb * min(sa, 1.0-da) + dst * d
        rgb11 = rgb * sat + dst * d
        alpha9 = sa * 1.0 + da * d
        alpha11 = sa + da * d
        assert abs(rgb9-rgb11) < 1e-12 and abs(alpha9-alpha11) < 1e-12
    cases += 1
assert cases == 83521
print("00608 native SRCALPHASAT PASS:", len(mutations)+7, "negative mutants,", cases, "RGBA scalar cases")
