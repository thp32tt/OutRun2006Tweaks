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
    "s.clearColor.matches(", "s.frameBatch.accepts_full_on_source_target(",
    "s.frameBatch.accepts_source_draw(", "s.preDrawFills.count != 0u",
    "GetVertexDeclaration(", "GetVertexShaderConstantF(",
    "GetPixelShaderConstantF(", "capture_live_sm3_sampler(",
    "mirror_texture(", "CreateInputLayout(", "GetVertexShader(",
    "GetPixelShader(", "context->Draw(", "context->DrawIndexed(",
    "context->PSSetShaderResources(0u, 16u,", "context->PSSetSamplers(0u, 16u,",
    "context->VSSetConstantBuffers(", "context->PSSetConstantBuffers(",
    "s.frameBatch.succeeded(", "s.frameBatch.record_source_draw(sourceOrdinal)",
):
    check(condition in source, "missing real game source-to-GPU binding: " + condition)

for rejection in (
    "blend || alpha || stencil || depth != D3DZB_FALSE",
    "fog || scissor || clipPlanes || fill != D3DFILL_SOLID",
    "cull != D3DCULL_NONE || colorMask != 0x0fu",
    "srgbWrite != FALSE", "if (indices[i] >= vertexCount) return false;",
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
