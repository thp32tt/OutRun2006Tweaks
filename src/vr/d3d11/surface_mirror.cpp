#include "surface_mirror.hpp"

#include <array>
#include <utility>

namespace outrun::vr::dx11
{
    bool NativeSurfaceMirror::initialize(
        ID3D11Device* device,
        ResourceRole role,
        UINT width,
        UINT height,
        D3DFORMAT sourceFormat,
        D3DPOOL sourcePool,
        DWORD sourceUsage,
        D3DMULTISAMPLE_TYPE sourceMultisampleType,
        DWORD sourceMultisampleQuality) noexcept
    {
        shutdown();

        role_ = role;
        width_ = width;
        height_ = height;
        source_format_ = sourceFormat;
        source_pool_ = sourcePool;
        source_usage_ = sourceUsage;
        source_multisample_type_ = sourceMultisampleType;
        source_multisample_quality_ = sourceMultisampleQuality;
        metadata_valid_ = source_descriptor_exact();
        if (!metadata_valid_)
            return false;

        return recreate(device);
    }

    bool NativeSurfaceMirror::source_descriptor_exact() const noexcept
    {
        if ((role_ != ResourceRole::Color &&
             role_ != ResourceRole::DepthStencil) ||
            width_ == 0 || height_ == 0)
            return false;

        // D3D9 and DXGI multisample quality semantics are not assumed to be
        // interchangeable. Keep non-MSAA surfaces exact and fail closed until
        // an adapter/quality-level translation is proven.
        if (source_multisample_type_ != D3DMULTISAMPLE_NONE ||
            source_multisample_quality_ != 0)
            return false;

        const auto format = translate_resource_format(source_format_, role_);
        const auto behavior =
            translate_resource_behavior(role_, source_pool_, source_usage_);
        const UINT expectedBind =
            role_ == ResourceRole::Color
                ? D3D11_BIND_RENDER_TARGET
                : D3D11_BIND_DEPTH_STENCIL;
        return format.exact &&
            behavior.descriptorExact &&
            behavior.lifetime == ResourceMirrorLifetime::DeviceGeneration &&
            behavior.usage == D3D11_USAGE_DEFAULT &&
            behavior.bindFlags == expectedBind &&
            behavior.cpuAccessFlags == 0 &&
            !behavior.requiresCpuShadow &&
            !behavior.requiresMutationTelemetry;
    }

    bool NativeSurfaceMirror::recreate(ID3D11Device* device) noexcept
    {
        release_mirror();
        if (!metadata_valid_ || !device || !source_descriptor_exact())
            return false;

        const auto format = translate_resource_format(source_format_, role_);
        const auto behavior =
            translate_resource_behavior(role_, source_pool_, source_usage_);
        if (!format.exact || !behavior.descriptorExact)
            return false;

        D3D11_TEXTURE2D_DESC textureDesc{};
        textureDesc.Width = width_;
        textureDesc.Height = height_;
        textureDesc.MipLevels = 1;
        textureDesc.ArraySize = 1;
        textureDesc.Format = format.format;
        textureDesc.SampleDesc.Count = 1;
        textureDesc.SampleDesc.Quality = 0;
        textureDesc.Usage = behavior.usage;
        textureDesc.BindFlags = behavior.bindFlags;
        textureDesc.CPUAccessFlags = behavior.cpuAccessFlags;
        textureDesc.MiscFlags = 0;

        Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
        if (FAILED(device->CreateTexture2D(
                &textureDesc, nullptr, texture.ReleaseAndGetAddressOf())) ||
            !texture)
            return false;

        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv;
        Microsoft::WRL::ComPtr<ID3D11DepthStencilView> dsv;
        if (role_ == ResourceRole::Color)
        {
            D3D11_RENDER_TARGET_VIEW_DESC viewDesc{};
            viewDesc.Format = format.format;
            viewDesc.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2D;
            viewDesc.Texture2D.MipSlice = 0;
            if (FAILED(device->CreateRenderTargetView(
                    texture.Get(), &viewDesc, rtv.ReleaseAndGetAddressOf())) ||
                !rtv)
                return false;
        }
        else
        {
            D3D11_DEPTH_STENCIL_VIEW_DESC viewDesc{};
            viewDesc.Format = format.format;
            viewDesc.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
            viewDesc.Flags = 0;
            viewDesc.Texture2D.MipSlice = 0;
            if (FAILED(device->CreateDepthStencilView(
                    texture.Get(), &viewDesc, dsv.ReleaseAndGetAddressOf())) ||
                !dsv)
                return false;
        }

        device_ = device;
        texture_ = std::move(texture);
        rtv_ = std::move(rtv);
        dsv_ = std::move(dsv);
        mirror_generation_ = device_generation_;
        if (!descriptor_exact(device))
        {
            release_mirror();
            return false;
        }
        mirror_serial_ = mirror_serial_ == ~std::uint64_t{0}
            ? 1
            : mirror_serial_ + 1;
        return true;
    }

    bool NativeSurfaceMirror::ready() const noexcept
    {
        if (!metadata_valid_ || !device_ || !texture_ ||
            mirror_generation_ == 0 ||
            mirror_generation_ != device_generation_)
            return false;

        return role_ == ResourceRole::Color
            ? rtv_.Get() != nullptr && dsv_.Get() == nullptr
            : role_ == ResourceRole::DepthStencil &&
                dsv_.Get() != nullptr && rtv_.Get() == nullptr;
    }

    bool NativeSurfaceMirror::descriptor_exact(
        ID3D11Device* expectedDevice) const noexcept
    {
        if (!ready() || !expectedDevice || device_.Get() != expectedDevice)
            return false;

        const auto format = translate_resource_format(source_format_, role_);
        const auto behavior =
            translate_resource_behavior(role_, source_pool_, source_usage_);
        if (!format.exact || !behavior.descriptorExact)
            return false;

        D3D11_TEXTURE2D_DESC textureDesc{};
        texture_->GetDesc(&textureDesc);
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

        Microsoft::WRL::ComPtr<ID3D11Device> textureDevice;
        texture_->GetDevice(textureDevice.ReleaseAndGetAddressOf());
        if (!textureDevice || textureDevice.Get() != expectedDevice)
            return false;

        Microsoft::WRL::ComPtr<ID3D11Resource> viewResource;
        if (role_ == ResourceRole::Color)
        {
            D3D11_RENDER_TARGET_VIEW_DESC viewDesc{};
            rtv_->GetDesc(&viewDesc);
            rtv_->GetResource(viewResource.ReleaseAndGetAddressOf());
            return viewResource &&
                viewResource.Get() == texture_.Get() &&
                viewDesc.Format == format.format &&
                viewDesc.ViewDimension == D3D11_RTV_DIMENSION_TEXTURE2D &&
                viewDesc.Texture2D.MipSlice == 0;
        }

        D3D11_DEPTH_STENCIL_VIEW_DESC viewDesc{};
        dsv_->GetDesc(&viewDesc);
        dsv_->GetResource(viewResource.ReleaseAndGetAddressOf());
        return viewResource &&
            viewResource.Get() == texture_.Get() &&
            viewDesc.Format == format.format &&
            viewDesc.ViewDimension == D3D11_DSV_DIMENSION_TEXTURE2D &&
            viewDesc.Flags == 0 &&
            viewDesc.Texture2D.MipSlice == 0;
    }

    bool NativeSurfaceMirror::copy_color_to_staging(
        ID3D11DeviceContext* context,
        ID3D11Texture2D** stagingOutput) const noexcept
    {
        if (!stagingOutput)
            return false;
        *stagingOutput = nullptr;
        if (!context ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
            role_ != ResourceRole::Color || !device_ ||
            !descriptor_exact(device_.Get()) || !texture_ || !rtv_)
            return false;

        Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
        if (!contextDevice || contextDevice.Get() != device_.Get())
            return false;

        // R166: same-device and immediate-context ownership alone does not
        // prove that the surface copied was the live OM color target. Fail
        // closed on post-draw detach/substitution instead of returning a
        // plausible but stale BGRA readback from another render target.
        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> observedRtv;
        context->OMGetRenderTargets(1u, observedRtv.GetAddressOf(), nullptr);
        if (observedRtv.Get() != rtv_.Get())
            return false;

        D3D11_TEXTURE2D_DESC sourceDesc{};
        texture_->GetDesc(&sourceDesc);
        if (sourceDesc.MipLevels != 1 || sourceDesc.ArraySize != 1 ||
            sourceDesc.SampleDesc.Count != 1 ||
            sourceDesc.SampleDesc.Quality != 0 ||
            sourceDesc.Usage != D3D11_USAGE_DEFAULT ||
            sourceDesc.BindFlags != D3D11_BIND_RENDER_TARGET ||
            sourceDesc.CPUAccessFlags != 0 || sourceDesc.MiscFlags != 0)
            return false;

        D3D11_TEXTURE2D_DESC readbackDesc = sourceDesc;
        readbackDesc.Usage = D3D11_USAGE_STAGING;
        readbackDesc.BindFlags = 0;
        readbackDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
        Microsoft::WRL::ComPtr<ID3D11Texture2D> readback;
        if (FAILED(device_->CreateTexture2D(
                &readbackDesc, nullptr, readback.ReleaseAndGetAddressOf())) ||
            !readback)
            return false;

        context->CopyResource(readback.Get(), texture_.Get());
        *stagingOutput = readback.Detach();
        return true;
    }

    bool NativeSurfaceMirror::copy_color_depth_pair_to_staging(
        ID3D11DeviceContext* context,
        const NativeSurfaceMirror& depth,
        ID3D11Texture2D** stagingOutput) const noexcept
    {
        if (!stagingOutput)
            return false;
        *stagingOutput = nullptr;
        if (!context ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
            !device_ ||
            !compose_surface_pair_readiness(device_.Get(), *this, depth).ready)
            return false;

        Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
        if (!contextDevice || contextDevice.Get() != device_.Get())
            return false;

        // R167: R166 proved only the color RTV. A late DSV detach or an
        // equivalent-descriptor DSV substitution must never pass as a valid
        // color/depth draw-pair readback. OMGetRenderTargets AddRefs both views.
        // R180: a slot-0 RTV/DSV match is insufficient: other live color
        // attachments or OM UAVs can change the producer's write identity.
        // Refuse direct pair staging as well as the receipt-validated wrapper.
        std::array<
            ID3D11RenderTargetView*,
            D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT> observedRtvs{};
        Microsoft::WRL::ComPtr<ID3D11DepthStencilView> observedDepth;
        context->OMGetRenderTargets(
            D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
            observedRtvs.data(), observedDepth.GetAddressOf());
        bool exactOm = observedRtvs[0] == render_target_view() &&
            observedDepth.Get() == depth.depth_stencil_view();
        for (UINT slot = 1; slot < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++slot)
        {
            if (observedRtvs[slot] != nullptr)
                exactOm = false;
        }
        for (auto* observedRtv : observedRtvs)
        {
            if (observedRtv)
                observedRtv->Release();
        }

        std::array<
            ID3D11UnorderedAccessView*,
            D3D11_PS_CS_UAV_REGISTER_COUNT - 1> observedUavs{};
        context->OMGetRenderTargetsAndUnorderedAccessViews(
            0, nullptr, nullptr, 1,
            static_cast<UINT>(observedUavs.size()), observedUavs.data());
        for (auto* observedUav : observedUavs)
        {
            if (observedUav != nullptr)
            {
                exactOm = false;
                observedUav->Release();
            }
        }
        if (!exactOm)
            return false;

        // R166 reobserves the live color RTV immediately before copying.
        return copy_color_to_staging(context, stagingOutput);
    }

    void NativeSurfaceMirror::observe_device_reset() noexcept
    {
        release_mirror();
        device_generation_ =
            device_generation_ == ~std::uint64_t{0}
                ? 1
                : device_generation_ + 1;
    }

    void NativeSurfaceMirror::release_mirror() noexcept
    {
        dsv_.Reset();
        rtv_.Reset();
        texture_.Reset();
        device_.Reset();
        mirror_generation_ = 0;
    }

    void NativeSurfaceMirror::shutdown() noexcept
    {
        release_mirror();
        role_ = ResourceRole::Color;
        width_ = 0;
        height_ = 0;
        source_format_ = D3DFMT_UNKNOWN;
        source_pool_ = D3DPOOL_DEFAULT;
        source_usage_ = 0;
        source_multisample_type_ = D3DMULTISAMPLE_NONE;
        source_multisample_quality_ = 0;
        metadata_valid_ = false;
        device_generation_ = 1;
    }

    NativeSurfacePairReadiness compose_surface_pair_readiness(
        ID3D11Device* expectedDevice,
        const NativeSurfaceMirror& color,
        const NativeSurfaceMirror& depth) noexcept
    {
        NativeSurfacePairReadiness out{};
        out.inputValid = expectedDevice != nullptr &&
            color.role() == ResourceRole::Color &&
            depth.role() == ResourceRole::DepthStencil;
        if (!out.inputValid)
            return out;

        out.colorReady = color.descriptor_exact(expectedDevice);
        out.depthReady = depth.descriptor_exact(expectedDevice);
        out.deviceMatches = out.colorReady && out.depthReady;
        out.dimensionsMatch = color.width() != 0 && color.height() != 0 &&
            color.width() == depth.width() && color.height() == depth.height();
        out.generationsCurrent =
            color.mirror_generation() != 0 &&
            color.mirror_generation() == color.device_generation() &&
            depth.mirror_generation() != 0 &&
            depth.mirror_generation() == depth.device_generation();
        out.colorMirrorSerial = color.mirror_serial();
        out.depthMirrorSerial = depth.mirror_serial();
        out.componentSerialsPresent =
            out.colorMirrorSerial != 0 && out.depthMirrorSerial != 0;
        out.width = color.width();
        out.height = color.height();
        out.ready = out.colorReady && out.depthReady && out.deviceMatches &&
            out.dimensionsMatch && out.generationsCurrent &&
            out.componentSerialsPresent;
        if (!out.ready)
            return out;

        std::uint64_t hash = 1469598103934665603ull;
        const auto mix = [&hash](std::uint64_t value) noexcept {
            hash ^= value;
            hash *= 1099511628211ull;
        };
        mix(static_cast<std::uint64_t>(color.role()));
        mix(static_cast<std::uint64_t>(depth.role()));
        mix(static_cast<std::uint64_t>(out.width));
        mix(static_cast<std::uint64_t>(out.height));
        mix(static_cast<std::uint64_t>(color.source_format()));
        mix(static_cast<std::uint64_t>(depth.source_format()));
        mix(color.device_generation());
        mix(color.mirror_generation());
        mix(depth.device_generation());
        mix(depth.mirror_generation());
        mix(out.colorMirrorSerial);
        mix(out.depthMirrorSerial);
        out.snapshotToken = hash == 0 ? 1 : hash;
        return out;
    }

    bool validate_surface_pair_snapshot(
        ID3D11Device* expectedDevice,
        const NativeSurfaceMirror& color,
        const NativeSurfaceMirror& depth,
        std::uint64_t snapshotToken) noexcept
    {
        if (snapshotToken == 0)
            return false;
        const auto current = compose_surface_pair_readiness(
            expectedDevice, color, depth);
        return current.ready && current.snapshotToken == snapshotToken;
    }

    bool NativeSurfacePairBinding::initialize(
        ID3D11Device* device,
        const NativeSurfaceMirror& color,
        const NativeSurfaceMirror& depth,
        const NativeSurfacePairReadiness& readiness) noexcept
    {
        shutdown();
        if (!device || !readiness.ready || readiness.snapshotToken == 0 ||
            !validate_surface_pair_snapshot(
                device, color, depth, readiness.snapshotToken))
            return false;

        ID3D11RenderTargetView* rtv = color.render_target_view();
        ID3D11DepthStencilView* dsv = depth.depth_stencil_view();
        if (!rtv || !dsv ||
            readiness.colorMirrorSerial != color.mirror_serial() ||
            readiness.depthMirrorSerial != depth.mirror_serial())
            return false;

        Microsoft::WRL::ComPtr<ID3D11Device> rtvDevice;
        Microsoft::WRL::ComPtr<ID3D11Device> dsvDevice;
        rtv->GetDevice(rtvDevice.ReleaseAndGetAddressOf());
        dsv->GetDevice(dsvDevice.ReleaseAndGetAddressOf());
        if (!rtvDevice || !dsvDevice ||
            rtvDevice.Get() != device || dsvDevice.Get() != device)
            return false;

        device_ = device;
        rtv_ = rtv;
        dsv_ = dsv;
        surface_pair_snapshot_token_ = readiness.snapshotToken;
        return true;
    }

    void NativeSurfacePairBinding::shutdown() noexcept
    {
        dsv_.Reset();
        rtv_.Reset();
        device_.Reset();
        surface_pair_snapshot_token_ = 0;
    }

    bool NativeSurfacePairBinding::apply(
        ID3D11DeviceContext* context,
        const NativeSurfaceMirror& color,
        const NativeSurfaceMirror& depth) const noexcept
    {
        // Deferred contexts record command lists instead of immediately
        // binding the game producer's live OM state. Never promote them.
        if (!ready() || !context ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
            !validate_surface_pair_snapshot(
                device_.Get(), color, depth, surface_pair_snapshot_token_) ||
            color.render_target_view() != rtv_.Get() ||
            depth.depth_stencil_view() != dsv_.Get())
            return false;

        Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
        if (!contextDevice || contextDevice.Get() != device_.Get())
            return false;

        ID3D11RenderTargetView* rtv = rtv_.Get();
        std::array<
            ID3D11UnorderedAccessView*,
            D3D11_PS_CS_UAV_REGISTER_COUNT - 1> clearedUavs{};
        context->OMSetRenderTargetsAndUnorderedAccessViews(
            1, &rtv, dsv_.Get(), 1,
            static_cast<UINT>(clearedUavs.size()), clearedUavs.data(), nullptr);
        return binding_readiness(context, color, depth).ready;
    }

    NativeSurfacePairBindingReadiness
    NativeSurfacePairBinding::binding_readiness(
        ID3D11DeviceContext* context,
        const NativeSurfaceMirror& color,
        const NativeSurfaceMirror& depth) const noexcept
    {
        NativeSurfacePairBindingReadiness out{};
        out.surfacePairSnapshotToken = surface_pair_snapshot_token_;
        out.inputValid =
            context != nullptr &&
            context->GetType() == D3D11_DEVICE_CONTEXT_IMMEDIATE &&
            surface_pair_snapshot_token_ != 0;
        out.ownerReady = ready();
        if (!out.inputValid || !out.ownerReady)
            return out;

        out.pairCurrent = validate_surface_pair_snapshot(
            device_.Get(), color, depth, surface_pair_snapshot_token_);
        out.colorViewCurrent =
            color.render_target_view() == rtv_.Get();
        out.depthViewCurrent =
            depth.depth_stencil_view() == dsv_.Get();
        if (!out.pairCurrent ||
            !out.colorViewCurrent ||
            !out.depthViewCurrent)
            return out;

        Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
        context->GetDevice(contextDevice.ReleaseAndGetAddressOf());
        out.contextMatches =
            contextDevice && contextDevice.Get() == device_.Get();
        if (!out.contextMatches)
            return out;

        std::array<
            ID3D11RenderTargetView*,
            D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT> observedRtvs{};
        Microsoft::WRL::ComPtr<ID3D11DepthStencilView> observedDsv;
        context->OMGetRenderTargets(
            D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
            observedRtvs.data(),
            observedDsv.ReleaseAndGetAddressOf());
        out.rtvBoundExact = observedRtvs[0] == rtv_.Get();
        for (UINT slot = 1;
             slot < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT;
             ++slot) {
            if (observedRtvs[slot] != nullptr)
                out.rtvBoundExact = false;
        }
        out.dsvBoundExact = observedDsv.Get() == dsv_.Get();

        std::array<
            ID3D11UnorderedAccessView*,
            D3D11_PS_CS_UAV_REGISTER_COUNT - 1> observedUavs{};
        context->OMGetRenderTargetsAndUnorderedAccessViews(
            0, nullptr, nullptr, 1,
            static_cast<UINT>(observedUavs.size()), observedUavs.data());
        out.unorderedAccessClear = true;
        for (auto* observedUav : observedUavs) {
            if (observedUav != nullptr)
                out.unorderedAccessClear = false;
        }

        out.ready =
            out.pairCurrent &&
            out.contextMatches &&
            out.colorViewCurrent &&
            out.depthViewCurrent &&
            out.rtvBoundExact &&
            out.dsvBoundExact &&
            out.unorderedAccessClear;
        if (out.ready) {
            std::uint64_t hash = 1469598103934665603ull;
            const auto mix = [&hash](std::uint64_t value) noexcept {
                hash ^= value;
                hash *= 1099511628211ull;
            };
            mix(out.surfacePairSnapshotToken);
            mix(static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(context)));
            mix(static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(observedRtvs[0])));
            mix(static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(observedDsv.Get())));
            mix(color.mirror_serial());
            mix(depth.mirror_serial());
            out.snapshotToken = hash == 0 ? 1 : hash;
        }
        for (auto* observedRtv : observedRtvs) {
            if (observedRtv)
                observedRtv->Release();
        }
        for (auto* observedUav : observedUavs) {
            if (observedUav)
                observedUav->Release();
        }
        return out;
    }

    bool NativeSurfacePairBinding::validate_binding_snapshot(
        ID3D11DeviceContext* context,
        const NativeSurfaceMirror& color,
        const NativeSurfaceMirror& depth,
        std::uint64_t snapshotToken) const noexcept
    {
        if (snapshotToken == 0)
            return false;
        const auto current = binding_readiness(context, color, depth);
        return current.ready && current.snapshotToken == snapshotToken;
    }

    bool NativeSurfaceMirror::copy_bound_color_depth_pair_to_staging(
        ID3D11DeviceContext* context,
        const NativeSurfaceMirror& depth,
        const NativeSurfacePairBinding& binding,
        std::uint64_t bindingSnapshotToken,
        ID3D11Texture2D** stagingOutput) const noexcept
    {
        if (!stagingOutput)
            return false;
        *stagingOutput = nullptr;

        // R168: R167's slot-0 proof alone cannot exclude a second live RTV
        // or an unrelated R145 owner. Revalidate the exact binding receipt
        // (all RTV slots/UAVs, DSV, immediate context and surface generation)
        // before staging the color member of that sealed pair.
        if (bindingSnapshotToken == 0 ||
            !binding.validate_binding_snapshot(
                context, *this, depth, bindingSnapshotToken))
            return false;

        return copy_color_depth_pair_to_staging(
            context, depth, stagingOutput);
    }
}
