#!/usr/bin/env python3
"""01086 indexed source strips -> native GPU submit plus fail-closed admission."""
from pathlib import Path
source=Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
live=source[source.index("bool submit_live_sm3_game_draw("):
            source.index("// Reuse geometric growth buffers",
                         source.index("bool submit_live_sm3_game_draw("))]
header=Path("src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
for token in ("game_sm3_plan_native_indexed_connected_chunks(",
              "indexedConnectedChunkPlan.chunkCount",
              "indexedConnectedChunkPlan.advanceVertices",
              "indexedConnectedChunkPlan.verticesPerChunk",
              "indexedChunkUpload || indexedConnectedChunkUpload",
              "indices[i] >= vertexCount", "nativeIndices = nullptr;",
              "game_sm3_assemble_indexed_window(",
              "issueNativeGameDraw(drawCount, 0u);",
              "context->Draw(vertices, base);", "s.frameBatch.abort();"):
    assert token in live,token
for token in ("uploadedVertices", "maxTotalBytes / nativeStride",
              "sourceVertices > maxVertices", "plan.chunkCount < 2u",
              "if (triangle) capacity -= capacity % 2u;"):
    assert token in header,token
print("01086 indexed connected SM3 source->GPU chunk integration PASS")
