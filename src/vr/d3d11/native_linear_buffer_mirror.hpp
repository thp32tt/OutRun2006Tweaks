#pragma once
// R183: dormant D3D9 DEFAULT VB/IB snapshot -> owned D3D11 IA resource.
// A successful snapshot never authorizes game-native Draw or future Lock updates.
#include "resource_translation.hpp"
#include <cstdint>
#include <utility>
#include <wrl/client.h>

namespace outrun::vr::dx11 {
class NativeLinearBufferMirror final {
public:
    bool initialize(ID3D11Device* device, ResourceRole role,
                    D3DPOOL pool, DWORD usage, D3DFORMAT indexFormat,
                    const void* sourceBytes, UINT byteWidth, UINT vertexStride,
                    std::uint64_t deviceGeneration,
                    std::uint64_t sourceSnapshotVersion) noexcept {
        shutdown(); // A rejected replacement cannot retain an old draw-ready VB/IB.
        if (!device || !sourceBytes || !byteWidth || !deviceGeneration ||
            !sourceSnapshotVersion || pool != D3DPOOL_DEFAULT ||
            (role != ResourceRole::Vertex && role != ResourceRole::Index))
            return false;

        const auto behavior = translate_resource_behavior(role, pool, usage);
        // DYNAMIC Map/NOOVERWRITE and MANAGED reset paths require a distinct
        // mutation/shadow owner; never label an initial upload as live parity.
        if (!behavior.descriptorExact ||
            behavior.lifetime != ResourceMirrorLifetime::DeviceGeneration ||
            behavior.usage != D3D11_USAGE_DEFAULT ||
            behavior.cpuAccessFlags != 0 || behavior.requiresCpuShadow)
            return false;

        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        if (role == ResourceRole::Vertex) {
            if (indexFormat != D3DFMT_UNKNOWN || !vertexStride ||
                byteWidth % vertexStride != 0)
                return false;
        } else {
            const auto translated = translate_resource_format(
                indexFormat, ResourceRole::Index);
            if (!translated.exact || vertexStride != 0)
                return false;
            format = translated.format;
            const UINT indexBytes = format == DXGI_FORMAT_R16_UINT ? 2u : 4u;
            if (byteWidth % indexBytes != 0)
                return false;
        }

        const UINT requiredBind = role == ResourceRole::Vertex
            ? D3D11_BIND_VERTEX_BUFFER : D3D11_BIND_INDEX_BUFFER;
        if (behavior.bindFlags != requiredBind)
            return false;

        D3D11_BUFFER_DESC desc{};
        desc.ByteWidth = byteWidth;
        desc.Usage = D3D11_USAGE_DEFAULT;
        desc.BindFlags = requiredBind;
        D3D11_SUBRESOURCE_DATA initial{};
        initial.pSysMem = sourceBytes;
        Microsoft::WRL::ComPtr<ID3D11Buffer> buffer;
        if (FAILED(device->CreateBuffer(
                &desc, &initial, buffer.GetAddressOf())) || !buffer)
            return false;
        device_ = device;
        buffer_ = std::move(buffer);
        role_ = role;
        format_ = format;
        byte_width_ = byteWidth;
        stride_ = vertexStride;
        generation_ = deviceGeneration;
        source_version_ = sourceSnapshotVersion;
        if (!descriptor_exact()) {
            shutdown();
            return false;
        }
        return true;
    }

    bool descriptor_exact() const noexcept {
        if (!buffer_ || !device_ || !generation_ || !source_version_)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> owningDevice;
        buffer_->GetDevice(owningDevice.GetAddressOf());
        if (owningDevice.Get() != device_.Get())
            return false;
        D3D11_BUFFER_DESC desc{};
        buffer_->GetDesc(&desc);
        return desc.ByteWidth == byte_width_ &&
            desc.Usage == D3D11_USAGE_DEFAULT &&
            desc.BindFlags == (role_ == ResourceRole::Vertex
                ? D3D11_BIND_VERTEX_BUFFER : D3D11_BIND_INDEX_BUFFER) &&
            desc.CPUAccessFlags == 0 && desc.MiscFlags == 0 &&
            desc.StructureByteStride == 0 &&
            (role_ == ResourceRole::Vertex
                ? format_ == DXGI_FORMAT_UNKNOWN && stride_ != 0
                : (format_ == DXGI_FORMAT_R16_UINT ||
                   format_ == DXGI_FORMAT_R32_UINT) && stride_ == 0);
    }

    bool bind(ID3D11DeviceContext* context,
              std::uint64_t currentGeneration,
              std::uint64_t currentSnapshotVersion) const noexcept {
        if (!same_immediate_device(context) || !descriptor_exact() ||
            currentGeneration != generation_ ||
            currentSnapshotVersion != source_version_)
            return false;
        if (role_ == ResourceRole::Vertex) {
            ID3D11Buffer* raw = buffer_.Get();
            const UINT offset = 0;
            context->IASetVertexBuffers(0, 1, &raw, &stride_, &offset);
        } else {
            context->IASetIndexBuffer(buffer_.Get(), format_, 0);
        }
        return binding_exact(context, currentGeneration, currentSnapshotVersion);
    }

    bool binding_exact(ID3D11DeviceContext* context,
                       std::uint64_t currentGeneration,
                       std::uint64_t currentSnapshotVersion) const noexcept {
        if (!same_immediate_device(context) || !descriptor_exact() ||
            currentGeneration != generation_ ||
            currentSnapshotVersion != source_version_)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Buffer> live;
        if (role_ == ResourceRole::Vertex) {
            UINT liveStride = 0, offset = 1;
            context->IAGetVertexBuffers(0, 1, live.GetAddressOf(),
                                         &liveStride, &offset);
            return live.Get() == buffer_.Get() &&
                liveStride == stride_ && offset == 0;
        }
        DXGI_FORMAT liveFormat = DXGI_FORMAT_UNKNOWN;
        UINT offset = 1;
        context->IAGetIndexBuffer(live.GetAddressOf(), &liveFormat, &offset);
        return live.Get() == buffer_.Get() &&
            liveFormat == format_ && offset == 0;
    }

    void shutdown() noexcept {
        buffer_.Reset();
        device_.Reset();
        role_ = ResourceRole::Vertex;
        format_ = DXGI_FORMAT_UNKNOWN;
        byte_width_ = stride_ = 0;
        generation_ = source_version_ = 0;
    }

    [[nodiscard]] ID3D11Buffer* buffer() const noexcept { return buffer_.Get(); }
private:
    bool same_immediate_device(ID3D11DeviceContext* context) const noexcept {
        if (!context || !device_ ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> owner;
        context->GetDevice(owner.GetAddressOf());
        return owner.Get() == device_.Get();
    }
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer_;
    ResourceRole role_ = ResourceRole::Vertex;
    DXGI_FORMAT format_ = DXGI_FORMAT_UNKNOWN;
    UINT byte_width_ = 0;
    UINT stride_ = 0;
    std::uint64_t generation_ = 0;
    std::uint64_t source_version_ = 0;
};
} // namespace outrun::vr::dx11
