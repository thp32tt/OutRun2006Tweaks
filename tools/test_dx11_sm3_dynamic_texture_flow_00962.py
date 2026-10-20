#!/usr/bin/env python3
"""Ensure game-owned SM3 TEXLDD / TEXLDL conditional Draw translation and DX9 fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
texture = (root / "src/vr/d3d11/native_sm3_texture_codegen.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
start = backend.index("if (sourcePredicated) {")
end = backend.index("op.sineCosine =", start)
predication = backend[start:end]
assert "instruction.opcode == D3DSIO_TEX)" in predication
assert "instruction.opcode == D3DSIO_TEXLDD)" not in predication
assert "sourcePredicated || !writtenFlow.empty()" in backend
assert "native_sm3_texture_mode_allowed_in_control_flow(" in backend
assert "return !conditional;" in texture
assert "case NativeSm3Texture2DMode::ExplicitLod:" in texture
assert "case NativeSm3Texture2DMode::Gradients:" in texture
assert 'sampling = ".SampleGrad("; break;' in texture
assert 'sampling = ".SampleLevel("; break;' in texture
assert "capture_live_sm3_sampler(game, slot, capture" in bridge
assert "context->PSSetShaderResources(0u, 16u, boundViews.data())" in bridge
assert "context->VSSetShaderResources(0u, 4u, boundVertexViews.data())" in bridge
assert "if (nativeIndices) context->DrawIndexed" in bridge
print("Native game shader TEXLDD / TEXLDL conditional translation + fail-closed sampler path linked; HMD untested")
