#!/usr/bin/env python3
"""01107 exact source ordinal -> real TARGET|Z|STENCIL native pre-Draw replay."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
batch=(root/"src/vr/d3d11/native_game_frame_batch.hpp").read_text()
assert "before_first_native_raster(" in batch
assert "observedSourceDraws - sourceEpochStart" in batch
assert "lastSourceDraw + 1u == observedSourceDraws" in batch
assert "can_seed_pre_draw_depth_at_ordinal(" in batch
assert bridge.count("can_seed_pre_draw_depth_at_ordinal(")>=3
assert bridge.count("before_first_native_raster(")>=3
assert "GameNativePreDrawCombinedClear::record(" in bridge
assert "s.preDrawFills.record_target_clear(" in bridge
assert "s.preDrawDepth.record(" in bridge
assert "GameNativeMainStencilClear::may_ignore_pre_draw(" in bridge
print("01107 real-game leading no-op Draw -> pre-first-native RTV/D32/STENCIL bridge OK")
