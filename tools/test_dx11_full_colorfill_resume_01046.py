#!/usr/bin/env python3
"""01046: original post-Draw full ColorFill restarts actual source epoch, never fake depth."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
batch = (root / "src/vr/d3d11/native_game_frame_batch.hpp").read_text(encoding="utf-8")
start = bridge.index("bool preserve_game_color_fill(")
end = bridge.index("void observe_scene_boundary(", start)
hook = bridge[start:end]
assert hook.index("sameGameBackbuffer") < hook.index("restart_after_full_color_fill(")
assert hook.index("GameNativeSourceMutation::mirrors_full_color_fill(") < hook.index("restart_after_full_color_fill(")
assert "s.frameBatch.restart_after_full_color_fill(\n                s.sourceDrawsThisFrame)" in hook
assert "s.pending = false;" in hook
assert "s.clearColor.argb = color;" in hook
assert "s.clearColor.opaqueDestinationAlpha =" in hook
assert "s.frameBatch.abort();" in hook
assert "s.clearColor.discard();" in hook
assert "s.outputGeneration" in hook
assert "sourceEpochStart" in batch
assert "if (colorFillEpoch && depth) return false;" in batch
assert "sourceDraws - sourceEpochStart" in batch
print("01046 live game ColorFill -> new native Draw epoch and original fallback PASS")
