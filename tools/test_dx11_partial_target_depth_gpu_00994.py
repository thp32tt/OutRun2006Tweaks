#!/usr/bin/env python3
"""00994: live D3D9 clipped TARGET|Z -> owned D3D11.0 paired GPU raster."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
stereo = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
header = (root / "src/vr/d3d11/native_game_stereo_submission.hpp").read_text()
helper = "native_game_raster_partial_backbuffer_target_depth_clear("
assert helper in bridge and helper in stereo and helper in header
assert "pairedDepthRaster = partial_game_paired_target_depth_raster(" in bridge
assert "nativeDepthReady = !clearZ || native_game_partial_depth_ready(" in bridge
assert "if (clearZ && hasClearView)" in bridge
assert "ctx1->ClearView(s.diagnosticDepthView.Get(), depthValue" in bridge
assert "raster_partial_eye_color_clear(" in stereo
assert "raster_partial_eye_depth_clear(" in stereo
assert "dsvDesc.Format != DXGI_FORMAT_D32_FLOAT" in stereo
assert "dsvDesc.ViewDimension != D3D11_DSV_DIMENSION_TEXTURE2D" in stereo
assert "D3D11_DSV_READ_ONLY_DEPTH" in stereo
assert "return false;" in bridge
assert "s.frameBatch.submitted != 0u" in bridge
print("00994 paired partial game TARGET|Z GPU replay: PASS_STATIC")
