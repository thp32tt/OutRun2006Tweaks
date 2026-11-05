#!/usr/bin/env python3
"""01105 game-authored RTV/DSV pre-Draw independent-band GPU replay wiring."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
helper=(root/"src/vr/d3d11/native_game_pre_draw_tile_coalesce.hpp").read_text()
color=(root/"src/vr/d3d11/native_game_source_mutation.hpp").read_text()
depth=(root/"src/vr/d3d11/native_game_pre_draw_depth.hpp").read_text()
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
assert "joined.left < intervening.right" in helper
assert "if (intersects) { safe = false; break; }" in helper
assert "tiles[count - 1u] = joined;" in helper
assert "game_native_merge_noninterfering_overwrite(" in color
assert "game_native_merge_noninterfering_overwrite(" in depth
assert "GameNativePreDrawCombinedClear::record(" in bridge
assert "game_native_replay_pre_draw_fills(" in bridge
assert "replay_native_game_pre_draw_depth(" in bridge
print("01105 authentic first-Draw GPU color/Z ordered replay wired")
