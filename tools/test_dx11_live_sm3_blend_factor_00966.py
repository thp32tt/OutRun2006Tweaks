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

# D3D9 independent-alpha SRCCOLOR/DESTCOLOR is a legal one-component
# game state in BOTH programmable and fixed-function Draw/DrawIndexed.
# An otherwise valid mixed source frame must not be poisoned by the FVF
# branch while the SM3 branch already handles these exact aliases.
fvf_alpha = src.split("constexpr bool native_game_alpha_factor(", 1)[1].split(
    "constexpr bool native_game_separate_alpha(", 1)[0]
for alias in ("SRCCOLOR", "INVSRCCOLOR", "DESTCOLOR", "INVDESTCOLOR"):
    require(f"case D3DBLEND_{alias}:", fvf_alpha)
require("D3DBLEND_SRCCOLOR, D3DBLEND_INVDESTCOLOR,", src)
require("D3DBLEND_INVSRCCOLOR, D3DBLEND_DESTCOLOR,", src)
require("src != D3D11_BLEND_SRC_ALPHA", src)
require("dst != D3D11_BLEND_INV_DEST_ALPHA", src)
require("D3DBLEND_SRCALPHASAT, D3DBLEND_ONE,", src)
require("D3DBLEND_BLENDFACTOR, D3DBLEND_ONE,", src)

# The shader-bound game's D3D9 state is captured for each Draw, not sourced
# from a WARP fixture, cached initial value, or fabricated blend constant.
game = src[src.index("bool submit_live_sm3_game_draw("):
           src.index("// A successful R9 RT0 switch")]
require("const bool usesBlendFactor = live_sm3_needs_dynamic_blend_factor(", game)
portable = (root / "src/vr/d3d11/live_game_sm3_composite.hpp").read_text()
require("live_sm3_effective_dest_factor(", portable)
require("!live_sm3_needs_dynamic_blend_factor(", portable)
require("true, 12u, 14u, true, 14u, 2u", portable)

# RT0-write mask governs which original blend factors reach the GPU.
# The other component's stale state must not veto the game Draw, while a
# malformed equation for any written component still fails closed.
require("srcBlendAlpha, dstBlendAlpha, colorMask);", game)
require("const bool writesRgb = (writeMask & 0x07u) != 0u;", src)
require("const bool writesAlpha = (writeMask & 0x08u) != 0u;", src)
require("const bool consumesRgbFactors = writesRgb || (writesAlpha && !separate);", src)
require("separate && writesAlpha, sa, da, oa, b)", src)
require("if (enabled && writeMask != 0u)", src)
require("(colorWriteMask & 0x07u)", portable)
require("(colorWriteMask & 0x08u)", portable)
require("separateAlpha", portable)
require("colorWriteMask = 0x0fu", portable)
require("sm3_live_masked_blend_desc(\n            true, 0x07u", src)
require("sm3_live_masked_blend_desc(\n            true, 0x08u", src)
require("sm3_live_masked_blend_desc(\n            true, 0x00u", src)
require("sm3_live_masked_blend_desc(\n            true, 0x0fu", src)
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
require("const DWORD rgbDst = live_sm3_effective_dest_factor(sc, dc);", desc)
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
    "dc == D3DBLEND_SRCALPHASAT",
    "da == D3DBLEND_SRCALPHASAT",
    "sm3_live_factor(rgbSrc, false",
    "sm3_live_factor(rgbDst, false",
):
    require(token, desc)
# Independent-alpha COLOR factors are legal game states: the alpha
# channel of SRCCOLOR/DESTCOLOR maps to D3D11 SRC_ALPHA/DEST_ALPHA.
# Rejecting the valid aliases would poison an otherwise eligible menu Draw.
require("f != D3DBLEND_SRCCOLOR && f != D3DBLEND_INVSRCCOLOR", factor)
require("f != D3DBLEND_DESTCOLOR && f != D3DBLEND_INVDESTCOLOR", factor)
require("static_assert(sm3_live_independent_alpha_color_alias_regression()", src)
require("true, 0x08u, 0xdeadbeefu, 0xdeadbeefu, 0xdeadbeefu", src)
require("true, D3DBLEND_SRCCOLOR, D3DBLEND_INVDESTCOLOR", src)
require("true, D3DBLEND_DESTCOLOR, D3DBLEND_INVSRCCOLOR", src)
require("D3DBLEND_SRCALPHASAT,", src)
require("static_assert(sm3_live_legacy_source_blend_regression()", src)
require("D3DBLEND_BOTHINVSRCALPHA, D3DBLEND_ZERO, D3DBLENDOP_ADD", src)
require("b.BlendOpAlpha != D3D11_BLEND_OP_MAX", src)
require("b.BlendOpAlpha == saved.BlendOpAlpha", src)
print("PASS source: actual shader-bound Draw blend factor/alpha/native OM/fail-closed; runtime UNTESTED")
