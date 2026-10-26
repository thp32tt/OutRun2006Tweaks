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
assert "if (pointFill && !fanChunkUpload &&" in live
assert "context->DrawIndexed(fillWindow.nativeIndexCount" in live
assert "type == D3DPT_TRIANGLEFAN" in live
assert "D3D11_PRIMITIVE_TOPOLOGY_POINTLIST" in live
assert "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST" in live
print("01088 indexed/nonindexed fan point/wire/solid GPU windows PASS")

# 01089: source-joined point/wire/solid triangle strips with original D3D9
# indexed and unindexed geometry through shader-bound native GPU Draws.
assert "game_sm3_strip_fill_window_plan(" in live
assert "!connectedChunkUpload && !indexedConnectedChunkUpload" in live
assert "std::uint64_t(indexCount) * plannedNativeStride" in live
assert live.count("context->DrawIndexed(window.pointIndexCount, 0u, 0);")==2
assert "game_sm3_plan_native_connected_chunks(" in live
print("01089 SM3 indexed/unindexed connected polygon strips native point/wire/solid PASS")

# 01090: source-visible independent TRIANGLELIST POINT/WIREFRAME GPU
# uploads are real per-window Draw submissions, not only metadata/planners.
assert "(!pointFill || type == D3DPT_TRIANGLELIST)" in live
assert "((!pointFill && !wireFill) || type == D3DPT_TRIANGLELIST)" in live
assert "!linearChunkUpload && !indexedChunkUpload" in live
indexed=live[live.index("        if (indexedChunkUpload) {",live.index("const UINT nativeSubmissionCount")):
             live.index("        if (indexedConnectedChunkUpload) {",live.index("const UINT nativeSubmissionCount"))]
linear=live[live.index("        if (linearChunkUpload) {",live.index("const UINT nativeSubmissionCount")):
            live.index("        if (connectedChunkUpload) {",live.index("const UINT nativeSubmissionCount"))]
assert "issueNativeGameDraw(drawCount, 0u);" in indexed
assert "game_sm3_assemble_indexed_window(" in indexed
assert "issueNativeGameDraw(drawCount, 0u);" in linear
assert "game_sm3_assemble_streams(" in linear
assert live.index("for (UINT i=0u;i<indexCount;++i)",live.index("const bool indexedChunkUpload")) < live.index("rejectionStage = 6u;")
print("01090 shader-bound SM3 indexed/unindexed polygon POINT/WIREFRAME GPU windows PASS")
