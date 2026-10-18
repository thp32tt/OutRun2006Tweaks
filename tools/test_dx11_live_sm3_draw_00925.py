#!/usr/bin/env python3
"""Bounded SM3 live-game Draw source/negative regression (not runtime proof)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
bridge = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
backend = (ROOT / "src/vr/d3d11/native_backend.cpp").read_text()
header = (ROOT / "src/vr/d3d11/native_backend.hpp").read_text()

def check(condition, detail):
    if not condition:
        raise SystemExit("DX11 live SM3 draw FAIL: " + detail)

match = re.search(
    r"bool submit_live_sm3_game_draw\(.*?\) noexcept \{(.*?)\n\}\n\n// Reuse geometric",
    bridge, re.S)
check(match is not None, "real game GPU draw function absent")
source = match.group(1)
for condition in (
    "env_full_game_opt_in()", "game_native_backbuffer_ready(game, viewport)",
    "s.clearColor.matches(", "liveBatch.accepts_full_on_source_target(",
    "liveBatch.accepts_source_draw(", "s.preDrawFills.count != 0u",
    "GetVertexDeclaration(", "GetVertexShaderConstantF(",
    "GetPixelShaderConstantF(", "capture_live_sm3_sampler(",
    "mirror_texture(", "CreateInputLayout(", "GetVertexShader(",
    "GetPixelShader(", "context->Draw(", "context->DrawIndexed(",
    "context->PSSetShaderResources(0u, 16u,", "context->PSSetSamplers(0u, 16u,",
    "context->VSSetConstantBuffers(", "context->PSSetConstantBuffers(",
    "liveBatch.succeeded(", "liveBatch.record_source_draw(sourceOrdinal)",
):
    check(condition in source, "missing real game source-to-GPU binding: " + condition)

for rejection in (
    "alpha || stencil || fog || clipPlanes || fill != D3DFILL_SOLID",
    "game_native_depth_admission(", "depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE",
    "s.clearColor.main_depth_still_bound(",
    "if (!liveBatch.accepts_depth(liveDepth.enabled, reverseDepth))",
    "if (scissor != FALSE)", "gameRect.right <= gameRect.left",
    "r <= l || b <= t",
    "colorMask != 0x0fu || srgbWrite != FALSE",
    "srgbWrite != FALSE", "if (nativeIndices[i] >= vertexCount) return false;",
    "if (s.liveSm3Pipelines.size() >= 64u) return false;",
    "if (pipeline.vertexTokens != vertexEvidence.tokens",
):
    check(rejection in source, "missing fail-closed source/state rejection: " + rejection)

layout = bridge.partition("bool live_sm3_input_layout(")[2].partition(
    "bool live_sm3_shader_bytes(")[0]
for token in ("D3DDECLTYPE_FLOAT1", "D3DDECLTYPE_FLOAT2",
              "D3DDECLTYPE_FLOAT3", "D3DDECLTYPE_FLOAT4",
              "default: return false;", "in.Stream != 0u",
              "static_cast<UINT>(in.Offset) + width > stride"):
    check(token in layout, "unsupported vertex declaration admitted: " + token)

composite = (ROOT / "src/vr/d3d11/live_game_sm3_composite.hpp").read_text()
for token in (
    "game_native_cull_admission(", "D3DRS_SRCBLEND",
    "D3DRS_DESTBLEND", "D3DRS_BLENDOP",
    "D3DRS_SEPARATEALPHABLENDENABLE", "live_sm3_blend(",
    "nativeBlend == LiveSm3Blend::unsupported", "context->RSSetState(liveRaster)",
    "context->OMSetBlendState(liveBlend",
    "s.diagnosticCullRasters[scissorSlot].Get()",
    "s.diagnosticCullRasters[scissorSlot + 1u].Get()",
    "s.scissorRaster.Get()",
    "s.alphaBlend.Get()", "s.additiveBlend.Get()",
    "s.sourceAlphaAddBlend.Get()", "s.premultipliedAlphaBlend.Get()",
):
    check(token in source, "live GPU raster/composite source missing: " + token)
for token in (
    "operation != 1u", "separateAlpha ||", "source == 5u && destination == 6u",
    "source == 2u && destination == 2u",
    "source == 5u && destination == 2u",
    "source == 2u && destination == 6u",
    "LiveSm3Blend::unsupported", "static_assert(",
):
    check(token in composite, "native D3D9 blend mapping/fallback missing: " + token)

# The SM3 real-game fan expansion changes the physical index buffer owner.
# The exact post-conversion pointer/count must be checked before the dynamic
# D3D11 upload; do not silently validate only the old D3D9 index pointer.
for token in (
    "if (nativeIndices) {",
    "for (UINT i = 0; i < nativeIndexCount; ++i)",
    "if (nativeIndices[i] >= vertexCount) return false;",
    "s.fullGameIndexCapacity, nativeIndices, indexBytes",
    "context->DrawIndexed(nativeIndexCount, 0u, 0);",
):
    check(token in source, "SM3 converted game index ownership missing: " + token)

# New live SM3 raster/DSV implementation must bind actual GPU state, not
# merely lift the old unsupported-depth/scissor admission rejection. Preserve
# source-owned depth identity, first/continued Z clears, per-draw raster
# clipping, full native Draw and a fail-closed game fallback.
for token in (
    "D3DRS_ZWRITEENABLE", "D3DRS_ZFUNC", "D3DRS_DEPTHBIAS",
    "D3DRS_SLOPESCALEDEPTHBIAS", "GetDepthStencilSurface(",
    "s.diagnosticDepthView", "DXGI_FORMAT_D32_FLOAT",
    "D3D11_DEPTH_WRITE_MASK_ZERO", "D3D11_COMPARISON_LESS_EQUAL",
    "D3D11_COMPARISON_GREATER_EQUAL", "CreateDepthStencilState(",
    "context->OMSetRenderTargets(", "liveDepth.enabled ? s.diagnosticDepthView.Get()",
    "context->OMSetDepthStencilState(liveDepthState, 0u)",
    "liveBatch.depth_clear_value(reverseDepth)",
    "liveBatch.consume_depth_clear()",
    "liveBatch.succeeded(liveDepth.enabled, reverseDepth)",
    "context->RSSetScissorRects(1u, &liveScissor)",
    "scissor != FALSE ? 2u : 0u",
    "scissor != FALSE ? s.scissorRaster.Get()",
):
    check(token in source, "SM3 real game Z/scissor GPU path absent: " + token)
# Negative mutation markers: guard disabled or unrelated source Z surfaces,
# W-buffer/bias/MSAA, malformed scissor and mixed Z ordering.
for token in (
    "depthDesc.Width != source.Width", "depthDesc.Height != source.Height",
    "depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE",
    "!s.clearColor.main_depth_still_bound(",
    "if (r <= l || b <= t) return false;",
    "if (!liveBatch.accepts_depth(liveDepth.enabled, reverseDepth))",
):
    check(token in source, "SM3 unsafe Z/scissor fallback admitted: " + token)
check("build_r283_sm3_mov_shader_source(vertexSource, true" in backend and
      "build_r283_sm3_mov_shader_source(pixelSource, false" in backend and
      'vertexHlsl.find("r283_texture")' in backend and
      "candidate.pixelSamplerMask" in backend and
      "CreatePixelShader(" in backend and "CreateVertexShader(" in backend,
      "native programmable SM3 pair must create real GPU objects")
check("struct NativeLiveSm3Program" in header and
      "s.liveSm3Pipelines.clear();" in bridge and
      "if (!submit_live_sm3_game_draw(" in bridge and
      "s.frameBatch.abort();" in bridge.partition(
          "if (!submit_live_sm3_game_draw(")[2][:350],
      "native shader source ownership or fallback missing")
print("DX11 live SM3 source/negative GPU-boundary regression PASS (runtime UNTESTED)")
