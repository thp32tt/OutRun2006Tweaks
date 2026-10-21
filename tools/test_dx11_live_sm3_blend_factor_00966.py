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
require("if (nativeIndices) context->DrawIndexed", game)
require("else context->Draw(vertexCount, 0u);", game)
require("s.frameBatch.abort();", src)
require("return false;", game)
print("PASS source: actual shader-bound Draw blend factor/alpha/native OM/fail-closed; runtime UNTESTED")
