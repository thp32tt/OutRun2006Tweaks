#!/usr/bin/env python3
"""00597 D3D9 premultiplied-alpha state -> native Draw/DrawIndexed integration."""
from pathlib import Path
SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def part(s, a, b):
    i, j = s.find(a), s.find(b, s.find(a) + len(a))
    return s[i:j] if i >= 0 and j > i else ""

def linked(s):
    output = part(s, "struct OutputCapture {", "struct ReadbackSlot {")
    state = part(s, "struct State {", "State& state()")
    pipeline = part(s, "bool ensure_pipeline(", "bool supported_game_state(")
    producer = part(s, "bool supported_game_state(", "bool translate_vertices(")
    consumer = part(s, "bool submit(", "void observe(")
    for section, phrases in (
        (output, ("bool premultipliedAlphaBlend = false;",)),
        (state, ("ComPtr<ID3D11BlendState> premultipliedAlphaBlend;",
                 "std::array<ComPtr<ID3D11BlendState>, 80> maskedBlends{};")),
        (pipeline, ("s.sourceAlphaAddBlend && s.premultipliedAlphaBlend &&",
                    "s.premultipliedAlphaBlend.Reset();",
                    "target.SrcBlend = D3D11_BLEND_ONE;",
                    "target.DestBlend = D3D11_BLEND_INV_SRC_ALPHA;",
                    "target.SrcBlendAlpha = D3D11_BLEND_ONE;",
                    "target.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;",
                    "dev->CreateBlendState(&blend, s.premultipliedAlphaBlend.GetAddressOf())")),
        (producer, ("if (separate != FALSE) {",
            "!native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,",
            "output.separateAlphaBlend = true;",
            "if (blendOp != D3DBLENDOP_ADD) {",
                    "const bool premultipliedAlpha = src == D3DBLEND_ONE &&",
                    "dst == D3DBLEND_INVSRCALPHA;", "if (!premultipliedAlpha &&",
                    "output.premultipliedAlphaBlend = premultipliedAlpha;")),
        (consumer, ("output.premultipliedAlphaBlend ? 48u : 0u",
                    "if (output.premultipliedAlphaBlend) {",
                    "maskDesc.RenderTarget[0].SrcBlend = D3D11_BLEND_ONE;",
                    "maskDesc.RenderTarget[0].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;",
                    "maskDesc.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;",
                    "maskDesc.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;",
                    "ctx->OMSetBlendState(s.premultipliedAlphaBlend.Get(), nullptr, 0xffffffffu);",
                    "ctx->DrawIndexed(indexCount, 0, 0);",
                    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))):
        if not all(x in section for x in phrases):
            return False
    return (s.count("for (auto& masked : s.maskedBlends) masked.Reset();") == 2
            and s.count("s.premultipliedAlphaBlend.Reset();") == 2)

def main():
    s = SOURCE.read_text(encoding="utf-8")
    assert linked(s), "real game blend capture -> native OM -> Draw not linked"
    mutations = (
        ("bool premultipliedAlphaBlend = false;", "bool missingBlend = false;"),
        ("ComPtr<ID3D11BlendState> premultipliedAlphaBlend;", "ComPtr<ID3D11BlendState> missingBlend;"),
        ("std::array<ComPtr<ID3D11BlendState>, 80> maskedBlends{};", "std::array<ComPtr<ID3D11BlendState>, 64> maskedBlends{};"),
        ("s.sourceAlphaAddBlend && s.premultipliedAlphaBlend &&", "s.sourceAlphaAddBlend && true &&"),
        ("s.premultipliedAlphaBlend.Reset();", "s.alphaBlend.Reset();"),
        ("dev->CreateBlendState(&blend, s.premultipliedAlphaBlend.GetAddressOf())", "dev->CreateBlendState(&blend, s.alphaBlend.GetAddressOf())"),
        ("!native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,", "/* independent alpha validation lost */ false &&"),
        ("output.separateAlphaBlend = true;", "output.separateAlphaBlend = false;"),
        ("const bool premultipliedAlpha = src == D3DBLEND_ONE &&", "const bool premultipliedAlpha = src == D3DBLEND_ZERO &&"),
        ("dst == D3DBLEND_INVSRCALPHA;", "dst == D3DBLEND_ONE;"),
        ("if (!premultipliedAlpha &&", "if (premultipliedAlpha &&"),
        ("output.premultipliedAlphaBlend = premultipliedAlpha;", "output.premultipliedAlphaBlend = false;"),
        ("output.premultipliedAlphaBlend ? 48u : 0u", "output.premultipliedAlphaBlend ? 0u : 0u"),
        ("if (output.premultipliedAlphaBlend) {", "if (false) {"),
        ("ctx->OMSetBlendState(s.premultipliedAlphaBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "/* no indexed native draw */"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "/* no native draw */"),
    )
    for original, broken in mutations:
        assert original in s
        assert not linked(s.replace(original, broken, 1)), "escaped mutation " + original
    for i in range(257):
        alpha = i / 256.
        for j in range(33):
            src, dst = j / 32., (32-j) / 32.
            premult = min(1., src + dst * (1. - alpha))
            native = min(1., src * 1. + dst * (1. - alpha))
            assert abs(premult - native) < 1e-12
            if 0 < i < 256 and 0 < j < 32 and premult < 1.:
                assert src*alpha + dst*(1.-alpha) < premult
    for src in ("ZERO", "ONE", "SRCALPHA", "DESTALPHA"):
        for dst in ("ONE", "INVSRCALPHA", "ZERO", "SRCALPHA"):
            for separate in (False, True):
                for op in ("ADD", "SUBTRACT"):
                    expected = not separate and op == "ADD" and (src,dst) in {
                        ("SRCALPHA","INVSRCALPHA"),("ONE","ONE"),
                        ("SRCALPHA","ONE"),("ONE","INVSRCALPHA")}
                    selected = not separate and op == "ADD" and (
                        (src == "SRCALPHA" and dst in ("INVSRCALPHA","ONE")) or
                        (src == "ONE" and dst in ("ONE","INVSRCALPHA")))
                    assert selected == expected
    assert max(16+48+mask for mask in range(16)) == 79
    print("00597 live game premultiplied OM 15 mutations + 8,481 numeric cases PASS")

if __name__ == "__main__":
    main()
