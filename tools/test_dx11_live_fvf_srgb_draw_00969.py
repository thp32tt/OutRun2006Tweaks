#!/usr/bin/env python3
"""FVF/SM3 real game per-Draw native RTV selection; source only, not HMD proof."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
code = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/native_game_srgb_draw.hpp").read_text()
def valid(source):
    a = source.index("bool supported_game_state(")
    b = source.index("bool submit_live_sm3_game_draw(", a)
    c = source.index("bool submit(State& s,", b)
    d = source.index("void observe(", c)
    fixed, sm3, draw = source[a:b], source[b:c], source[c:d]
    state = fixed.index("GetRenderState(D3DRS_SRGBWRITEENABLE, &srgbWrite)")
    admit = fixed.index("GameNativeSrgbDraw::admit(srgbWrite, fullFrame)")
    select = fixed.index("output.nativeSrgbWrite = GameNativeSrgbDraw::uses_srgb(srgbWrite)")
    sampler = fixed.index("if (capture.enabled) {", select)
    if not state < admit < select < sampler or "srgbWrite != FALSE" in fixed:
        return False
    if fixed.count("GetRenderState(D3DRS_SRGBWRITEENABLE, &srgbWrite)") != 1:
        return False
    required = ("output.nativeSrgbWrite && !s.backend.color_rtv_srgb()",
        "ID3D11RenderTargetView* gameRtv = output.nativeSrgbWrite",
        "? s.backend.color_rtv_srgb() : s.backend.color_rtv()",
        "ctx->OMSetRenderTargets(1u, &gameRtv,",
        "output.nativeDepthTest ? s.diagnosticDepthView.Get() : nullptr")
    if any(t not in draw for t in required):
        return False
    if "ctx->Draw(" not in draw or draw.index("ctx->OMSetRenderTargets(1u, &gameRtv,") > draw.index("ctx->Draw("):
        return False
    # The programmable live path already uses the same paired render target.
    return all(t in sm3 for t in (
        "srgbWrite == TRUE", "s.backend.color_rtv_srgb() : s.backend.color_rtv()",
        "context->OMSetRenderTargets(", "context->DrawIndexed(")) and (
        "fullFrame && gameWriteState == 1u" in header)
assert valid(code), "missing native per-draw fixed sRGB output or fallback"
bad = code.replace("GameNativeSrgbDraw::admit(srgbWrite, fullFrame)",
    "GameNativeSrgbDraw::admit(srgbWrite, true)", 1)
assert bad != code and not valid(bad), "inset fallback negative control"
bad = code.replace("ID3D11RenderTargetView* gameRtv = output.nativeSrgbWrite",
    "ID3D11RenderTargetView* gameRtv = false", 1)
assert bad != code and not valid(bad), "RTV source-state negative control"
print("DX11 live FVF/SM3 sRGB RT0 and D3D9 fallback integration PASS")
