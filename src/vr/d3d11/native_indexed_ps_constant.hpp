#pragma once
// R192: exact immutable PS b0 color ownership for dormant native indexed draws.
// PS constants are separate from VS b0; a new source revision requires a new GPU buffer.
#include "native_indexed_vs_constant.hpp"
#include <cmath>
#include <cstdint>
#include <utility>
#include <wrl/client.h>

namespace outrun::vr::dx11 {
struct alignas(16) NativePsColorR192 {
    float red, green, blue, alpha;
};
static_assert(sizeof(NativePsColorR192) == 16);

class NativePsConstantSnapshotR192 final {
public:
    bool initialize(ID3D11Device* device, NativePsColorR192 source,
                    std::uint64_t generation, std::uint64_t version) noexcept {
        shutdown();
        const float colors[] = {source.red,source.green,source.blue,source.alpha};
        if (!device || !generation || !version) return false;
        for (const float c : colors)
            if (!std::isfinite(c) || c < 0.f || c > 1.f) return false;
        D3D11_BUFFER_DESC desc{};
        desc.ByteWidth = sizeof(NativePsColorR192);
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
        version_ = version;
        return descriptor_exact();
    }

    bool bind_ps_b0(ID3D11DeviceContext* context, std::uint64_t generation,
                    std::uint64_t version) const noexcept {
        if (!same_immediate_device(context) || !descriptor_exact() ||
            generation != generation_ || version != version_) return false;
        ID3D11Buffer* raw = buffer_.Get();
        context->PSSetConstantBuffers(0, 1, &raw);
        return binding_exact(context, generation, version);
    }

    bool binding_exact(ID3D11DeviceContext* context, std::uint64_t generation,
                       std::uint64_t version) const noexcept {
        if (!same_immediate_device(context) || !descriptor_exact() ||
            generation != generation_ || version != version_) return false;
        Microsoft::WRL::ComPtr<ID3D11Buffer> live;
        context->PSGetConstantBuffers(0, 1, live.GetAddressOf());
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
        if (!device_ || !buffer_ || !generation_ || !version_) return false;
        Microsoft::WRL::ComPtr<ID3D11Device> actualDevice;
        buffer_->GetDevice(actualDevice.GetAddressOf());
        if (actualDevice.Get() != device_.Get()) return false;
        D3D11_BUFFER_DESC desc{};
        buffer_->GetDesc(&desc);
        return desc.ByteWidth == sizeof(NativePsColorR192) &&
               desc.Usage == D3D11_USAGE_IMMUTABLE &&
               desc.BindFlags == D3D11_BIND_CONSTANT_BUFFER &&
               desc.CPUAccessFlags == 0 && desc.MiscFlags == 0 &&
               desc.StructureByteStride == 0;
    }
    bool same_immediate_device(ID3D11DeviceContext* context) const noexcept {
        if (!context || !device_ ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE) return false;
        Microsoft::WRL::ComPtr<ID3D11Device> liveDevice;
        context->GetDevice(liveDevice.GetAddressOf());
        return liveDevice.Get() == device_.Get();
    }
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer_;
    std::uint64_t generation_ = 0;
    std::uint64_t version_ = 0;
};

[[nodiscard]] inline bool verified_indexed_ps_color_draw_ready(
    const NativeLinearBufferMirror& vb, const NativeLinearBufferMirror& ib,
    const NativeVsConstantSnapshotR191& vsTransform,
    const NativePsConstantSnapshotR192& psColor,
    ID3D11DeviceContext* context, UINT startIndex, UINT indexCount, INT baseVertex,
    std::uint64_t generation, std::uint64_t vbVersion, std::uint64_t ibVersion,
    std::uint64_t vsVersion, std::uint64_t psVersion,
    UINT targetWidth, UINT targetHeight, DXGI_FORMAT targetFormat,
    ID3D11RenderTargetView* expectedRtv) noexcept {
    return verified_indexed_vs_transform_draw_ready(
               vb, ib, vsTransform, context, startIndex, indexCount, baseVertex,
               generation, vbVersion, ibVersion, vsVersion, targetWidth,
               targetHeight, targetFormat, expectedRtv) &&
           psColor.binding_exact(context, generation, psVersion);
}
} // namespace outrun::vr::dx11
