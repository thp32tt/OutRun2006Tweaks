#include "native_backend.hpp"

#include "pipeline_translation.hpp"

#include <array>
#include <cstring>
#include <dxgi1_2.h>
#include <utility>

namespace outrun::vr::dx11 {
namespace {

bool same_luid(const LUID& a, const LUID& b) noexcept {
    return a.LowPart == b.LowPart && a.HighPart == b.HighPart;
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