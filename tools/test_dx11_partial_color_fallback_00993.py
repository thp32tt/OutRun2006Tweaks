#!/usr/bin/env python3
"""00993: actual partial D3D9 ColorFill/TARGET->D3D11.0 GPU replay linkage."""
from pathlib import Path
r = Path(__file__).resolve().parents[1]
bridge = (r / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
stereo = (r / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
header = (r / "src/vr/d3d11/native_game_stereo_submission.hpp").read_text()
assert "native_game_raster_partial_backbuffer_color_clear(" in bridge
# Two existing live partial TARGET/ColorFill sites plus both newly admitted
# first-Draw SM3/FVF replay paths must retain genuine D3D11.0 GPU dispatch.
assert bridge.count("native_game_raster_partial_backbuffer_color_clear(") == 4
assert bridge.count("game_native_replay_pre_draw_fills(") == 2
assert "if (!replayed) return false;" in bridge
assert "if (!replayed) {" in bridge
assert "native_game_raster_partial_backbuffer_color_clear(" in stereo
assert "native_game_raster_partial_backbuffer_color_clear(" in header
assert "raster_partial_eye_color_clear(" in stereo
assert "ScopedNativeGameEyeOutput restore(context, width, height);" in stereo
assert "for (UINT i = 0u; i < nativeRegionCount; ++i)" in bridge
assert "hasClearView, !clearZ, true" in bridge
assert "context1->ClearView(s.backend.color_rtv(), rgba, &nativeRect, 1u)" in bridge
assert "ctx1->ClearView(s.diagnosticDepthView.Get(), depthValue" in bridge
assert "s.frameBatch.submitted != 0u" in bridge
print("00993 partial game color GPU replay: PASS_STATIC")
