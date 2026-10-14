#!/usr/bin/env python3
"""DX11 00717 real game D3D9 alpha/color extrema -> native Draw/DrawIndexed OM."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
helper = (root/"src/vr/d3d11/live_game_blend_extrema.hpp").read_text()
workflow = (root/".github/workflows/dx11-fast-structural.yml").read_text()
capture = bridge.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
submit = bridge.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
def integrated(c,s,h):
    return all(x in c for x in (
        "game_native_extremum_admission(",
        "blendOp == D3DBLENDOP_MIN",
        "blendOp == D3DBLENDOP_MAX",
        "D3D11_BLEND_OP_MIN",
        "D3D11_BLEND_OP_MAX",
        "separate != FALSE, colorMask",
    )) and all(x in s for x in (
        "game_native_extremum_slot(",
        "s.extremumMaskedBlends[slot]",
        "desc.RenderTarget[0].BlendOp = output.blendOp;",
        "desc.RenderTarget[0].BlendOpAlpha = output.blendOp;",
        "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
        "dev->CreateBlendState(&desc, cached.GetAddressOf())",
        "maskedBlend = &cached;",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )) and all(x in h for x in (
        "(operation == 4u || operation == 5u)",
        "!separateAlpha",
        "(writeMask & 7u) != 0u",
        "return ((maximum ? 1u : 0u) * 4u + pairVariant) * 16u + writeMask;",
    ))
assert integrated(capture,submit,helper)
assert bridge.count("for (auto& masked : s.extremumMaskedBlends) masked.Reset();") == 2
assert "std::array<ComPtr<ID3D11BlendState>, 128> extremumMaskedBlends{};" in bridge
for poison in ("game_native_extremum_admission(", "blendOp == D3DBLENDOP_MIN",
               "separate != FALSE, colorMask"):
    assert not integrated(capture.replace(poison,"",1),submit,helper)
for poison in ("game_native_extremum_slot(", "desc.RenderTarget[0].BlendOpAlpha = output.blendOp;",
               "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
               "maskedBlend = &cached;"):
    # Restrict the mutation to the extrema OM branch; earlier independent
    # alpha and subtractive draws have similarly named statements.
    start = submit.index("} else if (output.blendOp == D3D11_BLEND_OP_MIN")
    end = submit.index("} else if (output.blendOp != D3D11_BLEND_OP_ADD)", start)
    assert not integrated(capture,submit[:start]+submit[start:end].replace(poison,"",1)+submit[end:],helper)
assert not integrated(capture,submit,helper.replace("!separateAlpha","true",1))
assert "test_dx11_game_blend_extrema_00717.py" in workflow
assert "dx11_game_blend_extrema_probe_00717.cpp" in workflow
print("PASS 00717: game menu/race MIN/MAX RGBA OM and masked native Draw/Indexed; fail-closed input")
