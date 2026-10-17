#include <cstdlib>
#include <cstring>
#include <iostream>

#include <d3dcompiler.h>
#include <d3d11shader.h>

#include "vr/d3d11/pipeline_translation.hpp"

namespace
{
    using outrun::vr::dx11::VertexInputLayoutTranslation;
    using outrun::vr::dx11::translate_vertex_input_layout;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R89 input-signature semantic smoke failure: "
                      << message << '\n';
            std::exit(1);
        }
    }

    struct ReflectedContract
    {
        D3D_REGISTER_COMPONENT_TYPE componentType =
            D3D_REGISTER_COMPONENT_UNKNOWN;
        BYTE mask = 0;
    };

    bool expected_contract(
        DXGI_FORMAT format,
        ReflectedContract& out) noexcept
    {
        switch (format)
        {
        case DXGI_FORMAT_R32_FLOAT:
            out.componentType = D3D_REGISTER_COMPONENT_FLOAT32;
            out.mask = 0x1;
            return true;
        case DXGI_FORMAT_R32G32_FLOAT:
            out.componentType = D3D_REGISTER_COMPONENT_FLOAT32;
            out.mask = 0x3;
            return true;
        case DXGI_FORMAT_R32G32B32_FLOAT:
            out.componentType = D3D_REGISTER_COMPONENT_FLOAT32;
            out.mask = 0x7;
            return true;
        case DXGI_FORMAT_R32G32B32A32_FLOAT:
            out.componentType = D3D_REGISTER_COMPONENT_FLOAT32;
            out.mask = 0xF;
            return true;
        case DXGI_FORMAT_R8G8B8A8_UINT:
            out.componentType = D3D_REGISTER_COMPONENT_UINT32;
            out.mask = 0xF;
            return true;
        case DXGI_FORMAT_B8G8R8A8_UNORM:
            out.componentType = D3D_REGISTER_COMPONENT_FLOAT32;
            out.mask = 0xF;
            return true;
        default:
            return false;
        }
    }

    bool signature_matches_layout(
        const VertexInputLayoutTranslation& layout,
        const char* hlsl)
    {
        ID3DBlob* bytecode = nullptr;
        ID3DBlob* diagnostics = nullptr;
        const auto compileHr = D3DCompile(
            hlsl,
            std::strlen(hlsl),
            "OutRunR89InputSignatureSmoke",
            nullptr,
            nullptr,
            "main",
            "vs_4_0",
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0,
            &bytecode,
            &diagnostics);

        if (diagnostics)
            diagnostics->Release();
        if (FAILED(compileHr) || !bytecode)
        {
            if (bytecode)
                bytecode->Release();
            return false;
        }

        ID3D11ShaderReflection* reflection = nullptr;
        const auto reflectHr = D3DReflect(
            bytecode->GetBufferPointer(),
            bytecode->GetBufferSize(),
            IID_ID3D11ShaderReflection,
            reinterpret_cast<void**>(&reflection));
        if (FAILED(reflectHr) || !reflection)
        {
            bytecode->Release();
            return false;
        }

        D3D11_SHADER_DESC shaderDesc{};
        bool matches =
            SUCCEEDED(reflection->GetDesc(&shaderDesc)) &&
            shaderDesc.InputParameters == layout.elementCount;

        for (UINT elementIndex = 0;
             matches && elementIndex < layout.elementCount;
             ++elementIndex)
        {
            const auto& element = layout.elements[elementIndex];
            ReflectedContract expected{};
            if (!element.SemanticName ||
                !expected_contract(element.Format, expected))
            {
                matches = false;
                break;
            }

            bool found = false;
            for (UINT inputIndex = 0;
                 inputIndex < shaderDesc.InputParameters;
                 ++inputIndex)
            {
                D3D11_SIGNATURE_PARAMETER_DESC parameter{};
                if (FAILED(reflection->GetInputParameterDesc(
                        inputIndex, &parameter)))
                {
                    matches = false;
                    break;
                }
                if (parameter.SemanticName &&
                    std::strcmp(
                        parameter.SemanticName,
                        element.SemanticName) == 0 &&
                    parameter.SemanticIndex == element.SemanticIndex)
                {
                    found =
                        parameter.ComponentType == expected.componentType &&
                        parameter.Mask == expected.mask;
                    break;
                }
            }
            matches = matches && found;
        }

        reflection->Release();
        bytecode->Release();
        return matches;
    }

    VertexInputLayoutTranslation translate(DWORD fvf, UINT stride)
    {
        return translate_vertex_input_layout(nullptr, 0, fvf, stride);
    }
}

int main()
{
    constexpr const char* xyzb5Shader = R"(
struct VSInput
{
    float3 position : POSITION0;
    float4 weights0 : BLENDWEIGHT0;
    float weight1 : BLENDWEIGHT1;
};
float4 main(VSInput input) : SV_Position
{
    float3 p = input.position;
    p += input.weights0.xyz * 0.001f;
    p += input.weight1.xxx * 0.001f;
    return float4(p, 1.0f);
}
)";

    constexpr const char* ubyte4Shader = R"(
struct VSInput
{
    float3 position : POSITION0;
    float2 weights : BLENDWEIGHT0;
    uint4 indices : BLENDINDICES0;
};
float4 main(VSInput input) : SV_Position
{
    float influence =
        dot(input.weights, float2(0.001f, 0.002f)) +
        dot(float4(input.indices), float4(0.0001f, 0.0002f, 0.0003f, 0.0004f));
    return float4(input.position.x + influence, input.position.yz, 1.0f);
}
)";

    constexpr const char* d3dColorShader = R"(
struct VSInput
{
    float3 position : POSITION0;
    float weight : BLENDWEIGHT0;
    float4 indices : BLENDINDICES0;
};
float4 main(VSInput input) : SV_Position
{
    float influence =
        input.weight * 0.001f +
        dot(input.indices, float4(0.0001f, 0.0002f, 0.0003f, 0.0004f));
    return float4(input.position.x + influence, input.position.yz, 1.0f);
}
)";

    constexpr const char* blendNormalShader = R"(
struct VSInput
{
    float3 position : POSITION0;
    float4 weights : BLENDWEIGHT0;
    float3 normal : NORMAL0;
};
float4 main(VSInput input) : SV_Position
{
    float3 p =
        input.position +
        input.normal * 0.001f +
        input.weights.xyz * 0.001f;
    return float4(p, 1.0f);
}
)";

    constexpr const char* wrongUbyte4TypeShader = R"(
struct VSInput
{
    float3 position : POSITION0;
    float2 weights : BLENDWEIGHT0;
    float4 indices : BLENDINDICES0;
};
float4 main(VSInput input) : SV_Position
{
    float influence =
        dot(input.weights, float2(0.001f, 0.002f)) +
        dot(input.indices, float4(0.0001f, 0.0002f, 0.0003f, 0.0004f));
    return float4(input.position.x + influence, input.position.yz, 1.0f);
}
)";

    const auto xyzb5 = translate(D3DFVF_XYZB5, 32);
    require(xyzb5.exact, "XYZB5 descriptor prerequisite");
    require(
        signature_matches_layout(xyzb5, xyzb5Shader),
        "XYZB5 split BLENDWEIGHT0/1 signature contract");

    const auto ubyte4 = translate(
        D3DFVF_XYZB3 | D3DFVF_LASTBETA_UBYTE4,
        24);
    require(ubyte4.exact, "XYZB3 UBYTE4 descriptor prerequisite");
    require(
        signature_matches_layout(ubyte4, ubyte4Shader),
        "UBYTE4 BLENDINDICES must consume uint4 shader input");
    require(
        !signature_matches_layout(ubyte4, wrongUbyte4TypeShader),
        "UBYTE4 BLENDINDICES float4 mismatch must fail closed");

    const auto d3dColor = translate(
        D3DFVF_XYZB2 | D3DFVF_LASTBETA_D3DCOLOR,
        20);
    require(d3dColor.exact, "XYZB2 D3DCOLOR descriptor prerequisite");
    require(
        signature_matches_layout(d3dColor, d3dColorShader),
        "D3DCOLOR BLENDINDICES must consume normalized float4 input");

    const auto blendNormal = translate(
        D3DFVF_XYZB4 | D3DFVF_NORMAL,
        40);
    require(blendNormal.exact, "XYZB4 NORMAL descriptor prerequisite");
    require(
        signature_matches_layout(blendNormal, blendNormalShader),
        "blend-weight plus NORMAL shader input contract");

    std::cout << "DX11 input signature semantics smoke R89: PASS\n";
    return 0;
}
