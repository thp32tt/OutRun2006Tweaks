#include "native_backend.hpp"

#include "pipeline_translation.hpp"
#include "resource_translation.hpp"

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
    out.ready =
        shadow->mirror_ready() &&
        out.resourcesOwned &&
        out.lifetimeCurrent &&
        out.deviceMatches;
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

        if (resourcesOwned)
            out.resourcesOwnedMask |= bit;
        if (lifetimeCurrent)
            out.lifetimeCurrentMask |= bit;
        if (deviceMatches)
            out.deviceMatchesMask |= bit;
        if (shadow->mirror_ready() &&
            resourcesOwned &&
            lifetimeCurrent &&
            deviceMatches)
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

bool NativeFixedFunctionPipelineBundle::initialize(
    ID3D11Device* device,
    const VertexInputLayoutTranslation& layout,
    const FixedFunctionVertexShaderPrototype& vertexPrototype,
    const FixedFunctionPixelShaderPrototype& pixelPrototype) noexcept {

    shutdown();
    if (!device || !layout.exact || layout.elementCount == 0 ||
        layout.elementCount > layout.elements.size() ||
        !vertexPrototype.generated() || !pixelPrototype.generated())
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
    return true;
}

void NativeFixedFunctionPipelineBundle::shutdown() noexcept {
    transform_buffer_.shutdown();
    input_layout_.Reset();
    pixel_shader_.Reset();
    vertex_shader_.Reset();
    device_.Reset();
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