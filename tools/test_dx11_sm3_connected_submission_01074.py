#!/usr/bin/env python3
"""01074: actual SM3 game Draw integration of segmented connected instances."""
from pathlib import Path
source = Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
required = (
    '#include "live_game_sm3_connected_submission.hpp"',
    "game_sm3_connected_submission_plan(",
    "connectedSubmission.mode == GameSm3ConnectedSubmissionMode::invalid",
    "connectedSubmission.mode == GameSm3ConnectedSubmissionMode::compact_indexed",
    "connectedSubmission.drawCount",
    "const UINT base = segmentedInstanceUpload",
    "context->DrawIndexed(nativeIndexCount, 0u, static_cast<INT>(base));",
    "context->Draw(vertices, base);",
    "((compactConnectedInstances || segmentedConnectedPlan.grouped) ? D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST",
    "((compactConnectedInstances || segmentedConnectedPlan.grouped) ? D3D11_PRIMITIVE_TOPOLOGY_LINELIST",
    "game_sm3_segmented_connected_submission_plan(",
    "context->DrawIndexed(static_cast<UINT>(chunkIndices.size()),",
)
for entry in required:
    assert entry in source, f"Native SM3 connected-instance integration missing: {entry}"
# The per-instance plan must NOT treat an over-budget index expansion as an
# unsupported original D3D9 shader-bound draw.
assert "const bool compactConnectedInstances = connectedCandidate &&" in source
assert "if (compactConnectedInstances) {" in source
print("01074 source/native per-instance GPU Draw integration: PASS")
