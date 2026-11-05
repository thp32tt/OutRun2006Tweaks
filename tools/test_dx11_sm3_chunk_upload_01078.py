#!/usr/bin/env python3
"""01078 authentic SM3 multi-instance GPU chunk + original Draw boundaries."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header=(root/"src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text(encoding="utf-8")
scope=bridge.split("bool submit_live_sm3_game_draw(",1)[1].split("// Reuse geometric",1)[0]
for key in (
    "game_sm3_plan_native_instance_chunk(",
    "firstChunkInstances",
    "firstChunkVertices * firstChunkInstances",
    "chunkPlan.firstUploadBytes : (linearChunkUpload",
    "instance % chunkPlan.instancesPerChunk == 0u",
    "const UINT chunkInstances =",
    "instanceStreams, vertexCount,",
    "chunkInstances, instanceSteps, unpacked, instance",
    "unpacked.size() != chunkBytes",
    "unpacked.data(), chunkBytes",
    "(instance % chunkPlan.instancesPerChunk) * vertexCount",
    "context->DrawIndexed(nativeIndexCount, 0u, static_cast<INT>(base))",
    "context->Draw(vertices, base)",
    "s.frameBatch.abort();",
):
    assert key in scope or (key=="s.frameBatch.abort();" and key in bridge), key
assert scope.index("game_sm3_plan_native_instance_chunk(") < scope.index("game_sm3_assemble_instanced_streams(")
assert scope.index("chunkPlan.firstUploadBytes : (linearChunkUpload") < scope.index("issueNativeGameDraw(")
assert scope.index("unpacked.size() != chunkBytes") < scope.index("issueNativeGameDraw(")
assert "lastInstance / instanceStep[element.stream] + 1u" in header
assert "destination.swap(candidate)" in header
assert "std::uint64_t(maxBytes) / bytesPerInstance" in header
assert "if (!env_full_game_opt_in()" in scope
print("01078 bounded native game SM3 grouped uploads: PASS")
