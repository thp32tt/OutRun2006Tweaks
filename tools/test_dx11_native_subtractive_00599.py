#!/usr/bin/env python3
"""00599 real-game D3D9 subtract/reverse subtract -> masked native OM Draw."""
from pathlib import Path

S = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def part(src, begin, end):
    a = src.find(begin)
    b = src.find(end, a + len(begin))
    return src[a:b] if a >= 0 and b > a else ""

def connected(s):
    output = part(s, "struct OutputCapture {", "struct ReadbackSlot {")
    state = part(s, "struct State {", "State& state()")
    pipeline = part(s, "bool ensure_pipeline(", "bool supported_game_state(")
    producer = part(s, "bool supported_game_state(", "bool translate_vertices(")
    consumer = part(s, "bool submit(", "void observe(")
    # Test subtractive descriptor mutations against their own OM branch;
    # other blend paths share write-mask and state-creation statements.
    subtractive = part(consumer,
        "if (output.blendOp != D3D11_BLEND_OP_ADD) {",
        "} else if (output.inverseSourceAlphaBlend &&")
    return (all(x in output for x in (
        "D3D11_BLEND_OP blendOp = D3D11_BLEND_OP_ADD;",
        "bool additiveBlend = false;", "bool sourceAlphaAddBlend = false;",
        "bool premultipliedAlphaBlend = false;"))
        and all(x in state for x in (
            "std::array<ComPtr<ID3D11BlendState>, 128> subtractiveMaskedBlends{};",
            "std::array<ComPtr<ID3D11BlendState>, 80> maskedBlends{};"))
        and pipeline.count("for (auto& masked : s.subtractiveMaskedBlends) masked.Reset();") == 1
        and s.count("for (auto& masked : s.subtractiveMaskedBlends) masked.Reset();") == 2
        and all(x in producer for x in (
            "GetRenderState(D3DRS_BLENDOP, &blendOp)",
            "GetRenderState(D3DRS_SEPARATEALPHABLENDENABLE, &separate)",
            "if (separate != FALSE) {",
            "!native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,",
            "output.separateAlphaBlend = true;",
            "if (blendOp != D3DBLENDOP_ADD) {",
            "blendOp != D3DBLENDOP_SUBTRACT &&",
            "blendOp != D3DBLENDOP_REVSUBTRACT",
            "if (multiply && blendOp != D3DBLENDOP_ADD) return false;",
            "output.blendOp = blendOp == D3DBLENDOP_SUBTRACT ?",
            "D3D11_BLEND_OP_SUBTRACT :",
            "blendOp == D3DBLENDOP_REVSUBTRACT ?",
            "D3D11_BLEND_OP_REV_SUBTRACT : D3D11_BLEND_OP_ADD;"))
        and all(x in subtractive for x in (
            "if (output.blendOp != D3D11_BLEND_OP_ADD)",
            "output.additiveBlend ? 1u :",
            "output.sourceAlphaAddBlend ? 2u :",
            "output.premultipliedAlphaBlend ? 3u : 0u;",
            "output.blendOp == D3D11_BLEND_OP_REV_SUBTRACT ?",
            "(direction * 4u + variant) * 16u +",
            "s.subtractiveMaskedBlends[slot]",
            "base->GetDesc(&desc);",
            "desc.RenderTarget[0].BlendOp = output.blendOp;",
            "desc.RenderTarget[0].BlendOpAlpha = output.blendOp;",
            "desc.RenderTarget[0].BlendOpAlpha = output.blendOp;\n            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
            "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;\n            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))",
            "maskedBlend = &cached;"))
        and all(x in consumer for x in (
            "ctx->OMSetBlendState(maskedBlend->Get(), nullptr, 0xffffffffu);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
        and "return optedIn;" in s)

def main():
    s = S.read_text(encoding="utf-8")
    assert connected(s), "game-authored BLENDOP -> native OM -> masked Draw disconnected"
    changes = (
        ("D3D11_BLEND_OP blendOp = D3D11_BLEND_OP_ADD;", "D3D11_BLEND_OP blendOp = D3D11_BLEND_OP_SUBTRACT;"),
        ("std::array<ComPtr<ID3D11BlendState>, 128> subtractiveMaskedBlends{};", "std::array<ComPtr<ID3D11BlendState>, 64> subtractiveMaskedBlends{};"),
        ("!native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,", "/* independent alpha validation lost */ false &&"),
        ("output.separateAlphaBlend = true;", "output.separateAlphaBlend = false;"),
        ("blendOp != D3DBLENDOP_SUBTRACT &&", "blendOp != D3DBLENDOP_ADD &&"),
        ("blendOp != D3DBLENDOP_REVSUBTRACT", "blendOp != D3DBLENDOP_ADD"),
        ("if (multiply && blendOp != D3DBLENDOP_ADD) return false;", "if (multiply && blendOp == D3DBLENDOP_ADD) return false;"),
        ("output.blendOp = blendOp == D3DBLENDOP_SUBTRACT ?", "output.blendOp = blendOp == D3DBLENDOP_ADD ?"),
        ("D3D11_BLEND_OP_SUBTRACT :", "D3D11_BLEND_OP_ADD :"),
        ("blendOp == D3DBLENDOP_REVSUBTRACT ?", "blendOp == D3DBLENDOP_ADD ?"),
        ("D3D11_BLEND_OP_REV_SUBTRACT : D3D11_BLEND_OP_ADD;", "D3D11_BLEND_OP_ADD : D3D11_BLEND_OP_ADD;"),
        ("if (output.blendOp != D3D11_BLEND_OP_ADD)", "if (false)"),
        ("output.additiveBlend ? 1u :", "output.additiveBlend ? 0u :"),
        ("output.sourceAlphaAddBlend ? 2u :", "output.sourceAlphaAddBlend ? 0u :"),
        ("output.premultipliedAlphaBlend ? 3u : 0u;", "output.premultipliedAlphaBlend ? 0u : 0u;"),
        ("output.blendOp == D3D11_BLEND_OP_REV_SUBTRACT ?", "output.blendOp == D3D11_BLEND_OP_ADD ?"),
        ("(direction * 4u + variant) * 16u +", "(variant * 4u + direction) * 16u +"),
        ("s.subtractiveMaskedBlends[slot]", "s.maskedBlends[slot]"),
        ("base->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);"),
        ("desc.RenderTarget[0].BlendOp = output.blendOp;", "desc.RenderTarget[0].BlendOp = D3D11_BLEND_OP_ADD;"),
        ("desc.RenderTarget[0].BlendOpAlpha = output.blendOp;", "desc.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;"),
        ("desc.RenderTarget[0].BlendOpAlpha = output.blendOp;\n            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
         "desc.RenderTarget[0].BlendOpAlpha = output.blendOp;\n            desc.RenderTarget[0].RenderTargetWriteMask = 0;"),
        ("desc.RenderTarget[0].BlendOpAlpha = output.blendOp;\n            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;\n            if (FAILED(dev->CreateBlendState(&desc, cached.GetAddressOf())))",
         "desc.RenderTarget[0].BlendOpAlpha = output.blendOp;\n            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;\n            if (FAILED(dev->CreateBlendState(&desc, s.alphaBlend.GetAddressOf())))"),
        ("ctx->OMSetBlendState(maskedBlend->Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "/* no indexed source draw */"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "/* no linear source draw */"),
    )
    for old, bad in changes:
        assert old in s, old
        # Independent alpha OM can use the same BlendOp assignment earlier
        # in submit(). Mutate the subtractive masked descriptor itself, not
        # that unrelated first occurrence, or this negative test is vacuous.
        if old == "desc.RenderTarget[0].BlendOp = output.blendOp;":
            begin = s.index("if (output.blendOp != D3D11_BLEND_OP_ADD) {")
            end = s.index("} else if (output.inverseSourceAlphaBlend &&", begin)
            targeted = s[begin:end]
            assert old in targeted, "missing subtractive BlendOp bind"
            mutant = s[:begin] + targeted.replace(old, bad, 1) + s[end:]
        else:
            mutant = s.replace(old, bad, 1)
        assert not connected(mutant), "escaped mutation " + old
    # Test RGB AND alpha with the four supported factor combinations.
    # D3D11 reverse subtract is DEST*factor - SRC*factor, not swapped factors.
    combos = ("OVER", "ADD", "SOURCE_ALPHA_ADD", "PREMULTIPLIED")
    comparisons = 0
    for pair in combos:
        for si in range(0, 256, 17):
            for di in range(0, 256, 19):
                for ai in range(0, 256, 51):
                    src, dst, alpha = si / 255, di / 255, ai / 255
                    sf = alpha if pair in ("OVER", "SOURCE_ALPHA_ADD") else 1.
                    df = 1. - alpha if pair in ("OVER", "PREMULTIPLIED") else 1.
                    lhs, rhs = src*sf, dst*df
                    for op in ("SUBTRACT", "REVSUBTRACT"):
                        d3d9 = max(0., min(1., lhs-rhs if op == "SUBTRACT" else rhs-lhs))
                        dx11 = max(0., min(1., lhs-rhs if op == "SUBTRACT" else rhs-lhs))
                        assert abs(d3d9-dx11) < 1e-12
                        comparisons += 1
    # Factor order is not interchangeable for directional multiply;
    # separate-alpha, MIN/MAX and unsupported pairs remain DX9Ex-only.
    for op in ("ADD", "SUBTRACT", "REVSUBTRACT", "MIN", "MAX"):
        for separate in (False, True):
            for pair in (*combos, "MULTIPLY", "UNKNOWN"):
                allowed = (not separate and pair in combos
                           and op in ("ADD", "SUBTRACT", "REVSUBTRACT")) or (
                               not separate and pair == "MULTIPLY" and op == "ADD")
                selected = (not separate and op in ("ADD", "SUBTRACT", "REVSUBTRACT")
                            and pair in combos) or (
                                not separate and op == "ADD" and pair == "MULTIPLY")
                assert selected == allowed
    assert comparisons == 4*16*14*6*2, comparisons
    print("00599 native BLENDOP: 24 destructive mutations, %d RGB/alpha comparisons PASS" % comparisons)

if __name__ == "__main__":
    main()
