#include "vr/d3d11/surface_mirror.hpp"

#include <d3d11.h>
#include <iostream>
#include <wrl/client.h>

namespace
{
    int fail(const char* message)
    {
        std::cerr << message << "\n";
        return 1;
    }
}

int main()
{
    Microsoft::WRL::ComPtr<ID3D11Device> device;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> context;
    D3D_FEATURE_LEVEL featureLevel = D3D_FEATURE_LEVEL_9_1;
    const HRESULT hr = D3D11CreateDevice(
        nullptr,
        D3D_DRIVER_TYPE_WARP,
        nullptr,
        D3D11_CREATE_DEVICE_BGRA_SUPPORT,
        nullptr,
        0,
        D3D11_SDK_VERSION,
        device.ReleaseAndGetAddressOf(),
        &featureLevel,
        context.ReleaseAndGetAddressOf());
    if (FAILED(hr) || !device || !context)
        return fail("failed to create WARP D3D11 device");

    using namespace outrun::vr::dx11;

    NativeSurfaceMirror color;
    if (!color.initialize(
            device.Get(),
            ResourceRole::Color,
            64,
            32,
            D3DFMT_A8R8G8B8,
            D3DPOOL_DEFAULT,
            D3DUSAGE_RENDERTARGET,
            D3DMULTISAMPLE_NONE,
            0))
        return fail("color surface mirror initialization failed");
    if (!color.ready() || !color.render_target_view() ||
        color.depth_stencil_view() || !color.descriptor_exact(device.Get()))
        return fail("color surface mirror readiness/descriptor drift");

    const auto firstGeneration = color.device_generation();
    color.observe_device_reset();
    if (color.ready() || color.texture() || color.render_target_view() ||
        color.mirror_generation() != 0 ||
        color.device_generation() == firstGeneration)
        return fail("color surface mirror did not invalidate on Reset");
    if (!color.recreate(device.Get()) || !color.ready() ||
        color.mirror_generation() != color.device_generation() ||
        !color.descriptor_exact(device.Get()))
        return fail("color surface mirror did not recreate for new generation");

    NativeSurfaceMirror depth;
    if (!depth.initialize(
            device.Get(),
            ResourceRole::DepthStencil,
            64,
            32,
            D3DFMT_D24S8,
            D3DPOOL_DEFAULT,
            D3DUSAGE_DEPTHSTENCIL,
            D3DMULTISAMPLE_NONE,
            0))
        return fail("depth surface mirror initialization failed");
    if (!depth.ready() || !depth.depth_stencil_view() ||
        depth.render_target_view() || !depth.descriptor_exact(device.Get()))
        return fail("depth surface mirror readiness/descriptor drift");

    const auto surfacePair = compose_surface_pair_readiness(
        device.Get(), color, depth);
    if (!surfacePair.ready || !surfacePair.deviceMatches ||
        !surfacePair.dimensionsMatch || !surfacePair.generationsCurrent ||
        !surfacePair.componentSerialsPresent || surfacePair.snapshotToken == 0 ||
        !validate_surface_pair_snapshot(
            device.Get(), color, depth, surfacePair.snapshotToken))
        return fail("surface pair readiness did not compose exact mirrors");

    const auto firstPairToken = surfacePair.snapshotToken;
    depth.observe_device_reset();
    if (validate_surface_pair_snapshot(
            device.Get(), color, depth, firstPairToken))
        return fail("stale surface pair snapshot survived depth Reset");
    if (!depth.recreate(device.Get()))
        return fail("depth surface mirror did not recreate after Reset");
    const auto recreatedPair = compose_surface_pair_readiness(
        device.Get(), color, depth);
    if (!recreatedPair.ready || recreatedPair.snapshotToken == firstPairToken ||
        !validate_surface_pair_snapshot(
            device.Get(), color, depth, recreatedPair.snapshotToken))
        return fail("surface pair snapshot did not refresh after recreation");

    NativeSurfaceMirror mismatchedDepth;
    if (!mismatchedDepth.initialize(
            device.Get(), ResourceRole::DepthStencil, 63, 32, D3DFMT_D24S8,
            D3DPOOL_DEFAULT, D3DUSAGE_DEPTHSTENCIL,
            D3DMULTISAMPLE_NONE, 0))
        return fail("mismatched depth setup failed");
    if (compose_surface_pair_readiness(
            device.Get(), color, mismatchedDepth).ready)
        return fail("surface pair accepted mismatched dimensions");

    if (color.descriptor_exact(nullptr) || depth.descriptor_exact(nullptr))
        return fail("surface descriptor validation accepted null device");
    color.shutdown();
    if (color.ready() || color.texture() || color.render_target_view() ||
        color.depth_stencil_view() || color.mirror_generation() != 0)
        return fail("surface mirror shutdown retained GPU ownership");

    NativeSurfaceMirror invalidPool;
    if (invalidPool.initialize(
            device.Get(),
            ResourceRole::Color,
            16,
            16,
            D3DFMT_A8R8G8B8,
            D3DPOOL_MANAGED,
            D3DUSAGE_RENDERTARGET,
            D3DMULTISAMPLE_NONE,
            0))
        return fail("MANAGED render target must remain fail-closed");

    NativeSurfaceMirror invalidUsage;
    if (invalidUsage.initialize(
            device.Get(),
            ResourceRole::DepthStencil,
            16,
            16,
            D3DFMT_D24S8,
            D3DPOOL_DEFAULT,
            0,
            D3DMULTISAMPLE_NONE,
            0))
        return fail("depth surface without DEPTHSTENCIL usage must fail closed");

    NativeSurfaceMirror unprovenMsaa;
    if (unprovenMsaa.initialize(
            device.Get(),
            ResourceRole::Color,
            16,
            16,
            D3DFMT_A8R8G8B8,
            D3DPOOL_DEFAULT,
            D3DUSAGE_RENDERTARGET,
            D3DMULTISAMPLE_2_SAMPLES,
            0))
        return fail("unproven D3D9-to-DXGI MSAA mapping must fail closed");

    std::cout << "DX11 dormant surface mirror probe passed\n";
    return 0;
}
