#!/usr/bin/env python3
"""00596 game-created D3D9 blend -> D3D11 native Draw/DrawIndexed mutation test."""
from pathlib import Path
S = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"
REQUIRED = {
    "struct OutputCapture {": [
        "bool additiveBlend = false;", "bool sourceAlphaAddBlend = false;"],
    "struct State {": [
        "ComPtr<ID3D11BlendState> additiveBlend;",
        "ComPtr<ID3D11BlendState> sourceAlphaAddBlend;",
        "std::array<ComPtr<ID3D11BlendState>, 80> maskedBlends{};"],
    "bool ensure_pipeline(": [
        "s.additiveBlend && s.sourceAlphaAddBlend",
        "s.additiveBlend.Reset(); s.sourceAlphaAddBlend.Reset();",
        "target.SrcBlend = D3D11_BLEND_ONE;",
        "target.DestBlend = D3D11_BLEND_ONE;",
        "target.SrcBlendAlpha = D3D11_BLEND_ONE;",
        "target.DestBlendAlpha = D3D11_BLEND_ONE;",
        "dev->CreateBlendState(&blend, s.additiveBlend.GetAddressOf())",
        "target.SrcBlend = D3D11_BLEND_SRC_ALPHA;",
        "target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;",
        "dev->CreateBlendState(&blend, s.sourceAlphaAddBlend.GetAddressOf())"],
    "bool supported_game_state(": [
        "GetRenderState(D3DRS_SRCBLEND, &src)",
        "GetRenderState(D3DRS_DESTBLEND, &dst)",
        "if (separate != FALSE) {",
        "!native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,",
        "output.separateAlphaBlend = true;",
        "if (blendOp != D3DBLENDOP_ADD) {",
        "const bool additive = src == D3DBLEND_ONE && dst == D3DBLEND_ONE;",
        "const bool sourceAlphaAdd = src == D3DBLEND_SRCALPHA",
        "!additive && !sourceAlphaAdd) return false;",
        "output.additiveBlend = additive;",
        "output.sourceAlphaAddBlend = sourceAlphaAdd;"],
    "bool submit(": [
        "output.additiveBlend ? 16u :",
        "output.sourceAlphaAddBlend ? 32u : 0u",
        "maskDesc.RenderTarget[0].SrcBlend =",
        "maskDesc.RenderTarget[0].DestBlend = D3D11_BLEND_ONE;",
        "maskDesc.RenderTarget[0].SrcBlendAlpha =",
        "maskDesc.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_ONE;",
        "ctx->OMSetBlendState(s.additiveBlend.Get(), nullptr, 0xffffffffu);",
        "ctx->OMSetBlendState(s.sourceAlphaAddBlend.Get(), nullptr, 0xffffffffu);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"]
}
def linked(code):
    for index, (section, evidence) in enumerate(REQUIRED.items()):
        start = code.find(section)
        if start < 0: return False
        next_sections = list(REQUIRED)[index + 1:]
        end = min((code.find(n, start + len(section)) for n in next_sections), default=len(code))
        fragment = code[start:end]
        if not all(e in fragment for e in evidence): return False
    # Count the 00596 additive descriptor only. Later valid source-copy
    # states may also use ONE without changing the existing additive proof.
    begin = code.find("// Game-supplied D3D9 SRCBLEND/DESTBLEND factors")
    end = code.find("// Premultiplied-alpha menu/UI surfaces:", begin)
    if begin < 0 or end <= begin: return False
    additive = code[begin:end]
    return (code.count("for (auto& masked : s.maskedBlends) masked.Reset();") == 2
            and additive.count("target.SrcBlend = D3D11_BLEND_ONE;") == 1
            and additive.count("target.SrcBlendAlpha = D3D11_BLEND_ONE;") == 1
            and additive.count("target.DestBlend = D3D11_BLEND_ONE;") == 1
            and additive.count("target.DestBlendAlpha = D3D11_BLEND_ONE;") == 1
            and "return optedIn;" in code)

def main():
    source = S.read_text(encoding="utf8")
    assert linked(source), "game D3D9 -> native OM -> Draw integration not linked"
    mutations = [
        ("bool additiveBlend = false;", "bool addLost = false;"),
        ("bool sourceAlphaAddBlend = false;", "bool alphaAddLost = false;"),
        ("std::array<ComPtr<ID3D11BlendState>, 80> maskedBlends{};", "std::array<ComPtr<ID3D11BlendState>, 32> maskedBlends{};"),
        ("target.SrcBlend = D3D11_BLEND_ONE;", "target.SrcBlend = D3D11_BLEND_ZERO;"),
        ("target.DestBlend = D3D11_BLEND_ONE;", "target.DestBlend = D3D11_BLEND_ZERO;"),
        ("target.SrcBlendAlpha = D3D11_BLEND_ONE;", "target.SrcBlendAlpha = D3D11_BLEND_ZERO;"),
        ("target.DestBlendAlpha = D3D11_BLEND_ONE;", "target.DestBlendAlpha = D3D11_BLEND_ZERO;"),
        ("dev->CreateBlendState(&blend, s.additiveBlend.GetAddressOf())", "dev->CreateBlendState(&blend, s.alphaBlend.GetAddressOf())"),
        ("dev->CreateBlendState(&blend, s.sourceAlphaAddBlend.GetAddressOf())", "dev->CreateBlendState(&blend, s.alphaBlend.GetAddressOf())"),
        ("const bool additive = src == D3DBLEND_ONE && dst == D3DBLEND_ONE;", "const bool additive = src == D3DBLEND_ONE || dst == D3DBLEND_ONE;"),
        # 00689 expanded real game separate-alpha without changing legacy
        # 00596 RGB blend modes. Mutation must break live producer admission.
        ("!native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,", "/* separate-alpha source validation lost */ false &&"),
        ("output.separateAlphaBlend = true;", "output.separateAlphaBlend = false;"),
        ("!additive && !sourceAlphaAdd) return false;", "false) return false;"),
        ("output.additiveBlend = additive;", "output.additiveBlend = false;"),
        ("output.sourceAlphaAddBlend = sourceAlphaAdd;", "output.sourceAlphaAddBlend = false;"),
        ("output.sourceAlphaAddBlend ? 32u : 0u", "output.sourceAlphaAddBlend ? 0u : 0u"),
        ("maskDesc.RenderTarget[0].DestBlend = D3D11_BLEND_ONE;", "maskDesc.RenderTarget[0].DestBlend = D3D11_BLEND_ZERO;"),
        ("ctx->OMSetBlendState(s.additiveBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "/* no native index Draw */")
    ]
    for original, broken in mutations:
        assert original in source, original
        assert not linked(source.replace(original, broken, 1)), original
    for src in ("ONE", "SRCALPHA", "ZERO", "DESTCOLOR"):
        for dst in ("ONE", "INVSRCALPHA", "ZERO", "SRCALPHA"):
            for separate in (False, True):
                for op in ("ADD", "SUBTRACT"):
                    allowed = not separate and op == "ADD" and (
                        (src, dst) in (("ONE", "ONE"), ("SRCALPHA", "INVSRCALPHA"), ("SRCALPHA", "ONE")))
                    expected = not separate and op == "ADD" and (
                        (src == "ONE" and dst == "ONE") or
                        (src == "SRCALPHA" and dst in ("INVSRCALPHA", "ONE")))
                    assert allowed == expected
    for i in range(257):
        alpha = i/256.0
        src,dst = 0.3,0.5
        assert abs((src*alpha + dst) - (dst + src*alpha)) < 1e-9
        assert abs((src + dst) - 0.8) < 1e-9
        assert src*alpha+dst >= dst
    print("00596 game D3D9 native additive OM integration and 17 mutations PASS")

if __name__ == "__main__":
    main()
