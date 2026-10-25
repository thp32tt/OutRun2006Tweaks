#!/usr/bin/env python3
"""00992 native game SM3 D3D9 instance-rate replay integration (static scope)."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
assembly = (root / "src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
assert "game_sm3_assemble_instanced_streams(" in bridge
assert "game_sm3_assemble_instanced_streams(" in assembly
assert "sourceFrequency != 1u" in bridge
assert "(frequency & ~kStreamFrequencyMask) == kStreamInstanced" in bridge
assert "instance * vertexCount" in bridge
assert "context->DrawIndexed(nativeIndexCount, 0u, static_cast<INT>(base))" in bridge
assert "context->Draw(vertexCount, base)" in bridge
assert "issueNativeGameDraw(" in bridge
assert "instance % chunkPlan.instancesPerChunk == 0u" in bridge
assert "const UINT nativeSubmissionCount = segmentedInstanceUpload" in bridge
assert "connectedCandidate ? connectedSubmission.drawCount : instanceCount" in bridge
assert "game_sm3_connected_submission_plan(" in bridge
assert "game_sm3_expand_connected_instance_indices(" in bridge
assert "compactConnectedInstances ? D3D11_PRIMITIVE_TOPOLOGY_LINELIST" in bridge
assert "compactConnectedInstances ? D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST" in bridge
assert "game_sm3_expand_list_instance_indices(" in bridge
assert "hashBytes(&packedFloat4, sizeof(packedFloat4));" in bridge
assert "sourceInstancing && !repack" in bridge
assert "sourceInstancing" in bridge
assert "liveBatch.record_source_draw(sourceOrdinal);" in bridge
assert "env_full_game_opt_in()" in bridge
print("00992 DX9 instance frequency -> native packed IA / GPU Draw: PASS_STATIC")
