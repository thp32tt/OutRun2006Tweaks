#include "../src/vr/d3d11/native_game_gpu_output_preserve.hpp"
#include <Windows.h>
#include <d3d11.h>
#include <wrl/client.h>
#include <cstdio>
using Microsoft::WRL::ComPtr;
using outrun::vr::dx11::live_game_frame::ScopedNativeGameGpuTransferOutputs;

static bool run_probe() {
    const D3D_FEATURE_LEVEL requested[] = {D3D_FEATURE_LEVEL_11_0};
    D3D_FEATURE_LEVEL created{};
    ComPtr<ID3D11Device> device;
    ComPtr<ID3D11DeviceContext> context;
    if (FAILED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr,
            0u, requested, 1u, D3D11_SDK_VERSION,
            device.GetAddressOf(), &created, context.GetAddressOf())) ||
        !device || !context || created != D3D_FEATURE_LEVEL_11_0)
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    desc.Width = 64u; desc.Height = 64u;
    desc.MipLevels = 1u; desc.ArraySize = 1u;
    desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    desc.SampleDesc.Count = 1u;
    desc.Usage = D3D11_USAGE_DEFAULT;
    desc.BindFlags = D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> source, other, dest;
    ComPtr<ID3D11RenderTargetView> first, second;
    if (FAILED(device->CreateTexture2D(&desc, nullptr, &source)) ||
        FAILED(device->CreateTexture2D(&desc, nullptr, &other)) ||
        FAILED(device->CreateTexture2D(&desc, nullptr, &dest)) ||
        FAILED(device->CreateRenderTargetView(source.Get(), nullptr, &first)) ||
        FAILED(device->CreateRenderTargetView(other.Get(), nullptr, &second)))
        return false;
    std::fputs("00900 WARP: created color RTV\n", stderr);
    const float red[] = {1.f, 0.f, 0.f, 1.f};
    context->ClearRenderTargetView(first.Get(), red);

    D3D11_TEXTURE2D_DESC uavDesc = desc;
    uavDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    uavDesc.BindFlags = D3D11_BIND_UNORDERED_ACCESS;
    ComPtr<ID3D11Texture2D> csResource, psResource;
    ComPtr<ID3D11UnorderedAccessView> csUav, psUav;
    if (FAILED(device->CreateTexture2D(&uavDesc, nullptr, &csResource)) ||
        FAILED(device->CreateTexture2D(&uavDesc, nullptr, &psResource)) ||
        FAILED(device->CreateUnorderedAccessView(
            csResource.Get(), nullptr, &csUav)) ||
        FAILED(device->CreateUnorderedAccessView(
            psResource.Get(), nullptr, &psUav)))
        return false;
    std::fputs("00900 WARP: created PS and CS UAV\n", stderr);
    ID3D11RenderTargetView* attachments[] = {first.Get(), second.Get()};
    ID3D11UnorderedAccessView* ps[] = {psUav.Get()};
    ID3D11UnorderedAccessView* cs[] = {csUav.Get()};
    context->OMSetRenderTargetsAndUnorderedAccessViews(
        2u, attachments, nullptr, 2u, 1u, ps, nullptr);
    context->CSSetUnorderedAccessViews(0u, 1u, cs, nullptr);
    std::fputs("00900 WARP: bound game MRT/UAV outputs\n", stderr);
    bool detached = false;
    {
    std::fputs("00900 WARP: before GPU source detach\n", stderr);
        ScopedNativeGameGpuTransferOutputs outputs(context.Get());
        ID3D11RenderTargetView* actual[2]{};
        ID3D11UnorderedAccessView* actualCS = nullptr;
        ID3D11UnorderedAccessView* actualPS = nullptr;
        context->OMGetRenderTargets(2u, actual, nullptr);
        context->OMGetRenderTargetsAndUnorderedAccessViews(
            0u, nullptr, nullptr, 2u, 1u, &actualPS);
        context->CSGetUnorderedAccessViews(0u, 1u, &actualCS);
        detached = !actual[0] && !actual[1] && !actualCS && !actualPS;
        for (auto* target : actual) if (target) target->Release();
        if (actualCS) actualCS->Release();
        if (actualPS) actualPS->Release();
        if (!detached) return false;
        // Real GPU copy from still-game-owned RTV0 to a separate frame
        // texture, while both MRTs and PS/CS UAV outputs are suspended.
    std::fputs("00900 WARP: detached output, starting real GPU copy\n", stderr);
        context->CopyResource(dest.Get(), source.Get());
    }
    std::fputs("00900 WARP: output restored\n", stderr);
    ID3D11RenderTargetView* restored[2]{};
    ID3D11UnorderedAccessView* restoredPS = nullptr;
    ID3D11UnorderedAccessView* restoredCS = nullptr;
    context->OMGetRenderTargetsAndUnorderedAccessViews(
        2u, restored, nullptr, 2u, 1u, &restoredPS);
    context->CSGetUnorderedAccessViews(0u, 1u, &restoredCS);
    const bool preserved =
        restored[0] == first.Get() && restored[1] == second.Get() &&
        restoredPS == psUav.Get() && restoredCS == csUav.Get();
    for (auto* target : restored) if (target) target->Release();
    if (restoredPS) restoredPS->Release();
    if (restoredCS) restoredCS->Release();

    std::fputs("00900 WARP: checked GPU output bindings\n", stderr);
    D3D11_TEXTURE2D_DESC staging = desc;
    staging.Usage = D3D11_USAGE_STAGING;
    staging.BindFlags = 0u;
    staging.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> readable;
    if (FAILED(device->CreateTexture2D(&staging, nullptr, &readable)))
        return false;
    context->CopyResource(readable.Get(), dest.Get());
    D3D11_MAPPED_SUBRESOURCE map{};
    if (FAILED(context->Map(readable.Get(), 0u, D3D11_MAP_READ, 0u, &map)))
        return false;
    const auto* pixel = static_cast<const unsigned char*>(map.pData);
    const bool copied = pixel && pixel[0] == 0u && pixel[1] == 0u &&
        pixel[2] == 255u && pixel[3] == 255u;
    context->Unmap(readable.Get(), 0u);
    std::fputs("00900 WARP: pixel Map/Unmap passed\n", stderr);
    context->OMSetRenderTargets(0u, nullptr, nullptr);
    ID3D11UnorderedAccessView* unbound = nullptr;
    context->CSSetUnorderedAccessViews(0u, 1u, &unbound, nullptr);
    return preserved && copied;
}
int main() {
    const bool passed = run_probe();
    if (!passed) std::fputs("DX11 native desktop GPU output binding preservation failed\n", stderr);
    return passed ? 0 : 1;
}
