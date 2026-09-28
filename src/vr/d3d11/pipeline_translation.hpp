#pragma once

#include <cstdint>
#include <d3d11.h>

#include "vr/core/d3d9_draw_state.hpp"

namespace outrun::vr::dx11
{
    enum PipelineUnsupported : std::uint32_t
    {
        PipelineUnsupportedNone = 0,
        PipelineUnsupportedIncompleteSnapshot = 1u << 0,
        PipelineUnsupportedWBuffer = 1u << 1,
        PipelineUnsupportedSeparateAlphaBlend = 1u << 2,
        PipelineUnsupportedAlphaTest = 1u << 3,
        PipelineUnsupportedStencil = 1u << 4,
        PipelineUnsupportedFog = 1u << 5,
        PipelineUnsupportedLighting = 1u << 6,
        PipelineUnsupportedSrgbWrite = 1u << 7,
        PipelineUnsupportedFillMode = 1u << 8,
        PipelineUnsupportedBlend = 1u << 9,
        PipelineUnsupportedDepthCompare = 1u << 10,
        PipelineUnsupportedCull = 1u << 11,
    };

    struct PipelineTranslation
    {
        D3D11_BLEND_DESC blend{};
        D3D11_DEPTH_STENCIL_DESC depth_stencil{};
        D3D11_RASTERIZER_DESC rasterizer{};
        std::uint32_t unsupported = PipelineUnsupportedNone;

        [[nodiscard]] bool exact() const noexcept
        {
            return unsupported == PipelineUnsupportedNone;
        }
    };

    [[nodiscard]] PipelineTranslation translate_pipeline(
        const OutRunVR::DrawState::RenderStateSnapshot& source) noexcept;
}
