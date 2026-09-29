#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>

#include <d3dcompiler.h>
#include <d3d11shader.h>

#include "vr/d3d11/pipeline_translation.hpp"

namespace
{
    using outrun::vr::dx11::FixedFunctionStageState;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R92 shader-linkage probe failure: "
                      << message << '\n';
            std::exit(1);
        }
    }

    ID3DBlob* compile_shader(
        const char* source,
        std::size_t size,
        const char* sourceName,
        const char* target)
    {
        ID3DBlob* bytecode = nullptr;
        ID3DBlob* diagnostics = nullptr;
        const HRESULT hr = D3DCompile(
            source,
            size,
            sourceName,
            nullptr,
            nullptr,
            "main",
            target,
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0,
            &bytecode,
            &diagnostics);

        if (diagnostics)
            diagnostics->Release();

        require(SUCCEEDED(hr) && bytecode != nullptr,
                "D3DCompile linkage prerequisite");
        return bytecode;
    }

    ID3D11ShaderReflection* reflect_shader(ID3DBlob* bytecode)
    {
        require(bytecode != nullptr, "reflection bytecode");
        ID3D11ShaderReflection* reflection = nullptr;
        const HRESULT hr = D3DReflect(
            bytecode->GetBufferPointer(),
            bytecode->GetBufferSize(),
            IID_ID3D11ShaderReflection,
            reinterpret_cast<void**>(&reflection));
        require(SUCCEEDED(hr) && reflection != nullptr, "D3DReflect");
        return reflection;
    }

    bool same_semantic(
        const D3D11_SIGNATURE_PARAMETER_DESC& a,
        const D3D11_SIGNATURE_PARAMETER_DESC& b)
    {
        return a.SemanticName && b.SemanticName &&
            _stricmp(a.SemanticName, b.SemanticName) == 0 &&
            a.SemanticIndex == b.SemanticIndex;
    }

    bool interfaces_compatible(
        ID3D11ShaderReflection* vertex,
        ID3D11ShaderReflection* pixel,
        bool& sawColor0,
        bool& sawTexcoord0)
    {
        sawColor0 = false;
        sawTexcoord0 = false;
        if (!vertex || !pixel)
            return false;

        D3D11_SHADER_DESC vertexDesc{};
        D3D11_SHADER_DESC pixelDesc{};
        if (FAILED(vertex->GetDesc(&vertexDesc)) ||
            FAILED(pixel->GetDesc(&pixelDesc)))
            return false;

        UINT checkedInputs = 0;
        for (UINT inputIndex = 0;
             inputIndex < pixelDesc.InputParameters;
             ++inputIndex)
        {
            D3D11_SIGNATURE_PARAMETER_DESC input{};
            if (FAILED(pixel->GetInputParameterDesc(inputIndex, &input)))
                return false;

            if (input.SystemValueType != D3D_NAME_UNDEFINED)
                continue;

            bool matched = false;
            for (UINT outputIndex = 0;
                 outputIndex < vertexDesc.OutputParameters;
                 ++outputIndex)
            {
                D3D11_SIGNATURE_PARAMETER_DESC output{};
                if (FAILED(vertex->GetOutputParameterDesc(
                        outputIndex, &output)))
                    return false;
                if (!same_semantic(input, output))
                    continue;

                if (output.ComponentType != input.ComponentType)
                    return false;
                if ((output.Mask & input.Mask) != input.Mask)
                    return false;

                if (_stricmp(input.SemanticName, "COLOR") == 0 &&
                    input.SemanticIndex == 0)
                    sawColor0 = true;
                if (_stricmp(input.SemanticName, "TEXCOORD") == 0 &&
                    input.SemanticIndex == 0)
                    sawTexcoord0 = true;

                matched = true;
                ++checkedInputs;
                break;
            }
            if (!matched)
                return false;
        }

        return checkedInputs > 0;
    }

    FixedFunctionStageState active_stage()
    {
        FixedFunctionStageState stage{};
        stage.colorOp = D3DTOP_MODULATE;
        stage.colorArg1 = D3DTA_TEXTURE;
        stage.colorArg2 = D3DTA_DIFFUSE;
        stage.alphaOp = D3DTOP_SELECTARG1;
        stage.alphaArg1 = D3DTA_TEXTURE;
        stage.alphaArg2 = D3DTA_CURRENT;
        stage.texCoordIndex = 0;
        stage.textureTransformFlags = D3DTTFF_DISABLE;
        stage.minFilter = D3DTEXF_POINT;
        stage.magFilter = D3DTEXF_POINT;
        stage.mipFilter = D3DTEXF_NONE;
        stage.addressU = D3DTADDRESS_WRAP;
        stage.addressV = D3DTADDRESS_WRAP;
        return stage;
    }
}

int main()
{
    constexpr const char* compatibleVertexShader = R"(
struct VSOutput
{
    float4 position : SV_Position;
    float4 diffuse : COLOR0;
    float4 tex0 : TEXCOORD0;
    float4 tex1 : TEXCOORD1;
    float4 tex2 : TEXCOORD2;
    float4 tex3 : TEXCOORD3;
    float4 tex4 : TEXCOORD4;
    float4 tex5 : TEXCOORD5;
    float4 tex6 : TEXCOORD6;
    float4 tex7 : TEXCOORD7;
};
VSOutput main(float3 position : POSITION0)
{
    VSOutput output;
    output.position = float4(position, 1.0f);
    output.diffuse = float4(1.0f, 1.0f, 1.0f, 1.0f);
    output.tex0 = float4(position.xy, 0.0f, 0.0f);
    output.tex1 = 0.0f;
    output.tex2 = 0.0f;
    output.tex3 = 0.0f;
    output.tex4 = 0.0f;
    output.tex5 = 0.0f;
    output.tex6 = 0.0f;
    output.tex7 = 0.0f;
    return output;
}
)";

    constexpr const char* mismatchedVertexShader = R"(
struct VSOutput
{
    float4 position : SV_Position;
    uint4 diffuse : COLOR0;
    float4 tex0 : TEXCOORD0;
};
VSOutput main(float3 position : POSITION0)
{
    VSOutput output;
    output.position = float4(position, 1.0f);
    output.diffuse = uint4(1, 1, 1, 1);
    output.tex0 = float4(position.xy, 0.0f, 0.0f);
    return output;
}
)";

    std::array<FixedFunctionStageState, 8> stages{};
    stages[0] = active_stage();
    std::array<D3DRESOURCETYPE, 8> textureTypes{};
    textureTypes.fill(D3DRTYPE_TEXTURE);

    const auto pixelPrototype =
        generate_fixed_function_pixel_shader_prototype(
            stages,
            true,
            0x01,
            0x01,
            textureTypes);
    require(pixelPrototype.generated(),
            "R84 fixed-function pixel shader prototype generation");

    ID3DBlob* pixelBytecode = compile_shader(
        pixelPrototype.source.data(),
        pixelPrototype.source.size(),
        "OutRunR92PixelShader",
        "ps_4_0");
    ID3DBlob* compatibleVertexBytecode = compile_shader(
        compatibleVertexShader,
        std::strlen(compatibleVertexShader),
        "OutRunR92CompatibleVertexShader",
        "vs_4_0");
    ID3DBlob* mismatchedVertexBytecode = compile_shader(
        mismatchedVertexShader,
        std::strlen(mismatchedVertexShader),
        "OutRunR92MismatchedVertexShader",
        "vs_4_0");

    ID3D11ShaderReflection* pixelReflection =
        reflect_shader(pixelBytecode);
    ID3D11ShaderReflection* compatibleVertexReflection =
        reflect_shader(compatibleVertexBytecode);
    ID3D11ShaderReflection* mismatchedVertexReflection =
        reflect_shader(mismatchedVertexBytecode);

    bool sawColor0 = false;
    bool sawTexcoord0 = false;
    require(
        interfaces_compatible(
            compatibleVertexReflection,
            pixelReflection,
            sawColor0,
            sawTexcoord0),
        "compatible VS/PS interface rejected");
    require(sawColor0, "COLOR0 was not validated");
    require(sawTexcoord0, "TEXCOORD0 was not validated");

    bool mismatchSawColor0 = false;
    bool mismatchSawTexcoord0 = false;
    require(
        !interfaces_compatible(
            mismatchedVertexReflection,
            pixelReflection,
            mismatchSawColor0,
            mismatchSawTexcoord0),
        "UINT COLOR0 mismatch did not fail closed");

    mismatchedVertexReflection->Release();
    compatibleVertexReflection->Release();
    pixelReflection->Release();
    mismatchedVertexBytecode->Release();
    compatibleVertexBytecode->Release();
    pixelBytecode->Release();

    std::cout << "DX11 shader linkage probe R92: PASS\n";
    return 0;
}
