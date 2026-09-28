#include <array>
#include <cstdlib>
#include <iostream>
#include <string>

#include "vr/d3d11/pipeline_translation.hpp"

namespace
{
    using outrun::vr::dx11::FixedFunctionPixelShaderCompileProbe;
    using outrun::vr::dx11::FixedFunctionPixelShaderPrototype;
    using outrun::vr::dx11::FixedFunctionShaderPrototypeUnsupportedNotReady;
    using outrun::vr::dx11::FixedFunctionShaderPrototypeUnsupportedResourceType;
    using outrun::vr::dx11::FixedFunctionStageState;
    using outrun::vr::dx11::FixedFunctionUnsupportedArgument;
    using outrun::vr::dx11::FixedFunctionUnsupportedSamplerFilter;
    using outrun::vr::dx11::FixedFunctionUnsupportedStageChain;
    using outrun::vr::dx11::FixedFunctionUnsupportedTextureTransform;
    using outrun::vr::dx11::compile_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::translate_fixed_function_readiness;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R87 semantic smoke failure: " << message << '\n';
            std::exit(1);
        }
    }

    FixedFunctionStageState active_stage(
        DWORD colorOp,
        DWORD colorArg1,
        DWORD colorArg2,
        DWORD alphaOp,
        DWORD alphaArg1,
        DWORD alphaArg2,
        DWORD texCoordIndex)
    {
        FixedFunctionStageState stage{};
        stage.colorOp = colorOp;
        stage.colorArg1 = colorArg1;
        stage.colorArg2 = colorArg2;
        stage.alphaOp = alphaOp;
        stage.alphaArg1 = alphaArg1;
        stage.alphaArg2 = alphaArg2;
        stage.texCoordIndex = texCoordIndex;
        stage.textureTransformFlags = D3DTTFF_DISABLE;
        stage.minFilter = D3DTEXF_POINT;
        stage.magFilter = D3DTEXF_POINT;
        stage.mipFilter = D3DTEXF_NONE;
        stage.addressU = D3DTADDRESS_WRAP;
        stage.addressV = D3DTADDRESS_WRAP;
        return stage;
    }

    void require_compiles(
        const FixedFunctionPixelShaderPrototype& prototype,
        const char* label)
    {
        require(prototype.generated(), label);
        const FixedFunctionPixelShaderCompileProbe probe =
            compile_fixed_function_pixel_shader_prototype(prototype);
        require(probe.attempted, "compile probe was not attempted");
        require(probe.succeeded, "generated HLSL did not compile");
        require(probe.result == S_OK, "D3DCompile did not return S_OK");
        require(probe.bytecodeBytes > 0, "compiled bytecode is empty");
        require(probe.bytecodeHash != 0, "compiled bytecode hash is empty");
    }
}

int main()
{
    std::array<D3DRESOURCETYPE, 8> textureTypes{};
    textureTypes.fill(D3DRTYPE_TEXTURE);

    {
        std::array<FixedFunctionStageState, 8> stages{};
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x00, 0x00);
        require(readiness.exact(), "zero-stage readiness was not exact");
        require(readiness.activeStages == 0, "zero-stage active count drift");

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes);
        require(prototype.generated(), "zero-stage passthrough was not generated");
        require(prototype.activeStages == 0, "zero-stage prototype count drift");
        require(
            prototype.source.find("Texture2D texture") == std::string::npos,
            "zero-stage shader emitted a texture declaration");
        require(
            prototype.source.find("return current;") != std::string::npos,
            "zero-stage shader did not return diffuse current");
        require_compiles(prototype, "zero-stage passthrough compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            0);

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes);
        require(prototype.generated(), "diffuse passthrough was not generated");
        require(
            prototype.source.find(
                "float3 nextColor = input.diffuse.rgb;") != std::string::npos,
            "diffuse color semantic drift");
        require(
            prototype.source.find(
                "float nextAlpha = input.diffuse.a;") != std::string::npos,
            "diffuse alpha semantic drift");
        require(
            prototype.source.find("Texture2D texture") == std::string::npos,
            "texture declaration emitted for texture-free stage");
        require_compiles(prototype, "diffuse passthrough compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_TEXTURE,
            D3DTA_DIFFUSE,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, textureTypes);
        require(prototype.generated(), "single texture modulate was not generated");
        require(
            prototype.source.find(
                "float4 sampled0 = texture0.Sample(sampler0, input.tex0.xy);") !=
                std::string::npos,
            "stage0 texture sample semantic drift");
        require(
            prototype.source.find(
                "float3 nextColor = sampled0.rgb * input.diffuse.rgb;") !=
                std::string::npos,
            "stage0 modulate semantic drift");
        require(
            prototype.source.find(
                "float nextAlpha = sampled0.a;") != std::string::npos,
            "stage0 texture alpha semantic drift");
        require_compiles(prototype, "single texture modulate compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_TEXTURE,
            D3DTA_DIFFUSE,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[1] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            D3DTOP_SELECTARG1,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            1);

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x03, 0x03, textureTypes);
        require(prototype.generated(), "two-stage chain was not generated");
        require(
            prototype.source.find(
                "float4 sampled1 = texture1.Sample(sampler1, input.tex1.xy);") !=
                std::string::npos,
            "stage1 texture sample semantic drift");
        require(
            prototype.source.find(
                "float3 nextColor = current.rgb * sampled1.rgb;") !=
                std::string::npos,
            "stage1 CURRENT chaining semantic drift");
        require(
            prototype.source.find(
                "float nextAlpha = current.a;") != std::string::npos,
            "stage1 CURRENT alpha semantic drift");
        require_compiles(prototype, "two-stage chain compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_TEXTURE,
            D3DTA_DIFFUSE,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[1] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            D3DTOP_SELECTARG1,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            1);
        stages[2] = active_stage(
            D3DTOP_SELECTARG2,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            D3DTOP_SELECTARG2,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            5);
        stages[2].minFilter = D3DTEXF_LINEAR;
        stages[2].magFilter = D3DTEXF_LINEAR;
        stages[2].mipFilter = D3DTEXF_LINEAR;
        stages[2].addressU = D3DTADDRESS_CLAMP;
        stages[2].addressV = D3DTADDRESS_CLAMP;

        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x07, 0x07);
        require(readiness.exact(), "stage2 SELECTARG2 readiness was not exact");
        require(readiness.activeStages == 3, "stage2 active count drift");

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x07, 0x07, textureTypes);
        require(prototype.generated(), "stage2 SELECTARG2 chain was not generated");
        require(
            prototype.source.find(
                "Texture2D texture2 : register(t2);") != std::string::npos,
            "stage2 texture register semantic drift");
        require(
            prototype.source.find(
                "float4 sampled2 = texture2.Sample(sampler2, input.tex5.xy);") !=
                std::string::npos,
            "stage2 nonmatching texcoord semantic drift");
        require(
            prototype.source.find(
                "float3 nextColor = sampled2.rgb;") != std::string::npos,
            "stage2 SELECTARG2 color semantic drift");
        require(
            prototype.source.find(
                "float nextAlpha = sampled2.a;") != std::string::npos,
            "stage2 SELECTARG2 alpha semantic drift");
        require_compiles(prototype, "stage2 SELECTARG2 chain compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[1] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            1);
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x00, 0x00);
        require(!readiness.exact(), "stage-chain hole did not fail closed");
        require(
            (readiness.unsupported & FixedFunctionUnsupportedStageChain) != 0,
            "stage-chain hole did not set stage-chain blocker");
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes);
        require(!prototype.generated(), "stage-chain hole generated HLSL");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE | D3DTA_COMPLEMENT,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            0);
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(!readiness.exact(), "argument modifier did not fail closed");
        require(
            (readiness.unsupported & FixedFunctionUnsupportedArgument) != 0,
            "argument modifier did not set argument blocker");
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, textureTypes);
        require(!prototype.generated(), "argument modifier generated HLSL");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[0].textureTransformFlags = D3DTTFF_COUNT2;
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(!readiness.exact(), "texture transform did not fail closed");
        require(
            (readiness.unsupported &
             FixedFunctionUnsupportedTextureTransform) != 0,
            "texture transform did not set transform blocker");
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, textureTypes);
        require(!prototype.generated(), "texture transform generated HLSL");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[0].minFilter = D3DTEXF_ANISOTROPIC;
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(!readiness.exact(), "anisotropic sampler did not fail closed");
        require(
            (readiness.unsupported &
             FixedFunctionUnsupportedSamplerFilter) != 0,
            "anisotropic sampler did not set sampler-filter blocker");
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, textureTypes);
        require(!prototype.generated(), "anisotropic sampler generated HLSL");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x00, textureTypes);
        require(!prototype.generated(), "missing exact resource did not fail closed");
        require(
            (prototype.unsupported &
             FixedFunctionShaderPrototypeUnsupportedNotReady) != 0,
            "missing exact resource did not set not-ready blocker");
        const auto probe =
            compile_fixed_function_pixel_shader_prototype(prototype);
        require(!probe.attempted, "compile probe ran for fail-closed prototype");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        auto cubeTypes = textureTypes;
        cubeTypes[0] = D3DRTYPE_CUBETEXTURE;

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, cubeTypes);
        require(!prototype.generated(), "cube texture did not fail closed");
        require(
            (prototype.unsupported &
             FixedFunctionShaderPrototypeUnsupportedResourceType) != 0,
            "cube texture did not set resource-type blocker");
        const auto probe =
            compile_fixed_function_pixel_shader_prototype(prototype);
        require(!probe.attempted, "compile probe ran for unsupported resource type");
    }

    std::cout << "DX11 fixed-function shader semantics smoke R87: PASS\n";
    return 0;
}
