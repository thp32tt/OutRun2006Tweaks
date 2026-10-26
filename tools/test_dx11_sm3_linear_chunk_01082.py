#!/usr/bin/env python3
"""01082: actual shader-bound live Draw/DrawIndexed path, not a standalone planner."""
from pathlib import Path
bridge = Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = Path("src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
start = bridge.index("const auto linearChunkPlan =")
end = bridge.index("s.pending = true;", start)
live = bridge[start:end]
for token in (
    "game_sm3_plan_native_linear_chunks(",
    "linearChunkUpload ? linearChunkPlan.chunkCount",
    "firstChunkVertices",
    "firstVertex = submit * linearChunkPlan.verticesPerChunk",
    "game_sm3_assemble_streams(",
    "instanceElements, instanceStreams, drawCount,",
    "unpacked, firstVertex",
    "upload_full_game_stream(",
    "context->Draw(drawCount, 0u);",
    "s.frameBatch.abort();",
):
    assert token in live, token
assert "count > src.vertexCount - firstVertex" in header
assert "sourceVertices % group != 0u" in header
assert "indexed ||" in header
assert "game_sm3_expand_connected_instance_indices(" in live
assert "segmentedConnectedPlan.grouped" in live
print("01082 live-game SM3 native independent list GPU chunk wiring: PASS")
