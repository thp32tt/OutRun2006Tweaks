#!/usr/bin/env python3
"""Ensure successful real camera GPU Clears reach the Copy/Stretch provenance."""
from pathlib import Path
src = (Path(__file__).resolve().parents[1] /
       "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
start = src.index("bool NativeGameEyeDrawEncoder::clear_offscreen_game_color(")
end = src.index("bool NativeGameEyeDrawEncoder::clear_offscreen_game_depth_stencil(", start)
method = src[start:end]
begin = method.index("const auto rememberClearedPixels = [&]() noexcept {")
done = method.index("    switch (route) {", begin)
writer = method[begin:done]
required = [
    "native_game_offscreen_clear_written_region(",
    "if (!native_game_offscreen_color_region_valid(filled)) return;",
    "remember_offscreen_color_region(",
    "texture.Get(), camera.arraySlice, camera.mip, filled);",
]
assert all(s in writer for s in required), "Cleared camera pixel provenance missing"
# The shared Draw/Clear admission method must retain exact physical keys,
# conservative rectangular unions and each actual source footprint.
helper_start = src.index("void NativeGameEyeDrawEncoder::remember_offscreen_color_region(")
helper_end = src.index("void NativeGameEyeDrawEncoder::invalidate_offscreen_color_source(", helper_start)
helper = src[helper_start:helper_end]
assert all(s in helper for s in [
    "native_game_offscreen_color_key_matches(",
    "native_game_offscreen_exact_rect_union(",
    "region = exact;",
    "record.texture = texture;",
    "record.arraySlice = arraySlice;",
    "record.mipSlice = mipSlice;",
    "record.region = region;",
]), "Shared camera Draw/Clear pixel evidence must remain exact-key and fail-closed"

for name, arm in [
    ("full", "case live_game_stereo::NativeColorClearRoute::FullRtv:"),
    ("rect", "case live_game_stereo::NativeColorClearRoute::ClearView:"),
    ("shader", "case live_game_stereo::NativeColorClearRoute::ShaderRaster:"),
]:
    branch = method.split(arm, 1)[1].split("    default:", 1)[0]
    if name != "shader":
        branch = branch.split("    case ", 1)[0]
    assert "invalidateWrittenPixels();" in branch, f"{name} preserved stale Draw pixels"
    assert "rememberClearedPixels();" in branch, f"{name} missed new GPU Clear pixels"
    assert branch.index("invalidateWrittenPixels();") < branch.index(
        "rememberClearedPixels();"), f"{name} wrote evidence before invalidation"
assert "if (issued) {" in method, "failed partial shader Clear must not supply pixels"
assert "++unpredicatedGameDrawCount_" not in method, "camera Clear invented a game Draw"
print("DX11 game camera GPU Clear -> Copy/Stretch color provenance: PASS")
