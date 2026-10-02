#include "fixed_function_pipeline.hpp"

namespace outrun::vr::dx11
{
    FixedFunctionPipelineShaderTranslation
    translate_fixed_function_pipeline_with_shader_semantics(
        const OutRunVR::DrawState::RenderStateSnapshot& source,
        bool fixedFunctionObserved,
        const std::array<FixedFunctionStageState, 8>& stages,
        bool fixedFunctionStateObservationComplete,
        std::uint8_t textureResourcePresentMask,
        std::uint8_t textureResourceExactMask,
        const std::array<D3DRESOURCETYPE, 8>& textureResourceTypes)
    {
        FixedFunctionPipelineShaderTranslation out{};
        out.renderStates = translate_pipeline(source);
        out.fixedFunctionObserved = fixedFunctionObserved;

        // A failed or ambiguous VS/PS observation must never inherit the
        // fixed-function shader-owned semantics below.
        if (!fixedFunctionObserved)
            return out;

        out.pixelShader = generate_fixed_function_pixel_shader_prototype(
            stages,
            fixedFunctionStateObservationComplete,
            textureResourcePresentMask,
            textureResourceExactMask,
            textureResourceTypes,
            FixedFunctionAlphaTestState{
                source.complete,
                source.alphaTestEnable,
                source.alphaRef,
                source.alphaFunc
            },
            source.textureFactor);

        if (!out.pixelShader.generated())
            return out;

        // translate_pipeline() remains conservative for every caller. Only
        // the fixed-function path that just generated a pixel shader from the
        // same complete D3D9 snapshot may move alpha testing from the render
        // state blocker set into shader ownership.
        if (source.complete &&
            source.alphaTestEnable != FALSE &&
            out.alpha_test_transfer_allowed() &&
            (out.renderStates.unsupported & PipelineUnsupportedAlphaTest) != 0)
        {
            out.renderStates.unsupported &= ~PipelineUnsupportedAlphaTest;
            out.alphaTestOwnedByPixelShader = true;
        }

        return out;
    }
}
