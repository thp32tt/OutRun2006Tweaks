#!/usr/bin/env python3
"""Constrained activation review for the FIRST_GAME_DRAW_FRAME diagnostic.

This is an admission check, NOT evidence that a game/HMD frame was drawn.
Only a small live-game FVF path is admitted; any other D3D11 Draw* still fails
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
            "capture.enabled = layout.textured;" in code and
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
            "primitiveCount == 0u || primitiveCount > 512u" in span and
            "required > 1536u" in span and
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
    require("s.backend.begin_frame(kBackground);" in code and
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
    require("void before_game_reset()" in code and "s.backend.shutdown();" in code,
            "reset must invalidate native device owner")
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
    require("before_game_reset();" in caller and "before_game_present(device);" in caller,
            "Present and reset must be tied to the game's real R30 hooks")
    require("bool initialize(const NativeBackendConfig& config)" in native and
            "ID3D11RenderTargetView* color_rtv()" in native,
            "native device and render target ownership missing")
    # Explicit native Draw dispatch permitted only inside the submit body.
    # Unrelated code must never obtain implicit native promotion.
    match = re.search(r"bool submit\s*\(.*?\) noexcept \{(.*?)\n\}\n\nvoid observe\(", code, re.S)
    require(match is not None, "isolated submit function missing")
    dispatch = re.findall(r"(?:->|\.)\s*Draw(?:Indexed)?\s*\(", code)
    scoped = re.findall(r"(?:->|\.)\s*Draw(?:Indexed)?\s*\(", match.group(1))
    require(len(dispatch) == len(scoped) == 2,
            "native Draw escapes the explicitly admitted diagnostic submit")
    # Default remains one real D3D9 game Draw. Explicit double opt-in admits
    # only eight contiguous game Draws; the full-scene cursor visits draws
    # beyond the former first-64 limit. Preserve bounds, Z and fallback.
    batch_source = (DX11.parent / "native_game_frame_batch.hpp").read_text(encoding="utf-8")
    require("const UINT candidateOrdinal = s.eligibleThisFrame++;" in code and
            "if (s.eligibleThisFrame == (std::numeric_limits<UINT>::max)()) return;" in code and
            "s.probeSlot = GameNativeFrameBatch::next_probe_slot(" in code and
            "s.probeSlot, s.eligibleThisFrame);" in code and
            "kProbeSlots = 64" not in code and
            'GetEnvironmentVariableW(L"OUTRUN_DX11_FIRST_GAME_FRAME"' in code and
            'GetEnvironmentVariableW(L"OUTRUN_DX11_FRAME_BATCH"' in code and
            "s.frameBatch.accepts(candidateOrdinal, s.probeSlot," in code and
            "env_batch_opt_in())) return;" in code and
            "if (s.frameBatch.first_draw()) s.backend.begin_frame(kBackground);" in code and
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
