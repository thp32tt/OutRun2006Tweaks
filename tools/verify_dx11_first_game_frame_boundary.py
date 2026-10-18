#!/usr/bin/env python3
"""Constrained activation review for the FIRST_GAME_DRAW_FRAME diagnostic.

This is an admission check, NOT evidence that a game/HMD frame was drawn.
Only the verified live FVF and bounded SM3 paths are admitted; other D3D11 Draw* still fail
verify_dx11_activation_boundary.py.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DX11 = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
ACTIVE_R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
HEADER = ROOT / "src/vr/d3d11/live_game_frame_bridge.hpp"
NATIVE = ROOT / "src/vr/d3d11/native_backend.hpp"

def require(value: bool, reason: str) -> None:
    if not value:
        raise SystemExit("DX11 FIRST_GAME_DRAW_FRAME activation unsafe: " + reason)

def validate(code: str, caller: str, header: str, native: str) -> None:
    require("bool diagnostic_enabled() noexcept" in code and
            "GetEnvironmentVariableW(L\"OUTRUN_DX11_FIRST_GAME_FRAME\"" in code and
            "value[0] == L'1'" in code,
            "explicit opt-in must be exact; diagnostics disabled by default")
    require("if (!diagnostic_enabled() || !game" in code,
            "both real game call and opt-in must be checked before observation")
    # The previous literal FVF whitelist was replaced by an exact layout
    # decoder. Verify the new producer and its texture-only consumer together,
    # rather than accepting an obsolete D3DFVF_XYZRHW|DIFFUSE token.
    fvf = (ROOT / "src/vr/d3d11/live_game_fvf_layout.hpp").read_text(
        encoding="utf-8")
    require("if (!game_fvf_layout(fvf, layout)) return false;" in code and
            # Texture coordinates still define the physical FVF vertex
            # stride when fixed-function stage 0 selects DIFFUSE only.
            # That state must bypass a stale sampler, but any real texture
            # operand or active following stage still needs native mirror or
            # DX9Ex fallback. Do NOT regress to unconditional TEXn admission.
            "game_fvf_diffuse_only_inactive_texture(" in code and
            "followingColorOp, layout.hasDiffuse);" in code and
            "capture.enabled = layout.textured && !diffuseOnly;" in code and
            "capture.inactiveStage0TextureBypass = diffuseOnly && layout.textured;" in code and
            "else if (tex && !diffuseOnly)" in code and
            "if (!layout.hasDiffuse && !selectTexture) return false;" in code and
            "if (!game_fvf_decode_vertex(data, stride, layout, decoded))" in code and
            "kGameFvfPositionMask == D3DFVF_POSITION_MASK" in code and
            "GetVertexShader(vs.GetAddressOf())" in code and
            "GetPixelShader(ps.GetAddressOf())" in code and
            "GetTexture(0, tex.GetAddressOf())" in code,
            "unsupported live D3D9 shader/texture states must be rejected")
    require("const std::uint32_t position = fvf & kGameFvfPositionMask;" in fvf and
            "if (!candidate.textured && !candidate.hasDiffuse) return false;" in fvf and
            "stride < layout.minStride" in fvf and
            "sample = candidate;" in fvf,
            "live FVF decoder must reject unsupported formats and short strides")
    require("GetRenderState(D3DRS_ALPHABLENDENABLE" in code and
            "GetRenderState(D3DRS_ZENABLE" in code,
            "blended/depth state must be rejected")
    # The game-owned diagnostic now admits both bounded D3D9 line families
    # as well as triangles. Inspect the shared enumerated span validator and
    # the live observer together so an unknown primitive cannot be promoted.
    span = (ROOT / "src/vr/d3d11/live_game_primitive_span.hpp").read_text(
        encoding="utf-8")
    require("game_native_primitive_element_count(static_cast<std::uint32_t>(type)," in code and
            all(f"case {kind}u:" in span for kind in (2, 3, 4, 5, 6)) and
            "default: return false;" in span and
            "kMaxNativeGamePrimitives = 2048u" in span and
            "kMaxNativeGamePrimitives * 3u" in span and
            "primitiveCount == 0u || primitiveCount > kMaxNativeGamePrimitives" in span and
            "required > kMaxNativeGameVertices" in span and
            "static_assert(game_native_mesh_span_contract()" in span and
            "observe_unavailable_game_draw(game);" in code and
            "indexCount != expectedElements" in code and
            "vertexCount != expectedElements" in code and
            "indices[i] >= vertexCount" in code,
            "unknown/unbounded primitives or invalid indexed game draws must be rejected")
    require("topology == D3DPT_LINELIST || topology == D3DPT_LINESTRIP" in code and
            "GetRenderState(D3DRS_ANTIALIASEDLINEENABLE, &lineAA)" in code and
            "GetRenderState(D3DRS_LASTPIXEL, &lastPixel)" in code and
            "lineAA != FALSE || lastPixel != TRUE" in code and
            "D3D11_PRIMITIVE_TOPOLOGY_LINELIST" in code and
            "D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP" in code,
            "native lines must retain explicit source raster-state parity fencing")
    # Validate the complete source-to-inset chain. A bounded, fenced,
    # nonblocking copy is stricter than the old synchronous staging Map:
    # no CPU wait, no unread-slot overwrite, and checked RGB pixel evidence.
    require("s.backend.begin_frame(env_full_game_opt_in()" in code and
            "s.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)" in code and
            ": kBackground);" in code and
            "ctx->CopyResource(next.staging.Get(), s.backend.color_texture())" in code and
            "ctx->End(next.fence.Get());" in code and
            "D3D11_QUERY_EVENT" in code and
            "D3D11_ASYNC_GETDATA_DONOTFLUSH" in code and
            "D3D11_MAP_FLAG_DO_NOT_WAIT" in code and
            "if (!next.busy)" in code and
            "s.readSlot = (s.readSlot + 1u) % kReadbackSlots;" in code and
            "changedPixels" in code and
            "game->UpdateSurface(" in code and
            "s.insetFormat != bb.Format" in code,
            "native frame must reach checked nonblocking desktop output")
    # A foreign menu/video Reset must not dispose the game-owned full-frame
    # Draw/DrawIndexed scene, while an owning Reset must still release its GPU.
    reset = code.partition("void before_game_reset(IDirect3DDevice9* game) noexcept {")[2]
    gate = reset.find("if (!GameNativeFrameBatch::reset_belongs_to_game_source(")
    teardown = reset.find("s.pending = false;")
    shutdown = reset.find("s.backend.shutdown();")
    require(reset and 0 <= gate < teardown < shutdown and
            "s.previousOutput.valid() ? s.previousOutput.device : 0u" in
                reset[gate:teardown] and
            "return;" in reset[gate:teardown] and
            "s.frameBatch.reset();" in reset[teardown:shutdown] and
            "void before_game_reset(IDirect3DDevice9* gameDevice) noexcept;" in header,
            "device-owned Reset must preserve auxiliary scene and retire owned GPU")
    require("ctx->IASetVertexBuffers" in code and
            "ctx->IASetInputLayout" in code and
            "ctx->VSSetShader" in code and
            "ctx->PSSetShader" in code and
            "ctx->DrawIndexed(indexCount, 0, 0)" in code and
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0)" in code,
            "native IA/shader/Draw must use the captured data")
    require("NativeDrawPathActive" not in code and
            "NativeDrawPathActive" not in caller and
            "NativeDrawPathActive" not in header,
            "production native activation flag cannot be promoted")
    require('R30ObserveNativeLinearVB(device, type, startVertex, primitiveCount);' in caller and
            'R30ObserveNativeIndexedVB(device, type, baseVertexIndex,' in caller and
            'R30ObserveNativeIndexedUP(device, type, minVertexIndex, numVertices,' in caller and
            'live_game_frame::observe_linear(' in caller,
            "all four live D3D9 source families must be hooked")
    require("R30PresentR29Hook.stdcall<HRESULT>(" in caller and
            "R30DrawPrimitiveR29Hook.stdcall<HRESULT>(" in caller and
            "R30DrawIndexedPrimitiveR29Hook.stdcall<HRESULT>(" in caller and
            "R30DrawPrimitiveUPR29Hook.stdcall<HRESULT>(" in caller and
            "R30DrawIndexedPrimitiveUPR29Hook.stdcall<HRESULT>(" in caller,
            "DX9Ex fallback must retain the established D3D9 caller")
    reset_hook = caller.partition("HRESULT __stdcall ResetDestR30(")[2]
    require(reset_hook and
            "live_game_frame::before_game_reset(device);" in
                reset_hook.partition("return R30Reset")[0] and
            "live_game_frame::before_game_reset();" not in reset_hook and
            "before_game_present(device, sourceRect, dirtyRegion);" in caller and
            "const RECT* sourceRect, const RGNDATA* dirtyRegion" in header and
            "const auto insetPlacement = presentRegion.inset_placement(" in code and
            "insetPlacement.valid" in code,
            "Present and reset must be tied to the game's real R30 hooks")
    require("bool initialize(const NativeBackendConfig& config)" in native and
            "ID3D11RenderTargetView* color_rtv()" in native,
            "native device and render target ownership missing")
    # Native Draw dispatch is confined to two independently source-admitted
    # functions. Do not globally bless extra Draw* just because the new
    # programmable path exists: a third Draw must still fail this review.
    match = re.search(r"bool submit\s*\(.*?\) noexcept \{(.*?)\n\}\n\nbool observe_source_device\(", code, re.S)
    sm3 = re.search(r"bool submit_live_sm3_game_draw\s*\(.*?\) noexcept \{(.*?)\n\}\n\n// Reuse geometric growth", code, re.S)
    require(match is not None and sm3 is not None,
            "both isolated FVF and SM3 source-owned GPU submits required")
    dispatch = re.findall(r"(?:->|\.)\s*Draw(?:Indexed)?\s*\(", code)
    scoped = re.findall(r"(?:->|\.)\s*Draw(?:Indexed)?\s*\(", match.group(1))
    sm3_scoped = re.findall(r"(?:->|\.)\s*Draw(?:Indexed)?\s*\(", sm3.group(1))
    require(len(dispatch) == len(scoped) + len(sm3_scoped) == 4 and
            len(scoped) == 2 and len(sm3_scoped) == 2,
            "native Draw escapes the two admitted game source submits")
    require(all(token in sm3.group(1) for token in (
                "env_full_game_opt_in()", "game_native_backbuffer_ready(game, viewport)",
                "s.clearColor.matches(", "s.frameBatch.accepts_full_on_source_target(",
                "s.frameBatch.accepts_source_draw(", "s.preDrawFills.count != 0u",
                "GetVertexDeclaration(", "live_sm3_shader_bytes(",
                "live_sm3_input_layout(", "GetVertexShaderConstantF(",
                "GetPixelShaderConstantF(", "capture_live_sm3_sampler(",
                "mirror_texture(", "context->VSSetShader(",
                "context->PSSetShader(", "context->PSSetShaderResources(",
                "context->PSSetSamplers(", "context->DrawIndexed(",
                "context->Draw(", "s.frameBatch.succeeded(",
                "s.frameBatch.record_source_draw(sourceOrdinal)")),
            "SM3 live native draw must retain exact source/constant/resource/fallback gates")
    require("if (!submit_live_sm3_game_draw(" in code and
            "s.frameBatch.abort();" in
                code.partition("if (!submit_live_sm3_game_draw(")[2][:300],
            "rejected live SM3 draw must cancel native publication")
    # Default remains one real D3D9 game Draw. Explicit double opt-in admits
    # only eight contiguous game Draws; the full-scene cursor visits draws
    # beyond the former first-64 limit. Preserve bounds, Z and fallback.
    batch_source = (DX11.parent / "native_game_frame_batch.hpp").read_text(encoding="utf-8")
    require("const UINT candidateOrdinal = s.eligibleThisFrame++;" in code and
            "if (s.eligibleThisFrame == (std::numeric_limits<UINT>::max)()) {" in code and
            "if (fullMode) s.frameBatch.abort();" in code and
            "s.probeSlot = GameNativeFrameBatch::next_probe_slot(" in code and
            "s.probeSlot, s.eligibleThisFrame);" in code and
            "kProbeSlots = 64" not in code and
            'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"' in code and
            'GetEnvironmentVariableW(L"OUTRUN_DX11_FRAME_BATCH"' in code and
            "s.frameBatch.accepts(candidateOrdinal, s.probeSlot," in code and
            "env_batch_opt_in());" in code and
            "if (!admitted)" in code and
            "s.frameBatch.must_abort_unsupported(fullMode, multiBatch)" in code and
            "s.frameBatch.must_abort_unsupported(fullMode, env_batch_opt_in())" in code and
            'GetEnvironmentVariableW(L"OUTRUN_DX11_FULL_GAME_FRAME"' in code and
            "s.frameBatch.accepts_full_on_source_target(" in code and
            "const bool sameClearedGameTarget = s.clearColor.matches(" in code and
            "return matchesClearedBackbuffer &&" in batch_source and
            "accepts_full_seeded(ordinal, matchesClearedBackbuffer);" in batch_source and
            "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in code and
            "kMaxFullFrameDraws = 4096u" in batch_source and
            "if (s.frameBatch.first_draw()) {" in code and
            "s.backend.begin_frame(env_full_game_opt_in()" in code and
            "s.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)" in code and
            ": kBackground);" in code and
            "if (s.frameBatch.clear_depth())" in code and
            "s.frameBatch.accepts_depth(output.nativeDepthTest," in code and
            "s.frameBatch.abort();" in code and
            code.count("s.frameBatch.reset();") >= 3 and
            "static constexpr std::uint32_t kMaxDraws = 8u;" in batch_source and
            "if (!multi) return submitted == 0u && ordinal == slot;" in batch_source and
            "return submitted < kMaxDraws && ordinal >= slot &&" in batch_source and
            "ordinal - slot < kMaxDraws;" in batch_source and
            "current < eligible - 1u" in batch_source and
            "if (stopped) return false;" in batch_source and
            "return !depth || depthDirection == 0u ||" in batch_source,
            "must preserve default single Draw, double opt-in, bounded native GPU work and Z isolation")
    require("return R30PresentR29Hook.stdcall<HRESULT>(" in caller,
            "game Present must retain the D3D9 path")

def main() -> None:
    require(DX11.is_file() and R30.is_file() and ACTIVE_R30.is_file()
            and HEADER.is_file(), "diagnostic source files absent")
    code = DX11.read_text(encoding="utf-8")
    header = HEADER.read_text(encoding="utf-8")
    native = NATIVE.read_text(encoding="utf-8")
    # Both compile variants must preserve the same source/return ownership.
    validate(code, R30.read_text(encoding="utf-8"), header, native)
    active = ACTIVE_R30.read_text(encoding="utf-8")
    validate(code, active, header, native)
    require("if (IsGameDevice(device) && !InternalStereoPass)" in active,
            "default R26+HUD game callsite must exclude synthetic eye replay")
    require("OUTRUN_VR_R26_HUD_COMPARE" in
            (ROOT / "CMakeLists.txt").read_text(encoding="utf-8") and
            "stereo_renderer_r30_r26_safe.cpp" in
            (ROOT / "CMakeLists.txt").read_text(encoding="utf-8"),
            "default game DLL must compile the audited R26+HUD owner")
    print("DX11 controlled live game draw diagnostic admission: PASS (static only)")

if __name__ == "__main__":
    main()
