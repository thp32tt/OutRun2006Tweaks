#include "native_backend.hpp"

#include "pipeline_translation.hpp"
#include "triangle_fan_index_buffer.hpp"
#include "resource_translation.hpp"
#include "state_translation.hpp"
#include "surface_mirror.hpp"

#include <array>
#include <cstddef>
#include <cstring>
#include <d3dcompiler.h>
#include <dxgi1_2.h>
#include <limits>
#include <utility>

namespace outrun::vr::dx11 {
namespace {

bool same_luid(const LUID& a, const LUID& b) noexcept {
    return a.LowPart == b.LowPart && a.HighPart == b.HighPart;
}

std::uint64_t mix_readiness_snapshot_token(
    std::uint64_t token,
    std::uint64_t value) noexcept {
    token ^= value + 0x9e3779b97f4a7c15ull + (token << 6) + (token >> 2);
    return token;
}

std::uint64_t hash_pipeline_input_layout_identity(
    const VertexInputLayoutTranslation& layout) noexcept {
    if (!layout.exact || layout.elementCount == 0 ||
        layout.elementCount > layout.elements.size())
        return 0;

    std::uint64_t hash = 0xcbf29ce484222325ull;
    hash = mix_readiness_snapshot_token(hash, layout.elementCount);
    hash = mix_readiness_snapshot_token(hash, layout.declarationPath ? 1u : 0u);
    hash = mix_readiness_snapshot_token(hash, layout.fvfPath ? 1u : 0u);
    hash = mix_readiness_snapshot_token(hash, layout.fvfPending ? 1u : 0u);
    for (UINT index = 0; index < layout.elementCount; ++index) {
        const auto& element = layout.elements[index];
        if (!element.SemanticName || element.SemanticName[0] == '\0')
            return 0;
        for (const unsigned char* ch =
                 reinterpret_cast<const unsigned char*>(element.SemanticName);
             *ch != 0; ++ch)
            hash = mix_readiness_snapshot_token(hash, *ch);
        hash = mix_readiness_snapshot_token(hash, 0xffu);
        hash = mix_readiness_snapshot_token(hash, element.SemanticIndex);
        hash = mix_readiness_snapshot_token(
            hash, static_cast<std::uint32_t>(element.Format));
        hash = mix_readiness_snapshot_token(hash, element.InputSlot);
        hash = mix_readiness_snapshot_token(hash, element.AlignedByteOffset);
        hash = mix_readiness_snapshot_token(
            hash, static_cast<std::uint32_t>(element.InputSlotClass));
        hash = mix_readiness_snapshot_token(
            hash, element.InstanceDataStepRate);
    }
    return hash == 0 ? 1 : hash;
}

std::uint64_t hash_pipeline_render_state_identity(
    const PipelineTranslation& pipeline) noexcept {
    if (!pipeline.exact())
        return 0;

    std::uint64_t hash = 0xcbf29ce484222325ull;
    const auto mix = [&hash](std::uint64_t value) noexcept {
        hash = mix_readiness_snapshot_token(hash, value);
    };
    const auto mix_float = [&mix](float value) noexcept {
        std::uint32_t bits = 0;
        std::memcpy(&bits, &value, sizeof(bits));
        mix(bits);
    };
    const auto mix_stencil_face =
        [&mix](const D3D11_DEPTH_STENCILOP_DESC& face) noexcept {
            mix(static_cast<std::uint32_t>(face.StencilFailOp));
            mix(static_cast<std::uint32_t>(face.StencilDepthFailOp));
            mix(static_cast<std::uint32_t>(face.StencilPassOp));
            mix(static_cast<std::uint32_t>(face.StencilFunc));
        };

    mix(pipeline.blend.AlphaToCoverageEnable != FALSE ? 1u : 0u);
    mix(pipeline.blend.IndependentBlendEnable != FALSE ? 1u : 0u);
    for (const auto& rt : pipeline.blend.RenderTarget) {
        mix(rt.BlendEnable != FALSE ? 1u : 0u);
        mix(static_cast<std::uint32_t>(rt.SrcBlend));
        mix(static_cast<std::uint32_t>(rt.DestBlend));
        mix(static_cast<std::uint32_t>(rt.BlendOp));
        mix(static_cast<std::uint32_t>(rt.SrcBlendAlpha));
        mix(static_cast<std::uint32_t>(rt.DestBlendAlpha));
        mix(static_cast<std::uint32_t>(rt.BlendOpAlpha));
        mix(rt.RenderTargetWriteMask);
    }

    const auto& depth = pipeline.depth_stencil;
    mix(depth.DepthEnable != FALSE ? 1u : 0u);
    mix(static_cast<std::uint32_t>(depth.DepthWriteMask));
    mix(static_cast<std::uint32_t>(depth.DepthFunc));
    mix(depth.StencilEnable != FALSE ? 1u : 0u);
    mix(depth.StencilReadMask);
    mix(depth.StencilWriteMask);
    mix_stencil_face(depth.FrontFace);
    mix_stencil_face(depth.BackFace);

    const auto& raster = pipeline.rasterizer;
    mix(static_cast<std::uint32_t>(raster.FillMode));
    mix(static_cast<std::uint32_t>(raster.CullMode));
    mix(raster.FrontCounterClockwise != FALSE ? 1u : 0u);
    mix(static_cast<std::uint32_t>(raster.DepthBias));
    mix_float(raster.DepthBiasClamp);
    mix_float(raster.SlopeScaledDepthBias);
    mix(raster.DepthClipEnable != FALSE ? 1u : 0u);
    mix(raster.ScissorEnable != FALSE ? 1u : 0u);
    mix(raster.MultisampleEnable != FALSE ? 1u : 0u);
    mix(raster.AntialiasedLineEnable != FALSE ? 1u : 0u);
    mix(pipeline.stencil_ref);

    return hash == 0 ? 1 : hash;
}

bool texture_uncompressed_row_bytes(
    D3DFORMAT format,
    UINT width,
    UINT& rowBytes) noexcept {

    if (width == 0)
        return false;

    UINT bytesPerPixel = 0;
    switch (format) {
    case D3DFMT_A8R8G8B8:
    case D3DFMT_X8R8G8B8:
    case D3DFMT_A8B8G8R8:
        bytesPerPixel = 4;
        break;
    case D3DFMT_R5G6B5:
    case D3DFMT_A1R5G5B5:
        bytesPerPixel = 2;
        break;
    case D3DFMT_A8:
        bytesPerPixel = 1;
        break;
    default:
        return false;
    }

    if (width > (std::numeric_limits<UINT>::max)() / bytesPerPixel)
        return false;
    rowBytes = width * bytesPerPixel;
    return true;
}

bool find_adapter(
    const LUID& wanted,
    Microsoft::WRL::ComPtr<IDXGIAdapter1>& adapter) noexcept {

    Microsoft::WRL::ComPtr<IDXGIFactory1> factory;
    if (FAILED(CreateDXGIFactory1(
            __uuidof(IDXGIFactory1),
            reinterpret_cast<void**>(factory.ReleaseAndGetAddressOf()))))
        return false;

    for (UINT index = 0;; ++index) {
        Microsoft::WRL::ComPtr<IDXGIAdapter1> candidate;
        const HRESULT hr = factory->EnumAdapters1(
            index, candidate.ReleaseAndGetAddressOf());
        if (hr == DXGI_ERROR_NOT_FOUND) break;
        if (FAILED(hr)) return false;

        DXGI_ADAPTER_DESC1 desc{};
        if (SUCCEEDED(candidate->GetDesc1(&desc)) &&
            same_luid(desc.AdapterLuid, wanted)) {
            adapter = std::move(candidate);
            return true;
        }
    }
    return false;
}

bool read_device_luid(
    ID3D11Device* device,
    LUID& luid) noexcept {

    if (!device) return false;
    Microsoft::WRL::ComPtr<IDXGIDevice> dxgiDevice;
    if (FAILED(device->QueryInterface(
            __uuidof(IDXGIDevice),
            reinterpret_cast<void**>(dxgiDevice.ReleaseAndGetAddressOf()))))
        return false;

    Microsoft::WRL::ComPtr<IDXGIAdapter> adapter;
    if (FAILED(dxgiDevice->GetAdapter(adapter.ReleaseAndGetAddressOf())) ||
        !adapter)
        return false;

    DXGI_ADAPTER_DESC desc{};
    if (FAILED(adapter->GetDesc(&desc)))
        return false;

    luid = desc.AdapterLuid;
    return true;
}

bool compile_shader_source(
    const std::string& source,
    const char* source_name,
    const char* target,
    Microsoft::WRL::ComPtr<ID3DBlob>& bytecode) noexcept {

    bytecode.Reset();
    if (source.empty() || !source_name || !target)
        return false;

    Microsoft::WRL::ComPtr<ID3DBlob> diagnostics;
    const HRESULT hr = D3DCompile(
        source.data(), source.size(), source_name,
        nullptr, nullptr, "main", target,
        D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
        0, bytecode.ReleaseAndGetAddressOf(),
        diagnostics.ReleaseAndGetAddressOf());
    return SUCCEEDED(hr) && bytecode;
}

HRESULT create_device(
    IDXGIAdapter* adapter,
    UINT flags,
    Microsoft::WRL::ComPtr<ID3D11Device>& device,
    Microsoft::WRL::ComPtr<ID3D11DeviceContext>& context,
    D3D_FEATURE_LEVEL& feature_level) noexcept {

    constexpr std::array<D3D_FEATURE_LEVEL, 4> kFeatureLevels = {
        D3D_FEATURE_LEVEL_11_1,
        D3D_FEATURE_LEVEL_11_0,
        D3D_FEATURE_LEVEL_10_1,
        D3D_FEATURE_LEVEL_10_0,
    };

    const D3D_DRIVER_TYPE driverType =
        adapter ? D3D_DRIVER_TYPE_UNKNOWN : D3D_DRIVER_TYPE_HARDWARE;

    HRESULT hr = D3D11CreateDevice(
        adapter, driverType, nullptr, flags,
        kFeatureLevels.data(), static_cast<UINT>(kFeatureLevels.size()),
        D3D11_SDK_VERSION, device.ReleaseAndGetAddressOf(),
        &feature_level, context.ReleaseAndGetAddressOf());

    if (hr == E_INVALIDARG) {
        constexpr std::array<D3D_FEATURE_LEVEL, 3> kFallbackLevels = {
            D3D_FEATURE_LEVEL_11_0,
            D3D_FEATURE_LEVEL_10_1,
            D3D_FEATURE_LEVEL_10_0,
        };
        hr = D3D11CreateDevice(
            adapter, driverType, nullptr, flags,
            kFallbackLevels.data(), static_cast<UINT>(kFallbackLevels.size()),
            D3D11_SDK_VERSION, device.ReleaseAndGetAddressOf(),
            &feature_level, context.ReleaseAndGetAddressOf());
    }

    return hr;
}

} // namespace

bool NativeFixedFunctionTransformBuffer::initialize(
    ID3D11Device* device) noexcept {

    shutdown();
    if (!device) return false;

    D3D11_BUFFER_DESC desc{};
    desc.ByteWidth = static_cast<UINT>(16u * sizeof(float));
    desc.Usage = D3D11_USAGE_DYNAMIC;
    desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;

    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer;
    if (FAILED(device->CreateBuffer(
            &desc, nullptr, buffer.ReleaseAndGetAddressOf())) ||
        !buffer)
        return false;

    device_ = device;
    buffer_ = std::move(buffer);
    upload_generation_ = 0;
    return true;
}

bool NativeFixedFunctionTransformBuffer::upload_and_bind(
    ID3D11DeviceContext* context,
    const FixedFunctionTransformConstants& constants) noexcept {

    if (!ready() || !context || !constants.exact())
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != device_.Get())
        return false;

    D3D11_MAPPED_SUBRESOURCE mapped{};
    if (FAILED(context->Map(
            buffer_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &mapped)) ||
        !mapped.pData)
        return false;

    constexpr std::size_t kTransformBytes = 16u * sizeof(float);
    static_assert(kTransformBytes == 64u);
    std::memcpy(
        mapped.pData,
        constants.worldViewProjection.data(),
        kTransformBytes);
    context->Unmap(buffer_.Get(), 0);

    ID3D11Buffer* buffer = buffer_.Get();
    context->VSSetConstantBuffers(0, 1, &buffer);
    ++upload_generation_;
    return true;
}

void NativeFixedFunctionTransformBuffer::shutdown() noexcept {
    buffer_.Reset();
    device_.Reset();
    upload_generation_ = 0;
}

bool NativeFixedFunctionSamplerState::initialize(
    ID3D11Device* device,
    const FixedFunctionStageState& stage) noexcept {

    shutdown();
    if (!device)
        return false;

    const auto translation = translate_fixed_function_sampler(stage);
    if (!translation.exact)
        return false;

    Microsoft::WRL::ComPtr<ID3D11SamplerState> sampler;
    if (FAILED(device->CreateSamplerState(
            &translation.desc, sampler.ReleaseAndGetAddressOf())) ||
        !sampler)
        return false;

    device_ = device;
    sampler_ = std::move(sampler);
    return true;
}

void NativeFixedFunctionSamplerState::shutdown() noexcept {
    sampler_.Reset();
    device_.Reset();
}

bool NativeFixedFunctionTextureView::initialize(
    ID3D11Device* device,
    ID3D11Texture2D* texture,
    D3DFORMAT sourceFormat,
    D3DPOOL sourcePool,
    DWORD sourceUsage) noexcept {

    shutdown();
    if (!device || !texture)
        return false;

    const auto format = translate_resource_format(
        sourceFormat, ResourceRole::Texture);
    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, sourcePool, sourceUsage);
    if (!format.exact || !behavior.descriptorExact ||
        behavior.requiresCpuShadow ||
        (behavior.bindFlags & D3D11_BIND_SHADER_RESOURCE) == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> textureDevice;
    texture->GetDevice(textureDevice.ReleaseAndGetAddressOf());
    if (!textureDevice || textureDevice.Get() != device)
        return false;

    D3D11_TEXTURE2D_DESC desc{};
    texture->GetDesc(&desc);
    if (desc.Width == 0 || desc.Height == 0 || desc.MipLevels == 0 ||
        desc.ArraySize != 1 || desc.SampleDesc.Count != 1 ||
        desc.Format != format.format || desc.Usage != behavior.usage ||
        (desc.BindFlags & behavior.bindFlags) != behavior.bindFlags ||
        desc.CPUAccessFlags != behavior.cpuAccessFlags ||
        (desc.MiscFlags & D3D11_RESOURCE_MISC_TEXTURECUBE) != 0)
        return false;

    D3D11_SHADER_RESOURCE_VIEW_DESC srvDesc{};
    srvDesc.Format = desc.Format;
    srvDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
    srvDesc.Texture2D.MostDetailedMip = 0;
    srvDesc.Texture2D.MipLevels = desc.MipLevels;

    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> srv;
    if (FAILED(device->CreateShaderResourceView(
            texture, &srvDesc, srv.ReleaseAndGetAddressOf())) ||
        !srv)
        return false;

    device_ = device;
    texture_ = texture;
    srv_ = std::move(srv);
    source_format_ = sourceFormat;
    source_pool_ = sourcePool;
    source_usage_ = sourceUsage;
    source_metadata_valid_ = true;
    upload_generation_ = 0;
    return true;
}

bool NativeFixedFunctionTextureView::upload_full_discard(
    ID3D11DeviceContext* context,
    const void* source,
    UINT sourceRowPitch,
    UINT sourceRows) noexcept {

    if (!ready() || !context || !source ||
        sourceRowPitch == 0 || sourceRows == 0)
        return false;

    const auto mutation = translate_texture_mutation(
        source_pool_, source_usage_, D3DLOCK_DISCARD, true);
    if (!mutation.planExact ||
        mutation.kind != TextureMutationUpdateKind::DynamicMapWriteDiscard ||
        mutation.mapType != D3D11_MAP_WRITE_DISCARD)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != device_.Get())
        return false;

    D3D11_TEXTURE2D_DESC desc{};
    texture_->GetDesc(&desc);
    if (desc.MipLevels != 1 || desc.ArraySize != 1 ||
        desc.SampleDesc.Count != 1 ||
        desc.Usage != D3D11_USAGE_DYNAMIC ||
        desc.CPUAccessFlags != D3D11_CPU_ACCESS_WRITE)
        return false;

    UINT rowBytes = 0;
    if (!texture_uncompressed_row_bytes(source_format_, desc.Width, rowBytes) ||
        sourceRows != desc.Height ||
        sourceRowPitch < rowBytes)
        return false;

    D3D11_MAPPED_SUBRESOURCE mapped{};
    if (FAILED(context->Map(
            texture_.Get(), 0, mutation.mapType, 0, &mapped)) ||
        !mapped.pData)
        return false;

    if (mapped.RowPitch < rowBytes) {
        context->Unmap(texture_.Get(), 0);
        return false;
    }

    const auto* sourceBytes = static_cast<const std::uint8_t*>(source);
    auto* destinationBytes = static_cast<std::uint8_t*>(mapped.pData);
    for (UINT row = 0; row < sourceRows; ++row) {
        std::memcpy(
            destinationBytes + static_cast<std::size_t>(row) * mapped.RowPitch,
            sourceBytes + static_cast<std::size_t>(row) * sourceRowPitch,
            rowBytes);
    }
    context->Unmap(texture_.Get(), 0);
    ++upload_generation_;
    return true;
}

bool bind_fixed_function_texture_stage_for_observation(
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture) noexcept {

    if (!context || !sampler.ready() || !texture.ready() ||
        slot >= D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT ||
        slot >= D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT)
        return false;

    ID3D11Device* samplerDevice = sampler.device();
    ID3D11Device* textureDevice = texture.device();
    if (!samplerDevice || !textureDevice || samplerDevice != textureDevice)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != samplerDevice)
        return false;

    ID3D11SamplerState* samplerState = sampler.sampler();
    ID3D11ShaderResourceView* shaderResource = texture.srv();
    if (!samplerState || !shaderResource)
        return false;

    context->PSSetSamplers(slot, 1, &samplerState);
    context->PSSetShaderResources(slot, 1, &shaderResource);

    // D3D11 silently NULLs an SRV when it conflicts with a resource that is
    // already bound for output. Treat that hazard resolution as a failed
    // observation bind instead of reporting a false-positive readiness state.
    Microsoft::WRL::ComPtr<ID3D11SamplerState> boundSampler;
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> boundResource;
    context->PSGetSamplers(
        slot, 1, boundSampler.ReleaseAndGetAddressOf());
    context->PSGetShaderResources(
        slot, 1, boundResource.ReleaseAndGetAddressOf());
    if (boundSampler.Get() != samplerState ||
        boundResource.Get() != shaderResource) {
        ID3D11SamplerState* nullSampler = nullptr;
        ID3D11ShaderResourceView* nullResource = nullptr;
        context->PSSetSamplers(slot, 1, &nullSampler);
        context->PSSetShaderResources(slot, 1, &nullResource);
        return false;
    }

    return true;
}

NativeFixedFunctionTextureStageBindingReadiness
observe_fixed_function_texture_stage_binding(
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture) noexcept {
    NativeFixedFunctionTextureStageBindingReadiness out{};
    out.slot = slot;
    out.textureUploadGeneration = texture.upload_generation();
    out.inputValid = context != nullptr;
    out.slotValid =
        slot < D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT &&
        slot < D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT;
    out.ownersReady = sampler.ready() && texture.ready();

    ID3D11Device* samplerDevice = sampler.device();
    ID3D11Device* textureDevice = texture.device();
    out.devicesMatch =
        samplerDevice != nullptr &&
        textureDevice != nullptr &&
        samplerDevice == textureDevice;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (context)
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextMatches =
        out.devicesMatch &&
        contextDevice &&
        contextDevice.Get() == samplerDevice;

    if (out.inputValid && out.slotValid && out.ownersReady &&
        out.devicesMatch && out.contextMatches) {
        Microsoft::WRL::ComPtr<ID3D11SamplerState> boundSampler;
        Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> boundResource;
        context->PSGetSamplers(
            slot, 1, boundSampler.ReleaseAndGetAddressOf());
        context->PSGetShaderResources(
            slot, 1, boundResource.ReleaseAndGetAddressOf());
        out.boundExact =
            boundSampler.Get() == sampler.sampler() &&
            boundResource.Get() == texture.srv();
    }

    out.ready =
        out.inputValid &&
        out.slotValid &&
        out.ownersReady &&
        out.devicesMatch &&
        out.contextMatches &&
        out.boundExact;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.slot);
        token = mix_readiness_snapshot_token(
            token, out.textureUploadGeneration);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(samplerDevice)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(sampler.sampler())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(texture.srv())));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_texture_stage_binding_snapshot(
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = observe_fixed_function_texture_stage_binding(
        context, slot, sampler, texture);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionTextureBindingSetReadiness
observe_fixed_function_texture_binding_set(
    ID3D11DeviceContext* context,
    std::uint32_t requiredTextureMask,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures) noexcept {
    NativeFixedFunctionTextureBindingSetReadiness out{};
    constexpr std::uint32_t kFixedFunctionStageMask = 0xffu;
    out.requiredTextureMask = requiredTextureMask;
    out.requiredMaskValid =
        requiredTextureMask != 0 &&
        (requiredTextureMask & ~kFixedFunctionStageMask) == 0;
    out.inputValid = context != nullptr && out.requiredMaskValid;
    if (!out.inputValid)
        return out;

    for (UINT slot = 0; slot < 8; ++slot) {
        const std::uint32_t stageBit = 1u << slot;
        if ((requiredTextureMask & stageBit) == 0)
            continue;

        const auto* sampler = samplers[slot];
        const auto* texture = textures[slot];
        if (!sampler || !texture)
            continue;

        const auto stage = observe_fixed_function_texture_stage_binding(
            context, slot, *sampler, *texture);
        if (!stage.ready || stage.snapshotToken == 0)
            continue;

        out.observedTextureMask |= stageBit;
        out.stageSnapshotTokens[slot] = stage.snapshotToken;
    }

    out.allRequiredBoundExact =
        out.observedTextureMask == out.requiredTextureMask;
    out.ready = out.inputValid && out.allRequiredBoundExact;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.requiredTextureMask);
        token = mix_readiness_snapshot_token(token, out.observedTextureMask);
        for (UINT slot = 0; slot < 8; ++slot) {
            const std::uint32_t stageBit = 1u << slot;
            if ((requiredTextureMask & stageBit) == 0)
                continue;
            token = mix_readiness_snapshot_token(token, stageBit);
            token = mix_readiness_snapshot_token(
                token, out.stageSnapshotTokens[slot]);
        }
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_texture_binding_set_snapshot(
    ID3D11DeviceContext* context,
    std::uint32_t requiredTextureMask,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = observe_fixed_function_texture_binding_set(
        context, requiredTextureMask, samplers, textures);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool validate_fixed_function_texture_binding_set_readiness_integrity(
    const NativeFixedFunctionTextureBindingSetReadiness& textureBindings) noexcept {
    constexpr std::uint32_t kFixedFunctionStageMask = 0xffu;
    if (!textureBindings.inputValid ||
        !textureBindings.requiredMaskValid ||
        !textureBindings.allRequiredBoundExact ||
        !textureBindings.ready ||
        textureBindings.snapshotToken == 0 ||
        textureBindings.requiredTextureMask == 0 ||
        (textureBindings.requiredTextureMask & ~kFixedFunctionStageMask) != 0 ||
        textureBindings.observedTextureMask !=
            textureBindings.requiredTextureMask)
        return false;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, textureBindings.requiredTextureMask);
    token = mix_readiness_snapshot_token(
        token, textureBindings.observedTextureMask);
    for (UINT slot = 0; slot < 8; ++slot) {
        const std::uint32_t stageBit = 1u << slot;
        const bool required =
            (textureBindings.requiredTextureMask & stageBit) != 0;
        if (!required) {
            if (textureBindings.stageSnapshotTokens[slot] != 0)
                return false;
            continue;
        }
        if (textureBindings.stageSnapshotTokens[slot] == 0)
            return false;
        token = mix_readiness_snapshot_token(token, stageBit);
        token = mix_readiness_snapshot_token(
            token, textureBindings.stageSnapshotTokens[slot]);
    }
    token = token == 0 ? 1 : token;
    return token == textureBindings.snapshotToken;
}

void NativeFixedFunctionTextureView::shutdown() noexcept {
    srv_.Reset();
    texture_.Reset();
    device_.Reset();
    source_format_ = D3DFMT_UNKNOWN;
    source_pool_ = D3DPOOL_DEFAULT;
    source_usage_ = 0;
    source_metadata_valid_ = false;
    upload_generation_ = 0;
}

bool NativeManagedBufferShadow::initialize(
    ResourceRole role,
    UINT byteWidth,
    DWORD sourceUsage) noexcept {

    shutdown();
    if ((role != ResourceRole::Vertex && role != ResourceRole::Index) ||
        byteWidth == 0)
        return false;

    const auto behavior = translate_resource_behavior(
        role, D3DPOOL_MANAGED, sourceUsage);
    const UINT expectedBind =
        role == ResourceRole::Vertex
            ? D3D11_BIND_VERTEX_BUFFER
            : D3D11_BIND_INDEX_BUFFER;
    if (!behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        behavior.bindFlags != expectedBind)
        return false;

    try {
        shadow_.assign(static_cast<std::size_t>(byteWidth), 0);
    } catch (...) {
        shutdown();
        return false;
    }

    role_ = role;
    source_usage_ = sourceUsage;
    byte_width_ = byteWidth;
    metadata_valid_ = true;
    lifetime_ = {};
    return true;
}

bool NativeManagedBufferShadow::write_range(
    UINT offset,
    const void* source,
    UINT sourceBytes) noexcept {

    if (!ready() || !source || sourceBytes == 0 ||
        offset > byte_width_ || sourceBytes > byte_width_ - offset)
        return false;

    const auto mutation = translate_buffer_mutation(
        role_, D3DPOOL_MANAGED, source_usage_, 0);
    // R125: R121 made ordinary MANAGED buffer mutation plans exact. The
    // dormant R113 CPU shadow must consume that exact plan rather than reject
    // it; R119 mirror readiness still independently rejects stale snapshots.
    if (mutation.kind != BufferMutationUpdateKind::ManagedCpuShadowWrite ||
        !mutation.requiresCpuShadow || !mutation.planExact)
        return false;

    // Until a complete initial image exists, a partial Lock cannot establish
    // deterministic contents for the untouched bytes.
    if (!shadow_valid() &&
        (offset != 0 || sourceBytes != byte_width_))
        return false;

    std::memcpy(
        shadow_.data() + static_cast<std::size_t>(offset),
        source,
        static_cast<std::size_t>(sourceBytes));
    release_mirror();
    lifetime_ = note_managed_shadow_write(lifetime_);
    return true;
}

bool NativeManagedBufferShadow::recreate_and_upload_mirror(
    ID3D11Device* device) noexcept {

    if (!ready() || !shadow_valid() || !device)
        return false;

    const auto behavior = translate_resource_behavior(
        role_, D3DPOOL_MANAGED, source_usage_);
    const UINT expectedBind =
        role_ == ResourceRole::Vertex
            ? D3D11_BIND_VERTEX_BUFFER
            : D3D11_BIND_INDEX_BUFFER;
    if (!behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        behavior.bindFlags != expectedBind)
        return false;

    release_mirror();

    D3D11_BUFFER_DESC desc{};
    desc.ByteWidth = byte_width_;
    desc.Usage = D3D11_USAGE_DEFAULT;
    desc.BindFlags = expectedBind;

    D3D11_SUBRESOURCE_DATA initialData{};
    initialData.pSysMem = shadow_.data();

    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer;
    if (FAILED(device->CreateBuffer(
            &desc, &initialData, buffer.ReleaseAndGetAddressOf())) ||
        !buffer)
        return false;

    mirror_device_ = device;
    mirror_buffer_ = std::move(buffer);
    lifetime_ = note_managed_mirror_upload(lifetime_);
    if (!mirror_ready()) {
        release_mirror();
        return false;
    }
    ++mirror_instance_generation_;
    if (mirror_instance_generation_ == 0)
        ++mirror_instance_generation_;
    return true;
}

bool NativeManagedBufferShadow::mirror_descriptor_exact(
    ID3D11Device* expectedDevice) const noexcept {

    if (!expectedDevice ||
        mirror_device_.Get() != expectedDevice ||
        !mirror_buffer_)
        return false;

    const auto behavior = translate_resource_behavior(
        role_, D3DPOOL_MANAGED, source_usage_);
    const UINT expectedBind =
        role_ == ResourceRole::Vertex
            ? D3D11_BIND_VERTEX_BUFFER
            : D3D11_BIND_INDEX_BUFFER;
    if (!behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        behavior.bindFlags != expectedBind)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> bufferDevice;
    mirror_buffer_->GetDevice(bufferDevice.ReleaseAndGetAddressOf());
    if (!bufferDevice || bufferDevice.Get() != expectedDevice)
        return false;

    D3D11_BUFFER_DESC desc{};
    mirror_buffer_->GetDesc(&desc);
    return desc.ByteWidth == byte_width_ &&
        desc.Usage == behavior.usage &&
        desc.BindFlags == behavior.bindFlags &&
        desc.CPUAccessFlags == behavior.cpuAccessFlags &&
        desc.MiscFlags == 0 &&
        desc.StructureByteStride == 0;
}

NativeManagedBufferMirrorReadiness
NativeManagedBufferShadow::mirror_readiness(
    ID3D11Device* expectedDevice) const noexcept {

    NativeManagedBufferMirrorReadiness out{};
    out.role = role_;
    out.deviceGeneration = lifetime_.deviceGeneration;
    out.shadowVersion = lifetime_.cpuShadowVersion;
    out.mirrorGeneration = lifetime_.mirrorGeneration;
    out.mirrorShadowVersion = lifetime_.mirrorShadowVersion;
    out.mirrorInstanceGeneration = mirror_instance_generation_;

    out.inputValid = ready() && expectedDevice != nullptr;
    if (!out.inputValid)
        return out;

    out.shadowValid = lifetime_.cpuShadowValid;
    out.resourcesOwned = mirror_device_ && mirror_buffer_;
    out.lifetimeCurrent = managed_mirror_ready(lifetime_);
    out.deviceMatches =
        out.resourcesOwned && mirror_device_.Get() == expectedDevice;
    if (out.deviceMatches) {
        Microsoft::WRL::ComPtr<ID3D11Device> bufferDevice;
        mirror_buffer_->GetDevice(bufferDevice.ReleaseAndGetAddressOf());
        out.deviceMatches =
            bufferDevice && bufferDevice.Get() == expectedDevice;
    }
    out.descriptorExact =
        out.deviceMatches && mirror_descriptor_exact(expectedDevice);
    const auto mutationPlan = translate_buffer_mutation(
        role_, D3DPOOL_MANAGED, source_usage_, 0);
    out.mutationPlanExact =
        mutationPlan.planExact &&
        mutationPlan.requiresCpuShadow &&
        mutationPlan.kind == BufferMutationUpdateKind::ManagedCpuShadowWrite;
    out.ready =
        out.shadowValid &&
        out.resourcesOwned &&
        out.lifetimeCurrent &&
        out.deviceMatches &&
        out.descriptorExact &&
        out.mutationPlanExact &&
        out.mirrorInstanceGeneration != 0;

    if (out.ready) {
        std::uint64_t snapshotToken = 0xcbf29ce484222325ull;
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(mirror_buffer_.Get())));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, static_cast<std::uint32_t>(role_));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, source_usage_);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, byte_width_);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.mutationPlanExact ? 1u : 0u);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.deviceGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.shadowVersion);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.mirrorGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.mirrorShadowVersion);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.mirrorInstanceGeneration);
        out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken;
    }
    return out;
}

bool NativeManagedBufferShadow::validate_mirror_readiness_snapshot(
    ID3D11Device* expectedDevice,
    std::uint64_t snapshotToken) const noexcept {

    if (snapshotToken == 0)
        return false;
    const auto current = mirror_readiness(expectedDevice);
    return current.ready && current.snapshotToken == snapshotToken;
}

void NativeManagedBufferShadow::observe_device_reset() noexcept {
    release_mirror();
    lifetime_ = advance_managed_device_generation(lifetime_);
}

void NativeManagedBufferShadow::release_mirror() noexcept {
    mirror_buffer_.Reset();
    mirror_device_.Reset();
    lifetime_.mirrorValid = false;
}

void NativeManagedBufferShadow::shutdown() noexcept {
    release_mirror();
    role_ = ResourceRole::Vertex;
    source_usage_ = 0;
    byte_width_ = 0;
    metadata_valid_ = false;
    shadow_.clear();
    lifetime_ = {};
    mirror_instance_generation_ = 0;
}

bool NativeManagedTextureShadow::initialize(
    D3DFORMAT sourceFormat,
    UINT width,
    UINT height) noexcept {

    shutdown();
    if (width == 0 || height == 0)
        return false;

    const auto format = translate_resource_format(
        sourceFormat, ResourceRole::Texture);
    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, D3DPOOL_MANAGED, 0);
    if (!format.exact || !behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow)
        return false;

    UINT rowBytes = 0;
    if (!texture_uncompressed_row_bytes(sourceFormat, width, rowBytes))
        return false;

    if (static_cast<std::size_t>(height) >
        (std::numeric_limits<std::size_t>::max)() / rowBytes)
        return false;
    const std::size_t shadowBytes =
        static_cast<std::size_t>(rowBytes) * height;

    try {
        shadow_.assign(shadowBytes, 0);
    } catch (...) {
        shutdown();
        return false;
    }

    source_format_ = sourceFormat;
    width_ = width;
    height_ = height;
    row_bytes_ = rowBytes;
    lifetime_ = {};
    return true;
}

bool NativeManagedTextureShadow::write_full(
    const void* source,
    UINT sourceRowPitch,
    UINT sourceRows) noexcept {

    if (!ready() || source_lock_active_ || source_unlock_staged_ || !source ||
        sourceRows != height_ || sourceRowPitch < row_bytes_)
        return false;

    const auto mutation = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, 0, true);
    if (mutation.kind != TextureMutationUpdateKind::ManagedCpuShadowWrite ||
        !mutation.requiresCpuShadow || mutation.planExact)
        return false;

    const auto* sourceBytes = static_cast<const std::uint8_t*>(source);
    for (UINT row = 0; row < height_; ++row) {
        std::memcpy(
            shadow_.data() + static_cast<std::size_t>(row) * row_bytes_,
            sourceBytes + static_cast<std::size_t>(row) * sourceRowPitch,
            row_bytes_);
    }

    release_mirror();
    lifetime_ = note_managed_shadow_write(lifetime_);
    return true;
}

bool NativeManagedTextureShadow::read_full(
    void* destination,
    UINT destinationRowPitch,
    UINT destinationRows) const noexcept {

    if (!ready() || source_lock_active_ || source_unlock_staged_ ||
        !shadow_valid() || !destination ||
        destinationRows != height_ || destinationRowPitch < row_bytes_)
        return false;

    const auto mutation = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, D3DLOCK_READONLY, true);
    if (mutation.kind != TextureMutationUpdateKind::ManagedCpuShadowRead ||
        !mutation.requiresCpuShadow || mutation.planExact)
        return false;

    auto* destinationBytes = static_cast<std::uint8_t*>(destination);
    for (UINT row = 0; row < height_; ++row) {
        std::memcpy(
            destinationBytes + static_cast<std::size_t>(row) * destinationRowPitch,
            shadow_.data() + static_cast<std::size_t>(row) * row_bytes_,
            row_bytes_);
    }
    return true;
}

bool NativeManagedTextureShadow::recreate_and_upload_mirror(
    ID3D11Device* device) noexcept {

    if (!ready() || source_lock_active_ || source_unlock_staged_ ||
        !shadow_valid() || !device)
        return false;

    const auto format = translate_resource_format(
        source_format_, ResourceRole::Texture);
    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, D3DPOOL_MANAGED, 0);
    if (!format.exact || !behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        (behavior.bindFlags & D3D11_BIND_SHADER_RESOURCE) == 0)
        return false;

    release_mirror();

    D3D11_TEXTURE2D_DESC desc{};
    desc.Width = width_;
    desc.Height = height_;
    desc.MipLevels = 1;
    desc.ArraySize = 1;
    desc.Format = format.format;
    desc.SampleDesc.Count = 1;
    desc.Usage = D3D11_USAGE_DEFAULT;
    desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;

    D3D11_SUBRESOURCE_DATA initialData{};
    initialData.pSysMem = shadow_.data();
    initialData.SysMemPitch = row_bytes_;

    Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
    if (FAILED(device->CreateTexture2D(
            &desc, &initialData, texture.ReleaseAndGetAddressOf())) ||
        !texture)
        return false;

    D3D11_SHADER_RESOURCE_VIEW_DESC srvDesc{};
    srvDesc.Format = desc.Format;
    srvDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
    srvDesc.Texture2D.MostDetailedMip = 0;
    srvDesc.Texture2D.MipLevels = 1;

    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> srv;
    if (FAILED(device->CreateShaderResourceView(
            texture.Get(), &srvDesc, srv.ReleaseAndGetAddressOf())) ||
        !srv)
        return false;

    mirror_device_ = device;
    mirror_texture_ = std::move(texture);
    mirror_srv_ = std::move(srv);
    note_mirror_uploaded();
    if (!mirror_ready()) {
        release_mirror();
        return false;
    }
    ++mirror_instance_generation_;
    if (mirror_instance_generation_ == 0)
        ++mirror_instance_generation_;
    return true;
}

bool NativeManagedTextureShadow::mirror_descriptor_exact(
    ID3D11Device* expectedDevice) const noexcept {
    if (!expectedDevice ||
        mirror_device_.Get() != expectedDevice ||
        !mirror_texture_ || !mirror_srv_)
        return false;

    const auto format = translate_resource_format(
        source_format_, ResourceRole::Texture);
    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, D3DPOOL_MANAGED, 0);
    if (!format.exact || !behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        behavior.usage != D3D11_USAGE_DEFAULT ||
        behavior.cpuAccessFlags != 0 ||
        behavior.bindFlags != D3D11_BIND_SHADER_RESOURCE)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> textureDevice;
    mirror_texture_->GetDevice(textureDevice.ReleaseAndGetAddressOf());
    if (!textureDevice || textureDevice.Get() != expectedDevice)
        return false;

    D3D11_TEXTURE2D_DESC textureDesc{};
    mirror_texture_->GetDesc(&textureDesc);
    if (textureDesc.Width != width_ ||
        textureDesc.Height != height_ ||
        textureDesc.MipLevels != 1 ||
        textureDesc.ArraySize != 1 ||
        textureDesc.Format != format.format ||
        textureDesc.SampleDesc.Count != 1 ||
        textureDesc.SampleDesc.Quality != 0 ||
        textureDesc.Usage != behavior.usage ||
        textureDesc.BindFlags != behavior.bindFlags ||
        textureDesc.CPUAccessFlags != behavior.cpuAccessFlags ||
        textureDesc.MiscFlags != 0)
        return false;

    D3D11_SHADER_RESOURCE_VIEW_DESC srvDesc{};
    mirror_srv_->GetDesc(&srvDesc);
    if (srvDesc.Format != textureDesc.Format ||
        srvDesc.ViewDimension != D3D11_SRV_DIMENSION_TEXTURE2D ||
        srvDesc.Texture2D.MostDetailedMip != 0 ||
        srvDesc.Texture2D.MipLevels != 1)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Resource> viewResource;
    mirror_srv_->GetResource(viewResource.ReleaseAndGetAddressOf());
    if (!viewResource)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Texture2D> viewTexture;
    if (FAILED(viewResource.As(&viewTexture)) ||
        !viewTexture || viewTexture.Get() != mirror_texture_.Get())
        return false;

    return true;
}

bool NativeManagedTextureShadow::begin_source_lock(
    UINT level,
    const RECT* sourceRect,
    DWORD lockFlags,
    const D3DLOCKED_RECT& lockedRect) noexcept {

    if (!ready() || source_lock_active_ || source_unlock_staged_ ||
        level != 0 || sourceRect != nullptr ||
        !lockedRect.pBits || lockedRect.Pitch <= 0)
        return false;

    const auto mutation = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, lockFlags, true);
    if (mutation.kind != TextureMutationUpdateKind::ManagedCpuShadowWrite ||
        !mutation.requiresCpuShadow || mutation.planExact)
        return false;

    const UINT pitch = static_cast<UINT>(lockedRect.Pitch);
    if (pitch < row_bytes_)
        return false;

    // A successful writable LockRect means the source can diverge before the
    // matching UnlockRect. Do not expose a previously uploaded mirror while
    // that source memory is mutable.
    release_mirror();
    source_lock_bits_ = lockedRect.pBits;
    source_lock_pitch_ = pitch;
    source_lock_level_ = level;
    source_lock_active_ = true;
    return true;
}

bool NativeManagedTextureShadow::stage_source_unlock(UINT level) noexcept {
    if (!source_lock_active_ || source_unlock_staged_ ||
        level != source_lock_level_ || !source_lock_bits_ ||
        source_lock_pitch_ < row_bytes_)
        return false;

    try {
        pending_unlock_.resize(shadow_.size());
    } catch (...) {
        invalidate_shadow();
        clear_source_lock();
        clear_unlock_stage();
        return false;
    }

    const auto* sourceBytes =
        static_cast<const std::uint8_t*>(source_lock_bits_);
    for (UINT row = 0; row < height_; ++row) {
        std::memcpy(
            pending_unlock_.data() +
                static_cast<std::size_t>(row) * row_bytes_,
            sourceBytes +
                static_cast<std::size_t>(row) * source_lock_pitch_,
            row_bytes_);
    }

    clear_source_lock();
    source_unlock_level_ = level;
    source_unlock_staged_ = true;
    return true;
}

bool NativeManagedTextureShadow::finish_source_unlock(
    UINT level,
    HRESULT unlockResult) noexcept {

    if (!source_unlock_staged_ || level != source_unlock_level_)
        return false;

    if (FAILED(unlockResult) || !ready() ||
        pending_unlock_.size() != shadow_.size()) {
        clear_unlock_stage();
        invalidate_shadow();
        return false;
    }

    std::memcpy(
        shadow_.data(), pending_unlock_.data(), pending_unlock_.size());
    clear_unlock_stage();
    release_mirror();
    lifetime_ = note_managed_shadow_write(lifetime_);
    return true;
}

bool NativeManagedTextureShadow::commit_source_unlock(UINT level) noexcept {
    return stage_source_unlock(level) &&
        finish_source_unlock(level, S_OK);
}

void NativeManagedTextureShadow::cancel_source_lock() noexcept {
    clear_source_lock();
    clear_unlock_stage();
}

void NativeManagedTextureShadow::note_mirror_uploaded() noexcept {
    if (!mirror_device_ || !mirror_texture_ || !mirror_srv_)
        return;
    lifetime_ = note_managed_mirror_upload(lifetime_);
}

void NativeManagedTextureShadow::observe_device_reset() noexcept {
    clear_source_lock();
    clear_unlock_stage();
    release_mirror();
    lifetime_ = advance_managed_device_generation(lifetime_);
}

bool NativeManagedTextureShadow::invalidate_external_mutation() noexcept {
    const bool wasValid = lifetime_.cpuShadowValid;
    clear_source_lock();
    clear_unlock_stage();
    invalidate_shadow();
    return wasValid;
}

void NativeManagedTextureShadow::release_mirror() noexcept {
    mirror_srv_.Reset();
    mirror_texture_.Reset();
    mirror_device_.Reset();
    lifetime_.mirrorValid = false;
}

void NativeManagedTextureShadow::invalidate_shadow() noexcept {
    release_mirror();
    lifetime_.cpuShadowValid = false;
    lifetime_.mirrorValid = false;
}

void NativeManagedTextureShadow::clear_source_lock() noexcept {
    source_lock_bits_ = nullptr;
    source_lock_pitch_ = 0;
    source_lock_level_ = 0;
    source_lock_active_ = false;
}

void NativeManagedTextureShadow::clear_unlock_stage() noexcept {
    pending_unlock_.clear();
    source_unlock_level_ = 0;
    source_unlock_staged_ = false;
}

void NativeManagedTextureShadow::shutdown() noexcept {
    clear_source_lock();
    clear_unlock_stage();
    release_mirror();
    source_format_ = D3DFMT_UNKNOWN;
    width_ = 0;
    height_ = 0;
    row_bytes_ = 0;
    shadow_.clear();
    lifetime_ = {};
    mirror_instance_generation_ = 0;
}

bool NativeManagedTextureRegistry::register_texture(
    const void* textureKey,
    D3DFORMAT sourceFormat,
    UINT width,
    UINT height,
    UINT levels,
    DWORD usage,
    D3DPOOL pool) noexcept {

    if (!textureKey || levels != 1)
        return false;

    const auto behavior = translate_resource_behavior(
        ResourceRole::Texture, pool, usage);
    if (!behavior.descriptorExact ||
        behavior.lifetime != ResourceMirrorLifetime::ManagedCpuShadow ||
        !behavior.requiresCpuShadow ||
        pool != D3DPOOL_MANAGED || usage != 0)
        return false;

    try {
        auto shadow = std::make_unique<NativeManagedTextureShadow>();
        if (!shadow->initialize(sourceFormat, width, height))
            return false;

        std::lock_guard<std::mutex> lock(mutex_);
        shadows_[textureKey] = std::move(shadow);
        advance_membership_generation_locked();
        return true;
    } catch (...) {
        return false;
    }
}

NativeManagedTextureShadow* NativeManagedTextureRegistry::find_locked(
    const void* textureKey) noexcept {
    const auto it = shadows_.find(textureKey);
    return it == shadows_.end() ? nullptr : it->second.get();
}

const NativeManagedTextureShadow* NativeManagedTextureRegistry::find_locked(
    const void* textureKey) const noexcept {
    const auto it = shadows_.find(textureKey);
    return it == shadows_.end() ? nullptr : it->second.get();
}

void NativeManagedTextureRegistry::advance_membership_generation_locked() noexcept {
    ++membership_generation_;
    if (membership_generation_ == 0)
        ++membership_generation_;
}

bool NativeManagedTextureRegistry::begin_source_lock(
    const void* textureKey,
    UINT level,
    const RECT* sourceRect,
    DWORD lockFlags,
    const D3DLOCKED_RECT& lockedRect) noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow &&
        shadow->begin_source_lock(level, sourceRect, lockFlags, lockedRect);
}

bool NativeManagedTextureRegistry::stage_source_unlock(
    const void* textureKey,
    UINT level) noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow && shadow->stage_source_unlock(level);
}

bool NativeManagedTextureRegistry::finish_source_unlock(
    const void* textureKey,
    UINT level,
    HRESULT unlockResult) noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow &&
        shadow->finish_source_unlock(level, unlockResult);
}

bool NativeManagedTextureRegistry::invalidate_external_mutation(
    const void* textureKey) noexcept {
    if (!textureKey)
        return false;
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow && shadow->invalidate_external_mutation();
}

bool NativeManagedTextureRegistry::recreate_and_upload_mirror_for_observation(
    const void* textureKey,
    ID3D11Device* device) noexcept {
    if (!textureKey || !device)
        return false;
    std::lock_guard<std::mutex> lock(mutex_);
    auto* shadow = find_locked(textureKey);
    return shadow && shadow->recreate_and_upload_mirror(device);
}

NativeManagedTextureMirrorReadiness
NativeManagedTextureRegistry::mirror_readiness(
    const void* textureKey,
    ID3D11Device* expectedDevice) const noexcept {
    NativeManagedTextureMirrorReadiness out{};
    if (!textureKey)
        return out;

    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    if (!shadow)
        return out;

    out.registered = true;
    out.shadowValid = shadow->shadow_valid();
    const auto& lifetime = shadow->lifetime_state();
    out.deviceGeneration = lifetime.deviceGeneration;
    out.shadowVersion = lifetime.cpuShadowVersion;
    out.mirrorGeneration = lifetime.mirrorGeneration;
    out.mirrorShadowVersion = lifetime.mirrorShadowVersion;
    out.resourcesOwned =
        shadow->mirror_device() != nullptr &&
        shadow->mirror_texture() != nullptr &&
        shadow->mirror_srv() != nullptr;
    out.lifetimeCurrent = managed_mirror_ready(lifetime);
    out.deviceMatches =
        expectedDevice != nullptr &&
        shadow->mirror_device() == expectedDevice;
    out.descriptorExact =
        shadow->mirror_descriptor_exact(expectedDevice);
    out.ready =
        shadow->mirror_ready() &&
        out.resourcesOwned &&
        out.lifetimeCurrent &&
        out.deviceMatches &&
        out.descriptorExact;
    return out;
}

NativeManagedTextureStageReadiness
NativeManagedTextureRegistry::mirror_readiness_for_stages(
    const void* const* textureKeys,
    std::size_t textureCount,
    std::uint32_t requiredMask,
    ID3D11Device* expectedDevice) const noexcept {
    NativeManagedTextureStageReadiness out{};
    out.requiredMask = requiredMask;
    out.pendingMask = requiredMask;

    if (textureCount > 32 ||
        (textureCount != 0 && textureKeys == nullptr))
        return out;

    const std::uint32_t validMask =
        textureCount == 32
        ? 0xffffffffu
        : (textureCount == 0
            ? 0u
            : ((1u << static_cast<std::uint32_t>(textureCount)) - 1u));
    if ((requiredMask & ~validMask) != 0 ||
        (requiredMask != 0 && expectedDevice == nullptr))
        return out;

    out.inputValid = true;
    std::uint64_t snapshotToken = 0xcbf29ce484222325ull;
    snapshotToken = mix_readiness_snapshot_token(
        snapshotToken, static_cast<std::uint64_t>(requiredMask));
    snapshotToken = mix_readiness_snapshot_token(
        snapshotToken,
        static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(expectedDevice)));

    std::lock_guard<std::mutex> lock(mutex_);
    snapshotToken = mix_readiness_snapshot_token(
        snapshotToken,
        static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(this)));
    snapshotToken = mix_readiness_snapshot_token(
        snapshotToken, membership_generation_);
    for (std::size_t stage = 0; stage < textureCount; ++stage) {
        const auto bit = static_cast<std::uint32_t>(1u << stage);
        if ((requiredMask & bit) == 0)
            continue;

        const auto* shadow = find_locked(textureKeys[stage]);
        if (!shadow)
            continue;

        out.registeredMask |= bit;
        if (shadow->shadow_valid())
            out.shadowValidMask |= bit;

        const auto& lifetime = shadow->lifetime_state();
        const bool resourcesOwned =
            shadow->mirror_device() != nullptr &&
            shadow->mirror_texture() != nullptr &&
            shadow->mirror_srv() != nullptr;
        const bool lifetimeCurrent = managed_mirror_ready(lifetime);
        const bool deviceMatches =
            shadow->mirror_device() == expectedDevice;
        const bool descriptorExact =
            shadow->mirror_descriptor_exact(expectedDevice);

        if (resourcesOwned)
            out.resourcesOwnedMask |= bit;
        if (lifetimeCurrent)
            out.lifetimeCurrentMask |= bit;
        if (deviceMatches)
            out.deviceMatchesMask |= bit;
        if (descriptorExact)
            out.descriptorExactMask |= bit;
        if (shadow->mirror_ready() &&
            resourcesOwned &&
            lifetimeCurrent &&
            deviceMatches &&
            descriptorExact)
            out.readyMask |= bit;

        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, static_cast<std::uint64_t>(stage));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(textureKeys[stage])));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, lifetime.deviceGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, lifetime.cpuShadowVersion);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, lifetime.mirrorGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, lifetime.mirrorShadowVersion);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, shadow->mirror_instance_generation());
    }

    out.pendingMask = out.requiredMask & ~out.readyMask;
    out.allRequiredReady = out.pendingMask == 0;
    if (out.allRequiredReady && out.requiredMask != 0) {
        out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken;
    }
    return out;
}

bool NativeManagedTextureRegistry::validate_mirror_readiness_snapshot_for_stages(
    const void* const* textureKeys,
    std::size_t textureCount,
    std::uint32_t requiredMask,
    ID3D11Device* expectedDevice,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0 || requiredMask == 0)
        return false;

    const auto current = mirror_readiness_for_stages(
        textureKeys, textureCount, requiredMask, expectedDevice);
    return current.inputValid &&
        current.allRequiredReady &&
        current.snapshotToken == snapshotToken;
}

void NativeManagedTextureRegistry::observe_device_reset() noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& entry : shadows_) {
        if (entry.second)
            entry.second->observe_device_reset();
    }
}

void NativeManagedTextureRegistry::forget_texture(
    const void* textureKey) noexcept {
    if (!textureKey)
        return;
    std::lock_guard<std::mutex> lock(mutex_);
    const auto it = shadows_.find(textureKey);
    if (it == shadows_.end())
        return;
    if (it->second)
        it->second->shutdown();
    shadows_.erase(it);
    advance_membership_generation_locked();
}

void NativeManagedTextureRegistry::clear() noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    if (shadows_.empty())
        return;
    for (auto& entry : shadows_) {
        if (entry.second)
            entry.second->shutdown();
    }
    shadows_.clear();
    advance_membership_generation_locked();
}

std::size_t NativeManagedTextureRegistry::size() const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    return shadows_.size();
}

bool NativeManagedTextureRegistry::contains(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    return find_locked(textureKey) != nullptr;
}

bool NativeManagedTextureRegistry::shadow_valid(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow && shadow->shadow_valid();
}

std::uint64_t NativeManagedTextureRegistry::shadow_version(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow ? shadow->shadow_version() : 0;
}

std::uint64_t NativeManagedTextureRegistry::device_generation(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow ? shadow->device_generation() : 0;
}

bool NativeManagedTextureRegistry::source_lock_active(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow && shadow->source_lock_active();
}

bool NativeManagedTextureRegistry::source_unlock_staged(
    const void* textureKey) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow && shadow->source_unlock_staged();
}

bool NativeManagedTextureRegistry::read_shadow(
    const void* textureKey,
    void* destination,
    UINT destinationRowPitch,
    UINT destinationRows) const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto* shadow = find_locked(textureKey);
    return shadow && shadow->read_full(
        destination, destinationRowPitch, destinationRows);
}

bool NativeFixedFunctionRenderStateBundle::initialize(
    ID3D11Device* device,
    const PipelineTranslation& translation) noexcept {

    shutdown();
    const auto translationIdentity =
        hash_pipeline_render_state_identity(translation);
    if (!device || translationIdentity == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3D11BlendState> blendState;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilState> depthStencilState;
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> rasterizerState;
    if (FAILED(device->CreateBlendState(
            &translation.blend,
            blendState.ReleaseAndGetAddressOf())) ||
        !blendState ||
        FAILED(device->CreateDepthStencilState(
            &translation.depth_stencil,
            depthStencilState.ReleaseAndGetAddressOf())) ||
        !depthStencilState ||
        FAILED(device->CreateRasterizerState(
            &translation.rasterizer,
            rasterizerState.ReleaseAndGetAddressOf())) ||
        !rasterizerState)
        return false;

    device_ = device;
    blend_state_ = std::move(blendState);
    depth_stencil_state_ = std::move(depthStencilState);
    rasterizer_state_ = std::move(rasterizerState);
    stencil_ref_ = translation.stencil_ref;
    translation_identity_ = translationIdentity;
    ++bundle_generation_;
    if (bundle_generation_ == 0)
        ++bundle_generation_;
    return true;
}

NativeFixedFunctionRenderStateReadiness
NativeFixedFunctionRenderStateBundle::translation_readiness(
    ID3D11Device* expectedDevice,
    const PipelineTranslation& translation) const noexcept {
    NativeFixedFunctionRenderStateReadiness out{};
    const auto translationIdentity =
        hash_pipeline_render_state_identity(translation);
    if (!expectedDevice || translationIdentity == 0)
        return out;

    out.inputValid = true;
    out.bundleReady = ready();
    out.bundleGeneration = bundle_generation_;
    out.translationIdentity = translationIdentity;
    out.translationMatches =
        translation_identity_ != 0 &&
        translation_identity_ == translationIdentity &&
        stencil_ref_ == translation.stencil_ref;

    if (out.bundleReady) {
        Microsoft::WRL::ComPtr<ID3D11Device> blendDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> depthDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> rasterDevice;
        blend_state_->GetDevice(blendDevice.ReleaseAndGetAddressOf());
        depth_stencil_state_->GetDevice(depthDevice.ReleaseAndGetAddressOf());
        rasterizer_state_->GetDevice(rasterDevice.ReleaseAndGetAddressOf());
        out.deviceMatches =
            device_.Get() == expectedDevice &&
            blendDevice.Get() == expectedDevice &&
            depthDevice.Get() == expectedDevice &&
            rasterDevice.Get() == expectedDevice;
    }

    out.ready =
        out.bundleReady &&
        out.deviceMatches &&
        out.translationMatches;
    if (out.ready) {
        std::uint64_t snapshotToken = 0xcbf29ce484222325ull;
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            reinterpret_cast<std::uintptr_t>(expectedDevice));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, translationIdentity);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, bundle_generation_);
        out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken;
    }
    return out;
}

bool NativeFixedFunctionRenderStateBundle::validate_translation_snapshot(
    ID3D11Device* expectedDevice,
    const PipelineTranslation& translation,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        translation_readiness(expectedDevice, translation);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool NativeFixedFunctionRenderStateBundle::validate_readiness_snapshot(
    ID3D11Device* expectedDevice,
    const NativeFixedFunctionRenderStateReadiness& readiness) const noexcept {
    if (!expectedDevice ||
        !readiness.inputValid ||
        !readiness.bundleReady ||
        !readiness.deviceMatches ||
        !readiness.translationMatches ||
        !readiness.ready ||
        readiness.bundleGeneration == 0 ||
        readiness.translationIdentity == 0 ||
        readiness.snapshotToken == 0 ||
        !ready() ||
        device_.Get() != expectedDevice ||
        readiness.bundleGeneration != bundle_generation_ ||
        readiness.translationIdentity != translation_identity_)
        return false;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, reinterpret_cast<std::uintptr_t>(expectedDevice));
    token = mix_readiness_snapshot_token(token, translation_identity_);
    token = mix_readiness_snapshot_token(token, bundle_generation_);
    token = token == 0 ? 1 : token;
    return token == readiness.snapshotToken;
}

void NativeFixedFunctionRenderStateBundle::shutdown() noexcept {
    rasterizer_state_.Reset();
    depth_stencil_state_.Reset();
    blend_state_.Reset();
    device_.Reset();
    stencil_ref_ = 0;
    translation_identity_ = 0;
}

bool NativeFixedFunctionPipelineBundle::initialize(
    ID3D11Device* device,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype) noexcept {

    shutdown();
    const auto inputLayoutIdentity =
        hash_pipeline_input_layout_identity(layout);
    if (!device || inputLayoutIdentity == 0 ||
        !vertexPrototype.generated() || !pixelPrototype.generated() ||
        vertexPrototype.sourceHash == 0 || pixelPrototype.sourceHash == 0)
        return false;

    Microsoft::WRL::ComPtr<ID3DBlob> vertexBytecode;
    Microsoft::WRL::ComPtr<ID3DBlob> pixelBytecode;
    if (!compile_shader_source(
            vertexPrototype.source,
            "OutRunR97FixedFunctionVertexShader",
            "vs_4_0", vertexBytecode) ||
        !compile_shader_source(
            pixelPrototype.source,
            "OutRunR97FixedFunctionPixelShader",
            "ps_4_0", pixelBytecode))
        return false;

    Microsoft::WRL::ComPtr<ID3D11VertexShader> vertexShader;
    if (FAILED(device->CreateVertexShader(
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(), nullptr,
            vertexShader.ReleaseAndGetAddressOf())) ||
        !vertexShader)
        return false;

    Microsoft::WRL::ComPtr<ID3D11InputLayout> inputLayout;
    if (FAILED(device->CreateInputLayout(
            layout.elements.data(), layout.elementCount,
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(),
            inputLayout.ReleaseAndGetAddressOf())) ||
        !inputLayout)
        return false;

    Microsoft::WRL::ComPtr<ID3D11PixelShader> pixelShader;
    if (FAILED(device->CreatePixelShader(
            pixelBytecode->GetBufferPointer(),
            pixelBytecode->GetBufferSize(), nullptr,
            pixelShader.ReleaseAndGetAddressOf())) ||
        !pixelShader)
        return false;

    if (!transform_buffer_.initialize(device)) {
        shutdown();
        return false;
    }

    device_ = device;
    vertex_shader_ = std::move(vertexShader);
    pixel_shader_ = std::move(pixelShader);
    input_layout_ = std::move(inputLayout);
    input_layout_identity_ = inputLayoutIdentity;
    vertex_shader_source_hash_ = vertexPrototype.sourceHash;
    pixel_shader_source_hash_ = pixelPrototype.sourceHash;
    ++bundle_generation_;
    if (bundle_generation_ == 0)
        ++bundle_generation_;
    return true;
}

NativeFixedFunctionPipelineReadiness
NativeFixedFunctionPipelineBundle::translation_readiness(
    ID3D11Device* expectedDevice,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype) const noexcept {
    NativeFixedFunctionPipelineReadiness out{};
    const auto inputLayoutIdentity =
        hash_pipeline_input_layout_identity(layout);
    if (!expectedDevice || inputLayoutIdentity == 0 ||
        !vertexPrototype.generated() || !pixelPrototype.generated() ||
        vertexPrototype.sourceHash == 0 || pixelPrototype.sourceHash == 0)
        return out;

    out.inputValid = true;
    out.bundleReady = ready();
    out.bundleGeneration = bundle_generation_;
    out.inputLayoutMatches =
        input_layout_identity_ != 0 &&
        input_layout_identity_ == inputLayoutIdentity;
    out.vertexShaderMatches =
        vertex_shader_source_hash_ != 0 &&
        vertex_shader_source_hash_ == vertexPrototype.sourceHash;
    out.pixelShaderMatches =
        pixel_shader_source_hash_ != 0 &&
        pixel_shader_source_hash_ == pixelPrototype.sourceHash;

    if (out.bundleReady) {
        Microsoft::WRL::ComPtr<ID3D11Device> vertexDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> pixelDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> layoutDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> transformDevice;
        vertex_shader_->GetDevice(vertexDevice.ReleaseAndGetAddressOf());
        pixel_shader_->GetDevice(pixelDevice.ReleaseAndGetAddressOf());
        input_layout_->GetDevice(layoutDevice.ReleaseAndGetAddressOf());
        transform_buffer_.buffer()->GetDevice(
            transformDevice.ReleaseAndGetAddressOf());
        out.deviceMatches =
            device_.Get() == expectedDevice &&
            vertexDevice.Get() == expectedDevice &&
            pixelDevice.Get() == expectedDevice &&
            layoutDevice.Get() == expectedDevice &&
            transformDevice.Get() == expectedDevice;
    }

    out.ready =
        out.bundleReady &&
        out.deviceMatches &&
        out.inputLayoutMatches &&
        out.vertexShaderMatches &&
        out.pixelShaderMatches &&
        out.bundleGeneration != 0;
    if (out.ready) {
        std::uint64_t snapshotToken = 0xcbf29ce484222325ull;
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(this)));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken,
            static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(expectedDevice)));
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, out.bundleGeneration);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, input_layout_identity_);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, vertex_shader_source_hash_);
        snapshotToken = mix_readiness_snapshot_token(
            snapshotToken, pixel_shader_source_hash_);
        out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken;
    }
    return out;
}

bool NativeFixedFunctionPipelineBundle::validate_translation_snapshot(
    ID3D11Device* expectedDevice,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = translation_readiness(
        expectedDevice, layout, vertexPrototype, pixelPrototype);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool NativeFixedFunctionPipelineBundle::bind_for_observation(
    ID3D11DeviceContext* context,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    std::uint64_t snapshotToken) const noexcept {

    if (!context || !ready() || snapshotToken == 0 ||
        !validate_translation_snapshot(
            device_.Get(), layout, vertexPrototype, pixelPrototype,
            snapshotToken))
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != device_.Get())
        return false;

    context->IASetInputLayout(input_layout_.Get());
    context->VSSetShader(vertex_shader_.Get(), nullptr, 0);
    context->PSSetShader(pixel_shader_.Get(), nullptr, 0);

    Microsoft::WRL::ComPtr<ID3D11InputLayout> boundInputLayout;
    Microsoft::WRL::ComPtr<ID3D11VertexShader> boundVertexShader;
    Microsoft::WRL::ComPtr<ID3D11PixelShader> boundPixelShader;
    context->IAGetInputLayout(boundInputLayout.ReleaseAndGetAddressOf());
    context->VSGetShader(
        boundVertexShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
    context->PSGetShader(
        boundPixelShader.ReleaseAndGetAddressOf(), nullptr, nullptr);

    if (boundInputLayout.Get() != input_layout_.Get() ||
        boundVertexShader.Get() != vertex_shader_.Get() ||
        boundPixelShader.Get() != pixel_shader_.Get()) {
        context->IASetInputLayout(nullptr);
        context->VSSetShader(nullptr, nullptr, 0);
        context->PSSetShader(nullptr, nullptr, 0);
        return false;
    }
    return true;
}

NativeFixedFunctionPipelineBindingReadiness
NativeFixedFunctionPipelineBundle::binding_readiness(
    ID3D11DeviceContext* context,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    std::uint64_t pipelineSnapshotToken) const noexcept {
    NativeFixedFunctionPipelineBindingReadiness out{};
    out.pipelineSnapshotToken = pipelineSnapshotToken;
    out.inputValid = context != nullptr && pipelineSnapshotToken != 0;
    out.bundleReady = ready();
    out.translationSnapshotValid =
        out.inputValid && out.bundleReady &&
        validate_translation_snapshot(
            device_.Get(), layout, vertexPrototype, pixelPrototype,
            pipelineSnapshotToken);

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    if (context)
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextMatches =
        contextDevice && device_ && contextDevice.Get() == device_.Get();

    if (out.translationSnapshotValid && out.contextMatches) {
        Microsoft::WRL::ComPtr<ID3D11InputLayout> boundInputLayout;
        Microsoft::WRL::ComPtr<ID3D11VertexShader> boundVertexShader;
        Microsoft::WRL::ComPtr<ID3D11PixelShader> boundPixelShader;
        context->IAGetInputLayout(boundInputLayout.ReleaseAndGetAddressOf());
        context->VSGetShader(
            boundVertexShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
        context->PSGetShader(
            boundPixelShader.ReleaseAndGetAddressOf(), nullptr, nullptr);
        out.boundExact =
            boundInputLayout.Get() == input_layout_.Get() &&
            boundVertexShader.Get() == vertex_shader_.Get() &&
            boundPixelShader.Get() == pixel_shader_.Get();
    }

    out.ready =
        out.inputValid && out.bundleReady && out.contextMatches &&
        out.translationSnapshotValid && out.boundExact;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, pipelineSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(device_.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(input_layout_.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(vertex_shader_.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(pixel_shader_.Get())));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeFixedFunctionPipelineBundle::validate_binding_snapshot(
    ID3D11DeviceContext* context,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype,
    std::uint64_t pipelineSnapshotToken,
    std::uint64_t bindingSnapshotToken) const noexcept {
    if (bindingSnapshotToken == 0)
        return false;
    const auto current = binding_readiness(
        context, layout, vertexPrototype, pixelPrototype,
        pipelineSnapshotToken);
    return current.ready && current.snapshotToken == bindingSnapshotToken;
}

NativeFixedFunctionActivationReadiness
compose_fixed_function_activation_readiness(
    const NativeFixedFunctionPipelineReadiness& pipeline,
    const NativeManagedTextureStageReadiness& textureStages) noexcept {
    NativeFixedFunctionActivationReadiness out{};
    out.requiredTextureMask = textureStages.requiredMask;
    out.pipelineSnapshotToken = pipeline.snapshotToken;
    out.textureSnapshotToken = textureStages.snapshotToken;

    const bool texturesRequired = textureStages.requiredMask != 0;
    const bool textureMaskReady =
        textureStages.readyMask == textureStages.requiredMask &&
        textureStages.pendingMask == 0;

    out.inputValid = pipeline.inputValid && textureStages.inputValid;
    out.pipelineReady = pipeline.ready && pipeline.snapshotToken != 0;
    out.textureStagesReady =
        textureStages.allRequiredReady &&
        textureMaskReady &&
        (!texturesRequired || textureStages.snapshotToken != 0);
    out.componentSnapshotsPresent =
        pipeline.snapshotToken != 0 &&
        (!texturesRequired || textureStages.snapshotToken != 0);
    out.ready =
        out.inputValid &&
        out.pipelineReady &&
        out.textureStagesReady &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t activationToken = 0xcbf29ce484222325ull;
        activationToken = mix_readiness_snapshot_token(
            activationToken, out.pipelineSnapshotToken);
        activationToken = mix_readiness_snapshot_token(
            activationToken, out.textureSnapshotToken);
        activationToken = mix_readiness_snapshot_token(
            activationToken,
            static_cast<std::uint64_t>(out.requiredTextureMask));
        out.snapshotToken = activationToken == 0 ? 1 : activationToken;
    }
    return out;
}

bool validate_fixed_function_activation_snapshot(
    const NativeFixedFunctionPipelineReadiness& pipeline,
    const NativeManagedTextureStageReadiness& textureStages,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_activation_readiness(
        pipeline, textureStages);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionGeometryReadiness
compose_fixed_function_geometry_readiness(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    bool indexed,
    const NativeManagedBufferMirrorReadiness& indexBuffer,
    D3DPRIMITIVETYPE primitive) noexcept {
    NativeFixedFunctionGeometryReadiness out{};
    const auto topology = translate_primitive(primitive);
    out.indexBufferRequired = indexed;
    out.topology = topology.value;
    out.vertexBufferSnapshotToken = vertexBuffer.snapshotToken;
    out.indexBufferSnapshotToken = indexed ? indexBuffer.snapshotToken : 0;
    out.inputValid =
        vertexBuffer.inputValid &&
        vertexBuffer.role == ResourceRole::Vertex &&
        (!indexed ||
         (indexBuffer.inputValid &&
          indexBuffer.role == ResourceRole::Index));
    out.vertexBufferReady =
        vertexBuffer.ready && vertexBuffer.snapshotToken != 0;
    out.indexBufferReady =
        !indexed || (indexBuffer.ready && indexBuffer.snapshotToken != 0);
    out.topologyReady =
        topology.exact &&
        topology.value != D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    out.componentSnapshotsPresent =
        vertexBuffer.snapshotToken != 0 &&
        (!indexed || indexBuffer.snapshotToken != 0);
    out.ready =
        out.inputValid &&
        out.vertexBufferReady &&
        out.indexBufferReady &&
        out.topologyReady &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(token, indexed ? 1u : 0u);
        token = mix_readiness_snapshot_token(
            token, out.indexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.topology));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_geometry_snapshot(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    bool indexed,
    const NativeManagedBufferMirrorReadiness& indexBuffer,
    D3DPRIMITIVETYPE primitive,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_geometry_readiness(
        vertexBuffer, indexed, indexBuffer, primitive);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionGeometryReadiness
compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex) noexcept {
    NativeFixedFunctionGeometryReadiness out{};
    const auto expansion = translate_triangle_fan_expansion(primitiveCount);
    out.indexBufferRequired = false;
    out.indexBufferReady = true;
    out.generatedIndexBufferRequired = true;
    out.topology = expansion.topology;
    out.vertexBufferSnapshotToken = vertexBuffer.snapshotToken;
    out.generatedIndexBufferSnapshotToken =
        generatedIndexBuffer.snapshotToken;

    std::uint64_t expectedContentHash = 0;
    if (expansion.exact &&
        expansion.expandedIndexCount != 0 &&
        expansion.topology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST) {
        std::uint64_t hash = 0xcbf29ce484222325ull;
        bool exactIndices = true;
        for (UINT expandedIndex = 0;
             expandedIndex < expansion.expandedIndexCount;
             ++expandedIndex) {
            UINT sourceElement = 0;
            if (!triangle_fan_source_element(
                    primitiveCount, expandedIndex, sourceElement) ||
                baseVertex >
                    std::numeric_limits<UINT>::max() - sourceElement) {
                exactIndices = false;
                break;
            }
            hash = mix_readiness_snapshot_token(
                hash, baseVertex + sourceElement);
        }
        if (exactIndices)
            expectedContentHash = hash == 0 ? 1 : hash;
    }

    out.inputValid =
        vertexBuffer.inputValid &&
        vertexBuffer.role == ResourceRole::Vertex &&
        expansion.exact &&
        expectedContentHash != 0;
    out.vertexBufferReady =
        vertexBuffer.ready && vertexBuffer.snapshotToken != 0;
    out.generatedIndexBufferReady =
        generatedIndexBuffer.ready &&
        generatedIndexBuffer.snapshotToken != 0;
    out.generatedIndexBufferMatchesDraw =
        out.generatedIndexBufferReady &&
        generatedIndexBuffer.indexCount == expansion.expandedIndexCount &&
        generatedIndexBuffer.contentHash == expectedContentHash;
    out.topologyReady =
        expansion.exact &&
        expansion.topology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST;
    out.componentSnapshotsPresent =
        vertexBuffer.snapshotToken != 0 &&
        generatedIndexBuffer.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.vertexBufferReady &&
        out.indexBufferReady &&
        out.generatedIndexBufferReady &&
        out.generatedIndexBufferMatchesDraw &&
        out.topologyReady &&
        out.componentSnapshotsPresent;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.vertexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.generatedIndexBufferSnapshotToken);
        token = mix_readiness_snapshot_token(token, primitiveCount);
        token = mix_readiness_snapshot_token(token, baseVertex);
        token = mix_readiness_snapshot_token(token, expectedContentHash);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(out.topology));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_nonindexed_triangle_fan_geometry_snapshot(
    const NativeManagedBufferMirrorReadiness& vertexBuffer,
    const NativeTriangleFanIndexBufferReadiness& generatedIndexBuffer,
    UINT primitiveCount,
    UINT baseVertex,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            vertexBuffer, generatedIndexBuffer, primitiveCount, baseVertex);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionOutputStateReadiness
compose_fixed_function_output_state_readiness(
    const OutRunVR::DrawState::RenderStateSnapshot& source,
    const NativeSurfacePairReadiness& surfacePair) noexcept {
    NativeFixedFunctionOutputStateReadiness out{};
    out.sampleMask = source.multiSampleMask;

    if (!source.outputStateComplete ||
        !surfacePair.inputValid ||
        !surfacePair.ready ||
        surfacePair.snapshotToken == 0 ||
        surfacePair.width == 0 ||
        surfacePair.height == 0)
        return out;

    out.inputValid = true;

    const std::uint64_t viewportRight =
        static_cast<std::uint64_t>(source.viewport.X) +
        static_cast<std::uint64_t>(source.viewport.Width);
    const std::uint64_t viewportBottom =
        static_cast<std::uint64_t>(source.viewport.Y) +
        static_cast<std::uint64_t>(source.viewport.Height);
    out.viewportExact =
        source.viewport.Width != 0 &&
        source.viewport.Height != 0 &&
        viewportRight <= surfacePair.width &&
        viewportBottom <= surfacePair.height &&
        source.viewport.MinZ >= 0.0f &&
        source.viewport.MinZ <= source.viewport.MaxZ &&
        source.viewport.MaxZ <= 1.0f;

    out.viewport.TopLeftX = static_cast<float>(source.viewport.X);
    out.viewport.TopLeftY = static_cast<float>(source.viewport.Y);
    out.viewport.Width = static_cast<float>(source.viewport.Width);
    out.viewport.Height = static_cast<float>(source.viewport.Height);
    out.viewport.MinDepth = source.viewport.MinZ;
    out.viewport.MaxDepth = source.viewport.MaxZ;

    out.scissorRect.left = source.scissorRect.left;
    out.scissorRect.top = source.scissorRect.top;
    out.scissorRect.right = source.scissorRect.right;
    out.scissorRect.bottom = source.scissorRect.bottom;
    const bool scissorBoundsExact =
        source.scissorRect.left >= 0 &&
        source.scissorRect.top >= 0 &&
        source.scissorRect.right >= source.scissorRect.left &&
        source.scissorRect.bottom >= source.scissorRect.top &&
        static_cast<std::uint64_t>(source.scissorRect.right) <=
            surfacePair.width &&
        static_cast<std::uint64_t>(source.scissorRect.bottom) <=
            surfacePair.height;
    out.scissorExact =
        source.scissorTestEnable == FALSE || scissorBoundsExact;

    constexpr float channelScale = 1.0f / 255.0f;
    out.blendFactor[0] =
        static_cast<float>((source.blendFactor >> 16) & 0xffu) *
        channelScale;
    out.blendFactor[1] =
        static_cast<float>((source.blendFactor >> 8) & 0xffu) *
        channelScale;
    out.blendFactor[2] =
        static_cast<float>(source.blendFactor & 0xffu) *
        channelScale;
    out.blendFactor[3] =
        static_cast<float>((source.blendFactor >> 24) & 0xffu) *
        channelScale;
    out.omDynamicExact = true;

    out.ready =
        out.inputValid &&
        out.viewportExact &&
        out.scissorExact &&
        out.omDynamicExact;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, surfacePair.snapshotToken);
        token = mix_readiness_snapshot_token(token, source.viewport.X);
        token = mix_readiness_snapshot_token(token, source.viewport.Y);
        token = mix_readiness_snapshot_token(token, source.viewport.Width);
        token = mix_readiness_snapshot_token(token, source.viewport.Height);
        std::uint32_t minDepthBits = 0;
        std::uint32_t maxDepthBits = 0;
        std::memcpy(
            &minDepthBits, &source.viewport.MinZ, sizeof(minDepthBits));
        std::memcpy(
            &maxDepthBits, &source.viewport.MaxZ, sizeof(maxDepthBits));
        token = mix_readiness_snapshot_token(token, minDepthBits);
        token = mix_readiness_snapshot_token(token, maxDepthBits);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(source.scissorRect.left));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(source.scissorRect.top));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(source.scissorRect.right));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint32_t>(source.scissorRect.bottom));
        token = mix_readiness_snapshot_token(
            token, source.scissorTestEnable != FALSE ? 1u : 0u);
        token = mix_readiness_snapshot_token(token, source.blendFactor);
        token = mix_readiness_snapshot_token(token, source.multiSampleMask);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_output_state_snapshot(
    const OutRunVR::DrawState::RenderStateSnapshot& source,
    const NativeSurfacePairReadiness& surfacePair,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_output_state_readiness(source, surfacePair);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool NativeFixedFunctionOutputStateBinding::initialize(
    ID3D11Device* device,
    const NativeFixedFunctionRenderStateBundle& renderStateBundle,
    const PipelineTranslation& translation,
    std::uint64_t renderStateSnapshotToken,
    const OutRunVR::DrawState::RenderStateSnapshot& source,
    const NativeSurfacePairReadiness& surfacePair,
    std::uint64_t outputStateSnapshotToken) noexcept {

    shutdown();
    if (!device ||
        renderStateSnapshotToken == 0 ||
        outputStateSnapshotToken == 0 ||
        !renderStateBundle.validate_translation_snapshot(
            device, translation, renderStateSnapshotToken) ||
        !validate_fixed_function_output_state_snapshot(
            source, surfacePair, outputStateSnapshotToken) ||
        !renderStateBundle.ready() ||
        renderStateBundle.device() != device ||
        !renderStateBundle.blend_state() ||
        !renderStateBundle.depth_stencil_state() ||
        !renderStateBundle.rasterizer_state())
        return false;

    const bool sourceScissorEnabled = source.scissorTestEnable != FALSE;
    if (translation.rasterizer.ScissorEnable != sourceScissorEnabled)
        return false;

    const auto renderState =
        renderStateBundle.translation_readiness(device, translation);
    const auto outputState =
        compose_fixed_function_output_state_readiness(source, surfacePair);
    if (!renderState.ready ||
        renderState.snapshotToken != renderStateSnapshotToken ||
        !outputState.ready ||
        outputState.snapshotToken != outputStateSnapshotToken)
        return false;

    D3D11_RECT sealedScissor = outputState.scissorRect;
    if (!sourceScissorEnabled) {
        if (surfacePair.width >
                static_cast<UINT>(std::numeric_limits<LONG>::max()) ||
            surfacePair.height >
                static_cast<UINT>(std::numeric_limits<LONG>::max()))
            return false;
        sealedScissor.left = 0;
        sealedScissor.top = 0;
        sealedScissor.right = static_cast<LONG>(surfacePair.width);
        sealedScissor.bottom = static_cast<LONG>(surfacePair.height);
    }

    device_ = device;
    blend_state_ = renderStateBundle.blend_state();
    depth_stencil_state_ = renderStateBundle.depth_stencil_state();
    rasterizer_state_ = renderStateBundle.rasterizer_state();
    viewport_ = outputState.viewport;
    scissor_rect_ = sealedScissor;
    blend_factor_ = outputState.blendFactor;
    sample_mask_ = outputState.sampleMask;
    stencil_ref_ = renderStateBundle.stencil_ref();
    render_state_snapshot_token_ = renderStateSnapshotToken;
    surface_pair_snapshot_token_ = surfacePair.snapshotToken;
    output_state_snapshot_token_ = outputStateSnapshotToken;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(
        token, render_state_snapshot_token_);
    token = mix_readiness_snapshot_token(
        token, surface_pair_snapshot_token_);
    token = mix_readiness_snapshot_token(
        token, output_state_snapshot_token_);
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(device_.Get())));
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(blend_state_.Get())));
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(depth_stencil_state_.Get())));
    token = mix_readiness_snapshot_token(
        token, static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(rasterizer_state_.Get())));
    snapshot_token_ = token == 0 ? 1 : token;
    return ready();
}

void NativeFixedFunctionOutputStateBinding::shutdown() noexcept {
    rasterizer_state_.Reset();
    depth_stencil_state_.Reset();
    blend_state_.Reset();
    device_.Reset();
    viewport_ = {};
    scissor_rect_ = {};
    blend_factor_ = {1.0f, 1.0f, 1.0f, 1.0f};
    sample_mask_ = 0xFFFFFFFFu;
    stencil_ref_ = 0;
    render_state_snapshot_token_ = 0;
    surface_pair_snapshot_token_ = 0;
    output_state_snapshot_token_ = 0;
    snapshot_token_ = 0;
}

bool NativeFixedFunctionOutputStateBinding::apply(
    ID3D11DeviceContext* context) const noexcept {

    if (!ready() || !context)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    if (!contextDevice || contextDevice.Get() != device_.Get())
        return false;

    context->RSSetState(rasterizer_state_.Get());
    context->RSSetViewports(1, &viewport_);
    context->RSSetScissorRects(1, &scissor_rect_);
    context->OMSetBlendState(
        blend_state_.Get(), blend_factor_.data(), sample_mask_);
    context->OMSetDepthStencilState(
        depth_stencil_state_.Get(), stencil_ref_);
    return true;
}

NativeFixedFunctionOutputBindingReadiness
NativeFixedFunctionOutputStateBinding::binding_readiness(
    ID3D11DeviceContext* context) const noexcept {
    NativeFixedFunctionOutputBindingReadiness out{};
    out.outputBindingSnapshotToken = snapshot_token_;
    out.inputValid = context != nullptr && snapshot_token_ != 0;
    out.ownerReady = ready();
    if (!out.inputValid || !out.ownerReady)
        return out;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
    out.contextMatches =
        contextDevice && contextDevice.Get() == device_.Get();
    if (!out.contextMatches)
        return out;

    Microsoft::WRL::ComPtr<ID3D11RasterizerState> observedRasterizer;
    Microsoft::WRL::ComPtr<ID3D11BlendState> observedBlend;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilState> observedDepthStencil;
    D3D11_VIEWPORT observedViewport{};
    D3D11_RECT observedScissor{};
    FLOAT observedBlendFactor[4]{};
    UINT observedSampleMask = 0;
    UINT observedStencilRef = 0;
    UINT viewportCount = 1;
    UINT scissorCount = 1;

    context->RSGetState(observedRasterizer.ReleaseAndGetAddressOf());
    context->RSGetViewports(&viewportCount, &observedViewport);
    context->RSGetScissorRects(&scissorCount, &observedScissor);
    context->OMGetBlendState(
        observedBlend.ReleaseAndGetAddressOf(),
        observedBlendFactor, &observedSampleMask);
    context->OMGetDepthStencilState(
        observedDepthStencil.ReleaseAndGetAddressOf(),
        &observedStencilRef);

    out.rasterizerMatches =
        observedRasterizer.Get() == rasterizer_state_.Get();
    out.viewportMatches =
        viewportCount == 1 &&
        observedViewport.TopLeftX == viewport_.TopLeftX &&
        observedViewport.TopLeftY == viewport_.TopLeftY &&
        observedViewport.Width == viewport_.Width &&
        observedViewport.Height == viewport_.Height &&
        observedViewport.MinDepth == viewport_.MinDepth &&
        observedViewport.MaxDepth == viewport_.MaxDepth;
    out.scissorMatches =
        scissorCount == 1 &&
        observedScissor.left == scissor_rect_.left &&
        observedScissor.top == scissor_rect_.top &&
        observedScissor.right == scissor_rect_.right &&
        observedScissor.bottom == scissor_rect_.bottom;
    out.blendStateMatches =
        observedBlend.Get() == blend_state_.Get();
    out.blendFactorMatches =
        observedBlendFactor[0] == blend_factor_[0] &&
        observedBlendFactor[1] == blend_factor_[1] &&
        observedBlendFactor[2] == blend_factor_[2] &&
        observedBlendFactor[3] == blend_factor_[3];
    out.sampleMaskMatches = observedSampleMask == sample_mask_;
    out.depthStencilMatches =
        observedDepthStencil.Get() == depth_stencil_state_.Get();
    out.stencilRefMatches = observedStencilRef == stencil_ref_;
    out.ready =
        out.rasterizerMatches &&
        out.viewportMatches &&
        out.scissorMatches &&
        out.blendStateMatches &&
        out.blendFactorMatches &&
        out.sampleMaskMatches &&
        out.depthStencilMatches &&
        out.stencilRefMatches;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.outputBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(context)));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(observedRasterizer.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(observedBlend.Get())));
        token = mix_readiness_snapshot_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(observedDepthStencil.Get())));
        token = mix_readiness_snapshot_token(token, observedSampleMask);
        token = mix_readiness_snapshot_token(token, observedStencilRef);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeFixedFunctionOutputStateBinding::validate_binding_snapshot(
    ID3D11DeviceContext* context,
    std::uint64_t bindingSnapshotToken) const noexcept {
    if (bindingSnapshotToken == 0)
        return false;
    const auto current = binding_readiness(context);
    return current.ready && current.snapshotToken == bindingSnapshotToken;
}

NativeFixedFunctionDrawReadiness
compose_fixed_function_draw_readiness(
    const NativeFixedFunctionActivationReadiness& activation,
    const NativeFixedFunctionRenderStateReadiness& renderState,
    const NativeSurfacePairReadiness& surfacePair,
    const NativeFixedFunctionOutputStateReadiness& outputState,
    const NativeFixedFunctionOutputStateBinding& outputBinding,
    const NativeFixedFunctionGeometryReadiness& geometry) noexcept {
    NativeFixedFunctionDrawReadiness out{};
    out.activationSnapshotToken = activation.snapshotToken;
    out.pipelineSnapshotToken = activation.pipelineSnapshotToken;
    out.renderStateSnapshotToken = renderState.snapshotToken;
    out.surfacePairSnapshotToken = surfacePair.snapshotToken;
    out.outputStateSnapshotToken = outputState.snapshotToken;
    out.outputBindingSnapshotToken = outputBinding.snapshot_token();
    out.geometrySnapshotToken = geometry.snapshotToken;
    out.requiredTextureMask = activation.requiredTextureMask;
    out.inputValid =
        activation.inputValid &&
        renderState.inputValid &&
        surfacePair.inputValid &&
        outputState.inputValid &&
        geometry.inputValid;
    out.activationReady =
        activation.ready && activation.snapshotToken != 0;
    out.renderStateReady =
        renderState.ready && renderState.snapshotToken != 0;
    out.surfacePairReady =
        surfacePair.ready && surfacePair.snapshotToken != 0;
    out.outputStateReady =
        outputState.ready && outputState.snapshotToken != 0;
    out.outputBindingReady =
        outputBinding.ready() &&
        outputBinding.render_state_snapshot_token() == renderState.snapshotToken &&
        outputBinding.surface_pair_snapshot_token() == surfacePair.snapshotToken &&
        outputBinding.output_state_snapshot_token() == outputState.snapshotToken &&
        outputBinding.snapshot_token() != 0;
    out.geometryReady =
        geometry.ready && geometry.snapshotToken != 0;
    out.componentSnapshotsPresent =
        activation.snapshotToken != 0 &&
        renderState.snapshotToken != 0 &&
        surfacePair.snapshotToken != 0 &&
        outputState.snapshotToken != 0 &&
        outputBinding.snapshot_token() != 0 &&
        geometry.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.activationReady &&
        out.renderStateReady &&
        out.surfacePairReady &&
        out.outputStateReady &&
        out.outputBindingReady &&
        out.geometryReady &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t drawToken = 0xcbf29ce484222325ull;
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.activationSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.pipelineSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.renderStateSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.surfacePairSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.outputStateSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.outputBindingSnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.geometrySnapshotToken);
        drawToken = mix_readiness_snapshot_token(
            drawToken, out.requiredTextureMask);
        out.snapshotToken = drawToken == 0 ? 1 : drawToken;
    }
    return out;
}

bool validate_fixed_function_draw_readiness_integrity(
    const NativeFixedFunctionDrawReadiness& draw) noexcept {
    if (!draw.inputValid ||
        !draw.activationReady ||
        !draw.renderStateReady ||
        !draw.surfacePairReady ||
        !draw.outputStateReady ||
        !draw.outputBindingReady ||
        !draw.geometryReady ||
        !draw.componentSnapshotsPresent ||
        !draw.ready ||
        draw.activationSnapshotToken == 0 ||
        draw.pipelineSnapshotToken == 0 ||
        draw.renderStateSnapshotToken == 0 ||
        draw.surfacePairSnapshotToken == 0 ||
        draw.outputStateSnapshotToken == 0 ||
        draw.outputBindingSnapshotToken == 0 ||
        draw.geometrySnapshotToken == 0 ||
        draw.snapshotToken == 0)
        return false;

    std::uint64_t token = 0xcbf29ce484222325ull;
    token = mix_readiness_snapshot_token(token, draw.activationSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.pipelineSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.renderStateSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.surfacePairSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.outputStateSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.outputBindingSnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.geometrySnapshotToken);
    token = mix_readiness_snapshot_token(token, draw.requiredTextureMask);
    token = token == 0 ? 1 : token;
    return token == draw.snapshotToken;
}

bool validate_fixed_function_draw_snapshot(
    const NativeFixedFunctionActivationReadiness& activation,
    const NativeFixedFunctionRenderStateReadiness& renderState,
    const NativeSurfacePairReadiness& surfacePair,
    const NativeFixedFunctionOutputStateReadiness& outputState,
    const NativeFixedFunctionOutputStateBinding& outputBinding,
    const NativeFixedFunctionGeometryReadiness& geometry,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_draw_readiness(
        activation, renderState, surfacePair, outputState, outputBinding, geometry);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionTexturedDrawReadiness
compose_fixed_function_textured_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture) noexcept {
    NativeFixedFunctionTexturedDrawReadiness out{};
    const auto textureStage = observe_fixed_function_texture_stage_binding(
        context, slot, sampler, texture);
    out.drawSnapshotToken = draw.snapshotToken;
    out.textureStageSnapshotToken = textureStage.snapshotToken;
    out.requiredTextureMask = draw.requiredTextureMask;
    out.observedTextureMask =
        textureStage.slot < 32u ? (1u << textureStage.slot) : 0u;
    // R133 is deliberately single-stage: one observed PS binding cannot prove
    // a multi-stage activation mask. Require the exact activation stage bit so
    // a valid sampler/SRV bound to the wrong slot cannot make the draw ready.
    out.textureMaskMatches =
        textureStage.slotValid &&
        out.requiredTextureMask != 0 &&
        out.requiredTextureMask == out.observedTextureMask;
    out.inputValid =
        draw.inputValid && textureStage.inputValid && out.textureMaskMatches;
    out.drawReady =
        validate_fixed_function_draw_readiness_integrity(draw);
    out.textureStageReady =
        textureStage.ready && textureStage.snapshotToken != 0;
    out.componentSnapshotsPresent =
        draw.snapshotToken != 0 && textureStage.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.drawReady &&
        out.textureStageReady &&
        out.textureMaskMatches &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.drawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.textureStageSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.requiredTextureMask);
        token = mix_readiness_snapshot_token(
            token, out.observedTextureMask);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_textured_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    UINT slot,
    const NativeFixedFunctionSamplerState& sampler,
    const NativeFixedFunctionTextureView& texture,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_textured_draw_readiness(
        draw, context, slot, sampler, texture);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionTexturedDrawReadiness
compose_fixed_function_multistage_textured_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures) noexcept {
    NativeFixedFunctionTexturedDrawReadiness out{};
    // Reobserve every required PS stage at composition time. A previously
    // captured aggregate is useful diagnostic evidence, but cannot authorize a
    // later draw candidate after the live context has changed.
    const auto textureBindings = observe_fixed_function_texture_binding_set(
        context, draw.requiredTextureMask, samplers, textures);
    out.drawSnapshotToken = draw.snapshotToken;
    out.textureStageSnapshotToken = textureBindings.snapshotToken;
    out.requiredTextureMask = draw.requiredTextureMask;
    out.observedTextureMask = textureBindings.observedTextureMask;
    out.textureMaskMatches =
        textureBindings.requiredMaskValid &&
        out.requiredTextureMask != 0 &&
        textureBindings.requiredTextureMask == out.requiredTextureMask &&
        out.observedTextureMask == out.requiredTextureMask;
    const bool drawSnapshotValid =
        validate_fixed_function_draw_readiness_integrity(draw);
    const bool textureBindingSnapshotValid =
        validate_fixed_function_texture_binding_set_readiness_integrity(
            textureBindings);
    out.inputValid =
        drawSnapshotValid &&
        textureBindingSnapshotValid &&
        out.textureMaskMatches;
    out.drawReady = drawSnapshotValid;
    out.textureStageReady = textureBindingSnapshotValid;
    out.componentSnapshotsPresent =
        draw.snapshotToken != 0 && textureBindings.snapshotToken != 0;
    out.ready =
        out.inputValid &&
        out.drawReady &&
        out.textureStageReady &&
        out.textureMaskMatches &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(token, out.drawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.textureStageSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.requiredTextureMask);
        token = mix_readiness_snapshot_token(
            token, out.observedTextureMask);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_multistage_textured_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    ID3D11DeviceContext* context,
    const std::array<const NativeFixedFunctionSamplerState*, 8>& samplers,
    const std::array<const NativeFixedFunctionTextureView*, 8>& textures,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current =
        compose_fixed_function_multistage_textured_draw_readiness(
            draw, context, samplers, textures);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeFixedFunctionBoundDrawReadiness
compose_fixed_function_bound_draw_readiness(
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionTexturedDrawReadiness& texturedDraw,
    const NativeFixedFunctionPipelineBindingReadiness& pipelineBinding,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding) noexcept {
    NativeFixedFunctionBoundDrawReadiness out{};
    out.texturedDrawSnapshotToken = texturedDraw.snapshotToken;
    out.pipelineBindingSnapshotToken = pipelineBinding.snapshotToken;
    const auto outputBinding =
        outputStateBinding.binding_readiness(context);
    out.outputBindingSnapshotToken = outputBinding.snapshotToken;
    const bool drawSnapshotValid =
        validate_fixed_function_draw_readiness_integrity(draw);
    out.inputValid =
        drawSnapshotValid &&
        texturedDraw.inputValid &&
        pipelineBinding.inputValid &&
        outputBinding.inputValid;
    out.texturedDrawReady =
        texturedDraw.ready && texturedDraw.snapshotToken != 0 &&
        texturedDraw.drawSnapshotToken == draw.snapshotToken;
    out.pipelineBindingReady =
        pipelineBinding.ready && pipelineBinding.snapshotToken != 0;
    out.pipelineBindingMatchesDraw =
        draw.pipelineSnapshotToken != 0 &&
        pipelineBinding.pipelineSnapshotToken == draw.pipelineSnapshotToken;
    out.outputBindingReady =
        outputBinding.ready && outputBinding.snapshotToken != 0;
    out.outputBindingMatchesDraw =
        draw.outputBindingSnapshotToken != 0 &&
        outputBinding.outputBindingSnapshotToken ==
            draw.outputBindingSnapshotToken;
    out.componentSnapshotsPresent =
        draw.snapshotToken != 0 &&
        texturedDraw.snapshotToken != 0 &&
        pipelineBinding.snapshotToken != 0 &&
        outputBinding.snapshotToken != 0;
    out.ready =
        draw.ready &&
        out.inputValid &&
        out.texturedDrawReady &&
        out.pipelineBindingReady &&
        out.pipelineBindingMatchesDraw &&
        out.outputBindingReady &&
        out.outputBindingMatchesDraw &&
        out.componentSnapshotsPresent;
    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_readiness_snapshot_token(
            token, out.texturedDrawSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.pipelineBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, out.outputBindingSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, draw.pipelineSnapshotToken);
        token = mix_readiness_snapshot_token(
            token, draw.outputBindingSnapshotToken);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool validate_fixed_function_bound_draw_snapshot(
    const NativeFixedFunctionDrawReadiness& draw,
    const NativeFixedFunctionTexturedDrawReadiness& texturedDraw,
    const NativeFixedFunctionPipelineBindingReadiness& pipelineBinding,
    ID3D11DeviceContext* context,
    const NativeFixedFunctionOutputStateBinding& outputStateBinding,
    std::uint64_t snapshotToken) noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = compose_fixed_function_bound_draw_readiness(
        draw, texturedDraw, pipelineBinding, context, outputStateBinding);
    return current.ready && current.snapshotToken == snapshotToken;
}

void NativeFixedFunctionPipelineBundle::shutdown() noexcept {
    transform_buffer_.shutdown();
    input_layout_.Reset();
    pixel_shader_.Reset();
    vertex_shader_.Reset();
    device_.Reset();
    input_layout_identity_ = 0;
    vertex_shader_source_hash_ = 0;
    pixel_shader_source_hash_ = 0;
}

bool NativeBackend::initialize(const NativeBackendConfig& config) noexcept {
    shutdown();
    if (config.width == 0 || config.height == 0) return false;

    if (config.require_adapter_luid && !config.adapter_luid_valid)
        return false;

    Microsoft::WRL::ComPtr<IDXGIAdapter1> requestedAdapter;
    if (config.adapter_luid_valid &&
        !find_adapter(config.adapter_luid, requestedAdapter) &&
        config.require_adapter_luid)
        return false;

    UINT flags = D3D11_CREATE_DEVICE_BGRA_SUPPORT;
    if (config.request_debug_layer) flags |= D3D11_CREATE_DEVICE_DEBUG;

    HRESULT hr = create_device(
        requestedAdapter.Get(), flags, device_, context_, feature_level_);
    if (FAILED(hr) && (flags & D3D11_CREATE_DEVICE_DEBUG) != 0) {
        device_.Reset();
        context_.Reset();
        flags &= ~D3D11_CREATE_DEVICE_DEBUG;
        hr = create_device(
            requestedAdapter.Get(), flags, device_, context_, feature_level_);
    }
    if (FAILED(hr)) {
        shutdown();
        return false;
    }

    selected_adapter_luid_valid_ =
        read_device_luid(device_.Get(), selected_adapter_luid_);
    if (config.adapter_luid_valid &&
        config.require_adapter_luid &&
        (!selected_adapter_luid_valid_ ||
         !same_luid(selected_adapter_luid_, config.adapter_luid))) {
        shutdown();
        return false;
    }

    config_ = config;
    if (!create_color_target(config.width, config.height, config.color_format)) {
        shutdown();
        return false;
    }
    return true;
}

bool NativeBackend::resize(std::uint32_t width, std::uint32_t height) noexcept {
    if (!device_ || width == 0 || height == 0) return false;

    color_srv_.Reset();
    color_rtv_.Reset();
    color_texture_.Reset();

    if (!create_color_target(width, height, config_.color_format)) return false;
    config_.width = width;
    config_.height = height;
    return true;
}

void NativeBackend::begin_frame(const std::array<float, 4>& clear_color) noexcept {
    if (!ready()) return;

    ID3D11RenderTargetView* rtv = color_rtv_.Get();
    context_->OMSetRenderTargets(1, &rtv, nullptr);

    D3D11_VIEWPORT viewport{};
    viewport.Width = static_cast<float>(config_.width);
    viewport.Height = static_cast<float>(config_.height);
    viewport.MinDepth = 0.0f;
    viewport.MaxDepth = 1.0f;
    context_->RSSetViewports(1, &viewport);
    context_->ClearRenderTargetView(color_rtv_.Get(), clear_color.data());
}

void NativeBackend::shutdown() noexcept {
    color_srv_.Reset();
    color_rtv_.Reset();
    color_texture_.Reset();
    context_.Reset();
    device_.Reset();
    config_ = {};
    feature_level_ = D3D_FEATURE_LEVEL_9_1;
    selected_adapter_luid_ = {};
    selected_adapter_luid_valid_ = false;
}

bool NativeBackend::create_color_target(
    std::uint32_t width, std::uint32_t height, DXGI_FORMAT format) noexcept {
    if (!device_ || width == 0 || height == 0) return false;

    D3D11_TEXTURE2D_DESC desc{};
    desc.Width = width;
    desc.Height = height;
    desc.MipLevels = 1;
    desc.ArraySize = 1;
    desc.Format = format;
    desc.SampleDesc.Count = 1;
    desc.Usage = D3D11_USAGE_DEFAULT;
    desc.BindFlags = D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;

    if (FAILED(device_->CreateTexture2D(&desc, nullptr, color_texture_.ReleaseAndGetAddressOf())))
        return false;
    if (FAILED(device_->CreateRenderTargetView(color_texture_.Get(), nullptr, color_rtv_.ReleaseAndGetAddressOf()))) {
        color_texture_.Reset();
        return false;
    }
    if (FAILED(device_->CreateShaderResourceView(color_texture_.Get(), nullptr, color_srv_.ReleaseAndGetAddressOf()))) {
        color_rtv_.Reset();
        color_texture_.Reset();
        return false;
    }
    return true;
}

} // namespace outrun::vr::dx11