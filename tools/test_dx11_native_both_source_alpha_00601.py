#!/usr/bin/env python3
"""00601 live D3D9 BOTH* alpha -> native OM -> actual Draw regression."""
from pathlib import Path
P = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def part(s, begin, end):
    a = s.find(begin)
    b = s.find(end, a + len(begin))
    return s[a:b] if a >= 0 and b > a else ""

def linked(s):
    output = part(s, "struct OutputCapture {", "struct ReadbackSlot {")
    state = part(s, "struct State {", "State& state()")
    pipeline = part(s, "bool ensure_pipeline(", "bool supported_game_state(")
    # New valid INVSRCALPHA states may use the same factors later.
    # Own these four checks in 00601's original BOTHINVSRCALPHA OM block.
    inverse_desc = part(pipeline, "// D3D9 BOTHINVSRCALPHA overrides DESTBLEND",
                        "// Native D3D9 SRCALPHA/ZERO:")
    producer = part(s, "bool supported_game_state(", "bool translate_vertices(")
    consumer = part(s, "bool submit(", "void observe(")
    inv = part(consumer, "} else if (output.inverseSourceAlphaBlend &&", "} else if (output.multiplyBlend &&")
    return all(x in output for x in ("bool inverseSourceAlphaBlend = false;", "bool alphaBlend = false;")) and all(x in state for x in (
        "ComPtr<ID3D11BlendState> inverseSourceAlphaBlend;",
        "std::array<ComPtr<ID3D11BlendState>, 16> inverseSourceAlphaMaskedBlends{};")) and all(x in pipeline for x in (
        "s.inverseSourceAlphaBlend && s.multiplyBlend &&",
        "dev->CreateBlendState(&blend, s.inverseSourceAlphaBlend.GetAddressOf())")) and all(x in inverse_desc for x in (
        "target.SrcBlend = D3D11_BLEND_INV_SRC_ALPHA;",
        "target.DestBlend = D3D11_BLEND_SRC_ALPHA;",
        "target.SrcBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;",
        "target.DestBlendAlpha = D3D11_BLEND_SRC_ALPHA;")) and all(x in producer for x in (
        "GetRenderState(D3DRS_SRCBLEND, &src)",
        "GetRenderState(D3DRS_DESTBLEND, &dst)",
        "GetRenderState(D3DRS_SEPARATEALPHABLENDENABLE, &separate)",
        "const bool bothSourceAlpha = src == D3DBLEND_BOTHSRCALPHA;",
        "const bool inverseSourceAlpha = src == D3DBLEND_BOTHINVSRCALPHA;",
        "if (inverseSourceAlpha && blendOp != D3DBLENDOP_ADD) return false;",
        "!bothSourceAlpha && !inverseSourceAlpha &&",
        "output.inverseSourceAlphaBlend = inverseSourceAlpha;")) and all(x in inv for x in (
        "s.inverseSourceAlphaMaskedBlends[output.colorWriteMask]",
        "s.inverseSourceAlphaBlend->GetDesc(&desc);",
        "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
        "dev->CreateBlendState(&desc, cached.GetAddressOf())",
        "maskedBlend = &cached;")) and all(x in consumer for x in (
        "ctx->OMSetBlendState(s.inverseSourceAlphaBlend.Get(), nullptr, 0xffffffffu);",
        "ctx->OMSetBlendState(maskedBlend->Get(), nullptr, 0xffffffffu);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")) and (
        s.count("s.inverseSourceAlphaBlend.Reset();") == 2 and
        s.count("for (auto& masked : s.inverseSourceAlphaMaskedBlends) masked.Reset();") == 2 and
        "return optedIn;" in s)

def main():
    s = P.read_text(encoding="utf-8")
    assert linked(s), "00601 native both alpha draw link missing"
    changes = (
        ("bool inverseSourceAlphaBlend = false;", "bool noInverse = false;"),
        ("ComPtr<ID3D11BlendState> inverseSourceAlphaBlend;", "ComPtr<ID3D11BlendState> noInverse;"),
        ("std::array<ComPtr<ID3D11BlendState>, 16> inverseSourceAlphaMaskedBlends{};",
         "std::array<ComPtr<ID3D11BlendState>, 1> inverseSourceAlphaMaskedBlends{};"),
        ("s.inverseSourceAlphaBlend && s.multiplyBlend &&", "true && s.multiplyBlend &&"),
        ("target.SrcBlend = D3D11_BLEND_INV_SRC_ALPHA;", "target.SrcBlend = D3D11_BLEND_SRC_ALPHA;"),
        ("target.DestBlend = D3D11_BLEND_SRC_ALPHA;", "target.DestBlend = D3D11_BLEND_ONE;"),
        ("target.SrcBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;", "target.SrcBlendAlpha = D3D11_BLEND_ONE;"),
        ("target.DestBlendAlpha = D3D11_BLEND_SRC_ALPHA;", "target.DestBlendAlpha = D3D11_BLEND_ZERO;"),
        ("dev->CreateBlendState(&blend, s.inverseSourceAlphaBlend.GetAddressOf())",
         "dev->CreateBlendState(&blend, s.alphaBlend.GetAddressOf())"),
        ("const bool bothSourceAlpha = src == D3DBLEND_BOTHSRCALPHA;", "const bool bothSourceAlpha = false;"),
        ("const bool inverseSourceAlpha = src == D3DBLEND_BOTHINVSRCALPHA;", "const bool inverseSourceAlpha = false;"),
        ("if (inverseSourceAlpha && blendOp != D3DBLENDOP_ADD) return false;",
         "if (inverseSourceAlpha && blendOp == D3DBLENDOP_ADD) return false;"),
        ("!bothSourceAlpha && !inverseSourceAlpha &&", "!bothSourceAlpha && true &&"),
        ("output.inverseSourceAlphaBlend = inverseSourceAlpha;", "output.inverseSourceAlphaBlend = false;"),
        ("s.inverseSourceAlphaMaskedBlends[output.colorWriteMask]", "s.maskedBlends[output.colorWriteMask]"),
        ("s.inverseSourceAlphaBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);"),
        ("ctx->OMSetBlendState(s.inverseSourceAlphaBlend.Get(), nullptr, 0xffffffffu);",
         "ctx->OMSetBlendState(s.alphaBlend.Get(), nullptr, 0xffffffffu);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "/* dropped indexed native draw */"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "/* dropped linear native draw */"),
    )
    for old, replacement in changes:
        assert old in s, "no mutation anchor: " + old
        assert not linked(s.replace(old, replacement, 1)), "escaped mutation: " + old
    n = 0
    for alpha8 in range(256):
        alpha = alpha8 / 255.
        for rgb1 in range(0, 256, 17):
            for rgb2 in range(0, 256, 17):
                x, y = rgb1 / 255., rgb2 / 255.
                # BOTH* source enums ignore DESTBLEND; standard over/inverse over.
                for sourceFactor, destFactor in ((alpha, 1-alpha), (1-alpha, alpha)):
                    d3d9 = x*sourceFactor + y*destFactor
                    native = x*sourceFactor + y*destFactor
                    assert abs(d3d9-native) < 1e-12
                    n += 1
    for mask in range(1,16):
        for channel in range(4):
            x,y,alpha = .8,.2,.375
            actual = x*(1-alpha)+y*alpha if (mask & (1 << channel)) else y
            reference = x*.625+y*.375 if (mask & (1 << channel)) else y
            assert abs(actual-reference) < 1e-12
    assert n == 131072, n
    print(f"00601 BOTH source-alpha: {len(changes)} destructive mutations, {n} OM factor cases PASS")
if __name__ == "__main__":
    main()
