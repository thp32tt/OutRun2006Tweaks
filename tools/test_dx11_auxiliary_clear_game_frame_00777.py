#!/usr/bin/env python3
"""00777: linked real game Clear/Draw/Present continuity and unsafe-depth fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
hook = (root / "src/vr/d3d9/stereo_renderer.cpp").read_text(encoding="utf-8")
clear = (root / "src/vr/d3d11/native_game_clear_color.hpp").read_text(encoding="utf-8")
offscreen = (root / "src/vr/d3d11/native_game_offscreen_pass.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def integrated(b, h, c, o):
    aux = b.split("bool preserve_offscreen_color_only_clear(", 1)[1].split(
        "void observe_scene_boundary(", 1)[0]
    native = b.split("void observe(IDirect3DDevice9* game,", 1)[1].split(
        "bool preserve_offscreen_color_only_clear(", 1)[0]
    seed = b.split("void observe_game_clear(", 1)[1].split(
        "void observe_unavailable_game_draw(", 1)[0]
    clear_hook = h.split("HRESULT __stdcall ClearDestR9(", 1)[1].split(
        "template <typename ActualDraw", 1)[0]
    return all((
        "SUCCEEDED(result)" in clear_hook,
        "observe_game_depth_clear(" in clear_hook,
        "preserve_offscreen_color_only_clear(" in clear_hook,
        "observe_scene_boundary(device)" in clear_hook,
        "GetDeviceCaps(&caps)" in aux,
        "valid_mrt_count(caps.NumSimultaneousRTs)" in aux,
        "GetRenderTarget(slot, extra.GetAddressOf())" in aux,
        "D3DERR_NOTFOUND" in aux,
        "GetDepthStencilSurface(depth.GetAddressOf())" in aux,
        "main_depth_still_bound(" in aux,
        "GameNativeOffscreenPass::isolated_auxiliary_clear(" in aux,
        "note_auxiliary_depth_clear()" in aux,
        "auxiliaryDepthCleared && output.nativeDepthTest" in native,
        "s.frameBatch.abort();" in native,
        "main_depth_still_bound(" in native,
        "mainDepthIdentity = reinterpret_cast<std::uintptr_t>" in seed,
        "s.clearColor.record(sourceDevice," in seed,
        "mainDepthIdentity);" in seed,
        "mainDepthIdentity = 0u;" in c,
        "auxiliaryDepthCleared = false;" in c,
        "bool isolated_auxiliary_clear(" in o,
        "sourceSeeded && !stopped" in o,
        "(!clearsColor || (offscreenRt0 && extraMrtUnbound))" in o,
        "const bool clearsColor = (flags & D3DCLEAR_TARGET) != 0u" in aux,
        "s.frameBatch.stopped, clearsColor)" in aux,
        "(!depthOrStencilClear || separateDepth)" in o,
    ))
assert integrated(bridge, hook, clear, offscreen)
for text, orig, fake in (
    ("bridge", "GetRenderTarget(slot, extra.GetAddressOf())", "GetRenderTarget(0, extra.GetAddressOf())"),
    ("bridge", "s.clearColor.main_depth_still_bound(", "true /* skipped identity */("),
    ("bridge", "s.clearColor.note_auxiliary_depth_clear();", "/* missed auxiliary depth */"),
    ("bridge", "auxiliaryDepthCleared && output.nativeDepthTest", "false && output.nativeDepthTest"),
    ("bridge", "mainDepthIdentity = reinterpret_cast<std::uintptr_t>", "mainDepthIdentity = 0 * reinterpret_cast<std::uintptr_t>"),
    ("offscreen", "offscreenRt0 && extraMrtUnbound",
     "true /* bypass TARGET RT/MRT isolation */"),
):
    args={"bridge":bridge, "hook":hook, "clear":clear, "offscreen":offscreen}
    if text == "bridge" and orig in (
        "s.clearColor.main_depth_still_bound(",
        "GetRenderTarget(slot, extra.GetAddressOf())",
    ):
        # Main Draw admission and offscreen Draws now inspect live MRTs/Z.
        # Destructively mutate only this test's auxiliary-Clear function:
        # a change to an earlier, unrelated Draw must not satisfy 00777.
        prefix, rest = args["bridge"].split(
            "bool preserve_offscreen_color_only_clear(", 1)
        region, suffix = rest.split("void observe_scene_boundary(", 1)
        assert orig in region
        region = region.replace(orig, fake, 1)
        args["bridge"] = (prefix +
                          "bool preserve_offscreen_color_only_clear(" + region +
                          "void observe_scene_boundary(" + suffix)
    else:
        args[text]=args[text].replace(orig, fake, 1)
    assert not integrated(args["bridge"], args["hook"], args["clear"], args["offscreen"]), orig
assert "tools/test_dx11_auxiliary_clear_game_frame_00777.py" in workflow
assert "tools/dx11_auxiliary_clear_game_frame_00777.cpp" in workflow
print("00777 native menu/car/race auxiliary MRT+depth Clear integration PASS")
