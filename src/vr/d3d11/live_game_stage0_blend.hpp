#pragma once

#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {

// D3D9 D3DTEXTUREOP values; the live bridge checks against SDK enums.
// On texture stage 0 only, CURRENT is vertex DIFFUSE before stage evaluation.
// Never equate CURRENT and DIFFUSE at any subsequent texture stage.
constexpr std::uint32_t kGameStage0BlendDiffuseAlpha = 12u;
constexpr std::uint32_t kGameStage0BlendCurrentAlpha = 16u;
constexpr std::uint32_t kGameStage0BlendTextureAlphaPM = 15u;
constexpr bool game_stage0_premultiplied_pair(std::uint32_t colorOp,
                                              std::uint32_t alphaOp) noexcept {
    return colorOp == kGameStage0BlendTextureAlphaPM &&
           alphaOp == kGameStage0BlendTextureAlphaPM;
}

// PM color with an independent stage0 SELECTARG2 alpha: do not borrow PM alpha.
constexpr bool game_stage0_premultiplied_diffuse_alpha_pair(
    std::uint32_t colorOp, std::uint32_t alphaOp) noexcept {
    return colorOp == kGameStage0BlendTextureAlphaPM && alphaOp == 3u; // D3DTOP_SELECTARG2
}

constexpr std::uint32_t canonical_game_stage0_blend_alpha_op(
    std::uint32_t op, bool currentIsVertexDiffuse) noexcept {
    return currentIsVertexDiffuse && op == kGameStage0BlendCurrentAlpha
        ? kGameStage0BlendDiffuseAlpha : op;
}

// Preserve the original CURRENT-weighted alpha operation when PM RGB requires
// its own shader (TEXTURE/TFACTOR versus TEXTURE/DIFFUSE). Canonicalizing this
// alpha op first made both live native PM variants unreachable. All non-PM
// stage0 color operations retain the established CURRENT->DIFFUSE mapping.
constexpr std::uint32_t canonical_game_stage0_pm_alpha_op(
    std::uint32_t colorOp, std::uint32_t alphaOp,
    bool currentIsVertexDiffuse) noexcept {
    return currentIsVertexDiffuse &&
           colorOp == kGameStage0BlendTextureAlphaPM &&
           alphaOp == kGameStage0BlendCurrentAlpha
        ? alphaOp
        : canonical_game_stage0_blend_alpha_op(alphaOp, currentIsVertexDiffuse);
}

static_assert(canonical_game_stage0_pm_alpha_op(
    kGameStage0BlendTextureAlphaPM, kGameStage0BlendCurrentAlpha, true) ==
    kGameStage0BlendCurrentAlpha);
static_assert(canonical_game_stage0_pm_alpha_op(
    kGameStage0BlendDiffuseAlpha, kGameStage0BlendCurrentAlpha, true) ==
    kGameStage0BlendDiffuseAlpha);
static_assert(canonical_game_stage0_pm_alpha_op(
    kGameStage0BlendTextureAlphaPM, kGameStage0BlendCurrentAlpha, false) ==
    kGameStage0BlendCurrentAlpha);


} // namespace outrun::vr::dx11::live_game_frame
