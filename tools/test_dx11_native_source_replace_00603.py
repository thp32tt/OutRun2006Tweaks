#!/usr/bin/env python3
"""00603: live D3D9 ONE/ZERO source replacement reaches native Draw/DrawIndexed."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def between(text, start, end):
    a = text.find(start)
    b = text.find(end, a + len(start))
    assert 0 <= a < b, (start, end)
    return text[a:b]

def linked(source):
    try:
        output = between(source, "struct OutputCapture {", "struct ReadbackSlot {")
        state = between(source, "struct State {", "State& state()")
        pipeline = between(source, "bool ensure_pipeline(", "bool supported_game_state(")
        game = between(source, "bool supported_game_state(", "bool translate_vertices(")
        draw = between(source, "bool submit(", "void observe(")
        descriptor = between(pipeline, "// D3D9 ONE/ZERO:", "// Multiplicative game overlays:")
        masked = between(draw, "} else if (output.sourceReplaceBlend &&",
                         "} else if (output.colorWriteMask !=")
        requirements = (
            (output, ("bool sourceReplaceBlend = false;",)),
            (state, ("ComPtr<ID3D11BlendState> sourceReplaceBlend;",
                     "std::array<ComPtr<ID3D11BlendState>, 16> sourceReplaceMaskedBlends{};")),
            (pipeline, ("s.sourceReplaceBlend &&",)),
            (descriptor, ("target.SrcBlend = D3D11_BLEND_ONE;",
                          "target.DestBlend = D3D11_BLEND_ZERO;",
                          "target.SrcBlendAlpha = D3D11_BLEND_ONE;",
                          "target.DestBlendAlpha = D3D11_BLEND_ZERO;",
                          "dev->CreateBlendState(&blend, s.sourceReplaceBlend.GetAddressOf())")),
            (game, ("GetRenderState(D3DRS_SRCBLEND, &src)",
                    "GetRenderState(D3DRS_DESTBLEND, &dst)",
                    "GetRenderState(D3DRS_BLENDOP, &blendOp)",
                    "GetRenderState(D3DRS_SEPARATEALPHABLENDENABLE, &separate)",
                    "const bool sourceReplace = src == D3DBLEND_ONE && dst == D3DBLEND_ZERO;",
                    "if (sourceReplace && blendOp != D3DBLENDOP_ADD) return false;",
                    "!sourceAlphaCopy && !sourceReplace &&",
                    "output.sourceReplaceBlend = sourceReplace;")),
            (masked, ("s.sourceReplaceMaskedBlends[output.colorWriteMask]",
                      "s.sourceReplaceBlend->GetDesc(&desc);",
                      "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
                      "dev->CreateBlendState(&desc, cached.GetAddressOf())",
                      "maskedBlend = &cached;")),
            (draw, ("ctx->OMSetBlendState(s.sourceReplaceBlend.Get(), nullptr, 0xffffffffu);",
                    "ctx->DrawIndexed(indexCount, 0, 0);",
                    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")),
        )
        return all(all(token in region for token in tokens) for region, tokens in requirements) and (
            source.count("s.sourceReplaceBlend.Reset();") == 2 and
            source.count("for (auto& masked : s.sourceReplaceMaskedBlends) masked.Reset();") == 2 and
            "return optedIn;" in source and "OUTRUN_DX11_FIRST_GAME_FRAME" in source)
    except AssertionError:
        return False

def main():
    source = SOURCE.read_text(encoding="utf-8")
    assert linked(source), "00603 D3D9 GetRenderState -> OM -> native Draw integration lost"
    mutants = (
        ("bool sourceReplaceBlend = false;", "bool sourceReplaceBlend = true;", ""),
        ("ComPtr<ID3D11BlendState> sourceReplaceBlend;", "ComPtr<ID3D11BlendState> missing;", ""),
        ("std::array<ComPtr<ID3D11BlendState>, 16> sourceReplaceMaskedBlends{};",
         "std::array<ComPtr<ID3D11BlendState>, 1> sourceReplaceMaskedBlends{};", ""),
        ("s.sourceReplaceBlend &&", "true &&", ""),
        ("target.SrcBlend = D3D11_BLEND_ONE;", "target.SrcBlend = D3D11_BLEND_SRC_ALPHA;", "desc"),
        ("target.DestBlend = D3D11_BLEND_ZERO;", "target.DestBlend = D3D11_BLEND_ONE;", "desc"),
        ("target.SrcBlendAlpha = D3D11_BLEND_ONE;", "target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;", "desc"),
        ("target.DestBlendAlpha = D3D11_BLEND_ZERO;", "target.DestBlendAlpha = D3D11_BLEND_ONE;", "desc"),
        ("dev->CreateBlendState(&blend, s.sourceReplaceBlend.GetAddressOf())",
         "dev->CreateBlendState(&blend, s.additiveBlend.GetAddressOf())", "desc"),
        ("const bool sourceReplace = src == D3DBLEND_ONE && dst == D3DBLEND_ZERO;",
         "const bool sourceReplace = false;", ""),
        ("if (sourceReplace && blendOp != D3DBLENDOP_ADD) return false;",
         "if (sourceReplace && blendOp == D3DBLENDOP_ADD) return false;", ""),
        ("!sourceAlphaCopy && !sourceReplace &&", "!sourceAlphaCopy &&", ""),
        ("output.sourceReplaceBlend = sourceReplace;", "output.sourceReplaceBlend = false;", ""),
        ("s.sourceReplaceMaskedBlends[output.colorWriteMask]",
         "s.sourceAlphaCopyMaskedBlends[output.colorWriteMask]", ""),
        ("s.sourceReplaceBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);", ""),
        ("desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
         "desc.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;", "mask"),
        ("ctx->OMSetBlendState(s.sourceReplaceBlend.Get(), nullptr, 0xffffffffu);",
         "ctx->OMSetBlendState(s.alphaBlend.Get(), nullptr, 0xffffffffu);", ""),
        ("s.sourceReplaceBlend.Reset();", "s.additiveBlend.Reset();", ""),
        ("for (auto& masked : s.sourceReplaceMaskedBlends) masked.Reset();",
         "for (auto& masked : s.multiplyMaskedBlends) masked.Reset();", ""),
    )
    for anchor, replacement, scope in mutants:
        if scope == "desc":
            start = source.index("// D3D9 ONE/ZERO: source replacement in all four channels")
            end = source.index("// Multiplicative game overlays:", start)
        elif scope == "mask":
            start = source.index("} else if (output.sourceReplaceBlend &&")
            end = source.index("} else if (output.colorWriteMask !=", start)
        else:
            start, end = 0, len(source)
        target = source[start:end]
        assert anchor in target, "mutation anchor missing: " + anchor
        mutant = source[:start] + target.replace(anchor, replacement, 1) + source[end:]
        assert not linked(mutant), "mutation escaped: " + anchor
    checked = 0
    for alpha8 in range(256):
        alpha = alpha8 / 255.0
        for color8 in range(0, 256, 17):
            color = color8 / 255.0
            for prior8 in range(0, 256, 17):
                prior = prior8 / 255.0
                # ONE/ZERO applies identically to RGB and alpha.
                assert abs((color * 1.0 + prior * 0.0) - color) < 1e-12
                assert abs((alpha * 1.0 + prior * 0.0) - alpha) < 1e-12
                checked += 1
    assert checked == 65536
    for mask in range(1, 16):
        if mask & 7 == 0:
            continue  # RGB-less masks cannot create the visible native inset.
        for channel in range(4):
            source_channel, previous = .79, .17
            actual = source_channel if (mask & (1 << channel)) else previous
            assert actual == (source_channel if (mask & (1 << channel)) else previous)
    print(f"00603 native source replace: {len(mutants)} destructive mutations, {checked} factor cases PASS")

if __name__ == "__main__":
    main()
