#!/usr/bin/env python3
"""01110: sparse post-Draw original D3D9 TARGET/Z -> native bounded GPU batches."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
bridge=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header=(r/"src/vr/d3d11/native_game_post_draw_clear_batch.hpp").read_text()
color=bridge[bridge.index("bool preserve_game_partial_target_clear("):
             bridge.index("bool preserve_game_color_fill(")]
depth=bridge[bridge.index("bool observe_game_depth_clear("):
             bridge.index("void observe_game_clear(")]
assert "std::array<Region, kMaxSourceRects>& output" in header
assert "gpu_chunk_size(" in header
assert "remaining < kMaxGpuRegions" in header
assert "count > kMaxSourceRects" in header
for section in (color,depth):
    assert "GameNativePostDrawClearBatch::build(" in section
    assert "GameNativePostDrawClearBatch::kMaxSourceRects> compact{}" in section
    assert "GameNativePostDrawClearBatch::kMaxSourceRects> regions{}" in section
    assert "GameNativePostDrawClearBatch::gpu_chunk_size(" in section
    assert "regions.data() + start, chunk" in section
    assert "return false;" in section
assert "ClearView(s.backend.color_rtv()" in color
assert "ClearView(s.diagnosticDepthView.Get()" in color
assert "ClearView(s.diagnosticDepthView.Get()" in depth
assert "native_game_raster_partial_backbuffer_target_depth_clear(" in color
assert "native_game_raster_partial_backbuffer_color_clear(" in color
assert "native_game_raster_partial_backbuffer_depth_clear(" in depth
assert "source[i].x1" in header
print("01110 authentic sparse TARGET/Z native GPU segmented source graph PASS")
