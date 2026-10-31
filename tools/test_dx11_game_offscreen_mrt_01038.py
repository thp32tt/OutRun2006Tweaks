from pathlib import Path

cpp = Path("src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
hpp = Path("src/vr/d3d11/native_game_stereo_submission.hpp").read_text()
layout = cpp.split("bool NativeGameEyeDrawEncoder::game_offscreen_outputs_admitted(", 1)[1].split(
    "bool NativeGameEyeDrawEncoder::geometry_outputs_isolated(", 1
)[0]
assert "native_game_offscreen_mrt_slot_compatible(" in layout
assert "context_->OMGetRenderTargetsAndUnorderedAccessViews(" in layout
assert "resource.Get() != eyeResource.Get()" in layout
assert "resource.Get() != gameDepthResource.Get()" in layout
assert "owner.Get() == device.Get()" in layout
# XR direct Draw remains isolated, only authentic offscreen Draw takes MRT.
assert "geometry_outputs_isolated(eyeTarget_)" in cpp
assert "game_offscreen_outputs_admitted(gameTarget)" in cpp
record = cpp.split("bool NativeGameEyeDrawEncoder::remember_offscreen_color_outputs(", 1)[1].split(
    "bool NativeGameEyeDrawEncoder::draw_offscreen(", 1
)[0]
assert "source_color_writable(output, i)" in record
assert "remember_offscreen_color_source(output)" in record
assert "IndependentBlendEnable ? outputSlot : 0u" in cpp
for name in ("draw_offscreen(", "draw_offscreen_indexed(",
             "draw_offscreen_instanced(", "draw_offscreen_indexed_instanced("):
    body = cpp.split("bool NativeGameEyeDrawEncoder::" + name, 1)[1].split("\n}\n", 1)[0]
    assert "remember_offscreen_color_outputs(gameTarget)" in body
    assert "++drawCount_" in body
    assert "source_color_writable(gameTarget)" not in body
assert "remember_offscreen_color_outputs" in hpp
print("01038 source MRT/eye isolation and source ordinal wiring PASS")
