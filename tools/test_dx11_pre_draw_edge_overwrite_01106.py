#!/usr/bin/env python3
"""01106 source-wired D3D9 pre-Draw edge-overwrite native pixel regression."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
helper=(root/"src/vr/d3d11/native_game_pre_draw_tile_coalesce.hpp").read_text()
color=(root/"src/vr/d3d11/native_game_source_mutation.hpp").read_text()
depth=(root/"src/vr/d3d11/native_game_pre_draw_depth.hpp").read_text()
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
assert "game_native_trim_partially_overwritten" in helper
assert "prior.top = b;" in helper and "prior.bottom = t;" in helper
assert "prior.left = r;" in helper and "prior.right = l;" in helper
assert "(void)game_native_trim_partially_overwritten(saved, next)" in color
assert "(void)game_native_trim_partially_overwritten(prior,next)" in depth
assert "GameNativePreDrawCombinedClear::record(" in bridge
assert "game_native_replay_pre_draw_fills(" in bridge
assert "replay_native_game_pre_draw_depth(" in bridge
print("01106 D3D9 partial Clear to native first-Draw color/Z source graph OK")
