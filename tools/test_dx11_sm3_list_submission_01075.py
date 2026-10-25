#!/usr/bin/env python3
"""01075: all independent live-game SM3 lists preserve valid large indexed instancing."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
helper=(root/"src/vr/d3d11/live_game_sm3_instance_batches.hpp").read_text(encoding="utf-8")
for token in (
    "const bool listCandidate = sourceInstancing && instanceCount > 1u",
    "game_sm3_list_submission_plan(",
    "listSubmission.mode == GameSm3ListSubmissionMode::invalid",
    "listSubmission.mode == GameSm3ListSubmissionMode::compact_indexed",
    "listSubmission.mode == GameSm3ListSubmissionMode::compact_linear",
    "if (compactListIndexedSubmission && nativeIndices) {",
    "listCandidate ? listSubmission.drawCount",
    "const UINT base = segmentedInstanceUpload",
    "context->DrawIndexed(nativeIndexCount, 0u, static_cast<INT>(base));",
    "context->Draw(vertexCount, base);",
    "if (nativeIndices[i] >=",
    "if (!ensure_full_game_upload_buffer(device, s.fullGameVertexUpload,",
    "s.pending = true;",
):
    assert token in source, "01075 native source regression: "+token
assert "GameSm3ListSubmissionMode::per_instance" in helper
assert "sourceCount > maxExpandedIndices" in helper
assert "std::uint64_t(sourceCount) <= allowed / instanceCount" in helper
assert "game_sm3_expand_list_instance_indices(" in source
assert "if (compactListInstances && nativeIndices)" not in source
submit = source.split("bool submit_live_sm3_game_draw(", 1)[1].split("// Reuse geometric", 1)[0]
assert submit.index("listSubmission.mode == GameSm3ListSubmissionMode::invalid") < submit.index("upload_full_game_stream(")
print("01075 list GPU Draw + source rejection/fallback: PASS_STATIC")
