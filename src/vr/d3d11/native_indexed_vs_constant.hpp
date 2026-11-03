#pragma once
// R191: owned, immutable VS b0 transform snapshot for the dormant native indexed path.
// Each D3D9 source revision gets a NEW D3D11 buffer; an old bound buffer cannot
// become a new draw-ready snapshot by changing only an integer receipt.
#include "native_indexed_target_viewport.hpp"
#include <cmath>
#include <cstdint>
#include <wrl/client.h>

namespace outrun::vr::dx11 {
struct alignas(16) NativeVsTransformR191 {
    float offsetX, offsetY, scaleX, scaleY;
};
static_assert(sizeof(NativeVsTransformR191) == 16);

class NativeVsConstantSnapshotR191 final {
public:
    bool initialize(ID3D11Device* device, NativeVsTransformR191 source,
                    std::uint64_t generation, std::uint64_t snapshotVersion) noexcept {
        shutdown();
        if (!device || !generation || !snapshotVersion ||
            !std::isfinite(source.offsetX) || !std::isfinite(source.offsetY) ||
            !std::isfinite(source.scaleX) || !std::isfinite(source.scaleY) ||
            source.scaleX == 0.f || source.scaleY == 0.f)
            return false;
        D3D11_BUFFER_DESC desc{};
        desc.ByteWidth = sizeof(NativeVsTransformR191);
        desc.Usage = D3D11_USAGE_IMMUTABLE;
        desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
        D3D11_SUBRESOURCE_DATA data{};
        data.pSysMem = &source;
        Microsoft::WRL::ComPtr<ID3D11Buffer> fresh;
        if (FAILED(device->CreateBuffer(&desc, &data, fresh.GetAddressOf())) || !fresh)
            return false;
        device_ = device;
        buffer_ = std::move(fresh);
        generation_ = generation;
        version_ = snapshotVersion;
        return descriptor_exact();
    }

    bool bind_vs_b0(ID3D11DeviceContext* context, std::uint64_t generation,
                    std::uint64_t version) const noexcept {
        if (!same_immediate_device(context) || !descriptor_exact() ||
            generation != generation_ || version != version_)
            return false;
        ID3D11Buffer* raw = buffer_.Get();
        context->VSSetConstantBuffers(0, 1, &raw);
        return binding_exact(context, generation, version);
    }

    bool binding_exact(ID3D11DeviceContext* context, std::uint64_t generation,
                       std::uint64_t version) const noexcept {
        if (!same_immediate_device(context) || !descriptor_exact() ||
            generation != generation_ || version != version_)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Buffer> live;
        context->VSGetConstantBuffers(0, 1, live.GetAddressOf());
        return live.Get() == buffer_.Get();
    }

    void shutdown() noexcept {
        buffer_.Reset();
        device_.Reset();
        generation_ = 0;
        version_ = 0;
    }

private:
    bool descriptor_exact() const noexcept {
        if (!buffer_ || !device_ || !generation_ || !version_)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> actualDevice;
        buffer_->GetDevice(actualDevice.GetAddressOf());
        if (actualDevice.Get() != device_.Get()) return false;
        D3D11_BUFFER_DESC desc{};
        buffer_->GetDesc(&desc);
        return desc.ByteWidth == sizeof(NativeVsTransformR191) &&
            desc.Usage == D3D11_USAGE_IMMUTABLE &&
            desc.BindFlags == D3D11_BIND_CONSTANT_BUFFER &&
            desc.CPUAccessFlags == 0 && desc.MiscFlags == 0 &&
            desc.StructureByteStride == 0;
    }
    bool same_immediate_device(ID3D11DeviceContext* context) const noexcept {
        if (!context || !device_ ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> device;
        context->GetDevice(device.GetAddressOf());
        return device.Get() == device_.Get();
    }
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer_;
    std::uint64_t generation_ = 0;
    std::uint64_t version_ = 0;
};

[[nodiscard]] inline bool verified_indexed_vs_transform_draw_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    const NativeVsConstantSnapshotR191& transform,
    ID3D11DeviceContext* context, UINT startIndex, UINT indexCount, INT baseVertex,
    std::uint64_t generation, std::uint64_t vbVersion, std::uint64_t ibVersion,
    std::uint64_t vsVersion, UINT targetWidth, UINT targetHeight,
    DXGI_FORMAT targetFormat, ID3D11RenderTargetView* expectedRtv) noexcept {
    return verified_indexed_full_target_draw_ready(
               vb, ib, context, startIndex, indexCount, baseVertex,
               generation, vbVersion, ibVersion, targetWidth, targetHeight,
               targetFormat, expectedRtv) &&
           transform.binding_exact(context, generation, vsVersion);
}
} // namespace outrun::vr::dx11
