#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>

#include <d3d11.h>
#include <wrl/client.h>

#include "vr/d3d11/native_backend.hpp"

namespace outrun::vr::dx11 {
struct NativeBackendResizeProbeAccess {
    static bool initialize_from_warp(
        NativeBackend& backend,
        ID3D11Device* device,
        ID3D11DeviceContext* context,
        std::uint32_t width,
        std::uint32_t height) {
        if (!device || !context || !width || !height)
            return false;
        backend.device_ = device;
        backend.context_ = context;
        backend.config_.width = width;
        backend.config_.height = height;
        backend.config_.color_format = DXGI_FORMAT_B8G8R8A8_UNORM;
        return backend.create_color_target(
            width, height, backend.config_.color_format);
    }
};
} // namespace outrun::vr::dx11

namespace {
using Microsoft::WRL::ComPtr;
using outrun::vr::dx11::NativeBackend;
using outrun::vr::dx11::NativeBackendResizeProbeAccess;

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "R177 WARP resize failure: " << message << "\n";
        std::exit(1);
    }
}

void verify_target_clear(
    NativeBackend& backend,
    const std::array<float, 4>& color,
    const std::array<unsigned int, 4>& expectedBgra) {
    require(backend.ready(), "target must be ready for rendering");
    backend.begin_frame(color);
    D3D11_TEXTURE2D_DESC desc{};
    backend.color_texture()->GetDesc(&desc);
    require(desc.Width == backend.config().width &&
                desc.Height == backend.config().height,
            "native texture and committed viewport dimensions disagree");
    D3D11_TEXTURE2D_DESC stagingDesc = desc;
    stagingDesc.Usage = D3D11_USAGE_STAGING;
    stagingDesc.BindFlags = 0;
    stagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    stagingDesc.MiscFlags = 0;
    ComPtr<ID3D11Texture2D> staging;
    require(SUCCEEDED(backend.device()->CreateTexture2D(
                &stagingDesc, nullptr, staging.GetAddressOf())) &&
                staging != nullptr,
            "create staging target readback");
    backend.context()->CopyResource(staging.Get(), backend.color_texture());
    D3D11_MAPPED_SUBRESOURCE mapped{};
    require(SUCCEEDED(backend.context()->Map(
                staging.Get(), 0, D3D11_MAP_READ, 0, &mapped)) &&
                mapped.pData != nullptr &&
                mapped.RowPitch >= static_cast<UINT>(desc.Width) * 4u,
            "map WARP color target staging");
    const auto* px = static_cast<const unsigned char*>(mapped.pData);
    const std::array<unsigned int, 4> got{
        px[0], px[1], px[2], px[3]
    };
    backend.context()->Unmap(staging.Get(), 0);
    require(got == expectedBgra, "color RTV clear/readback differs");
}

} // namespace

int main() {
    ComPtr<ID3D11Device> device;
    ComPtr<ID3D11DeviceContext> context;
    D3D_FEATURE_LEVEL level = D3D_FEATURE_LEVEL_9_1;
    const D3D_FEATURE_LEVEL levels[]{
        D3D_FEATURE_LEVEL_11_0,
        D3D_FEATURE_LEVEL_10_1,
        D3D_FEATURE_LEVEL_10_0
    };
    require(SUCCEEDED(D3D11CreateDevice(
                nullptr, D3D_DRIVER_TYPE_WARP, nullptr,
                D3D11_CREATE_DEVICE_BGRA_SUPPORT, levels,
                static_cast<UINT>(std::size(levels)), D3D11_SDK_VERSION,
                device.GetAddressOf(), &level,
                context.GetAddressOf())) &&
                device != nullptr && context != nullptr,
            "create WARP device");
    NativeBackend backend;
    require(NativeBackendResizeProbeAccess::initialize_from_warp(
                backend, device.Get(), context.Get(), 16, 16),
            "create initial native texture+RTV+SRV");
    ComPtr<ID3D11Texture2D> originalTexture = backend.color_texture();
    ComPtr<ID3D11RenderTargetView> originalRtv = backend.color_rtv();
    ComPtr<ID3D11ShaderResourceView> originalSrv = backend.color_srv();
    verify_target_clear(
        backend, {1.0f, 0.0f, 0.0f, 1.0f},
        {0u, 0u, 255u, 255u});

    // A repeated size notification must not reallocate live native objects.
    require(backend.resize(16, 16) &&
                backend.color_texture() == originalTexture.Get() &&
                backend.color_rtv() == originalRtv.Get() &&
                backend.color_srv() == originalSrv.Get(),
            "same-size resize changed live resource identities");
    // Overflow dimensions deterministically reject at CreateTexture2D on
    // WARP, after the production code has already entered the staged path.
    require(!backend.resize(UINT32_MAX, UINT32_MAX) &&
                backend.ready() &&
                backend.color_texture() == originalTexture.Get() &&
                backend.color_rtv() == originalRtv.Get() &&
                backend.color_srv() == originalSrv.Get() &&
                backend.config().width == 16 &&
                backend.config().height == 16,
            "failed allocation destroyed the published native target");
    verify_target_clear(
        backend, {1.0f, 0.0f, 0.0f, 1.0f},
        {0u, 0u, 255u, 255u});

    require(backend.resize(32, 24) && backend.ready() &&
                backend.color_texture() != originalTexture.Get() &&
                backend.color_rtv() != originalRtv.Get() &&
                backend.color_srv() != originalSrv.Get() &&
                backend.config().width == 32 &&
                backend.config().height == 24,
            "successful resize did not commit a complete new target");
    verify_target_clear(
        backend, {0.0f, 1.0f, 0.0f, 1.0f},
        {0u, 255u, 0u, 255u});
    backend.shutdown();
    require(!backend.ready(), "shutdown must release target readiness");
    std::cout << "DX11 R177 same-size native identity: PASS\n"
              << "DX11 R177 failed native target allocation rollback: PASS\n"
              << "DX11 R177 live WARP clear/readback before and after resize: PASS\n";
    return 0;
}
