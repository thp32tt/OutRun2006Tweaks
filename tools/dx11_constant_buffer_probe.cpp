#include <cstdlib>
#include <cstring>
#include <iostream>

#include <d3dcompiler.h>
#include <d3d11.h>
#include <d3d11shader.h>

#include "vr/d3d11/native_backend.hpp"
#include "vr/d3d11/pipeline_translation.hpp"

namespace
{
    using outrun::vr::dx11::FixedFunctionStageState;
    using outrun::vr::dx11::NativeFixedFunctionPipelineBundle;
    using outrun::vr::dx11::NativeFixedFunctionSamplerState;
    using outrun::vr::dx11::NativeFixedFunctionTransformBuffer;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::generate_fixed_function_transform_constants;
    using outrun::vr::dx11::generate_fixed_function_vertex_shader_prototype;
    using outrun::vr::dx11::translate_fixed_function_sampler;
    using outrun::vr::dx11::translate_vertex_input_layout;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R95 constant-buffer probe failure: "
                      << message << '\n';
            std::exit(1);
        }
    }

    struct DevicePair
    {
        ID3D11Device* device = nullptr;
        ID3D11DeviceContext* context = nullptr;
    };

    DevicePair create_warp_device()
    {
        const D3D_FEATURE_LEVEL requestedLevels[] = {
            D3D_FEATURE_LEVEL_11_0,
            D3D_FEATURE_LEVEL_10_1,
            D3D_FEATURE_LEVEL_10_0,
        };

        DevicePair out{};
        D3D_FEATURE_LEVEL createdLevel = D3D_FEATURE_LEVEL_9_1;
        const HRESULT hr = D3D11CreateDevice(
            nullptr,
            D3D_DRIVER_TYPE_WARP,
            nullptr,
            0,
            requestedLevels,
            3,
            D3D11_SDK_VERSION,
            &out.device,
            &createdLevel,
            &out.context);

        require(
            SUCCEEDED(hr) && out.device != nullptr && out.context != nullptr,
            "D3D11 WARP device/context creation");
        require(
            createdLevel >= D3D_FEATURE_LEVEL_10_0,
            "D3D11 WARP feature level");
        return out;
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

    ID3DBlob* compile_vertex_shader(const std::string& source)
    {
        ID3DBlob* bytecode = nullptr;
        ID3DBlob* diagnostics = nullptr;
        const HRESULT hr = D3DCompile(
            source.data(),
            source.size(),
            "OutRunR95FixedFunctionVertexShader",
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

        require(
            SUCCEEDED(hr) && bytecode != nullptr,
            "D3DCompile R93 vertex prototype");
        return bytecode;
    }
}

int main()
{
    D3DMATRIX identity{};
    identity._11 = 1.0f;
    identity._22 = 1.0f;
    identity._33 = 1.0f;
    identity._44 = 1.0f;

    D3DMATRIX world = identity;
    world._41 = 2.0f;
    D3DMATRIX view = identity;
    view._11 = 3.0f;

    const auto transform =
        generate_fixed_function_transform_constants(
            world, view, identity, true);
    require(transform.exact(), "R94 transform prerequisite");

    constexpr UINT expectedConstantBytes = 16u * sizeof(float);
    static_assert(expectedConstantBytes == 64u);
    require(
        sizeof(transform.worldViewProjection) == expectedConstantBytes,
        "R94 WVP payload must remain 64 bytes");

    constexpr DWORD fixedFunctionFvf =
        D3DFVF_XYZ | D3DFVF_DIFFUSE | D3DFVF_TEX1;
    const auto vertexPrototype =
        generate_fixed_function_vertex_shader_prototype(
            fixedFunctionFvf, 24);
    require(
        vertexPrototype.generated(),
        "R93 vertex prototype prerequisite");

    const auto inputLayout =
        translate_vertex_input_layout(
            nullptr, 0, fixedFunctionFvf, 24);
    require(
        inputLayout.exact && inputLayout.elementCount > 0,
        "R97 input-layout prerequisite");

    std::array<FixedFunctionStageState, 8> stages{};
    stages[0] = active_stage();
    std::array<D3DRESOURCETYPE, 8> textureTypes{};
    textureTypes.fill(D3DRTYPE_TEXTURE);
    const auto pixelPrototype =
        generate_fixed_function_pixel_shader_prototype(
            stages, true, 0x01, 0x01, textureTypes);
    require(
        pixelPrototype.generated(),
        "R97 pixel prototype prerequisite");

    ID3DBlob* vertexBytecode =
        compile_vertex_shader(vertexPrototype.source);

    ID3D11ShaderReflection* reflection = nullptr;
    require(
        SUCCEEDED(D3DReflect(
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(),
            IID_ID3D11ShaderReflection,
            reinterpret_cast<void**>(&reflection))) &&
        reflection != nullptr,
        "D3DReflect R93 vertex shader");

    D3D11_SHADER_INPUT_BIND_DESC binding{};
    require(
        SUCCEEDED(reflection->GetResourceBindingDescByName(
            "FixedFunctionTransform",
            &binding)),
        "reflect FixedFunctionTransform binding");
    require(
        binding.Type == D3D_SIT_CBUFFER &&
        binding.BindPoint == 0 &&
        binding.BindCount == 1,
        "FixedFunctionTransform must bind at b0");

    ID3D11ShaderReflectionConstantBuffer* reflectedBuffer =
        reflection->GetConstantBufferByName("FixedFunctionTransform");
    require(
        reflectedBuffer != nullptr,
        "reflect FixedFunctionTransform constant buffer");

    D3D11_SHADER_BUFFER_DESC reflectedBufferDesc{};
    require(
        SUCCEEDED(reflectedBuffer->GetDesc(&reflectedBufferDesc)),
        "reflect FixedFunctionTransform descriptor");
    require(
        reflectedBufferDesc.Size == expectedConstantBytes,
        "FixedFunctionTransform must remain 64 bytes");

    DevicePair d3d = create_warp_device();

    const auto pointWrapSampler =
        translate_fixed_function_sampler(stages[0]);
    require(
        pointWrapSampler.exact &&
        pointWrapSampler.desc.Filter == D3D11_FILTER_MIN_MAG_MIP_POINT &&
        pointWrapSampler.desc.AddressU == D3D11_TEXTURE_ADDRESS_WRAP &&
        pointWrapSampler.desc.AddressV == D3D11_TEXTURE_ADDRESS_WRAP &&
        pointWrapSampler.desc.MaxLOD == 0.0f,
        "R98 point/wrap sampler translation");

    NativeFixedFunctionSamplerState samplerOwner;
    require(!samplerOwner.ready(),
            "R98 sampler owner must start dormant");
    require(
        samplerOwner.initialize(d3d.device, stages[0]),
        "R98 sampler owner initialize");
    require(
        samplerOwner.ready() &&
        samplerOwner.device() == d3d.device &&
        samplerOwner.sampler() != nullptr,
        "R98 sampler owner readiness");

    D3D11_SAMPLER_DESC observedSampler{};
    samplerOwner.sampler()->GetDesc(&observedSampler);
    require(
        observedSampler.Filter == D3D11_FILTER_MIN_MAG_MIP_POINT &&
        observedSampler.AddressU == D3D11_TEXTURE_ADDRESS_WRAP &&
        observedSampler.AddressV == D3D11_TEXTURE_ADDRESS_WRAP &&
        observedSampler.MaxLOD == 0.0f,
        "R98 created sampler descriptor");

    auto linearClampStage = stages[0];
    linearClampStage.minFilter = D3DTEXF_LINEAR;
    linearClampStage.magFilter = D3DTEXF_LINEAR;
    linearClampStage.mipFilter = D3DTEXF_LINEAR;
    linearClampStage.addressU = D3DTADDRESS_CLAMP;
    linearClampStage.addressV = D3DTADDRESS_CLAMP;
    const auto linearClampSampler =
        translate_fixed_function_sampler(linearClampStage);
    require(
        linearClampSampler.exact &&
        linearClampSampler.desc.Filter == D3D11_FILTER_MIN_MAG_MIP_LINEAR &&
        linearClampSampler.desc.AddressU == D3D11_TEXTURE_ADDRESS_CLAMP &&
        linearClampSampler.desc.AddressV == D3D11_TEXTURE_ADDRESS_CLAMP &&
        linearClampSampler.desc.MaxLOD == D3D11_FLOAT32_MAX,
        "R98 linear/clamp sampler translation");
    require(
        samplerOwner.initialize(d3d.device, linearClampStage),
        "R98 sampler owner reinitialize with linear clamp");

    auto unsupportedSamplerStage = stages[0];
    unsupportedSamplerStage.minFilter = D3DTEXF_ANISOTROPIC;
    require(
        !translate_fixed_function_sampler(unsupportedSamplerStage).exact,
        "R98 anisotropic sampler translation must fail closed");
    require(
        !samplerOwner.initialize(d3d.device, unsupportedSamplerStage),
        "R98 unsupported sampler owner must fail closed");
    require(
        !samplerOwner.ready(),
        "R98 failed sampler reinitialize must leave owner dormant");
    require(
        samplerOwner.initialize(d3d.device, stages[0]),
        "R98 sampler owner recovery after fail-closed reset");

    ID3D11VertexShader* vertexShader = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateVertexShader(
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(),
            nullptr,
            &vertexShader)) &&
        vertexShader != nullptr,
        "CreateVertexShader R93");
    d3d.context->VSSetShader(vertexShader, nullptr, 0);

    NativeFixedFunctionTransformBuffer owner;
    require(!owner.ready(), "R96 owner must start dormant");
    require(owner.upload_generation() == 0,
            "R96 owner generation must start at zero");
    require(owner.initialize(d3d.device),
            "R96 owner initialize");

    NativeFixedFunctionPipelineBundle pipelineBundle;
    require(!pipelineBundle.ready(),
            "R97 bundle must start dormant");
    require(
        pipelineBundle.initialize(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype),
        "R97 bundle initialize");
    require(
        pipelineBundle.ready() &&
        pipelineBundle.device() == d3d.device &&
        pipelineBundle.vertex_shader() != nullptr &&
        pipelineBundle.pixel_shader() != nullptr &&
        pipelineBundle.input_layout() != nullptr &&
        pipelineBundle.transform_buffer().ready(),
        "R97 bundle owned-object readiness");

    auto inexactLayout = inputLayout;
    inexactLayout.exact = false;
    require(
        !pipelineBundle.initialize(
            d3d.device, inexactLayout, vertexPrototype, pixelPrototype),
        "R97 inexact input layout must fail closed");
    require(
        !pipelineBundle.ready(),
        "R97 failed reinitialize must leave bundle dormant");
    require(
        pipelineBundle.initialize(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype),
        "R97 bundle reinitialize after fail-closed reset");
    require(
        pipelineBundle.ready(),
        "R97 bundle must recover after exact reinitialize");

    D3D11_BUFFER_DESC observedDesc{};
    owner.buffer()->GetDesc(&observedDesc);
    require(
        observedDesc.ByteWidth == expectedConstantBytes &&
        observedDesc.Usage == D3D11_USAGE_DYNAMIC &&
        observedDesc.BindFlags == D3D11_BIND_CONSTANT_BUFFER &&
        observedDesc.CPUAccessFlags == D3D11_CPU_ACCESS_WRITE,
        "constant-buffer descriptor contract");

    DevicePair otherDevice = create_warp_device();
    require(
        !owner.upload_and_bind(otherDevice.context, transform),
        "R96 foreign device context must fail closed");
    require(owner.upload_generation() == 0,
            "R96 failed upload must not advance generation");

    const auto incompleteTransform =
        generate_fixed_function_transform_constants(
            identity, identity, identity, false);
    require(
        !owner.upload_and_bind(d3d.context, incompleteTransform),
        "R96 inexact transform must fail closed");
    require(owner.upload_generation() == 0,
            "R96 inexact upload must not advance generation");

    require(
        owner.upload_and_bind(d3d.context, transform),
        "R96 owner upload and b0 bind");
    require(owner.upload_generation() == 1,
            "R96 successful upload generation");

    ID3D11Buffer* boundBuffer = nullptr;
    d3d.context->VSGetConstantBuffers(0, 1, &boundBuffer);
    require(
        boundBuffer != nullptr && boundBuffer == owner.buffer(),
        "VS b0 constant-buffer binding");
    if (boundBuffer)
        boundBuffer->Release();

    D3DMATRIX translatedWorld = world;
    translatedWorld._42 = 4.0f;
    const auto transform2 =
        generate_fixed_function_transform_constants(
            translatedWorld, view, identity, true);
    require(transform2.exact(), "R96 second transform prerequisite");
    require(
        owner.upload_and_bind(d3d.context, transform2),
        "R96 second owner upload");
    require(owner.upload_generation() == 2,
            "R96 upload generation must advance monotonically");

    ID3D11Buffer* nullBuffer = nullptr;
    d3d.context->VSSetConstantBuffers(0, 1, &nullBuffer);
    d3d.context->VSSetShader(nullptr, nullptr, 0);

    samplerOwner.shutdown();
    require(!samplerOwner.ready(),
            "R98 sampler shutdown must release owner resources");
    require(
        samplerOwner.device() == nullptr &&
        samplerOwner.sampler() == nullptr,
        "R98 sampler shutdown must clear owned objects");

    pipelineBundle.shutdown();
    require(!pipelineBundle.ready(),
            "R97 shutdown must release bundle resources");
    require(
        pipelineBundle.device() == nullptr &&
        pipelineBundle.vertex_shader() == nullptr &&
        pipelineBundle.pixel_shader() == nullptr &&
        pipelineBundle.input_layout() == nullptr &&
        !pipelineBundle.transform_buffer().ready(),
        "R97 shutdown must clear owned objects");

    owner.shutdown();
    require(!owner.ready(), "R96 shutdown must release owner resources");
    require(owner.buffer() == nullptr,
            "R96 shutdown must clear constant buffer");
    require(owner.upload_generation() == 0,
            "R96 shutdown must reset generation");

    require(owner.initialize(d3d.device),
            "R96 owner reinitialize after shutdown");
    require(owner.ready(), "R96 owner must be ready after reinitialize");
    owner.shutdown();

    otherDevice.context->Release();
    otherDevice.device->Release();
    vertexShader->Release();
    d3d.context->Release();
    d3d.device->Release();
    reflection->Release();
    vertexBytecode->Release();

    std::cout << "DX11 constant buffer probe R95: PASS\n";
    std::cout << "DX11 constant buffer lifetime R96: PASS\n";
    std::cout << "DX11 fixed-function pipeline bundle R97: PASS\n";
    std::cout << "DX11 fixed-function sampler ownership R98: PASS\n";
    return 0;
}
