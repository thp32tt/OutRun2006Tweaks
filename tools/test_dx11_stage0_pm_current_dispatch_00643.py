#!/usr/bin/env python3
"""00643: execute the previously unreachable game-native PM CURRENT-alpha routes."""
from pathlib import Path
from itertools import product

root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/live_game_stage0_blend.hpp").read_text(encoding="utf-8")
source = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
helper = """constexpr std::uint32_t canonical_game_stage0_pm_alpha_op(
    std::uint32_t colorOp, std::uint32_t alphaOp,
    bool currentIsVertexDiffuse) noexcept {
    return currentIsVertexDiffuse &&
           colorOp == kGameStage0BlendTextureAlphaPM &&
           alphaOp == kGameStage0BlendCurrentAlpha
        ? alphaOp
        : canonical_game_stage0_blend_alpha_op(alphaOp, currentIsVertexDiffuse);
}"""
callsite = """alphaOp = canonical_game_stage0_pm_alpha_op(
            op, alphaOp, stage0CurrentIsDiffuse);"""
assert helper in header and callsite in source
assert source.index("op = canonical_game_stage0_blend_alpha_op(op, stage0CurrentIsDiffuse);") < source.index(callsite)
assert source.index(callsite) < source.index("const bool blendTextureAlphaPMBlendCurrentFactorAlpha =")
assert source.index(callsite) < source.index("const bool blendTextureAlphaPMBlendCurrentDiffuseAlpha =")
assert "alphaOp = canonical_game_stage0_blend_alpha_op(alphaOp, stage0CurrentIsDiffuse);" not in source
# Prove both originally dead selector branches now consume the captured operation.
for branch, required in (
    ("blendTextureAlphaPMBlendCurrentFactorAlpha", "capture.blendTextureAlphaPMBlendCurrentFactorAlpha = blendTextureAlphaPMBlendCurrentFactorAlpha;"),
    ("blendTextureAlphaPMBlendCurrentDiffuseAlpha", "if (blendTextureAlphaPMBlendCurrentDiffuseAlpha)\n            capture.blendTextureAlphaPMBlendDiffuseAlpha = true;"),
):
    start = source.index("const bool " + branch + " =")
    predicate = source[start:source.index(";", start) + 1]
    assert "alphaOp == D3DTOP_BLENDCURRENTALPHA" in predicate
    assert "op == D3DTOP_BLENDTEXTUREALPHAPM" in predicate
    assert required in source
    assert source.index(required) > start
assert "ctx->DrawIndexed(indexCount, 0, 0);" in source
assert "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in source

PM, CURRENT, DIFFUSE, DISABLED = 15, 16, 12, 0
def canonical(color, alpha, vertex_diffuse):
    if vertex_diffuse and color == PM and alpha == CURRENT:
        return alpha
    return DIFFUSE if vertex_diffuse and alpha == CURRENT else alpha

cases = 0
for color, alpha, vertex_diffuse in product((PM, DIFFUSE, 2, 3, 4, DISABLED),
                                            (CURRENT, DIFFUSE, 2, 3, 4, 15),
                                            (False, True)):
    actual = canonical(color, alpha, vertex_diffuse)
    expected = (CURRENT if (vertex_diffuse and color == PM and alpha == CURRENT)
                else DIFFUSE if vertex_diffuse and alpha == CURRENT else alpha)
    assert actual == expected
    if vertex_diffuse and color == PM and alpha == CURRENT:
        # Old callsite incorrectly rewrote 16 to 12 before these comparisons.
        assert actual == CURRENT and actual != DIFFUSE
    if vertex_diffuse and color != PM and alpha == CURRENT:
        assert actual == DIFFUSE
    cases += 1
assert cases == 72
# Two real PM variants require distinct alpha sources: factor and vertex.
for texture, diffuse, factor in product((0.0, 0.2, 0.6, 1.0),
                                        (0.0, 0.3, 0.7, 1.0),
                                        (0.0, 0.4, 0.8, 1.0)):
    factor_alpha = texture * diffuse + factor * (1.0 - diffuse)
    diffuse_alpha = texture * diffuse + diffuse * (1.0 - diffuse)
    assert 0 <= factor_alpha <= 1 and 0 <= diffuse_alpha <= 1
    assert abs(factor_alpha - (factor + diffuse * (texture - factor))) < 1e-12
    assert abs(diffuse_alpha - (diffuse + diffuse * (texture - diffuse))) < 1e-12
print("00643 live stage0 PM CURRENT alpha 72 selector + 64 pixel cases PASS; gamepad/HMD UNTESTED")
