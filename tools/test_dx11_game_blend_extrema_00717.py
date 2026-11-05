#!/usr/bin/env python3
"""00717: game D3D9 MIN/MAX blended native RGBA OM + exact game Draw fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
helper = (root/"src/vr/d3d11/live_game_blend_extrema.hpp").read_text()
workflow = (root/".github/workflows/dx11-fast-structural.yml").read_text()
capture = bridge.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
submit = bridge.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
def integrated(c,s,h):
    gate = c.split("const bool extrema =",1)[1].split("// Only exact known-good",1)[0]
    mapping = c.split("if (extrema) output.blendOp = blendOp",1)[1].split(";",1)[0]
    om = s.split("} else if (output.blendOp == D3D11_BLEND_OP_MIN",1)[1].split(
        "} else if (output.blendOp != D3D11_BLEND_OP_ADD)",1)[0]
    return all(x in gate for x in (
        "blendOp == D3DBLENDOP_MIN", "blendOp == D3DBLENDOP_MAX",
        "game_native_extremum_admission(",
        "separate != FALSE, colorMask",
    )) and all(x in mapping for x in (
        "D3D11_BLEND_OP_MIN", "D3D11_BLEND_OP_MAX",
    )) and all(x in om for x in (
        "game_native_extremum_slot(",
        "s.extremumMaskedBlends[slot]",
        "desc.RenderTarget[0].BlendOp = output.blendOp;",
        "desc.RenderTarget[0].BlendOpAlpha = output.blendOp;",
        "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
        "dev->CreateBlendState(&desc, cached.GetAddressOf())",
        "maskedBlend = &cached;",
    )) and all(x in s for x in (
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )) and all(x in h for x in (
        "(operation == 4u || operation == 5u)",
        "!separateAlpha", "(writeMask & 7u) != 0u",
        "return ((maximum ? 1u : 0u) * 4u + pairVariant) * 16u + writeMask;",
    ))
assert integrated(capture,submit,helper)
assert bridge.count("for (auto& masked : s.extremumMaskedBlends) masked.Reset();") == 2
assert "std::array<ComPtr<ID3D11BlendState>, 128> extremumMaskedBlends{};" in bridge
for poison in ("game_native_extremum_admission(", "blendOp == D3DBLENDOP_MIN",
               "blendOp == D3DBLENDOP_MAX", "separate != FALSE, colorMask"):
    assert not integrated(capture.replace(poison,"",1),submit,helper)
for poison in ("game_native_extremum_slot(",
               "desc.RenderTarget[0].BlendOpAlpha = output.blendOp;",
               "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;",
               "maskedBlend = &cached;"):
    start = submit.index("} else if (output.blendOp == D3D11_BLEND_OP_MIN")
    end = submit.index("} else if (output.blendOp != D3D11_BLEND_OP_ADD)",start)
    mutated = submit[:start] + submit[start:end].replace(poison,"",1) + submit[end:]
    assert not integrated(capture,mutated,helper)
assert not integrated(capture,submit,helper.replace("!separateAlpha","true",1))
assert "test_dx11_game_blend_extrema_00717.py" in workflow
assert "dx11_game_blend_extrema_probe_00717.cpp" in workflow
print("PASS 00717: live game MIN/MAX RGBA OM masked native Draw/Indexed with DX9Ex fallback")
