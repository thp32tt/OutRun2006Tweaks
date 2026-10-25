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
assert "instruction.opcode == D3DSIO_TEX &&" in predication
assert "!predicateDrawUniformity.implicit_sampling_safe(true)" in predication
assert "instruction.opcode == D3DSIO_TEXLDD)" not in predication
# Implicit TEX is still denied under pixel-varying IFC or unproven p0;
# genuine draw-uniform SETP p0 and D3D9 IF b# now admit native sampling.
assert "!predicateDrawUniformity.implicit_sampling_safe(sourcePredicated)" in backend
assert "!derivativeUniformity.implicit_sampling_safe()" in backend
assert "predicateDrawUniformity.write(" in backend
# Branch/loop admission now follows the explicit p0 physical provenance
# tracker, not a blanket structuredFlow.empty() ban. Preserve the legacy
# varying-IFC and unknown-p0 denial while permitting uniform both-arm SETP.
assert "predicateDrawUniformity.uniform_flow() &&" in backend
assert "predicateDrawUniformity.begin_if(uniformComparison)" in backend
assert "predicateDrawUniformity.begin_if(true)" in backend
assert "predicateDrawUniformity.otherwise()" in backend
assert "predicateDrawUniformity.end_if()" in backend
assert "predicateDrawUniformity.begin_loop()" in backend
assert "predicateDrawUniformity.end_loop()" in backend
# A real IFC(c#,c#) is now correctly quad-uniform; a pixel-varying
# TEMP/input/vPos/vFace on EITHER side must not unlock implicit derivatives.
assert "NativeSm3IfcScalarOrigin::PixelDependent" in backend
assert "scalarOrigins[i] = NativeSm3IfcScalarOrigin::DrawFloatConstant;" in backend
assert "const bool uniformComparison = native_sm3_ifc_is_quad_uniform(" in backend
assert "if (!derivativeUniformity.begin(uniformComparison) ||" in backend
assert "!tempDrawUniformity.begin_if(uniformComparison)" in backend
assert "scalarOrigins[0], scalarOrigins[1]" in backend
assert "!derivativeUniformity.begin(true)" in backend
assert "!derivativeUniformity.end()" in backend
assert "!derivativeUniformity.empty()" in backend
assert "native_sm3_texture_mode_allowed_in_control_flow(" in backend
assert "return !conditional;" in texture
assert "case NativeSm3Texture2DMode::ExplicitLod:" in texture
assert "case NativeSm3Texture2DMode::Gradients:" in texture
assert 'sampling = ".SampleGrad("; break;' in texture
assert 'sampling = ".SampleLevel("; break;' in texture
import re
# Live TEX* capture now carries a vertex/pixel stage and a cube-sampler bit.
# Both paths must reach the guarded game-owned sampler snapshot, regardless
# of formatting or additional arguments added to the callsite.
for stage in ("true", "false"):
    assert re.search(
        r"capture_live_sm3_sampler\(\s*game,\s*slot,\s*capture,\s*" + stage + r"\s*,",
        bridge), "missing " + stage + " stage TEX* game sampler capture"
assert "vertexCubeSamplerMask" in bridge and "pixelCubeSamplerMask" in bridge
assert "context->PSSetShaderResources(0u, 16u, boundViews.data())" in bridge
assert "context->VSSetShaderResources(0u, 4u, boundVertexViews.data())" in bridge
assert re.search(r"if \(nativeIndices\)\s*context->DrawIndexed\(nativeIndexCount", bridge)
assert "const UINT nativeSubmissionCount = segmentedInstanceUpload" in bridge
assert "connectedCandidate ? connectedSubmission.drawCount : instanceCount" in bridge
assert "game_sm3_connected_submission_plan(" in bridge
assert "game_sm3_expand_connected_instance_indices(" in bridge
assert "compactConnectedInstances ? D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST" in bridge
assert "for (UINT instance = 0u; instance < nativeSubmissionCount; ++instance)" in bridge
assert "if (segmentedInstanceUpload && instance != 0u)" in bridge
assert "const UINT base = segmentedInstanceUpload ? 0u :" in bridge
print("Native game shader TEXLDD / TEXLDL conditional translation + fail-closed sampler path linked; HMD untested")
