#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>

#include <d3dcompiler.h>
#include <d3d11.h>
#include <d3d11shader.h>

#include "vr/d3d11/native_backend.hpp"
#include "vr/d3d11/pipeline_translation.hpp"
#include "vr/d3d11/resource_translation.hpp"
#include "vr/d3d11/surface_mirror.hpp"
#include "vr/d3d11/triangle_fan_index_buffer.hpp"

namespace
{
    using outrun::vr::dx11::FixedFunctionStageState;
    using outrun::vr::dx11::NativeFixedFunctionPipelineBundle;
    using outrun::vr::dx11::NativeFixedFunctionRenderStateBundle;
    using outrun::vr::dx11::NativeFixedFunctionOutputStateBinding;
    using outrun::vr::dx11::NativeFixedFunctionSamplerState;
    using outrun::vr::dx11::NativeFixedFunctionTextureView;
    using outrun::vr::dx11::NativeFixedFunctionTransformBuffer;
    using outrun::vr::dx11::NativeManagedBufferShadow;
    using outrun::vr::dx11::NativeManagedTextureRegistry;
    using outrun::vr::dx11::NativeManagedTextureShadow;
    using outrun::vr::dx11::NativeManagedTextureStageReadiness;
    using outrun::vr::dx11::NativeSurfacePairReadiness;
    using outrun::vr::dx11::NativeTriangleFanIndexBuffer;
    using outrun::vr::dx11::NativeTriangleFanIndexBufferReadiness;
    using outrun::vr::dx11::PipelineUnsupportedBlend;
    using outrun::vr::dx11::compose_fixed_function_activation_readiness;
    using outrun::vr::dx11::compose_fixed_function_nonindexed_triangle_fan_geometry_readiness;
    using outrun::vr::dx11::validate_fixed_function_activation_snapshot;
    using outrun::vr::dx11::validate_fixed_function_nonindexed_triangle_fan_geometry_snapshot;
    using outrun::vr::dx11::ResourceRole;
    using outrun::vr::dx11::TextureMutationUpdateKind;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::generate_fixed_function_transform_constants;
    using outrun::vr::dx11::generate_fixed_function_vertex_shader_prototype;
    using outrun::vr::dx11::translate_fixed_function_sampler;
    using outrun::vr::dx11::translate_pipeline;
    using outrun::vr::dx11::translate_texture_mutation;
    using outrun::vr::dx11::translate_vertex_input_layout;
    using outrun::vr::dx11::bind_fixed_function_texture_stage_for_observation;

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

    ID3DBlob* compile_geometry_shader()
    {
        static const char source[] = R"(
struct GSIn { float4 position : SV_Position; };
struct GSOut { float4 position : SV_Position; };
[maxvertexcount(1)]
void main(point GSIn input[1], inout PointStream<GSOut> outputStream)
{
    GSOut output;
    output.position = input[0].position;
    outputStream.Append(output);
}
)";
        ID3DBlob* bytecode = nullptr;
        ID3DBlob* diagnostics = nullptr;
        const HRESULT hr = D3DCompile(
            source,
            sizeof(source) - 1,
            "OutRunR147IsolationGeometryShader",
            nullptr,
            nullptr,
            "main",
            "gs_4_0",
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0,
            &bytecode,
            &diagnostics);

        if (diagnostics)
            diagnostics->Release();

        require(
            SUCCEEDED(hr) && bytecode != nullptr,
            "D3DCompile R147 isolation geometry shader");
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

    auto translatedLodStage = linearClampStage;
    translatedLodStage.mipLodBiasBits = 0x3F000000u;
    translatedLodStage.maxMipLevel = 1u;
    const auto translatedLodSampler =
        translate_fixed_function_sampler(translatedLodStage);
    require(
        translatedLodSampler.exact &&
        translatedLodSampler.desc.MipLODBias == 0.5f &&
        translatedLodSampler.desc.MinLOD == 1.0f &&
        translatedLodSampler.desc.MaxLOD == D3D11_FLOAT32_MAX,
        "sampler LOD bias/MAXMIPLEVEL translation");
    require(
        samplerOwner.initialize(d3d.device, translatedLodStage),
        "sampler owner accepts translated LOD state");
    D3D11_SAMPLER_DESC observedLodSampler{};
    samplerOwner.sampler()->GetDesc(&observedLodSampler);
    require(
        observedLodSampler.MipLODBias == 0.5f &&
        observedLodSampler.MinLOD == 1.0f &&
        observedLodSampler.MaxLOD == D3D11_FLOAT32_MAX,
        "created sampler preserves translated LOD state");

    auto unsupportedLodBiasStage = linearClampStage;
    unsupportedLodBiasStage.mipLodBiasBits = 0x41800000u;
    require(
        !translate_fixed_function_sampler(unsupportedLodBiasStage).exact,
        "out-of-range sampler MIP LOD bias must fail closed");

    auto unsupportedMaxMipStage = linearClampStage;
    unsupportedMaxMipStage.maxMipLevel = D3D11_REQ_MIP_LEVELS;
    require(
        !translate_fixed_function_sampler(unsupportedMaxMipStage).exact,
        "out-of-range sampler MAXMIPLEVEL must fail closed");

    auto unsupportedNoMipLodStage = stages[0];
    unsupportedNoMipLodStage.maxMipLevel = 1u;
    require(
        !translate_fixed_function_sampler(unsupportedNoMipLodStage).exact,
        "no-mip non-default sampler LOD must fail closed");

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

    constexpr UINT textureStageSlot = 3;
    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, textureStageSlot, samplerOwner, textureView),
        "DX11 dormant texture-stage same-device bind");

    ID3D11SamplerState* observedStageSampler = nullptr;
    ID3D11ShaderResourceView* observedStageSrv = nullptr;
    d3d.context->PSGetSamplers(
        textureStageSlot, 1, &observedStageSampler);
    d3d.context->PSGetShaderResources(
        textureStageSlot, 1, &observedStageSrv);
    require(
        observedStageSampler == samplerOwner.sampler() &&
        observedStageSrv == textureView.srv(),
        "DX11 dormant texture-stage binding preserves sampler/SRV identity");

    const auto textureStageBindingReady =
        outrun::vr::dx11::observe_fixed_function_texture_stage_binding(
            d3d.context, textureStageSlot, samplerOwner, textureView);
    require(
        textureStageBindingReady.inputValid &&
        textureStageBindingReady.slotValid &&
        textureStageBindingReady.ownersReady &&
        textureStageBindingReady.devicesMatch &&
        textureStageBindingReady.contextMatches &&
        textureStageBindingReady.boundExact &&
        textureStageBindingReady.ready &&
        textureStageBindingReady.slot == textureStageSlot &&
        textureStageBindingReady.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_texture_stage_binding_snapshot(
            d3d.context, textureStageSlot, samplerOwner, textureView,
            textureStageBindingReady.snapshotToken),
        "R132 texture-stage binding issues exact sampler/SRV snapshot");
    if (observedStageSampler)
        observedStageSampler->Release();
    if (observedStageSrv)
        observedStageSrv->Release();

    require(
        !bind_fixed_function_texture_stage_for_observation(
            d3d.context, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT,
            samplerOwner, textureView),
        "DX11 dormant texture-stage sampler slot overflow fails closed");
    require(
        !bind_fixed_function_texture_stage_for_observation(
            d3d.context, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT,
            samplerOwner, textureView),
        "DX11 dormant texture-stage SRV slot overflow fails closed");

    DevicePair textureStageOtherDevice = create_warp_device();
    require(
        !bind_fixed_function_texture_stage_for_observation(
            textureStageOtherDevice.context, 0, samplerOwner, textureView),
        "DX11 dormant texture-stage foreign context fails closed");

    NativeFixedFunctionSamplerState foreignStageSampler;
    require(
        foreignStageSampler.initialize(
            textureStageOtherDevice.device, stages[0]),
        "DX11 dormant texture-stage foreign sampler prerequisite");
    require(
        !bind_fixed_function_texture_stage_for_observation(
            d3d.context, 0, foreignStageSampler, textureView),
        "DX11 dormant texture-stage cross-device owners fail closed");
    foreignStageSampler.shutdown();
    textureStageOtherDevice.context->Release();
    textureStageOtherDevice.device->Release();

    ID3D11SamplerState* nullSampler = nullptr;
    ID3D11ShaderResourceView* nullSrv = nullptr;
    d3d.context->PSSetSamplers(
        textureStageSlot, 1, &nullSampler);
    d3d.context->PSSetShaderResources(
        textureStageSlot, 1, &nullSrv);

    D3D11_TEXTURE2D_DESC hazardTextureDesc = textureDesc;
    hazardTextureDesc.BindFlags =
        D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_RENDER_TARGET;
    ID3D11Texture2D* hazardTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &hazardTextureDesc, nullptr, &hazardTexture)) &&
        hazardTexture != nullptr,
        "DX11 dormant texture-stage output hazard texture prerequisite");

    NativeFixedFunctionTextureView hazardTextureView;
    require(
        hazardTextureView.initialize(
            d3d.device, hazardTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, 0),
        "DX11 dormant texture-stage output hazard view prerequisite");

    ID3D11RenderTargetView* hazardRtv = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateRenderTargetView(
            hazardTexture, nullptr, &hazardRtv)) &&
        hazardRtv != nullptr,
        "DX11 dormant texture-stage output hazard RTV prerequisite");
    d3d.context->OMSetRenderTargets(1, &hazardRtv, nullptr);

    require(
        !bind_fixed_function_texture_stage_for_observation(
            d3d.context, textureStageSlot, samplerOwner, hazardTextureView),
        "DX11 dormant texture-stage output hazard fails closed");

    ID3D11SamplerState* hazardBoundSampler = nullptr;
    ID3D11ShaderResourceView* hazardBoundSrv = nullptr;
    d3d.context->PSGetSamplers(
        textureStageSlot, 1, &hazardBoundSampler);
    d3d.context->PSGetShaderResources(
        textureStageSlot, 1, &hazardBoundSrv);
    require(
        hazardBoundSampler == nullptr && hazardBoundSrv == nullptr,
        "DX11 dormant texture-stage failed bind clears partial state");
    if (hazardBoundSampler)
        hazardBoundSampler->Release();
    if (hazardBoundSrv)
        hazardBoundSrv->Release();

    d3d.context->OMSetRenderTargets(0, nullptr, nullptr);
    hazardRtv->Release();
    hazardTextureView.shutdown();
    hazardTexture->Release();

    const auto managedVertexWritePlan = translate_buffer_mutation(
        ResourceRole::Vertex, D3DPOOL_MANAGED, D3DUSAGE_WRITEONLY, 0);
    require(
        managedVertexWritePlan.planExact &&
        managedVertexWritePlan.kind ==
            BufferMutationUpdateKind::ManagedCpuShadowWrite &&
        managedVertexWritePlan.requiresCpuShadow,
        "R121 managed VB write is an exact CPU-shadow mutation plan");

    const auto managedIndexReadPlan = translate_buffer_mutation(
        ResourceRole::Index, D3DPOOL_MANAGED, 0, D3DLOCK_READONLY);
    require(
        managedIndexReadPlan.planExact &&
        managedIndexReadPlan.kind ==
            BufferMutationUpdateKind::ManagedCpuShadowRead &&
        managedIndexReadPlan.requiresCpuShadow,
        "R121 managed IB read is an exact CPU-shadow mutation plan");

    const auto managedDiscardPlan = translate_buffer_mutation(
        ResourceRole::Vertex, D3DPOOL_MANAGED, D3DUSAGE_WRITEONLY,
        D3DLOCK_DISCARD);
    require(
        !managedDiscardPlan.planExact &&
        managedDiscardPlan.kind == BufferMutationUpdateKind::Unsupported,
        "R121 managed DISCARD remains fail-closed");

    const auto managedNoOverwritePlan = translate_buffer_mutation(
        ResourceRole::Index, D3DPOOL_MANAGED, D3DUSAGE_WRITEONLY,
        D3DLOCK_NOOVERWRITE);
    require(
        !managedNoOverwritePlan.planExact &&
        managedNoOverwritePlan.kind == BufferMutationUpdateKind::Unsupported,
        "R121 managed NOOVERWRITE remains fail-closed");

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

    NativeManagedBufferShadow managedVertexBuffer;
    require(
        managedVertexBuffer.initialize(
            ResourceRole::Vertex, 256, D3DUSAGE_WRITEONLY),
        "R113 managed vertex-buffer shadow initialize");
    require(
        managedVertexBuffer.ready() &&
        !managedVertexBuffer.shadow_valid() &&
        !managedVertexBuffer.mirror_ready(),
        "R113 managed vertex-buffer shadow starts content-invalid");

    std::array<unsigned char, 256> managedVertexBytes{};
    for (std::size_t index = 0; index < managedVertexBytes.size(); ++index)
        managedVertexBytes[index] =
            static_cast<unsigned char>(0x20u + index);

    require(
        !managedVertexBuffer.write_range(
            4, managedVertexBytes.data() + 4, 8),
        "R113 first managed buffer write must cover the full resource");
    require(
        managedVertexBuffer.write_range(
            0, managedVertexBytes.data(),
            static_cast<UINT>(managedVertexBytes.size())) &&
        managedVertexBuffer.shadow_valid() &&
        managedVertexBuffer.shadow_version() == 1,
        "R113 full managed vertex-buffer write establishes CPU shadow");
    require(
        managedVertexBuffer.recreate_and_upload_mirror(d3d.device) &&
        managedVertexBuffer.mirror_ready() &&
        managedVertexBuffer.mirror_descriptor_exact(d3d.device),
        "R113 managed vertex-buffer mirror upload");

    const auto managedVertexReady =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexReady.inputValid &&
        managedVertexReady.shadowValid &&
        managedVertexReady.resourcesOwned &&
        managedVertexReady.lifetimeCurrent &&
        managedVertexReady.deviceMatches &&
        managedVertexReady.descriptorExact &&
        managedVertexReady.mutationPlanExact &&
        managedVertexReady.ready &&
        managedVertexReady.role == ResourceRole::Vertex &&
        managedVertexReady.deviceGeneration == 1 &&
        managedVertexReady.shadowVersion == 1 &&
        managedVertexReady.mirrorGeneration == 1 &&
        managedVertexReady.mirrorShadowVersion == 1 &&
        managedVertexReady.mirrorInstanceGeneration == 1 &&
        managedVertexReady.snapshotToken != 0 &&
        managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexReady.snapshotToken),
        "R119 managed vertex-buffer mirror issues exact readiness snapshot");
    require(
        managedVertexReady.mutationPlanExact,
        "R127 managed-buffer readiness consumes exact mutation plan");
    const auto managedVertexInitialToken = managedVertexReady.snapshotToken;

    DevicePair managedBufferOtherDevice = create_warp_device();
    const auto managedVertexForeignReady =
        managedVertexBuffer.mirror_readiness(managedBufferOtherDevice.device);
    require(
        managedVertexForeignReady.inputValid &&
        managedVertexForeignReady.shadowValid &&
        managedVertexForeignReady.resourcesOwned &&
        managedVertexForeignReady.lifetimeCurrent &&
        !managedVertexForeignReady.deviceMatches &&
        !managedVertexForeignReady.descriptorExact &&
        !managedVertexForeignReady.ready &&
        managedVertexForeignReady.snapshotToken == 0 &&
        !managedVertexBuffer.validate_mirror_readiness_snapshot(
            managedBufferOtherDevice.device, managedVertexInitialToken),
        "R119 foreign device cannot claim managed-buffer readiness");
    managedBufferOtherDevice.context->Release();
    managedBufferOtherDevice.device->Release();

    D3D11_BUFFER_DESC managedVertexDesc{};
    managedVertexBuffer.mirror_buffer()->GetDesc(&managedVertexDesc);
    require(
        managedVertexDesc.ByteWidth == managedVertexBytes.size() &&
        managedVertexDesc.Usage == D3D11_USAGE_DEFAULT &&
        managedVertexDesc.BindFlags == D3D11_BIND_VERTEX_BUFFER &&
        managedVertexDesc.CPUAccessFlags == 0,
        "R113 managed vertex-buffer descriptor contract");

    D3D11_BUFFER_DESC managedVertexStagingDesc = managedVertexDesc;
    managedVertexStagingDesc.Usage = D3D11_USAGE_STAGING;
    managedVertexStagingDesc.BindFlags = 0;
    managedVertexStagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Buffer* managedVertexStaging = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateBuffer(
            &managedVertexStagingDesc, nullptr, &managedVertexStaging)) &&
        managedVertexStaging != nullptr,
        "R113 managed vertex-buffer staging prerequisite");
    d3d.context->CopyResource(
        managedVertexStaging, managedVertexBuffer.mirror_buffer());
    D3D11_MAPPED_SUBRESOURCE managedVertexMap{};
    require(
        SUCCEEDED(d3d.context->Map(
            managedVertexStaging, 0, D3D11_MAP_READ, 0, &managedVertexMap)) &&
        managedVertexMap.pData != nullptr &&
        std::memcmp(
            managedVertexMap.pData,
            managedVertexBytes.data(),
            managedVertexBytes.size()) == 0,
        "R113 managed vertex-buffer mirror bytes");
    d3d.context->Unmap(managedVertexStaging, 0);
    managedVertexStaging->Release();

    const unsigned char managedVertexPatch[] = {0xe1, 0xe2, 0xe3, 0xe4};
    require(
        managedVertexBuffer.write_range(
            8, managedVertexPatch,
            static_cast<UINT>(sizeof(managedVertexPatch))) &&
        managedVertexBuffer.shadow_version() == 2 &&
        !managedVertexBuffer.mirror_ready() &&
        managedVertexBuffer.mirror_buffer() == nullptr,
        "R113 partial managed buffer update invalidates stale mirror");
    const auto managedVertexAfterWrite =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexAfterWrite.inputValid &&
        managedVertexAfterWrite.shadowValid &&
        !managedVertexAfterWrite.resourcesOwned &&
        !managedVertexAfterWrite.lifetimeCurrent &&
        !managedVertexAfterWrite.ready &&
        managedVertexAfterWrite.snapshotToken == 0 &&
        !managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexInitialToken),
        "R119 shadow mutation invalidates managed-buffer snapshot");
    require(
        !managedVertexBuffer.write_range(
            static_cast<UINT>(managedVertexBytes.size() - 1u),
            managedVertexPatch,
            static_cast<UINT>(sizeof(managedVertexPatch))),
        "R113 out-of-range managed buffer write must fail closed");
    require(
        managedVertexBuffer.recreate_and_upload_mirror(d3d.device),
        "R113 managed vertex-buffer mirror recreation");
    const auto managedVertexAfterWriteRecreate =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexAfterWriteRecreate.ready &&
        managedVertexAfterWriteRecreate.shadowVersion == 2 &&
        managedVertexAfterWriteRecreate.mirrorShadowVersion == 2 &&
        managedVertexAfterWriteRecreate.mirrorInstanceGeneration == 2 &&
        managedVertexAfterWriteRecreate.snapshotToken != 0 &&
        managedVertexAfterWriteRecreate.snapshotToken != managedVertexInitialToken &&
        managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexAfterWriteRecreate.snapshotToken),
        "R119 managed-buffer recreation issues fresh snapshot");
    const auto managedVertexPreResetToken =
        managedVertexAfterWriteRecreate.snapshotToken;

    managedVertexBuffer.observe_device_reset();
    require(
        managedVertexBuffer.device_generation() == 2 &&
        managedVertexBuffer.shadow_valid() &&
        managedVertexBuffer.shadow_version() == 2 &&
        !managedVertexBuffer.mirror_ready() &&
        managedVertexBuffer.mirror_buffer() == nullptr,
        "R113 Reset preserves managed buffer CPU shadow only");
    const auto managedVertexAfterReset =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexAfterReset.inputValid &&
        managedVertexAfterReset.shadowValid &&
        !managedVertexAfterReset.resourcesOwned &&
        !managedVertexAfterReset.lifetimeCurrent &&
        !managedVertexAfterReset.ready &&
        managedVertexAfterReset.snapshotToken == 0 &&
        !managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexPreResetToken),
        "R119 Reset invalidates managed-buffer readiness snapshot");
    require(
        managedVertexBuffer.recreate_and_upload_mirror(d3d.device) &&
        managedVertexBuffer.mirror_descriptor_exact(d3d.device),
        "R113 post-Reset managed vertex-buffer mirror recreation");
    const auto managedVertexPostResetReady =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexPostResetReady.ready &&
        managedVertexPostResetReady.deviceGeneration == 2 &&
        managedVertexPostResetReady.shadowVersion == 2 &&
        managedVertexPostResetReady.mirrorGeneration == 2 &&
        managedVertexPostResetReady.mirrorShadowVersion == 2 &&
        managedVertexPostResetReady.mirrorInstanceGeneration == 3 &&
        managedVertexPostResetReady.snapshotToken != 0 &&
        managedVertexPostResetReady.snapshotToken != managedVertexPreResetToken &&
        managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexPostResetReady.snapshotToken),
        "R119 post-Reset managed-buffer mirror issues generation-current snapshot");

    NativeManagedBufferShadow managedIndexBuffer;
    std::array<unsigned short, 6> managedIndexBytes{0, 1, 2, 2, 3, 0};
    require(
        managedIndexBuffer.initialize(
            ResourceRole::Index,
            static_cast<UINT>(sizeof(managedIndexBytes)),
            0) &&
        managedIndexBuffer.write_range(
            0, managedIndexBytes.data(),
            static_cast<UINT>(sizeof(managedIndexBytes))) &&
        managedIndexBuffer.recreate_and_upload_mirror(d3d.device) &&
        managedIndexBuffer.mirror_descriptor_exact(d3d.device),
        "R113 managed index-buffer mirror upload");
    D3D11_BUFFER_DESC managedIndexDesc{};
    managedIndexBuffer.mirror_buffer()->GetDesc(&managedIndexDesc);
    require(
        managedIndexDesc.BindFlags == D3D11_BIND_INDEX_BUFFER,
        "R113 managed index-buffer bind contract");
    const auto managedIndexReady =
        managedIndexBuffer.mirror_readiness(d3d.device);
    require(
        managedIndexReady.ready &&
        managedIndexReady.role == ResourceRole::Index &&
        managedIndexReady.snapshotToken != 0 &&
        managedIndexReady.mirrorInstanceGeneration == 1 &&
        managedIndexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedIndexReady.snapshotToken),
        "R119 managed index-buffer mirror issues exact readiness snapshot");

    const auto indexedGeometryReady =
        compose_fixed_function_geometry_readiness(
            managedVertexPostResetReady, true, managedIndexReady,
            D3DPT_TRIANGLELIST);
    require(
        indexedGeometryReady.inputValid &&
        indexedGeometryReady.vertexBufferReady &&
        indexedGeometryReady.indexBufferRequired &&
        indexedGeometryReady.indexBufferReady &&
        indexedGeometryReady.topologyReady &&
        indexedGeometryReady.componentSnapshotsPresent &&
        indexedGeometryReady.ready &&
        indexedGeometryReady.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        indexedGeometryReady.vertexBufferSnapshotToken ==
            managedVertexPostResetReady.snapshotToken &&
        indexedGeometryReady.indexBufferSnapshotToken ==
            managedIndexReady.snapshotToken &&
        indexedGeometryReady.snapshotToken != 0 &&
        validate_fixed_function_geometry_snapshot(
            managedVertexPostResetReady, true, managedIndexReady,
            D3DPT_TRIANGLELIST, indexedGeometryReady.snapshotToken),
        "R122 indexed geometry seals VB IB and topology snapshots");

    const auto nonIndexedGeometryReady =
        compose_fixed_function_geometry_readiness(
            managedVertexPostResetReady, false, managedIndexReady,
            D3DPT_TRIANGLESTRIP);
    require(
        nonIndexedGeometryReady.ready &&
        !nonIndexedGeometryReady.indexBufferRequired &&
        nonIndexedGeometryReady.indexBufferReady &&
        nonIndexedGeometryReady.indexBufferSnapshotToken == 0 &&
        nonIndexedGeometryReady.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP,
        "R122 non-indexed geometry ignores unrelated IB identity");

    constexpr UINT geometryVertexStride = 24u;
    constexpr UINT geometryVertexOffset = 0u;
    constexpr UINT geometryIndexOffset = 0u;
    require(
        outrun::vr::dx11::
            validate_fixed_function_direct_geometry_readiness_integrity(
                indexedGeometryReady) &&
        outrun::vr::dx11::
            validate_fixed_function_direct_geometry_readiness_integrity(
                nonIndexedGeometryReady),
        "R139 direct geometry readiness seals copied struct identity");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R139 direct indexed geometry binds exact IA state");
    const auto indexedGeometryBinding =
        outrun::vr::dx11::observe_fixed_function_geometry_binding(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        indexedGeometryBinding.inputValid &&
        indexedGeometryBinding.geometryReady &&
        indexedGeometryBinding.contextMatches &&
        indexedGeometryBinding.vertexBufferCurrent &&
        indexedGeometryBinding.indexBufferCurrent &&
        indexedGeometryBinding.vertexBufferBoundExact &&
        indexedGeometryBinding.indexBufferBoundExact &&
        indexedGeometryBinding.topologyBoundExact &&
        indexedGeometryBinding.ready &&
        indexedGeometryBinding.indexed &&
        indexedGeometryBinding.geometrySnapshotToken ==
            indexedGeometryReady.snapshotToken &&
        indexedGeometryBinding.vertexBufferSnapshotToken ==
            managedVertexPostResetReady.snapshotToken &&
        indexedGeometryBinding.indexBufferSnapshotToken ==
            managedIndexReady.snapshotToken &&
        indexedGeometryBinding.vertexStride == geometryVertexStride &&
        indexedGeometryBinding.indexFormat == DXGI_FORMAT_R16_UINT &&
        indexedGeometryBinding.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        indexedGeometryBinding.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_geometry_binding_snapshot(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            indexedGeometryBinding.snapshotToken),
        "R139 live IA observer seals VB IB stride offsets and topology");

    d3d.context->IASetPrimitiveTopology(
        D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    const auto driftedGeometryBinding =
        outrun::vr::dx11::observe_fixed_function_geometry_binding(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        driftedGeometryBinding.inputValid &&
        driftedGeometryBinding.geometryReady &&
        driftedGeometryBinding.vertexBufferBoundExact &&
        driftedGeometryBinding.indexBufferBoundExact &&
        !driftedGeometryBinding.topologyBoundExact &&
        !driftedGeometryBinding.ready &&
        driftedGeometryBinding.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_geometry_binding_snapshot(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            indexedGeometryBinding.snapshotToken),
        "R139 live IA topology drift invalidates geometry binding snapshot");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, nonIndexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            nullptr, DXGI_FORMAT_UNKNOWN, 0),
        "R139 non-indexed geometry clears unrelated IA index binding");
    const auto nonIndexedGeometryBinding =
        outrun::vr::dx11::observe_fixed_function_geometry_binding(
            d3d.context, nonIndexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            nullptr, DXGI_FORMAT_UNKNOWN, 0);
    require(
        nonIndexedGeometryBinding.ready &&
        !nonIndexedGeometryBinding.indexed &&
        nonIndexedGeometryBinding.indexBufferCurrent &&
        nonIndexedGeometryBinding.indexBufferBoundExact &&
        nonIndexedGeometryBinding.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP &&
        nonIndexedGeometryBinding.snapshotToken != 0,
        "R139 non-indexed live IA binding is exact and index-free");

    auto forgedDirectGeometry = indexedGeometryReady;
    forgedDirectGeometry.topology = D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP;
    require(
        !outrun::vr::dx11::
            validate_fixed_function_direct_geometry_readiness_integrity(
                forgedDirectGeometry) &&
        !outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, forgedDirectGeometry, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R139 copied geometry topology drift fails closed before IA mutation");
    require(
        !outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R8_UINT, geometryIndexOffset),
        "R139 unsupported IA index format fails closed");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset) &&
        outrun::vr::dx11::validate_fixed_function_geometry_binding_snapshot(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            indexedGeometryBinding.snapshotToken),
        "R139 exact indexed IA binding restores deterministic snapshot");

    auto wrongVertexRole = managedVertexPostResetReady;
    wrongVertexRole.role = ResourceRole::Index;
    auto missingIndexReady = managedIndexReady;
    missingIndexReady.ready = false;
    missingIndexReady.snapshotToken = 0;
    const auto wrongRoleGeometry =
        compose_fixed_function_geometry_readiness(
            wrongVertexRole, true, managedIndexReady, D3DPT_TRIANGLELIST);
    const auto missingIndexGeometry =
        compose_fixed_function_geometry_readiness(
            managedVertexPostResetReady, true, missingIndexReady,
            D3DPT_TRIANGLELIST);
    const auto fanGeometry =
        compose_fixed_function_geometry_readiness(
            managedVertexPostResetReady, false, managedIndexReady,
            D3DPT_TRIANGLEFAN);
    require(
        !wrongRoleGeometry.inputValid &&
        !wrongRoleGeometry.ready &&
        wrongRoleGeometry.snapshotToken == 0 &&
        !missingIndexGeometry.ready &&
        missingIndexGeometry.snapshotToken == 0 &&
        !fanGeometry.topologyReady &&
        !fanGeometry.ready &&
        fanGeometry.snapshotToken == 0,
        "R122 geometry fails closed on role IB or unowned fan expansion");

    NativeTriangleFanIndexBufferReadiness generatedFanReady{};
    generatedFanReady.resourcesOwned = true;
    generatedFanReady.deviceMatches = true;
    generatedFanReady.descriptorExact = true;
    generatedFanReady.sourceProvenanceExact = true;
    generatedFanReady.indexedSource = false;
    generatedFanReady.ready = true;
    generatedFanReady.indexCount = 9;
    generatedFanReady.primitiveCount = 3;
    generatedFanReady.baseVertex = 7;
    generatedFanReady.generation = 1;
    generatedFanReady.contentHash = 0xd8928727f6a47b73ull;
    generatedFanReady.snapshotToken = 0x1280F11ull;

    const auto expandedNonIndexedFan =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, generatedFanReady, 3u, 7u);
    require(
        expandedNonIndexedFan.inputValid &&
        expandedNonIndexedFan.vertexBufferReady &&
        !expandedNonIndexedFan.indexBufferRequired &&
        expandedNonIndexedFan.indexBufferReady &&
        expandedNonIndexedFan.generatedIndexBufferRequired &&
        expandedNonIndexedFan.generatedIndexBufferReady &&
        expandedNonIndexedFan.generatedIndexBufferMatchesDraw &&
        expandedNonIndexedFan.topologyReady &&
        expandedNonIndexedFan.componentSnapshotsPresent &&
        expandedNonIndexedFan.ready &&
        expandedNonIndexedFan.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        expandedNonIndexedFan.indexBufferSnapshotToken == 0 &&
        expandedNonIndexedFan.generatedIndexBufferSnapshotToken ==
            generatedFanReady.snapshotToken &&
        expandedNonIndexedFan.snapshotToken != 0 &&
        validate_fixed_function_nonindexed_triangle_fan_geometry_snapshot(
            managedVertexPostResetReady, generatedFanReady, 3u, 7u,
            expandedNonIndexedFan.snapshotToken),
        "R128 generated IB makes exact non-indexed fan geometry ready");

    auto mismatchedGeneratedFan = generatedFanReady;
    mismatchedGeneratedFan.contentHash ^= 0x1u;
    const auto mismatchedFanGeometry =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, mismatchedGeneratedFan, 3u, 7u);
    auto staleGeneratedFan = generatedFanReady;
    staleGeneratedFan.snapshotToken ^= 0x100000001b3ull;
    const auto staleFanGeometry =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, staleGeneratedFan, 3u, 7u);
    require(
        mismatchedFanGeometry.generatedIndexBufferReady &&
        !mismatchedFanGeometry.generatedIndexBufferMatchesDraw &&
        !mismatchedFanGeometry.ready &&
        mismatchedFanGeometry.snapshotToken == 0 &&
        staleFanGeometry.ready &&
        staleFanGeometry.snapshotToken !=
            expandedNonIndexedFan.snapshotToken &&
        !validate_fixed_function_nonindexed_triangle_fan_geometry_snapshot(
            managedVertexPostResetReady, staleGeneratedFan, 3u, 7u,
            expandedNonIndexedFan.snapshotToken),
        "R128 fan geometry rejects mismatched or stale generated IB identity");

    auto wrongFanProvenance = generatedFanReady;
    wrongFanProvenance.baseVertex = 8u;
    const auto wrongProvenanceFanGeometry =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, wrongFanProvenance, 3u, 7u);
    require(
        wrongProvenanceFanGeometry.generatedIndexBufferReady &&
        !wrongProvenanceFanGeometry.generatedIndexBufferMatchesDraw &&
        !wrongProvenanceFanGeometry.ready &&
        wrongProvenanceFanGeometry.snapshotToken == 0,
        "R142 non-indexed fan geometry rejects owner provenance drift");

    auto overflowGeneratedFan = generatedFanReady;
    overflowGeneratedFan.indexCount = 3;
    const auto overflowFanGeometry =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, overflowGeneratedFan, 1u, ~0u);
    require(
        !overflowFanGeometry.inputValid &&
        overflowFanGeometry.vertexBufferReady &&
        overflowFanGeometry.generatedIndexBufferReady &&
        !overflowFanGeometry.generatedIndexBufferMatchesDraw &&
        overflowFanGeometry.topologyReady &&
        !overflowFanGeometry.ready &&
        overflowFanGeometry.snapshotToken == 0,
        "R129 non-indexed fan base-vertex overflow fails closed");

    auto indexedGeneratedFanReady = generatedFanReady;
    indexedGeneratedFanReady.sourceProvenanceExact = true;
    indexedGeneratedFanReady.indexedSource = true;
    indexedGeneratedFanReady.primitiveCount = 3u;
    indexedGeneratedFanReady.sourceIndexFormat = D3DFMT_INDEX16;
    indexedGeneratedFanReady.sourceStartIndex = 2u;
    indexedGeneratedFanReady.sourceIndexCount = 8u;
    indexedGeneratedFanReady.sourceIndexSnapshotToken =
        managedIndexReady.snapshotToken;
    indexedGeneratedFanReady.snapshotToken = 0x1430F11ull;

    const auto indexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 8u);
    require(
        indexedFanGeometry.inputValid &&
        indexedFanGeometry.vertexBufferReady &&
        indexedFanGeometry.indexBufferRequired &&
        indexedFanGeometry.indexBufferReady &&
        indexedFanGeometry.generatedIndexBufferRequired &&
        indexedFanGeometry.generatedIndexBufferReady &&
        indexedFanGeometry.generatedIndexBufferMatchesDraw &&
        indexedFanGeometry.topologyReady &&
        indexedFanGeometry.componentSnapshotsPresent &&
        indexedFanGeometry.ready &&
        indexedFanGeometry.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        indexedFanGeometry.indexBufferSnapshotToken ==
            managedIndexReady.snapshotToken &&
        indexedFanGeometry.generatedIndexBufferSnapshotToken ==
            indexedGeneratedFanReady.snapshotToken &&
        indexedFanGeometry.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_indexed_triangle_fan_geometry_snapshot(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 8u,
                indexedFanGeometry.snapshotToken),
        "R143 indexed fan geometry seals current source-index mirror provenance");

    auto staleIndexedFan = indexedGeneratedFanReady;
    staleIndexedFan.sourceIndexSnapshotToken ^= 0x100000001b3ull;
    staleIndexedFan.snapshotToken ^= 0x100000001b3ull;
    const auto staleIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                staleIndexedFan, 3u, D3DFMT_INDEX16, 2u, 8u);
    require(
        staleIndexedFanGeometry.generatedIndexBufferReady &&
        !staleIndexedFanGeometry.generatedIndexBufferMatchesDraw &&
        !staleIndexedFanGeometry.ready &&
        staleIndexedFanGeometry.snapshotToken == 0,
        "R143 indexed fan geometry rejects stale source-index snapshot");

    const auto formatDriftIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX32, 2u, 8u);
    const auto startDriftIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 3u, 8u);
    const auto countDriftIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 7u);
    require(
        !formatDriftIndexedFanGeometry.generatedIndexBufferMatchesDraw &&
        !formatDriftIndexedFanGeometry.ready &&
        !startDriftIndexedFanGeometry.generatedIndexBufferMatchesDraw &&
        !startDriftIndexedFanGeometry.ready &&
        !countDriftIndexedFanGeometry.generatedIndexBufferMatchesDraw &&
        !countDriftIndexedFanGeometry.ready,
        "R143 indexed fan geometry rejects format start and count drift");

    auto wrongSourceIndexRole = managedIndexReady;
    wrongSourceIndexRole.role = ResourceRole::Vertex;
    const auto wrongSourceRoleIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, wrongSourceIndexRole,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 8u);
    require(
        !wrongSourceRoleIndexedFanGeometry.inputValid &&
        !wrongSourceRoleIndexedFanGeometry.ready &&
        wrongSourceRoleIndexedFanGeometry.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_indexed_triangle_fan_geometry_snapshot(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 7u,
                indexedFanGeometry.snapshotToken),
        "R143 indexed fan geometry rejects source role and sealed range drift");
    std::cout << "DX11 indexed triangle-fan geometry readiness R143: PASS\n";

    NativeManagedBufferShadow invalidManagedBuffer;
    require(
        !invalidManagedBuffer.initialize(
            ResourceRole::Texture, 32, 0),
        "R113 non-buffer managed shadow must fail closed");

    NativeManagedTextureShadow managedShadow;
    require(
        managedShadow.initialize(D3DFMT_A8R8G8B8, 4, 4),
        "R102 managed shadow initialize");
    require(
        managedShadow.ready() &&
        !managedShadow.shadow_valid() &&
        !managedShadow.mirror_ready() &&
        managedShadow.mirror_device() == nullptr &&
        managedShadow.mirror_texture() == nullptr &&
        managedShadow.mirror_srv() == nullptr &&
        managedShadow.shadow_version() == 0 &&
        managedShadow.device_generation() == 1,
        "R102 managed shadow starts allocated but content-invalid");
    require(
        !managedShadow.recreate_and_upload_mirror(d3d.device),
        "R103 mirror upload requires valid CPU shadow");
    managedShadow.note_mirror_uploaded();
    require(
        !managedShadow.mirror_ready(),
        "R103 bare mirror acknowledgment must not fabricate readiness");

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

    require(
        managedShadow.recreate_and_upload_mirror(d3d.device),
        "R103 managed shadow creates DEFAULT mirror");
    require(
        managedShadow.mirror_ready() &&
        managedShadow.mirror_device() == d3d.device &&
        managedShadow.mirror_texture() != nullptr &&
        managedShadow.mirror_srv() != nullptr &&
        managedShadow.lifetime_state().mirrorGeneration == 1 &&
        managedShadow.lifetime_state().mirrorShadowVersion == 1,
        "R103 managed mirror ownership matches shadow generation");

    D3D11_TEXTURE2D_DESC managedMirrorDesc{};
    managedShadow.mirror_texture()->GetDesc(&managedMirrorDesc);
    require(
        managedMirrorDesc.Width == 4 &&
        managedMirrorDesc.Height == 4 &&
        managedMirrorDesc.MipLevels == 1 &&
        managedMirrorDesc.ArraySize == 1 &&
        managedMirrorDesc.Format == DXGI_FORMAT_B8G8R8A8_UNORM &&
        managedMirrorDesc.Usage == D3D11_USAGE_DEFAULT &&
        managedMirrorDesc.CPUAccessFlags == 0 &&
        (managedMirrorDesc.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0,
        "R103 managed mirror DEFAULT descriptor contract");

    D3D11_TEXTURE2D_DESC managedStagingDesc = managedMirrorDesc;
    managedStagingDesc.Usage = D3D11_USAGE_STAGING;
    managedStagingDesc.BindFlags = 0;
    managedStagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Texture2D* managedStagingTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &managedStagingDesc, nullptr, &managedStagingTexture)) &&
        managedStagingTexture != nullptr,
        "R103 managed mirror staging prerequisite");
    d3d.context->CopyResource(
        managedStagingTexture, managedShadow.mirror_texture());

    D3D11_MAPPED_SUBRESOURCE managedStagingMap{};
    require(
        SUCCEEDED(d3d.context->Map(
            managedStagingTexture, 0, D3D11_MAP_READ, 0, &managedStagingMap)) &&
        managedStagingMap.pData != nullptr &&
        managedStagingMap.RowPitch >= managedRowBytes,
        "R103 managed mirror staging readback map");
    for (UINT row = 0; row < managedRows; ++row) {
        const auto* observed =
            static_cast<const unsigned char*>(managedStagingMap.pData) +
            static_cast<std::size_t>(row) * managedStagingMap.RowPitch;
        const auto* expected =
            managedSource.data() +
            static_cast<std::size_t>(row) * managedSourcePitch;
        require(
            std::memcmp(observed, expected, managedRowBytes) == 0,
            "R103 managed mirror uploaded bytes must match shadow rows");
    }
    d3d.context->Unmap(managedStagingTexture, 0);
    managedStagingTexture->Release();

    managedShadow.observe_device_reset();
    require(
        managedShadow.device_generation() == 2 &&
        managedShadow.shadow_valid() &&
        managedShadow.shadow_version() == 1 &&
        !managedShadow.mirror_ready(),
        "R102 Reset preserves CPU shadow and invalidates GPU mirror");
    require(
        managedShadow.mirror_device() == nullptr &&
        managedShadow.mirror_texture() == nullptr &&
        managedShadow.mirror_srv() == nullptr,
        "R103 Reset preserves shadow and releases generation-bound mirror");

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

    require(
        managedShadow.recreate_and_upload_mirror(d3d.device),
        "R103 post-Reset mirror recreation");
    require(
        managedShadow.mirror_ready() &&
        managedShadow.lifetime_state().mirrorGeneration == 2,
        "R102 post-Reset mirror acknowledgment uses new device generation");
    require(
        managedShadow.mirror_ready() &&
        managedShadow.mirror_device() == d3d.device &&
        managedShadow.mirror_texture() != nullptr &&
        managedShadow.mirror_srv() != nullptr &&
        managedShadow.lifetime_state().mirrorShadowVersion == 1,
        "R103 post-Reset mirror upload uses new device generation");
    require(
        managedShadow.mirror_descriptor_exact(d3d.device) &&
        !managedShadow.mirror_descriptor_exact(textureOtherDevice.device),
        "R111 managed mirror descriptor and SRV view identity are exact-device bound");

    managedSource[0] ^= 0x33;
    require(
        managedShadow.write_full(
            managedSource.data(), managedSourcePitch, managedRows),
        "R102 second managed shadow full write");
    require(
        managedShadow.shadow_version() == 2 &&
        !managedShadow.mirror_ready() &&
        managedShadow.mirror_device() == nullptr &&
        managedShadow.mirror_texture() == nullptr &&
        managedShadow.mirror_srv() == nullptr &&
        !managedShadow.mirror_descriptor_exact(d3d.device),
        "R103 shadow mutation invalidates and releases uploaded mirror");

    NativeManagedTextureShadow unsupportedManagedShadow;
    require(
        !unsupportedManagedShadow.initialize(D3DFMT_DXT1, 4, 4),
        "R102 compressed managed shadow must fail closed");
    require(
        !unsupportedManagedShadow.ready(),
        "R102 failed managed shadow initialize stays dormant");

    NativeManagedTextureShadow lockBridgeShadow;
    require(
        lockBridgeShadow.initialize(D3DFMT_A8R8G8B8, 4, 4),
        "R104 LockRect bridge shadow initialize");

    std::array<unsigned char, 80> lockBridgeSource{};
    for (UINT row = 0; row < managedRows; ++row) {
        for (UINT column = 0; column < managedRowBytes; ++column) {
            lockBridgeSource[
                static_cast<std::size_t>(row) * managedSourcePitch + column] =
                static_cast<unsigned char>(0x90 + row * 16 + column);
        }
    }

    D3DLOCKED_RECT sourceLock{};
    sourceLock.Pitch = static_cast<INT>(managedSourcePitch);
    sourceLock.pBits = lockBridgeSource.data();
    RECT partialRect{0, 0, 2, 2};

    require(
        !lockBridgeShadow.begin_source_lock(
            1, nullptr, 0, sourceLock),
        "R104 nonzero mip LockRect must fail closed");
    require(
        !lockBridgeShadow.begin_source_lock(
            0, &partialRect, 0, sourceLock),
        "R104 partial LockRect must fail closed");
    require(
        !lockBridgeShadow.begin_source_lock(
            0, nullptr, D3DLOCK_READONLY, sourceLock),
        "R104 read-only LockRect must not arm write capture");
    require(
        !lockBridgeShadow.begin_source_lock(
            0, nullptr, D3DLOCK_DISCARD, sourceLock),
        "R104 MANAGED discard LockRect must fail closed");

    D3DLOCKED_RECT shortPitchLock = sourceLock;
    shortPitchLock.Pitch = static_cast<INT>(managedRowBytes - 1);
    require(
        !lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, shortPitchLock),
        "R104 short-pitch LockRect must fail closed");

    require(
        lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, sourceLock) &&
        lockBridgeShadow.source_lock_active(),
        "R104 full MANAGED LockRect arms source capture");
    require(
        !lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, sourceLock),
        "R104 nested LockRect must fail closed");
    require(
        !lockBridgeShadow.commit_source_unlock(1) &&
        lockBridgeShadow.source_lock_active(),
        "R104 mismatched UnlockRect level must preserve active capture");

    // Prove the bridge observes the final lock contents rather than the bytes
    // that happened to exist when LockRect first returned.
    lockBridgeSource[0] ^= 0x5c;
    require(
        lockBridgeShadow.commit_source_unlock(0) &&
        !lockBridgeShadow.source_lock_active(),
        "R104 matching UnlockRect commits final lock contents");
    require(
        lockBridgeShadow.shadow_valid() &&
        lockBridgeShadow.shadow_version() == 1,
        "R104 UnlockRect commit advances managed shadow version");

    std::array<unsigned char, 96> lockBridgeReadback{};
    require(
        lockBridgeShadow.read_full(
            lockBridgeReadback.data(), managedReadbackPitch, managedRows),
        "R104 committed LockRect shadow readback");
    for (UINT row = 0; row < managedRows; ++row) {
        require(
            std::memcmp(
                lockBridgeReadback.data() +
                    static_cast<std::size_t>(row) * managedReadbackPitch,
                lockBridgeSource.data() +
                    static_cast<std::size_t>(row) * managedSourcePitch,
                managedRowBytes) == 0,
            "R104 UnlockRect-captured bytes must match final source rows");
    }

    require(
        lockBridgeShadow.recreate_and_upload_mirror(d3d.device),
        "R104 bridge mirror prerequisite");
    require(
        lockBridgeShadow.mirror_ready(),
        "R104 bridge mirror starts generation-current");

    lockBridgeSource[0] ^= 0x27;
    require(
        lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, sourceLock) &&
        lockBridgeShadow.source_lock_active() &&
        !lockBridgeShadow.mirror_ready() &&
        lockBridgeShadow.mirror_texture() == nullptr,
        "R104 writable LockRect invalidates stale GPU mirror immediately");
    require(
        !lockBridgeShadow.read_full(
            lockBridgeReadback.data(), managedReadbackPitch, managedRows) &&
        !lockBridgeShadow.recreate_and_upload_mirror(d3d.device),
        "R104 active source lock blocks stale shadow read/upload");

    lockBridgeShadow.observe_device_reset();
    require(
        !lockBridgeShadow.source_lock_active() &&
        !lockBridgeShadow.commit_source_unlock(0) &&
        lockBridgeShadow.shadow_valid() &&
        lockBridgeShadow.shadow_version() == 1 &&
        lockBridgeShadow.device_generation() == 2,
        "R104 Reset clears stale LockRect pointer without committing it");

    require(
        lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, sourceLock),
        "R104 post-Reset LockRect re-arms capture");
    lockBridgeShadow.cancel_source_lock();
    require(
        !lockBridgeShadow.source_lock_active() &&
        lockBridgeShadow.shadow_version() == 1,
        "R104 cancelled LockRect clears capture without shadow mutation");

    NativeManagedTextureRegistry managedRegistry;
    int registryTextureA = 0;
    int registryTextureB = 0;
    require(
        !managedRegistry.register_texture(
            nullptr, D3DFMT_A8R8G8B8, 4, 4, 1, 0, D3DPOOL_MANAGED),
        "R105 registry rejects null texture identity");
    require(
        !managedRegistry.register_texture(
            &registryTextureB, D3DFMT_A8R8G8B8, 4, 4, 2, 0,
            D3DPOOL_MANAGED),
        "R105 registry rejects multi-mip MANAGED texture");
    require(
        !managedRegistry.register_texture(
            &registryTextureB, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_DEFAULT),
        "R105 registry rejects non-MANAGED texture");
    require(
        managedRegistry.register_texture(
            &registryTextureA, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_MANAGED) &&
        managedRegistry.size() == 1 &&
        managedRegistry.contains(&registryTextureA),
        "R105 registry accepts exact single-mip MANAGED texture");

    std::array<unsigned char, 80> registrySource{};
    for (UINT row = 0; row < managedRows; ++row) {
        for (UINT column = 0; column < managedRowBytes; ++column) {
            registrySource[
                static_cast<std::size_t>(row) * managedSourcePitch + column] =
                static_cast<unsigned char>(0x30 + row * 16 + column);
        }
    }
    D3DLOCKED_RECT registryLock{};
    registryLock.Pitch = static_cast<INT>(managedSourcePitch);
    registryLock.pBits = registrySource.data();

    require(
        managedRegistry.begin_source_lock(
            &registryTextureA, 0, nullptr, 0, registryLock) &&
        managedRegistry.source_lock_active(&registryTextureA),
        "R105 registry begins exact managed LockRect transaction");
    registrySource[0] ^= 0x19;
    require(
        managedRegistry.stage_source_unlock(&registryTextureA, 0) &&
        !managedRegistry.source_lock_active(&registryTextureA) &&
        managedRegistry.source_unlock_staged(&registryTextureA),
        "R105 pre-Unlock staging clears raw source pointer");
    const unsigned char stagedFirstByte = registrySource[0];
    registrySource[0] ^= 0x7f;
    require(
        managedRegistry.finish_source_unlock(
            &registryTextureA, 0, S_OK) &&
        managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) == 1 &&
        !managedRegistry.source_unlock_staged(&registryTextureA),
        "R105 successful real Unlock commits staged bytes");

    std::array<unsigned char, 96> registryReadback{};
    require(
        managedRegistry.read_shadow(
            &registryTextureA,
            registryReadback.data(), managedReadbackPitch, managedRows) &&
        registryReadback[0] == stagedFirstByte &&
        registryReadback[0] != registrySource[0],
        "R105 commit uses pre-Unlock staged snapshot, not post-stage source");

    registrySource[0] ^= 0x23;
    require(
        managedRegistry.begin_source_lock(
            &registryTextureA, 0, nullptr, 0, registryLock) &&
        managedRegistry.stage_source_unlock(&registryTextureA, 0),
        "R105 failed-Unlock transaction stages before COM call");
    require(
        !managedRegistry.finish_source_unlock(
            &registryTextureA, 0, E_FAIL) &&
        !managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) == 1,
        "R105 failed real Unlock invalidates shadow without commit");

    require(
        managedRegistry.begin_source_lock(
            &registryTextureA, 0, nullptr, 0, registryLock) &&
        managedRegistry.stage_source_unlock(&registryTextureA, 0) &&
        managedRegistry.finish_source_unlock(
            &registryTextureA, 0, S_OK) &&
        managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) == 2,
        "R105 later successful Unlock recovers invalidated shadow");

    const auto registryVersionBeforeExternalMutation =
        managedRegistry.shadow_version(&registryTextureA);
    require(
        !managedRegistry.recreate_and_upload_mirror_for_observation(
            nullptr, d3d.device) &&
        !managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, nullptr),
        "R108 registry mirror preparation rejects incomplete ownership identity");
    require(
        managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, d3d.device),
        "R108 registry prepares exact identity-owned mirror for observation");
    const auto registryMirrorReady =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorReady.registered &&
        registryMirrorReady.shadowValid &&
        registryMirrorReady.resourcesOwned &&
        registryMirrorReady.lifetimeCurrent &&
        registryMirrorReady.deviceMatches &&
        registryMirrorReady.descriptorExact &&
        registryMirrorReady.ready &&
        registryMirrorReady.deviceGeneration ==
            managedRegistry.device_generation(&registryTextureA) &&
        registryMirrorReady.shadowVersion ==
            registryVersionBeforeExternalMutation &&
        registryMirrorReady.mirrorGeneration ==
            registryMirrorReady.deviceGeneration &&
        registryMirrorReady.mirrorShadowVersion ==
            registryMirrorReady.shadowVersion,
        "R108 registry mirror readiness seals texture identity generation and shadow version");
    const auto registryMirrorForeignDevice =
        managedRegistry.mirror_readiness(
            &registryTextureA, textureOtherDevice.device);
    require(
        registryMirrorForeignDevice.registered &&
        registryMirrorForeignDevice.shadowValid &&
        registryMirrorForeignDevice.resourcesOwned &&
        registryMirrorForeignDevice.lifetimeCurrent &&
        !registryMirrorForeignDevice.deviceMatches &&
        !registryMirrorForeignDevice.descriptorExact &&
        !registryMirrorForeignDevice.ready,
        "R108 foreign D3D11 device cannot claim registered mirror readiness");

    const std::array<const void*, 2> registryStageKeys{
        &registryTextureA, &registryTextureB};
    const auto registryStageNullKeys =
        managedRegistry.mirror_readiness_for_stages(
            nullptr, 1, 0x1u, d3d.device);
    require(
        !registryStageNullKeys.inputValid &&
        registryStageNullKeys.requiredMask == 0x1u &&
        registryStageNullKeys.pendingMask == 0x1u &&
        !registryStageNullKeys.allRequiredReady,
        "R109 stage aggregate rejects null key array fail-closed");
    const auto registryStageOutOfRange =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), 1, 0x2u, d3d.device);
    require(
        !registryStageOutOfRange.inputValid &&
        registryStageOutOfRange.pendingMask == 0x2u &&
        !registryStageOutOfRange.allRequiredReady,
        "R109 stage aggregate rejects required bits beyond observed stages");
    const auto registryStageNullDevice =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, nullptr);
    require(
        !registryStageNullDevice.inputValid &&
        registryStageNullDevice.pendingMask == 0x1u &&
        !registryStageNullDevice.allRequiredReady,
        "R109 stage aggregate rejects missing expected D3D11 device");
    const auto registryStageReady =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageReady.inputValid &&
        registryStageReady.requiredMask == 0x1u &&
        registryStageReady.registeredMask == 0x1u &&
        registryStageReady.shadowValidMask == 0x1u &&
        registryStageReady.resourcesOwnedMask == 0x1u &&
        registryStageReady.lifetimeCurrentMask == 0x1u &&
        registryStageReady.deviceMatchesMask == 0x1u &&
        registryStageReady.descriptorExactMask == 0x1u &&
        registryStageReady.readyMask == 0x1u &&
        registryStageReady.pendingMask == 0 &&
        registryStageReady.allRequiredReady,
        "R109 exact required stage aggregates all R108 readiness evidence");
    require(
        registryStageReady.snapshotToken != 0 &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageReady.snapshotToken),
        "R110 ready stage aggregate issues a valid nonzero snapshot token");
    require(
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, textureOtherDevice.device, registryStageReady.snapshotToken) &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x3u, d3d.device, registryStageReady.snapshotToken) &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, 0),
        "R110 snapshot token is bound to exact device mask and nonzero identity");
    const auto registryStageInitialToken = registryStageReady.snapshotToken;
    require(
        managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, d3d.device),
        "R110 same-shadow mirror recreation prerequisite");
    const auto registryStageAfterSameShadowRecreate =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterSameShadowRecreate.allRequiredReady &&
        registryStageAfterSameShadowRecreate.snapshotToken != 0 &&
        registryStageAfterSameShadowRecreate.snapshotToken !=
            registryStageInitialToken &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageInitialToken) &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device,
            registryStageAfterSameShadowRecreate.snapshotToken),
        "R110 mirror instance recreation invalidates stale readiness token");
    const auto registryStageBeforeMembershipChangeToken =
        registryStageAfterSameShadowRecreate.snapshotToken;
    require(
        managedRegistry.register_texture(
            &registryTextureB, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_MANAGED),
        "R110 registry membership generation change prerequisite");
    require(
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageBeforeMembershipChangeToken),
        "R110 registry membership change invalidates prior snapshot token");
    managedRegistry.forget_texture(&registryTextureB);
    const auto registryStageAfterMembershipRefresh =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterMembershipRefresh.allRequiredReady &&
        registryStageAfterMembershipRefresh.snapshotToken != 0 &&
        registryStageAfterMembershipRefresh.snapshotToken !=
            registryStageBeforeMembershipChangeToken &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device,
            registryStageAfterMembershipRefresh.snapshotToken),
        "R110 refreshed membership snapshot issues a fresh valid token");
    const auto registryStageBeforeExternalMutationToken =
        registryStageAfterMembershipRefresh.snapshotToken;
    const auto registryStageMissingRequired =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x3u, d3d.device);
    require(
        registryStageMissingRequired.inputValid &&
        registryStageMissingRequired.registeredMask == 0x1u &&
        registryStageMissingRequired.readyMask == 0x1u &&
        registryStageMissingRequired.pendingMask == 0x2u &&
        !registryStageMissingRequired.allRequiredReady,
        "R109 unregistered required stage remains activation-pending");
    const auto registryStageForeignDevice =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, textureOtherDevice.device);
    require(
        registryStageForeignDevice.inputValid &&
        registryStageForeignDevice.registeredMask == 0x1u &&
        registryStageForeignDevice.shadowValidMask == 0x1u &&
        registryStageForeignDevice.resourcesOwnedMask == 0x1u &&
        registryStageForeignDevice.lifetimeCurrentMask == 0x1u &&
        registryStageForeignDevice.deviceMatchesMask == 0 &&
        registryStageForeignDevice.descriptorExactMask == 0 &&
        registryStageForeignDevice.readyMask == 0 &&
        registryStageForeignDevice.pendingMask == 0x1u &&
        !registryStageForeignDevice.allRequiredReady,
        "R109 foreign device keeps required stage activation-pending");

    require(
        managedRegistry.invalidate_external_mutation(&registryTextureA) &&
        !managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) ==
            registryVersionBeforeExternalMutation,
        "R107 external update invalidates current MANAGED texture shadow");
    const auto registryMirrorAfterExternalMutation =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorAfterExternalMutation.registered &&
        !registryMirrorAfterExternalMutation.shadowValid &&
        !registryMirrorAfterExternalMutation.resourcesOwned &&
        !registryMirrorAfterExternalMutation.lifetimeCurrent &&
        !registryMirrorAfterExternalMutation.ready,
        "R108 external mutation clears registry mirror ownership readiness");
    const auto registryStageAfterExternalMutation =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterExternalMutation.inputValid &&
        registryStageAfterExternalMutation.registeredMask == 0x1u &&
        registryStageAfterExternalMutation.shadowValidMask == 0 &&
        registryStageAfterExternalMutation.resourcesOwnedMask == 0 &&
        registryStageAfterExternalMutation.lifetimeCurrentMask == 0 &&
        registryStageAfterExternalMutation.deviceMatchesMask == 0 &&
        registryStageAfterExternalMutation.descriptorExactMask == 0 &&
        registryStageAfterExternalMutation.readyMask == 0 &&
        registryStageAfterExternalMutation.pendingMask == 0x1u &&
        !registryStageAfterExternalMutation.allRequiredReady,
        "R109 external mutation makes required stage activation-pending");
    require(
        registryStageAfterExternalMutation.snapshotToken == 0 &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageBeforeExternalMutationToken),
        "R110 external mutation invalidates prior readiness snapshot token");
    require(
        !managedRegistry.invalidate_external_mutation(&registryTextureA) &&
        !managedRegistry.shadow_valid(&registryTextureA),
        "R107 repeated external update remains fail-closed while shadow is stale");

    registrySource[0] ^= 0x31;
    require(
        managedRegistry.begin_source_lock(
            &registryTextureA, 0, nullptr, 0, registryLock) &&
        managedRegistry.stage_source_unlock(&registryTextureA, 0) &&
        managedRegistry.finish_source_unlock(
            &registryTextureA, 0, S_OK) &&
        managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) ==
            registryVersionBeforeExternalMutation + 1,
        "R107 LockRect recapture restores readiness after external update");

    require(
        managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, d3d.device),
        "R108 recaptured shadow recreates registry mirror");
    const auto registryMirrorBeforeReset =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorBeforeReset.ready &&
        registryMirrorBeforeReset.mirrorGeneration ==
            registryMirrorBeforeReset.deviceGeneration &&
        registryMirrorBeforeReset.mirrorShadowVersion ==
            registryMirrorBeforeReset.shadowVersion,
        "R108 recaptured mirror is generation-current before Reset");
    const auto registryStageAfterRecapture =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterRecapture.inputValid &&
        registryStageAfterRecapture.readyMask == 0x1u &&
        registryStageAfterRecapture.pendingMask == 0 &&
        registryStageAfterRecapture.allRequiredReady,
        "R109 recaptured mirror restores required stage readiness");
    require(
        registryStageAfterRecapture.snapshotToken != 0 &&
        registryStageAfterRecapture.snapshotToken !=
            registryStageBeforeExternalMutationToken &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageAfterRecapture.snapshotToken),
        "R110 recapture and mirror recreation issue a fresh valid token");
    const auto registryStageBeforeResetToken =
        registryStageAfterRecapture.snapshotToken;

    const auto registryVersionBeforeReset =
        managedRegistry.shadow_version(&registryTextureA);
    const auto registryGenerationBeforeReset =
        managedRegistry.device_generation(&registryTextureA);
    managedRegistry.observe_device_reset();
    require(
        managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) ==
            registryVersionBeforeReset &&
        managedRegistry.device_generation(&registryTextureA) ==
            registryGenerationBeforeReset + 1,
        "R105 Reset preserves CPU shadow and advances registry generation");
    const auto registryMirrorAfterReset =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorAfterReset.registered &&
        registryMirrorAfterReset.shadowValid &&
        !registryMirrorAfterReset.resourcesOwned &&
        !registryMirrorAfterReset.lifetimeCurrent &&
        !registryMirrorAfterReset.ready &&
        registryMirrorAfterReset.deviceGeneration ==
            registryGenerationBeforeReset + 1 &&
        registryMirrorAfterReset.shadowVersion == registryVersionBeforeReset,
        "R108 Reset invalidates generation-bound registry mirror readiness");
    const auto registryStageAfterReset =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterReset.inputValid &&
        registryStageAfterReset.registeredMask == 0x1u &&
        registryStageAfterReset.shadowValidMask == 0x1u &&
        registryStageAfterReset.resourcesOwnedMask == 0 &&
        registryStageAfterReset.lifetimeCurrentMask == 0 &&
        registryStageAfterReset.deviceMatchesMask == 0 &&
        registryStageAfterReset.descriptorExactMask == 0 &&
        registryStageAfterReset.readyMask == 0 &&
        registryStageAfterReset.pendingMask == 0x1u &&
        !registryStageAfterReset.allRequiredReady,
        "R109 Reset keeps required stage activation-pending");
    require(
        registryStageAfterReset.snapshotToken == 0 &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageBeforeResetToken),
        "R110 Reset invalidates pre-Reset readiness snapshot token");
    require(
        managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, d3d.device),
        "R108 post-Reset registry mirror recreation");
    const auto registryMirrorAfterResetRecreate =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorAfterResetRecreate.ready &&
        registryMirrorAfterResetRecreate.deviceGeneration ==
            registryGenerationBeforeReset + 1 &&
        registryMirrorAfterResetRecreate.mirrorGeneration ==
            registryMirrorAfterResetRecreate.deviceGeneration &&
        registryMirrorAfterResetRecreate.mirrorShadowVersion ==
            registryVersionBeforeReset,
        "R108 post-Reset mirror readiness uses current device generation");
    const auto registryStageAfterResetRecreate =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterResetRecreate.inputValid &&
        registryStageAfterResetRecreate.readyMask == 0x1u &&
        registryStageAfterResetRecreate.pendingMask == 0 &&
        registryStageAfterResetRecreate.allRequiredReady,
        "R109 post-Reset recreation restores required stage readiness");
    require(
        registryStageAfterResetRecreate.snapshotToken != 0 &&
        registryStageAfterResetRecreate.snapshotToken !=
            registryStageBeforeResetToken &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device,
            registryStageAfterResetRecreate.snapshotToken),
        "R110 post-Reset recreation issues a generation-current fresh token");

    managedRegistry.forget_texture(&registryTextureA);
    require(
        !managedRegistry.contains(&registryTextureA) &&
        managedRegistry.size() == 0,
        "R105 Release cleanup forgets per-texture shadow");

    require(
        managedRegistry.register_texture(
            &registryTextureA, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_MANAGED) &&
        managedRegistry.register_texture(
            &registryTextureB, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_MANAGED) &&
        managedRegistry.size() == 2,
        "R105 registry clear prerequisite");
    managedRegistry.clear();
    require(
        managedRegistry.size() == 0,
        "R105 registry shutdown clears all texture ownership");

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

    ID3DBlob* isolationGeometryBytecode = compile_geometry_shader();
    ID3D11GeometryShader* isolationGeometryShader = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateGeometryShader(
            isolationGeometryBytecode->GetBufferPointer(),
            isolationGeometryBytecode->GetBufferSize(),
            nullptr,
            &isolationGeometryShader)) &&
        isolationGeometryShader != nullptr,
        "CreateGeometryShader R147 isolation probe");

    D3D11_BUFFER_DESC isolationStreamOutputDesc{};
    isolationStreamOutputDesc.ByteWidth = 64;
    isolationStreamOutputDesc.Usage = D3D11_USAGE_DEFAULT;
    isolationStreamOutputDesc.BindFlags = D3D11_BIND_STREAM_OUTPUT;
    ID3D11Buffer* isolationStreamOutputBuffer = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateBuffer(
            &isolationStreamOutputDesc, nullptr,
            &isolationStreamOutputBuffer)) &&
        isolationStreamOutputBuffer != nullptr,
        "CreateBuffer R148 stream-output isolation probe");
    D3D11_QUERY_DESC isolationPredicateDesc{};
    isolationPredicateDesc.Query = D3D11_QUERY_OCCLUSION_PREDICATE;
    ID3D11Predicate* isolationPredicate = nullptr;
    require(
        SUCCEEDED(d3d.device->CreatePredicate(
            &isolationPredicateDesc, &isolationPredicate)) &&
        isolationPredicate != nullptr,
        "CreatePredicate R148 draw-predication isolation probe");

    NativeFixedFunctionTransformBuffer owner;
    require(!owner.ready(), "R96 owner must start dormant");
    require(owner.upload_generation() == 0,
            "R96 owner generation must start at zero");
    require(owner.initialize(d3d.device),
            "R96 owner initialize");

    OutRunVR::DrawState::RenderStateSnapshot renderStateSource{};
    renderStateSource.complete = true;
    renderStateSource.stencilEnable = TRUE;
    renderStateSource.stencilRef = 0x5au;
    renderStateSource.stencilFunc = D3DCMP_ALWAYS;
    const auto renderStateTranslation =
        translate_pipeline(renderStateSource);
    require(
        renderStateTranslation.exact(),
        "R116 render-state translation prerequisite");

    NativeFixedFunctionRenderStateBundle renderStateBundle;
    require(
        !renderStateBundle.ready(),
        "R116 render-state bundle must start dormant");
    require(
        renderStateBundle.initialize(d3d.device, renderStateTranslation),
        "R116 render-state bundle initialize");
    require(
        renderStateBundle.ready() &&
        renderStateBundle.device() == d3d.device &&
        renderStateBundle.blend_state() != nullptr &&
        renderStateBundle.depth_stencil_state() != nullptr &&
        renderStateBundle.rasterizer_state() != nullptr &&
        renderStateBundle.stencil_ref() == 0x5au,
        "R116 render-state bundle owns exact translated state objects");

    const auto renderStateReady =
        renderStateBundle.translation_readiness(
            d3d.device, renderStateTranslation);
    require(
        renderStateReady.inputValid &&
        renderStateReady.bundleReady &&
        renderStateReady.deviceMatches &&
        renderStateReady.translationMatches &&
        renderStateReady.ready &&
        renderStateReady.bundleGeneration != 0 &&
        renderStateReady.translationIdentity != 0 &&
        renderStateReady.snapshotToken != 0 &&
        renderStateBundle.validate_translation_snapshot(
            d3d.device, renderStateTranslation,
            renderStateReady.snapshotToken),
        "R116 exact render-state translation issues a valid snapshot");

    auto changedRenderStateTranslation = renderStateTranslation;
    changedRenderStateTranslation.stencil_ref ^= 0x1u;
    const auto changedRenderStateReady =
        renderStateBundle.translation_readiness(
            d3d.device, changedRenderStateTranslation);
    require(
        changedRenderStateReady.inputValid &&
        changedRenderStateReady.bundleReady &&
        changedRenderStateReady.deviceMatches &&
        !changedRenderStateReady.translationMatches &&
        !changedRenderStateReady.ready &&
        changedRenderStateReady.snapshotToken == 0 &&
        !renderStateBundle.validate_translation_snapshot(
            d3d.device, changedRenderStateTranslation,
            renderStateReady.snapshotToken),
        "R116 changed render-state identity fails closed");

    DevicePair renderStateOtherDevice = create_warp_device();
    const auto foreignRenderStateReady =
        renderStateBundle.translation_readiness(
            renderStateOtherDevice.device, renderStateTranslation);
    require(
        foreignRenderStateReady.inputValid &&
        foreignRenderStateReady.bundleReady &&
        !foreignRenderStateReady.deviceMatches &&
        !foreignRenderStateReady.ready &&
        foreignRenderStateReady.snapshotToken == 0,
        "R116 foreign device cannot claim render-state readiness");
    renderStateOtherDevice.context->Release();
    renderStateOtherDevice.device->Release();

    const auto renderStateInitialToken = renderStateReady.snapshotToken;
    const auto renderStateInitialGeneration =
        renderStateReady.bundleGeneration;
    auto inexactRenderStateTranslation = renderStateTranslation;
    inexactRenderStateTranslation.unsupported |= PipelineUnsupportedBlend;
    require(
        !renderStateBundle.initialize(
            d3d.device, inexactRenderStateTranslation) &&
        !renderStateBundle.ready(),
        "R116 inexact render-state translation must fail closed");
    require(
        renderStateBundle.initialize(d3d.device, renderStateTranslation),
        "R116 render-state bundle recreate");
    const auto renderStateRecreated =
        renderStateBundle.translation_readiness(
            d3d.device, renderStateTranslation);
    require(
        renderStateRecreated.ready &&
        renderStateRecreated.bundleGeneration >
            renderStateInitialGeneration &&
        renderStateRecreated.snapshotToken != 0 &&
        renderStateRecreated.snapshotToken != renderStateInitialToken &&
        !renderStateBundle.validate_translation_snapshot(
            d3d.device, renderStateTranslation,
            renderStateInitialToken) &&
        renderStateBundle.validate_translation_snapshot(
            d3d.device, renderStateTranslation,
            renderStateRecreated.snapshotToken),
        "R116 render-state bundle recreation invalidates stale snapshot");

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

    const auto pipelineIdentityReady =
        pipelineBundle.translation_readiness(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype);
    require(
        pipelineIdentityReady.inputValid &&
        pipelineIdentityReady.bundleReady &&
        pipelineIdentityReady.deviceMatches &&
        pipelineIdentityReady.inputLayoutMatches &&
        pipelineIdentityReady.vertexShaderMatches &&
        pipelineIdentityReady.pixelShaderMatches &&
        pipelineIdentityReady.ready &&
        pipelineIdentityReady.bundleGeneration != 0 &&
        pipelineIdentityReady.snapshotToken != 0 &&
        pipelineBundle.validate_translation_snapshot(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R112 exact fixed-function pipeline translation identity issues a valid snapshot");

    require(
        pipelineBundle.upload_transform_for_observation(d3d.context, transform),
        "final VS b0 transform upload prerequisite");
    const auto pipelineTransformBindingReady =
        pipelineBundle.transform_buffer().binding_readiness(
            d3d.context, transform);
    require(
        pipelineTransformBindingReady.inputValid &&
        pipelineTransformBindingReady.ownerReady &&
        pipelineTransformBindingReady.contextMatches &&
        pipelineTransformBindingReady.payloadMatches &&
        pipelineTransformBindingReady.boundExact &&
        pipelineTransformBindingReady.uploadPresent &&
        pipelineTransformBindingReady.ready &&
        pipelineTransformBindingReady.payloadHash == transform.payloadHash &&
        pipelineTransformBindingReady.snapshotToken != 0 &&
        pipelineBundle.transform_buffer().validate_binding_snapshot(
            d3d.context, transform, pipelineTransformBindingReady.snapshotToken),
        "final VS b0 transform binding seals exact WVP payload");

    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "dormant pipeline binding accepts exact same-device R97 snapshot");

    ID3D11InputLayout* boundPipelineLayout = nullptr;
    ID3D11VertexShader* boundPipelineVertexShader = nullptr;
    ID3D11PixelShader* boundPipelinePixelShader = nullptr;
    d3d.context->IAGetInputLayout(&boundPipelineLayout);
    d3d.context->VSGetShader(
        &boundPipelineVertexShader, nullptr, nullptr);
    d3d.context->PSGetShader(
        &boundPipelinePixelShader, nullptr, nullptr);
    require(
        boundPipelineLayout == pipelineBundle.input_layout() &&
        boundPipelineVertexShader == pipelineBundle.vertex_shader() &&
        boundPipelinePixelShader == pipelineBundle.pixel_shader(),
        "dormant pipeline binding preserves exact IA VS PS identity");
    if (boundPipelineLayout)
        boundPipelineLayout->Release();
    if (boundPipelineVertexShader)
        boundPipelineVertexShader->Release();
    if (boundPipelinePixelShader)
        boundPipelinePixelShader->Release();

    require(
        !pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype, 0),
        "dormant pipeline binding rejects missing R97 snapshot");
    require(
        !pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken ^ 0x100000001b3ull),
        "dormant pipeline binding rejects stale R97 snapshot");

    DevicePair pipelineBindingForeignDevice = create_warp_device();
    require(
        !pipelineBundle.bind_for_observation(
            pipelineBindingForeignDevice.context,
            inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "dormant pipeline binding rejects foreign D3D11 context");
    pipelineBindingForeignDevice.context->Release();
    pipelineBindingForeignDevice.device->Release();

    d3d.context->IASetInputLayout(nullptr);
    d3d.context->VSSetShader(vertexShader, nullptr, 0);
    d3d.context->PSSetShader(nullptr, nullptr, 0);

    NativeManagedTextureStageReadiness untexturedStageReady{};
    untexturedStageReady.inputValid = true;
    untexturedStageReady.allRequiredReady = true;
    const auto untexturedActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, untexturedStageReady);
    require(
        untexturedActivation.inputValid &&
        untexturedActivation.pipelineReady &&
        untexturedActivation.textureStagesReady &&
        untexturedActivation.componentSnapshotsPresent &&
        untexturedActivation.ready &&
        untexturedActivation.requiredTextureMask == 0 &&
        untexturedActivation.pipelineSnapshotToken ==
            pipelineIdentityReady.snapshotToken &&
        untexturedActivation.textureSnapshotToken == 0 &&
        untexturedActivation.snapshotToken != 0 &&
        validate_fixed_function_activation_snapshot(
            pipelineIdentityReady, untexturedStageReady,
            untexturedActivation.snapshotToken),
        "R115 composite activation readiness accepts exact untextured evidence");

    NativeManagedTextureStageReadiness texturedStageReady{};
    texturedStageReady.inputValid = true;
    texturedStageReady.allRequiredReady = true;
    texturedStageReady.requiredMask = 0x1u;
    texturedStageReady.readyMask = 0x1u;
    texturedStageReady.snapshotToken = 0x115001ull;
    const auto texturedActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, texturedStageReady);
    require(
        texturedActivation.inputValid &&
        texturedActivation.pipelineReady &&
        texturedActivation.textureStagesReady &&
        texturedActivation.componentSnapshotsPresent &&
        texturedActivation.ready &&
        texturedActivation.requiredTextureMask == 0x1u &&
        texturedActivation.textureSnapshotToken ==
            texturedStageReady.snapshotToken &&
        texturedActivation.snapshotToken != 0 &&
        validate_fixed_function_activation_snapshot(
            pipelineIdentityReady, texturedStageReady,
            texturedActivation.snapshotToken),
        "R115 composite activation readiness requires both exact component snapshots");

    auto missingTextureSnapshot = texturedStageReady;
    missingTextureSnapshot.snapshotToken = 0;
    const auto missingTextureActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, missingTextureSnapshot);
    auto pendingTextureStage = texturedStageReady;
    pendingTextureStage.allRequiredReady = false;
    pendingTextureStage.readyMask = 0;
    pendingTextureStage.pendingMask = 0x1u;
    pendingTextureStage.snapshotToken = 0;
    const auto pendingTextureActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, pendingTextureStage);
    auto pipelineNotReady = pipelineIdentityReady;
    pipelineNotReady.ready = false;
    const auto pipelinePendingActivation =
        compose_fixed_function_activation_readiness(
            pipelineNotReady, texturedStageReady);
    require(
        !missingTextureActivation.ready &&
        missingTextureActivation.snapshotToken == 0 &&
        !pendingTextureActivation.ready &&
        pendingTextureActivation.snapshotToken == 0 &&
        !pipelinePendingActivation.ready &&
        pipelinePendingActivation.snapshotToken == 0,
        "R115 composite activation readiness fails closed on missing component evidence");

    auto changedPipelineIdentity = pipelineIdentityReady;
    changedPipelineIdentity.snapshotToken ^= 0x100000001b3ull;
    const auto changedActivation =
        compose_fixed_function_activation_readiness(
            changedPipelineIdentity, texturedStageReady);
    require(
        changedActivation.ready &&
        changedActivation.snapshotToken != 0 &&
        changedActivation.snapshotToken != texturedActivation.snapshotToken &&
        !validate_fixed_function_activation_snapshot(
            changedPipelineIdentity, texturedStageReady,
            texturedActivation.snapshotToken) &&
        validate_fixed_function_activation_snapshot(
            changedPipelineIdentity, texturedStageReady,
            changedActivation.snapshotToken),
        "R115 composite activation snapshot changes with component identity");

    outrun::vr::dx11::NativeSurfaceMirror outputColorSurface;
    require(
        outputColorSurface.initialize(
            d3d.device, ResourceRole::Color, 64u, 32u,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, D3DUSAGE_RENDERTARGET,
            D3DMULTISAMPLE_NONE, 0u),
        "R145 live OM color mirror prerequisite");
    outrun::vr::dx11::NativeSurfaceMirror outputDepthSurface;
    require(
        outputDepthSurface.initialize(
            d3d.device, ResourceRole::DepthStencil, 64u, 32u,
            D3DFMT_D24S8, D3DPOOL_DEFAULT, D3DUSAGE_DEPTHSTENCIL,
            D3DMULTISAMPLE_NONE, 0u),
        "R145 live OM depth mirror prerequisite");
    const auto surfacePairReady =
        outrun::vr::dx11::compose_surface_pair_readiness(
            d3d.device, outputColorSurface, outputDepthSurface);
    require(
        surfacePairReady.ready &&
        surfacePairReady.snapshotToken != 0,
        "R145 live OM surface pair prerequisite");

    outrun::vr::dx11::NativeSurfacePairBinding surfaceTargetBinding;
    require(
        surfaceTargetBinding.initialize(
            d3d.device, outputColorSurface, outputDepthSurface,
            surfacePairReady) &&
        surfaceTargetBinding.apply(
            d3d.context, outputColorSurface, outputDepthSurface),
        "R145 live OM target owner prerequisite");
    const auto surfaceTargetBindingReady =
        surfaceTargetBinding.binding_readiness(
            d3d.context, outputColorSurface, outputDepthSurface);
    require(
        surfaceTargetBindingReady.ready &&
        surfaceTargetBindingReady.surfacePairSnapshotToken ==
            surfacePairReady.snapshotToken &&
        surfaceTargetBindingReady.snapshotToken != 0 &&
        surfaceTargetBinding.validate_binding_snapshot(
            d3d.context, outputColorSurface, outputDepthSurface,
            surfaceTargetBindingReady.snapshotToken),
        "R145 live OM target prerequisite seals current RTV DSV");

    auto outputStateSource = renderStateSource;
    outputStateSource.outputStateComplete = true;
    outputStateSource.scissorTestEnable = TRUE;
    outputStateSource.blendFactor = 0xFF804020u;
    outputStateSource.multiSampleMask = 0x0F0FF0F0u;
    outputStateSource.viewport.X = 4;
    outputStateSource.viewport.Y = 2;
    outputStateSource.viewport.Width = 56;
    outputStateSource.viewport.Height = 28;
    outputStateSource.viewport.MinZ = 0.125f;
    outputStateSource.viewport.MaxZ = 0.875f;
    outputStateSource.scissorRect = RECT{5, 3, 58, 29};

    const auto outputStateReady =
        compose_fixed_function_output_state_readiness(
            outputStateSource, surfacePairReady);
    require(
        outputStateReady.inputValid &&
        outputStateReady.viewportExact &&
        outputStateReady.scissorExact &&
        outputStateReady.omDynamicExact &&
        outputStateReady.ready &&
        outputStateReady.viewport.TopLeftX == 4.0f &&
        outputStateReady.viewport.TopLeftY == 2.0f &&
        outputStateReady.viewport.Width == 56.0f &&
        outputStateReady.viewport.Height == 28.0f &&
        outputStateReady.viewport.MinDepth == 0.125f &&
        outputStateReady.viewport.MaxDepth == 0.875f &&
        outputStateReady.scissorRect.left == 5 &&
        outputStateReady.scissorRect.top == 3 &&
        outputStateReady.scissorRect.right == 58 &&
        outputStateReady.scissorRect.bottom == 29 &&
        outputStateReady.blendFactor[0] == 128.0f / 255.0f &&
        outputStateReady.blendFactor[1] == 64.0f / 255.0f &&
        outputStateReady.blendFactor[2] == 32.0f / 255.0f &&
        outputStateReady.blendFactor[3] == 1.0f &&
        outputStateReady.sampleMask == 0x0F0FF0F0u &&
        outputStateReady.snapshotToken != 0 &&
        validate_fixed_function_output_state_snapshot(
            outputStateSource, surfacePairReady,
            outputStateReady.snapshotToken),
        "R124 exact dynamic output state issues a valid snapshot");

    const auto outputBindingTranslation =
        translate_pipeline(outputStateSource);
    require(
        outputBindingTranslation.exact() &&
        outputBindingTranslation.rasterizer.ScissorEnable,
        "R126 output-state binding translation prerequisite");

    NativeFixedFunctionRenderStateBundle outputBindingRenderStateBundle;
    require(
        outputBindingRenderStateBundle.initialize(
            d3d.device, outputBindingTranslation),
        "R126 output-state binding render bundle initialize");
    const auto outputBindingRenderReady =
        outputBindingRenderStateBundle.translation_readiness(
            d3d.device, outputBindingTranslation);
    require(
        outputBindingRenderReady.ready &&
        outputBindingRenderReady.snapshotToken != 0,
        "R126 output-state binding render snapshot prerequisite");

    NativeFixedFunctionOutputStateBinding outputStateBinding;
    require(
        outputStateBinding.initialize(
            d3d.device,
            outputBindingRenderStateBundle,
            outputBindingTranslation,
            outputBindingRenderReady.snapshotToken,
            outputStateSource,
            surfacePairReady,
            outputStateReady.snapshotToken) &&
        outputStateBinding.ready() &&
        outputStateBinding.render_state_snapshot_token() ==
            outputBindingRenderReady.snapshotToken &&
        outputStateBinding.surface_pair_snapshot_token() ==
            surfacePairReady.snapshotToken &&
        outputStateBinding.output_state_snapshot_token() ==
            outputStateReady.snapshotToken &&
        outputStateBinding.snapshot_token() != 0,
        "R126 exact render/output snapshots initialize dormant binding owner");
    require(
        outputStateBinding.apply(d3d.context),
        "R126 output binding applies exact RS/OM state");

    ID3D11RasterizerState* boundRasterizer = nullptr;
    ID3D11BlendState* boundBlend = nullptr;
    ID3D11DepthStencilState* boundDepthStencil = nullptr;
    UINT boundStencilRef = 0;
    FLOAT boundBlendFactor[4] = {};
    UINT boundSampleMask = 0;
    UINT boundViewportCount = 1;
    UINT boundScissorCount = 1;
    D3D11_VIEWPORT boundViewport{};
    D3D11_RECT boundScissor{};
    d3d.context->RSGetState(&boundRasterizer);
    d3d.context->RSGetViewports(&boundViewportCount, &boundViewport);
    d3d.context->RSGetScissorRects(&boundScissorCount, &boundScissor);
    d3d.context->OMGetBlendState(
        &boundBlend, boundBlendFactor, &boundSampleMask);
    d3d.context->OMGetDepthStencilState(
        &boundDepthStencil, &boundStencilRef);
    require(
        boundRasterizer == outputBindingRenderStateBundle.rasterizer_state() &&
        boundBlend == outputBindingRenderStateBundle.blend_state() &&
        boundDepthStencil ==
            outputBindingRenderStateBundle.depth_stencil_state() &&
        boundStencilRef == outputBindingRenderStateBundle.stencil_ref() &&
        boundViewportCount == 1 &&
        boundViewport.TopLeftX == outputStateReady.viewport.TopLeftX &&
        boundViewport.TopLeftY == outputStateReady.viewport.TopLeftY &&
        boundViewport.Width == outputStateReady.viewport.Width &&
        boundViewport.Height == outputStateReady.viewport.Height &&
        boundViewport.MinDepth == outputStateReady.viewport.MinDepth &&
        boundViewport.MaxDepth == outputStateReady.viewport.MaxDepth &&
        boundScissorCount == 1 &&
        boundScissor.left == outputStateReady.scissorRect.left &&
        boundScissor.top == outputStateReady.scissorRect.top &&
        boundScissor.right == outputStateReady.scissorRect.right &&
        boundScissor.bottom == outputStateReady.scissorRect.bottom &&
        boundBlendFactor[0] == outputStateReady.blendFactor[0] &&
        boundBlendFactor[1] == outputStateReady.blendFactor[1] &&
        boundBlendFactor[2] == outputStateReady.blendFactor[2] &&
        boundBlendFactor[3] == outputStateReady.blendFactor[3] &&
        boundSampleMask == outputStateReady.sampleMask,
        "R126 WARP context exposes the exact sealed RS/OM binding");
    if (boundRasterizer)
        boundRasterizer->Release();
    if (boundBlend)
        boundBlend->Release();
    if (boundDepthStencil)
        boundDepthStencil->Release();

    const auto liveOutputBindingReady =
        outputStateBinding.binding_readiness(d3d.context);
    require(
        liveOutputBindingReady.inputValid &&
        liveOutputBindingReady.ownerReady &&
        liveOutputBindingReady.contextMatches &&
        liveOutputBindingReady.rasterizerMatches &&
        liveOutputBindingReady.viewportMatches &&
        liveOutputBindingReady.scissorMatches &&
        liveOutputBindingReady.blendStateMatches &&
        liveOutputBindingReady.blendFactorMatches &&
        liveOutputBindingReady.sampleMaskMatches &&
        liveOutputBindingReady.depthStencilMatches &&
        liveOutputBindingReady.stencilRefMatches &&
        liveOutputBindingReady.ready &&
        liveOutputBindingReady.outputBindingSnapshotToken ==
            outputStateBinding.snapshot_token() &&
        liveOutputBindingReady.snapshotToken != 0 &&
        outputStateBinding.validate_binding_snapshot(
            d3d.context, liveOutputBindingReady.snapshotToken),
        "R137 live output binding issues exact RS OM snapshot");

    d3d.context->RSSetState(nullptr);
    const auto driftedOutputBinding =
        outputStateBinding.binding_readiness(d3d.context);
    require(
        driftedOutputBinding.inputValid &&
        driftedOutputBinding.ownerReady &&
        driftedOutputBinding.contextMatches &&
        !driftedOutputBinding.rasterizerMatches &&
        !driftedOutputBinding.ready &&
        driftedOutputBinding.snapshotToken == 0 &&
        !outputStateBinding.validate_binding_snapshot(
            d3d.context, liveOutputBindingReady.snapshotToken),
        "R137 live output binding fails closed after RS drift");
    require(
        outputStateBinding.apply(d3d.context),
        "R137 live output binding restores sealed RS OM state");
    const auto restoredOutputBinding =
        outputStateBinding.binding_readiness(d3d.context);
    require(
        restoredOutputBinding.ready &&
        restoredOutputBinding.snapshotToken ==
            liveOutputBindingReady.snapshotToken &&
        outputStateBinding.validate_binding_snapshot(
            d3d.context, liveOutputBindingReady.snapshotToken),
        "R137 restored output binding reproduces exact snapshot");

    DevicePair outputBindingOtherDevice = create_warp_device();
    require(
        !outputStateBinding.apply(outputBindingOtherDevice.context),
        "R126 foreign D3D11 context cannot consume binding owner");
    outputBindingOtherDevice.context->Release();
    outputBindingOtherDevice.device->Release();

    NativeFixedFunctionOutputStateBinding rejectedOutputBinding;
    require(
        !rejectedOutputBinding.initialize(
            d3d.device,
            outputBindingRenderStateBundle,
            outputBindingTranslation,
            outputBindingRenderReady.snapshotToken,
            outputStateSource,
            surfacePairReady,
            0) &&
        !rejectedOutputBinding.ready(),
        "R126 missing R124 snapshot token fails closed");
    require(
        !rejectedOutputBinding.initialize(
            d3d.device,
            outputBindingRenderStateBundle,
            outputBindingTranslation,
            0,
            outputStateSource,
            surfacePairReady,
            outputStateReady.snapshotToken) &&
        !rejectedOutputBinding.ready(),
        "R126 missing R116 snapshot token fails closed");

    require(
        !rejectedOutputBinding.initialize(
            d3d.device,
            renderStateBundle,
            renderStateTranslation,
            renderStateRecreated.snapshotToken,
            outputStateSource,
            surfacePairReady,
            outputStateReady.snapshotToken) &&
        !rejectedOutputBinding.ready(),
        "R126 mismatched sealed scissor state fails closed");

    auto staleOutputBindingSource = outputStateSource;
    staleOutputBindingSource.blendFactor ^= 0x00010000u;
    require(
        !rejectedOutputBinding.initialize(
            d3d.device,
            outputBindingRenderStateBundle,
            outputBindingTranslation,
            outputBindingRenderReady.snapshotToken,
            staleOutputBindingSource,
            surfacePairReady,
            outputStateReady.snapshotToken) &&
        !rejectedOutputBinding.ready(),
        "R126 stale R124 source/token pair fails closed");

    auto incompleteOutputState = outputStateSource;
    incompleteOutputState.outputStateComplete = false;
    const auto incompleteOutputReady =
        compose_fixed_function_output_state_readiness(
            incompleteOutputState, surfacePairReady);
    require(
        !incompleteOutputReady.inputValid &&
        !incompleteOutputReady.ready &&
        incompleteOutputReady.snapshotToken == 0,
        "R124 incomplete output-state observation fails closed");

    auto invalidViewportState = outputStateSource;
    invalidViewportState.viewport.Width = 61;
    const auto invalidViewportReady =
        compose_fixed_function_output_state_readiness(
            invalidViewportState, surfacePairReady);
    require(
        invalidViewportReady.inputValid &&
        !invalidViewportReady.viewportExact &&
        !invalidViewportReady.ready &&
        invalidViewportReady.snapshotToken == 0,
        "R124 out-of-bounds viewport fails closed");

    auto invalidScissorState = outputStateSource;
    invalidScissorState.scissorRect.right = 65;
    const auto invalidScissorReady =
        compose_fixed_function_output_state_readiness(
            invalidScissorState, surfacePairReady);
    require(
        invalidScissorReady.inputValid &&
        invalidScissorReady.viewportExact &&
        !invalidScissorReady.scissorExact &&
        !invalidScissorReady.ready &&
        invalidScissorReady.snapshotToken == 0,
        "R124 enabled out-of-bounds scissor fails closed");

    auto changedOutputStateSource = outputStateSource;
    changedOutputStateSource.blendFactor ^= 0x00010000u;
    changedOutputStateSource.multiSampleMask ^= 0x00000001u;
    const auto changedOutputStateReady =
        compose_fixed_function_output_state_readiness(
            changedOutputStateSource, surfacePairReady);
    require(
        changedOutputStateReady.ready &&
        changedOutputStateReady.snapshotToken != 0 &&
        changedOutputStateReady.snapshotToken !=
            outputStateReady.snapshotToken &&
        !validate_fixed_function_output_state_snapshot(
            changedOutputStateSource, surfacePairReady,
            outputStateReady.snapshotToken) &&
        validate_fixed_function_output_state_snapshot(
            changedOutputStateSource, surfacePairReady,
            changedOutputStateReady.snapshotToken),
        "R124 OM dynamic state changes invalidate output snapshot");

    constexpr UINT drawTextureStageSlot = 0;
    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, drawTextureStageSlot, samplerOwner, textureView),
        "R132 textured draw texture-stage rebind prerequisite");
    const auto drawTextureStageReady =
        outrun::vr::dx11::observe_fixed_function_texture_stage_binding(
            d3d.context, drawTextureStageSlot, samplerOwner, textureView);
    require(
        drawTextureStageReady.ready &&
        drawTextureStageReady.snapshotToken != 0,
        "R132 textured draw texture-stage snapshot prerequisite");

    const auto drawReady =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady);
    require(
        drawReady.inputValid &&
        drawReady.activationReady &&
        drawReady.renderStateReady &&
        drawReady.surfacePairReady &&
        drawReady.outputStateReady &&
        drawReady.outputBindingReady &&
        drawReady.geometryReady &&
        drawReady.componentSnapshotsPresent &&
        drawReady.ready &&
        drawReady.requiredTextureMask == 0x1u &&
        drawReady.activationSnapshotToken ==
            texturedActivation.snapshotToken &&
        drawReady.pipelineSnapshotToken ==
            texturedActivation.pipelineSnapshotToken &&
        drawReady.renderStateSnapshotToken ==
            outputBindingRenderReady.snapshotToken &&
        drawReady.surfacePairSnapshotToken ==
            surfacePairReady.snapshotToken &&
        drawReady.outputStateSnapshotToken ==
            outputStateReady.snapshotToken &&
        drawReady.outputBindingSnapshotToken ==
            outputStateBinding.snapshot_token() &&
        drawReady.geometrySnapshotToken ==
            indexedGeometryReady.snapshotToken &&
        drawReady.snapshotToken != 0 &&
        validate_fixed_function_draw_readiness_integrity(drawReady) &&
        validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady,
            drawReady.snapshotToken),
        "R131 draw readiness composes sealed output binding identity");

    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R134 bound draw pipeline rebind prerequisite");
    const auto drawPipelineBindingReady =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        drawPipelineBindingReady.inputValid &&
        drawPipelineBindingReady.bundleReady &&
        drawPipelineBindingReady.contextMatches &&
        drawPipelineBindingReady.translationSnapshotValid &&
        drawPipelineBindingReady.geometryShaderClear &&
        drawPipelineBindingReady.hullShaderClear &&
        drawPipelineBindingReady.domainShaderClear &&
        drawPipelineBindingReady.graphicsStageIsolationReady &&
        drawPipelineBindingReady.streamOutputTargetsClear &&
        drawPipelineBindingReady.predicationClear &&
        drawPipelineBindingReady.drawSideEffectIsolationReady &&
        drawPipelineBindingReady.boundExact &&
        drawPipelineBindingReady.ready &&
        drawPipelineBindingReady.pipelineSnapshotToken ==
            pipelineIdentityReady.snapshotToken &&
        drawPipelineBindingReady.snapshotToken != 0 &&
        pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R134 exact IA VS PS binding issues a live snapshot");

    d3d.context->GSSetShader(isolationGeometryShader, nullptr, 0);
    const auto graphicsStageIsolationDrift =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        graphicsStageIsolationDrift.inputValid &&
        graphicsStageIsolationDrift.bundleReady &&
        graphicsStageIsolationDrift.contextMatches &&
        graphicsStageIsolationDrift.translationSnapshotValid &&
        !graphicsStageIsolationDrift.geometryShaderClear &&
        graphicsStageIsolationDrift.hullShaderClear &&
        graphicsStageIsolationDrift.domainShaderClear &&
        !graphicsStageIsolationDrift.graphicsStageIsolationReady &&
        !graphicsStageIsolationDrift.boundExact &&
        !graphicsStageIsolationDrift.ready &&
        graphicsStageIsolationDrift.snapshotToken == 0 &&
        !pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R147 live GS drift invalidates fixed-function pipeline binding");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R147 restore fixed-function graphics stage isolation");
    const auto graphicsStageIsolationRestored =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        graphicsStageIsolationRestored.ready &&
        graphicsStageIsolationRestored.graphicsStageIsolationReady &&
        graphicsStageIsolationRestored.streamOutputTargetsClear &&
        graphicsStageIsolationRestored.predicationClear &&
        graphicsStageIsolationRestored.drawSideEffectIsolationReady &&
        graphicsStageIsolationRestored.snapshotToken ==
            drawPipelineBindingReady.snapshotToken,
        "R147 restored graphics stage isolation reproduces pipeline snapshot");

    UINT isolationStreamOutputOffset = 0;
    d3d.context->SOSetTargets(
        1, &isolationStreamOutputBuffer, &isolationStreamOutputOffset);
    const auto streamOutputIsolationDrift =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        streamOutputIsolationDrift.inputValid &&
        streamOutputIsolationDrift.graphicsStageIsolationReady &&
        !streamOutputIsolationDrift.streamOutputTargetsClear &&
        streamOutputIsolationDrift.predicationClear &&
        !streamOutputIsolationDrift.drawSideEffectIsolationReady &&
        !streamOutputIsolationDrift.boundExact &&
        !streamOutputIsolationDrift.ready &&
        streamOutputIsolationDrift.snapshotToken == 0 &&
        !pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R148 live SO target drift invalidates fixed-function pipeline binding");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R148 restore fixed-function stream-output isolation");
    const auto streamOutputIsolationRestored =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        streamOutputIsolationRestored.ready &&
        streamOutputIsolationRestored.streamOutputTargetsClear &&
        streamOutputIsolationRestored.predicationClear &&
        streamOutputIsolationRestored.drawSideEffectIsolationReady &&
        streamOutputIsolationRestored.snapshotToken ==
            drawPipelineBindingReady.snapshotToken,
        "R148 restored SO isolation reproduces pipeline snapshot");

    d3d.context->SetPredication(isolationPredicate, TRUE);
    const auto predicationIsolationDrift =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        predicationIsolationDrift.inputValid &&
        predicationIsolationDrift.graphicsStageIsolationReady &&
        predicationIsolationDrift.streamOutputTargetsClear &&
        !predicationIsolationDrift.predicationClear &&
        !predicationIsolationDrift.drawSideEffectIsolationReady &&
        !predicationIsolationDrift.boundExact &&
        !predicationIsolationDrift.ready &&
        predicationIsolationDrift.snapshotToken == 0 &&
        !pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R148 live predication drift invalidates fixed-function pipeline binding");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R148 restore fixed-function draw-predication isolation");
    const auto predicationIsolationRestored =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        predicationIsolationRestored.ready &&
        predicationIsolationRestored.streamOutputTargetsClear &&
        predicationIsolationRestored.predicationClear &&
        predicationIsolationRestored.drawSideEffectIsolationReady &&
        predicationIsolationRestored.snapshotToken ==
            drawPipelineBindingReady.snapshotToken,
        "R148 restored predication isolation reproduces pipeline snapshot");

    const auto texturedDrawReady =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            drawReady, d3d.context, drawTextureStageSlot, samplerOwner, textureView);
    require(
        texturedDrawReady.inputValid &&
        texturedDrawReady.drawReady &&
        texturedDrawReady.textureStageReady &&
        texturedDrawReady.textureMaskMatches &&
        texturedDrawReady.componentSnapshotsPresent &&
        texturedDrawReady.ready &&
        texturedDrawReady.requiredTextureMask == 0x1u &&
        texturedDrawReady.observedTextureMask == 0x1u &&
        texturedDrawReady.drawSnapshotToken == drawReady.snapshotToken &&
        texturedDrawReady.textureStageSnapshotToken ==
            drawTextureStageReady.snapshotToken &&
        texturedDrawReady.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_textured_draw_snapshot(
            drawReady, d3d.context, drawTextureStageSlot, samplerOwner, textureView,
            texturedDrawReady.snapshotToken),
        "R133 textured draw readiness composes the exact required PS stage");

    auto multiStageTextureReady = texturedStageReady;
    multiStageTextureReady.requiredMask = 0x3u;
    multiStageTextureReady.readyMask = 0x3u;
    multiStageTextureReady.pendingMask = 0;
    multiStageTextureReady.snapshotToken = 0x136003ull;
    const auto multiStageActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, multiStageTextureReady);
    require(
        multiStageActivation.ready &&
        multiStageActivation.requiredTextureMask == 0x3u &&
        multiStageActivation.snapshotToken != 0,
        "R136 two-stage activation prerequisite");

    const auto multiStageDrawReady =
        compose_fixed_function_draw_readiness(
            multiStageActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady);
    require(
        multiStageDrawReady.ready &&
        multiStageDrawReady.requiredTextureMask == 0x3u &&
        validate_fixed_function_draw_readiness_integrity(
            multiStageDrawReady),
        "R136 two-stage sealed draw prerequisite");

    constexpr UINT secondDrawTextureStageSlot = 1;
    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, secondDrawTextureStageSlot, samplerOwner, textureView),
        "R136 second texture-stage live binding prerequisite");

    std::array<
        const outrun::vr::dx11::NativeFixedFunctionSamplerState*, 8>
        multiStageSamplers{};
    std::array<
        const outrun::vr::dx11::NativeFixedFunctionTextureView*, 8>
        multiStageTextures{};
    multiStageSamplers[0] = &samplerOwner;
    multiStageSamplers[1] = &samplerOwner;
    multiStageTextures[0] = &textureView;
    multiStageTextures[1] = &textureView;

    const auto multiStageBindingSet =
        outrun::vr::dx11::observe_fixed_function_texture_binding_set(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures);
    require(
        multiStageBindingSet.inputValid &&
        multiStageBindingSet.requiredMaskValid &&
        multiStageBindingSet.allRequiredBoundExact &&
        multiStageBindingSet.ready &&
        multiStageBindingSet.requiredTextureMask == 0x3u &&
        multiStageBindingSet.observedTextureMask == 0x3u &&
        multiStageBindingSet.stageSnapshotTokens[0] != 0 &&
        multiStageBindingSet.stageSnapshotTokens[1] != 0 &&
        multiStageBindingSet.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_texture_binding_set_readiness_integrity(
                multiStageBindingSet) &&
        outrun::vr::dx11::validate_fixed_function_texture_binding_set_snapshot(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures,
            multiStageBindingSet.snapshotToken),
        "R136 aggregate two-stage PS binding captures exact live identity");

    const auto multiStageTexturedDraw =
        outrun::vr::dx11::
            compose_fixed_function_multistage_textured_draw_readiness(
                multiStageDrawReady, d3d.context,
                multiStageSamplers, multiStageTextures);
    require(
        multiStageTexturedDraw.inputValid &&
        multiStageTexturedDraw.drawReady &&
        multiStageTexturedDraw.textureStageReady &&
        multiStageTexturedDraw.textureMaskMatches &&
        multiStageTexturedDraw.componentSnapshotsPresent &&
        multiStageTexturedDraw.ready &&
        multiStageTexturedDraw.requiredTextureMask == 0x3u &&
        multiStageTexturedDraw.observedTextureMask == 0x3u &&
        multiStageTexturedDraw.drawSnapshotToken ==
            multiStageDrawReady.snapshotToken &&
        multiStageTexturedDraw.textureStageSnapshotToken ==
            multiStageBindingSet.snapshotToken &&
        multiStageTexturedDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_multistage_textured_draw_snapshot(
                multiStageDrawReady, d3d.context,
                multiStageSamplers, multiStageTextures,
                multiStageTexturedDraw.snapshotToken),
        "R136 aggregate two-stage PS binding composes exact draw readiness");

    const auto multiStageBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            multiStageDrawReady, multiStageTexturedDraw,
            drawPipelineBindingReady, d3d.context, outputStateBinding);
    require(
        multiStageBoundDraw.ready &&
        multiStageBoundDraw.pipelineBindingMatchesDraw &&
        multiStageBoundDraw.snapshotToken != 0,
        "R136 aggregate textured draw remains compatible with R134 pipeline identity");

    auto forgedMultiStageBindingSet = multiStageBindingSet;
    forgedMultiStageBindingSet.stageSnapshotTokens[1] ^=
        0x9e3779b97f4a7c15ull;
    require(
        !outrun::vr::dx11::
            validate_fixed_function_texture_binding_set_readiness_integrity(
                forgedMultiStageBindingSet),
        "R136 aggregate binding snapshot rejects copied stage-token drift");

    auto injectedUnusedStageBindingSet = multiStageBindingSet;
    injectedUnusedStageBindingSet.stageSnapshotTokens[2] =
        multiStageBindingSet.stageSnapshotTokens[0];
    require(
        !outrun::vr::dx11::
            validate_fixed_function_texture_binding_set_readiness_integrity(
                injectedUnusedStageBindingSet),
        "R136 aggregate binding snapshot rejects unrequired stage-token injection");

    ID3D11SamplerState* clearSecondStageSampler = nullptr;
    ID3D11ShaderResourceView* clearSecondStageSrv = nullptr;
    d3d.context->PSSetSamplers(
        secondDrawTextureStageSlot, 1, &clearSecondStageSampler);
    d3d.context->PSSetShaderResources(
        secondDrawTextureStageSlot, 1, &clearSecondStageSrv);
    const auto missingSecondStageBindingSet =
        outrun::vr::dx11::observe_fixed_function_texture_binding_set(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures);
    require(
        missingSecondStageBindingSet.inputValid &&
        missingSecondStageBindingSet.requiredMaskValid &&
        !missingSecondStageBindingSet.allRequiredBoundExact &&
        !missingSecondStageBindingSet.ready &&
        missingSecondStageBindingSet.observedTextureMask == 0x1u &&
        missingSecondStageBindingSet.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_texture_binding_set_snapshot(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures,
            multiStageBindingSet.snapshotToken),
        "R136 aggregate binding fails closed after one required PS stage drifts");

    const auto staleLiveMultiStageDraw =
        outrun::vr::dx11::
            compose_fixed_function_multistage_textured_draw_readiness(
                multiStageDrawReady, d3d.context,
                multiStageSamplers, multiStageTextures);
    require(
        !staleLiveMultiStageDraw.textureStageReady &&
        !staleLiveMultiStageDraw.ready &&
        staleLiveMultiStageDraw.observedTextureMask == 0x1u &&
        staleLiveMultiStageDraw.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_multistage_textured_draw_snapshot(
                multiStageDrawReady, d3d.context,
                multiStageSamplers, multiStageTextures,
                multiStageTexturedDraw.snapshotToken),
        "R136 multistage draw reobserves live PS binding drift");

    const auto unsupportedStageMaskBindingSet =
        outrun::vr::dx11::observe_fixed_function_texture_binding_set(
            d3d.context, 0x101u, multiStageSamplers, multiStageTextures);
    require(
        !unsupportedStageMaskBindingSet.requiredMaskValid &&
        !unsupportedStageMaskBindingSet.inputValid &&
        !unsupportedStageMaskBindingSet.ready &&
        unsupportedStageMaskBindingSet.snapshotToken == 0,
        "R136 aggregate binding rejects stages outside fixed-function 0-7");

    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, secondDrawTextureStageSlot, samplerOwner, textureView) &&
        outrun::vr::dx11::validate_fixed_function_texture_binding_set_snapshot(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures,
            multiStageBindingSet.snapshotToken),
        "R136 aggregate live binding restores deterministic snapshot identity");

    const auto boundDrawReady =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding);
    require(
        boundDrawReady.inputValid &&
        boundDrawReady.texturedDrawReady &&
        boundDrawReady.pipelineBindingReady &&
        boundDrawReady.pipelineBindingMatchesDraw &&
        boundDrawReady.outputBindingReady &&
        boundDrawReady.outputBindingMatchesDraw &&
        boundDrawReady.componentSnapshotsPresent &&
        boundDrawReady.ready &&
        boundDrawReady.texturedDrawSnapshotToken ==
            texturedDrawReady.snapshotToken &&
        boundDrawReady.pipelineBindingSnapshotToken ==
            drawPipelineBindingReady.snapshotToken &&
        boundDrawReady.outputBindingSnapshotToken ==
            liveOutputBindingReady.snapshotToken &&
        boundDrawReady.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_bound_draw_snapshot(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding, boundDrawReady.snapshotToken),
        "R138 bound draw reobserves exact live RS OM binding");

    d3d.context->RSSetState(nullptr);
    const auto staleOutputBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding);
    require(
        staleOutputBoundDraw.pipelineBindingReady &&
        staleOutputBoundDraw.pipelineBindingMatchesDraw &&
        !staleOutputBoundDraw.outputBindingReady &&
        staleOutputBoundDraw.outputBindingMatchesDraw &&
        !staleOutputBoundDraw.componentSnapshotsPresent &&
        !staleOutputBoundDraw.ready &&
        staleOutputBoundDraw.outputBindingSnapshotToken == 0 &&
        staleOutputBoundDraw.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_bound_draw_snapshot(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding, boundDrawReady.snapshotToken),
        "R138 bound draw fails closed after live RS drift");
    require(
        outputStateBinding.apply(d3d.context),
        "R138 restore output binding after final draw drift probe");
    const auto restoredOutputBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding);
    require(
        restoredOutputBoundDraw.ready &&
        restoredOutputBoundDraw.outputBindingReady &&
        restoredOutputBoundDraw.outputBindingMatchesDraw &&
        restoredOutputBoundDraw.outputBindingSnapshotToken ==
            liveOutputBindingReady.snapshotToken &&
        restoredOutputBoundDraw.snapshotToken ==
            boundDrawReady.snapshotToken,
        "R138 restored output binding reproduces final bound draw snapshot");


    const auto sameContextBoundDraw =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        sameContextBoundDraw.inputValid &&
        sameContextBoundDraw.texturedDrawReady &&
        sameContextBoundDraw.pipelineBindingReady &&
        sameContextBoundDraw.pipelineBindingMatchesDraw &&
        sameContextBoundDraw.outputBindingReady &&
        sameContextBoundDraw.outputBindingMatchesDraw &&
        sameContextBoundDraw.componentSnapshotsPresent &&
        sameContextBoundDraw.ready &&
        sameContextBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_same_context_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            sameContextBoundDraw.snapshotToken),
        "R139 same-context final bound draw reobserves every live binding");

    d3d.context->PSSetShader(nullptr, nullptr, 0);
    const auto sameContextPipelineDrift =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        sameContextPipelineDrift.texturedDrawReady &&
        !sameContextPipelineDrift.pipelineBindingReady &&
        sameContextPipelineDrift.outputBindingReady &&
        !sameContextPipelineDrift.ready &&
        sameContextPipelineDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_same_context_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            sameContextBoundDraw.snapshotToken),
        "R139 same-context final bound draw rejects live PS pipeline drift");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R139 restore pipeline after same-context drift probe");

    ID3D11SamplerState* clearSameContextSampler = nullptr;
    ID3D11ShaderResourceView* clearSameContextSrv = nullptr;
    d3d.context->PSSetSamplers(
        secondDrawTextureStageSlot, 1, &clearSameContextSampler);
    d3d.context->PSSetShaderResources(
        secondDrawTextureStageSlot, 1, &clearSameContextSrv);
    const auto sameContextTextureDrift =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        !sameContextTextureDrift.texturedDrawReady &&
        sameContextTextureDrift.pipelineBindingReady &&
        sameContextTextureDrift.outputBindingReady &&
        !sameContextTextureDrift.ready &&
        sameContextTextureDrift.snapshotToken == 0,
        "R139 same-context final bound draw rejects live aggregate PS drift");
    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, secondDrawTextureStageSlot, samplerOwner, textureView),
        "R139 restore aggregate PS stage after same-context drift probe");

    d3d.context->RSSetState(nullptr);
    const auto sameContextOutputDrift =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        sameContextOutputDrift.texturedDrawReady &&
        sameContextOutputDrift.pipelineBindingReady &&
        !sameContextOutputDrift.outputBindingReady &&
        !sameContextOutputDrift.ready &&
        sameContextOutputDrift.snapshotToken == 0,
        "R139 same-context final bound draw rejects live RS OM drift");
    require(
        outputStateBinding.apply(d3d.context),
        "R139 restore RS OM after same-context drift probe");

    const auto sameContextRestored =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        sameContextRestored.ready &&
        sameContextRestored.snapshotToken == sameContextBoundDraw.snapshotToken,
        "R139 same-context final bound draw restores deterministic snapshot");

    const auto completeBoundDraw =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeBoundDraw.inputValid &&
        completeBoundDraw.sameContextBoundDrawReady &&
        completeBoundDraw.geometryBindingReady &&
        completeBoundDraw.geometryBindingMatchesDraw &&
        completeBoundDraw.componentSnapshotsPresent &&
        completeBoundDraw.ready &&
        completeBoundDraw.sameContextBoundDrawSnapshotToken ==
            sameContextBoundDraw.snapshotToken &&
        completeBoundDraw.geometryBindingSnapshotToken ==
            indexedGeometryBinding.snapshotToken &&
        completeBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 complete bound draw includes exact live IA geometry");

    d3d.context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    const auto completeGeometryDrift =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeGeometryDrift.sameContextBoundDrawReady &&
        !completeGeometryDrift.geometryBindingReady &&
        completeGeometryDrift.geometryBindingMatchesDraw &&
        !completeGeometryDrift.componentSnapshotsPresent &&
        !completeGeometryDrift.ready &&
        completeGeometryDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 final gate fails closed after live IA topology drift");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R140 restore IA geometry after final gate drift probe");
    const auto completeBoundDrawRestored =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeBoundDrawRestored.ready &&
        completeBoundDrawRestored.geometryBindingReady &&
        completeBoundDrawRestored.geometryBindingMatchesDraw &&
        completeBoundDrawRestored.snapshotToken == completeBoundDraw.snapshotToken,
        "R140 restored IA geometry reproduces complete bound draw snapshot");

    ID3D11Buffer* strideDriftVertex =
        managedVertexBuffer.mirror_buffer();
    const UINT strideDriftValue = geometryVertexStride + 4u;
    d3d.context->IASetVertexBuffers(
        0, 1, &strideDriftVertex, &strideDriftValue, &geometryVertexOffset);
    const auto completeStrideDrift =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeStrideDrift.sameContextBoundDrawReady &&
        !completeStrideDrift.geometryBindingReady &&
        completeStrideDrift.geometryBindingMatchesDraw &&
        !completeStrideDrift.componentSnapshotsPresent &&
        !completeStrideDrift.ready &&
        completeStrideDrift.geometryBindingSnapshotToken == 0 &&
        completeStrideDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 complete bound draw rejects live IA vertex stride drift");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R140 restore IA after vertex stride drift");

    d3d.context->IASetIndexBuffer(
        managedIndexBuffer.mirror_buffer(), DXGI_FORMAT_R16_UINT,
        geometryIndexOffset + 2u);
    const auto completeIndexOffsetDrift =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeIndexOffsetDrift.sameContextBoundDrawReady &&
        !completeIndexOffsetDrift.geometryBindingReady &&
        completeIndexOffsetDrift.geometryBindingMatchesDraw &&
        !completeIndexOffsetDrift.componentSnapshotsPresent &&
        !completeIndexOffsetDrift.ready &&
        completeIndexOffsetDrift.geometryBindingSnapshotToken == 0 &&
        completeIndexOffsetDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 complete bound draw rejects live IA index offset drift");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset) &&
        outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 complete bound draw restores exact IA binding parameters");


    {
        const auto fullyBoundDraw =
            outrun::vr::dx11::compose_fixed_function_fully_bound_draw_readiness(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform);
        require(
            fullyBoundDraw.inputValid &&
            fullyBoundDraw.completeBoundDrawReady &&
            fullyBoundDraw.transformBindingReady &&
            fullyBoundDraw.componentSnapshotsPresent &&
            fullyBoundDraw.ready &&
            fullyBoundDraw.transformBindingSnapshotToken ==
                pipelineTransformBindingReady.snapshotToken &&
            fullyBoundDraw.transformPayloadHash == transform.payloadHash &&
            fullyBoundDraw.snapshotToken != 0 &&
            outrun::vr::dx11::validate_fixed_function_fully_bound_draw_snapshot(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform, fullyBoundDraw.snapshotToken),
            "final fully bound draw includes exact live VS b0 transform");

        ID3D11Buffer* nullFinalTransformBuffer = nullptr;
        d3d.context->VSSetConstantBuffers(0, 1, &nullFinalTransformBuffer);
        const auto missingTransformBinding =
            outrun::vr::dx11::compose_fixed_function_fully_bound_draw_readiness(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform);
        require(
            missingTransformBinding.completeBoundDrawReady &&
            !missingTransformBinding.transformBindingReady &&
            !missingTransformBinding.ready &&
            missingTransformBinding.snapshotToken == 0 &&
            !outrun::vr::dx11::validate_fixed_function_fully_bound_draw_snapshot(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform, fullyBoundDraw.snapshotToken),
            "final fully bound draw fails closed after VS b0 drift");

        ID3D11Buffer* restoredFinalTransformBuffer =
            pipelineBundle.transform_buffer().buffer();
        d3d.context->VSSetConstantBuffers(0, 1, &restoredFinalTransformBuffer);
        const auto fullyBoundDrawRestored =
            outrun::vr::dx11::compose_fixed_function_fully_bound_draw_readiness(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform);
        require(
            fullyBoundDrawRestored.ready &&
            fullyBoundDrawRestored.snapshotToken == fullyBoundDraw.snapshotToken,
            "final VS b0 restore reproduces fully bound draw snapshot");

        auto transformPayloadDrift = transform;
        transformPayloadDrift.worldViewProjection[0] += 1.0f;
        const auto copiedPayloadDrift =
            pipelineBundle.transform_buffer().binding_readiness(
                d3d.context, transformPayloadDrift);
        require(
            !copiedPayloadDrift.inputValid &&
            !copiedPayloadDrift.payloadMatches &&
            !copiedPayloadDrift.ready &&
            copiedPayloadDrift.snapshotToken == 0,
            "final VS b0 copied WVP payload drift fails closed");

        const auto renderTargetBoundDraw =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface);
        require(
            renderTargetBoundDraw.inputValid &&
            renderTargetBoundDraw.fullyBoundDrawReady &&
            renderTargetBoundDraw.surfaceTargetBindingReady &&
            renderTargetBoundDraw.surfacePairMatchesDraw &&
            renderTargetBoundDraw.geometryRangeMetadataExact &&
            renderTargetBoundDraw.vertexStrideMatchesInputLayout &&
            renderTargetBoundDraw.vertexStride == geometryVertexStride &&
            renderTargetBoundDraw.inputLayoutStream0Stride ==
                inputLayout.stream0Stride &&
            renderTargetBoundDraw.vertexOffset == geometryVertexOffset &&
            renderTargetBoundDraw.vertexBufferByteWidth == managedVertexBytes.size() &&
            renderTargetBoundDraw.indexFormat == DXGI_FORMAT_R16_UINT &&
            renderTargetBoundDraw.indexOffset == geometryIndexOffset &&
            renderTargetBoundDraw.indexBufferByteWidth == sizeof(managedIndexBytes) &&
            renderTargetBoundDraw.componentSnapshotsPresent &&
            renderTargetBoundDraw.ready &&
            renderTargetBoundDraw.surfaceTargetBindingSnapshotToken ==
                surfaceTargetBindingReady.snapshotToken &&
            renderTargetBoundDraw.surfacePairSnapshotToken ==
                surfacePairReady.snapshotToken &&
            renderTargetBoundDraw.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_render_target_bound_draw_snapshot(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface,
                    renderTargetBoundDraw.snapshotToken),
            "R145 final draw seals exact live OM RTV DSV identity");

        constexpr UINT mismatchedLayoutStride = 16u;
        require(
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, indexedGeometryReady, managedVertexBuffer,
                mismatchedLayoutStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
            "R158 mismatched IA stride binding prerequisite");
        const auto layoutStrideMismatch =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    mismatchedLayoutStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface);
        require(
            layoutStrideMismatch.inputValid &&
            layoutStrideMismatch.fullyBoundDrawReady &&
            layoutStrideMismatch.surfaceTargetBindingReady &&
            layoutStrideMismatch.geometryRangeMetadataExact &&
            !layoutStrideMismatch.vertexStrideMatchesInputLayout &&
            layoutStrideMismatch.vertexStride == mismatchedLayoutStride &&
            layoutStrideMismatch.inputLayoutStream0Stride ==
                inputLayout.stream0Stride &&
            !layoutStrideMismatch.ready &&
            layoutStrideMismatch.snapshotToken == 0,
            "R158 final draw rejects live IA stride drift from translated layout");
        require(
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset) &&
            outrun::vr::dx11::
                validate_fixed_function_render_target_bound_draw_snapshot(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface,
                    renderTargetBoundDraw.snapshotToken),
            "R158 exact IA stride restore keeps final draw snapshot deterministic");

        d3d.context->OMSetRenderTargets(0, nullptr, nullptr);
        const auto missingRenderTargets =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface);
        require(
            missingRenderTargets.fullyBoundDrawReady &&
            !missingRenderTargets.surfaceTargetBindingReady &&
            missingRenderTargets.surfacePairMatchesDraw &&
            !missingRenderTargets.ready &&
            missingRenderTargets.snapshotToken == 0 &&
            !outrun::vr::dx11::
                validate_fixed_function_render_target_bound_draw_snapshot(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface,
                    renderTargetBoundDraw.snapshotToken),
            "R145 final draw fails closed after live OM target unbind");

        require(
            surfaceTargetBinding.apply(
                d3d.context, outputColorSurface, outputDepthSurface) &&
            outrun::vr::dx11::
                validate_fixed_function_render_target_bound_draw_snapshot(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface,
                    renderTargetBoundDraw.snapshotToken),
            "R145 live OM target restore reproduces final draw snapshot");

        const auto indexedDirectDispatch =
            outrun::vr::dx11::
                compose_fixed_function_direct_draw_dispatch_readiness(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLELIST, 2u, true,
                    0u, 0u, 0);
        require(
            indexedDirectDispatch.inputValid &&
            indexedDirectDispatch.renderTargetBoundDrawReady &&
            indexedDirectDispatch.geometryReady &&
            indexedDirectDispatch.geometryMatchesDraw &&
            indexedDirectDispatch.surfacePairMatchesDraw &&
            indexedDirectDispatch.topologyMatchesGeometry &&
            indexedDirectDispatch.bufferRangeExact &&
            indexedDirectDispatch.dispatchArgumentsExact &&
            indexedDirectDispatch.componentSnapshotsPresent &&
            indexedDirectDispatch.ready &&
            indexedDirectDispatch.indexed &&
            indexedDirectDispatch.elementCount == 6u &&
            indexedDirectDispatch.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_direct_draw_dispatch_snapshot(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLELIST, 2u, true,
                    0u, 0u, 0, indexedDirectDispatch.snapshotToken),
            "R147 direct indexed dispatch seals DrawIndexed arguments");

        const auto indexedSourceRange =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 4u, 0u);
        require(
            indexedSourceRange.inputValid &&
            indexedSourceRange.primitiveExact &&
            indexedSourceRange.vertexRangeExact &&
            indexedSourceRange.indexRangeExact &&
            indexedSourceRange.ready &&
            indexedSourceRange.topology ==
                D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
            indexedSourceRange.primitiveCount == 2u &&
            indexedSourceRange.elementCount == 6u &&
            indexedSourceRange.baseVertexIndex == 0 &&
            indexedSourceRange.minVertexIndex == 0u &&
            indexedSourceRange.numVertices == 4u &&
            indexedSourceRange.maxVertexIndex == 3u &&
            indexedSourceRange.startIndex == 0u &&
            indexedSourceRange.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_source_range_snapshot(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 4u, 0u,
                    indexedSourceRange.snapshotToken),
            "R149 indexed source range seals D3D9 DrawIndexedPrimitive arguments");

        const auto indexedSourceRangeMissingVertices =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 0u, 0u);
        require(
            indexedSourceRangeMissingVertices.inputValid &&
            indexedSourceRangeMissingVertices.primitiveExact &&
            !indexedSourceRangeMissingVertices.vertexRangeExact &&
            indexedSourceRangeMissingVertices.indexRangeExact &&
            !indexedSourceRangeMissingVertices.ready &&
            indexedSourceRangeMissingVertices.snapshotToken == 0,
            "R149 indexed source range rejects empty vertex range for live primitives");

        const auto indexedSourceRangeVertexOverflow =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 1u, 0,
                    std::numeric_limits<UINT>::max(), 2u, 0u);
        require(
            indexedSourceRangeVertexOverflow.inputValid &&
            !indexedSourceRangeVertexOverflow.vertexRangeExact &&
            indexedSourceRangeVertexOverflow.indexRangeExact &&
            !indexedSourceRangeVertexOverflow.ready &&
            indexedSourceRangeVertexOverflow.snapshotToken == 0,
            "R149 indexed source range rejects MinVertexIndex NumVertices overflow");

        const auto indexedSourceRangeNegativeEffectiveVertex =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 1u, -2, 1u, 3u, 0u);
        require(
            indexedSourceRangeNegativeEffectiveVertex.inputValid &&
            !indexedSourceRangeNegativeEffectiveVertex.vertexRangeExact &&
            indexedSourceRangeNegativeEffectiveVertex.indexRangeExact &&
            !indexedSourceRangeNegativeEffectiveVertex.ready &&
            indexedSourceRangeNegativeEffectiveVertex.snapshotToken == 0,
            "R149 indexed source range rejects negative effective BaseVertexIndex range");

        const auto indexedSourceRangeEffectiveVertexOverflow =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 1u, 1,
                    std::numeric_limits<UINT>::max(), 1u, 0u);
        require(
            indexedSourceRangeEffectiveVertexOverflow.inputValid &&
            !indexedSourceRangeEffectiveVertexOverflow.vertexRangeExact &&
            indexedSourceRangeEffectiveVertexOverflow.indexRangeExact &&
            !indexedSourceRangeEffectiveVertexOverflow.ready &&
            indexedSourceRangeEffectiveVertexOverflow.snapshotToken == 0,
            "R149 indexed source range rejects effective BaseVertexIndex maximum overflow");

        const auto indexedSourceRangeNegativeBaseValid =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 1u, -2, 2u, 3u, 0u);
        require(
            indexedSourceRangeNegativeBaseValid.vertexRangeExact &&
            indexedSourceRangeNegativeBaseValid.ready &&
            indexedSourceRangeNegativeBaseValid.snapshotToken != 0,
            "R149 indexed source range accepts bounded negative BaseVertexIndex");

        const auto indexedSourceRangeIndexOverflow =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 4u,
                    std::numeric_limits<UINT>::max() - 5u);
        require(
            indexedSourceRangeIndexOverflow.inputValid &&
            indexedSourceRangeIndexOverflow.vertexRangeExact &&
            !indexedSourceRangeIndexOverflow.indexRangeExact &&
            !indexedSourceRangeIndexOverflow.ready &&
            indexedSourceRangeIndexOverflow.snapshotToken == 0,
            "R149 indexed source range rejects StartIndex element-count overflow");

        const auto indexedSourceRangeFan =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLEFAN, 2u, 0, 0u, 4u, 0u);
        require(
            !indexedSourceRangeFan.inputValid &&
            !indexedSourceRangeFan.primitiveExact &&
            !indexedSourceRangeFan.ready &&
            indexedSourceRangeFan.snapshotToken == 0,
            "R149 indexed source range keeps triangle fan on generated-index path");

        const auto indexedSourceRangePointList =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_POINTLIST, 1u, 0, 0u, 1u, 0u);
        require(
            !indexedSourceRangePointList.inputValid &&
            !indexedSourceRangePointList.primitiveExact &&
            indexedSourceRangePointList.vertexRangeExact &&
            indexedSourceRangePointList.indexRangeExact &&
            !indexedSourceRangePointList.ready &&
            indexedSourceRangePointList.snapshotToken == 0,
            "R149 indexed source range rejects D3D9 DIP point list");

        require(
            !outrun::vr::dx11::
                validate_fixed_function_indexed_source_range_snapshot(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 3u, 0u,
                    indexedSourceRange.snapshotToken),
            "R149 indexed source range snapshot rejects NumVertices drift");

        const auto indexedDirectLineage =
            outrun::vr::dx11::
                compose_fixed_function_indexed_direct_dispatch_readiness(
                    indexedDirectDispatch, indexedSourceRange,
                    renderTargetBoundDraw);
        require(
            indexedDirectLineage.inputValid &&
            indexedDirectLineage.directDispatchReady &&
            indexedDirectLineage.sourceRangeReady &&
            indexedDirectLineage.boundDrawReady &&
            indexedDirectLineage.dispatchMatchesSourceRange &&
            indexedDirectLineage.boundDrawMatchesDispatch &&
            indexedDirectLineage.vertexBufferRangeExact &&
            indexedDirectLineage.componentSnapshotsPresent &&
            indexedDirectLineage.ready &&
            indexedDirectLineage.directDispatchSnapshotToken ==
                indexedDirectDispatch.snapshotToken &&
            indexedDirectLineage.sourceRangeSnapshotToken ==
                indexedSourceRange.snapshotToken &&
            indexedDirectLineage.boundDrawSnapshotToken ==
                renderTargetBoundDraw.snapshotToken &&
            indexedDirectLineage.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_direct_dispatch_snapshot(
                    indexedDirectDispatch, indexedSourceRange,
                    renderTargetBoundDraw, indexedDirectLineage.snapshotToken),
            "R150 indexed direct dispatch binds R147 tuple to R149 source range");

        const auto indexedSourceRangeStartDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 4u, 1u);
        const auto indexedDirectLineageDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_direct_dispatch_readiness(
                    indexedDirectDispatch, indexedSourceRangeStartDrift,
                    renderTargetBoundDraw);
        require(
            indexedSourceRangeStartDrift.ready &&
            indexedDirectLineageDrift.inputValid &&
            indexedDirectLineageDrift.directDispatchReady &&
            indexedDirectLineageDrift.sourceRangeReady &&
            !indexedDirectLineageDrift.dispatchMatchesSourceRange &&
            !indexedDirectLineageDrift.ready &&
            indexedDirectLineageDrift.snapshotToken == 0 &&
            !outrun::vr::dx11::
                validate_fixed_function_indexed_direct_dispatch_snapshot(
                    indexedDirectDispatch, indexedSourceRangeStartDrift,
                    renderTargetBoundDraw, indexedDirectLineage.snapshotToken),
            "R150 indexed direct dispatch rejects R149 StartIndex lineage drift");

        const auto indexedSourceRangeBufferOverrun =
            outrun::vr::dx11::compose_fixed_function_indexed_source_range_readiness(
                D3DPT_TRIANGLELIST, 2u, 0, 14u, 3u, 0u);
        const auto indexedVertexBufferOverrun =
            outrun::vr::dx11::compose_fixed_function_indexed_direct_dispatch_readiness(
                indexedDirectDispatch, indexedSourceRangeBufferOverrun,
                renderTargetBoundDraw);
        require(
            indexedSourceRangeBufferOverrun.ready &&
            indexedVertexBufferOverrun.inputValid &&
            indexedVertexBufferOverrun.dispatchMatchesSourceRange &&
            indexedVertexBufferOverrun.boundDrawMatchesDispatch &&
            !indexedVertexBufferOverrun.vertexBufferRangeExact &&
            !indexedVertexBufferOverrun.ready &&
            indexedVertexBufferOverrun.snapshotToken == 0,
            "R151 indexed direct lineage rejects declared vertex buffer overrun");

        const auto indexedIndexBufferOverrun =
            outrun::vr::dx11::compose_fixed_function_direct_draw_dispatch_readiness(
                renderTargetBoundDraw, multiStageDrawReady,
                indexedGeometryReady, D3DPT_TRIANGLELIST, 2u, true,
                0u, 1u, 0);
        require(
            indexedIndexBufferOverrun.inputValid &&
            !indexedIndexBufferOverrun.bufferRangeExact &&
            !indexedIndexBufferOverrun.dispatchArgumentsExact &&
            !indexedIndexBufferOverrun.ready &&
            indexedIndexBufferOverrun.snapshotToken == 0,
            "R151 direct indexed dispatch rejects index buffer overrun");

        const auto indexedSourceValues =
            managedIndexBuffer.index_range_readiness(
                managedIndexReady, D3DFMT_INDEX16,
                indexedSourceRange.startIndex,
                indexedSourceRange.elementCount,
                indexedSourceRange.minVertexIndex,
                indexedSourceRange.maxVertexIndex);
        require(
            indexedSourceValues.inputValid &&
            indexedSourceValues.shadowValid &&
            indexedSourceValues.indexFormatExact &&
            indexedSourceValues.mirrorSnapshotExact &&
            indexedSourceValues.byteRangeExact &&
            indexedSourceValues.valuesWithinDeclaredRange &&
            indexedSourceValues.ready &&
            indexedSourceValues.startIndex == 0u &&
            indexedSourceValues.indexCount == 6u &&
            indexedSourceValues.observedMinIndex == 0u &&
            indexedSourceValues.observedMaxIndex == 3u &&
            indexedSourceValues.mirrorSnapshotToken ==
                managedIndexReady.snapshotToken &&
            indexedSourceValues.contentHash != 0 &&
            indexedSourceValues.snapshotToken != 0 &&
            managedIndexBuffer.validate_index_range_readiness_snapshot(
                managedIndexReady, D3DFMT_INDEX16, 0u, 6u, 0u, 3u,
                indexedSourceValues.snapshotToken),
            "R152 indexed source values scan exact managed IB range");

        const auto indexedSourceValueLineage =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_value_readiness(
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues);
        require(
            indexedSourceValueLineage.inputValid &&
            indexedSourceValueLineage.directDispatchReady &&
            indexedSourceValueLineage.indexedLineageReady &&
            indexedSourceValueLineage.sourceRangeReady &&
            indexedSourceValueLineage.geometryReady &&
            indexedSourceValueLineage.sourceValuesReady &&
            indexedSourceValueLineage.dispatchMatchesLineage &&
            indexedSourceValueLineage.geometryMatchesSourceValues &&
            indexedSourceValueLineage.sourceValuesMatchRange &&
            indexedSourceValueLineage.componentSnapshotsPresent &&
            indexedSourceValueLineage.ready &&
            indexedSourceValueLineage.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_source_value_snapshot(
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues,
                    indexedSourceValueLineage.snapshotToken),
            "R152 indexed source values bind exact IB contents to R150 lineage");

        const auto indexedSourceBinding =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_binding_readiness(
                    indexedSourceValueLineage, indexedDirectDispatch,
                    indexedDirectLineage, indexedSourceRange,
                    indexedGeometryReady, indexedSourceValues,
                    renderTargetBoundDraw);
        require(
            indexedSourceBinding.inputValid &&
            indexedSourceBinding.sourceValueLineageReady &&
            indexedSourceBinding.boundDrawReady &&
            indexedSourceBinding.boundDrawMatchesLineage &&
            indexedSourceBinding.indexFormatMatchesSourceValues &&
            indexedSourceBinding.indexOffsetExact &&
            indexedSourceBinding.componentSnapshotsPresent &&
            indexedSourceBinding.ready &&
            indexedSourceBinding.sourceIndexFormat == D3DFMT_INDEX16 &&
            indexedSourceBinding.boundIndexFormat == DXGI_FORMAT_R16_UINT &&
            indexedSourceBinding.boundIndexOffset == 0u &&
            indexedSourceBinding.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_source_binding_snapshot(
                    indexedSourceValueLineage, indexedDirectDispatch,
                    indexedDirectLineage, indexedSourceRange,
                    indexedGeometryReady, indexedSourceValues,
                    renderTargetBoundDraw, indexedSourceBinding.snapshotToken),
            "R153 indexed source binding seals live IA format and offset");

        auto indexedSourceValuesFormatDrift = indexedSourceValues;
        indexedSourceValuesFormatDrift.sourceIndexFormat = D3DFMT_INDEX32;
        const auto indexedSourceValueLineageFormatDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_value_readiness(
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValuesFormatDrift);
        const auto indexedSourceBindingFormatDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_binding_readiness(
                    indexedSourceValueLineageFormatDrift,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValuesFormatDrift, renderTargetBoundDraw);
        require(
            indexedSourceValueLineageFormatDrift.ready &&
            indexedSourceBindingFormatDrift.inputValid &&
            indexedSourceBindingFormatDrift.sourceValueLineageReady &&
            indexedSourceBindingFormatDrift.boundDrawReady &&
            !indexedSourceBindingFormatDrift.indexFormatMatchesSourceValues &&
            indexedSourceBindingFormatDrift.indexOffsetExact &&
            !indexedSourceBindingFormatDrift.ready &&
            indexedSourceBindingFormatDrift.snapshotToken == 0,
            "R153 indexed source binding rejects source format drift");

        auto indexedBoundDrawOffsetDrift = renderTargetBoundDraw;
        indexedBoundDrawOffsetDrift.indexOffset = 2u;
        const auto indexedSourceBindingOffsetDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_binding_readiness(
                    indexedSourceValueLineage, indexedDirectDispatch,
                    indexedDirectLineage, indexedSourceRange,
                    indexedGeometryReady, indexedSourceValues,
                    indexedBoundDrawOffsetDrift);
        require(
            indexedSourceBindingOffsetDrift.inputValid &&
            indexedSourceBindingOffsetDrift.sourceValueLineageReady &&
            !indexedSourceBindingOffsetDrift.boundDrawReady &&
            indexedSourceBindingOffsetDrift.boundDrawMatchesLineage &&
            indexedSourceBindingOffsetDrift.indexFormatMatchesSourceValues &&
            !indexedSourceBindingOffsetDrift.indexOffsetExact &&
            !indexedSourceBindingOffsetDrift.ready &&
            indexedSourceBindingOffsetDrift.snapshotToken == 0 &&
            !outrun::vr::dx11::
                validate_fixed_function_indexed_source_binding_snapshot(
                    indexedSourceValueLineage, indexedDirectDispatch,
                    indexedDirectLineage, indexedSourceRange,
                    indexedGeometryReady, indexedSourceValues,
                    indexedBoundDrawOffsetDrift,
                    indexedSourceBinding.snapshotToken),
            "R153 indexed source binding rejects live IA index offset drift");


        const auto indexedSourceLiveBinding =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_live_binding_readiness(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer);
        require(
            indexedSourceLiveBinding.inputValid &&
            indexedSourceLiveBinding.sourceBindingReady &&
            indexedSourceLiveBinding.contextMatchesMirror &&
            indexedSourceLiveBinding.indexMirrorCurrent &&
            indexedSourceLiveBinding.liveIndexBufferExact &&
            indexedSourceLiveBinding.liveIndexFormatExact &&
            indexedSourceLiveBinding.liveIndexOffsetExact &&
            indexedSourceLiveBinding.componentSnapshotsPresent &&
            indexedSourceLiveBinding.ready &&
            indexedSourceLiveBinding.observedIndexFormat ==
                DXGI_FORMAT_R16_UINT &&
            indexedSourceLiveBinding.observedIndexOffset == 0u &&
            indexedSourceLiveBinding.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_source_live_binding_snapshot(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer,
                    indexedSourceLiveBinding.snapshotToken),
            "R153 live source binding reobserves current IA index mirror");

        d3d.context->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0u);
        const auto indexedSourceLiveBindingDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_live_binding_readiness(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer);
        require(
            indexedSourceLiveBindingDrift.inputValid &&
            indexedSourceLiveBindingDrift.sourceBindingReady &&
            indexedSourceLiveBindingDrift.contextMatchesMirror &&
            indexedSourceLiveBindingDrift.indexMirrorCurrent &&
            !indexedSourceLiveBindingDrift.liveIndexBufferExact &&
            !indexedSourceLiveBindingDrift.ready &&
            indexedSourceLiveBindingDrift.snapshotToken == 0 &&
            !outrun::vr::dx11::
                validate_fixed_function_indexed_source_live_binding_snapshot(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer,
                    indexedSourceLiveBinding.snapshotToken),
            "R153 live source binding rejects post-snapshot IA index drift");

        d3d.context->IASetIndexBuffer(
            managedIndexBuffer.mirror_buffer(), DXGI_FORMAT_R16_UINT, 0u);
        const auto indexedSourceLiveBindingRestored =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_live_binding_readiness(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer);
        require(
            indexedSourceLiveBindingRestored.ready &&
            indexedSourceLiveBindingRestored.liveIndexBufferExact &&
            indexedSourceLiveBindingRestored.liveIndexFormatExact &&
            indexedSourceLiveBindingRestored.liveIndexOffsetExact &&
            indexedSourceLiveBindingRestored.snapshotToken ==
                indexedSourceLiveBinding.snapshotToken,
            "R153 live source binding restores deterministic IA identity");

        const auto indexedSourceValuesOutOfRange =
            managedIndexBuffer.index_range_readiness(
                managedIndexReady, D3DFMT_INDEX16, 0u, 6u, 1u, 3u);
        require(
            indexedSourceValuesOutOfRange.inputValid &&
            indexedSourceValuesOutOfRange.byteRangeExact &&
            !indexedSourceValuesOutOfRange.valuesWithinDeclaredRange &&
            !indexedSourceValuesOutOfRange.ready &&
            indexedSourceValuesOutOfRange.snapshotToken == 0,
            "R152 indexed source values reject index outside declared vertex range");

        auto forgedManagedIndexReady = managedIndexReady;
        forgedManagedIndexReady.snapshotToken ^= 1u;
        const auto indexedSourceValuesForgedMirror =
            managedIndexBuffer.index_range_readiness(
                forgedManagedIndexReady, D3DFMT_INDEX16, 0u, 6u, 0u, 3u);
        require(
            indexedSourceValuesForgedMirror.inputValid &&
            !indexedSourceValuesForgedMirror.mirrorSnapshotExact &&
            !indexedSourceValuesForgedMirror.ready &&
            indexedSourceValuesForgedMirror.snapshotToken == 0,
            "R152 indexed source values reject forged managed IB snapshot");

        auto forgedIndexedGeometry = indexedGeometryReady;
        forgedIndexedGeometry.indexBufferSnapshotToken ^= 1u;
        const auto indexedSourceValueGeometryDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_value_readiness(
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, forgedIndexedGeometry,
                    indexedSourceValues);
        require(
            indexedSourceValueGeometryDrift.inputValid &&
            !indexedSourceValueGeometryDrift.geometryMatchesSourceValues &&
            !indexedSourceValueGeometryDrift.ready &&
            indexedSourceValueGeometryDrift.snapshotToken == 0,
            "R152 indexed source values reject geometry IB identity drift");

        require(
            !outrun::vr::dx11::
                validate_fixed_function_direct_draw_dispatch_snapshot(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLELIST, 2u, true,
                    0u, 1u, 0, indexedDirectDispatch.snapshotToken),
            "R147 direct indexed dispatch snapshot rejects StartIndexLocation drift");

        const auto directFanDispatch =
            outrun::vr::dx11::
                compose_fixed_function_direct_draw_dispatch_readiness(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLEFAN, 2u, true,
                    0u, 0u, 0);
        require(
            !directFanDispatch.topologyMatchesGeometry &&
            !directFanDispatch.dispatchArgumentsExact &&
            !directFanDispatch.ready &&
            directFanDispatch.snapshotToken == 0,
            "R147 direct dispatch keeps triangle fan fail closed");

        const auto overflowDirectDispatch =
            outrun::vr::dx11::
                compose_fixed_function_direct_draw_dispatch_readiness(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLELIST,
                    std::numeric_limits<UINT>::max(), true, 0u, 0u, 0);
        require(
            !overflowDirectDispatch.dispatchArgumentsExact &&
            !overflowDirectDispatch.ready &&
            overflowDirectDispatch.snapshotToken == 0,
            "R147 direct dispatch rejects element-count overflow");

        require(
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, nonIndexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                nullptr, DXGI_FORMAT_UNKNOWN, 0),
            "R147 nonindexed direct IA prerequisite");
        const auto nonIndexedDirectDrawReady =
            compose_fixed_function_draw_readiness(
                multiStageActivation, outputBindingRenderReady, surfacePairReady,
                outputStateReady, outputStateBinding, nonIndexedGeometryReady);
        require(
            nonIndexedDirectDrawReady.ready,
            "R147 nonindexed direct sealed draw prerequisite");
        const auto nonIndexedRenderTargetBoundDraw =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    nonIndexedDirectDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    nonIndexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    nullptr, DXGI_FORMAT_UNKNOWN, 0u, transform,
                    surfaceTargetBinding, outputColorSurface, outputDepthSurface);
        require(
            nonIndexedRenderTargetBoundDraw.ready,
            "R147 nonindexed final bound-state prerequisite");

        const auto nonIndexedDirectDispatch =
            outrun::vr::dx11::
                compose_fixed_function_direct_draw_dispatch_readiness(
                    nonIndexedRenderTargetBoundDraw, nonIndexedDirectDrawReady,
                    nonIndexedGeometryReady, D3DPT_TRIANGLESTRIP, 2u, false,
                    1u, 0u, 0);
        require(
            nonIndexedDirectDispatch.ready &&
            !nonIndexedDirectDispatch.indexed &&
            nonIndexedDirectDispatch.bufferRangeExact &&
            nonIndexedDirectDispatch.elementCount == 4u &&
            nonIndexedDirectDispatch.startVertexLocation == 1u &&
            nonIndexedDirectDispatch.startIndexLocation == 0u &&
            nonIndexedDirectDispatch.baseVertexLocation == 0 &&
            nonIndexedDirectDispatch.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_direct_draw_dispatch_snapshot(
                    nonIndexedRenderTargetBoundDraw, nonIndexedDirectDrawReady,
                    nonIndexedGeometryReady, D3DPT_TRIANGLESTRIP, 2u, false,
                    1u, 0u, 0, nonIndexedDirectDispatch.snapshotToken),
            "R147 direct nonindexed dispatch seals Draw start vertex");
        require(
            !outrun::vr::dx11::
                validate_fixed_function_direct_draw_dispatch_snapshot(
                    nonIndexedRenderTargetBoundDraw, nonIndexedDirectDrawReady,
                    nonIndexedGeometryReady, D3DPT_TRIANGLESTRIP, 2u, false,
                    2u, 0u, 0, nonIndexedDirectDispatch.snapshotToken),
            "R147 direct nonindexed dispatch snapshot rejects StartVertexLocation drift");

        const auto nonIndexedVertexBufferOverrun =
            outrun::vr::dx11::compose_fixed_function_direct_draw_dispatch_readiness(
                nonIndexedRenderTargetBoundDraw, nonIndexedDirectDrawReady,
                nonIndexedGeometryReady, D3DPT_TRIANGLESTRIP, 2u, false,
                14u, 0u, 0);
        require(
            nonIndexedVertexBufferOverrun.inputValid &&
            !nonIndexedVertexBufferOverrun.bufferRangeExact &&
            !nonIndexedVertexBufferOverrun.dispatchArgumentsExact &&
            !nonIndexedVertexBufferOverrun.ready &&
            nonIndexedVertexBufferOverrun.snapshotToken == 0,
            "R151 direct nonindexed dispatch rejects vertex buffer overrun");

        const auto pointListGeometryReady =
            outrun::vr::dx11::compose_fixed_function_geometry_readiness(
                managedVertexPostResetReady, false, managedIndexReady,
                D3DPT_POINTLIST);
        require(
            pointListGeometryReady.ready &&
            pointListGeometryReady.topology ==
                D3D11_PRIMITIVE_TOPOLOGY_POINTLIST &&
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, pointListGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                nullptr, DXGI_FORMAT_UNKNOWN, 0u),
            "R155 point-list fixture reaches exact dormant IA topology");

        const auto pointListDrawReady =
            compose_fixed_function_draw_readiness(
                multiStageActivation, outputBindingRenderReady, surfacePairReady,
                outputStateReady, outputStateBinding, pointListGeometryReady);
        const auto pointListRenderTargetBoundDraw =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    pointListDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    pointListGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    nullptr, DXGI_FORMAT_UNKNOWN, 0u, transform,
                    surfaceTargetBinding, outputColorSurface, outputDepthSurface);
        const auto pointListDirectDispatch =
            outrun::vr::dx11::compose_fixed_function_direct_draw_dispatch_readiness(
                pointListRenderTargetBoundDraw, pointListDrawReady,
                pointListGeometryReady, D3DPT_POINTLIST, 1u, false,
                0u, 0u, 0);
        require(
            pointListRenderTargetBoundDraw.ready &&
            pointListDirectDispatch.inputValid &&
            pointListDirectDispatch.renderTargetBoundDrawReady &&
            pointListDirectDispatch.geometryReady &&
            pointListDirectDispatch.geometryMatchesDraw &&
            pointListDirectDispatch.topologyMatchesGeometry &&
            pointListDirectDispatch.bufferRangeExact &&
            pointListDirectDispatch.dispatchArgumentsExact &&
            !pointListDirectDispatch.pointRasterSemanticsExact &&
            !pointListDirectDispatch.ready &&
            pointListDirectDispatch.snapshotToken == 0,
            "R155 direct point-list raster semantics remain fail closed");

        const std::array<D3DPRIMITIVETYPE, 2> directLinePrimitives{
            D3DPT_LINELIST, D3DPT_LINESTRIP};
        for (const auto linePrimitive : directLinePrimitives) {
            const auto lineGeometryReady =
                outrun::vr::dx11::compose_fixed_function_geometry_readiness(
                    managedVertexPostResetReady, false, managedIndexReady,
                    linePrimitive);
            require(
                lineGeometryReady.ready &&
                outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                    d3d.context, lineGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    nullptr, DXGI_FORMAT_UNKNOWN, 0u),
                "R157 line fixture reaches exact dormant IA topology");

            const auto lineDrawReady = compose_fixed_function_draw_readiness(
                multiStageActivation, outputBindingRenderReady, surfacePairReady,
                outputStateReady, outputStateBinding, lineGeometryReady);
            const auto lineRenderTargetBoundDraw =
                outrun::vr::dx11::
                    compose_fixed_function_render_target_bound_draw_readiness(
                        lineDrawReady, d3d.context, outputStateBinding,
                        pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                        multiStageSamplers, multiStageTextures,
                        lineGeometryReady, managedVertexBuffer,
                        geometryVertexStride, geometryVertexOffset,
                        nullptr, DXGI_FORMAT_UNKNOWN, 0u, transform,
                        surfaceTargetBinding, outputColorSurface, outputDepthSurface);
            const auto lineDirectDispatch =
                outrun::vr::dx11::compose_fixed_function_direct_draw_dispatch_readiness(
                    lineRenderTargetBoundDraw, lineDrawReady, lineGeometryReady,
                    linePrimitive, 1u, false, 0u, 0u, 0);
            require(
                lineRenderTargetBoundDraw.ready &&
                lineDirectDispatch.inputValid &&
                lineDirectDispatch.renderTargetBoundDrawReady &&
                lineDirectDispatch.geometryReady &&
                lineDirectDispatch.geometryMatchesDraw &&
                lineDirectDispatch.topologyMatchesGeometry &&
                lineDirectDispatch.pointRasterSemanticsExact &&
                !lineDirectDispatch.lineRasterSemanticsExact &&
                lineDirectDispatch.bufferRangeExact &&
                lineDirectDispatch.dispatchArgumentsExact &&
                !lineDirectDispatch.ready &&
                lineDirectDispatch.snapshotToken == 0,
                "R157 direct line raster semantics remain fail closed");
        }

        require(
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
            "R147 restore indexed direct IA after dispatch proof");
    }

    NativeTriangleFanIndexBuffer liveFanOwner;
    require(
        liveFanOwner.initialize_nonindexed(d3d.device, 3u, 7u),
        "R142 generated fan owner prerequisite");
    const auto liveFanOwnerReady = liveFanOwner.readiness(d3d.device);
    const auto liveFanVertexReady =
        managedVertexBuffer.mirror_readiness(d3d.device);
    const auto liveFanGeometryReady =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            liveFanVertexReady, liveFanOwnerReady, 3u, 7u);
    require(
        liveFanGeometryReady.ready &&
        liveFanGeometryReady.generatedIndexBufferMatchesDraw &&
        liveFanGeometryReady.generatedIndexBufferSnapshotToken ==
            liveFanOwnerReady.snapshotToken,
        "R142 generated fan geometry prerequisite");

    const auto liveFanDrawReady =
        compose_fixed_function_draw_readiness(
            multiStageActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, liveFanGeometryReady);
    require(
        liveFanDrawReady.ready &&
        liveFanDrawReady.geometrySnapshotToken ==
            liveFanGeometryReady.snapshotToken,
        "R142 generated fan sealed draw prerequisite");

    ID3D11Buffer* liveFanVertexBuffer =
        managedVertexBuffer.mirror_buffer();
    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &geometryVertexStride, &geometryVertexOffset);
    require(
        liveFanOwner.bind(d3d.context),
        "R142 bind generated fan IA prerequisite");

    const auto completeFanBoundDraw =
        outrun::vr::dx11::
            compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u);
    require(
        completeFanBoundDraw.inputValid &&
        completeFanBoundDraw.sameContextBoundDrawReady &&
        completeFanBoundDraw.geometryReady &&
        completeFanBoundDraw.geometryMatchesDraw &&
        completeFanBoundDraw.vertexBufferBoundExact &&
        completeFanBoundDraw.generatedIndexBindingReady &&
        completeFanBoundDraw.generatedIndexMatchesGeometry &&
        completeFanBoundDraw.componentSnapshotsPresent &&
        completeFanBoundDraw.ready &&
        completeFanBoundDraw.geometrySnapshotToken ==
            liveFanGeometryReady.snapshotToken &&
        completeFanBoundDraw.vertexBufferSnapshotToken ==
            liveFanVertexReady.snapshotToken &&
        completeFanBoundDraw.generatedIndexBindingSnapshotToken != 0 &&
        completeFanBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_complete_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, completeFanBoundDraw.snapshotToken),
        "R142 complete fan bound draw seals live VB and generated IB");

    const auto finalFanBoundDraw =
        outrun::vr::dx11::
            compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        finalFanBoundDraw.inputValid &&
        finalFanBoundDraw.completeFanBoundDrawReady &&
        finalFanBoundDraw.transformBindingReady &&
        finalFanBoundDraw.surfaceTargetBindingReady &&
        finalFanBoundDraw.surfacePairMatchesDraw &&
        finalFanBoundDraw.componentSnapshotsPresent &&
        finalFanBoundDraw.ready &&
        finalFanBoundDraw.transformPayloadHash == transform.payloadHash &&
        finalFanBoundDraw.surfacePairSnapshotToken ==
            surfacePairReady.snapshotToken &&
        finalFanBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_final_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalFanBoundDraw.snapshotToken),
        "R146 nonindexed fan final draw seals live VS b0 and OM target");

    ID3D11Buffer* nullFanTransformBuffer = nullptr;
    d3d.context->VSSetConstantBuffers(0, 1, &nullFanTransformBuffer);
    const auto fanMissingTransform =
        outrun::vr::dx11::
            compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        fanMissingTransform.completeFanBoundDrawReady &&
        !fanMissingTransform.transformBindingReady &&
        fanMissingTransform.surfaceTargetBindingReady &&
        !fanMissingTransform.ready &&
        fanMissingTransform.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_final_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalFanBoundDraw.snapshotToken),
        "R146 nonindexed fan final draw fails closed after VS b0 drift");

    ID3D11Buffer* restoredFanTransformBuffer =
        pipelineBundle.transform_buffer().buffer();
    d3d.context->VSSetConstantBuffers(0, 1, &restoredFanTransformBuffer);
    d3d.context->OMSetRenderTargets(0, nullptr, nullptr);
    const auto fanMissingTargets =
        outrun::vr::dx11::
            compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        fanMissingTargets.completeFanBoundDrawReady &&
        fanMissingTargets.transformBindingReady &&
        !fanMissingTargets.surfaceTargetBindingReady &&
        fanMissingTargets.surfacePairMatchesDraw &&
        !fanMissingTargets.ready &&
        fanMissingTargets.snapshotToken == 0,
        "R146 nonindexed fan final draw fails closed after OM target drift");
    require(
        surfaceTargetBinding.apply(
            d3d.context, outputColorSurface, outputDepthSurface) &&
        outrun::vr::dx11::
            validate_fixed_function_final_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalFanBoundDraw.snapshotToken),
        "R146 nonindexed fan final draw restores transform and OM target snapshot");


    const auto fanDispatch =
        outrun::vr::dx11::
            compose_fixed_function_nonindexed_triangle_fan_draw_dispatch_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        fanDispatch.inputValid &&
        fanDispatch.finalFanBoundDrawReady &&
        fanDispatch.generatedIndexReady &&
        fanDispatch.generatedIndexMatchesDispatch &&
        fanDispatch.vertexBufferRangeExact &&
        fanDispatch.dispatchArgumentsExact &&
        fanDispatch.componentSnapshotsPresent &&
        fanDispatch.ready &&
        !fanDispatch.indexedSource &&
        fanDispatch.primitiveCount == 3u &&
        fanDispatch.indexCount == 9u &&
        fanDispatch.startIndexLocation == 0u &&
        fanDispatch.baseVertexLocation == 0 &&
        fanDispatch.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_nonindexed_triangle_fan_draw_dispatch_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                fanDispatch.snapshotToken),
        "R148 generated fan dispatch seals nonindexed DrawIndexed tuple");
    require(
        !outrun::vr::dx11::
            validate_fixed_function_nonindexed_triangle_fan_draw_dispatch_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 8u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                fanDispatch.snapshotToken),
        "R148 generated fan dispatch rejects nonindexed base-vertex drift");

    const UINT fanCapacityOverrunStride =
        managedVertexBuffer.byte_width();
    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &fanCapacityOverrunStride, &geometryVertexOffset);
    const auto fanCapacityOverrun =
        outrun::vr::dx11::
            compose_fixed_function_nonindexed_triangle_fan_draw_dispatch_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, fanCapacityOverrunStride,
                geometryVertexOffset, liveFanOwner, 3u, 7u, transform,
                surfaceTargetBinding, outputColorSurface, outputDepthSurface);
    require(
        fanCapacityOverrun.inputValid &&
        fanCapacityOverrun.finalFanBoundDrawReady &&
        fanCapacityOverrun.generatedIndexReady &&
        fanCapacityOverrun.generatedIndexMatchesDispatch &&
        !fanCapacityOverrun.vertexBufferRangeExact &&
        !fanCapacityOverrun.dispatchArgumentsExact &&
        !fanCapacityOverrun.ready &&
        fanCapacityOverrun.snapshotToken == 0,
        "R154 nonindexed fan dispatch rejects vertex buffer overrun");
    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &geometryVertexStride, &geometryVertexOffset);
    require(
        outrun::vr::dx11::
            validate_fixed_function_nonindexed_triangle_fan_draw_dispatch_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                fanDispatch.snapshotToken),
        "R154 nonindexed fan dispatch restores bounded vertex span");

    d3d.context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    const auto fanTopologyDrift =
        outrun::vr::dx11::
            compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u);
    require(
        fanTopologyDrift.sameContextBoundDrawReady &&
        fanTopologyDrift.geometryReady &&
        fanTopologyDrift.geometryMatchesDraw &&
        fanTopologyDrift.vertexBufferBoundExact &&
        !fanTopologyDrift.generatedIndexBindingReady &&
        !fanTopologyDrift.ready &&
        fanTopologyDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_complete_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, completeFanBoundDraw.snapshotToken),
        "R142 complete fan bound draw rejects generated IB topology drift");
    require(
        liveFanOwner.bind(d3d.context),
        "R142 restore generated fan topology after drift");

    const UINT liveFanStrideDrift = geometryVertexStride + 4u;
    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &liveFanStrideDrift, &geometryVertexOffset);
    const auto fanVertexDrift =
        outrun::vr::dx11::
            compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u);
    require(
        fanVertexDrift.sameContextBoundDrawReady &&
        fanVertexDrift.geometryReady &&
        fanVertexDrift.geometryMatchesDraw &&
        !fanVertexDrift.vertexBufferBoundExact &&
        fanVertexDrift.generatedIndexBindingReady &&
        fanVertexDrift.generatedIndexMatchesGeometry &&
        !fanVertexDrift.ready &&
        fanVertexDrift.snapshotToken == 0,
        "R142 complete fan bound draw rejects live VB stride drift");

    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &geometryVertexStride, &geometryVertexOffset);
    require(
        outrun::vr::dx11::
            validate_fixed_function_complete_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, 7u, completeFanBoundDraw.snapshotToken),
        "R142 complete fan bound draw restores deterministic live IA snapshot");

    // R156 capacity fixture is intentionally bounded by the 256-byte managed
    // VB at stride 24. The positive BaseVertexLocation (-3) must fit while the
    // negative probe (+1) must cross the same byte-capacity boundary.
    const std::array<std::uint16_t, 5> liveIndexedFanSource{
        99u, 4u, 6u, 8u, 9u};
    NativeManagedBufferShadow liveIndexedFanSourceBuffer;
    require(
        liveIndexedFanSourceBuffer.initialize(
            ResourceRole::Index,
            static_cast<UINT>(sizeof(liveIndexedFanSource)),
            0) &&
        liveIndexedFanSourceBuffer.write_range(
            0, liveIndexedFanSource.data(),
            static_cast<UINT>(sizeof(liveIndexedFanSource))) &&
        liveIndexedFanSourceBuffer.recreate_and_upload_mirror(d3d.device),
        "R155 indexed fan managed source prerequisite");
    const auto liveIndexedSourceReady =
        liveIndexedFanSourceBuffer.mirror_readiness(d3d.device);
    NativeTriangleFanIndexBuffer liveIndexedFanOwner;
    require(
        liveIndexedSourceReady.ready &&
        liveIndexedSourceReady.role == ResourceRole::Index &&
        liveIndexedFanOwner.initialize_indexed(
            d3d.device, 2u, D3DFMT_INDEX16, 1u,
            liveIndexedFanSource.data(),
            static_cast<UINT>(liveIndexedFanSource.size()),
            liveIndexedSourceReady.snapshotToken),
        "R144 indexed generated fan owner prerequisite");
    const auto liveIndexedFanOwnerReady =
        liveIndexedFanOwner.readiness(d3d.device);
    const auto liveIndexedFanSourceContent =
        outrun::vr::dx11::compose_fixed_function_indexed_fan_source_content_readiness(
            liveIndexedFanSourceBuffer, liveIndexedFanOwner, d3d.device);
    require(
        liveIndexedFanSourceContent.inputValid &&
        liveIndexedFanSourceContent.generatedIndexReady &&
        liveIndexedFanSourceContent.sourceIndexReady &&
        liveIndexedFanSourceContent.sourceProvenanceMatches &&
        liveIndexedFanSourceContent.expandedContentExact &&
        liveIndexedFanSourceContent.componentSnapshotsPresent &&
        liveIndexedFanSourceContent.ready &&
        liveIndexedFanSourceContent.expectedExpandedContentHash ==
            liveIndexedFanOwnerReady.contentHash &&
        liveIndexedFanSourceContent.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_indexed_fan_source_content_snapshot(
            liveIndexedFanSourceBuffer, liveIndexedFanOwner, d3d.device,
            liveIndexedFanSourceContent.snapshotToken),
        "R155 indexed fan source content matches exact managed IB shadow");

    const std::array<std::uint16_t, 5> forgedIndexedFanSource{
        99u, 4u, 6u, 8u, 10u};
    NativeTriangleFanIndexBuffer forgedIndexedFanOwner;
    require(
        forgedIndexedFanOwner.initialize_indexed(
            d3d.device, 2u, D3DFMT_INDEX16, 1u,
            forgedIndexedFanSource.data(),
            static_cast<UINT>(forgedIndexedFanSource.size()),
            liveIndexedSourceReady.snapshotToken),
        "R155 forged indexed fan owner prerequisite");
    const auto forgedIndexedFanSourceContent =
        outrun::vr::dx11::compose_fixed_function_indexed_fan_source_content_readiness(
            liveIndexedFanSourceBuffer, forgedIndexedFanOwner, d3d.device);
    require(
        forgedIndexedFanSourceContent.inputValid &&
        forgedIndexedFanSourceContent.generatedIndexReady &&
        forgedIndexedFanSourceContent.sourceIndexReady &&
        forgedIndexedFanSourceContent.sourceProvenanceMatches &&
        !forgedIndexedFanSourceContent.expandedContentExact &&
        !forgedIndexedFanSourceContent.ready &&
        forgedIndexedFanSourceContent.snapshotToken == 0,
        "R155 indexed fan source content rejects borrowed token with foreign bytes");
    const auto liveIndexedFanGeometryReady =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                liveFanVertexReady, liveIndexedSourceReady,
                liveIndexedFanOwnerReady, 2u, D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()));
    require(
        liveIndexedFanGeometryReady.ready &&
        liveIndexedFanGeometryReady.indexBufferSnapshotToken ==
            liveIndexedSourceReady.snapshotToken &&
        liveIndexedFanGeometryReady.generatedIndexBufferSnapshotToken ==
            liveIndexedFanOwnerReady.snapshotToken,
        "R144 indexed fan geometry prerequisite");

    const auto liveIndexedFanDrawReady =
        compose_fixed_function_draw_readiness(
            multiStageActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding,
            liveIndexedFanGeometryReady);
    require(
        liveIndexedFanDrawReady.ready &&
        liveIndexedFanDrawReady.geometrySnapshotToken ==
            liveIndexedFanGeometryReady.snapshotToken,
        "R144 indexed fan sealed draw prerequisite");

    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &geometryVertexStride, &geometryVertexOffset);
    require(
        liveIndexedFanOwner.bind(d3d.context),
        "R144 bind indexed generated fan IA prerequisite");

    constexpr INT indexedFanBaseVertexLocation = -3;
    constexpr UINT indexedFanObservedMaxIndex = 9u;
    const std::int64_t indexedFanPositiveEffectiveMax =
        static_cast<std::int64_t>(indexedFanBaseVertexLocation) +
        static_cast<std::int64_t>(indexedFanObservedMaxIndex);
    const std::int64_t indexedFanOverrunEffectiveMax =
        1ll + static_cast<std::int64_t>(indexedFanObservedMaxIndex);
    require(
        indexedFanPositiveEffectiveMax >= 0 &&
        (static_cast<std::uint64_t>(indexedFanPositiveEffectiveMax) + 1ull) *
                static_cast<std::uint64_t>(geometryVertexStride) <=
            static_cast<std::uint64_t>(managedVertexBuffer.byte_width()) &&
        indexedFanOverrunEffectiveMax >= 0 &&
        (static_cast<std::uint64_t>(indexedFanOverrunEffectiveMax) + 1ull) *
                static_cast<std::uint64_t>(geometryVertexStride) >
            static_cast<std::uint64_t>(managedVertexBuffer.byte_width()),
        "R156 indexed fan capacity fixture straddles managed VB boundary");
    const auto completeIndexedFanBoundDraw =
        outrun::vr::dx11::
            compose_fixed_function_complete_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation);
    require(
        completeIndexedFanBoundDraw.inputValid &&
        completeIndexedFanBoundDraw.sameContextBoundDrawReady &&
        completeIndexedFanBoundDraw.geometryReady &&
        completeIndexedFanBoundDraw.geometryMatchesDraw &&
        completeIndexedFanBoundDraw.sourceIndexBufferCurrent &&
        completeIndexedFanBoundDraw.vertexBufferBoundExact &&
        completeIndexedFanBoundDraw.generatedIndexBindingReady &&
        completeIndexedFanBoundDraw.generatedIndexMatchesGeometry &&
        completeIndexedFanBoundDraw.componentSnapshotsPresent &&
        completeIndexedFanBoundDraw.ready &&
        completeIndexedFanBoundDraw.geometrySnapshotToken ==
            liveIndexedFanGeometryReady.snapshotToken &&
        completeIndexedFanBoundDraw.sourceIndexBufferSnapshotToken ==
            liveIndexedSourceReady.snapshotToken &&
        completeIndexedFanBoundDraw.generatedIndexBindingSnapshotToken != 0 &&
        completeIndexedFanBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_complete_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation,
                completeIndexedFanBoundDraw.snapshotToken),
        "R144 indexed fan final bound draw seals source provenance and live generated IA");

    const auto finalIndexedFanBoundDraw =
        outrun::vr::dx11::
            compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        finalIndexedFanBoundDraw.inputValid &&
        finalIndexedFanBoundDraw.completeFanBoundDrawReady &&
        finalIndexedFanBoundDraw.transformBindingReady &&
        finalIndexedFanBoundDraw.surfaceTargetBindingReady &&
        finalIndexedFanBoundDraw.surfacePairMatchesDraw &&
        finalIndexedFanBoundDraw.componentSnapshotsPresent &&
        finalIndexedFanBoundDraw.ready &&
        finalIndexedFanBoundDraw.transformPayloadHash == transform.payloadHash &&
        finalIndexedFanBoundDraw.surfacePairSnapshotToken ==
            surfacePairReady.snapshotToken &&
        finalIndexedFanBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalIndexedFanBoundDraw.snapshotToken),
        "R146 indexed fan final draw seals live VS b0 and OM target");

    ID3D11Buffer* nullIndexedFanTransformBuffer = nullptr;
    d3d.context->VSSetConstantBuffers(0, 1, &nullIndexedFanTransformBuffer);
    const auto indexedFanMissingTransform =
        outrun::vr::dx11::
            compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        indexedFanMissingTransform.completeFanBoundDrawReady &&
        !indexedFanMissingTransform.transformBindingReady &&
        indexedFanMissingTransform.surfaceTargetBindingReady &&
        indexedFanMissingTransform.surfacePairMatchesDraw &&
        !indexedFanMissingTransform.ready &&
        indexedFanMissingTransform.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalIndexedFanBoundDraw.snapshotToken),
        "R146 indexed fan final draw fails closed after VS b0 drift");

    ID3D11Buffer* restoredIndexedFanTransformBuffer =
        pipelineBundle.transform_buffer().buffer();
    d3d.context->VSSetConstantBuffers(
        0, 1, &restoredIndexedFanTransformBuffer);

    d3d.context->OMSetRenderTargets(0, nullptr, nullptr);
    const auto indexedFanMissingTargets =
        outrun::vr::dx11::
            compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        indexedFanMissingTargets.completeFanBoundDrawReady &&
        indexedFanMissingTargets.transformBindingReady &&
        !indexedFanMissingTargets.surfaceTargetBindingReady &&
        indexedFanMissingTargets.surfacePairMatchesDraw &&
        !indexedFanMissingTargets.ready &&
        indexedFanMissingTargets.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalIndexedFanBoundDraw.snapshotToken),
        "R146 indexed fan final draw fails closed after OM target drift");

    require(
        surfaceTargetBinding.apply(
            d3d.context, outputColorSurface, outputDepthSurface) &&
        outrun::vr::dx11::
            validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalIndexedFanBoundDraw.snapshotToken),
        "R146 indexed fan final draw restores transform and OM target snapshot");

    require(
        !outrun::vr::dx11::
            validate_fixed_function_complete_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation + 1,
                completeIndexedFanBoundDraw.snapshotToken),
        "R144 indexed fan final snapshot rejects BaseVertexLocation drift");

    const auto indexedFanFormatDrift =
        outrun::vr::dx11::
            compose_fixed_function_complete_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX32, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation);
    require(
        indexedFanFormatDrift.sameContextBoundDrawReady &&
        !indexedFanFormatDrift.geometryReady &&
        !indexedFanFormatDrift.geometryMatchesDraw &&
        indexedFanFormatDrift.generatedIndexBindingReady &&
        !indexedFanFormatDrift.ready &&
        indexedFanFormatDrift.snapshotToken == 0,
        "R144 indexed fan final bound draw rejects source format drift");


    const auto indexedFanDispatch =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        indexedFanDispatch.inputValid &&
        indexedFanDispatch.finalFanBoundDrawReady &&
        indexedFanDispatch.generatedIndexReady &&
        indexedFanDispatch.generatedIndexMatchesDispatch &&
        indexedFanDispatch.vertexBufferRangeExact &&
        indexedFanDispatch.dispatchArgumentsExact &&
        indexedFanDispatch.componentSnapshotsPresent &&
        indexedFanDispatch.ready &&
        indexedFanDispatch.indexedSource &&
        indexedFanDispatch.primitiveCount == 2u &&
        indexedFanDispatch.indexCount == 6u &&
        indexedFanDispatch.startIndexLocation == 0u &&
        indexedFanDispatch.baseVertexLocation ==
            indexedFanBaseVertexLocation &&
        indexedFanDispatch.sourceIndexSnapshotToken ==
            liveIndexedSourceReady.snapshotToken &&
        indexedFanDispatch.sourceContentSnapshotToken ==
            liveIndexedFanSourceContent.snapshotToken &&
        indexedFanDispatch.sourceObservedMinIndex == 4u &&
        indexedFanDispatch.sourceObservedMaxIndex == indexedFanObservedMaxIndex &&
        indexedFanDispatch.sourceValueSnapshotToken != 0 &&
        indexedFanDispatch.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_indexed_triangle_fan_draw_dispatch_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                indexedFanDispatch.snapshotToken),
        "R148 generated fan dispatch seals indexed DrawIndexed tuple");

    const auto indexedFanVertexOverrun =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                1, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        indexedFanVertexOverrun.inputValid &&
        indexedFanVertexOverrun.finalFanBoundDrawReady &&
        indexedFanVertexOverrun.generatedIndexReady &&
        indexedFanVertexOverrun.generatedIndexMatchesDispatch &&
        indexedFanVertexOverrun.sourceObservedMinIndex == 4u &&
        indexedFanVertexOverrun.sourceObservedMaxIndex == indexedFanObservedMaxIndex &&
        indexedFanVertexOverrun.sourceValueSnapshotToken != 0 &&
        !indexedFanVertexOverrun.vertexBufferRangeExact &&
        !indexedFanVertexOverrun.dispatchArgumentsExact &&
        !indexedFanVertexOverrun.ready &&
        indexedFanVertexOverrun.snapshotToken == 0,
        "R156 indexed fan dispatch rejects effective vertex buffer overrun");

    require(
        !outrun::vr::dx11::
            validate_fixed_function_indexed_triangle_fan_draw_dispatch_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation + 1, transform,
                surfaceTargetBinding, outputColorSurface, outputDepthSurface,
                indexedFanDispatch.snapshotToken),
        "R148 generated fan dispatch rejects indexed BaseVertexLocation drift");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R142 restore direct IA geometry after generated fan proof");

    auto mismatchedPipelineBinding = drawPipelineBindingReady;
    mismatchedPipelineBinding.pipelineSnapshotToken ^= 0x100000001b3ull;
    const auto mismatchedPipelineBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, texturedDrawReady, mismatchedPipelineBinding,
            d3d.context, outputStateBinding);
    require(
        mismatchedPipelineBoundDraw.pipelineBindingReady &&
        !mismatchedPipelineBoundDraw.pipelineBindingMatchesDraw &&
        !mismatchedPipelineBoundDraw.ready &&
        mismatchedPipelineBoundDraw.snapshotToken == 0,
        "R134 bound draw rejects mismatched R112 pipeline identity");

    auto mismatchedTexturedDraw = texturedDrawReady;
    mismatchedTexturedDraw.drawSnapshotToken ^= 0x9e3779b97f4a7c15ull;
    const auto mismatchedTexturedBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, mismatchedTexturedDraw, drawPipelineBindingReady,
            d3d.context, outputStateBinding);
    require(
        !mismatchedTexturedBoundDraw.texturedDrawReady &&
        mismatchedTexturedBoundDraw.pipelineBindingReady &&
        mismatchedTexturedBoundDraw.pipelineBindingMatchesDraw &&
        !mismatchedTexturedBoundDraw.ready &&
        mismatchedTexturedBoundDraw.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_bound_draw_snapshot(
            drawReady, mismatchedTexturedDraw, drawPipelineBindingReady,
            d3d.context, outputStateBinding, boundDrawReady.snapshotToken),
        "R134 bound draw rejects textured R133-to-R131 identity drift");

    d3d.context->PSSetShader(nullptr, nullptr, 0);
    const auto staleLivePipelineBinding =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        !staleLivePipelineBinding.boundExact &&
        !staleLivePipelineBinding.ready &&
        staleLivePipelineBinding.snapshotToken == 0 &&
        !pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R134 live PS binding drift invalidates pipeline binding snapshot");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R134 restore pipeline binding after drift probe");

    ID3D11SamplerState* clearDrawSampler = nullptr;
    ID3D11ShaderResourceView* clearDrawSrv = nullptr;
    d3d.context->PSSetSamplers(
        drawTextureStageSlot, 1, &clearDrawSampler);
    d3d.context->PSSetShaderResources(
        drawTextureStageSlot, 1, &clearDrawSrv);
    const auto missingTextureStageDraw =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            drawReady, d3d.context, drawTextureStageSlot, samplerOwner, textureView);
    require(
        !missingTextureStageDraw.textureStageReady &&
        !missingTextureStageDraw.ready &&
        missingTextureStageDraw.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_texture_stage_binding_snapshot(
            d3d.context, drawTextureStageSlot, samplerOwner, textureView,
            drawTextureStageReady.snapshotToken) &&
        !outrun::vr::dx11::validate_fixed_function_textured_draw_snapshot(
            drawReady, d3d.context, drawTextureStageSlot, samplerOwner, textureView,
            texturedDrawReady.snapshotToken),
        "R132 textured draw readiness fails closed after PS binding drift");

    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, textureStageSlot, samplerOwner, textureView),
        "R133 wrong-stage binding prerequisite");
    const auto wrongTextureStageDraw =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            drawReady, d3d.context, textureStageSlot, samplerOwner, textureView);
    require(
        wrongTextureStageDraw.textureStageReady &&
        !wrongTextureStageDraw.textureMaskMatches &&
        !wrongTextureStageDraw.inputValid &&
        !wrongTextureStageDraw.ready &&
        wrongTextureStageDraw.requiredTextureMask == 0x1u &&
        wrongTextureStageDraw.observedTextureMask ==
            (1u << textureStageSlot) &&
        wrongTextureStageDraw.snapshotToken == 0,
        "R133 textured draw rejects texture stage outside activation mask");

    auto forgedTextureMaskDraw = drawReady;
    forgedTextureMaskDraw.requiredTextureMask =
        (1u << textureStageSlot);
    const auto forgedTextureMaskTexturedDraw =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            forgedTextureMaskDraw, d3d.context, textureStageSlot,
            samplerOwner, textureView);
    require(
        forgedTextureMaskTexturedDraw.textureStageReady &&
        forgedTextureMaskTexturedDraw.textureMaskMatches &&
        !outrun::vr::dx11::validate_fixed_function_draw_readiness_integrity(
            forgedTextureMaskDraw) &&
        !forgedTextureMaskTexturedDraw.drawReady &&
        !forgedTextureMaskTexturedDraw.ready &&
        forgedTextureMaskTexturedDraw.snapshotToken == 0,
        "R135 textured readiness rejects unsealed required-stage mask drift");

    auto multiStageDraw = drawReady;
    multiStageDraw.requiredTextureMask = 0x3u;
    const auto partialMultiStageDraw =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            multiStageDraw, d3d.context, textureStageSlot, samplerOwner, textureView);
    require(
        partialMultiStageDraw.textureStageReady &&
        !partialMultiStageDraw.textureMaskMatches &&
        !partialMultiStageDraw.drawReady &&
        !partialMultiStageDraw.ready &&
        partialMultiStageDraw.snapshotToken == 0,
        "R133 single-stage observer rejects multi-stage activation mask");

    auto activationMissingSnapshot = texturedActivation;
    activationMissingSnapshot.snapshotToken = 0;
    auto renderStateMissingSnapshot = outputBindingRenderReady;
    renderStateMissingSnapshot.snapshotToken = 0;
    auto renderStateNotReady = outputBindingRenderReady;
    renderStateNotReady.ready = false;
    auto surfacePairMissingSnapshot = surfacePairReady;
    surfacePairMissingSnapshot.snapshotToken = 0;
    auto surfacePairNotReady = surfacePairReady;
    surfacePairNotReady.ready = false;
    auto outputStateNotReady = outputStateReady;
    outputStateNotReady.ready = false;
    outputStateNotReady.snapshotToken = 0;
    NativeFixedFunctionOutputStateBinding missingDrawOutputBinding;

    const auto missingActivationDraw =
        compose_fixed_function_draw_readiness(
            activationMissingSnapshot, outputBindingRenderReady,
            surfacePairReady, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto missingRenderStateDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, renderStateMissingSnapshot,
            surfacePairReady, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto pendingRenderStateDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, renderStateNotReady,
            surfacePairReady, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto missingSurfacePairDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady,
            surfacePairMissingSnapshot, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto pendingSurfacePairDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady,
            surfacePairNotReady, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto pendingOutputStateDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateNotReady, outputStateBinding, indexedGeometryReady);
    const auto missingOutputBindingDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, missingDrawOutputBinding, indexedGeometryReady);
    auto geometryNotReady = indexedGeometryReady;
    geometryNotReady.ready = false;
    geometryNotReady.snapshotToken = 0;
    const auto pendingGeometryDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, geometryNotReady);
    require(
        !missingActivationDraw.ready &&
        missingActivationDraw.snapshotToken == 0 &&
        !missingRenderStateDraw.ready &&
        missingRenderStateDraw.snapshotToken == 0 &&
        !pendingRenderStateDraw.ready &&
        pendingRenderStateDraw.snapshotToken == 0 &&
        !missingSurfacePairDraw.ready &&
        missingSurfacePairDraw.snapshotToken == 0 &&
        !pendingSurfacePairDraw.ready &&
        pendingSurfacePairDraw.snapshotToken == 0 &&
        !pendingOutputStateDraw.ready &&
        pendingOutputStateDraw.snapshotToken == 0 &&
        !missingOutputBindingDraw.outputBindingReady &&
        !missingOutputBindingDraw.ready &&
        missingOutputBindingDraw.snapshotToken == 0 &&
        !pendingGeometryDraw.ready &&
        pendingGeometryDraw.snapshotToken == 0,
        "R131 draw readiness fails closed on missing binding evidence");

    auto changedRenderStateIdentity = outputBindingRenderReady;
    changedRenderStateIdentity.snapshotToken ^= 0x9e3779b97f4a7c15ull;
    const auto changedDrawReady =
        compose_fixed_function_draw_readiness(
            texturedActivation, changedRenderStateIdentity, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady);
    require(
        !changedDrawReady.outputBindingReady &&
        !changedDrawReady.ready &&
        changedDrawReady.snapshotToken == 0 &&
        !validate_fixed_function_draw_snapshot(
            texturedActivation, changedRenderStateIdentity, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady,
            drawReady.snapshotToken),
        "R131 draw binding rejects render-state identity drift");

    auto changedSurfacePairIdentity = surfacePairReady;
    changedSurfacePairIdentity.snapshotToken ^= 0x100000001b3ull;
    const auto changedSurfacePairDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady,
            changedSurfacePairIdentity, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    require(
        !changedSurfacePairDraw.outputBindingReady &&
        !changedSurfacePairDraw.ready &&
        changedSurfacePairDraw.snapshotToken == 0 &&
        !validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady,
            changedSurfacePairIdentity, outputStateReady, outputStateBinding,
            indexedGeometryReady, drawReady.snapshotToken),
        "R131 draw binding rejects surface-pair identity drift");

    const auto changedOutputStateDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            changedOutputStateReady, outputStateBinding, indexedGeometryReady);
    require(
        !changedOutputStateDraw.outputBindingReady &&
        !changedOutputStateDraw.ready &&
        changedOutputStateDraw.snapshotToken == 0 &&
        !validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            changedOutputStateReady, outputStateBinding, indexedGeometryReady,
            drawReady.snapshotToken),
        "R131 draw binding rejects output-state identity drift");

    auto changedGeometryIdentity = indexedGeometryReady;
    changedGeometryIdentity.snapshotToken ^= 0x9e3779b97f4a7c15ull;
    const auto changedGeometryDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, changedGeometryIdentity);
    require(
        changedGeometryDraw.outputBindingReady &&
        changedGeometryDraw.ready &&
        changedGeometryDraw.snapshotToken != 0 &&
        changedGeometryDraw.snapshotToken != drawReady.snapshotToken &&
        !validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, changedGeometryIdentity,
            drawReady.snapshotToken) &&
        validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, changedGeometryIdentity,
            changedGeometryDraw.snapshotToken),
        "R122 draw snapshot changes with geometry identity; R131 draw snapshot still changes with independent geometry identity");

    DevicePair pipelineOtherDevice = create_warp_device();
    auto changedLayout = inputLayout;
    changedLayout.elements[0].SemanticIndex ^= 1u;
    auto changedStrideLayout = inputLayout;
    changedStrideLayout.stream0Stride -= 4u;
    auto changedVertexPrototype = vertexPrototype;
    changedVertexPrototype.sourceHash ^= 0x100000001b3ull;
    auto changedPixelPrototype = pixelPrototype;
    changedPixelPrototype.sourceHash ^= 0x9e3779b97f4a7c15ull;
    const auto pipelineForeignDevice =
        pipelineBundle.translation_readiness(
            pipelineOtherDevice.device, inputLayout,
            vertexPrototype, pixelPrototype);
    const auto pipelineChangedLayout =
        pipelineBundle.translation_readiness(
            d3d.device, changedLayout, vertexPrototype, pixelPrototype);
    const auto pipelineChangedStride =
        pipelineBundle.translation_readiness(
            d3d.device, changedStrideLayout, vertexPrototype, pixelPrototype);
    const auto pipelineChangedVertex =
        pipelineBundle.translation_readiness(
            d3d.device, inputLayout, changedVertexPrototype, pixelPrototype);
    const auto pipelineChangedPixel =
        pipelineBundle.translation_readiness(
            d3d.device, inputLayout, vertexPrototype, changedPixelPrototype);
    require(
        pipelineForeignDevice.inputValid &&
        pipelineForeignDevice.bundleReady &&
        !pipelineForeignDevice.deviceMatches &&
        !pipelineForeignDevice.ready &&
        pipelineForeignDevice.snapshotToken == 0 &&
        pipelineChangedLayout.inputValid &&
        !pipelineChangedLayout.inputLayoutMatches &&
        !pipelineChangedLayout.ready &&
        pipelineChangedLayout.snapshotToken == 0 &&
        pipelineChangedStride.inputValid &&
        !pipelineChangedStride.inputLayoutMatches &&
        !pipelineChangedStride.ready &&
        pipelineChangedStride.snapshotToken == 0 &&
        pipelineChangedVertex.inputValid &&
        !pipelineChangedVertex.vertexShaderMatches &&
        !pipelineChangedVertex.ready &&
        pipelineChangedVertex.snapshotToken == 0 &&
        pipelineChangedPixel.inputValid &&
        !pipelineChangedPixel.pixelShaderMatches &&
        !pipelineChangedPixel.ready &&
        pipelineChangedPixel.snapshotToken == 0,
        "R112 pipeline identity fails closed on device layout and shader provenance drift");
    pipelineOtherDevice.context->Release();
    pipelineOtherDevice.device->Release();

    const auto pipelineInitialToken = pipelineIdentityReady.snapshotToken;
    const auto pipelineInitialGeneration =
        pipelineIdentityReady.bundleGeneration;

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
    const auto pipelineIdentityRecreated =
        pipelineBundle.translation_readiness(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype);
    require(
        pipelineIdentityRecreated.ready &&
        pipelineIdentityRecreated.bundleGeneration >
            pipelineInitialGeneration &&
        pipelineIdentityRecreated.snapshotToken != 0 &&
        pipelineIdentityRecreated.snapshotToken != pipelineInitialToken &&
        !pipelineBundle.validate_translation_snapshot(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype,
            pipelineInitialToken) &&
        pipelineBundle.validate_translation_snapshot(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityRecreated.snapshotToken),
        "R112 bundle recreation invalidates stale pipeline translation snapshot");

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

    lockBridgeShadow.shutdown();
    require(
        !lockBridgeShadow.ready() &&
        !lockBridgeShadow.source_lock_active() &&
        !lockBridgeShadow.shadow_valid() &&
        !lockBridgeShadow.mirror_ready(),
        "R104 LockRect bridge shutdown clears capture and ownership");

    managedIndexBuffer.shutdown();
    managedVertexBuffer.shutdown();
    require(
        !managedIndexBuffer.ready() &&
        !managedIndexBuffer.shadow_valid() &&
        !managedIndexBuffer.mirror_ready() &&
        managedIndexBuffer.mirror_buffer() == nullptr &&
        !managedVertexBuffer.ready() &&
        !managedVertexBuffer.shadow_valid() &&
        !managedVertexBuffer.mirror_ready() &&
        managedVertexBuffer.mirror_buffer() == nullptr,
        "R113 managed buffer shutdown releases CPU/GPU ownership");

    managedShadow.shutdown();
    require(
        !managedShadow.ready() &&
        !managedShadow.shadow_valid() &&
        !managedShadow.mirror_ready() &&
        managedShadow.shadow_version() == 0 &&
        managedShadow.device_generation() == 1,
        "R102 managed shadow shutdown resets storage and lifetime");
    require(
        managedShadow.mirror_device() == nullptr &&
        managedShadow.mirror_texture() == nullptr &&
        managedShadow.mirror_srv() == nullptr,
        "R103 managed shadow shutdown resets CPU and GPU ownership");

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
    isolationPredicate->Release();
    isolationStreamOutputBuffer->Release();
    isolationGeometryShader->Release();
    isolationGeometryBytecode->Release();
    vertexShader->Release();
    d3d.context->Release();
    d3d.device->Release();
    reflection->Release();
    vertexBytecode->Release();

    std::cout << "DX11 constant buffer probe R95: PASS\n";
    std::cout << "DX11 constant buffer lifetime R96: PASS\n";
    std::cout << "DX11 fixed-function pipeline bundle R97: PASS\n";
    std::cout << "DX11 dormant fixed-function pipeline object binding: PASS\n";
    std::cout << "DX11 fixed-function GS/HS/DS isolation R147: PASS\n";
    std::cout << "DX11 fixed-function SO/predication isolation R148: PASS\n";
    std::cout << "DX11 direct bound-buffer capacity R151: PASS\n";
    std::cout << "DX11 indexed source binding R153: PASS\n";
    std::cout << "DX11 indexed fan source content R155: PASS\n";
    std::cout << "DX11 indexed fan vertex capacity R156: PASS\n";
    std::cout << "DX11 direct line raster semantics R157: PASS\n";
    std::cout << "DX11 fixed-function sampler ownership R98: PASS\n";
    std::cout << "DX11 fixed-function texture view ownership R99: PASS\n";
    std::cout << "DX11 texture mutation readiness R100: PASS\n";
    std::cout << "DX11 fixed-function texture upload R101: PASS\n";
    std::cout << "DX11 managed texture shadow lifetime R102: PASS\n";
    std::cout << "DX11 managed texture mirror reupload R103: PASS\n";
    std::cout << "DX11 managed Texture2D LockRect bridge R104: PASS\n";
    std::cout << "DX11 managed Texture2D lifetime registry R105: PASS\n";
    std::cout << "DX11 managed Texture2D mutation-source completeness R107: PASS\n";
    std::cout << "DX11 managed Texture2D registry mirror readiness R108: PASS\n";
    std::cout << "DX11 managed Texture2D stage mirror readiness R109: PASS\n";
    std::cout << "DX11 managed Texture2D readiness snapshot token R110: PASS\n";
    std::cout << "DX11 managed Texture2D mirror descriptor exactness R111: PASS\n";
    std::cout << "DX11 fixed-function pipeline translation identity R112: PASS\n";
    std::cout << "DX11 managed vertex/index buffer mirror R113: PASS\n";
    std::cout << "DX11 managed buffer mirror readiness snapshot R119: PASS\n";
    std::cout << "DX11 fixed-function activation evidence composition R115: PASS\n";
    std::cout << "DX11 fixed-function render-state bundle R116: PASS\n";
    std::cout << "DX11 fixed-function draw readiness composition R120: PASS\n";
    std::cout << "DX11 draw output-binding readiness R131: PASS\n";
    std::cout << "DX11 final dormant bound-draw readiness R134: PASS\n";
    std::cout << "DX11 draw texture-mask snapshot integrity R135: PASS\n";
    std::cout << "DX11 aggregate texture binding readiness R136: PASS\n";
    std::cout << "DX11 geometry-gated draw readiness R122: PASS\n";
    std::cout << "DX11 dynamic output-state readiness R124: PASS\n";
    return 0;
}
