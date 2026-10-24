#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>

#include <d3dcompiler.h>
#include <d3d11.h>

#include "vr/d3d11/pipeline_translation.hpp"

namespace
{
    using outrun::vr::dx11::FixedFunctionStageState;
    using outrun::vr::dx11::VertexInputLayoutTranslation;
    using outrun::vr::dx11::ProgrammableShaderFunctionIdentity;
    using outrun::vr::dx11::ProgrammableShaderPairIdentityUnsupportedIncompleteObservation;
    using outrun::vr::dx11::ProgrammableShaderPairIdentityUnsupportedInvalidVertexBytecode;
    using outrun::vr::dx11::ProgrammableShaderPairIdentityUnsupportedInvalidVertexVersion;
    using outrun::vr::dx11::ProgrammableShaderPairIdentityUnsupportedMissingPixelHash;
    using outrun::vr::dx11::ProgrammableShaderPairIdentityUnsupportedMixedPair;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::seal_programmable_shader_pair_cache_identity;
    using outrun::vr::dx11::translate_vertex_input_layout;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R91 shader-object probe failure: "
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
                "D3DCompile shader object prerequisite");
        return bytecode;
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
    const ProgrammableShaderFunctionIdentity programmableVs{
        true,
        true,
        128u,
        D3DVS_VERSION(3, 0),
        0x1111111111111111ull,
    };
    const ProgrammableShaderFunctionIdentity programmablePs{
        true,
        true,
        96u,
        D3DPS_VERSION(3, 0),
        0x2222222222222222ull,
    };

    const auto programmablePair =
        seal_programmable_shader_pair_cache_identity(
            true, false, programmableVs, programmablePs);
    require(
        programmablePair.exact_identity() &&
        programmablePair.cacheKey != 0 &&
        !programmablePair.translationImplemented,
        "R239 programmable pair identity/cache key prerequisite");

    const auto programmablePairRepeat =
        seal_programmable_shader_pair_cache_identity(
            true, false, programmableVs, programmablePs);
    require(
        programmablePairRepeat.exact_identity() &&
        programmablePairRepeat.cacheKey == programmablePair.cacheKey,
        "R239 programmable pair cache key must be deterministic");

    auto changedProgrammablePs = programmablePs;
    changedProgrammablePs.bytecodeHash ^= 1ull;
    const auto changedProgrammablePair =
        seal_programmable_shader_pair_cache_identity(
            true, false, programmableVs, changedProgrammablePs);
    require(
        changedProgrammablePair.exact_identity() &&
        changedProgrammablePair.cacheKey != programmablePair.cacheKey,
        "R239 programmable pair cache key must include PS bytecode identity");

    const auto incompleteProgrammablePair =
        seal_programmable_shader_pair_cache_identity(
            false, false, programmableVs, programmablePs);
    require(
        !incompleteProgrammablePair.exact_identity() &&
        (incompleteProgrammablePair.unsupported &
         ProgrammableShaderPairIdentityUnsupportedIncompleteObservation) != 0,
        "R239 incomplete programmable observation must fail closed");

    const auto mixedProgrammablePair =
        seal_programmable_shader_pair_cache_identity(
            true, true, programmableVs, programmablePs);
    require(
        !mixedProgrammablePair.exact_identity() &&
        (mixedProgrammablePair.unsupported &
         ProgrammableShaderPairIdentityUnsupportedMixedPair) != 0,
        "R239 mixed programmable pair must fail closed");

    auto invalidProgrammableVs = programmableVs;
    invalidProgrammableVs.byteSize = 127u;
    const auto invalidBytecodePair =
        seal_programmable_shader_pair_cache_identity(
            true, false, invalidProgrammableVs, programmablePs);
    require(
        !invalidBytecodePair.exact_identity() &&
        (invalidBytecodePair.unsupported &
         ProgrammableShaderPairIdentityUnsupportedInvalidVertexBytecode) != 0,
        "R239 non-DWORD-aligned VS bytecode must fail closed");

    invalidProgrammableVs = programmableVs;
    invalidProgrammableVs.versionToken = D3DPS_VERSION(3, 0);
    const auto invalidVersionPair =
        seal_programmable_shader_pair_cache_identity(
            true, false, invalidProgrammableVs, programmablePs);
    require(
        !invalidVersionPair.exact_identity() &&
        (invalidVersionPair.unsupported &
         ProgrammableShaderPairIdentityUnsupportedInvalidVertexVersion) != 0,
        "R239 stage-mismatched VS version token must fail closed");

    auto missingHashPs = programmablePs;
    missingHashPs.bytecodeHash = 0;
    const auto missingHashPair =
        seal_programmable_shader_pair_cache_identity(
            true, false, programmableVs, missingHashPs);
    require(
        !missingHashPair.exact_identity() &&
        (missingHashPair.unsupported &
         ProgrammableShaderPairIdentityUnsupportedMissingPixelHash) != 0,
        "R239 zero PS bytecode hash must fail closed");

    constexpr const char* vertexShaderSource = R"(
struct VSInput
{
    float3 position : POSITION0;
    float4 weights0 : BLENDWEIGHT0;
    float weight1 : BLENDWEIGHT1;
};
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
VSOutput main(VSInput input)
{
    VSOutput output;
    float3 p = input.position;
    p += input.weights0.xyz * 0.001f;
    p += input.weight1.xxx * 0.001f;
    output.position = float4(p, 1.0f);
    output.diffuse = float4(1.0f, 1.0f, 1.0f, 1.0f);
    output.tex0 = 0.0f;
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

    ID3D11Device* device = create_warp_device();

    const VertexInputLayoutTranslation layout =
        translate_vertex_input_layout(
            nullptr, 0, D3DFVF_XYZB5, 32);
    require(layout.exact && layout.elementCount == 3,
            "XYZB5 input-layout prerequisite");

    ID3DBlob* vertexBytecode = compile_shader(
        vertexShaderSource,
        std::strlen(vertexShaderSource),
        "OutRunR91VertexShaderObjectProbe",
        "vs_4_0");

    ID3D11VertexShader* vertexShader = nullptr;
    require(
        SUCCEEDED(device->CreateVertexShader(
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(),
            nullptr,
            &vertexShader)) &&
        vertexShader != nullptr,
        "CreateVertexShader");

    ID3D11InputLayout* inputLayout = nullptr;
    require(
        SUCCEEDED(device->CreateInputLayout(
            layout.elements.data(),
            layout.elementCount,
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(),
            &inputLayout)) &&
        inputLayout != nullptr,
        "CreateInputLayout paired with vertex shader");

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
    require(pixelPrototype.sourceHash != 0,
            "R84 pixel shader source hash");

    ID3DBlob* pixelBytecode = compile_shader(
        pixelPrototype.source.data(),
        pixelPrototype.source.size(),
        "OutRunR91PixelShaderObjectProbe",
        "ps_4_0");

    ID3D11PixelShader* pixelShader = nullptr;
    require(
        SUCCEEDED(device->CreatePixelShader(
            pixelBytecode->GetBufferPointer(),
            pixelBytecode->GetBufferSize(),
            nullptr,
            &pixelShader)) &&
        pixelShader != nullptr,
        "CreatePixelShader from R84 prototype");

    pixelShader->Release();
    pixelBytecode->Release();
    inputLayout->Release();
    vertexShader->Release();
    vertexBytecode->Release();
    device->Release();

    std::cout << "DX11 shader object probe R91: PASS\n";
    return 0;
}
