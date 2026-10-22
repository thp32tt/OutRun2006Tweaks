#!/usr/bin/env python3
"""Verify actual D3D9 game Draw blend-factor -> D3D11 OM linkage (source-only).

Windows compilation/real GPU readback belongs to exact-SHA backend/Build CI;
this fast guard does not claim pixels, native game frames or Quest3 results.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()

def require(fragment, source=src):
    assert fragment in source, f"Missing live game blend-factor contract: {fragment}"

# Both D3D9 color and separately enabled alpha factors use the same dynamic
# per-Draw ARGB state. Cached BlendState contains *only* immutable equations.
require("case D3DBLEND_BLENDFACTOR: out = D3D11_BLEND_BLEND_FACTOR;")
require("case D3DBLEND_INVBLENDFACTOR: out = D3D11_BLEND_INV_BLEND_FACTOR;")
require("f != D3DBLEND_INVDESTALPHA &&\n        !sm3_live_uses_blend_factor(f)")
require("sm3_live_blend_key(b)")
require("sm3_live_blend_factor_rgba(DWORD argb)")
require("(argb >> 16u) & 0xffu")  # R
require("(argb >>  8u) & 0xffu")  # G
require("argb         & 0xffu")  # B
require("(argb >> 24u) & 0xffu")  # A
require("sm3_live_masked_blend_regression()")
require("sm3_live_blend_regression()")
require("sm3_live_blend_desc(0xdeadbeefu, D3DBLEND_ONE")
require("b.SrcBlendAlpha != D3D11_BLEND_BLEND_FACTOR")
require("b.DestBlendAlpha != D3D11_BLEND_INV_BLEND_FACTOR")
require("0xdeadbeefu")            # Unknown factors still fail-closed

# The shader-bound game's D3D9 state is captured for each Draw, not sourced
# from a WARP fixture, cached initial value, or fabricated blend constant.
game = src[src.index("bool submit_live_sm3_game_draw("):
           src.index("// A successful R9 RT0 switch")]
require("const bool usesBlendFactor = blend != FALSE", game)
require("sm3_live_uses_blend_factor(srcBlendAlpha)", game)
require("sm3_live_uses_blend_factor(dstBlendAlpha)", game)
require("FAILED(game->GetRenderState(D3DRS_BLENDFACTOR, &gameBlendFactor))", game)
require("const auto nativeBlendFactor = sm3_live_blend_factor_rgba(gameBlendFactor);", game)
require("usesBlendFactor ? nativeBlendFactor.data() : nullptr", game)
require("context->OMSetBlendState(liveBlend,", game)
require("context->DrawIndexed(nativeIndexCount, 0u, static_cast<INT>(base))", game)
require("context->Draw(vertexCount, base);", game)
require("s.frameBatch.abort();", src)
require("return false;", game)
# A real game shader-bound Draw may use SRCALPHASAT RGB or D3D9 BOTH*
# source factors. Validate the native OM normalization, semantic compile-time
# tests and rejection of unsupported destination/independent-alpha saturation.
factor = src.split("constexpr bool sm3_live_factor(", 1)[1].split(
    "constexpr bool sm3_live_blend_op(", 1)[0]
desc = src.split("constexpr bool sm3_live_blend_desc(", 1)[1].split(
    "constexpr bool sm3_live_legacy_source_blend_regression()", 1)[0]
for token in (
    "case D3DBLEND_SRCALPHASAT:",
    "D3D11_BLEND_SRC_ALPHA_SAT",
    "alpha ? D3D11_BLEND_ONE",
    "if (independent) return false;",
):
    require(token, factor)
for token in (
    "sc == D3DBLEND_BOTHSRCALPHA",
    "sc == D3DBLEND_BOTHINVSRCALPHA",
    "bothSrc ? D3DBLEND_INVSRCALPHA",
    "bothInvSrc ? D3DBLEND_SRCALPHA",
    "dc == D3DBLEND_SRCALPHASAT",
    "da == D3DBLEND_SRCALPHASAT",
    "sm3_live_factor(rgbSrc, false",
    "sm3_live_factor(rgbDst, false",
):
    require(token, desc)
require("static_assert(sm3_live_legacy_source_blend_regression()", src)
require("D3DBLEND_BOTHINVSRCALPHA, D3DBLEND_ZERO, D3DBLENDOP_ADD", src)
require("b.BlendOpAlpha != D3D11_BLEND_OP_MAX", src)
require("sm3_live_blend_key(b) == sm3_live_blend_key(saved)", src)
print("PASS source: actual shader-bound Draw blend factor/alpha/native OM/fail-closed; runtime UNTESTED")
