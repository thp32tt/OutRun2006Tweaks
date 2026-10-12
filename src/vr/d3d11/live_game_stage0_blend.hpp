#pragma once

#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {

// D3D9 D3DTEXTUREOP values; the live bridge checks against SDK enums.
// On texture stage 0 only, CURRENT is vertex DIFFUSE before stage evaluation.
// Never equate CURRENT and DIFFUSE at any subsequent texture stage.
constexpr std::uint32_t kGameStage0BlendDiffuseAlpha = 12u;
constexpr std::uint32_t kGameStage0BlendCurrentAlpha = 16u;

constexpr std::uint32_t canonical_game_stage0_blend_alpha_op(
    std::uint32_t op, bool currentIsVertexDiffuse) noexcept {
    return currentIsVertexDiffuse && op == kGameStage0BlendCurrentAlpha
        ? kGameStage0BlendDiffuseAlpha : op;
}

} // namespace outrun::vr::dx11::live_game_frame
