#pragma once

#include <array>
#include <cstdint>
#include <d3d9.h>
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

    // R82 models a deliberately conservative subset of D3D9 fixed-function
    // texture/sampler state that a future native shader generator may consume.
    // This is readiness classification only; it does not emit shaders and must
    // not be treated as native-draw activation proof.
    enum FixedFunctionUnsupported : std::uint32_t
    {
        FixedFunctionUnsupportedNone = 0,
        FixedFunctionUnsupportedIncompleteObservation = 1u << 0,
        FixedFunctionUnsupportedStageChain = 1u << 1,
        FixedFunctionUnsupportedResourceStageCoverage = 1u << 2,
        FixedFunctionUnsupportedColorOp = 1u << 3,
        FixedFunctionUnsupportedAlphaOp = 1u << 4,
        FixedFunctionUnsupportedArgument = 1u << 5,
        FixedFunctionUnsupportedTexCoord = 1u << 6,
        FixedFunctionUnsupportedTextureTransform = 1u << 7,
        FixedFunctionUnsupportedSamplerFilter = 1u << 8,
        FixedFunctionUnsupportedSamplerAddress = 1u << 9,
    };

    struct FixedFunctionStageState
    {
        DWORD colorOp = D3DTOP_DISABLE;
        DWORD colorArg1 = D3DTA_TEXTURE;
        DWORD colorArg2 = D3DTA_CURRENT;
        DWORD alphaOp = D3DTOP_DISABLE;
        DWORD alphaArg1 = D3DTA_TEXTURE;
        DWORD alphaArg2 = D3DTA_CURRENT;
        DWORD texCoordIndex = 0;
        DWORD textureTransformFlags = D3DTTFF_DISABLE;
        DWORD minFilter = D3DTEXF_NONE;
        DWORD magFilter = D3DTEXF_NONE;
        DWORD mipFilter = D3DTEXF_NONE;
        DWORD addressU = D3DTADDRESS_WRAP;
        DWORD addressV = D3DTADDRESS_WRAP;
    };

    struct FixedFunctionTranslationReadiness
    {
        std::uint32_t unsupported = FixedFunctionUnsupportedNone;
        UINT activeStages = 0;

        [[nodiscard]] bool exact() const noexcept
        {
            return unsupported == FixedFunctionUnsupportedNone;
        }
    };

    [[nodiscard]] FixedFunctionTranslationReadiness
    translate_fixed_function_readiness(
        const std::array<FixedFunctionStageState, 8>& source,
        bool observationComplete) noexcept;

    // R79 translates either an explicit D3D9 declaration or a conservative
    // supported FVF subset into canonical D3D11 input-layout descriptors.
    // FVF blend-weight/index encodings and any unmodelled flag combination
    // remain fail-closed. Programmable shader-signature compatibility remains
    // an independent F21 gate; exact means descriptor-level readiness only.
    struct VertexInputLayoutTranslation
    {
        std::array<D3D11_INPUT_ELEMENT_DESC, MAXD3DDECLLENGTH> elements{};
        UINT elementCount = 0;
        bool exact = false;
        bool declarationPath = false;
        bool fvfPath = false;
        bool fvfPending = false;
    };

    [[nodiscard]] VertexInputLayoutTranslation translate_vertex_input_layout(
        const D3DVERTEXELEMENT9* source,
        UINT count,
        DWORD fvf,
        UINT stream0Stride) noexcept;
}
