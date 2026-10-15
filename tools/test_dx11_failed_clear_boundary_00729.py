#!/usr/bin/env python3
"""00729: live native menu/race Draw survives failed Clear; success splits scenes."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
renderer = (root / "src/vr/d3d9/stereo_renderer.cpp").read_text(encoding="utf-8")
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
a = renderer.index("HRESULT __stdcall ClearDestR9(")
b = renderer.index("template <typename ActualDraw", a)
hook = renderer[a:b]

def valid(h):
    start = h.find("auto finishNativeClear =")
    end = h.find("++R9ClearCalls;", start)
    if start < 0 or end < 0:
        return False
    finish = h[start:end]
    gate = finish.find("if (SUCCEEDED(result)) {")
    boundary = finish.find("live_game_frame::observe_scene_boundary(device)")
    color = finish.find("live_game_frame::observe_game_clear(")
    result = finish.find("return result;")
    mask = finish.find("if (!nativePartialClear &&")
    return all((
        0 <= gate < mask < boundary < color < result,
        "preserve_game_partial_target_clear(" in finish,
        "if ((flags & D3DCLEAR_TARGET) && !nativePartialClear)" in finish,
        "finishNativeClear(R9ClearCallbackHook.stdcall<HRESULT>(" in h,
        "finishNativeClear(ClearHook.stdcall<HRESULT>(" in h,
        "return finishNativeClear(stereoHr);" in h,
        "observe_scene_boundary(device)" not in h[end:],
        "s.frameBatch.scene_boundary();" in bridge,
        "s.pending = false;" in bridge,
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in bridge,
    ))

assert valid(hook), "failed Clear must leave real-game native Draw scene intact"
for old, new in (
    ("if (SUCCEEDED(result)) {", "if (true) {"),
    ("if (SUCCEEDED(result)) {", "if (FAILED(result)) {"),
    ("live_game_frame::observe_scene_boundary(device)", "/* omitted boundary */"),
    ("if ((flags & D3DCLEAR_TARGET) && !nativePartialClear)", "if (false)"),
    ("return finishNativeClear(stereoHr);", "return stereoHr;"),
):
    mutant = hook.replace(old, new, 1)
    assert mutant != hook and not valid(mutant), old
assert "python tools/test_dx11_failed_clear_boundary_00729.py" in workflow
print("PASS 00729: failed D3D9 Clear preserves menu/race Draw, successful Clear splits full native frame")
