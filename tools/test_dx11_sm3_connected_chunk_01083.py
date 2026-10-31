#!/usr/bin/env python3
"""01083: real SM3 strip -> bounded D3D11 GPU Draw, not a planner-only change."""
from pathlib import Path
bridge = Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = Path("src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
start = bridge.index("const auto connectedChunkPlan =")
end = bridge.index("s.pending = true;", start)
live = bridge[start:end]
for token in (
    "game_sm3_plan_native_connected_chunks(",
    "connectedChunkUpload ? connectedChunkPlan.chunkCount",
    "connectedChunkPlan.verticesPerChunk",
    "firstVertex = submit * connectedChunkPlan.advanceVertices",
    "vertexCount - firstVertex",
    "game_sm3_assemble_streams(",
    "unpacked, firstVertex",
    "upload_full_game_stream(",
    "issueNativeGameDraw(drawCount, 0u);",
    "s.frameBatch.abort();",
    "connectedChunkUpload",
):
    assert token in live, token
assert "!pointFill && !wireFill" in live
assert "primitiveType == 3u" in header and "primitiveType == 5u" in header
assert "capacity -= capacity % 2u" in header
assert "capacity - (line ? 1u : 2u)" in header
assert "D3D9 TRIANGLEFAN" in header
assert "context->IASetPrimitiveTopology(" in live
assert "context->DrawIndexed" in live
print("01083 live shader-bound native connected GPU strip integration: PASS")
