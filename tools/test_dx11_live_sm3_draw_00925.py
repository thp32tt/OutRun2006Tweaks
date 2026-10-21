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
    "if (fog != FALSE) {",
    "if (clipPlanes != 0u) {",
    "if (fill != D3DFILL_SOLID) {",
    "D3DRS_ALPHAFUNC", "D3DRS_ALPHAREF", "alphaRef > 255u",
    "alphaFunc < D3DCMP_NEVER", "alphaFunc > D3DCMP_ALWAYS",
    "pipeline.alphaCompare != alphaFunc", "pipeline.alphaReference",
    "context->PSSetConstantBuffers(1u, 1u, &alphaBuffer)",
    "game_native_depth_admission(", "depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE",
    "s.clearColor.main_depth_still_bound(",
    "if (!liveBatch.accepts_depth(liveDepth.enabled, reverseDepth))",
    "if (scissor != FALSE)", "gameRect.right <= gameRect.left",
    "r <= l || b <= t",
    "if ((colorMask & ~0x0fu) != 0u) {",
    "if (srgbWrite != FALSE) {",
    "if (!game_native_backbuffer_ready(game, viewport)) {",
    "++s.liveSm3StateRejectReasons[0];",
    "++s.liveSm3StateRejectReasons[1];",
    "++s.liveSm3StateRejectReasons[2];",
    "++s.liveSm3StateRejectReasons[3];",
    "++s.liveSm3StateRejectReasons[4];",
    "++s.liveSm3StateRejectReasons[5];",
    "++s.liveSm3StateRejectReasons[6];",
    "++s.liveSm3StateRejectReasons[7];",
    "if (nativeIndices[i] >= vertexCount) return false;",
    "if (s.liveSm3Pipelines.size() >= 64u) return false;",
    "pipeline.vertexTokens != vertexEvidence.tokens",
):
    check(rejection in source, "missing fail-closed source/state rejection: " + rejection)

layout = bridge.partition("bool live_sm3_input_layout(")[2].partition(
    "bool live_sm3_shader_bytes(")[0]
for token in ("D3DDECLTYPE_FLOAT1", "D3DDECLTYPE_FLOAT2",
              "D3DDECLTYPE_FLOAT3", "D3DDECLTYPE_FLOAT4",
              "default: return false;", "in.Stream != 0u",
              "static_cast<UINT>(in.Offset) + width > sourceStride"):
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

# Real programmable menu/race lines already exist in the D3D9 observer,
# but must reach the actual native SM3 IA topology instead of being
# reinterpreted as triangles. Unsupported AA/LASTPIXEL must fail closed.
for token in (
    "type != D3DPT_LINELIST && type != D3DPT_LINESTRIP",
    "D3DRS_ANTIALIASEDLINEENABLE", "D3DRS_LASTPIXEL",
    "game_native_sm3_line_raster(static_cast<std::uint32_t>(type),",
    "D3D11_PRIMITIVE_TOPOLOGY_LINELIST",
    "D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP",
    "type == D3DPT_LINELIST ? D3D11_PRIMITIVE_TOPOLOGY_LINELIST :",
    "context->IASetPrimitiveTopology(type == D3DPT_POINTLIST ?",
    "D3D11_PRIMITIVE_TOPOLOGY_POINTLIST",
):
    check(token in source, "live SM3 game point/line GPU routing absent: " + token)
# D3D9 already exposes POINTLIST source spans to both indexed and
# non-indexed hooks. Assert the genuine shader-bound game Draw now reaches
# the native IA with original indexed/nonindexed geometry, but only under a
# one-pixel point raster. Unsupported PSIZE/sprites/scaled points return to
# original D3D9 before native pipeline/upload mutation.
for token in (
    "type != D3DPT_POINTLIST && type != D3DPT_TRIANGLELIST",
    "if (type == D3DPT_POINTLIST) {",
    "D3DRS_POINTSIZE, &size",
    "D3DRS_POINTSIZE_MIN, &minimum",
    "D3DRS_POINTSIZE_MAX, &maximum",
    "D3DRS_POINTSPRITEENABLE, &sprite",
    "D3DRS_POINTSCALEENABLE, &scaled",
    "declaration[i].Usage == D3DDECLUSAGE_PSIZE",
    "!game_native_unit_point_raster(",
    "context->Draw(vertexCount, 0u);",
    "context->DrawIndexed(nativeIndexCount, 0u, 0);",
):
    check(token in source, "real game SM3 point/fallback integration missing: " + token)
    check(token not in source.replace(token, "", 1),
          "point negative source mutation did not remove " + token)
check(source.index("!game_native_unit_point_raster(") <
      source.index("ensure_pipeline(s, source.Width, source.Height)") <
      source.index("context->DrawIndexed(nativeIndexCount"),
      "unsupported point mode must fail before native GPU mutation")
span_header = (ROOT / "src/vr/d3d11/live_game_primitive_span.hpp").read_text()
check("!antialiased && lastPixel" in span_header and
      "game_native_sm3_line_raster(3u, false, true)" in span_header,
      "live SM3 D3D9 line raster unsupported-state fallback absent")

# SM3 first-Draw source ColorFill must be replayed as actual GPU ClearView
# BEFORE native Draw and only after matching owner, extent and D3D11.1.
check("s.preDrawFills.count != 0u || viewport.Width" not in source,
      "real SM3 source ColorFill still rejected unconditionally")
for token in (
    "s.preDrawFills.replay_ready(", "s.clearColor.matches(owner, targetId)",
    "IID_PPV_ARGS(preDrawContext.GetAddressOf())",
    "preDrawContext->ClearView(s.backend.color_rtv(), rgba, &rect, 1u)",
    "s.clearColor.opaqueDestinationAlpha ? 1.0f",
    "s.preDrawFills.discard();",
):
    check(token in source, "live SM3 pre-Draw replay missing: " + token)
check(source.index("s.preDrawFills.replay_ready(") <
      source.index("upload_full_game_stream(") <
      source.index("preDrawContext->ClearView(") <
      source.index("context->DrawIndexed(nativeIndexCount"),
      "SM3 pre-Draw validation/replay must precede GPU draw")
fill_header = (ROOT / "src/vr/d3d11/native_game_source_mutation.hpp").read_text()
for token in (
    "constexpr bool replay_ready(", "!belongs_to(currentDevice, currentBackbuffer)",
    "count > kCapacity", "fill.right > static_cast<std::int64_t>(width)",
    "fill.bottom > static_cast<std::int64_t>(height)",
):
    check(token in fill_header, "unsafe pre-Draw ColorFill replay: " + token)

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
check(re.search(
          r"build_r283_sm3_mov_shader_source\(\s*vertexSource,\s*true,\s*vertexHlsl",
          backend) and
      re.search(
          r"build_r283_sm3_mov_shader_source\(\s*pixelSource,\s*false,\s*pixelHlsl",
          backend) and
      "candidate.vertexSamplerMask" in backend and
      "(vertexStage && reg >= 4u)" in backend and
      "candidate.pixelSamplerMask" in backend and
      "CreatePixelShader(" in backend and "CreateVertexShader(" in backend and
      "append_native_sm3_alpha_test(pixelHlsl, alphaCompare)" in backend,
      "native programmable SM3 pair must create real GPU objects")
check("struct NativeLiveSm3Program" in header and
      "s.liveSm3Pipelines.clear();" in bridge and
      "if (!submit_live_sm3_game_draw(" in bridge and
      "s.frameBatch.abort();" in bridge.partition(
          "if (!submit_live_sm3_game_draw(")[2][:350],
      "native shader source ownership or fallback missing")
# Preserve the real (nine-argument) observer after multi-stream ownership
# was added, including empty legal draws. D3DVERTEXELEMENT9::Stream is WORD,
# while GameSm3ElementRef::stream is uint8_t: the preceding declaration
# validation proves < 4, so explicitly narrow rather than failing MSVC C2397.
check("static_cast<std::uint8_t>(declaration[i].Stream)" in bridge,
      "actual SM3 multistream vertex declaration fails Win32 C2397")
check("observe(game, type, 0u, nullptr, 0u, 0u, nullptr, 0u, nullptr);" in bridge,
      "empty game draw missing additional-stream argument (Win32 C2660)")

# Real D3D9 vertex-stage TEXLDL samples the independent game texture
# namespace 256..259, never pixel samplers 0..15. The VS HLSL program
# must explicitly own its required stages, and both native shader stages
# must bind their own resources on the same immediate Draw context.
slot_header = (ROOT / "src/vr/d3d11/live_game_sm3_sampler_slots.hpp").read_text()
for required in (
    "shaderRegister < 4u ? 256u + shaderRegister",
    "shaderRegister < 16u ? shaderRegister",
    "kGameSm3InvalidSamplerSlot",
):
    check(required in slot_header,
          "missing distinct D3D9 VS/PS sampler ownership: " + required)
for required in (
    "case D3DSIO_TEXLDL:", "if ((instruction.instructionToken & 0x00ff0000u) != 0u)",
    "candidate.vertexSamplerMask", "candidate.pixelSamplerMask",
    "(vertexStage && reg >= 4u)",
):
    check(required in backend, "unsafe native SM3 VS texture compiler: " + required)
for required in (
    "game_sm3_sampler_source_slot(vertexStage, slot)",
    "game->GetTexture(sourceSlot,", "game->GetSamplerState(sourceSlot,",
):
    check(required in bridge, "missing source game vertex sampler capture: " + required)
for required in (
    "capture_live_sm3_sampler(",
    "vertexViews[slot], vertexSamplers[slot]",
    "boundVertexViews[slot] = vertexViews[slot].Get();",
    "boundVertexSamplers[slot] = vertexSamplers[slot].Get();",
    "context->VSSetShaderResources(0u, 4u, boundVertexViews.data());",
    "context->VSSetSamplers(0u, 4u, boundVertexSamplers.data());",
    "context->PSSetShaderResources(0u, 16u, boundViews.data());",
    "context->PSSetSamplers(0u, 16u, boundSamplers.data());",
):
    check(required in source, "real-game VS texture binding/fallback absent: " + required)
    # Removing ANY single required GPU binding/capture must fail the contract;
    # this remains a negative safety check, not a string-only readiness PASS.
    check(required not in source.replace(required, "", 1),
          "source mutation failed to remove required VS/PS binding: " + required)

# The D3D9 vertex sampler namespace and pixel sampler namespace must each
# select their own cube flag before touching the native GPU.
for stage, mask in (("true", "vertexCubeSamplerMask"),
                    ("false", "pixelCubeSamplerMask")):
    capture_pattern = (
        r"capture_live_sm3_sampler\(\s*game,\s*slot,\s*capture,\s*" +
        stage + r"\s*,\s*\(pipeline\.program\." + mask +
        r"\s*&\s*\(1u\s*<<\s*slot\)\)\s*!=\s*0u\)"
    )
    check(re.search(capture_pattern, source) is not None,
          "missing stage-owned live SM3 sampler/cube dispatch: " + mask)
    check(re.search(capture_pattern, source.replace(mask, "removed_mask", 1)) is None,
          "sampler cube negative mutation survived: " + mask)

# Programmable shader translation must admit only actually-read TEMP lanes:
# native VS/PS code generation consumes the helper directly; real unwritten
# channels, scalar/dot/matrix and TEX coordinates stay fail-closed.
for token in (
    "native_sm3_source_components(op.opcode, mask, i)",
    "case D3DSIO_TEXKILL:",
    "case D3DSIO_DSX:",
    "case D3DSIO_DSY:",
    "op.texkill = instruction.opcode == D3DSIO_TEXKILL;",
    "native_sm3_texkill_ready(",
    "op.texkillWrittenMask = tempWritten[op.destinationRegister];",
    "op.texkillWrittenMask, static_cast<unsigned>(i)",
    "append_native_sm3_texkill(",
    "native_sm3_swizzled_components(",
    "native_sm3_texture_source_components(op.textureMode, i)",
    "case D3DSIO_TEXLDD:", "case D3DSIO_TEXLDL:",
    "NativeSm3Texture2DMode::Projected",
    "NativeSm3Texture2DMode::Bias",
    "NativeSm3Texture2DMode::ExplicitLod",
    "NativeSm3Texture2DMode::Gradients",
    "case D3DSIO_M4x3:", "case D3DSIO_M3x4:", "case D3DSIO_M3x2:",
    "op.matrixRowCount != 0u", "op.matrixVectorComponents == 4u ? 15u : 7u",
    "op.matrixRowCount, static_cast<unsigned>(i)",
    "(tempWritten[reg] & required) != required",
):
    check(token in backend, "SM3 partial-register source/negative path missing: " + token)
# Matrix address arithmetic now uses subtraction after a base bound check,
# avoiding unsigned base+rows wrap and checking relative row coverage.
check("reg >= constantLimit ||" in backend and
      "op.matrixRowCount > constantLimit - reg" in backend and
      "native_sm3_relative_matrix_references(" in backend,
      "SM3 matrix relative source range/fail-closed admission absent")
# Game-created matrix operands must translate into native row-dot GPU
# shaders; unsupported destination lanes and unwritten TEMP xyz/w must
# still reject rather than borrow D3D9's undefined data.
for token in (
    "case D3DSIO_M4x4:", "case D3DSIO_M4x3:",
    "case D3DSIO_M3x4:", "case D3DSIO_M3x3:",
    "case D3DSIO_M3x2:", "op.matrixRowCount = 2u",
    "op.matrixVectorComponents = 3u",
    "(mask & ~((1u << op.matrixRowCount) - 1u))",
    "row < op.matrixRowCount; ++row",
    "op.matrixVectorComponents == 4u ? 15u : 7u",
):
    check(token in backend, "matrix native path or fallback missing: " + token)

arith = (ROOT / "src/vr/d3d11/native_sm3_arithmetic_codegen.hpp").read_text()

# The actual game SM3->HLSL->GPU draw path must implement procedural
# sin/cos and VS-only sign with physical TEMP scratch invalidation.
for token in ("case D3DSIO_SINCOS:", "case D3DSIO_SGN:",
              "NativeSm3ArithmeticOpcode::SineCosine",
              "NativeSm3ArithmeticOpcode::Sign",
              "op.sineCosine = instruction.opcode == D3DSIO_SINCOS;",
              "op.signScratch = instruction.opcode == D3DSIO_SGN;",
              "swizzle != 0x55u", "reg == op.signInputTemp",
              "reg == op.destinationRegister", "reg == op.signTemps[0]",
              "tempWritten[scratch] = 0u;"):
    check(token in backend, "missing native SM3 procedural draw/source fallback: " + token)
for token in ("cos(", "sin(", "sign(", "(mask & ~0x03u)"):
    check(token in arith, "missing native SM3 HLSL math: " + token)

# Vertex lighting/distance ops flow through the real game-created shader
# bytecode decoder and the native GPU shader emitter, never through a
# fixed-function dummy pixel path. Unsupported PS opcode still fails closed.
arith = (ROOT / "src/vr/d3d11/native_sm3_arithmetic_codegen.hpp").read_text()
for opcode, kind in (("D3DSIO_LIT", "Lighting"), ("D3DSIO_DST", "Distance")):
    check("case " + opcode + ":" in backend and
          "NativeSm3ArithmeticOpcode::" + kind in backend and
          "NativeSm3ArithmeticOpcode::" + kind in arith,
          "missing live vertex shader lighting/distance operation: " + opcode)
check(backend.count("if (!vertexStage) return false;") >= 2,
      "vertex-only lighting/distance must fail closed for pixel shader")
check("127.9961f" in arith and "destinationMask & 0x0au" in arith and
      "sourceIndex == 0u" in arith,
      "D3D9 lit power clamp or dst physical lane contract missing")

# Native alpha testing is a real translated PS/CB resource, never a
# removed D3D9 alpha admission check or a disabled game's alpha stage.
alpha_helper = (ROOT / "src/vr/d3d11/live_game_sm3_alpha_test.hpp").read_text()
for required in ("register(b1)", "discard;", "r283_alpha_ref", "saturate(",
                 "case 1u:", "case 7u:", "case 8u:"):
    check(required in alpha_helper, "D3D9 alpha comparison missing: " + required)
check("hashBytes(&alphaCompare, sizeof(alphaCompare))" in bridge and
      "pipeline.alphaCompare = alphaFunc;" in bridge and
      "UpdateSubresource(pipeline.alphaReference.Get()" in bridge,
      "live alpha compare must be cached and uploaded per real Draw")
# Validate the actual real-game source-to-OM mask path and negative states.
for token in (
    "sm3_live_masked_blend_desc(", "D3DRS_COLORWRITEENABLE",
    "b.RenderTargetWriteMask = static_cast<UINT8>(writeMask);",
    "static_cast<std::uint64_t>(b.RenderTargetWriteMask) << 48u",
    "static_cast<std::uint64_t>(b.BlendEnable != FALSE) << 56u",
    "sm3_live_masked_blend_regression()",
    "D3D11_COLOR_WRITE_ENABLE_ALPHA", "if (customBlend)",
    "liveBlend = extendedBlend;",
    "context->OMSetBlendState(liveBlend, nullptr, 0xffffffffu);",
):
    check(token in bridge, "masked real SM3 Draw GPU output missing: " + token)
check("colorMask != 0x0fu || srgbWrite" not in source and
      "if ((colorMask & ~0x0fu) != 0u) {" in source and
      "if (srgbWrite != FALSE) {" in source,
      "valid per-game-Draw partial channel mask still rejected")
check("if (customBlend &&" in source and
      "sm3_live_masked_blend_desc(" in source,
      "native game draw must fail before GPU mutation for invalid OM states")
print("DX11 live SM3 source/negative GPU-boundary regression PASS (runtime UNTESTED)")

# Native programmable menu/car/race Draw: admit inert stencil and MRT without
# ever losing a conditional stencil test or writable extra D3D9 target.
# Keep this assertion scoped to the *real live SM3 submit*, not a helper or
# the fixed-function probe, so accidental fallback-only wiring is detected.
sm3 = bridge.split("bool submit_live_sm3_game_draw(", 1)[1].split(
    "// Reuse geometric growth buffers", 1)[0]
def inert_gpu_draw_linked(body):
    return all(token in body for token in (
        "GetRenderState(D3DRS_STENCILFUNC, &stencilFunc)",
        "GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)",
        "GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)",
        "stencil_equivalent_to_disabled(",
        "GetDeviceCaps(&caps)",
        "valid_mrt_count(caps.NumSimultaneousRTs)",
        "GetRenderTarget(slot, extra.GetAddressOf())",
        "if (hr == D3DERR_NOTFOUND) continue;",
        "GetRenderState(extraColorMasks[slot - 1u],",
        "extra_target_inert(true, extraMask)",
        "context->Draw(", "context->DrawIndexed(",
    )) and "stencil || fog || clipPlanes" not in body
check(inert_gpu_draw_linked(sm3), "live SM3 draw must check inert stencil and every extra MRT")
for token in (
    "stencil_equivalent_to_disabled(",
    "GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)",
    "GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)",
    "valid_mrt_count(caps.NumSimultaneousRTs)",
    "GetRenderTarget(slot, extra.GetAddressOf())",
    "extra_target_inert(true, extraMask)",
):
    check(not inert_gpu_draw_linked(sm3.replace(token, "removed_guard(", 1)),
          "SM3 live native fallback regression did not detect removal of " + token)

print('DX11 live SM3 inert-stencil/MRT positive and negative source regression PASS')
