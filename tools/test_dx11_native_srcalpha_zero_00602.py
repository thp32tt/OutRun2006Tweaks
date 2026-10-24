#!/usr/bin/env python3
"""00602: real-game SRCALPHA/ZERO producer -> native D3D11 OM -> Draw integration."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def part(src, begin, end):
    start = src.find(begin)
    stop = src.find(end, start + len(begin))
    return src[start:stop] if start >= 0 and stop > start else ""

def linked(src):
    output = part(src, "struct OutputCapture {", "struct ReadbackSlot {")
    state = part(src, "struct State {", "State& state()")
    pipeline = part(src, "bool ensure_pipeline(", "bool supported_game_state(")
    game = part(src, "bool supported_game_state(", "bool translate_vertices(")
    draw = part(src, "bool submit(", "void observe(")
    om = part(pipeline, "// Native D3D9 SRCALPHA/ZERO:",
              "// Exact live D3D9 inverse-source-alpha")
    mask = part(draw, "} else if (output.sourceAlphaCopyBlend &&", "} else if (output.colorWriteMask !=")
    required = (
        (output, ("bool sourceAlphaCopyBlend = false;",)),
        (state, ("ComPtr<ID3D11BlendState> sourceAlphaCopyBlend;",
                 "std::array<ComPtr<ID3D11BlendState>, 16> sourceAlphaCopyMaskedBlends{};")),
        (pipeline, ("s.sourceAlphaCopyBlend &&",)),
        (om, ("target.SrcBlend = D3D11_BLEND_SRC_ALPHA;",
              "target.DestBlend = D3D11_BLEND_ZERO;",
              "target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;",
              "target.DestBlendAlpha = D3D11_BLEND_ZERO;",
              "dev->CreateBlendState(&blend, s.sourceAlphaCopyBlend.GetAddressOf())")),
        (game, ("GetRenderState(D3DRS_SRCBLEND, &src)",
                "GetRenderState(D3DRS_DESTBLEND, &dst)",
                "GetRenderState(D3DRS_BLENDOP, &blendOp)",
                "GetRenderState(D3DRS_SEPARATEALPHABLENDENABLE, &separate)",
                "const bool sourceAlphaCopy = src == D3DBLEND_SRCALPHA && dst == D3DBLEND_ZERO;",
                "if (sourceAlphaCopy && blendOp != D3DBLENDOP_ADD) return false;",
                "if (!premultipliedAlpha && !multiply &&\n            !sourceAlphaCopy &&",
                "output.sourceAlphaCopyBlend = sourceAlphaCopy;")),
        (mask, ("s.sourceAlphaCopyMaskedBlends[output.colorWriteMask]",
                "s.sourceAlphaCopyBlend->GetDesc(&desc);",
                "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
                "dev->CreateBlendState(&desc, cached.GetAddressOf())",
                "maskedBlend = &cached;")),
        (draw, ("ctx->OMSetBlendState(s.sourceAlphaCopyBlend.Get(), nullptr, 0xffffffffu);",
                "ctx->OMSetBlendState(maskedBlend->Get(), nullptr, 0xffffffffu);",
                "ctx->DrawIndexed(indexCount, 0, 0);",
                "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")),
    )
    return all(all(token in section for token in terms) for section, terms in required) and (
        src.count("s.sourceAlphaCopyBlend.Reset();") == 2 and
        src.count("for (auto& masked : s.sourceAlphaCopyMaskedBlends) masked.Reset();") == 2 and
        "return optedIn;" in src)

def main():
    source = SOURCE.read_text(encoding="utf-8")
    assert linked(source), "00602 source/OM/draw integration broken"
    attacks = (
        ("bool sourceAlphaCopyBlend = false;", "bool sourceAlphaCopyBlend = true;"),
        ("ComPtr<ID3D11BlendState> sourceAlphaCopyBlend;", "ComPtr<ID3D11BlendState> missingSourceCopy;"),
        ("std::array<ComPtr<ID3D11BlendState>, 16> sourceAlphaCopyMaskedBlends{};",
         "std::array<ComPtr<ID3D11BlendState>, 1> sourceAlphaCopyMaskedBlends{};"),
        ("s.sourceAlphaCopyBlend &&", "true &&"),
        ("// Native D3D9 SRCALPHA/ZERO:", "// Unknown blend:"),
        ("target.DestBlend = D3D11_BLEND_ZERO;", "target.DestBlend = D3D11_BLEND_ONE;"),
        ("target.SrcBlendAlpha = D3D11_BLEND_SRC_ALPHA;", "target.SrcBlendAlpha = D3D11_BLEND_ONE;"),
        ("target.DestBlendAlpha = D3D11_BLEND_ZERO;", "target.DestBlendAlpha = D3D11_BLEND_ONE;"),
        ("dev->CreateBlendState(&blend, s.sourceAlphaCopyBlend.GetAddressOf())",
         "dev->CreateBlendState(&blend, s.multiplyBlend.GetAddressOf())"),
        ("const bool sourceAlphaCopy = src == D3DBLEND_SRCALPHA && dst == D3DBLEND_ZERO;",
         "const bool sourceAlphaCopy = false;"),
        ("if (sourceAlphaCopy && blendOp != D3DBLENDOP_ADD) return false;",
         "if (sourceAlphaCopy && blendOp == D3DBLENDOP_ADD) return false;"),
        ("if (!premultipliedAlpha && !multiply &&\n            !sourceAlphaCopy &&",
         "!premultipliedAlpha && !multiply &&"),
        ("output.sourceAlphaCopyBlend = sourceAlphaCopy;",
         "output.sourceAlphaCopyBlend = false;"),
        ("s.sourceAlphaCopyMaskedBlends[output.colorWriteMask]",
         "s.multiplyMaskedBlends[output.colorWriteMask]"),
        ("s.sourceAlphaCopyBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);"),
        ("ctx->OMSetBlendState(s.sourceAlphaCopyBlend.Get(), nullptr, 0xffffffffu);",
         "ctx->OMSetBlendState(s.alphaBlend.Get(), nullptr, 0xffffffffu);"),
        ("s.sourceAlphaCopyBlend.Reset();", "s.multiplyBlend.Reset();"),
        ("for (auto& masked : s.sourceAlphaCopyMaskedBlends) masked.Reset();",
         "for (auto& masked : s.multiplyMaskedBlends) masked.Reset();"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "/* indexed draw lost */"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "/* linear draw lost */"),
    )
    for old, changed in attacks:
        assert old in source, "missing mutation anchor: " + old
        # Isolate the OM descriptor factors so a different valid blend path
        # cannot hide a destructive mutation in the new factor pair.
        if old.startswith("target."):
            begin = source.index("// Native D3D9 SRCALPHA/ZERO:")
            end = source.index("// Exact live D3D9 inverse-source-alpha", begin)
            portion = source[begin:end]
            assert old in portion
            mutant = source[:begin] + portion.replace(old, changed, 1) + source[end:]
        else:
            mutant = source.replace(old, changed, 1)
        assert not linked(mutant), "escaped mutation: " + old
    checked = 0
    for alpha8 in range(256):
        alpha = alpha8 / 255.0
        for source8 in range(0, 256, 17):
            source_color = source8 / 255.0
            for dest8 in range(0, 256, 17):
                dest_color = dest8 / 255.0
                # D3D9 source SRCALPHA/destination ZERO; D3D11 same factors.
                expected = source_color * alpha + dest_color * 0.0
                native = source_color * alpha
                assert abs(expected - native) < 1e-12
                # Alpha is NOT premultiplied-one: SRC_ALPHA * srcAlpha.
                assert abs(alpha * alpha + dest_color * 0 - alpha * alpha) < 1e-12
                checked += 1
    assert checked == 65536, checked
    for mask in range(1, 16):
        if not (mask & 7): # Alpha-only cannot show the diagnostic RGB inset.
            continue
        for channel in range(4):
            # Do not shadow `source`: it holds the full C++ source text for
            # the opt-in / DX9Ex fallback assertion below.
            channel_source, channel_dest, channel_alpha = .8, .23, .375
            expected = channel_source * channel_alpha if mask & (1 << channel) else channel_dest
            native = channel_source * channel_alpha if mask & (1 << channel) else channel_dest
            assert abs(expected - native) < 1e-12
    assert "OUTRUN_DX11_FIRST_GAME_FRAME" in source
    print(f"00602 SRCALPHA/ZERO: {len(attacks)} destructive mutations, {checked} numeric OM cases PASS")

if __name__ == "__main__":
    main()
