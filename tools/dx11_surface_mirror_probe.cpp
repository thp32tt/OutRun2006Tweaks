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

    // R179: compressed texture data may be sampled but never advertised
    // as an exact native RTV; vertex-buffer roles have no texture format.
    for (const auto source : {
             D3DFMT_DXT1, D3DFMT_DXT3, D3DFMT_DXT5 })
    {
        const auto textureFormat =
            translate_resource_format(source, ResourceRole::Texture);
        const auto targetFormat =
            translate_resource_format(source, ResourceRole::Color);
        if (!textureFormat.exact ||
            textureFormat.format == DXGI_FORMAT_UNKNOWN ||
            targetFormat.exact ||
            targetFormat.format != DXGI_FORMAT_UNKNOWN)
            return fail("R179 compressed texture incorrectly qualifies as RTV");

        // Exercise the actual dormant D3D11 texture/RTV owner, not only
        // the format helper. It must reject all block-compressed color
        // targets before creating or retaining any GPU resources.
        NativeSurfaceMirror invalidCompressedTarget;
        if (invalidCompressedTarget.initialize(
                device.Get(), ResourceRole::Color, 16, 16,
                source, D3DPOOL_DEFAULT, D3DUSAGE_RENDERTARGET,
                D3DMULTISAMPLE_NONE, 0) ||
            invalidCompressedTarget.ready() ||
            invalidCompressedTarget.texture() ||
            invalidCompressedTarget.render_target_view())
            return fail("R179 compressed NativeSurfaceMirror owner accepted RTV");
    }
    if (translate_resource_format(
            D3DFMT_A8R8G8B8, ResourceRole::Vertex).exact ||
        !translate_resource_format(
            D3DFMT_A8R8G8B8, ResourceRole::Color).exact)
        return fail("R179 non-texture role classified as a texture format");

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

    NativeSurfacePairBinding binding;
    if (!binding.initialize(device.Get(), color, depth, recreatedPair) ||
        !binding.ready() ||
        binding.surface_pair_snapshot_token() != recreatedPair.snapshotToken)
        return fail("R130 surface-pair binding owner initialization failed");
    if (!binding.apply(context.Get(), color, depth))
        return fail("R130 exact surface-pair binding failed");

    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> boundRtv;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilView> boundDsv;
    context->OMGetRenderTargets(
        1, boundRtv.ReleaseAndGetAddressOf(), boundDsv.ReleaseAndGetAddressOf());
    if (boundRtv.Get() != color.render_target_view() ||
        boundDsv.Get() != depth.depth_stencil_view())
        return fail("R130 OM render-target binding identity drifted");

    const auto liveTargetBinding =
        binding.binding_readiness(context.Get(), color, depth);
    if (!liveTargetBinding.inputValid ||
        !liveTargetBinding.ownerReady ||
        !liveTargetBinding.pairCurrent ||
        !liveTargetBinding.contextMatches ||
        !liveTargetBinding.colorViewCurrent ||
        !liveTargetBinding.depthViewCurrent ||
        !liveTargetBinding.rtvBoundExact ||
        !liveTargetBinding.dsvBoundExact ||
        !liveTargetBinding.unorderedAccessClear ||
        !liveTargetBinding.ready ||
        liveTargetBinding.surfacePairSnapshotToken != recreatedPair.snapshotToken ||
        liveTargetBinding.snapshotToken == 0 ||
        !binding.validate_binding_snapshot(
            context.Get(), color, depth, liveTargetBinding.snapshotToken))
        return fail("R145 live OM target binding seals exact RTV DSV identity");

    // R149: a deferred context can belong to this same device but cannot
    // constitute the live immediate OM binding required for native draw.
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> deferredContext;
    if (FAILED(device->CreateDeferredContext(
            0, deferredContext.ReleaseAndGetAddressOf())) ||
        !deferredContext ||
        deferredContext->GetType() != D3D11_DEVICE_CONTEXT_DEFERRED)
        return fail("R149 deferred context WARP setup failed");
    if (binding.apply(deferredContext.Get(), color, depth))
        return fail("R149 deferred context incorrectly accepted live OM apply");
    const auto deferredBinding =
        binding.binding_readiness(deferredContext.Get(), color, depth);
    if (deferredBinding.inputValid || deferredBinding.ready ||
        deferredBinding.snapshotToken != 0 ||
        binding.validate_binding_snapshot(
            deferredContext.Get(), color, depth, liveTargetBinding.snapshotToken))
        return fail("R149 deferred context incorrectly promoted live OM readiness");
    if (!binding.validate_binding_snapshot(
            context.Get(), color, depth, liveTargetBinding.snapshotToken))
        return fail("R149 deferred rejection mutated immediate OM state");

    NativeSurfaceMirror extraColor;
    if (!extraColor.initialize(
            device.Get(),
            ResourceRole::Color,
            64,
            32,
            D3DFMT_A8R8G8B8,
            D3DPOOL_DEFAULT,
            D3DUSAGE_RENDERTARGET,
            D3DMULTISAMPLE_NONE,
            0))
        return fail("R145 extra RTV surface setup failed");
    ID3D11RenderTargetView* extraRtvs[2] = {
        color.render_target_view(),
        extraColor.render_target_view(),
    };
    context->OMSetRenderTargets(
        2, extraRtvs, depth.depth_stencil_view());
    const auto extraTargetBinding =
        binding.binding_readiness(context.Get(), color, depth);
    if (!extraTargetBinding.inputValid ||
        !extraTargetBinding.ownerReady ||
        !extraTargetBinding.pairCurrent ||
        !extraTargetBinding.contextMatches ||
        !extraTargetBinding.colorViewCurrent ||
        !extraTargetBinding.depthViewCurrent ||
        extraTargetBinding.rtvBoundExact ||
        !extraTargetBinding.dsvBoundExact ||
        !extraTargetBinding.unorderedAccessClear ||
        extraTargetBinding.ready ||
        extraTargetBinding.snapshotToken != 0 ||
        binding.validate_binding_snapshot(
            context.Get(), color, depth, liveTargetBinding.snapshotToken))
        return fail("R145 live OM target binding rejects extra RTV slot");

    if (featureLevel >= D3D_FEATURE_LEVEL_11_0) {
        D3D11_BUFFER_DESC uavBufferDesc{};
        uavBufferDesc.ByteWidth = 16;
        uavBufferDesc.Usage = D3D11_USAGE_DEFAULT;
        uavBufferDesc.BindFlags = D3D11_BIND_UNORDERED_ACCESS;
        uavBufferDesc.MiscFlags = D3D11_RESOURCE_MISC_BUFFER_STRUCTURED;
        uavBufferDesc.StructureByteStride = 4;

        Microsoft::WRL::ComPtr<ID3D11Buffer> unexpectedUavBuffer;
        if (FAILED(device->CreateBuffer(
                &uavBufferDesc, nullptr,
                unexpectedUavBuffer.ReleaseAndGetAddressOf())) ||
            !unexpectedUavBuffer)
            return fail("R146 unexpected OM UAV buffer setup failed");

        D3D11_UNORDERED_ACCESS_VIEW_DESC uavDesc{};
        uavDesc.Format = DXGI_FORMAT_UNKNOWN;
        uavDesc.ViewDimension = D3D11_UAV_DIMENSION_BUFFER;
        uavDesc.Buffer.FirstElement = 0;
        uavDesc.Buffer.NumElements = 4;
        Microsoft::WRL::ComPtr<ID3D11UnorderedAccessView> unexpectedUav;
        if (FAILED(device->CreateUnorderedAccessView(
                unexpectedUavBuffer.Get(), &uavDesc,
                unexpectedUav.ReleaseAndGetAddressOf())) ||
            !unexpectedUav)
            return fail("R146 unexpected OM UAV view setup failed");

        ID3D11RenderTargetView* exactRtv = color.render_target_view();
        ID3D11UnorderedAccessView* exactUav = unexpectedUav.Get();
        context->OMSetRenderTargetsAndUnorderedAccessViews(
            1, &exactRtv, depth.depth_stencil_view(),
            1, 1, &exactUav, nullptr);
        const auto unexpectedUavBinding =
            binding.binding_readiness(context.Get(), color, depth);
        if (!unexpectedUavBinding.inputValid ||
            !unexpectedUavBinding.ownerReady ||
            !unexpectedUavBinding.pairCurrent ||
            !unexpectedUavBinding.contextMatches ||
            !unexpectedUavBinding.colorViewCurrent ||
            !unexpectedUavBinding.depthViewCurrent ||
            !unexpectedUavBinding.rtvBoundExact ||
            !unexpectedUavBinding.dsvBoundExact ||
            unexpectedUavBinding.unorderedAccessClear ||
            unexpectedUavBinding.ready ||
            unexpectedUavBinding.snapshotToken != 0 ||
            binding.validate_binding_snapshot(
                context.Get(), color, depth, liveTargetBinding.snapshotToken))
            return fail("R146 live OM target binding rejects unexpected UAV");

        if (!binding.apply(context.Get(), color, depth))
            return fail("R146 live OM target apply did not clear unexpected UAV");
        const auto clearedUavBinding =
            binding.binding_readiness(context.Get(), color, depth);
        if (!clearedUavBinding.ready ||
            !clearedUavBinding.unorderedAccessClear ||
            clearedUavBinding.snapshotToken != liveTargetBinding.snapshotToken)
            return fail("R146 live OM target restore changed snapshot identity");
    }

    context->OMSetRenderTargets(0, nullptr, nullptr);
    const auto missingTargetBinding =
        binding.binding_readiness(context.Get(), color, depth);
    if (!missingTargetBinding.inputValid ||
        !missingTargetBinding.ownerReady ||
        !missingTargetBinding.pairCurrent ||
        !missingTargetBinding.contextMatches ||
        !missingTargetBinding.colorViewCurrent ||
        !missingTargetBinding.depthViewCurrent ||
        missingTargetBinding.rtvBoundExact ||
        missingTargetBinding.dsvBoundExact ||
        missingTargetBinding.ready ||
        missingTargetBinding.snapshotToken != 0 ||
        binding.validate_binding_snapshot(
            context.Get(), color, depth, liveTargetBinding.snapshotToken))
        return fail("R145 live OM target binding fails closed after RTV DSV unbind");

    if (!binding.apply(context.Get(), color, depth) ||
        !binding.validate_binding_snapshot(
            context.Get(), color, depth, liveTargetBinding.snapshotToken))
        return fail("R145 live OM target binding restores deterministic snapshot");

    Microsoft::WRL::ComPtr<ID3D11Device> foreignDevice;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> foreignContext;
    D3D_FEATURE_LEVEL foreignFeatureLevel = D3D_FEATURE_LEVEL_9_1;
    if (FAILED(D3D11CreateDevice(
            nullptr,
            D3D_DRIVER_TYPE_WARP,
            nullptr,
            D3D11_CREATE_DEVICE_BGRA_SUPPORT,
            nullptr,
            0,
            D3D11_SDK_VERSION,
            foreignDevice.ReleaseAndGetAddressOf(),
            &foreignFeatureLevel,
            foreignContext.ReleaseAndGetAddressOf())) ||
        !foreignDevice || !foreignContext)
        return fail("R130 foreign WARP device setup failed");
    if (binding.apply(foreignContext.Get(), color, depth))
        return fail("R130 foreign context did not fail closed");

    const auto boundPairToken = binding.surface_pair_snapshot_token();
    depth.observe_device_reset();
    if (binding.apply(context.Get(), color, depth))
        return fail("R130 stale binding survived depth Reset");
    if (!depth.recreate(device.Get()))
        return fail("R130 depth recreation after stale binding failed");
    const auto reboundPair = compose_surface_pair_readiness(
        device.Get(), color, depth);
    if (!reboundPair.ready || reboundPair.snapshotToken == boundPairToken)
        return fail("R130 recreated pair did not invalidate binding identity");
    if (binding.apply(context.Get(), color, depth))
        return fail("R130 stale binding survived mirror recreation");
    if (!binding.initialize(device.Get(), color, depth, reboundPair) ||
        !binding.apply(context.Get(), color, depth))
        return fail("R130 binding did not recover on refreshed pair");

    binding.shutdown();
    if (binding.ready() || binding.surface_pair_snapshot_token() != 0 ||
        binding.apply(context.Get(), color, depth))
        return fail("R130 binding shutdown retained bindable state");

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
    std::cout << "DX11 dormant surface-pair binding R130: PASS\n";
    std::cout << "DX11 live OM target binding R145: PASS\n";
    return 0;
}
