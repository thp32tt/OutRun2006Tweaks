#!/usr/bin/env python3
"""00736 source integration: original game X8 Clear -> native color alpha; safe fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
helper = (root / "src/vr/d3d11/native_game_clear_color.hpp").read_text()
hook = (root / "src/vr/d3d9/stereo_renderer.cpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
def linked(cpp, hdr):
    clear = cpp.split("void observe_game_clear(", 1)[1].split("void observe_unavailable_game_draw(", 1)[0]
    submit = cpp.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
    callback = hook.split("HRESULT __stdcall ClearDestR9(", 1)[1].split("template <typename ActualDraw, typename LegacyDraw>", 1)[0]
    drawing = cpp.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
    return all(token in clear for token in (
        "if (s.sourceGameDevice != 0u && s.sourceGameDevice != sourceDevice) return;",
        "targetIdentity.Get() == backbufferIdentity.Get()",
        "s.clearColor.record(sourceDevice,",
        "static_cast<std::uint32_t>(color), wholeBackbuffer,",
        "bbDesc.Format == D3DFMT_X8R8G8B8);",
        "s.frameBatch.reset();",
    )) and all(token in hdr for token in (
        "bool opaqueDestinationAlpha = false;",
        "opaqueDestinationAlpha = false;",
        "opaqueDestinationAlpha = opaqueBackbuffer;",
        "opaqueDestinationAlpha ? 1.0f :",
        "native_write_mask(",
        "requested & ~std::uint32_t{0x08u}",
        "if (!matches(device, backbuffer)) return fallback;",
    )) and all(token in drawing for token in (
        "const UINT nativeColorWriteMask = env_full_game_opt_in() ?",
        "s.clearColor.native_write_mask(s.sourceGameDevice,",
        "output.targetIdentity, output.colorWriteMask)",
        "desc.RenderTarget[0].RenderTargetWriteMask = nativeColorWriteMask;",
        "s.destAlphaCrossfadeMaskedBlends[nativeColorWriteMask]",
    )) and all(token in submit for token in (
        "s.frameBatch.first_draw()",
        "s.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)",
        "s.backend.begin_frame(",
    )) and all(token in callback for token in (
        "if (SUCCEEDED(result)) {",
        "live_game_frame::observe_game_clear(",
        "return finishNativeClear(hr);",
    ))
assert linked(bridge, helper), "game-authored X8 backbuffer alpha not linked to native Draw"
for before, after in (
    ("bbDesc.Format == D3DFMT_X8R8G8B8);", "false);"),
    ("static_cast<std::uint32_t>(color), wholeBackbuffer,", "static_cast<std::uint32_t>(color), false,"),
):
    bad = bridge.replace(before, after, 1)
    assert bad != bridge and not linked(bad, helper), before
for before, after in (
    ("opaqueDestinationAlpha = opaqueBackbuffer;", "opaqueDestinationAlpha = false;"),
    ("opaqueDestinationAlpha ? 1.0f :", "float((argb >> 24) & 255u) * (1.0f/255.0f) :"),
    ("opaqueDestinationAlpha = false;\n        valid = false;", "valid = false;"),
    ("requested & ~std::uint32_t{0x08u}", "requested"),
):
    bad = helper.replace(before, after, 1)
    assert bad != helper and not linked(bridge, bad), before
for before, after in (
    ("const UINT nativeColorWriteMask = env_full_game_opt_in() ?", "const UINT nativeColorWriteMask = false ?"),
    ("desc.RenderTarget[0].RenderTargetWriteMask = nativeColorWriteMask;", "desc.RenderTarget[0].RenderTargetWriteMask = output.colorWriteMask;"),
):
    bad = bridge.replace(before, after, 1)
    assert bad != bridge and not linked(bad, helper), before
assert "python tools/test_dx11_x8_dest_alpha_00736.py" in workflow
assert "tools/dx11_x8_dest_alpha_00736.cpp" in workflow
print("DX11 00736 X8/A8 Clear alpha to native full Draw & D3D9 fallback PASS")
