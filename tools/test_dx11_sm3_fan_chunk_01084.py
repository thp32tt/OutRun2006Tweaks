#!/usr/bin/env python3
"""01084: fan chunk upload reaches a game-authored programmable native GPU Draw."""
from pathlib import Path
bridge=Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header=Path("src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
live=bridge[bridge.index("bool submit_live_sm3_game_draw("):
            bridge.index("// Reuse geometric growth buffers",bridge.index("bool submit_live_sm3_game_draw("))]
for token in (
    "game_sm3_plan_native_fan_chunks(",
    "fanChunkUpload ? fanChunkPlan.chunkCount",
    "fanChunkPlan.advanceRimVertices",
    "game_sm3_assemble_fan_window(",
    "game_sm3_copy_native_fan_window(",
    "game_sm3_fan_window_indices(",
    # The same fan center/rim GPU windows now cover all three D3D9 fill
    # modes. The validated count (not an unbounded whole-fan expansion)
    # must drive native DrawIndexed, with point mode using POINTLIST.
    "if (!fillWindow.supported) {",
    "fanIndices.size() != fillWindow.nativeIndexCount",
    "context->IASetPrimitiveTopology(pointFill",
    "D3D11_PRIMITIVE_TOPOLOGY_POINTLIST",
    "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST",
    "context->DrawIndexed(fillWindow.nativeIndexCount, 0u, 0);",
    "s.frameBatch.abort();",
    "!sourceInstancing &&",
    "type == D3DPT_TRIANGLEFAN",
):
    assert token in live, token
assert "sourceVertices <= capacity" in header
assert "candidate.push_back(0u)" in header
assert "game_sm3_assemble_streams(elements, streams, 1u, center)" in header
assert "game_sm3_assemble_streams(elements, streams," in header
assert "nativeIndices = nullptr;" in live
print("01084 real SM3 fan chunk source/IA/DrawIndexed integration: PASS")
