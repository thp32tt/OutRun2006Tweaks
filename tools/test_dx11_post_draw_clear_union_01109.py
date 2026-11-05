#!/usr/bin/env python3
"""01109: original D3D9 post-Draw color/Z source -> compacted native GPU rects."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
bridge=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header=(r/"src/vr/d3d11/native_game_post_draw_clear_batch.hpp").read_text()
assert '#include "native_game_post_draw_clear_batch.hpp"' in bridge
color=bridge[bridge.index("bool preserve_game_partial_target_clear("):
             bridge.index("bool preserve_game_color_fill(")]
depth=bridge[bridge.index("bool observe_game_depth_clear("):
             bridge.index("void observe_game_clear(")]
assert "GameNativePostDrawClearBatch::build(" in color
assert "GameNativePostDrawClearBatch::build(" in depth
assert "GameNativePostDrawClearBatch::kMaxSourceRects" in color
assert "GameNativePostDrawClearBatch::kMaxSourceRects" in depth
for section in (color,depth):
    assert "regions.data()" in section
    assert "GameNativePostDrawClearBatch::build(" in section
assert "game_native_merge_ordered_overwrite(" in header
assert "used > kMaxSourceRects" in header
assert "GameNativeSourceMutation::classify_target_clear_rect(" in header
assert "source[i].x1" in header
assert "ClearView(s.backend.color_rtv()" in color
assert "regions.data() + start" in color
assert "regions.data() + start" in depth
assert "ClearView(s.diagnosticDepthView.Get()" in color
assert "ClearView(s.diagnosticDepthView.Get()" in depth
assert "native_game_raster_partial_backbuffer_depth_clear(" in depth
assert "native_game_raster_partial_backbuffer_target_depth_clear(" in color
print("01109 post-Draw game color/Z GPU region union source graph PASS")
