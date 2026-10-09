#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>

#include <d3dcompiler.h>
#include <d3d11shader.h>

#include "vr/d3d11/pipeline_translation.hpp"

namespace
{
    using outrun::vr::dx11::FixedFunctionStageState;
    using outrun::vr::dx11::FixedFunctionVertexShaderPrototypeUnsupportedBlend;
    using outrun::vr::dx11::FixedFunctionVertexShaderPrototypeUnsupportedNormal;
    using outrun::vr::dx11::FixedFunctionVertexShaderPrototypeUnsupportedPosition;
    using outrun::vr::dx11::FixedFunctionTransformUnsupportedIncompleteObservation;
    using outrun::vr::dx11::FixedFunctionTransformUnsupportedNonFinite;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::generate_fixed_function_transform_constants;
    using outrun::vr::dx11::generate_fixed_function_vertex_shader_prototype;

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

    D3DMATRIX identity{};
    identity._11 = 1.0f;
    identity._22 = 1.0f;
    identity._33 = 1.0f;
    identity._44 = 1.0f;

    D3DMATRIX world = identity;
    world._41 = 2.0f;
    D3DMATRIX view = identity;
    view._11 = 3.0f;

    const auto transformConstants =
        generate_fixed_function_transform_constants(
            world, view, identity, true);
    require(transformConstants.exact(),
            "R94 transform constants should be exact");
    require(transformConstants.worldViewProjection[0] == 3.0f,
            "R94 WORLD*VIEW scale order");
    require(transformConstants.worldViewProjection[12] == 6.0f,
            "R94 WORLD*VIEW translation order");
    require(transformConstants.worldViewProjection[15] == 1.0f,
            "R94 homogeneous transform");
    require(transformConstants.payloadHash != 0,
            "R94 transform payload hash");

    const auto incompleteTransform =
        generate_fixed_function_transform_constants(
            identity, identity, identity, false);
    require(
        !incompleteTransform.exact() &&
        (incompleteTransform.unsupported &
         FixedFunctionTransformUnsupportedIncompleteObservation) != 0,
        "R94 incomplete transform observation must fail closed");

    D3DMATRIX nonFinite = identity;
    nonFinite._11 = std::numeric_limits<float>::infinity();
    const auto nonFiniteTransform =
        generate_fixed_function_transform_constants(
            nonFinite, identity, identity, true);
    require(
        !nonFiniteTransform.exact() &&
        (nonFiniteTransform.unsupported &
         FixedFunctionTransformUnsupportedNonFinite) != 0,
        "R94 non-finite transform must fail closed");

    const DWORD fixedFunctionFvf =
        D3DFVF_XYZ | D3DFVF_NORMAL | D3DFVF_DIFFUSE | D3DFVF_TEX1;
    const auto vertexPrototype =
        generate_fixed_function_vertex_shader_prototype(
            fixedFunctionFvf,
            36,
            { true, FALSE });
    require(vertexPrototype.generated(),
            "R93 fixed-function vertex shader prototype generation");
    require(vertexPrototype.inputElements == 4,
            "R93 input element count");
    require(vertexPrototype.texCoordCount == 1,
            "R93 texture-coordinate count");
    require(vertexPrototype.hasDiffuse,
            "R93 diffuse semantic");
    require(vertexPrototype.hasNormal,
            "R123 unlit normal FVF must generate");
    require(vertexPrototype.source.find("NORMAL0") != std::string::npos,
            "R123 unlit normal semantic");
    require(vertexPrototype.source.find("worldViewProjection") !=
                std::string::npos,
            "R93 WVP constant-buffer contract");
    require(vertexPrototype.sourceHash != 0,
            "R93 vertex shader source hash");

    const auto specularVertexPrototype =
        generate_fixed_function_vertex_shader_prototype(
            D3DFVF_XYZ | D3DFVF_SPECULAR,
            16,
            { true, FALSE });
    require(
        specularVertexPrototype.generated() &&
        specularVertexPrototype.hasSpecular,
        "R198 SPECULAR FVF must generate COLOR1 output");
    require(
        specularVertexPrototype.source.find(
            "float4 specular : COLOR1;") != std::string::npos &&
        specularVertexPrototype.source.find(
            "output.specular = input.specular.bgra;") != std::string::npos,
        "R198 SPECULAR FVF COLOR1 packed BGRA swizzle drift");

    const auto defaultSpecularVertexPrototype =
        generate_fixed_function_vertex_shader_prototype(
            D3DFVF_XYZ,
            12,
            { true, FALSE });
    require(
        defaultSpecularVertexPrototype.generated() &&
        !defaultSpecularVertexPrototype.hasSpecular &&
        defaultSpecularVertexPrototype.source.find(
            "output.specular = float4(1.0f, 1.0f, 1.0f, 1.0f);") !=
            std::string::npos,
        "R198 missing SPECULAR FVF must emit documented opaque-white default");

    const auto rhwPrototype =
        generate_fixed_function_vertex_shader_prototype(
            D3DFVF_XYZRHW | D3DFVF_DIFFUSE, 20);
    require(
        !rhwPrototype.generated() &&
        (rhwPrototype.unsupported &
         FixedFunctionVertexShaderPrototypeUnsupportedPosition) != 0,
        "R93 XYZRHW must fail closed");

    const auto blendedPrototype =
        generate_fixed_function_vertex_shader_prototype(
            D3DFVF_XYZB1, 16);
    require(
        !blendedPrototype.generated() &&
        (blendedPrototype.unsupported &
         FixedFunctionVertexShaderPrototypeUnsupportedBlend) != 0,
        "R93 blend-weight FVF must fail closed");

    const auto unknownLightingNormalPrototype =
        generate_fixed_function_vertex_shader_prototype(
            D3DFVF_XYZ | D3DFVF_NORMAL, 24);
    require(
        !unknownLightingNormalPrototype.generated() &&
        (unknownLightingNormalPrototype.unsupported &
         FixedFunctionVertexShaderPrototypeUnsupportedNormal) != 0,
        "R123 unknown lighting normal FVF must fail closed");

    const auto litNormalPrototype =
        generate_fixed_function_vertex_shader_prototype(
            D3DFVF_XYZ | D3DFVF_NORMAL,
            24,
            { true, TRUE });
    require(
        !litNormalPrototype.generated() &&
        (litNormalPrototype.unsupported &
         FixedFunctionVertexShaderPrototypeUnsupportedNormal) != 0,
        "R123 lit normal FVF must fail closed");

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

    std::array<FixedFunctionStageState, 8> specularStages{};
    // Keep the R198 linkage fixture on the same fully observed sampler
    // defaults as every other active fixed-function stage. The SPECULAR
    // selector itself does not sample texture, but readiness still validates
    // captured sampler state for active stages.
    specularStages[0] = active_stage();
    specularStages[0].colorOp = D3DTOP_SELECTARG1;
    specularStages[0].colorArg1 = D3DTA_SPECULAR;
    specularStages[0].alphaOp = D3DTOP_SELECTARG1;
    specularStages[0].alphaArg1 = D3DTA_SPECULAR;
    const auto specularPixelPrototype =
        generate_fixed_function_pixel_shader_prototype(
            specularStages, true, 0x00, 0x00, textureTypes);
    require(
        specularPixelPrototype.generated() &&
        specularPixelPrototype.source.find("input.specular") !=
            std::string::npos,
        "R198 D3DTA_SPECULAR pixel prototype generation");

    ID3DBlob* pixelBytecode = compile_shader(
        pixelPrototype.source.data(),
        pixelPrototype.source.size(),
        "OutRunR92PixelShader",
        "ps_4_0");
    ID3DBlob* compatibleVertexBytecode = compile_shader(
        vertexPrototype.source.data(),
        vertexPrototype.source.size(),
        "OutRunR93FixedFunctionVertexShader",
        "vs_4_0");
    ID3DBlob* mismatchedVertexBytecode = compile_shader(
        mismatchedVertexShader,
        std::strlen(mismatchedVertexShader),
        "OutRunR92MismatchedVertexShader",
        "vs_4_0");
    ID3DBlob* specularPixelBytecode = compile_shader(
        specularPixelPrototype.source.data(),
        specularPixelPrototype.source.size(),
        "OutRunR198SpecularPixelShader",
        "ps_4_0");
    ID3DBlob* specularVertexBytecode = compile_shader(
        specularVertexPrototype.source.data(),
        specularVertexPrototype.source.size(),
        "OutRunR198SpecularVertexShader",
        "vs_4_0");

    ID3D11ShaderReflection* pixelReflection =
        reflect_shader(pixelBytecode);
    ID3D11ShaderReflection* compatibleVertexReflection =
        reflect_shader(compatibleVertexBytecode);
    ID3D11ShaderReflection* mismatchedVertexReflection =
        reflect_shader(mismatchedVertexBytecode);
    ID3D11ShaderReflection* specularPixelReflection =
        reflect_shader(specularPixelBytecode);
    ID3D11ShaderReflection* specularVertexReflection =
        reflect_shader(specularVertexBytecode);

    bool specularSawColor0 = false;
    bool specularSawTexcoord0 = false;
    require(
        interfaces_compatible(
            specularVertexReflection,
            specularPixelReflection,
            specularSawColor0,
            specularSawTexcoord0),
        "R198 D3DTA_SPECULAR VS/PS COLOR1 interface rejected");

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

    specularVertexReflection->Release();
    specularPixelReflection->Release();
    mismatchedVertexReflection->Release();
    compatibleVertexReflection->Release();
    pixelReflection->Release();
    specularVertexBytecode->Release();
    specularPixelBytecode->Release();
    mismatchedVertexBytecode->Release();
    compatibleVertexBytecode->Release();
    pixelBytecode->Release();

    std::cout
        << "DX11 fixed-function SPECULAR COLOR1 linkage R198: PASS\n"
        << "DX11 shader linkage probe R92: PASS\n";
    return 0;
}
