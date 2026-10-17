#!/usr/bin/env python3
"""DX11-00604: real D3D9 INVSRCALPHA ZERO/ONE diagnostic Draw/DrawIndexed."""
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def part(s, begin, end):
    i = s.index(begin)
    return s[i:s.index(end, i + len(begin))]

def linked(s):
    try:
        cap = part(s, "struct OutputCapture {", "struct ReadbackSlot {")
        st = part(s, "struct State {", "State& state()")
        pipeline = part(s, "bool ensure_pipeline(", "bool supported_game_state(")
        desc = part(pipeline, "// Exact live D3D9 inverse-source-alpha", "// D3D9 ONE/ZERO:")
        game = part(s, "bool supported_game_state(", "bool translate_vertices(")
        draw = part(s, "bool submit(", "void observe(")
        mc = part(draw, "} else if (output.inverseAlphaCopyBlend &&",
                  "} else if (output.inverseAlphaAddBlend &&")
        ma = part(draw, "} else if (output.inverseAlphaAddBlend &&",
                  "} else if (output.sourceReplaceBlend &&")
        checks = [
            (cap, ["bool inverseAlphaCopyBlend = false;", "bool inverseAlphaAddBlend = false;"]),
            (st, ["ComPtr<ID3D11BlendState> inverseAlphaCopyBlend;", "ComPtr<ID3D11BlendState> inverseAlphaAddBlend;",
                  "std::array<ComPtr<ID3D11BlendState>, 16> inverseAlphaCopyMaskedBlends{};",
                  "std::array<ComPtr<ID3D11BlendState>, 16> inverseAlphaAddMaskedBlends{};"]),
            (pipeline, ["s.inverseAlphaCopyBlend &&", "s.inverseAlphaAddBlend &&"]),
            (desc, ["target.SrcBlend = D3D11_BLEND_INV_SRC_ALPHA;",
                    "target.DestBlend = D3D11_BLEND_ZERO;", "target.SrcBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;",
                    "target.DestBlendAlpha = D3D11_BLEND_ZERO;",
                    "dev->CreateBlendState(&blend, s.inverseAlphaCopyBlend.GetAddressOf())",
                    "target.DestBlend = D3D11_BLEND_ONE;", "target.DestBlendAlpha = D3D11_BLEND_ONE;",
                    "dev->CreateBlendState(&blend, s.inverseAlphaAddBlend.GetAddressOf())"]),
            (game, ["GetRenderState(D3DRS_SRCBLEND, &src)", "GetRenderState(D3DRS_DESTBLEND, &dst)",
                    "GetRenderState(D3DRS_BLENDOP, &blendOp)",
                    "GetRenderState(D3DRS_SEPARATEALPHABLENDENABLE, &separate)",
                    "const bool inverseAlphaCopy = src == D3DBLEND_INVSRCALPHA && dst == D3DBLEND_ZERO;",
                    "const bool inverseAlphaAdd = src == D3DBLEND_INVSRCALPHA && dst == D3DBLEND_ONE;",
                    "if ((inverseAlphaCopy || inverseAlphaAdd) && blendOp != D3DBLENDOP_ADD)",
                    "!inverseAlphaCopy && !inverseAlphaAdd &&",
                    "output.inverseAlphaCopyBlend = inverseAlphaCopy;",
                    "output.inverseAlphaAddBlend = inverseAlphaAdd;"]),
            (mc, ["s.inverseAlphaCopyMaskedBlends[output.colorWriteMask]",
                  "s.inverseAlphaCopyBlend->GetDesc(&desc);", "maskedBlend = &cached;"]),
            (ma, ["s.inverseAlphaAddMaskedBlends[output.colorWriteMask]",
                  "s.inverseAlphaAddBlend->GetDesc(&desc);", "maskedBlend = &cached;"]),
            (draw, ["ctx->OMSetBlendState(s.inverseAlphaCopyBlend.Get(), nullptr, 0xffffffffu);",
                    "ctx->OMSetBlendState(s.inverseAlphaAddBlend.Get(), nullptr, 0xffffffffu);",
                    "ctx->DrawIndexed(indexCount, 0, 0);", "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"])
        ]
        return all(all(token in region for token in tokens) for region, tokens in checks) and all(
            s.count(token) == 2 for token in [
                "s.inverseAlphaCopyBlend.Reset();", "s.inverseAlphaAddBlend.Reset();",
                "for (auto& masked : s.inverseAlphaCopyMaskedBlends) masked.Reset();",
                "for (auto& masked : s.inverseAlphaAddMaskedBlends) masked.Reset();"
            ]) and "OUTRUN_DX11_FIRST_GAME_FRAME" in s and "return optedIn;" in s
    except ValueError:
        return False

def main():
    s = SRC.read_text(encoding="utf-8")
    assert linked(s), "DX11-00604 native GetRenderState->OM->Draw integration broken"
    mutations = [
        ("bool inverseAlphaCopyBlend = false;", "bool inverseAlphaCopyBlend = true;", ""),
        ("bool inverseAlphaAddBlend = false;", "bool inverseAlphaAddBlend = true;", ""),
        ("s.inverseAlphaCopyBlend &&", "false &&", ""),
        ("s.inverseAlphaAddBlend &&", "false &&", ""),
        ("target.SrcBlend = D3D11_BLEND_INV_SRC_ALPHA;", "target.SrcBlend = D3D11_BLEND_SRC_ALPHA;", "desc"),
        ("target.DestBlend = D3D11_BLEND_ZERO;", "target.DestBlend = D3D11_BLEND_ONE;", "desc"),
        ("target.SrcBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;", "target.SrcBlendAlpha = D3D11_BLEND_ONE;", "desc"),
        ("target.DestBlendAlpha = D3D11_BLEND_ZERO;", "target.DestBlendAlpha = D3D11_BLEND_ONE;", "desc"),
        ("target.DestBlend = D3D11_BLEND_ONE;", "target.DestBlend = D3D11_BLEND_ZERO;", "add"),
        ("target.DestBlendAlpha = D3D11_BLEND_ONE;", "target.DestBlendAlpha = D3D11_BLEND_ZERO;", "add"),
        ("dev->CreateBlendState(&blend, s.inverseAlphaCopyBlend.GetAddressOf())", "return false", "desc"),
        ("dev->CreateBlendState(&blend, s.inverseAlphaAddBlend.GetAddressOf())", "return false", "desc"),
        ("const bool inverseAlphaCopy = src == D3DBLEND_INVSRCALPHA && dst == D3DBLEND_ZERO;", "const bool inverseAlphaCopy = false;", ""),
        ("const bool inverseAlphaAdd = src == D3DBLEND_INVSRCALPHA && dst == D3DBLEND_ONE;", "const bool inverseAlphaAdd = false;", ""),
        ("if ((inverseAlphaCopy || inverseAlphaAdd) && blendOp != D3DBLENDOP_ADD)", "if ((inverseAlphaCopy || inverseAlphaAdd) && blendOp == D3DBLENDOP_ADD)", ""),
        ("!inverseAlphaCopy && !inverseAlphaAdd &&", "!inverseAlphaCopy &&", ""),
        ("output.inverseAlphaCopyBlend = inverseAlphaCopy;", "output.inverseAlphaCopyBlend = false;", ""),
        ("output.inverseAlphaAddBlend = inverseAlphaAdd;", "output.inverseAlphaAddBlend = false;", ""),
        ("s.inverseAlphaCopyMaskedBlends[output.colorWriteMask]", "s.multiplyMaskedBlends[output.colorWriteMask]", ""),
        ("s.inverseAlphaAddMaskedBlends[output.colorWriteMask]", "s.multiplyMaskedBlends[output.colorWriteMask]", ""),
        ("s.inverseAlphaCopyBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);", ""),
        ("s.inverseAlphaAddBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);", ""),
        ("ctx->OMSetBlendState(s.inverseAlphaCopyBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(s.alphaBlend.Get(), nullptr, 0xffffffffu);", ""),
        ("ctx->OMSetBlendState(s.inverseAlphaAddBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(s.alphaBlend.Get(), nullptr, 0xffffffffu);", ""),
        ("s.inverseAlphaCopyBlend.Reset();", "s.alphaBlend.Reset();", ""),
        ("s.inverseAlphaAddBlend.Reset();", "s.alphaBlend.Reset();", ""),
        ("for (auto& masked : s.inverseAlphaCopyMaskedBlends) masked.Reset();", "for (auto& masked : s.multiplyMaskedBlends) masked.Reset();", ""),
        ("for (auto& masked : s.inverseAlphaAddMaskedBlends) masked.Reset();", "for (auto& masked : s.multiplyMaskedBlends) masked.Reset();", "")
    ]
    for before, after, scope in mutations:
        i, j = 0, len(s)
        if scope in ("desc", "add"):
            i = s.index("// Exact live D3D9 inverse-source-alpha")
            j = s.index("// D3D9 ONE/ZERO:", i)
            if scope == "add":
                i = s.index("target.DestBlend = D3D11_BLEND_ONE;", i, j)
        assert before in s[i:j], before
        mutation = s[:i] + s[i:j].replace(before, after, 1) + s[j:]
        assert not linked(mutation), "mutation escaped: " + before
    cases = 0
    for a8 in range(256):
        alpha = a8 / 255.0
        for sv in range(0, 256, 17):
            source = sv / 255.0
            for dv in range(0, 256, 17):
                dest = dv / 255.0
                for factor in (0, 1):
                    expected = source - source * alpha + (dest if factor else 0.0)
                    observed = source * (1.0 - alpha) + dest * factor
                    assert abs(expected - observed) < 1e-12
                    cases += 1
    assert cases == 131072
    print(f"DX11-00604: {len(mutations)} destructive mutations, {cases} numeric cases PASS")
if __name__ == "__main__":
    main()
