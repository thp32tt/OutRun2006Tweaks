#!/usr/bin/env python3
"""00598 live D3D9 multiplicative game draw -> native D3D11 OM regression."""
from pathlib import Path

S = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def section(s, start, end):
    i = s.find(start)
    j = s.find(end, i + len(start))
    return s[i:j] if i >= 0 and j > i else ""

def connected(s):
    output = section(s, "struct OutputCapture {", "struct ReadbackSlot {")
    state = section(s, "struct State {", "State& state()")
    pipe = section(s, "bool ensure_pipeline(", "bool supported_game_state(")
    capture = section(s, "bool supported_game_state(", "bool translate_vertices(")
    draw = section(s, "bool submit(", "void observe(")
    multiply_om = section(pipe, "// Multiplicative game overlays:",
                          "// Menu/vehicle/race complement modulation.")
    return (
        "bool multiplyBlend = false;" in output
        and "ComPtr<ID3D11BlendState> multiplyBlend;" in state
        and "std::array<ComPtr<ID3D11BlendState>, 16> multiplyMaskedBlends{};" in state
        and "s.multiplyBlend &&" in pipe
        and all(x in multiply_om for x in (
            "target.SrcBlend = D3D11_BLEND_DEST_COLOR;",
            "target.DestBlend = D3D11_BLEND_ZERO;",
            "target.SrcBlendAlpha = D3D11_BLEND_DEST_ALPHA;",
            "target.DestBlendAlpha = D3D11_BLEND_ZERO;",
            "dev->CreateBlendState(&blend, s.multiplyBlend.GetAddressOf())"))
        and all(x in capture for x in (
            "src == D3DBLEND_DESTCOLOR && dst == D3DBLEND_ZERO",
            "src == D3DBLEND_ZERO && dst == D3DBLEND_SRCCOLOR",
            "if (separate != FALSE) {",
            "!native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,",
            "output.separateAlphaBlend = true;",
            "if (blendOp != D3DBLENDOP_ADD) {",
            "if (!premultipliedAlpha && !multiply &&",
            "output.multiplyBlend = multiply;"))
        and all(x in draw for x in (
            "if (output.multiplyBlend && output.colorWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL)",
            "s.multiplyMaskedBlends[output.colorWriteMask]",
            # Scope masked-write proof to the multiplicative state, not
            # the new 00599 subtractive state's identically named mask.
            "s.multiplyBlend->GetDesc(&desc);\n            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
            "dev->CreateBlendState(&desc, cached.GetAddressOf())",
            "ctx->OMSetBlendState(s.multiplyBlend.Get(), nullptr, 0xffffffffu);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
        and s.count("s.multiplyBlend.Reset();") == 2
        and s.count("for (auto& masked : s.multiplyMaskedBlends) masked.Reset();") == 2
        and "return optedIn;" in s
    )

def main():
    s = S.read_text(encoding="utf-8")
    assert connected(s), "D3D9 multiply -> DX11 OM -> native draw/inset missing"
    mutations = (
        ("bool multiplyBlend = false;", "bool badMultiply = false;"),
        ("ComPtr<ID3D11BlendState> multiplyBlend;", "ComPtr<ID3D11BlendState> lostBlend;"),
        ("s.multiplyBlend &&", "true &&"),
        ("target.SrcBlend = D3D11_BLEND_DEST_COLOR;", "target.SrcBlend = D3D11_BLEND_ONE;"),
        ("target.DestBlend = D3D11_BLEND_ZERO;", "target.DestBlend = D3D11_BLEND_ONE;"),
        ("target.SrcBlendAlpha = D3D11_BLEND_DEST_ALPHA;", "target.SrcBlendAlpha = D3D11_BLEND_DEST_COLOR;"),
        ("dev->CreateBlendState(&blend, s.multiplyBlend.GetAddressOf())", "dev->CreateBlendState(&blend, s.alphaBlend.GetAddressOf())"),
        ("!native_game_separate_alpha(srcAlpha, dstAlpha, opAlpha,", "/* independent alpha validation lost */ false &&"),
        ("output.separateAlphaBlend = true;", "output.separateAlphaBlend = false;"),
        ("src == D3DBLEND_DESTCOLOR && dst == D3DBLEND_ZERO", "src == D3DBLEND_ONE && dst == D3DBLEND_ZERO"),
        ("src == D3DBLEND_ZERO && dst == D3DBLEND_SRCCOLOR", "src == D3DBLEND_ZERO && dst == D3DBLEND_ONE"),
        ("if (!premultipliedAlpha && !multiply &&", "if (!premultipliedAlpha && true &&"),
        ("output.multiplyBlend = multiply;", "output.multiplyBlend = false;"),
        ("s.multiplyMaskedBlends[output.colorWriteMask]", "s.maskedBlends[output.colorWriteMask]"),
        ("s.multiplyBlend->GetDesc(&desc);", "s.alphaBlend->GetDesc(&desc);"),
        ("s.multiplyBlend->GetDesc(&desc);\n            desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
         "s.multiplyBlend->GetDesc(&desc);\n            desc.RenderTarget[0].RenderTargetWriteMask = 0;"),
        ("ctx->OMSetBlendState(s.multiplyBlend.Get(), nullptr, 0xffffffffu);", "ctx->OMSetBlendState(nullptr, nullptr, 0xffffffffu);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "/* skipped indexed */"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "/* skipped linear */"),
    )
    for old, bad in mutations:
        assert old in s, old
        # An adjacent SRCALPHA/ZERO descriptor has its own ZERO factor;
        # mutate only the original 00598 multiplicative output-merger state.
        if old.startswith("target."):
            start = s.index("// Multiplicative game overlays:")
            end = s.index("// Menu/vehicle/race complement modulation.", start)
            block = s[start:end]
            assert old in block, "missing multiplicative OM anchor: " + old
            mutant = s[:start] + block.replace(old, bad, 1) + s[end:]
        else:
            mutant = s.replace(old, bad, 1)
        assert not connected(mutant), "escaped mutation: " + old
    # Both D3D9 blend choices yield source*destination on all RGBA channels.
    # D3D11 DEST_COLOR is not valid for the alpha blend slot; DEST_ALPHA is.
    cases = 0
    for src in range(0, 257, 8):
        for dst in range(0, 257, 8):
            a, b = src / 256.0, dst / 256.0
            d3d9_destcolor_zero = a*b + b*0
            d3d9_zero_srccolor = a*0 + b*a
            dx11_color_and_alpha = a*b + b*0
            assert abs(d3d9_destcolor_zero - dx11_color_and_alpha) < 1e-12
            assert abs(d3d9_zero_srccolor - dx11_color_and_alpha) < 1e-12
            cases += 1
    for src, dst in (("DESTCOLOR", "ZERO"), ("ZERO", "SRCCOLOR"),
                     ("ONE", "ZERO"), ("SRCALPHA", "ONE")):
        for op in ("ADD", "SUBTRACT"):
            for separate in (False, True):
                allow = not separate and op == "ADD" and (
                    (src, dst) in {("DESTCOLOR", "ZERO"), ("ZERO", "SRCCOLOR")})
                exact = not separate and op == "ADD" and (
                    (src == "DESTCOLOR" and dst == "ZERO") or
                    (src == "ZERO" and dst == "SRCCOLOR"))
                assert allow == exact
    assert cases == 1089
    print("00598 native multiply OM: 17 negative mutations, 1089 RGBA factors PASS")

if __name__ == "__main__":
    main()
