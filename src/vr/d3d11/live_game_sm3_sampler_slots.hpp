#pragma once
// Map SM3 shader s-registers to the two *different* D3D9 texture namespaces.
// D3DVERTEXTEXTURESAMPLER0 is 256; VS has four slots, PS has sixteen.
// The native D3D11 stages both start at t0/s0; never bind a pixel texture
// when the original game requested an independent vertex-stage texture.
namespace outrun::vr::dx11::live_game_frame {
inline constexpr unsigned kGameSm3InvalidSamplerSlot = ~0u;
[[nodiscard]] constexpr unsigned game_sm3_sampler_source_slot(
    bool vertexStage, unsigned shaderRegister) noexcept {
    return vertexStage
        ? (shaderRegister < 4u ? 256u + shaderRegister
                                : kGameSm3InvalidSamplerSlot)
        : (shaderRegister < 16u ? shaderRegister
                                 : kGameSm3InvalidSamplerSlot);
}
} // namespace outrun::vr::dx11::live_game_frame
