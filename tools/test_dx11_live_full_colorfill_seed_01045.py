#!/usr/bin/env python3
"""01045: the real original-game ColorFill hook must seed native D3D11 Draw."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
start = bridge.index("bool preserve_game_color_fill(")
end = bridge.index("void observe_scene_boundary(", start)
hook = bridge[start:end]
before_seed = hook.index("const bool sameGameBackbuffer")
assert "native_game_full_color_fill_can_seed(" in hook[:before_seed]
for guard in ("GetBackBuffer(", "GetRenderTarget(", "surfaceIdentity.Get() == backbufferId.Get()", "targetId.Get() == backbufferId.Get()", "s.sourceDrawsThisFrame == 0u", "D3DMULTISAMPLE_NONE", "GameNativeFrameBatch::admits_game_source(", "s.clearColor.record(", "s.sourceGameDevice = owner;"):
    assert guard in hook[:before_seed], guard
assert "if (native_game_color_fill_retires_draw_batch(" in hook[before_seed:]
assert "s.frameBatch.abort();" in hook[before_seed:]
assert "FAILED(originalResult)" in hook
print("01045 live original D3D9 ColorFill -> actual native Draw source seed PASS")
