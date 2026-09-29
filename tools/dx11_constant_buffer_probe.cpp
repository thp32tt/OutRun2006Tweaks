#include <cstdlib>
#include <cstring>
#include <iostream>

#include <d3dcompiler.h>
#include <d3d11.h>
#include <d3d11shader.h>

#include "vr/d3d11/native_backend.hpp"
#include "vr/d3d11/pipeline_translation.hpp"
#include "vr/d3d11/resource_translation.hpp"

namespace
{
    using outrun::vr::dx11::FixedFunctionStageState;
    using outrun::vr::dx11::NativeFixedFunctionPipelineBundle;
    using outrun::vr::dx11::NativeFixedFunctionSamplerState;
    using outrun::vr::dx11::NativeFixedFunctionTextureView;
    using outrun::vr::dx11::NativeFixedFunctionTransformBuffer;
    using outrun::vr::dx11::TextureMutationUpdateKind;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::generate_fixed_function_transform_constants;
    using outrun::vr::dx11::generate_fixed_function_vertex_shader_prototype;
    using outrun::vr::dx11::translate_fixed_function_sampler;
    using outrun::vr::dx11::translate_texture_mutation;
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

    D3D11_TEXTURE2D_DESC textureDesc{};
    textureDesc.Width = 4;
    textureDesc.Height = 4;
    textureDesc.MipLevels = 1;
    textureDesc.ArraySize = 1;
    textureDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    textureDesc.SampleDesc.Count = 1;
    textureDesc.Usage = D3D11_USAGE_DEFAULT;
    textureDesc.BindFlags = D3D11_BIND_SHADER_RESOURCE;

    ID3D11Texture2D* fixedFunctionTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &textureDesc, nullptr, &fixedFunctionTexture)) &&
        fixedFunctionTexture != nullptr,
        "R99 translated texture prerequisite");

    NativeFixedFunctionTextureView textureView;
    require(!textureView.ready(),
            "R99 texture view must start dormant");
    require(
        textureView.initialize(
            d3d.device, fixedFunctionTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, 0),
        "R99 texture view initialize");
    require(
        textureView.ready() &&
        textureView.device() == d3d.device &&
        textureView.texture() == fixedFunctionTexture &&
        textureView.srv() != nullptr,
        "R99 texture/SRV owner readiness");

    D3D11_SHADER_RESOURCE_VIEW_DESC observedTextureSrv{};
    textureView.srv()->GetDesc(&observedTextureSrv);
    require(
        observedTextureSrv.Format == DXGI_FORMAT_B8G8R8A8_UNORM &&
        observedTextureSrv.ViewDimension == D3D11_SRV_DIMENSION_TEXTURE2D &&
        observedTextureSrv.Texture2D.MostDetailedMip == 0 &&
        observedTextureSrv.Texture2D.MipLevels == 1,
        "R99 created Texture2D SRV descriptor");

    require(
        !textureView.initialize(
            d3d.device, fixedFunctionTexture,
            D3DFMT_A8B8G8R8, D3DPOOL_DEFAULT, 0),
        "R99 mismatched translated format must fail closed");
    require(!textureView.ready(),
            "R99 format failure must leave owner dormant");

    require(
        !textureView.initialize(
            d3d.device, fixedFunctionTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_MANAGED, 0),
        "R99 managed source without CPU shadow must fail closed");
    require(!textureView.ready(),
            "R99 managed-source failure must leave owner dormant");

    D3D11_TEXTURE2D_DESC noSrvDesc = textureDesc;
    noSrvDesc.BindFlags = D3D11_BIND_RENDER_TARGET;
    ID3D11Texture2D* noSrvTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &noSrvDesc, nullptr, &noSrvTexture)) &&
        noSrvTexture != nullptr,
        "R99 no-SRV negative texture prerequisite");
    require(
        !textureView.initialize(
            d3d.device, noSrvTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, 0),
        "R99 texture without shader-resource bind must fail closed");
    require(!textureView.ready(),
            "R99 bind failure must leave owner dormant");

    require(
        textureView.initialize(
            d3d.device, fixedFunctionTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, 0),
        "R99 texture view recovery after fail-closed reset");

    const auto dynamicDiscardTexture = translate_texture_mutation(
        D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC, D3DLOCK_DISCARD, true);
    require(
        dynamicDiscardTexture.planExact &&
        dynamicDiscardTexture.kind ==
            TextureMutationUpdateKind::DynamicMapWriteDiscard &&
        dynamicDiscardTexture.mapType == D3D11_MAP_WRITE_DISCARD &&
        dynamicDiscardTexture.requiresFullSubresource &&
        !dynamicDiscardTexture.requiresCpuShadow,
        "R100 full dynamic texture discard maps exactly");

    const auto partialDiscardTexture = translate_texture_mutation(
        D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC, D3DLOCK_DISCARD, false);
    require(
        !partialDiscardTexture.planExact &&
        partialDiscardTexture.kind == TextureMutationUpdateKind::Unsupported &&
        partialDiscardTexture.requiresFullSubresource,
        "R100 partial dynamic texture discard must fail closed");

    const auto plainDynamicTexture = translate_texture_mutation(
        D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC, 0, true);
    require(
        !plainDynamicTexture.planExact &&
        plainDynamicTexture.kind == TextureMutationUpdateKind::Unsupported &&
        plainDynamicTexture.requiresFullSubresource,
        "R100 plain dynamic texture write must fail closed");

    const auto noOverwriteTexture = translate_texture_mutation(
        D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC, D3DLOCK_NOOVERWRITE, true);
    require(
        !noOverwriteTexture.planExact &&
        noOverwriteTexture.kind == TextureMutationUpdateKind::Unsupported,
        "R100 texture NOOVERWRITE must fail closed");

    const auto managedTextureWrite = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, 0, true);
    require(
        !managedTextureWrite.planExact &&
        managedTextureWrite.kind ==
            TextureMutationUpdateKind::ManagedCpuShadowWrite &&
        managedTextureWrite.requiresCpuShadow,
        "R100 managed texture write requires CPU shadow");

    const auto managedTextureRead = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, D3DLOCK_READONLY, true);
    require(
        !managedTextureRead.planExact &&
        managedTextureRead.kind ==
            TextureMutationUpdateKind::ManagedCpuShadowRead &&
        managedTextureRead.requiresCpuShadow,
        "R100 managed texture read requires CPU shadow");

    D3D11_TEXTURE2D_DESC dynamicTextureDesc = textureDesc;
    dynamicTextureDesc.Usage = D3D11_USAGE_DYNAMIC;
    dynamicTextureDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;

    ID3D11Texture2D* dynamicTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &dynamicTextureDesc, nullptr, &dynamicTexture)) &&
        dynamicTexture != nullptr,
        "R101 dynamic texture prerequisite");

    NativeFixedFunctionTextureView dynamicTextureView;
    require(
        dynamicTextureView.initialize(
            d3d.device, dynamicTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC),
        "R101 dynamic texture view initialize");
    require(
        dynamicTextureView.ready() &&
        !dynamicTextureView.content_ready() &&
        dynamicTextureView.upload_generation() == 0,
        "R101 dynamic texture content starts uninitialized");

    std::array<unsigned char, 80> dynamicSource{};
    constexpr UINT dynamicSourcePitch = 20;
    constexpr UINT dynamicRowBytes = 16;
    constexpr UINT dynamicRows = 4;
    for (UINT row = 0; row < dynamicRows; ++row) {
        for (UINT column = 0; column < dynamicRowBytes; ++column) {
            dynamicSource[static_cast<std::size_t>(row) * dynamicSourcePitch + column] =
                static_cast<unsigned char>(row * 32 + column + 1);
        }
    }

    require(
        !dynamicTextureView.upload_full_discard(
            d3d.context, dynamicSource.data(), dynamicRowBytes - 1, dynamicRows),
        "R101 short source row pitch must fail closed");
    require(
        !dynamicTextureView.upload_full_discard(
            d3d.context, dynamicSource.data(), dynamicSourcePitch, dynamicRows - 1),
        "R101 partial source rows must fail closed");
    require(
        dynamicTextureView.upload_generation() == 0 &&
        !dynamicTextureView.content_ready(),
        "R101 rejected uploads must not advance content generation");

    DevicePair textureOtherDevice = create_warp_device();
    require(
        !dynamicTextureView.upload_full_discard(
            textureOtherDevice.context,
            dynamicSource.data(), dynamicSourcePitch, dynamicRows),
        "R101 foreign device context must fail closed");
    require(
        dynamicTextureView.upload_generation() == 0,
        "R101 foreign-context rejection must preserve generation");

    require(
        dynamicTextureView.upload_full_discard(
            d3d.context, dynamicSource.data(), dynamicSourcePitch, dynamicRows),
        "R101 full dynamic texture discard upload");
    require(
        dynamicTextureView.content_ready() &&
        dynamicTextureView.upload_generation() == 1,
        "R101 successful upload advances content generation");

    D3D11_TEXTURE2D_DESC stagingDesc = dynamicTextureDesc;
    stagingDesc.Usage = D3D11_USAGE_STAGING;
    stagingDesc.BindFlags = 0;
    stagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;

    ID3D11Texture2D* stagingTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &stagingDesc, nullptr, &stagingTexture)) &&
        stagingTexture != nullptr,
        "R101 staging readback prerequisite");
    d3d.context->CopyResource(stagingTexture, dynamicTexture);

    D3D11_MAPPED_SUBRESOURCE stagingMap{};
    require(
        SUCCEEDED(d3d.context->Map(
            stagingTexture, 0, D3D11_MAP_READ, 0, &stagingMap)) &&
        stagingMap.pData != nullptr &&
        stagingMap.RowPitch >= dynamicRowBytes,
        "R101 staging readback map");
    for (UINT row = 0; row < dynamicRows; ++row) {
        const auto* observed =
            static_cast<const unsigned char*>(stagingMap.pData) +
            static_cast<std::size_t>(row) * stagingMap.RowPitch;
        const auto* expected =
            dynamicSource.data() +
            static_cast<std::size_t>(row) * dynamicSourcePitch;
        require(
            std::memcmp(observed, expected, dynamicRowBytes) == 0,
            "R101 uploaded texture bytes must match source rows");
    }
    d3d.context->Unmap(stagingTexture, 0);

    dynamicSource[0] ^= 0x5a;
    require(
        dynamicTextureView.upload_full_discard(
            d3d.context, dynamicSource.data(), dynamicSourcePitch, dynamicRows),
        "R101 second full-discard upload");
    require(
        dynamicTextureView.upload_generation() == 2,
        "R101 upload generation must advance monotonically");

    NativeManagedTextureShadow managedShadow;
    require(
        managedShadow.initialize(D3DFMT_A8R8G8B8, 4, 4),
        "R102 managed shadow initialize");
    require(
        managedShadow.ready() &&
        !managedShadow.shadow_valid() &&
        !managedShadow.mirror_ready() &&
        managedShadow.shadow_version() == 0 &&
        managedShadow.device_generation() == 1,
        "R102 managed shadow starts allocated but content-invalid");

    std::array<unsigned char, 80> managedSource{};
    constexpr UINT managedSourcePitch = 20;
    constexpr UINT managedRowBytes = 16;
    constexpr UINT managedRows = 4;
    for (UINT row = 0; row < managedRows; ++row) {
        for (UINT column = 0; column < managedRowBytes; ++column) {
            managedSource[static_cast<std::size_t>(row) * managedSourcePitch + column] =
                static_cast<unsigned char>(0x40 + row * 16 + column);
        }
    }

    require(
        !managedShadow.write_full(
            managedSource.data(), managedRowBytes - 1, managedRows),
        "R102 managed shadow short source pitch must fail closed");
    require(
        !managedShadow.write_full(
            managedSource.data(), managedSourcePitch, managedRows - 1),
        "R102 managed shadow partial rows must fail closed");
    require(
        managedShadow.shadow_version() == 0 &&
        !managedShadow.shadow_valid(),
        "R102 rejected managed writes must preserve invalid version");

    require(
        managedShadow.write_full(
            managedSource.data(), managedSourcePitch, managedRows),
        "R102 managed shadow full write");
    require(
        managedShadow.shadow_valid() &&
        managedShadow.shadow_version() == 1 &&
        !managedShadow.mirror_ready(),
        "R102 managed write advances shadow version and invalidates mirror");

    std::array<unsigned char, 96> managedReadback{};
    constexpr UINT managedReadbackPitch = 24;
    require(
        managedShadow.read_full(
            managedReadback.data(), managedReadbackPitch, managedRows),
        "R102 managed shadow full read");
    for (UINT row = 0; row < managedRows; ++row) {
        require(
            std::memcmp(
                managedReadback.data() +
                    static_cast<std::size_t>(row) * managedReadbackPitch,
                managedSource.data() +
                    static_cast<std::size_t>(row) * managedSourcePitch,
                managedRowBytes) == 0,
            "R102 managed shadow readback must match source rows");
    }

    managedShadow.note_mirror_uploaded();
    require(
        managedShadow.mirror_ready() &&
        managedShadow.lifetime_state().mirrorGeneration == 1 &&
        managedShadow.lifetime_state().mirrorShadowVersion == 1,
        "R102 managed mirror acknowledgment matches shadow generation");

    managedShadow.observe_device_reset();
    require(
        managedShadow.device_generation() == 2 &&
        managedShadow.shadow_valid() &&
        managedShadow.shadow_version() == 1 &&
        !managedShadow.mirror_ready(),
        "R102 Reset preserves CPU shadow and invalidates GPU mirror");

    managedReadback.fill(0);
    require(
        managedShadow.read_full(
            managedReadback.data(), managedReadbackPitch, managedRows),
        "R102 managed shadow remains readable after Reset");
    require(
        std::memcmp(
            managedReadback.data(),
            managedSource.data(),
            managedRowBytes) == 0,
        "R102 Reset-preserved first row must match");

    managedShadow.note_mirror_uploaded();
    require(
        managedShadow.mirror_ready() &&
        managedShadow.lifetime_state().mirrorGeneration == 2,
        "R102 post-Reset mirror acknowledgment uses new device generation");

    managedSource[0] ^= 0x33;
    require(
        managedShadow.write_full(
            managedSource.data(), managedSourcePitch, managedRows),
        "R102 second managed shadow full write");
    require(
        managedShadow.shadow_version() == 2 &&
        !managedShadow.mirror_ready(),
        "R102 second shadow write invalidates acknowledged mirror");

    NativeManagedTextureShadow unsupportedManagedShadow;
    require(
        !unsupportedManagedShadow.initialize(D3DFMT_DXT1, 4, 4),
        "R102 compressed managed shadow must fail closed");
    require(
        !unsupportedManagedShadow.ready(),
        "R102 failed managed shadow initialize stays dormant");

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

    managedShadow.shutdown();
    require(
        !managedShadow.ready() &&
        !managedShadow.shadow_valid() &&
        !managedShadow.mirror_ready() &&
        managedShadow.shadow_version() == 0 &&
        managedShadow.device_generation() == 1,
        "R102 managed shadow shutdown resets storage and lifetime");

    dynamicTextureView.shutdown();
    require(
        !dynamicTextureView.ready() &&
        !dynamicTextureView.content_ready() &&
        dynamicTextureView.upload_generation() == 0,
        "R101 dynamic texture shutdown resets ownership and content generation");

    textureView.shutdown();
    require(!textureView.ready(),
            "R99 texture view shutdown must release owner resources");
    require(
        textureView.device() == nullptr &&
        textureView.texture() == nullptr &&
        textureView.srv() == nullptr,
        "R99 texture view shutdown must clear owned objects");

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

    stagingTexture->Release();
    dynamicTexture->Release();
    textureOtherDevice.context->Release();
    textureOtherDevice.device->Release();
    noSrvTexture->Release();
    fixedFunctionTexture->Release();
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
    std::cout << "DX11 fixed-function texture view ownership R99: PASS\n";
    std::cout << "DX11 texture mutation readiness R100: PASS\n";
    std::cout << "DX11 fixed-function texture upload R101: PASS\n";
    std::cout << "DX11 managed texture shadow lifetime R102: PASS\n";
    return 0;
}
