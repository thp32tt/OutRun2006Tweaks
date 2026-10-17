#pragma once

#include <array>
#include <cstdint>

#include "pipeline_translation.hpp"

namespace outrun::vr::dx11
{
    // R118 bridges one shader-owned D3D9 fixed-function semantic into the
    // otherwise render-state-only PipelineTranslation contract. The generic
    // translator intentionally keeps alpha test unsupported because a
    // programmable D3D9 pixel shader still needs a separate alpha-test
    // emulation path. This fixed-function wrapper may discharge only that
    // single blocker, and only after it has generated the exact R84 pixel
    // shader prototype from the same observed alpha-test state.
    //
    // This is dormant readiness evidence. It does not bind D3D11 state and it
    // does not route a game Draw* call to the native backend.
    struct FixedFunctionPipelineShaderTranslation
    {
        PipelineTranslation renderStates{};
        FixedFunctionPixelShaderPrototype pixelShader{};
        bool fixedFunctionObserved = false;
        bool alphaTestOwnedByPixelShader = false;

        [[nodiscard]] bool alpha_test_transfer_allowed() const noexcept
        {
            return fixedFunctionObserved && pixelShader.generated();
        }

        [[nodiscard]] bool alpha_test_transferred() const noexcept
        {
            return alphaTestOwnedByPixelShader && pixelShader.generated();
        }

        [[nodiscard]] bool exact() const noexcept
        {
            return fixedFunctionObserved &&
                renderStates.exact() &&
                pixelShader.generated();
        }
    };

    [[nodiscard]] FixedFunctionPipelineShaderTranslation
    translate_fixed_function_pipeline_with_shader_semantics(
        const OutRunVR::DrawState::RenderStateSnapshot& source,
        bool fixedFunctionObserved,
        const std::array<FixedFunctionStageState, 8>& stages,
        bool fixedFunctionStateObservationComplete,
        std::uint8_t textureResourcePresentMask,
        std::uint8_t textureResourceExactMask,
        const std::array<D3DRESOURCETYPE, 8>& textureResourceTypes);
}
