#!/usr/bin/env python3
"""01104 game source Clear RTV/DSV ordered compact tile integration."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/"src/vr/d3d11/native_game_source_mutation.hpp").read_text()
depth=(root/"src/vr/d3d11/native_game_pre_draw_depth.hpp").read_text()
fusion=(root/"src/vr/d3d11/native_game_pre_draw_tile_coalesce.hpp").read_text()
combined=(root/"src/vr/d3d11/native_game_pre_draw_combined_clear.hpp").read_text()
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
assert "game_native_merge_ordered_overwrite(" in source
assert "game_native_merge_ordered_overwrite(" in depth
assert "prior.top == next.top && prior.bottom == next.bottom" in fusion
assert "prior.left == next.left && prior.right == next.right" in fusion
assert "if (!horizontal && !vertical) return false;" in fusion
assert "auto staged = *this;" in source
assert "if (output >= kCapacity) return false;" in source
assert "if(retained>=kCapacity)return false;" in depth
assert "auto stagedColor = colors;" in combined
assert "auto stagedDepth = depths;" in combined
assert "s.preDrawFills.count != 0u" in bridge
assert "s.preDrawDepth.replay_ready(" in bridge
assert "GameNativePreDrawCombinedClear::record(" in bridge
print("01104 native authentic first-Draw color/depth replay tile fusion linkage PASS")
