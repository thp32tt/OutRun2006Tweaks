#!/usr/bin/env python3
"""01111 authentic 128-region pre-first-Draw paired GPU replay wiring."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
color=(root/"src/vr/d3d11/native_game_source_mutation.hpp").read_text()
depth=(root/"src/vr/d3d11/native_game_pre_draw_depth.hpp").read_text()
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
combined=(root/"src/vr/d3d11/native_game_pre_draw_combined_clear.hpp").read_text()
assert "static constexpr std::uint32_t kCapacity = 128u;" in color
assert "static constexpr std::uint32_t kCapacity=128u;" in depth
assert "kGpuChunkCapacity =" in depth
assert "kMaxPartialTargetClearRects" in depth
assert "tiles[start+used].z==z" in depth
assert "used<kGpuChunkCapacity" in depth
assert "if (!replay_ready(owner,rt,ds,w,h)) return false;" in depth
assert "s.preDrawDepth.replay_batched(" in bridge
assert "context1->ClearView(s.diagnosticDepthView.Get()," in bridge
assert "value,rects,count" in bridge
assert "native_game_raster_partial_backbuffer_depth_clear(" in bridge
assert "if(!replayed)return false;" in bridge
assert "s.preDrawDepth.discard();" in bridge
assert "auto stagedColor = colors;" in combined
assert "auto stagedDepth = depths;" in combined
assert combined.index("stagedDepth.record(")<combined.index("colors = stagedColor;")
print("01111 authentic 128 sparse TARGET/Z first-Draw source and GPU paths PASS")
