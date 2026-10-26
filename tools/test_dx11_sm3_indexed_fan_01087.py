#!/usr/bin/env python3
"""01087 indexed/nonindexed fan full-IB overflow -> bounded SM3 GPU draw."""
from pathlib import Path
bridge=Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header=Path("src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
live=bridge[bridge.index("bool submit_live_sm3_game_draw("):
            bridge.index("// Reuse geometric growth buffers",
                         bridge.index("bool submit_live_sm3_game_draw("))]
for item in ("deferredFanTriangles", "indexedFanChunkUpload",
             "game_sm3_plan_native_indexed_fan_chunks(",
             "game_sm3_assemble_indexed_fan_window(",
             "game_sm3_copy_native_indexed_fan_window(",
             "indexedFanChunkUpload ? indexCount : vertexCount",
             "game_sm3_fan_window_indices(", "context->DrawIndexed(",
             "indices[i] >= vertexCount", "nativeIndices = nullptr;",
             "s.frameBatch.abort();", "return false; // unsupported large fan"):
    assert item in live, item
for item in ("uploadVertices", "maxTotalBytes / nativeStride",
             "selected.push_back(indices[0u]);",
             "firstRim + i - 1u", "output.swap(staged);"):
    assert item in header,item
assert live.index("if (fanChunkUpload) {") < live.index("if (repack) {")
assert live.index("if (indexedFanChunkUpload && !repack)") < live.index("rejectionStage = 6u;")
print("01087 indexed SM3 fan center/rim/oversized-IB native integration PASS")

# 01088 must enter the *same* shader-bound fan native GPU source path.
assert "game_sm3_fan_fill_window_plan(" in live
assert "if (pointFill && !fanChunkUpload)" in live
assert "context->DrawIndexed(fillWindow.nativeIndexCount" in live
assert "type == D3DPT_TRIANGLEFAN" in live
assert "D3D11_PRIMITIVE_TOPOLOGY_POINTLIST" in live
assert "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST" in live
print("01088 indexed/nonindexed fan point/wire/solid GPU windows PASS")
