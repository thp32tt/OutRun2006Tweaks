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
    "record.texture = texture;",
    "record.arraySlice = camera.arraySlice;",
    "record.mipSlice = camera.mip;",
    "record.region = filled;",
]
assert all(s in writer for s in required), "Cleared camera pixel provenance missing"
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
