#!/usr/bin/env python3
"""CONVERSION-DX11-00967: real SM3 source Draw -> sRGB native RTV integration.

This is a source integration guard; exact-SHA Windows compilation and native
WARP/game pixel tests are separate mandatory validation layers.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
header = (root / "src/vr/d3d11/native_backend.hpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()

def require(source: str, text: str) -> None:
    assert text in source, f"Missing native SM3 sRGB source contract: {text}"

# Both view formats must address the same typeless BGRA render surface.
for token in (
    "DXGI_FORMAT_B8G8R8A8_TYPELESS",
    "DXGI_FORMAT_B8G8R8A8_UNORM_SRGB",
    "D3D11_RTV_DIMENSION_TEXTURE2D",
    "D3D11_SRV_DIMENSION_TEXTURE2D",
    "candidateSrgbRtv.GetAddressOf()",
    "color_rtv_srgb_ = std::move(candidateSrgbRtv)",
):
    require(backend, token)
require(backend, "if (pairedSrgb && format != DXGI_FORMAT_B8G8R8A8_UNORM)")
require(backend, "pairedSrgb ? &linearView : nullptr")
require(backend, "pairedSrgb ? &shaderView : nullptr")
require(header, "(!config_.enable_srgb_write || color_rtv_srgb_)")
require(header, "bool enable_srgb_write = false;")
require(bridge, "cfg.enable_srgb_write = env_full_game_opt_in();")
require(bridge, "GetRenderState(D3DRS_SRGBWRITEENABLE, &srgbWrite)")
require(bridge, "if (srgbWrite != FALSE && srgbWrite != TRUE)")
require(bridge, "srgbWrite == TRUE\n        ? s.backend.color_rtv_srgb() : s.backend.color_rtv()")
require(bridge, "if (!rtv) return false;")
assert "exact sRGB output not translated" not in bridge
assert backend.index("candidateSrgbRtv.GetAddressOf()") < backend.index(
    "color_rtv_ = std::move(candidateRtv)")
print("PASS: SM3 per-draw linear/sRGB RTV, transaction, fallback contracts")
