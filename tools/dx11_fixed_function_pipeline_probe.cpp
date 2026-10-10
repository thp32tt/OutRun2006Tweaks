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
            "R162 Gouraud shade mode remains exact");

        auto flatState = gouraudState;
        flatState.shadeMode = D3DSHADE_FLAT;
        const auto flat = translate_pipeline(flatState);
        require(
            !flat.exact() &&
            (flat.unsupported & PipelineUnsupportedShadeMode) != 0,
            "R162 flat shade mode remains fail closed");
        const auto fixedFlat =
            translate_fixed_function_pipeline_with_shader_semantics(
                flatState, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            !fixedFlat.exact() &&
            (fixedFlat.renderStates.unsupported &
             PipelineUnsupportedShadeMode) != 0,
            "R162 shader handoff retains flat shade blocker");

        auto phongState = gouraudState;
        phongState.shadeMode = D3DSHADE_PHONG;
        const auto phong = translate_pipeline(phongState);
        require(
            !phong.exact() &&
            (phong.unsupported & PipelineUnsupportedShadeMode) != 0,
            "R162 phong shade mode remains fail closed");
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

    {
        auto unbiased = base_state();
        const auto unbiasedPipeline = translate_pipeline(unbiased);
        require(
            unbiasedPipeline.exact() &&
            (unbiasedPipeline.unsupported & PipelineUnsupportedDepthBias) == 0,
            "DX11 zero depth bias must remain exact");

        auto constantBias = unbiased;
        constantBias.depthBiasBits = 0x3F000000u; // +0.5f as raw D3D9 bits
        const auto constantBiasPipeline = translate_pipeline(constantBias);
        require(
            !constantBiasPipeline.exact() &&
            (constantBiasPipeline.unsupported &
             PipelineUnsupportedDepthBias) != 0,
            "DX11 nonzero D3D9 constant depth bias must fail closed");

        auto slopeBias = unbiased;
        slopeBias.slopeScaleDepthBiasBits = 0xBF800000u; // -1.0f
        const auto slopeBiasPipeline = translate_pipeline(slopeBias);
        require(
            !slopeBiasPipeline.exact() &&
            (slopeBiasPipeline.unsupported &
             PipelineUnsupportedDepthBias) != 0,
            "DX11 nonzero D3D9 slope depth bias must fail closed");

        const auto fixedSlopeBias =
            translate_fixed_function_pipeline_with_shader_semantics(
                slopeBias, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            !fixedSlopeBias.exact() &&
            (fixedSlopeBias.renderStates.unsupported &
             PipelineUnsupportedDepthBias) != 0,
            "DX11 fixed-function handoff must retain depth-bias blocker");
    }

    {
        auto noVertexBlend = base_state();
        const auto defaultPipeline = translate_pipeline(noVertexBlend);
        require(
            defaultPipeline.exact() &&
            (defaultPipeline.unsupported &
             PipelineUnsupportedVertexBlend) == 0,
            "R163 disabled vertex blending must remain exact");

        auto weightedVertexBlend = noVertexBlend;
        weightedVertexBlend.vertexBlend = D3DVBF_1WEIGHTS;
        const auto weightedPipeline =
            translate_pipeline(weightedVertexBlend);
        require(
            !weightedPipeline.exact() &&
            (weightedPipeline.unsupported &
             PipelineUnsupportedVertexBlend) != 0,
            "R163 weighted vertex blending must fail closed");

        auto indexedVertexBlend = noVertexBlend;
        indexedVertexBlend.vertexBlend = D3DVBF_1WEIGHTS;
        indexedVertexBlend.indexedVertexBlendEnable = TRUE;
        const auto indexedPipeline =
            translate_pipeline(indexedVertexBlend);
        require(
            !indexedPipeline.exact() &&
            (indexedPipeline.unsupported &
             PipelineUnsupportedVertexBlend) != 0,
            "R163 indexed vertex blending must fail closed");

        const auto fixedIndexed =
            translate_fixed_function_pipeline_with_shader_semantics(
                indexedVertexBlend, true, stages, true,
                0x00, 0x00, textureTypes);
        require(
            !fixedIndexed.exact() &&
            (fixedIndexed.renderStates.unsupported &
             PipelineUnsupportedVertexBlend) != 0,
            "R163 fixed-function handoff must retain vertex-blend blocker");
    }

    {
        auto ditherOff = base_state();
        ditherOff.ditherEnable = FALSE;
        const auto ditherOffPipeline = translate_pipeline(ditherOff);
        require(
            ditherOffPipeline.exact() &&
            (ditherOffPipeline.unsupported & PipelineUnsupportedDither) == 0,
            "R165 disabled D3D9 dithering must remain exact");

        auto ditherOn = ditherOff;
        ditherOn.ditherEnable = TRUE;
        const auto ditherOnPipeline = translate_pipeline(ditherOn);
        require(
            !ditherOnPipeline.exact() &&
            (ditherOnPipeline.unsupported & PipelineUnsupportedDither) != 0,
            "R165 enabled D3D9 dithering must fail closed");

        const auto fixedDitherOn =
            translate_fixed_function_pipeline_with_shader_semantics(
                ditherOn, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            !fixedDitherOn.exact() &&
            (fixedDitherOn.renderStates.unsupported &
             PipelineUnsupportedDither) != 0,
            "R165 fixed-function shader handoff must retain dithering blocker");
    }

    {
        std::array<FixedFunctionStageState, 8> tempStages{};
        tempStages[0].colorOp = D3DTOP_SELECTARG1;
        tempStages[0].colorArg1 = D3DTA_DIFFUSE;
        tempStages[0].alphaOp = D3DTOP_SELECTARG1;
        tempStages[0].alphaArg1 = D3DTA_DIFFUSE;
        tempStages[0].resultArg = D3DTA_TEMP;
        tempStages[0].minFilter = D3DTEXF_POINT;
        tempStages[0].magFilter = D3DTEXF_POINT;
        tempStages[0].mipFilter = D3DTEXF_NONE;

        tempStages[1].colorOp = D3DTOP_ADD;
        tempStages[1].colorArg1 = D3DTA_TEMP;
        tempStages[1].colorArg2 = D3DTA_CURRENT;
        tempStages[1].alphaOp = D3DTOP_ADD;
        tempStages[1].alphaArg1 = D3DTA_TEMP;
        tempStages[1].alphaArg2 = D3DTA_CURRENT;
        tempStages[1].resultArg = D3DTA_CURRENT;
        tempStages[1].minFilter = D3DTEXF_POINT;
        tempStages[1].magFilter = D3DTEXF_POINT;
        tempStages[1].mipFilter = D3DTEXF_NONE;

        const auto tempReadiness = translate_fixed_function_readiness(
            tempStages, true, 0x00u, 0x00u);
        require(
            tempReadiness.exact() &&
            (tempReadiness.unsupported &
             FixedFunctionUnsupportedResultArg) == 0,
            "R200 D3DTSS_RESULTARG TEMP write/read chain must become exact");

        const auto tempShader =
            generate_fixed_function_pixel_shader_prototype(
                tempStages, true, 0x00u, 0x00u, textureTypes);
        require(
            tempShader.generated() && tempShader.activeStages == 2,
            "R200 TEMP register fixture must generate a two-stage shader");
        require(
            tempShader.source.find("float4 temp = 0.0f;") !=
                std::string::npos &&
            tempShader.source.find(
                "temp = float4(nextColor, nextAlpha);") !=
                std::string::npos &&
            tempShader.source.find(
                "float3 nextColor = temp.rgb + current.rgb;") !=
                std::string::npos &&
            tempShader.source.find(
                "float nextAlpha = temp.a + current.a;") !=
                std::string::npos,
            "R200 TEMP register shader dataflow drift");

        const auto tempCompile =
            compile_fixed_function_pixel_shader_prototype(tempShader);
        require(
            tempCompile.attempted && tempCompile.succeeded &&
            tempCompile.result == S_OK && tempCompile.bytecodeBytes != 0,
            "R200 TEMP register fixed-function shader prototype did not compile");

        auto uninitializedTemp = tempStages;
        uninitializedTemp[0].resultArg = D3DTA_CURRENT;
        uninitializedTemp[0].colorArg1 = D3DTA_TEMP;
        uninitializedTemp[0].alphaArg1 = D3DTA_TEMP;
        uninitializedTemp[1].colorOp = D3DTOP_DISABLE;
        uninitializedTemp[1].alphaOp = D3DTOP_DISABLE;
        const auto uninitializedReadiness =
            translate_fixed_function_readiness(
                uninitializedTemp, true, 0x00u, 0x00u);
        require(
            uninitializedReadiness.exact() &&
            (uninitializedReadiness.unsupported &
             FixedFunctionUnsupportedResultArg) == 0,
            "R201 default-zero D3DTA_TEMP read must remain exact");
        const auto uninitializedShader =
            generate_fixed_function_pixel_shader_prototype(
                uninitializedTemp, true, 0x00u, 0x00u, textureTypes);
        require(
            uninitializedShader.generated() &&
            uninitializedShader.source.find("float4 temp = 0.0f;") !=
                std::string::npos &&
            uninitializedShader.source.find(
                "float3 nextColor = temp.rgb;") != std::string::npos &&
            uninitializedShader.source.find(
                "float nextAlpha = temp.a;") != std::string::npos,
            "R201 default-zero TEMP shader semantics drift");
        const auto uninitializedCompile =
            compile_fixed_function_pixel_shader_prototype(uninitializedShader);
        require(
            uninitializedCompile.attempted &&
            uninitializedCompile.succeeded &&
            uninitializedCompile.result == S_OK &&
            uninitializedCompile.bytecodeBytes != 0,
            "R201 default-zero TEMP fixed-function shader did not compile");

        auto invalidDestination = tempStages;
        invalidDestination[0].resultArg = D3DTA_DIFFUSE;
        const auto invalidDestinationReadiness =
            translate_fixed_function_readiness(
                invalidDestination, true, 0x00u, 0x00u);
        require(
            !invalidDestinationReadiness.exact() &&
            (invalidDestinationReadiness.unsupported &
             FixedFunctionUnsupportedResultArg) != 0,
            "R200 invalid D3DTSS_RESULTARG selector must fail closed");
    }

    {
        auto multisampleOn = base_state();
        multisampleOn.multiSampleAntialias = TRUE;
        const auto multisampleOnPipeline = translate_pipeline(multisampleOn);
        require(
            multisampleOnPipeline.exact() &&
            multisampleOnPipeline.rasterizer.MultisampleEnable == TRUE,
            "R171 enabled D3D9 multisample raster intent reaches D3D11 rasterizer state");

        auto multisampleOff = multisampleOn;
        multisampleOff.multiSampleAntialias = FALSE;
        const auto multisampleOffPipeline = translate_pipeline(multisampleOff);
        require(
            multisampleOffPipeline.exact() &&
            multisampleOffPipeline.rasterizer.MultisampleEnable == FALSE,
            "R171 disabled D3D9 multisample raster intent reaches D3D11 rasterizer state");
    }

    {
        auto defaultMrt = base_state();
        const auto defaultMrtPipeline = translate_pipeline(defaultMrt);
        require(
            defaultMrtPipeline.exact() &&
            (defaultMrtPipeline.unsupported &
             PipelineUnsupportedMrtColorWrite) == 0,
            "default MRT color-write masks must remain exact");

        auto mrt1Masked = defaultMrt;
        mrt1Masked.additionalColorWriteEnable[0] = D3DCOLORWRITEENABLE_RED;
        const auto mrt1Pipeline = translate_pipeline(mrt1Masked);
        require(
            !mrt1Pipeline.exact() &&
            (mrt1Pipeline.unsupported &
             PipelineUnsupportedMrtColorWrite) != 0,
            "non-default COLORWRITEENABLE1 must fail closed");

        auto mrt3Masked = defaultMrt;
        mrt3Masked.additionalColorWriteEnable[2] = 0u;
        const auto mrt3Pipeline = translate_pipeline(mrt3Masked);
        require(
            !mrt3Pipeline.exact() &&
            (mrt3Pipeline.unsupported &
             PipelineUnsupportedMrtColorWrite) != 0,
            "non-default COLORWRITEENABLE3 must fail closed");

        const auto fixedMrt3 =
            translate_fixed_function_pipeline_with_shader_semantics(
                mrt3Masked, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            !fixedMrt3.exact() &&
            (fixedMrt3.renderStates.unsupported &
             PipelineUnsupportedMrtColorWrite) != 0,
            "fixed-function handoff must retain MRT color-write blocker");
    }

    {
        auto lineRaster = base_state();
        lineRaster.lastPixel = TRUE;
        lineRaster.antialiasedLineEnable = FALSE;
        const auto aliasedLinePipeline = translate_pipeline(lineRaster);
        require(
            aliasedLinePipeline.exact() &&
            aliasedLinePipeline.rasterizer.AntialiasedLineEnable == FALSE,
            "R168 aliased D3D9 line intent maps to disabled D3D11 line AA");

        auto antialiasedLine = lineRaster;
        antialiasedLine.antialiasedLineEnable = TRUE;
        const auto antialiasedLinePipeline = translate_pipeline(antialiasedLine);
        require(
            antialiasedLinePipeline.exact() &&
            antialiasedLinePipeline.rasterizer.AntialiasedLineEnable == TRUE,
            "R168 D3D9 antialiased-line intent reaches D3D11 rasterizer state");

        auto noLastPixel = lineRaster;
        noLastPixel.lastPixel = FALSE;
        const auto noLastPixelPipeline = translate_pipeline(noLastPixel);
        require(
            noLastPixelPipeline.exact(),
            "R168 LASTPIXEL remains dispatch-scoped rather than globally blocking triangles");
    }

    {
        auto wrapOff = base_state();
        const auto wrapOffPipeline = translate_pipeline(wrapOff);
        require(
            wrapOffPipeline.exact() &&
            (wrapOffPipeline.unsupported &
             PipelineUnsupportedTextureCoordinateWrap) == 0,
            "R170 zero texture-coordinate wrap masks must remain exact");

        auto wrapStage0 = wrapOff;
        wrapStage0.textureCoordinateWrap[0] = D3DWRAP_U;
        const auto wrapStage0Pipeline = translate_pipeline(wrapStage0);
        require(
            !wrapStage0Pipeline.exact() &&
            (wrapStage0Pipeline.unsupported &
             PipelineUnsupportedTextureCoordinateWrap) != 0,
            "R170 nonzero D3DRS_WRAP0 must fail closed");

        auto wrapStage7 = wrapOff;
        wrapStage7.textureCoordinateWrap[7] = D3DWRAP_V | D3DWRAP_W;
        const auto wrapStage7Pipeline = translate_pipeline(wrapStage7);
        require(
            !wrapStage7Pipeline.exact() &&
            (wrapStage7Pipeline.unsupported &
             PipelineUnsupportedTextureCoordinateWrap) != 0,
            "R170 nonzero D3DRS_WRAP7 must fail closed");

        const auto fixedWrapStage7 =
            translate_fixed_function_pipeline_with_shader_semantics(
                wrapStage7, true, stages, true, 0x00, 0x00, textureTypes);
        require(
            !fixedWrapStage7.exact() &&
            (fixedWrapStage7.renderStates.unsupported &
             PipelineUnsupportedTextureCoordinateWrap) != 0,
            "R170 fixed-function handoff must retain texture-coordinate wrap blocker");
    }

    {
        std::array<FixedFunctionStageState, 8> modifierStages{};
        modifierStages[0].colorOp = D3DTOP_SELECTARG1;
        modifierStages[0].colorArg1 =
            D3DTA_TEXTURE | D3DTA_ALPHAREPLICATE | D3DTA_COMPLEMENT;
        modifierStages[0].alphaOp = D3DTOP_SELECTARG1;
        modifierStages[0].alphaArg1 = D3DTA_DIFFUSE | D3DTA_COMPLEMENT;
        modifierStages[0].minFilter = D3DTEXF_POINT;
        modifierStages[0].magFilter = D3DTEXF_POINT;
        modifierStages[0].mipFilter = D3DTEXF_NONE;

        const auto modifierReadiness = translate_fixed_function_readiness(
            modifierStages, true, 0x01u, 0x01u);
        require(
            modifierReadiness.exact() &&
            (modifierReadiness.unsupported &
             FixedFunctionUnsupportedArgument) == 0,
            "R178 supported D3DTA modifiers must remain shader-exact");

        const auto modifierShader =
            generate_fixed_function_pixel_shader_prototype(
                modifierStages, true, 0x01u, 0x01u, textureTypes);
        require(
            modifierShader.generated() &&
            modifierShader.source.find(
                "float3 nextColor = (1.0 - sampled0.aaa);") !=
                std::string::npos &&
            modifierShader.source.find(
                "float nextAlpha = (1.0 - input.diffuse.a);") !=
                std::string::npos,
            "R178 complement/alpha-replicate shader expression drift");

        const auto modifierCompile =
            compile_fixed_function_pixel_shader_prototype(modifierShader);
        require(
            modifierCompile.attempted && modifierCompile.succeeded &&
            modifierCompile.result == S_OK &&
            modifierCompile.bytecodeBytes != 0,
            "R178 D3DTA modifier shader prototype did not compile");

        auto unknownModifierStages = modifierStages;
        unknownModifierStages[0].colorArg1 = D3DTA_TEXTURE | 0x40u;
        const auto unknownModifierReadiness =
            translate_fixed_function_readiness(
                unknownModifierStages, true, 0x01u, 0x01u);
        require(
            !unknownModifierReadiness.exact() &&
            (unknownModifierReadiness.unsupported &
             FixedFunctionUnsupportedArgument) != 0,
            "R178 unknown D3DTA modifier bits must fail closed");
    }

    {
        std::array<FixedFunctionStageState, 8> addStages{};
        addStages[0].colorOp = D3DTOP_ADD;
        addStages[0].colorArg1 = D3DTA_TEXTURE;
        addStages[0].colorArg2 = D3DTA_DIFFUSE;
        addStages[0].alphaOp = D3DTOP_SELECTARG1;
        addStages[0].alphaArg1 = D3DTA_TEXTURE;
        addStages[0].minFilter = D3DTEXF_POINT;
        addStages[0].magFilter = D3DTEXF_POINT;
        addStages[0].mipFilter = D3DTEXF_NONE;

        const auto addShader = generate_fixed_function_pixel_shader_prototype(
            addStages, true, 0x01u, 0x01u, textureTypes);
        require(
            addShader.generated() && addShader.activeStages == 1,
            "D3DTOP_ADD fixed-function stage must become shader-exact");
        require(
            addShader.source.find(
                "float3 nextColor = sampled0.rgb + input.diffuse.rgb;") !=
                std::string::npos,
            "D3DTOP_ADD shader expression drift");
        const auto addCompile =
            compile_fixed_function_pixel_shader_prototype(addShader);
        require(
            addCompile.attempted && addCompile.succeeded &&
            addCompile.result == S_OK && addCompile.bytecodeBytes != 0,
            "D3DTOP_ADD fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> subtractStages{};
        subtractStages[0].colorOp = D3DTOP_SUBTRACT;
        subtractStages[0].colorArg1 = D3DTA_TEXTURE;
        subtractStages[0].colorArg2 = D3DTA_DIFFUSE;
        subtractStages[0].alphaOp = D3DTOP_SELECTARG1;
        subtractStages[0].alphaArg1 = D3DTA_TEXTURE;
        subtractStages[0].minFilter = D3DTEXF_POINT;
        subtractStages[0].magFilter = D3DTEXF_POINT;
        subtractStages[0].mipFilter = D3DTEXF_NONE;
        const auto subtractShader = generate_fixed_function_pixel_shader_prototype(
            subtractStages, true, 0x01u, 0x01u, textureTypes);
        require(
            subtractShader.generated() && subtractShader.activeStages == 1,
            "R177 D3DTOP_SUBTRACT fixed-function stage must become shader-exact");
        require(
            subtractShader.source.find(
                "float3 nextColor = sampled0.rgb - input.diffuse.rgb;") != std::string::npos,
            "R177 D3DTOP_SUBTRACT shader expression drift");
        const auto subtractCompile =
            compile_fixed_function_pixel_shader_prototype(subtractShader);
        require(
            subtractCompile.attempted && subtractCompile.succeeded &&
            subtractCompile.result == S_OK && subtractCompile.bytecodeBytes != 0,
            "R177 D3DTOP_SUBTRACT fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> modulate2xStages{};
        modulate2xStages[0].colorOp = D3DTOP_MODULATE2X;
        modulate2xStages[0].colorArg1 = D3DTA_TEXTURE;
        modulate2xStages[0].colorArg2 = D3DTA_DIFFUSE;
        modulate2xStages[0].alphaOp = D3DTOP_MODULATE2X;
        modulate2xStages[0].alphaArg1 = D3DTA_TEXTURE;
        modulate2xStages[0].alphaArg2 = D3DTA_DIFFUSE;
        modulate2xStages[0].minFilter = D3DTEXF_POINT;
        modulate2xStages[0].magFilter = D3DTEXF_POINT;
        modulate2xStages[0].mipFilter = D3DTEXF_NONE;

        const auto modulate2xShader =
            generate_fixed_function_pixel_shader_prototype(
                modulate2xStages, true, 0x01u, 0x01u, textureTypes);
        require(
            modulate2xShader.generated() && modulate2xShader.activeStages == 1,
            "R180 D3DTOP_MODULATE2X fixed-function stage must become shader-exact");
        require(
            modulate2xShader.source.find(
                "float3 nextColor = (sampled0.rgb * input.diffuse.rgb) * 2.0;") !=
                std::string::npos &&
            modulate2xShader.source.find(
                "float nextAlpha = (sampled0.a * input.diffuse.a) * 2.0;") !=
                std::string::npos,
            "R180 D3DTOP_MODULATE2X shader expression drift");
        const auto modulate2xCompile =
            compile_fixed_function_pixel_shader_prototype(modulate2xShader);
        require(
            modulate2xCompile.attempted && modulate2xCompile.succeeded &&
            modulate2xCompile.result == S_OK &&
            modulate2xCompile.bytecodeBytes != 0,
            "R180 D3DTOP_MODULATE2X fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> modulate4xStages{};
        modulate4xStages[0].colorOp = D3DTOP_MODULATE4X;
        modulate4xStages[0].colorArg1 = D3DTA_TEXTURE;
        modulate4xStages[0].colorArg2 = D3DTA_DIFFUSE;
        modulate4xStages[0].alphaOp = D3DTOP_MODULATE4X;
        modulate4xStages[0].alphaArg1 = D3DTA_TEXTURE;
        modulate4xStages[0].alphaArg2 = D3DTA_DIFFUSE;
        modulate4xStages[0].minFilter = D3DTEXF_POINT;
        modulate4xStages[0].magFilter = D3DTEXF_POINT;
        modulate4xStages[0].mipFilter = D3DTEXF_NONE;

        const auto modulate4xShader =
            generate_fixed_function_pixel_shader_prototype(
                modulate4xStages, true, 0x01u, 0x01u, textureTypes);
        require(
            modulate4xShader.generated() && modulate4xShader.activeStages == 1,
            "R181 D3DTOP_MODULATE4X fixed-function stage must become shader-exact");
        require(
            modulate4xShader.source.find(
                "float3 nextColor = (sampled0.rgb * input.diffuse.rgb) * 4.0;") !=
                std::string::npos &&
            modulate4xShader.source.find(
                "float nextAlpha = (sampled0.a * input.diffuse.a) * 4.0;") !=
                std::string::npos,
            "R181 D3DTOP_MODULATE4X shader expression drift");
        const auto modulate4xCompile =
            compile_fixed_function_pixel_shader_prototype(modulate4xShader);
        require(
            modulate4xCompile.attempted && modulate4xCompile.succeeded &&
            modulate4xCompile.result == S_OK &&
            modulate4xCompile.bytecodeBytes != 0,
            "R181 D3DTOP_MODULATE4X fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> addSignedStages{};
        addSignedStages[0].colorOp = D3DTOP_ADDSIGNED;
        addSignedStages[0].colorArg1 = D3DTA_TEXTURE;
        addSignedStages[0].colorArg2 = D3DTA_DIFFUSE;
        addSignedStages[0].alphaOp = D3DTOP_ADDSIGNED;
        addSignedStages[0].alphaArg1 = D3DTA_TEXTURE;
        addSignedStages[0].alphaArg2 = D3DTA_DIFFUSE;
        addSignedStages[0].minFilter = D3DTEXF_POINT;
        addSignedStages[0].magFilter = D3DTEXF_POINT;
        addSignedStages[0].mipFilter = D3DTEXF_NONE;

        const auto addSignedShader =
            generate_fixed_function_pixel_shader_prototype(
                addSignedStages, true, 0x01u, 0x01u, textureTypes);
        require(
            addSignedShader.generated() && addSignedShader.activeStages == 1,
            "R182 D3DTOP_ADDSIGNED fixed-function stage must become shader-exact");
        require(
            addSignedShader.source.find(
                "float3 nextColor = sampled0.rgb + input.diffuse.rgb - 0.5;") !=
                std::string::npos &&
            addSignedShader.source.find(
                "float nextAlpha = sampled0.a + input.diffuse.a - 0.5;") !=
                std::string::npos,
            "R182 D3DTOP_ADDSIGNED shader expression drift");
        const auto addSignedCompile =
            compile_fixed_function_pixel_shader_prototype(addSignedShader);
        require(
            addSignedCompile.attempted && addSignedCompile.succeeded &&
            addSignedCompile.result == S_OK &&
            addSignedCompile.bytecodeBytes != 0,
            "R182 D3DTOP_ADDSIGNED fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> addSigned2xStages{};
        addSigned2xStages[0].colorOp = D3DTOP_ADDSIGNED2X;
        addSigned2xStages[0].colorArg1 = D3DTA_TEXTURE;
        addSigned2xStages[0].colorArg2 = D3DTA_DIFFUSE;
        addSigned2xStages[0].alphaOp = D3DTOP_ADDSIGNED2X;
        addSigned2xStages[0].alphaArg1 = D3DTA_TEXTURE;
        addSigned2xStages[0].alphaArg2 = D3DTA_DIFFUSE;
        addSigned2xStages[0].minFilter = D3DTEXF_POINT;
        addSigned2xStages[0].magFilter = D3DTEXF_POINT;
        addSigned2xStages[0].mipFilter = D3DTEXF_NONE;

        const auto addSigned2xShader =
            generate_fixed_function_pixel_shader_prototype(
                addSigned2xStages, true, 0x01u, 0x01u, textureTypes);
        require(
            addSigned2xShader.generated() && addSigned2xShader.activeStages == 1,
            "R183 D3DTOP_ADDSIGNED2X fixed-function stage must become shader-exact");
        require(
            addSigned2xShader.source.find(
                "float3 nextColor = (sampled0.rgb + input.diffuse.rgb - 0.5) * 2.0;") !=
                std::string::npos &&
            addSigned2xShader.source.find(
                "float nextAlpha = (sampled0.a + input.diffuse.a - 0.5) * 2.0;") !=
                std::string::npos,
            "R183 D3DTOP_ADDSIGNED2X shader expression drift");
        const auto addSigned2xCompile =
            compile_fixed_function_pixel_shader_prototype(addSigned2xShader);
        require(
            addSigned2xCompile.attempted && addSigned2xCompile.succeeded &&
            addSigned2xCompile.result == S_OK &&
            addSigned2xCompile.bytecodeBytes != 0,
            "R183 D3DTOP_ADDSIGNED2X fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> addSmoothStages{};
        addSmoothStages[0].colorOp = D3DTOP_ADDSMOOTH;
        addSmoothStages[0].colorArg1 = D3DTA_TEXTURE;
        addSmoothStages[0].colorArg2 = D3DTA_DIFFUSE;
        addSmoothStages[0].alphaOp = D3DTOP_ADDSMOOTH;
        addSmoothStages[0].alphaArg1 = D3DTA_TEXTURE;
        addSmoothStages[0].alphaArg2 = D3DTA_DIFFUSE;
        addSmoothStages[0].minFilter = D3DTEXF_POINT;
        addSmoothStages[0].magFilter = D3DTEXF_POINT;
        addSmoothStages[0].mipFilter = D3DTEXF_NONE;

        const auto addSmoothShader =
            generate_fixed_function_pixel_shader_prototype(
                addSmoothStages, true, 0x01u, 0x01u, textureTypes);
        require(
            addSmoothShader.generated() && addSmoothShader.activeStages == 1,
            "R184 D3DTOP_ADDSMOOTH fixed-function stage must become shader-exact");
        require(
            addSmoothShader.source.find(
                "float3 nextColor = sampled0.rgb + input.diffuse.rgb * (1.0 - sampled0.rgb);") !=
                std::string::npos &&
            addSmoothShader.source.find(
                "float nextAlpha = sampled0.a + input.diffuse.a * (1.0 - sampled0.a);") !=
                std::string::npos,
            "R184 D3DTOP_ADDSMOOTH shader expression drift");
        const auto addSmoothCompile =
            compile_fixed_function_pixel_shader_prototype(addSmoothShader);
        require(
            addSmoothCompile.attempted && addSmoothCompile.succeeded &&
            addSmoothCompile.result == S_OK &&
            addSmoothCompile.bytecodeBytes != 0,
            "R184 D3DTOP_ADDSMOOTH fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> blendDiffuseAlphaStages{};
        blendDiffuseAlphaStages[0].colorOp = D3DTOP_BLENDDIFFUSEALPHA;
        blendDiffuseAlphaStages[0].colorArg1 = D3DTA_TEXTURE;
        blendDiffuseAlphaStages[0].colorArg2 = D3DTA_DIFFUSE;
        blendDiffuseAlphaStages[0].alphaOp = D3DTOP_BLENDDIFFUSEALPHA;
        blendDiffuseAlphaStages[0].alphaArg1 = D3DTA_TEXTURE;
        blendDiffuseAlphaStages[0].alphaArg2 = D3DTA_DIFFUSE;
        blendDiffuseAlphaStages[0].minFilter = D3DTEXF_POINT;
        blendDiffuseAlphaStages[0].magFilter = D3DTEXF_POINT;
        blendDiffuseAlphaStages[0].mipFilter = D3DTEXF_NONE;

        const auto blendDiffuseAlphaShader =
            generate_fixed_function_pixel_shader_prototype(
                blendDiffuseAlphaStages, true, 0x01u, 0x01u, textureTypes);
        require(
            blendDiffuseAlphaShader.generated() &&
                blendDiffuseAlphaShader.activeStages == 1,
            "R185 D3DTOP_BLENDDIFFUSEALPHA fixed-function stage must become shader-exact");
        require(
            blendDiffuseAlphaShader.source.find(
                "float3 nextColor = sampled0.rgb * input.diffuse.a + input.diffuse.rgb * (1.0 - input.diffuse.a);") !=
                std::string::npos &&
            blendDiffuseAlphaShader.source.find(
                "float nextAlpha = sampled0.a * input.diffuse.a + input.diffuse.a * (1.0 - input.diffuse.a);") !=
                std::string::npos,
            "R185 D3DTOP_BLENDDIFFUSEALPHA shader expression drift");
        const auto blendDiffuseAlphaCompile =
            compile_fixed_function_pixel_shader_prototype(
                blendDiffuseAlphaShader);
        require(
            blendDiffuseAlphaCompile.attempted &&
            blendDiffuseAlphaCompile.succeeded &&
            blendDiffuseAlphaCompile.result == S_OK &&
            blendDiffuseAlphaCompile.bytecodeBytes != 0,
            "R185 D3DTOP_BLENDDIFFUSEALPHA fixed-function shader prototype did not compile");
    }


    {
        std::array<FixedFunctionStageState, 8> blendCurrentAlphaStages{};
        blendCurrentAlphaStages[0].colorOp = D3DTOP_SELECTARG1;
        blendCurrentAlphaStages[0].colorArg1 = D3DTA_DIFFUSE;
        blendCurrentAlphaStages[0].alphaOp = D3DTOP_SELECTARG1;
        blendCurrentAlphaStages[0].alphaArg1 = D3DTA_DIFFUSE;
        blendCurrentAlphaStages[0].minFilter = D3DTEXF_POINT;
        blendCurrentAlphaStages[0].magFilter = D3DTEXF_POINT;
        blendCurrentAlphaStages[0].mipFilter = D3DTEXF_NONE;
        blendCurrentAlphaStages[1].colorOp = D3DTOP_BLENDCURRENTALPHA;
        blendCurrentAlphaStages[1].colorArg1 = D3DTA_TEXTURE;
        blendCurrentAlphaStages[1].colorArg2 = D3DTA_DIFFUSE;
        blendCurrentAlphaStages[1].alphaOp = D3DTOP_BLENDCURRENTALPHA;
        blendCurrentAlphaStages[1].alphaArg1 = D3DTA_TEXTURE;
        blendCurrentAlphaStages[1].alphaArg2 = D3DTA_DIFFUSE;
        blendCurrentAlphaStages[1].minFilter = D3DTEXF_POINT;
        blendCurrentAlphaStages[1].magFilter = D3DTEXF_POINT;
        blendCurrentAlphaStages[1].mipFilter = D3DTEXF_NONE;

        const auto blendCurrentAlphaShader =
            generate_fixed_function_pixel_shader_prototype(
                blendCurrentAlphaStages, true, 0x02u, 0x02u, textureTypes);
        require(
            blendCurrentAlphaShader.generated() &&
                blendCurrentAlphaShader.activeStages == 2,
            "D3DTOP_BLENDCURRENTALPHA fixed-function stages must become shader-exact");
        require(
            blendCurrentAlphaShader.source.find(
                "float3 nextColor = sampled1.rgb * current.a + input.diffuse.rgb * (1.0 - current.a);") !=
                std::string::npos &&
            blendCurrentAlphaShader.source.find(
                "float nextAlpha = sampled1.a * current.a + input.diffuse.a * (1.0 - current.a);") !=
                std::string::npos,
            "D3DTOP_BLENDCURRENTALPHA shader expression drift");
        const auto blendCurrentAlphaCompile =
            compile_fixed_function_pixel_shader_prototype(
                blendCurrentAlphaShader);
        require(
            blendCurrentAlphaCompile.attempted &&
            blendCurrentAlphaCompile.succeeded &&
            blendCurrentAlphaCompile.result == S_OK &&
            blendCurrentAlphaCompile.bytecodeBytes != 0,
            "D3DTOP_BLENDCURRENTALPHA fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> blendTextureAlphaStages{};
        blendTextureAlphaStages[0].colorOp = D3DTOP_BLENDTEXTUREALPHA;
        blendTextureAlphaStages[0].colorArg1 = D3DTA_DIFFUSE;
        blendTextureAlphaStages[0].colorArg2 = D3DTA_CURRENT;
        blendTextureAlphaStages[0].alphaOp = D3DTOP_BLENDTEXTUREALPHA;
        blendTextureAlphaStages[0].alphaArg1 = D3DTA_DIFFUSE;
        blendTextureAlphaStages[0].alphaArg2 = D3DTA_CURRENT;
        blendTextureAlphaStages[0].minFilter = D3DTEXF_POINT;
        blendTextureAlphaStages[0].magFilter = D3DTEXF_POINT;
        blendTextureAlphaStages[0].mipFilter = D3DTEXF_NONE;

        const auto blendTextureAlphaMissingResource =
            translate_fixed_function_readiness(
                blendTextureAlphaStages, true, 0x00u, 0x00u);
        require(
            !blendTextureAlphaMissingResource.exact() &&
            (blendTextureAlphaMissingResource.unsupported &
             FixedFunctionUnsupportedResourceStageCoverage) != 0,
            "R186 implicit texture-alpha resource coverage must fail closed");


        const auto blendTextureAlphaShader =
            generate_fixed_function_pixel_shader_prototype(
                blendTextureAlphaStages, true, 0x01u, 0x01u, textureTypes);
        require(
            blendTextureAlphaShader.generated() &&
                blendTextureAlphaShader.activeStages == 1,
            "R186 D3DTOP_BLENDTEXTUREALPHA fixed-function stage must become shader-exact");
        require(
            blendTextureAlphaShader.source.find(
                "float3 nextColor = input.diffuse.rgb * sampled0.a + current.rgb * (1.0 - sampled0.a);") !=
                std::string::npos &&
            blendTextureAlphaShader.source.find(
                "float nextAlpha = input.diffuse.a * sampled0.a + current.a * (1.0 - sampled0.a);") !=
                std::string::npos,
            "R186 D3DTOP_BLENDTEXTUREALPHA shader expression or intrinsic texture dependency drift");
        const auto blendTextureAlphaCompile =
            compile_fixed_function_pixel_shader_prototype(
                blendTextureAlphaShader);
        require(
            blendTextureAlphaCompile.attempted &&
            blendTextureAlphaCompile.succeeded &&
            blendTextureAlphaCompile.result == S_OK &&
            blendTextureAlphaCompile.bytecodeBytes != 0,
            "R186 D3DTOP_BLENDTEXTUREALPHA fixed-function shader prototype did not compile");
    }


    {
        std::array<FixedFunctionStageState, 8> blendTextureAlphaPmStages{};
        blendTextureAlphaPmStages[0].colorOp = D3DTOP_BLENDTEXTUREALPHAPM;
        blendTextureAlphaPmStages[0].colorArg1 = D3DTA_DIFFUSE;
        blendTextureAlphaPmStages[0].colorArg2 = D3DTA_CURRENT;
        blendTextureAlphaPmStages[0].alphaOp = D3DTOP_BLENDTEXTUREALPHAPM;
        blendTextureAlphaPmStages[0].alphaArg1 = D3DTA_DIFFUSE;
        blendTextureAlphaPmStages[0].alphaArg2 = D3DTA_CURRENT;
        blendTextureAlphaPmStages[0].minFilter = D3DTEXF_POINT;
        blendTextureAlphaPmStages[0].magFilter = D3DTEXF_POINT;
        blendTextureAlphaPmStages[0].mipFilter = D3DTEXF_NONE;

        const auto blendTextureAlphaPmMissingResource =
            translate_fixed_function_readiness(
                blendTextureAlphaPmStages, true, 0x00u, 0x00u);
        require(
            !blendTextureAlphaPmMissingResource.exact() &&
            (blendTextureAlphaPmMissingResource.unsupported &
             FixedFunctionUnsupportedResourceStageCoverage) != 0,
            "R187 implicit texture-alpha resource coverage must fail closed");


        const auto blendTextureAlphaPmShader =
            generate_fixed_function_pixel_shader_prototype(
                blendTextureAlphaPmStages, true, 0x01u, 0x01u, textureTypes);
        require(
            blendTextureAlphaPmShader.generated() &&
                blendTextureAlphaPmShader.activeStages == 1,
            "R187 D3DTOP_BLENDTEXTUREALPHAPM fixed-function stage must become shader-exact");
        require(
            blendTextureAlphaPmShader.source.find(
                "float3 nextColor = input.diffuse.rgb + current.rgb * (1.0 - sampled0.a);") !=
                std::string::npos &&
            blendTextureAlphaPmShader.source.find(
                "float nextAlpha = input.diffuse.a + current.a * (1.0 - sampled0.a);") !=
                std::string::npos,
            "R187 D3DTOP_BLENDTEXTUREALPHAPM shader expression or intrinsic texture dependency drift");
        const auto blendTextureAlphaPmCompile =
            compile_fixed_function_pixel_shader_prototype(
                blendTextureAlphaPmShader);
        require(
            blendTextureAlphaPmCompile.attempted &&
            blendTextureAlphaPmCompile.succeeded &&
            blendTextureAlphaPmCompile.result == S_OK &&
            blendTextureAlphaPmCompile.bytecodeBytes != 0,
            "R187 D3DTOP_BLENDTEXTUREALPHAPM fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> modulateAlphaAddColorStages{};
        modulateAlphaAddColorStages[0].colorOp =
            D3DTOP_MODULATEALPHA_ADDCOLOR;
        modulateAlphaAddColorStages[0].colorArg1 = D3DTA_TEXTURE;
        modulateAlphaAddColorStages[0].colorArg2 = D3DTA_DIFFUSE;
        modulateAlphaAddColorStages[0].alphaOp = D3DTOP_SELECTARG1;
        modulateAlphaAddColorStages[0].alphaArg1 = D3DTA_DIFFUSE;
        modulateAlphaAddColorStages[0].alphaArg2 = D3DTA_CURRENT;
        modulateAlphaAddColorStages[0].minFilter = D3DTEXF_POINT;
        modulateAlphaAddColorStages[0].magFilter = D3DTEXF_POINT;
        modulateAlphaAddColorStages[0].mipFilter = D3DTEXF_NONE;

        const auto modulateAlphaAddColorShader =
            generate_fixed_function_pixel_shader_prototype(
                modulateAlphaAddColorStages, true, 0x01u, 0x01u,
                textureTypes);
        require(
            modulateAlphaAddColorShader.generated() &&
                modulateAlphaAddColorShader.activeStages == 1,
            "D3DTOP_MODULATEALPHA_ADDCOLOR COLOROP must become shader-exact");
        require(
            modulateAlphaAddColorShader.source.find(
                "float3 nextColor = sampled0.rgb + sampled0.a * input.diffuse.rgb;") !=
                std::string::npos &&
            modulateAlphaAddColorShader.source.find(
                "float nextAlpha = input.diffuse.a;") !=
                std::string::npos,
            "D3DTOP_MODULATEALPHA_ADDCOLOR shader expression drift");
        const auto modulateAlphaAddColorCompile =
            compile_fixed_function_pixel_shader_prototype(
                modulateAlphaAddColorShader);
        require(
            modulateAlphaAddColorCompile.attempted &&
            modulateAlphaAddColorCompile.succeeded &&
            modulateAlphaAddColorCompile.result == S_OK &&
            modulateAlphaAddColorCompile.bytecodeBytes != 0,
            "D3DTOP_MODULATEALPHA_ADDCOLOR fixed-function shader prototype did not compile");

        auto invalidAlphaStages = modulateAlphaAddColorStages;
        invalidAlphaStages[0].colorOp = D3DTOP_SELECTARG1;
        invalidAlphaStages[0].colorArg1 = D3DTA_DIFFUSE;
        invalidAlphaStages[0].alphaOp =
            D3DTOP_MODULATEALPHA_ADDCOLOR;
        invalidAlphaStages[0].alphaArg1 = D3DTA_TEXTURE;
        invalidAlphaStages[0].alphaArg2 = D3DTA_DIFFUSE;
        const auto invalidAlphaReadiness =
            translate_fixed_function_readiness(
                invalidAlphaStages, true, 0x01u, 0x01u);
        require(
            (invalidAlphaReadiness.unsupported &
             FixedFunctionUnsupportedAlphaOp) != 0,
            "D3DTOP_MODULATEALPHA_ADDCOLOR must remain fail-closed as ALPHAOP");
    }

    {
        std::array<FixedFunctionStageState, 8> modulateColorAddAlphaStages{};
        modulateColorAddAlphaStages[0].colorOp =
            D3DTOP_MODULATECOLOR_ADDALPHA;
        modulateColorAddAlphaStages[0].colorArg1 = D3DTA_TEXTURE;
        modulateColorAddAlphaStages[0].colorArg2 = D3DTA_DIFFUSE;
        modulateColorAddAlphaStages[0].alphaOp = D3DTOP_SELECTARG1;
        modulateColorAddAlphaStages[0].alphaArg1 = D3DTA_DIFFUSE;
        modulateColorAddAlphaStages[0].alphaArg2 = D3DTA_CURRENT;
        modulateColorAddAlphaStages[0].minFilter = D3DTEXF_POINT;
        modulateColorAddAlphaStages[0].magFilter = D3DTEXF_POINT;
        modulateColorAddAlphaStages[0].mipFilter = D3DTEXF_NONE;

        const auto modulateColorAddAlphaShader =
            generate_fixed_function_pixel_shader_prototype(
                modulateColorAddAlphaStages, true, 0x01u, 0x01u,
                textureTypes);
        require(
            modulateColorAddAlphaShader.generated() &&
                modulateColorAddAlphaShader.activeStages == 1,
            "R188 D3DTOP_MODULATECOLOR_ADDALPHA COLOROP must become shader-exact");
        require(
            modulateColorAddAlphaShader.source.find(
                "float3 nextColor = sampled0.rgb * input.diffuse.rgb + sampled0.a;") !=
                std::string::npos &&
            modulateColorAddAlphaShader.source.find(
                "float nextAlpha = input.diffuse.a;") !=
                std::string::npos,
            "R188 D3DTOP_MODULATECOLOR_ADDALPHA shader expression drift");
        const auto modulateColorAddAlphaCompile =
            compile_fixed_function_pixel_shader_prototype(
                modulateColorAddAlphaShader);
        require(
            modulateColorAddAlphaCompile.attempted &&
            modulateColorAddAlphaCompile.succeeded &&
            modulateColorAddAlphaCompile.result == S_OK &&
            modulateColorAddAlphaCompile.bytecodeBytes != 0,
            "R188 D3DTOP_MODULATECOLOR_ADDALPHA fixed-function shader prototype did not compile");

        auto invalidAlphaStages = modulateColorAddAlphaStages;
        invalidAlphaStages[0].colorOp = D3DTOP_SELECTARG1;
        invalidAlphaStages[0].colorArg1 = D3DTA_DIFFUSE;
        invalidAlphaStages[0].alphaOp =
            D3DTOP_MODULATECOLOR_ADDALPHA;
        invalidAlphaStages[0].alphaArg1 = D3DTA_TEXTURE;
        invalidAlphaStages[0].alphaArg2 = D3DTA_DIFFUSE;
        const auto invalidAlphaReadiness =
            translate_fixed_function_readiness(
                invalidAlphaStages, true, 0x01u, 0x01u);
        require(
            (invalidAlphaReadiness.unsupported &
             FixedFunctionUnsupportedAlphaOp) != 0,
            "R188 D3DTOP_MODULATECOLOR_ADDALPHA must remain fail-closed as ALPHAOP");
    }

    {
        std::array<FixedFunctionStageState, 8> modulateInvAlphaAddColorStages{};
        modulateInvAlphaAddColorStages[0].colorOp =
            D3DTOP_MODULATEINVALPHA_ADDCOLOR;
        modulateInvAlphaAddColorStages[0].colorArg1 = D3DTA_TEXTURE;
        modulateInvAlphaAddColorStages[0].colorArg2 = D3DTA_DIFFUSE;
        modulateInvAlphaAddColorStages[0].alphaOp = D3DTOP_SELECTARG1;
        modulateInvAlphaAddColorStages[0].alphaArg1 = D3DTA_DIFFUSE;
        modulateInvAlphaAddColorStages[0].alphaArg2 = D3DTA_CURRENT;
        modulateInvAlphaAddColorStages[0].minFilter = D3DTEXF_POINT;
        modulateInvAlphaAddColorStages[0].magFilter = D3DTEXF_POINT;
        modulateInvAlphaAddColorStages[0].mipFilter = D3DTEXF_NONE;

        const auto modulateInvAlphaAddColorShader =
            generate_fixed_function_pixel_shader_prototype(
                modulateInvAlphaAddColorStages, true, 0x01u, 0x01u,
                textureTypes);
        require(
            modulateInvAlphaAddColorShader.generated() &&
                modulateInvAlphaAddColorShader.activeStages == 1,
            "R189 D3DTOP_MODULATEINVALPHA_ADDCOLOR COLOROP must become shader-exact");
        require(
            modulateInvAlphaAddColorShader.source.find(
                "float3 nextColor = sampled0.rgb + (1.0 - sampled0.a) * input.diffuse.rgb;") !=
                std::string::npos &&
            modulateInvAlphaAddColorShader.source.find(
                "float nextAlpha = input.diffuse.a;") !=
                std::string::npos,
            "R189 D3DTOP_MODULATEINVALPHA_ADDCOLOR shader expression drift");
        const auto modulateInvAlphaAddColorCompile =
            compile_fixed_function_pixel_shader_prototype(
                modulateInvAlphaAddColorShader);
        require(
            modulateInvAlphaAddColorCompile.attempted &&
            modulateInvAlphaAddColorCompile.succeeded &&
            modulateInvAlphaAddColorCompile.result == S_OK &&
            modulateInvAlphaAddColorCompile.bytecodeBytes != 0,
            "R189 D3DTOP_MODULATEINVALPHA_ADDCOLOR fixed-function shader prototype did not compile");

        auto invalidAlphaStages = modulateInvAlphaAddColorStages;
        invalidAlphaStages[0].colorOp = D3DTOP_SELECTARG1;
        invalidAlphaStages[0].colorArg1 = D3DTA_DIFFUSE;
        invalidAlphaStages[0].alphaOp =
            D3DTOP_MODULATEINVALPHA_ADDCOLOR;
        invalidAlphaStages[0].alphaArg1 = D3DTA_TEXTURE;
        invalidAlphaStages[0].alphaArg2 = D3DTA_DIFFUSE;
        const auto invalidAlphaReadiness =
            translate_fixed_function_readiness(
                invalidAlphaStages, true, 0x01u, 0x01u);
        require(
            (invalidAlphaReadiness.unsupported &
             FixedFunctionUnsupportedAlphaOp) != 0,
            "R189 D3DTOP_MODULATEINVALPHA_ADDCOLOR must remain fail-closed as ALPHAOP");
    }

    {
        std::array<FixedFunctionStageState, 8> modulateInvColorAddAlphaStages{};
        modulateInvColorAddAlphaStages[0].colorOp =
            D3DTOP_MODULATEINVCOLOR_ADDALPHA;
        modulateInvColorAddAlphaStages[0].colorArg1 = D3DTA_TEXTURE;
        modulateInvColorAddAlphaStages[0].colorArg2 = D3DTA_DIFFUSE;
        modulateInvColorAddAlphaStages[0].alphaOp = D3DTOP_SELECTARG1;
        modulateInvColorAddAlphaStages[0].alphaArg1 = D3DTA_DIFFUSE;
        modulateInvColorAddAlphaStages[0].alphaArg2 = D3DTA_CURRENT;
        modulateInvColorAddAlphaStages[0].minFilter = D3DTEXF_POINT;
        modulateInvColorAddAlphaStages[0].magFilter = D3DTEXF_POINT;
        modulateInvColorAddAlphaStages[0].mipFilter = D3DTEXF_NONE;

        const auto modulateInvColorAddAlphaShader =
            generate_fixed_function_pixel_shader_prototype(
                modulateInvColorAddAlphaStages, true, 0x01u, 0x01u,
                textureTypes);
        require(
            modulateInvColorAddAlphaShader.generated() &&
                modulateInvColorAddAlphaShader.activeStages == 1,
            "R190 D3DTOP_MODULATEINVCOLOR_ADDALPHA COLOROP must become shader-exact");
        require(
            modulateInvColorAddAlphaShader.source.find(
                "float3 nextColor = (1.0 - sampled0.rgb) * input.diffuse.rgb + sampled0.a;") !=
                std::string::npos &&
            modulateInvColorAddAlphaShader.source.find(
                "float nextAlpha = input.diffuse.a;") !=
                std::string::npos,
            "R190 D3DTOP_MODULATEINVCOLOR_ADDALPHA shader expression drift");
        const auto modulateInvColorAddAlphaCompile =
            compile_fixed_function_pixel_shader_prototype(
                modulateInvColorAddAlphaShader);
        require(
            modulateInvColorAddAlphaCompile.attempted &&
            modulateInvColorAddAlphaCompile.succeeded &&
            modulateInvColorAddAlphaCompile.result == S_OK &&
            modulateInvColorAddAlphaCompile.bytecodeBytes != 0,
            "R190 D3DTOP_MODULATEINVCOLOR_ADDALPHA fixed-function shader prototype did not compile");

        auto invalidAlphaStages = modulateInvColorAddAlphaStages;
        invalidAlphaStages[0].colorOp = D3DTOP_SELECTARG1;
        invalidAlphaStages[0].colorArg1 = D3DTA_DIFFUSE;
        invalidAlphaStages[0].alphaOp =
            D3DTOP_MODULATEINVCOLOR_ADDALPHA;
        invalidAlphaStages[0].alphaArg1 = D3DTA_TEXTURE;
        invalidAlphaStages[0].alphaArg2 = D3DTA_DIFFUSE;
        const auto invalidAlphaReadiness =
            translate_fixed_function_readiness(
                invalidAlphaStages, true, 0x01u, 0x01u);
        require(
            (invalidAlphaReadiness.unsupported &
             FixedFunctionUnsupportedAlphaOp) != 0,
            "R190 D3DTOP_MODULATEINVCOLOR_ADDALPHA must remain fail-closed as ALPHAOP");
    }

    {
        std::array<FixedFunctionStageState, 8> dotProductStages{};
        dotProductStages[0].colorOp = D3DTOP_DOTPRODUCT3;
        dotProductStages[0].colorArg1 = D3DTA_TEXTURE;
        dotProductStages[0].colorArg2 = D3DTA_DIFFUSE;
        dotProductStages[0].alphaOp = D3DTOP_DOTPRODUCT3;
        dotProductStages[0].alphaArg1 = D3DTA_TEXTURE;
        dotProductStages[0].alphaArg2 = D3DTA_DIFFUSE;
        dotProductStages[0].minFilter = D3DTEXF_POINT;
        dotProductStages[0].magFilter = D3DTEXF_POINT;
        dotProductStages[0].mipFilter = D3DTEXF_NONE;

        const auto dotProductShader =
            generate_fixed_function_pixel_shader_prototype(
                dotProductStages, true, 0x01u, 0x01u, textureTypes);
        require(
            dotProductShader.generated() &&
                dotProductShader.activeStages == 1,
            "R193 D3DTOP_DOTPRODUCT3 COLOROP/ALPHAOP must become shader-exact");
        require(
            dotProductShader.source.find(
                "float3 nextColor = dot((sampled0.rgb * 2.0 - 1.0), (input.diffuse.rgb * 2.0 - 1.0));") !=
                std::string::npos &&
            dotProductShader.source.find(
                "float nextAlpha = dot((sampled0.rgb * 2.0 - 1.0), (input.diffuse.rgb * 2.0 - 1.0));") !=
                std::string::npos,
            "R193 D3DTOP_DOTPRODUCT3 signed RGB dot-product shader expression drift");

        const auto dotProductCompile =
            compile_fixed_function_pixel_shader_prototype(dotProductShader);
        require(
            dotProductCompile.attempted &&
            dotProductCompile.succeeded &&
            dotProductCompile.result == S_OK &&
            dotProductCompile.bytecodeBytes != 0,
            "R193 D3DTOP_DOTPRODUCT3 fixed-function shader prototype did not compile");

        const auto missingTextureReadiness =
            translate_fixed_function_readiness(
                dotProductStages, true, 0x00u, 0x00u);
        require(
            (missingTextureReadiness.unsupported &
             FixedFunctionUnsupportedResourceStageCoverage) != 0,
            "R193 D3DTOP_DOTPRODUCT3 texture dependency must fail closed without exact resource coverage");
    }


    // R201 made D3DTA_TEMP a supported default-zero source. Keep the older
    // R194/R196 negative ARG0 probes on a selector value that is actually
    // outside the D3DTA source enum while still inside D3DTA_SELECTMASK.
    constexpr DWORD invalidArgumentSelector =
        static_cast<DWORD>(D3DTA_SELECTMASK);

    {
        std::array<FixedFunctionStageState, 8> multiplyAddStages{};
        multiplyAddStages[0].colorOp = D3DTOP_MULTIPLYADD;
        multiplyAddStages[0].colorArg0 = D3DTA_TEXTURE;
        multiplyAddStages[0].colorArg1 = D3DTA_DIFFUSE;
        multiplyAddStages[0].colorArg2 = D3DTA_TFACTOR;
        multiplyAddStages[0].alphaOp = D3DTOP_MULTIPLYADD;
        multiplyAddStages[0].alphaArg0 = D3DTA_TEXTURE;
        multiplyAddStages[0].alphaArg1 = D3DTA_DIFFUSE;
        multiplyAddStages[0].alphaArg2 = D3DTA_TFACTOR;
        multiplyAddStages[0].minFilter = D3DTEXF_POINT;
        multiplyAddStages[0].magFilter = D3DTEXF_POINT;
        multiplyAddStages[0].mipFilter = D3DTEXF_NONE;

        constexpr DWORD multiplyAddFactor = 0x80402010u;
        const auto multiplyAddShader =
            generate_fixed_function_pixel_shader_prototype(
                multiplyAddStages, true, 0x01u, 0x01u, textureTypes,
                FixedFunctionAlphaTestState{}, multiplyAddFactor);
        require(
            multiplyAddShader.generated() &&
                multiplyAddShader.activeStages == 1,
            "R194 D3DTOP_MULTIPLYADD ARG0 fixture must become shader-exact");
        require(
            multiplyAddShader.source.find(
                "float3 nextColor = input.diffuse.rgb + float4(64.0f / 255.0f, 32.0f / 255.0f, 16.0f / 255.0f, 128.0f / 255.0f).rgb * sampled0.rgb;") !=
                std::string::npos &&
            multiplyAddShader.source.find(
                "float nextAlpha = input.diffuse.a + float4(64.0f / 255.0f, 32.0f / 255.0f, 16.0f / 255.0f, 128.0f / 255.0f).a * sampled0.a;") !=
                std::string::npos,
            "R194 D3DTOP_MULTIPLYADD Arg1 + Arg2 * Arg0 expression drift");

        const auto multiplyAddCompile =
            compile_fixed_function_pixel_shader_prototype(multiplyAddShader);
        require(
            multiplyAddCompile.attempted &&
            multiplyAddCompile.succeeded &&
            multiplyAddCompile.result == S_OK &&
            multiplyAddCompile.bytecodeBytes != 0,
            "R194 D3DTOP_MULTIPLYADD fixed-function shader prototype did not compile");

        const auto missingArg0Texture =
            translate_fixed_function_readiness(
                multiplyAddStages, true, 0x00u, 0x00u);
        require(
            (missingArg0Texture.unsupported &
             FixedFunctionUnsupportedResourceStageCoverage) != 0,
            "R194 D3DTOP_MULTIPLYADD ARG0 texture dependency must fail closed");

        auto unsupportedArg0Stages = multiplyAddStages;
        unsupportedArg0Stages[0].colorArg0 = invalidArgumentSelector;
        const auto unsupportedArg0 =
            translate_fixed_function_readiness(
                unsupportedArg0Stages, true, 0x01u, 0x01u);
        require(
            (unsupportedArg0.unsupported &
             FixedFunctionUnsupportedArgument) != 0,
            "R194 D3DTOP_MULTIPLYADD unsupported ARG0 selector must fail closed");
    }



    {
        std::array<FixedFunctionStageState, 8> lerpStages{};
        lerpStages[0].colorOp = D3DTOP_LERP;
        lerpStages[0].colorArg0 = D3DTA_TEXTURE;
        lerpStages[0].colorArg1 = D3DTA_DIFFUSE;
        lerpStages[0].colorArg2 = D3DTA_TFACTOR;
        lerpStages[0].alphaOp = D3DTOP_LERP;
        lerpStages[0].alphaArg0 = D3DTA_TEXTURE;
        lerpStages[0].alphaArg1 = D3DTA_DIFFUSE;
        lerpStages[0].alphaArg2 = D3DTA_TFACTOR;
        lerpStages[0].minFilter = D3DTEXF_POINT;
        lerpStages[0].magFilter = D3DTEXF_POINT;
        lerpStages[0].mipFilter = D3DTEXF_NONE;

        constexpr DWORD lerpFactor = 0x80402010u;
        const auto lerpShader =
            generate_fixed_function_pixel_shader_prototype(
                lerpStages, true, 0x01u, 0x01u, textureTypes,
                FixedFunctionAlphaTestState{}, lerpFactor);
        require(
            lerpShader.generated() && lerpShader.activeStages == 1,
            "R196 D3DTOP_LERP ARG0 fixture must become shader-exact");
        require(
            lerpShader.source.find(
                "float3 nextColor = input.diffuse.rgb * sampled0.rgb + float4(64.0f / 255.0f, 32.0f / 255.0f, 16.0f / 255.0f, 128.0f / 255.0f).rgb * (1.0 - sampled0.rgb);") !=
                std::string::npos &&
            lerpShader.source.find(
                "float nextAlpha = input.diffuse.a * sampled0.a + float4(64.0f / 255.0f, 32.0f / 255.0f, 16.0f / 255.0f, 128.0f / 255.0f).a * (1.0 - sampled0.a);") !=
                std::string::npos,
            "R196 D3DTOP_LERP Arg1*Arg0 + Arg2*(1-Arg0) expression drift");

        const auto lerpCompile =
            compile_fixed_function_pixel_shader_prototype(lerpShader);
        require(
            lerpCompile.attempted &&
            lerpCompile.succeeded &&
            lerpCompile.result == S_OK &&
            lerpCompile.bytecodeBytes != 0,
            "R196 D3DTOP_LERP fixed-function shader prototype did not compile");

        const auto missingLerpTexture =
            translate_fixed_function_readiness(
                lerpStages, true, 0x00u, 0x00u);
        require(
            (missingLerpTexture.unsupported &
             FixedFunctionUnsupportedResourceStageCoverage) != 0,
            "R196 D3DTOP_LERP ARG0 texture dependency must fail closed");

        auto unsupportedLerpArg0 = lerpStages;
        unsupportedLerpArg0[0].colorArg0 = invalidArgumentSelector;
        const auto invalidLerpArg0 =
            translate_fixed_function_readiness(
                unsupportedLerpArg0, true, 0x01u, 0x01u);
        require(
            (invalidLerpArg0.unsupported &
             FixedFunctionUnsupportedArgument) != 0,
            "R196 D3DTOP_LERP unsupported ARG0 selector must fail closed");
    }

    {
        std::array<FixedFunctionStageState, 8> stageConstantStages{};
        stageConstantStages[0].colorOp = D3DTOP_SELECTARG1;
        stageConstantStages[0].colorArg1 = D3DTA_CONSTANT;
        stageConstantStages[0].alphaOp = D3DTOP_SELECTARG1;
        stageConstantStages[0].alphaArg1 = D3DTA_CONSTANT;
        stageConstantStages[0].stageConstant = 0x80402010u;
        stageConstantStages[0].minFilter = D3DTEXF_POINT;
        stageConstantStages[0].magFilter = D3DTEXF_POINT;
        stageConstantStages[0].mipFilter = D3DTEXF_NONE;

        const auto stageConstantShader =
            generate_fixed_function_pixel_shader_prototype(
                stageConstantStages, true, 0x00u, 0x00u, textureTypes);
        require(
            stageConstantShader.generated() &&
                stageConstantShader.activeStages == 1,
            "R197 D3DTA_CONSTANT must become shader-exact without a bound texture");
        require(
            stageConstantShader.source.find(
                "float3 nextColor = float4(64.0f / 255.0f, 32.0f / 255.0f, 16.0f / 255.0f, 128.0f / 255.0f).rgb;") !=
                std::string::npos &&
            stageConstantShader.source.find(
                "float nextAlpha = float4(64.0f / 255.0f, 32.0f / 255.0f, 16.0f / 255.0f, 128.0f / 255.0f).a;") !=
                std::string::npos,
            "R197 D3DTA_CONSTANT ARGB-to-RGBA normalization drift");

        const auto stageConstantCompile =
            compile_fixed_function_pixel_shader_prototype(stageConstantShader);
        require(
            stageConstantCompile.attempted &&
            stageConstantCompile.succeeded &&
            stageConstantCompile.result == S_OK &&
            stageConstantCompile.bytecodeBytes != 0,
            "R197 D3DTA_CONSTANT fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stageConstantStages{};
        stageConstantStages[0].colorOp = D3DTOP_SELECTARG1;
        stageConstantStages[0].colorArg1 = D3DTA_CONSTANT;
        stageConstantStages[0].alphaOp = D3DTOP_SELECTARG1;
        stageConstantStages[0].alphaArg1 = D3DTA_CONSTANT;
        stageConstantStages[0].stageConstant = 0x80402010u;
        stageConstantStages[0].minFilter = D3DTEXF_POINT;
        stageConstantStages[0].magFilter = D3DTEXF_POINT;
        stageConstantStages[0].mipFilter = D3DTEXF_NONE;

        stageConstantStages[1].colorOp = D3DTOP_ADD;
        stageConstantStages[1].colorArg1 = D3DTA_CURRENT;
        stageConstantStages[1].colorArg2 = D3DTA_CONSTANT;
        stageConstantStages[1].alphaOp = D3DTOP_ADD;
        stageConstantStages[1].alphaArg1 = D3DTA_CURRENT;
        stageConstantStages[1].alphaArg2 = D3DTA_CONSTANT;
        stageConstantStages[1].stageConstant = 0xFF102030u;
        stageConstantStages[1].minFilter = D3DTEXF_POINT;
        stageConstantStages[1].magFilter = D3DTEXF_POINT;
        stageConstantStages[1].mipFilter = D3DTEXF_NONE;

        const auto stageConstantShader =
            generate_fixed_function_pixel_shader_prototype(
                stageConstantStages, true, 0x00u, 0x00u, textureTypes);
        require(
            stageConstantShader.generated() &&
                stageConstantShader.activeStages == 2,
            "R197 D3DTA_CONSTANT per-stage fixture must become shader-exact");
        require(
            stageConstantShader.source.find(
                "float3 nextColor = float4(64.0f / 255.0f, 32.0f / 255.0f, 16.0f / 255.0f, 128.0f / 255.0f).rgb;") !=
                std::string::npos &&
            stageConstantShader.source.find(
                "float nextAlpha = float4(64.0f / 255.0f, 32.0f / 255.0f, 16.0f / 255.0f, 128.0f / 255.0f).a;") !=
                std::string::npos &&
            stageConstantShader.source.find(
                "float3 nextColor = current.rgb + float4(16.0f / 255.0f, 32.0f / 255.0f, 48.0f / 255.0f, 255.0f / 255.0f).rgb;") !=
                std::string::npos &&
            stageConstantShader.source.find(
                "float nextAlpha = current.a + float4(16.0f / 255.0f, 32.0f / 255.0f, 48.0f / 255.0f, 255.0f / 255.0f).a;") !=
                std::string::npos,
            "R197 D3DTSS_CONSTANT must preserve independent per-stage ARGB values");

        const auto stageConstantCompile =
            compile_fixed_function_pixel_shader_prototype(stageConstantShader);
        require(
            stageConstantCompile.attempted &&
                stageConstantCompile.succeeded &&
                stageConstantCompile.result == S_OK &&
                stageConstantCompile.bytecodeBytes != 0,
            "R197 D3DTA_CONSTANT fixed-function shader prototype did not compile");
    }


    {
        std::array<FixedFunctionStageState, 8> textureFactorStages{};
        textureFactorStages[0].colorOp = D3DTOP_SELECTARG1;
        textureFactorStages[0].colorArg1 = D3DTA_TFACTOR;
        textureFactorStages[0].alphaOp = D3DTOP_SELECTARG1;
        textureFactorStages[0].alphaArg1 = D3DTA_TFACTOR;
        textureFactorStages[0].minFilter = D3DTEXF_POINT;
        textureFactorStages[0].magFilter = D3DTEXF_POINT;
        textureFactorStages[0].mipFilter = D3DTEXF_NONE;

        constexpr DWORD textureFactor = 0x80654321u;
        const auto textureFactorShader =
            generate_fixed_function_pixel_shader_prototype(
                textureFactorStages, true, 0x00u, 0x00u,
                textureTypes, FixedFunctionAlphaTestState{}, textureFactor);
        require(
            textureFactorShader.generated() &&
                textureFactorShader.activeStages == 1,
            "R191 D3DTA_TFACTOR argument must become shader-exact without a bound texture");
        require(
            textureFactorShader.source.find(
                "float3 nextColor = float4(101.0f / 255.0f, 67.0f / 255.0f, 33.0f / 255.0f, 128.0f / 255.0f).rgb;") !=
                std::string::npos &&
            textureFactorShader.source.find(
                "float nextAlpha = float4(101.0f / 255.0f, 67.0f / 255.0f, 33.0f / 255.0f, 128.0f / 255.0f).a;") !=
                std::string::npos,
            "R191 D3DTA_TFACTOR ARGB-to-RGBA normalization drift");

        std::array<FixedFunctionStageState, 8> blendFactorAlphaStages{};
        blendFactorAlphaStages[0].colorOp = D3DTOP_BLENDFACTORALPHA;
        blendFactorAlphaStages[0].colorArg1 = D3DTA_TEXTURE;
        blendFactorAlphaStages[0].colorArg2 = D3DTA_DIFFUSE;
        blendFactorAlphaStages[0].alphaOp = D3DTOP_BLENDFACTORALPHA;
        blendFactorAlphaStages[0].alphaArg1 = D3DTA_TEXTURE;
        blendFactorAlphaStages[0].alphaArg2 = D3DTA_DIFFUSE;
        blendFactorAlphaStages[0].minFilter = D3DTEXF_POINT;
        blendFactorAlphaStages[0].magFilter = D3DTEXF_POINT;
        blendFactorAlphaStages[0].mipFilter = D3DTEXF_NONE;

        const auto blendFactorAlphaShader =
            generate_fixed_function_pixel_shader_prototype(
                blendFactorAlphaStages, true, 0x01u, 0x01u,
                textureTypes, FixedFunctionAlphaTestState{}, textureFactor);
        require(
            blendFactorAlphaShader.generated() &&
                blendFactorAlphaShader.activeStages == 1,
            "R191 D3DTOP_BLENDFACTORALPHA operation must become shader-exact");
        require(
            blendFactorAlphaShader.source.find(
                "float3 nextColor = sampled0.rgb * (128.0f / 255.0f) + input.diffuse.rgb * (1.0 - (128.0f / 255.0f));") !=
                std::string::npos &&
            blendFactorAlphaShader.source.find(
                "float nextAlpha = sampled0.a * (128.0f / 255.0f) + input.diffuse.a * (1.0 - (128.0f / 255.0f));") !=
                std::string::npos,
            "R191 D3DTOP_BLENDFACTORALPHA interpolation drift");
        const auto blendFactorAlphaCompile =
            compile_fixed_function_pixel_shader_prototype(
                blendFactorAlphaShader);
        require(
            blendFactorAlphaCompile.attempted &&
            blendFactorAlphaCompile.succeeded &&
            blendFactorAlphaCompile.result == S_OK &&
            blendFactorAlphaCompile.bytecodeBytes != 0,
            "R191 texture-factor fixed-function shader prototype did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> premodulateStages{};
        premodulateStages[0].colorOp = D3DTOP_PREMODULATE;
        premodulateStages[0].colorArg1 = D3DTA_DIFFUSE;
        premodulateStages[0].alphaOp = D3DTOP_PREMODULATE;
        premodulateStages[0].alphaArg1 = D3DTA_DIFFUSE;
        premodulateStages[0].minFilter = D3DTEXF_POINT;
        premodulateStages[0].magFilter = D3DTEXF_POINT;
        premodulateStages[0].mipFilter = D3DTEXF_NONE;

        premodulateStages[1].colorOp = D3DTOP_SELECTARG1;
        premodulateStages[1].colorArg1 = D3DTA_CURRENT;
        premodulateStages[1].alphaOp = D3DTOP_SELECTARG1;
        premodulateStages[1].alphaArg1 = D3DTA_CURRENT;
        premodulateStages[1].minFilter = D3DTEXF_POINT;
        premodulateStages[1].magFilter = D3DTEXF_POINT;
        premodulateStages[1].mipFilter = D3DTEXF_NONE;

        const auto premodulateShader =
            generate_fixed_function_pixel_shader_prototype(
                premodulateStages, true, 0x02u, 0x02u, textureTypes);
        require(
            premodulateShader.generated() &&
                premodulateShader.activeStages == 2,
            "R195 D3DTOP_PREMODULATE two-stage fixture must become shader-exact");
        require(
            premodulateShader.source.find(
                "Texture2D texture1 : register(t1);") != std::string::npos &&
            premodulateShader.source.find(
                "float3 nextColor = (current * sampled1).rgb;") !=
                std::string::npos &&
            premodulateShader.source.find(
                "float nextAlpha = (current * sampled1).a;") !=
                std::string::npos,
            "R195 D3DTOP_PREMODULATE must premultiply next-stage CURRENT by its bound texture");

        const auto premodulateCompile =
            compile_fixed_function_pixel_shader_prototype(premodulateShader);
        require(
            premodulateCompile.attempted &&
            premodulateCompile.succeeded &&
            premodulateCompile.result == S_OK &&
            premodulateCompile.bytecodeBytes != 0,
            "R195 D3DTOP_PREMODULATE fixed-function shader prototype did not compile");

        const auto inexactNextTexture =
            translate_fixed_function_readiness(
                premodulateStages, true, 0x02u, 0x00u);
        require(
            (inexactNextTexture.unsupported &
             FixedFunctionUnsupportedResourceStageCoverage) != 0,
            "R195 PREMODULATE implicit next-stage texture dependency must fail closed when inexact");

        const auto noNextTextureShader =
            generate_fixed_function_pixel_shader_prototype(
                premodulateStages, true, 0x00u, 0x00u, textureTypes);
        require(
            noNextTextureShader.generated() &&
            noNextTextureShader.source.find("Texture2D texture1") ==
                std::string::npos &&
            noNextTextureShader.source.find(
                "float3 nextColor = current.rgb;") != std::string::npos &&
            noNextTextureShader.source.find(
                "float nextAlpha = current.a;") != std::string::npos,
            "R195 PREMODULATE must leave next-stage CURRENT unchanged when no texture is bound");
    }


    {
        std::array<FixedFunctionStageState, 8> specularStages{};
        specularStages[0].colorOp = D3DTOP_SELECTARG1;
        specularStages[0].colorArg1 = D3DTA_SPECULAR;
        specularStages[0].alphaOp = D3DTOP_SELECTARG1;
        specularStages[0].alphaArg1 = D3DTA_SPECULAR;
        specularStages[0].minFilter = D3DTEXF_POINT;
        specularStages[0].magFilter = D3DTEXF_POINT;
        specularStages[0].mipFilter = D3DTEXF_NONE;

        const auto specularShader =
            generate_fixed_function_pixel_shader_prototype(
                specularStages, true, 0x00u, 0x00u, textureTypes);
        require(
            specularShader.generated() &&
                specularShader.activeStages == 1,
            "R198 D3DTA_SPECULAR selector must become shader-exact");
        require(
            specularShader.source.find(
                "float3 nextColor = input.specular.rgb;") !=
                std::string::npos &&
            specularShader.source.find(
                "float nextAlpha = input.specular.a;") !=
                std::string::npos,
            "R198 D3DTA_SPECULAR COLOR1 shader expression drift");
        const auto specularCompile =
            compile_fixed_function_pixel_shader_prototype(specularShader);
        require(
            specularCompile.attempted &&
            specularCompile.succeeded &&
            specularCompile.result == S_OK &&
            specularCompile.bytecodeBytes != 0,
            "R198 D3DTA_SPECULAR fixed-function shader prototype did not compile");
    }

    std::cout
        << "DX11 fixed-function D3DTA_SPECULAR support R198: PASS\n"
        << "DX11 fixed-function D3DTA_CONSTANT per-stage support R197: PASS\n"
        << "DX11 fixed-function D3DTA_CONSTANT per-stage color R197: PASS\n"
        << "DX11 fixed-function D3DTOP_LERP ARG0 support R196: PASS\n"
        << "DX11 fixed-function PREMODULATE stage-chain support R195: PASS\n"
        << "DX11 fixed-function D3DTOP_MULTIPLYADD ARG0 support R194: PASS\n"
        << "DX11 fixed-function texture-factor consumption R191: PASS\n"
        << "DX11 fixed-function D3DTOP_DOTPRODUCT3 support R193: PASS\n"
        << "DX11 fixed-function D3DTOP_MODULATEINVCOLOR_ADDALPHA COLOROP support R190: PASS\n"
        << "DX11 fixed-function D3DTOP_MODULATEINVALPHA_ADDCOLOR COLOROP support R189: PASS\n"
        << "DX11 fixed-function D3DTOP_MODULATECOLOR_ADDALPHA COLOROP support R188: PASS\n"
        << "DX11 fixed-function D3DTOP_MODULATEALPHA_ADDCOLOR COLOROP support: PASS\n"
        << "DX11 fixed-function D3DTOP_BLENDTEXTUREALPHAPM support R187: PASS\n"
        << "DX11 fixed-function D3DTOP_BLENDTEXTUREALPHA support R186: PASS\n"
        << "DX11 fixed-function D3DTOP_BLENDDIFFUSEALPHA support R185: PASS\n"
        << "DX11 fixed-function D3DTOP_ADDSMOOTH support R184: PASS\n"
        << "DX11 fixed-function D3DTOP_ADDSIGNED2X support R183: PASS\n"
        << "DX11 MRT color-write fail-closed: PASS\n"
        << "DX11 fixed-function D3DTOP_BLENDCURRENTALPHA support: PASS\n"
        << "DX11 fixed-function D3DTOP_ADDSIGNED support R182: PASS\n"
        << "DX11 fixed-function D3DTOP_MODULATE4X support R181: PASS\n"
        << "DX11 fixed-function D3DTOP_MODULATE2X support R180: PASS\n"
        << "DX11 fixed-function D3DTOP_SUBTRACT support R177: PASS\n"
        << "DX11 fixed-function argument modifiers R178: PASS\n"
        << "DX11 fixed-function D3DTOP_ADD support: PASS\n"
        << "DX11 fixed-function TEMP default-zero semantics R201: PASS\n"
        << "DX11 multisample raster provenance R171: PASS\n"
        << "DX11 texture-coordinate wrap fail-closed R170: PASS\n"
        << "DX11 line-raster provenance R168: PASS\n"
        << "DX11 fixed-function dithering fail-closed R165: PASS\n"
        << "DX11 fixed-function vertex-blend fail-closed R163: PASS\n"
        << "DX11 fixed-function clipping fail-closed R161: PASS\n"
        << "DX11 fixed-function alpha-test pipeline handoff R118: PASS\n"
        << "DX11 fixed-function shade-mode fail-closed R162: PASS\n";
    return 0;
}
