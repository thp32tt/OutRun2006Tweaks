#!/usr/bin/env python3
"""01085 indexed original game IB -> native FLOAT4 vertex GPU Draw admission."""
from pathlib import Path
source=Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
live=source[source.index("bool submit_live_sm3_game_draw("):
            source.index("// Reuse geometric growth buffers",source.index("bool submit_live_sm3_game_draw("))]
header=Path("src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
for token in ("game_sm3_plan_native_indexed_chunks(",
              "!sourceInstancing && indices && repack &&",
              "indices[i] >= vertexCount", "nativeIndices = nullptr;",
              "indexedChunkPlan.chunkCount", "indexedChunkPlan.verticesPerChunk",
              "game_sm3_assemble_indexed_window(",
              "indexedWindow.data(),", "issueNativeGameDraw(drawCount, 0u);",
              "s.frameBatch.abort();"):
    assert token in live,token
for token in ("indexCount % group","maxTotalBytes",
              "indices[firstIndex+v] >= stream.vertexCount","output.swap(staged)"):
    assert token in header,token
assert "context->Draw(vertices, base);" in live
print("01085 real SM3 indexed list native GPU window integration PASS")
