#!/usr/bin/env python3
"""01076: source-authoritative SM3 instance segmentation linked to native GPU Draw."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
streams=(root/"src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text(encoding="utf-8")
scope=bridge.split("bool submit_live_sm3_game_draw(",1)[1].split("// Reuse geometric",1)[0]
for token in (
    "constexpr UINT kMaxSegmentedGameInstances = 128u;",
    "const bool segmentedInstanceUpload = sourceInstancing &&",
    "expandedVertices > kMaxVertices &&",
    "segmentedInstanceUpload ? 1u : instanceCount",
    "segmentedInstanceUpload ? vertexCount : expandedVertices",
    "const UINT nativeSubmissionCount = segmentedInstanceUpload",
    "if (segmentedInstanceUpload && instance != 0u)",
    "instanceElements, instanceStreams, vertexCount, 1u,",
    "instanceSteps, unpacked, instance)",
    "unpacked.size() != vertexBytes",
    "upload_full_game_stream(context, s.fullGameVertexUpload.Get()",
    "segmentedInstanceUpload ? 0u :",
    "issueNativeGameDraw(",
    "context->DrawIndexed(nativeIndexCount, 0u, static_cast<INT>(base))",
    "context->Draw(vertexCount, base)",
    "s.pending = true;",
):
    assert token in scope, "01076 real native path missing: "+token
assert scope.index("unpacked.size() != vertexBytes") < scope.index("issueNativeGameDraw(")
assert scope.index("context->DrawIndexed(nativeIndexCount") < scope.index("s.pending = true;")
assert "firstInstance + inst" in streams
assert "lastInstance / instanceStep[element.stream] + 1u" in streams
assert "destination.swap(candidate)" in streams
# Missing native shadow, unsuccessful Map, source over-budget and unsupported
# presentation continue to take existing fail-closed fallback.
for token in ("if (!bytes || !stride)", "s.frameBatch.abort();",
              "if (!nativeIndexCount || nativeIndexCount > kMaxIndices)",
              "if (!ensure_full_game_upload_buffer(device, s.fullGameVertexUpload",
              "if (!env_full_game_opt_in()"):
    assert token in bridge, "01076 negative/fallback regression: "+token
print("01076 segmented live game SM3 GPU draws: PASS_STATIC")
