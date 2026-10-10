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
    require("D3DFVF_XYZRHW | D3DFVF_DIFFUSE" in code and
            "GetVertexShader(vs.GetAddressOf())" in code and
            "GetPixelShader(ps.GetAddressOf())" in code and
            "GetTexture(0, tex.GetAddressOf())" in code,
            "unsupported live D3D9 shader/texture states must be rejected")
    require("GetRenderState(D3DRS_ALPHABLENDENABLE" in code and
            "GetRenderState(D3DRS_ZENABLE" in code,
            "blended/depth state must be rejected")
    require("type != D3DPT_TRIANGLELIST" in code and
            "idx" not in "" and "indices[i] >= vertexCount" in code,
            "non-triangle or invalid indices must be rejected")
    require("s.backend.begin_frame(kBackground);" in code and
            "ctx->CopyResource(s.staging.Get(), s.backend.color_texture())" in code and
            "ctx->Map(s.staging.Get(), 0, D3D11_MAP_READ" in code and
            "changedPixels" in code and "game->UpdateSurface(" in code,
            "native frame must reach checked visible desktop output")
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
    require("s.attempted = true;" in code and "if (s.attempted) return;" in code,
            "must bound diagnostic GPU work to one call per game frame")
    require("return R30PresentR29Hook.stdcall<HRESULT>(" in caller,
            "game Present must retain the D3D9 path")

def main() -> None:
    require(DX11.is_file() and R30.is_file() and HEADER.is_file(),
            "diagnostic source files absent")
    validate(DX11.read_text(encoding="utf-8"),
             R30.read_text(encoding="utf-8"),
             HEADER.read_text(encoding="utf-8"),
             NATIVE.read_text(encoding="utf-8"))
    print("DX11 controlled live game draw diagnostic admission: PASS (static only)")

if __name__ == "__main__":
    main()
