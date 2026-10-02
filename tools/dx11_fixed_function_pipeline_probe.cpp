#include <array>
#include <cstdlib>
#include <iostream>
#include <string>

#include "vr/d3d11/fixed_function_pipeline.hpp"

namespace
{
    using namespace outrun::vr::dx11;

    [[noreturn]] void fail(const char* message)
    {
        std::cerr << "DX11 R118 fixed-function pipeline smoke failure: "
                  << message << '\n';
        std::exit(1);
    }

    void require(bool condition, const char* message)
    {
        if (!condition)
            fail(message);
    }

    OutRunVR::DrawState::RenderStateSnapshot base_state()
    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        return state;
    }
}

int main()
{
    std::array<FixedFunctionStageState, 8> stages{};
    std::array<D3DRESOURCETYPE, 8> textureTypes{};
    textureTypes.fill(D3DRTYPE_TEXTURE);

    {
        auto state = base_state();
        state.alphaTestEnable = TRUE;
        state.alphaRef = 128;
        state.alphaFunc = D3DCMP_GREATEREQUAL;

        const auto raw = translate_pipeline(state);
        require(
            (raw.unsupported & PipelineUnsupportedAlphaTest) != 0,
            "generic pipeline translator must keep alpha test fail-closed");

        const auto fixed = translate_fixed_function_pipeline_with_shader_semantics(
            state, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            fixed.fixedFunctionObserved &&
            fixed.alphaTestOwnedByPixelShader &&
            fixed.pixelShader.generated() &&
            fixed.renderStates.unsupported == PipelineUnsupportedNone &&
            fixed.exact(),
            "exact fixed-function alpha test was not transferred to shader ownership");
        require(
            fixed.pixelShader.source.find(
                "if (!(current.a >= alphaRef)) discard;") != std::string::npos,
            "fixed-function alpha-test shader semantic drift");

        const auto compile =
            compile_fixed_function_pixel_shader_prototype(fixed.pixelShader);
        require(
            compile.attempted && compile.succeeded &&
            compile.result == S_OK && compile.bytecodeBytes != 0,
            "shader-owned alpha-test prototype did not compile");
    }

    {
        auto state = base_state();
        state.alphaTestEnable = TRUE;
        state.alphaRef = 64;
        state.alphaFunc = D3DCMP_GREATER;

        const auto programmable =
            translate_fixed_function_pipeline_with_shader_semantics(
                state, false, stages, true, 0x00, 0x00, textureTypes);
        require(
            !programmable.fixedFunctionObserved &&
            !programmable.alphaTestOwnedByPixelShader &&
            !programmable.pixelShader.generated() &&
            (programmable.renderStates.unsupported &
             PipelineUnsupportedAlphaTest) != 0 &&
            !programmable.exact(),
            "non-fixed-function draw incorrectly discharged alpha-test blocker");
    }

    {
        auto state = base_state();
        state.alphaTestEnable = TRUE;
        state.alphaRef = 32;
        state.alphaFunc = D3DCMP_LESS;

        const auto incompleteStages =
            translate_fixed_function_pipeline_with_shader_semantics(
                state, true, stages, false, 0x00, 0x00, textureTypes);
        require(
            !incompleteStages.pixelShader.generated() &&
            !incompleteStages.alphaTestOwnedByPixelShader &&
            (incompleteStages.renderStates.unsupported &
             PipelineUnsupportedAlphaTest) != 0,
            "incomplete fixed-function observation discharged alpha-test blocker");

        state.alphaFunc = 0xFFFFFFFFu;
        const auto invalidCompare =
            translate_fixed_function_pipeline_with_shader_semantics(
                state, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            !invalidCompare.pixelShader.generated() &&
            !invalidCompare.alphaTestOwnedByPixelShader &&
            (invalidCompare.renderStates.unsupported &
             PipelineUnsupportedAlphaTest) != 0,
            "unsupported alpha compare discharged alpha-test blocker");
    }

    {
        auto state = base_state();
        state.alphaTestEnable = TRUE;
        state.alphaRef = 100;
        state.alphaFunc = D3DCMP_GREATER;
        state.fogEnable = TRUE;

        const auto fixed = translate_fixed_function_pipeline_with_shader_semantics(
            state, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            fixed.pixelShader.generated() &&
            fixed.alphaTestOwnedByPixelShader &&
            (fixed.renderStates.unsupported &
             PipelineUnsupportedAlphaTest) == 0 &&
            (fixed.renderStates.unsupported &
             PipelineUnsupportedFog) != 0 &&
            !fixed.exact(),
            "alpha-test handoff cleared an unrelated pipeline blocker");
    }

    {
        auto state = base_state();
        const auto fixed = translate_fixed_function_pipeline_with_shader_semantics(
            state, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            fixed.pixelShader.generated() &&
            !fixed.alphaTestOwnedByPixelShader &&
            fixed.renderStates.exact() &&
            fixed.exact(),
            "disabled alpha test should need no shader-owned blocker discharge");
    }

    {
        auto gouraudState = base_state();
        gouraudState.shadeMode = D3DSHADE_GOURAUD;
        const auto gouraud = translate_pipeline(gouraudState);
        require(
            gouraud.exact() &&
            (gouraud.unsupported & PipelineUnsupportedShadeMode) == 0,
            "R158 Gouraud shade mode remains exact");

        auto flatState = gouraudState;
        flatState.shadeMode = D3DSHADE_FLAT;
        const auto flat = translate_pipeline(flatState);
        require(
            !flat.exact() &&
            (flat.unsupported & PipelineUnsupportedShadeMode) != 0,
            "R158 flat shade mode remains fail closed");
        const auto fixedFlat =
            translate_fixed_function_pipeline_with_shader_semantics(
                flatState, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            !fixedFlat.exact() &&
            (fixedFlat.renderStates.unsupported &
             PipelineUnsupportedShadeMode) != 0,
            "R158 shader handoff retains flat shade blocker");

        auto phongState = gouraudState;
        phongState.shadeMode = D3DSHADE_PHONG;
        const auto phong = translate_pipeline(phongState);
        require(
            !phong.exact() &&
            (phong.unsupported & PipelineUnsupportedShadeMode) != 0,
            "R158 phong shade mode remains fail closed");
    }

    {
        auto defaultClipping = base_state();
        const auto defaultPipeline = translate_pipeline(defaultClipping);
        require(
            defaultPipeline.exact() &&
            defaultPipeline.rasterizer.DepthClipEnable == TRUE &&
            (defaultPipeline.unsupported & PipelineUnsupportedClipping) == 0,
            "R161 default D3D9 clipping must remain exact");

        auto clippingDisabled = defaultClipping;
        clippingDisabled.clipping = FALSE;
        const auto disabledPipeline = translate_pipeline(clippingDisabled);
        require(
            !disabledPipeline.exact() &&
            (disabledPipeline.unsupported & PipelineUnsupportedClipping) != 0,
            "R161 disabled D3D9 clipping must fail closed");

        auto userClipPlane = defaultClipping;
        userClipPlane.clipPlaneEnable = 1u << 2;
        const auto userClipPipeline = translate_pipeline(userClipPlane);
        require(
            !userClipPipeline.exact() &&
            (userClipPipeline.unsupported & PipelineUnsupportedClipping) != 0,
            "R161 enabled D3D9 user clip plane must fail closed");

        const auto fixedUserClip =
            translate_fixed_function_pipeline_with_shader_semantics(
                userClipPlane, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            !fixedUserClip.exact() &&
            (fixedUserClip.renderStates.unsupported &
             PipelineUnsupportedClipping) != 0,
            "R161 fixed-function shader handoff must retain clipping blocker");
    }

    std::cout
        << "DX11 fixed-function clipping fail-closed R161: PASS\n"
        << "DX11 fixed-function alpha-test pipeline handoff R118: PASS\n"
        << "DX11 fixed-function shade-mode fail-closed R158: PASS\n";
    return 0;
}
