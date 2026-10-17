#!/usr/bin/env python3
"""00607: live game D3D9 dest-alpha crossfade -> DX11 native Draw/DrawIndexed."""
from pathlib import Path

S = (Path(__file__).resolve().parents[1] /
     "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
def section(s, a, b):
    i = s.find(a)
    j = s.find(b, i+len(a))
    return s[i:j] if i >= 0 and j > i else ""

def integrated(s):
    cap = section(s, "bool supported_game_state(", "bool translate_vertices(")
    pipe = section(s, "bool ensure_pipeline(", "bool supported_game_state(")
    desc = section(pipe, "// Actual game Draw state may weight", "D3D11_BUFFER_DESC constants{}")
    draw = section(s, "bool submit(", "void observe(")
    required = [
        ("bool destAlphaCrossfadeBlend = false;", s),
        ("bool reverseDestAlphaCrossfadeBlend = false;", s),
        ("s.destAlphaCrossfadeBlend && s.reverseDestAlphaCrossfadeBlend &&", pipe),
        ("target.SrcBlend = D3D11_BLEND_DEST_ALPHA;", desc),
        ("target.DestBlend = D3D11_BLEND_INV_DEST_ALPHA;", desc),
        ("target.SrcBlendAlpha = D3D11_BLEND_DEST_ALPHA;", desc),
        ("target.DestBlendAlpha = D3D11_BLEND_INV_DEST_ALPHA;", desc),
        ("target.SrcBlend = D3D11_BLEND_INV_DEST_ALPHA;", desc),
        ("target.DestBlend = D3D11_BLEND_DEST_ALPHA;", desc),
        ("target.SrcBlendAlpha = D3D11_BLEND_INV_DEST_ALPHA;", desc),
        ("target.DestBlendAlpha = D3D11_BLEND_DEST_ALPHA;", desc),
        ("s.destAlphaCrossfadeBlend.GetAddressOf()", desc),
        ("s.reverseDestAlphaCrossfadeBlend.GetAddressOf()", desc),
        ("src == D3DBLEND_DESTALPHA && dst == D3DBLEND_INVDESTALPHA", cap),
        ("src == D3DBLEND_INVDESTALPHA && dst == D3DBLEND_DESTALPHA", cap),
        ("if ((destAlphaCrossfade || reverseDestAlphaCrossfade) &&", cap),
        ("destAlphaCrossfade || reverseDestAlphaCrossfade) {", cap),
        ("output.destAlphaCrossfadeBlend = destAlphaCrossfade;", cap),
        ("output.reverseDestAlphaCrossfadeBlend = reverseDestAlphaCrossfade;", cap),
        ("s.destAlphaCrossfadeMaskedBlends[output.colorWriteMask]", draw),
        ("s.reverseDestAlphaCrossfadeMaskedBlends[output.colorWriteMask]", draw),
        ("s.destAlphaCrossfadeBlend->GetDesc(&desc);", draw),
        ("s.reverseDestAlphaCrossfadeBlend->GetDesc(&desc);", draw),
        ("ctx->OMSetBlendState(s.destAlphaCrossfadeBlend.Get(), nullptr, 0xffffffffu);", draw),
        ("ctx->OMSetBlendState(s.reverseDestAlphaCrossfadeBlend.Get(), nullptr, 0xffffffffu);", draw),
        ("ctx->DrawIndexed(indexCount, 0, 0);", draw),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", draw),
        ("return optedIn;", s),
    ]
    return all(needle in block for needle,block in required) and all(
        s.count(term)==2 for term in (
            "s.destAlphaCrossfadeBlend.Reset();",
            "s.reverseDestAlphaCrossfadeBlend.Reset();",
            "for (auto& masked : s.destAlphaCrossfadeMaskedBlends) masked.Reset();",
            "for (auto& masked : s.reverseDestAlphaCrossfadeMaskedBlends) masked.Reset();"))

assert integrated(S), "00607 live-game D3D9 to native OM connection missing"
mutations = [
    ("bool destAlphaCrossfadeBlend = false;", "bool noDestAlpha = false;"),
    ("bool reverseDestAlphaCrossfadeBlend = false;", "bool noReverse = false;"),
    ("s.destAlphaCrossfadeBlend && s.reverseDestAlphaCrossfadeBlend &&", "s.alphaBlend &&"),
    ("target.SrcBlend = D3D11_BLEND_DEST_ALPHA;", "target.SrcBlend = D3D11_BLEND_SRC_ALPHA;"),
    ("target.DestBlend = D3D11_BLEND_INV_DEST_ALPHA;", "target.DestBlend = D3D11_BLEND_INV_SRC_ALPHA;"),
    ("target.SrcBlendAlpha = D3D11_BLEND_DEST_ALPHA;", "target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;"),
    ("target.DestBlendAlpha = D3D11_BLEND_INV_DEST_ALPHA;", "target.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;"),
    ("target.SrcBlend = D3D11_BLEND_INV_DEST_ALPHA;", "target.SrcBlend = D3D11_BLEND_INV_SRC_ALPHA;"),
    ("target.DestBlend = D3D11_BLEND_DEST_ALPHA;", "target.DestBlend = D3D11_BLEND_SRC_ALPHA;"),
    ("target.SrcBlendAlpha = D3D11_BLEND_INV_DEST_ALPHA;", "target.SrcBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;"),
    ("target.DestBlendAlpha = D3D11_BLEND_DEST_ALPHA;", "target.DestBlendAlpha = D3D11_BLEND_SRC_ALPHA;"),
    ("s.destAlphaCrossfadeBlend.GetAddressOf()", "s.alphaBlend.GetAddressOf()"),
    ("s.reverseDestAlphaCrossfadeBlend.GetAddressOf()", "s.alphaBlend.GetAddressOf()"),
    ("src == D3DBLEND_DESTALPHA && dst == D3DBLEND_INVDESTALPHA", "src == D3DBLEND_SRCALPHA && dst == D3DBLEND_INVDESTALPHA"),
    ("src == D3DBLEND_INVDESTALPHA && dst == D3DBLEND_DESTALPHA", "src == D3DBLEND_INVSRCALPHA && dst == D3DBLEND_DESTALPHA"),
    ("if ((destAlphaCrossfade || reverseDestAlphaCrossfade) &&", "if (false &&"),
    ("destAlphaCrossfade || reverseDestAlphaCrossfade) {", "false) {"),
    ("output.destAlphaCrossfadeBlend = destAlphaCrossfade;", "output.destAlphaCrossfadeBlend = false;"),
    ("output.reverseDestAlphaCrossfadeBlend = reverseDestAlphaCrossfade;", "output.reverseDestAlphaCrossfadeBlend = false;"),
    ("s.destAlphaCrossfadeMaskedBlends[output.colorWriteMask]", "s.maskedBlends[output.colorWriteMask]"),
    ("s.reverseDestAlphaCrossfadeMaskedBlends[output.colorWriteMask]", "s.maskedBlends[output.colorWriteMask]"),
    ("s.destAlphaCrossfadeBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);"),
    ("s.reverseDestAlphaCrossfadeBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);"),
    ("ctx->OMSetBlendState(s.destAlphaCrossfadeBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
    ("ctx->OMSetBlendState(s.reverseDestAlphaCrossfadeBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
]
for old,bad in mutations:
    assert old in S, "lost mutation anchor " + old
    if old.startswith("target."):
        i = S.index("// Actual game Draw state may weight")
        j = S.index("D3D11_BUFFER_DESC constants{}", i)
        corrupted = S[:i] + S[i:j].replace(old,bad,1) + S[j:]
    else:
        corrupted = S.replace(old,bad,1)
    assert not integrated(corrupted), "undetected mutation: " + old
grid = [i/16 for i in range(17)]
cases = 0
for a in grid:
    for src in grid:
        for dst in grid:
            forward = src*a + dst*(1-a)
            reverse = src*(1-a) + dst*a
            assert abs(forward-(src*a+dst*(1-a))) < 1e-12
            assert abs(reverse-(src*(1-a)+dst*a)) < 1e-12
            cases += 1
assert cases == 4913
print("00607 destination-alpha native OM PASS:", len(mutations), "mutations,", cases, "RGBA factor cases")
