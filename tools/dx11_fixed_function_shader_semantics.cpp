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
    using outrun::vr::dx11::compile_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R86 semantic smoke failure: " << message << '\n';
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

    std::cout << "DX11 fixed-function shader semantics smoke: PASS\n";
    return 0;
}
