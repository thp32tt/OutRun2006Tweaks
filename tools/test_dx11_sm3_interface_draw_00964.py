#!/usr/bin/env python3
"""Validate true game shader DCL -> native DX11 IA/VS/PS extended interface.
All runtime game/HMD observations remain UNTESTED."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/live_game_sm3_interface_capacity.hpp").read_text()
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
stream = (root / "src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
assert "inputs <= (vertexStage ? 16u : 10u)" in header
assert "outputs <= 12u" in header and "outputs == 0u" in header
assert "native_sm3_interface_decl_capacity(" in backend
assert "inputs.size() > 8u" not in backend
assert "native_sm3_ia_element_capacity(layout.size() + 1u)" in bridge
assert "game_sm3_assemble_streams(elements,streams,vertexCount,unpacked)" in bridge
assert "device->CreateInputLayout(" in bridge
assert "context->IASetInputLayout(pipeline.inputLayout.Get())" in bridge
assert "if (nativeIndices) context->DrawIndexed" in bridge
assert "destination.swap(candidate)" in stream
assert "if (!submit_live_sm3_game_draw(" in bridge
assert "s.frameBatch.abort();" in bridge
print("SM3 16/12/10 game interface, multistream native Draw and fail-closed fallback wired; no runtime result claimed")
