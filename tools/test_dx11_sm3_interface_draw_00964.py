#!/usr/bin/env python3
"""Validate true game shader DCL -> native DX11 IA/VS/PS extended interface.
All runtime game/HMD observations remain UNTESTED."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/live_game_sm3_interface_capacity.hpp").read_text()
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
stream = (root / "src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
# ps_3_0 vPos/vFace are rasterizer system inputs, not v# interpolants;
# vs_3_0 still caps at sixteen attributes and forbids all misc inputs.
assert "systemInputs == 0u && inputs <= 16u" in header
assert "inputs - systemInputs <= 10u" in header
assert "systemInputs > inputs || systemInputs > 2u" in header
assert "native_sm3_interface_decl_capacity(false, 12u, 0u, 2u)" in header
assert "!native_sm3_interface_decl_capacity(false, 13u, 0u, 2u)" in header
assert "!native_sm3_interface_decl_capacity(true, 3u, 1u, 1u)" in header
assert "outputs <= 12u" in header and "outputs == 0u" in header
assert "native_sm3_interface_decl_capacity(" in backend
assert "inputs.size() > 8u" not in backend
assert "native_sm3_ia_element_capacity(layout.size() + 1u)" in bridge
assert "elements, streams, vertexCount, unpacked)" in bridge
assert "device->CreateInputLayout(" in bridge
assert "context->IASetInputLayout(pipeline.inputLayout.Get())" in bridge
assert "context->DrawIndexed(nativeIndexCount, 0u, static_cast<INT>(base))" in bridge
assert "destination.swap(candidate)" in stream
assert "if (!submit_live_sm3_game_draw(" in bridge
assert "s.frameBatch.abort();" in bridge
print("SM3 VS16/12 PS10+vPos/vFace game interface, multistream native Draw and fail-closed fallback wired; no runtime result claimed")
