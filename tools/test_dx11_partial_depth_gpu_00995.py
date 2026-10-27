#!/usr/bin/env python3
"""Native source-game partial Z-only clear on D3D11.0, not D3D9 replacement."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
gpu=(root/"src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
hdr=(root/"src/vr/d3d11/native_game_stereo_submission.hpp").read_text()
source_rects=(root/"src/vr/d3d11/native_game_post_draw_clear_batch.hpp").read_text()
source=bridge[bridge.index("bool observe_game_depth_clear("):]
adapter="native_game_raster_partial_backbuffer_depth_clear("
assert adapter in source and adapter in gpu and adapter in hdr
for condition in ("const bool partialDepth = clearZ && !coversDepth;",
                  "if (!continuingFullNativeDraw",
                  "native_game_partial_depth_ready(s, game, bbDesc.Width, bbDesc.Height)",
                  "GameNativePostDrawClearBatch::build(",
                  "if (used == 0u) return true;",
                  "const bool hasClearView = SUCCEEDED(",
                  "context1->ClearView(s.diagnosticDepthView.Get(), depthValue",
                  "for (std::uint32_t i = 0u; i < used; ++i)",
                  "if (!native_game_raster_partial_backbuffer_depth_clear("):
    assert condition in source, condition
# The real game D3DRECT signed clipping now lives in the shared
# post-Draw production batch used by both TARGET and depth; validate that
# the true implementation still clips and refuses over-budget GPU regions.
for guard in ("GameNativeSourceMutation::classify_target_clear_rect(",
              "used > kMaxGpuRegions",
              "game_native_merge_ordered_overwrite("):
    assert guard in source_rects, guard
assert "GameNativePostDrawClearBatch::build(" in bridge[
    bridge.index("bool preserve_game_partial_target_clear("):
    bridge.index("bool preserve_game_color_fill(")]
adapter_code=gpu[gpu.index("bool native_game_raster_partial_backbuffer_depth_clear("):]
adapter_code=adapter_code[:adapter_code.index("// An original D3D9 combined partial TARGET|Z")]
for guard in ("DXGI_FORMAT_D32_FLOAT", "D3D11_DSV_DIMENSION_TEXTURE2D",
              "D3D11_DSV_READ_ONLY_DEPTH", "textureDesc.SampleDesc.Count != 1u",
              "owner.Get() != sourceDevice.Get()", "raster_partial_eye_depth_clear("):
    assert guard in adapter_code, guard
assert adapter in gpu[gpu.index("bool native_game_raster_partial_backbuffer_target_depth_clear("):]
print("00995 real-game Z-only GPU depth replay: PASS_STATIC")
