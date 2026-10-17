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
                if (output.Register != input.Register)
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

    // R176 independent signature-level reproduction of the R175 WARP
    // generic-varying discriminator. This changes neither its raster probe
    // nor any gameplay Draw path; the existing R175 failing readback remains
    // authoritative for pixel behavior.
    constexpr const char* r176VertexShader = R"(
struct Input { float3 position : POSITION0; float4 color : COLOR0; };
struct Output { float4 position : SV_Position; float4 payload : TEXCOORD6; };
Output main(Input input) {
    Output output;
    output.position = float4(input.position, 1.0f);
    output.payload = float4(32.0f/255.0f, 128.0f/255.0f,
                            224.0f/255.0f, 1.0f);
    return output;
}
)";
    constexpr const char* r176PixelShader = R"(
struct Input { float4 position : SV_Position; float4 payload : TEXCOORD6; };
float4 main(Input input) : SV_Target {
    if (input.position.x < 0.0f) discard;
    return input.payload;
}
)";
    // Same semantic/type but different DXBC register than the vertex output.
    constexpr const char* r176WrongRegisterPixelShader = R"(
float4 main(float4 payload : TEXCOORD6) : SV_Target { return payload; }
)";
    constexpr const char* r176WrongSemanticPixelShader = R"(
float4 main(float4 payload : TEXCOORD7) : SV_Target { return payload; }
)";
    constexpr const char* r176WrongTypePixelShader = R"(
float4 main(uint4 payload : TEXCOORD6) : SV_Target {
    return float4(payload);
}
)";
    ID3DBlob* r176Vs = compile_shader(
        r176VertexShader, std::strlen(r176VertexShader),
        "OutRunR176Texcoord6VS", "vs_4_0");
    ID3DBlob* r176Ps = compile_shader(
        r176PixelShader, std::strlen(r176PixelShader),
        "OutRunR176Texcoord6PS", "ps_4_0");
    ID3DBlob* r176WrongRegisterPs = compile_shader(
        r176WrongRegisterPixelShader,
        std::strlen(r176WrongRegisterPixelShader),
        "OutRunR176WrongRegisterPS", "ps_4_0");
    ID3DBlob* r176WrongSemanticPs = compile_shader(
        r176WrongSemanticPixelShader,
        std::strlen(r176WrongSemanticPixelShader),
        "OutRunR176WrongSemanticPS", "ps_4_0");
    ID3DBlob* r176WrongTypePs = compile_shader(
        r176WrongTypePixelShader, std::strlen(r176WrongTypePixelShader),
        "OutRunR176WrongTypePS", "ps_4_0");
    ID3D11ShaderReflection* r176VsReflection = reflect_shader(r176Vs);
    ID3D11ShaderReflection* r176PsReflection = reflect_shader(r176Ps);
    ID3D11ShaderReflection* r176WrongRegisterReflection =
        reflect_shader(r176WrongRegisterPs);
    ID3D11ShaderReflection* r176WrongSemanticReflection =
        reflect_shader(r176WrongSemanticPs);
    ID3D11ShaderReflection* r176WrongTypeReflection =
        reflect_shader(r176WrongTypePs);
    bool r176SawColor0 = false;
    bool r176SawTexcoord0 = false;
    require(interfaces_compatible(
                r176VsReflection, r176PsReflection,
                r176SawColor0, r176SawTexcoord0) &&
                !r176SawColor0 && !r176SawTexcoord0,
            "R176 TEXCOORD6 compiled VS/PS linkage must be exact");
    D3D11_SHADER_DESC r176VsDesc{};
    D3D11_SHADER_DESC r176PsDesc{};
    require(SUCCEEDED(r176VsReflection->GetDesc(&r176VsDesc)) &&
                SUCCEEDED(r176PsReflection->GetDesc(&r176PsDesc)),
            "R176 shader reflection descriptions");
    bool r176FoundVs = false;
    bool r176FoundPs = false;
    UINT r176VsRegister = 0u;
    UINT r176PsRegister = 0u;
    for (UINT i = 0; i < r176VsDesc.OutputParameters; ++i)
    {
        D3D11_SIGNATURE_PARAMETER_DESC p{};
        require(SUCCEEDED(r176VsReflection->GetOutputParameterDesc(i, &p)),
                "R176 VS output signature accessible");
        if (p.SemanticName && _stricmp(p.SemanticName, "TEXCOORD") == 0 &&
            p.SemanticIndex == 6u)
        {
            require(!r176FoundVs && p.ComponentType ==
                        D3D_REGISTER_COMPONENT_FLOAT32 && p.Mask == 0xFu,
                    "R176 VS TEXCOORD6 float4 output signature");
            r176FoundVs = true;
            r176VsRegister = p.Register;
        }
    }
    for (UINT i = 0; i < r176PsDesc.InputParameters; ++i)
    {
        D3D11_SIGNATURE_PARAMETER_DESC p{};
        require(SUCCEEDED(r176PsReflection->GetInputParameterDesc(i, &p)),
                "R176 PS input signature accessible");
        if (p.SemanticName && _stricmp(p.SemanticName, "TEXCOORD") == 0 &&
            p.SemanticIndex == 6u)
        {
            require(!r176FoundPs && p.ComponentType ==
                        D3D_REGISTER_COMPONENT_FLOAT32 && p.Mask == 0xFu,
                    "R176 PS TEXCOORD6 float4 input signature");
            r176FoundPs = true;
            r176PsRegister = p.Register;
        }
    }
    require(r176FoundVs && r176FoundPs &&
                r176VsRegister == r176PsRegister,
            "R176 TEXCOORD6 must occupy matching DXBC registers");
    bool r176NegativeColor = false;
    bool r176NegativeTexcoord = false;
    require(!interfaces_compatible(
                r176VsReflection, r176WrongRegisterReflection,
                r176NegativeColor, r176NegativeTexcoord),
            "R176 same semantic but wrong register must fail closed");
    require(!interfaces_compatible(
                r176VsReflection, r176WrongSemanticReflection,
                r176NegativeColor, r176NegativeTexcoord),
            "R176 mismatched TEXCOORD7 must fail closed");
    require(!interfaces_compatible(
                r176VsReflection, r176WrongTypeReflection,
                r176NegativeColor, r176NegativeTexcoord),
            "R176 mismatched uint4 TEXCOORD6 must fail closed");
    std::cout << "DX11 R176 TEXCOORD6 DXBC signature: MATCH float4"
              << " VS_register=" << r176VsRegister
              << " PS_register=" << r176PsRegister
              << " negative_semantic=REJECT negative_type=REJECT\n";
    r176WrongTypeReflection->Release();
    r176WrongSemanticReflection->Release();
    r176WrongRegisterReflection->Release();
    r176PsReflection->Release();
    r176VsReflection->Release();
    r176WrongTypePs->Release();
    r176WrongSemanticPs->Release();
    r176WrongRegisterPs->Release();
    r176Ps->Release();
    r176Vs->Release();

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
