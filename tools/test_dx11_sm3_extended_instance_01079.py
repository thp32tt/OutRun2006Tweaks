#!/usr/bin/env python3
"""01079: real-game >128 source instances continue through bounded GPU chunks."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root/"src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text(encoding="utf-8")
scope = bridge.split("bool submit_live_sm3_game_draw(",1)[1].split("// Reuse geometric",1)[0]
for token in (
    "kMaxSegmentedGameInstances = 128u",
    "kMaxExtendedSegmentedGameInstances = 256u",
    "kMaxVertices, 1u << 25u, kMaxExtendedSegmentedGameInstances",
    "game_sm3_extended_instance_upload_allowed(",
    "kMaxSegmentedGameInstances, kMaxExtendedSegmentedGameInstances",
    "1ull << 26u",
    "game_sm3_plan_native_instance_chunk(",
    "chunkInstances, instanceSteps, unpacked, instance",
    "instance % chunkPlan.instancesPerChunk",
    "issueNativeGameDraw(",
    "context->DrawIndexed(",
    "context->Draw(vertexCount, base)",
):
    assert token in scope, "01079 integration missing: " + token
assert scope.index("game_sm3_extended_instance_upload_allowed(") < scope.index(
    "game_sm3_assemble_instanced_streams(")
assert scope.index("unpacked.size() != chunkBytes") < scope.index("issueNativeGameDraw(")
assert "extraTotalByteLimit / nativeStride" in header
for token in ("if (!env_full_game_opt_in()", "s.frameBatch.abort();",
              "if (!ensure_full_game_upload_buffer("):
    assert token in bridge, "01079 fallback path removed: " + token
print("01079 game-authored extended SM3 native uploads: PASS_STATIC")
