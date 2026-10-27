#!/usr/bin/env python3
"""01113 authentic full source GPU copy -> native first-Draw color."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
bridge=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
clear=(r/"src/vr/d3d11/native_game_clear_color.hpp").read_text()
source=bridge[bridge.index("bool preserve_game_surface_copy("):bridge.index("bool begin_game_surface_cpu_write(")]
replay=bridge[bridge.index("bool replay_native_game_pre_draw_surface("):bridge.index("bool replay_native_game_pre_draw_depth(")]
assert "native_game_full_surface_copy_can_seed(" in source
assert "boundIdentity.Get() == backbufferIdentity.Get()" in source
assert "wholeCopiedBackbuffer" in source
assert "s.sourceDrawsThisFrame == 0u && !s.frameBatch.hasSourceDraw" in source
assert source.index("s.preDrawSurface.record_consuming(") < source.index("s.clearColor.copySnapshotRequired = true;")
assert source.index("s.clearColor.copySnapshotRequired = true;") < source.index("s.surfaceReplayBudget.note_success(desc.Width, desc.Height);")
assert "if (!s.preDrawSurface.active()) return !s.clearColor.copySnapshotRequired;" in replay
assert replay.index("GetDeviceRemovedReason()") < replay.index("s.clearColor.copySnapshotRequired = false;")
assert "copySnapshotRequired = false;" in clear
# Both REAL first-Draw paths must upload the authenticated GPU seed.
# Programmable SM3 names its immediate context 'context'; the fixed-function
# FVF path names it 'ctx'. Their differing locals are not missing callsites.
assert bridge.count("replay_native_game_pre_draw_surface(s,context,") == 1
assert bridge.count("replay_native_game_pre_draw_surface(s,ctx,") == 1
print("01113 native first-Draw full-copy source graph PASS")
