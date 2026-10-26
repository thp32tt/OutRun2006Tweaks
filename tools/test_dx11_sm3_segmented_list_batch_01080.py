#!/usr/bin/env python3
"""01080 integrated native SM3 source-list GPU chunk submissions."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
helper = (root/"src/vr/d3d11/live_game_sm3_instance_batches.hpp").read_text(encoding="utf-8")
scope = source.split("bool submit_live_sm3_game_draw(", 1)[1].split(
    "// Reuse geometric", 1)[0]
for token in (
    "game_sm3_segmented_list_submission_plan(",
    "segmentedListPlan.grouped ? segmentedListPlan.batches : instanceCount",
    "const UINT instance = segmentedListPlan.grouped",
    "instanceSteps, unpacked, instance",
    "context->Draw(chunkInstances * vertexCount, 0u)",
    "game_sm3_expand_list_instance_indices(",
    "context->IASetIndexBuffer(s.fullGameIndexUpload.Get()",
    "context->DrawIndexed(sourceIndexCount, 0u, 0)",
    "issueNativeGameDraw(",
    "s.frameBatch.abort();",
):
    assert token in scope or token in source, "01080 native wiring absent: " + token
assert "primitiveType" in helper and "pointFill" in helper
assert "sourceIndexCount) * instancesPerUpload" in helper
assert scope.index("game_sm3_segmented_list_submission_plan(") < scope.index("context->Draw(chunkInstances")
assert scope.index("game_sm3_assemble_instanced_streams(") < scope.index("context->Draw(chunkInstances")
assert "if (!env_full_game_opt_in()" in scope
print("01080 real-game segmented independent native GPU lists: PASS_STATIC")
