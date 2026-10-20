#!/usr/bin/env python3
"""SM3 game LOOP and aL indexed constant HLSL/fallback source integration."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/native_backend.hpp").read_text()
flow = (root / "src/vr/d3d11/native_sm3_repeat_flow.hpp").read_text()
pipeline = (root / "src/vr/d3d11/pipeline_translation.cpp").read_text()
for value in ("D3DSIO_LOOP", "D3DSIO_ENDLOOP", "D3DSPR_LOOP"):
    assert value in pipeline and value in backend, value
for value in (
    "native_sm3_static_loop_parameters(",
    "structuredFlow.begin_loop(", "structuredFlow.end_loop(",
    "append_native_sm3_loop_begin(", "r283_c[",
    '" + r283_aL]"', "loopRanges.back().dynamic",
    "if (relative && kind != D3DSPR_CONST) return false",
    "if (defPresent[static_cast<unsigned>(k)]) return false",
    "operandCursor != instruction.operandTokens.size()",
    "candidate.vertexLoopIntegerMask", "candidate.pixelLoopIntegerMask",
):
    assert value in backend, value
for value in ("native_sm3_live_loop_payload_valid(",
              "vertexLoopIntegerMask", "pixelLoopIntegerMask"):
    assert value in bridge and (value in header or value in flow), value
assert "hasBreak = dynamic" in flow
assert "int r283_aL" in flow
print("SM3 native LOOP/indexed c# source/fallback integrated; real game/HMD UNTESTED")
