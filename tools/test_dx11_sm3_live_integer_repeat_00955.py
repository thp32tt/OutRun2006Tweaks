#!/usr/bin/env python3
"""Verify game-authored VS/PS i# dynamic REP across D3D9 capture and native b3."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
def source(path): return (root / path).read_text()
backend = source("src/vr/d3d11/native_backend.cpp")
header = source("src/vr/d3d11/native_backend.hpp")
flow = source("src/vr/d3d11/native_sm3_repeat_flow.hpp")
game = source("src/vr/d3d11/live_game_frame_bridge.cpp")
for fragment in (
    "const bool dynamic = !intDefPresent[reg];",
    "structuredFlow.begin_live_repeat(tempWritten, outputWritten)",
    "op.repeatDynamic = dynamic;",
    "append_native_sm3_live_repeat_begin(",
    "cbuffer R283LiveIntegers : register(b3)",
    "candidate.vertexIntegerMask |=",
    "candidate.pixelIntegerMask |=",
):
    assert fragment in backend, fragment
assert "std::uint16_t vertexIntegerMask" in header
assert "std::uint16_t pixelIntegerMask" in header
assert "r283_i[" in flow
assert "frames_.back().hasBreak = true" in flow
for fragment in (
    "game->GetVertexShaderConstantI(",
    "game->GetPixelShaderConstantI(",
    "!native_sm3_live_repeat_payload_valid(",
    "pipeline.vertexIntegers.Get(), 0u, nullptr,",
    "pipeline.pixelIntegers.Get(), 0u, nullptr,",
    "context->VSSetConstantBuffers(3u",
    "context->PSSetConstantBuffers(3u",
):
    assert fragment in game, fragment
assert game.index("!native_sm3_live_repeat_payload_valid(") < game.index("upload_full_game_stream(context")
assert game.index("GetVertexShaderConstantI(") < game.index("context->VSSetConstantBuffers(3u")
assert game.index("GetPixelShaderConstantI(") < game.index("context->PSSetConstantBuffers(3u")
assert "if (!env_full_game_opt_in()" in game
print("Live SM3 i# REP/ENDREP game capture + native b3 + fallback PASS")
