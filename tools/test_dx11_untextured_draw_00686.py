#!/usr/bin/env python3
"""Validate 00686 real menu/vehicle-select FVF -> native Draw and fallback."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
h=(r/"src/vr/d3d11/live_game_fvf_layout.hpp").read_text()
part=s.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
draw=s.split("bool submit(",1)[1].split("void observe(",1)[0]
assert "game_fvf_untextured_stage0(" in part
assert "nextColorOp, layout.hasDiffuse" in part
assert "GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)" in part
assert "GetTextureStageState(1, D3DTSS_COLOROP, &nextColorOp)" in part
assert "if (!layout.hasDiffuse ||" in part
assert "game_native_backbuffer_ready(game, viewport)" in part
assert "if (!diffuse) return false;" in h
assert "if (op == 1u) return nextOp == 1u;" in h
assert "return rgb && a;" in h
for x in ("ctx->DrawIndexed(indexCount, 0, 0);",
          "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
          "s.ps.Get()"): assert x in draw
for x in ("game_fvf_untextured_stage0(", "nextColorOp, layout.hasDiffuse",
          "GetTextureStageState(0, D3DTSS_ALPHAOP, &alphaOp)"):
    assert x not in part.replace(x,"REMOVED",1)
assert "observe_source_device(s, game)" in s
print("00686 native game untextured Draw/Indexed integration: PASS")
