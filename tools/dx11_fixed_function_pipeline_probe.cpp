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
        auto currentStages = stages;
        currentStages[0].colorOp = D3DTOP_SELECTARG1;
        currentStages[0].colorArg1 = D3DTA_DIFFUSE;
        currentStages[0].alphaOp = D3DTOP_SELECTARG1;
        currentStages[0].alphaArg1 = D3DTA_DIFFUSE;
        currentStages[0].resultArg = D3DTA_CURRENT;

        const auto currentReadiness = translate_fixed_function_readiness(
            currentStages, true, 0x00, 0x00);
        require(
            currentReadiness.exact() &&
            (currentReadiness.unsupported &
             FixedFunctionUnsupportedResultArg) == 0,
            "R173 default D3DTSS_RESULTARG CURRENT must remain exact");

        auto tempStages = currentStages;
        tempStages[0].resultArg = D3DTA_TEMP;
        const auto tempReadiness = translate_fixed_function_readiness(
            tempStages, true, 0x00, 0x00);
        require(
            !tempReadiness.exact() &&
            (tempReadiness.unsupported &
             FixedFunctionUnsupportedResultArg) != 0,
            "R173 D3DTSS_RESULTARG TEMP must fail closed");

        const auto tempPipeline =
            translate_fixed_function_pipeline_with_shader_semantics(
                base_state(), true, tempStages, true,
                0x00, 0x00, textureTypes);
        require(
            !tempPipeline.exact() &&
            !tempPipeline.pixelShader.generated() &&
            (tempPipeline.pixelShader.unsupported &
             FixedFunctionShaderPrototypeUnsupportedNotReady) != 0,
            "R173 TEMP result destination reached generated fixed-function HLSL");
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

    std::cout
        << "DX11 MRT color-write fail-closed: PASS\n"
        << "DX11 fixed-function D3DTOP_MODULATE2X support R180: PASS\n"
        << "DX11 fixed-function D3DTOP_SUBTRACT support R177: PASS\n"
        << "DX11 fixed-function argument modifiers R178: PASS\n"
        << "DX11 fixed-function D3DTOP_ADD support: PASS\n"
        << "DX11 fixed-function RESULTARG fail-closed R173: PASS\n"
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
