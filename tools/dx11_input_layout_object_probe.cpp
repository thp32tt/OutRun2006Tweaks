#include <cstdlib>
#include <cstring>
#include <iostream>

#include <d3dcompiler.h>
#include <d3d11.h>

#include "vr/d3d11/pipeline_translation.hpp"

namespace
{
    using outrun::vr::dx11::VertexInputLayoutTranslation;
    using outrun::vr::dx11::translate_vertex_input_layout;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R90 input-layout object probe failure: "
                      << message << '\n';
            std::exit(1);
        }
    }

    ID3D11Device* create_warp_device()
    {
        const D3D_FEATURE_LEVEL requestedLevels[] = {
            D3D_FEATURE_LEVEL_11_0,
            D3D_FEATURE_LEVEL_10_1,
            D3D_FEATURE_LEVEL_10_0,
        };

        ID3D11Device* device = nullptr;
        ID3D11DeviceContext* context = nullptr;
        D3D_FEATURE_LEVEL createdLevel = D3D_FEATURE_LEVEL_9_1;
        const HRESULT hr = D3D11CreateDevice(
            nullptr,
            D3D_DRIVER_TYPE_WARP,
            nullptr,
            0,
            requestedLevels,
            3,
            D3D11_SDK_VERSION,
            &device,
            &createdLevel,
            &context);

        if (context)
            context->Release();

        require(SUCCEEDED(hr) && device != nullptr,
                "D3D11 WARP device creation");
        require(createdLevel >= D3D_FEATURE_LEVEL_10_0,
                "D3D11 WARP feature level");
        return device;
    }

    bool create_input_layout_object(
        ID3D11Device* device,
        const VertexInputLayoutTranslation& layout,
        const char* hlsl)
    {
        if (!device || !layout.exact || layout.elementCount == 0 || !hlsl)
            return false;

        ID3DBlob* bytecode = nullptr;
        ID3DBlob* diagnostics = nullptr;
        const HRESULT compileHr = D3DCompile(
            hlsl,
            std::strlen(hlsl),
            "OutRunR90InputLayoutObjectProbe",
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

        ID3D11InputLayout* inputLayout = nullptr;
        const HRESULT layoutHr = device->CreateInputLayout(
            layout.elements.data(),
            layout.elementCount,
            bytecode->GetBufferPointer(),
            bytecode->GetBufferSize(),
            &inputLayout);

        bytecode->Release();
        if (inputLayout)
            inputLayout->Release();

        return SUCCEEDED(layoutHr) && inputLayout != nullptr;
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

    ID3D11Device* device = create_warp_device();

    const auto xyzb5 = translate(D3DFVF_XYZB5, 32);
    require(xyzb5.exact, "XYZB5 descriptor prerequisite");
    require(
        create_input_layout_object(device, xyzb5, xyzb5Shader),
        "XYZB5 CreateInputLayout");

    const auto ubyte4 = translate(
        D3DFVF_XYZB3 | D3DFVF_LASTBETA_UBYTE4,
        24);
    require(ubyte4.exact, "XYZB3 UBYTE4 descriptor prerequisite");
    require(
        create_input_layout_object(device, ubyte4, ubyte4Shader),
        "UBYTE4 BLENDINDICES CreateInputLayout");

    const auto blendNormal = translate(
        D3DFVF_XYZB4 | D3DFVF_NORMAL,
        40);
    require(blendNormal.exact, "XYZB4 NORMAL descriptor prerequisite");
    require(
        create_input_layout_object(device, blendNormal, blendNormalShader),
        "blend-weight plus NORMAL CreateInputLayout");

    UINT bgraSupport = 0;
    const HRESULT bgraHr = device->CheckFormatSupport(
        DXGI_FORMAT_B8G8R8A8_UNORM,
        &bgraSupport);
    std::cout
        << "R90 D3DCOLOR/BGRA IA support: "
        << ((SUCCEEDED(bgraHr) &&
             (bgraSupport & D3D11_FORMAT_SUPPORT_IA_VERTEX_BUFFER) != 0)
                ? "SUPPORTED"
                : "PENDING")
        << "\n";

    device->Release();

    std::cout << "DX11 input layout object probe R90: PASS\n";
    return 0;
}
