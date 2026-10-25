#!/usr/bin/env python3
"""01077: native GPU byte-limit segmentation in real shader-bound game draw."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text(encoding="utf-8")
scope = bridge.split("bool submit_live_sm3_game_draw(", 1)[1].split("// Reuse geometric", 1)[0]
for token in (
    "game_sm3_plan_native_instance_upload(",
    "const UINT plannedNativeStride = sourceInstancing && !repack",
    "input.size() * 16u) : nativeStride",
    "sourceInstancing, vertexCount, instanceCount, plannedNativeStride,",
    "uploadPlan.mode == GameSm3NativeUploadMode::segmented",
    "uploadPlan.mode == GameSm3NativeUploadMode::invalid",
    "firstChunkInstances",
    "vertexCount * firstChunkInstances",
    "chunkPlan.firstUploadBytes : uploadPlan.vertexBytes",
    "instance % chunkPlan.instancesPerChunk == 0u",
    "instanceSteps, unpacked, instance)",
    "upload_full_game_stream(context, s.fullGameVertexUpload.Get()",
    "issueNativeGameDraw(",
    "context->DrawIndexed(nativeIndexCount, 0u, static_cast<INT>(base))",
    "context->Draw(vertexCount, base)",
    "s.pending = true;",
):
    assert token in scope, "01077 missing native integration: " + token
assert scope.index("game_sm3_plan_native_instance_upload(") < scope.index(
    "game_sm3_assemble_instanced_streams(")
assert scope.index("chunkPlan.firstUploadBytes : uploadPlan.vertexBytes") < scope.index(
    "issueNativeGameDraw(")
for token in (
    "expanded > maxVertices ||",
    "expanded > maxBytes / nativeStride",
    "vertexCount > maxBytes / nativeStride",
    "instanceCount > maxSegmentedInstances",
    "GameSm3NativeUploadMode::invalid",
):
    assert token in header, "01077 missing budget/fallback: " + token
assert "s.frameBatch.abort();" in bridge
assert "if (!env_full_game_opt_in()" in bridge
print("01077 authentic native SM3 per-instance byte budget: PASS_STATIC")
