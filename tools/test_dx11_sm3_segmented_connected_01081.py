#!/usr/bin/env python3
"""01081: structural wiring of genuine segmented connected game GPU submission."""
from pathlib import Path
bridge = Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
helper = Path("src/vr/d3d11/live_game_sm3_connected_submission.hpp").read_text()
slice_start = bridge.index("const auto segmentedConnectedPlan =")
slice_end = bridge.index("s.pending = true;", slice_start)
submission = bridge[slice_start:slice_end]
for token in (
    "game_sm3_segmented_connected_submission_plan(",
    "game_sm3_expand_connected_instance_indices(",
    "fullConnectedChunkIndices",
    "tailConnectedChunkIndices",
    "segmentedConnectedPlan.grouped",
    "chunkInstances == chunkPlan.instancesPerChunk",
    "context->DrawIndexed(static_cast<UINT>(chunkIndices.size()),",
    "D3D11_PRIMITIVE_TOPOLOGY_LINELIST",
    "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST",
    "s.frameBatch.abort();",
):
    assert token in submission, token
assert "limit / instancesPerUpload" in helper
assert "pointFill || wireFill" in helper
assert "const UINT nativeSubmissionCount = segmentedInstanceUpload" in submission
print("01081 segmented connected GPU DrawIndexed source contract: PASS")
