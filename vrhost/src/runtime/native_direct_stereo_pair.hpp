#pragma once
#include <cstdint>
#include <cstring>
#include <d3d11.h>

// Portable descriptor-only CI stubs intentionally omit COM render-view types.
// Forward declarations keep the uninstantiated native-copy template parsable;
// full COM interfaces are required only at the actual D3D11/WARP callsite.
struct ID3D11RenderTargetView;
struct ID3D11DepthStencilView;
struct ID3D11UnorderedAccessView;

namespace OutRunVrNativeEyePair
{
    // A typed *_SRGB SRV is automatically decoded to linear RGB by D3D11
    // texture sampling. The host compositor must not apply SrgbToLinear twice.
    [[nodiscard]] constexpr bool IsSrgbView(DXGI_FORMAT format) noexcept
    {
        return format == DXGI_FORMAT_B8G8R8A8_UNORM_SRGB ||
               format == DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
    }

    [[nodiscard]] constexpr bool IsSupportedSourceFormat(DXGI_FORMAT format) noexcept
    {
        return format == DXGI_FORMAT_B8G8R8A8_UNORM ||
               format == DXGI_FORMAT_R8G8B8A8_UNORM ||
               format == DXGI_FORMAT_R10G10B10A2_UNORM ||
               format == DXGI_FORMAT_R16G16B16A16_FLOAT ||
               IsSrgbView(format);
    }
    // Genuine DirectGPU game frames may use the packed DXGI 10:10:10:2
    // backbuffer path. Decode the exact little-endian DXGI channel layout
    // for the host's nonblocking source/projection pixel evidence. This is
    // not the HMD compositor's sRGB/HDR transfer, which stays unchanged.
    [[nodiscard]] inline bool DecodeR10G10B10A2Rgb(
        const std::uint8_t* pixel, float* rgb) noexcept
    {
        if (!pixel || !rgb) return false;
        std::uint32_t value = 0;
        std::memcpy(&value, pixel, sizeof(value));
        constexpr float inverse1023 = 1.0f / 1023.0f;
        rgb[0] = static_cast<float>(value & 0x3ffu) * inverse1023;
        rgb[1] = static_cast<float>((value >> 10) & 0x3ffu) * inverse1023;
        rgb[2] = static_cast<float>((value >> 20) & 0x3ffu) * inverse1023;
        return true;
    }

    // The shared handle numbers may differ while both opens refer to the same
    // D3D11 allocation. Compare canonical COM identities *after* opening, not
    // the handle values, before copying a supposedly stereo game frame.
    // This is a secondary host-side check: only native producer provenance
    // may establish independent left/right game renders.
    // Existing portable sRGB/descriptor regressions compile this header with
    // restricted DXGI descriptors. Defer COM type checking until the actual
    // D3D11 host or WARP resource-identity test instantiates this function.
    template <typename Canonical, typename Texture, typename InterfaceId>
    [[nodiscard]] inline bool DistinctSourceAllocations(
        Texture* left, Texture* right, const InterfaceId& unknownIid) noexcept
    {
        if (!left || !right || left == right) return false;
        Canonical* leftIdentity = nullptr;
        Canonical* rightIdentity = nullptr;
        const auto leftResult = left->QueryInterface(
            unknownIid, reinterpret_cast<void**>(&leftIdentity));
        const auto rightResult = right->QueryInterface(
            unknownIid, reinterpret_cast<void**>(&rightIdentity));
        const bool distinct = leftResult >= 0 && rightResult >= 0 &&
            leftIdentity && rightIdentity && leftIdentity != rightIdentity;
        if (leftIdentity) leftIdentity->Release();
        if (rightIdentity) rightIdentity->Release();
        return distinct;
    }


    // A recreated OpenXR/D3D11 device can have the same source size and
    // DXGI format as the previous session. Descriptor equality is not proof
    // that a cached game-eye or host hold texture belongs to the current
    // immediate context. The host must reopen/recreate it before GPU copy.
    // Keep this templated so restricted descriptor-only test headers need
    // not provide the complete D3D11 COM interfaces until instantiated.
    template <typename Texture, typename Device>
    [[nodiscard]] inline bool TextureOwnedByDevice(
        Texture* texture, Device* device) noexcept
    {
        if (!texture || !device) return false;
        Device* owner = nullptr;
        texture->GetDevice(&owner);
        const bool same = owner != nullptr && owner == device;
        if (owner) owner->Release();
        return same;
    }


    // Live DirectGPU game eye sources may still be bound as CS UAVs after
    // native camera compute postpasses. D3D11 GPU copies must detach both
    // those writable aliases and the full host OM MRT/DSV attachments, then
    // restore the exact caller bindings for the next HUD/game pass.
    // No append/consume counter is reset by these two-eye transfers.
    template <typename Context>
    class ScopedNativeEyeCopyBindings final
    {
    public:
        explicit ScopedNativeEyeCopyBindings(Context* context) noexcept
            : context_(context)
        {
            context_->OMGetRenderTargets(kRenderSlots, targets_, &depth_);
            context_->CSGetUnorderedAccessViews(0u, kComputeSlots, compute_);
            ID3D11UnorderedAccessView* empty[kComputeSlots]{};
            context_->CSSetUnorderedAccessViews(0u, kComputeSlots, empty, nullptr);
            context_->OMSetRenderTargets(0u, nullptr, nullptr);
        }

        ~ScopedNativeEyeCopyBindings() noexcept
        {
            context_->OMSetRenderTargets(kRenderSlots, targets_, depth_);
            UINT preserveCounters[kComputeSlots]{};
            for (auto& counter : preserveCounters) counter = UINT(-1);
            context_->CSSetUnorderedAccessViews(
                0u, kComputeSlots, compute_, preserveCounters);
            const auto release = [](auto*& view) noexcept {
                if (view) { view->Release(); view = nullptr; }
            };
            for (auto*& target : targets_) release(target);
            release(depth_);
            for (auto*& output : compute_) release(output);
        }

        ScopedNativeEyeCopyBindings(const ScopedNativeEyeCopyBindings&) = delete;
        ScopedNativeEyeCopyBindings& operator=(const ScopedNativeEyeCopyBindings&) = delete;

    private:
        enum : unsigned { kRenderSlots = 8u, kComputeSlots = 8u };
        Context* context_{};
        ID3D11RenderTargetView* targets_[kRenderSlots]{};
        ID3D11DepthStencilView* depth_{};
        ID3D11UnorderedAccessView* compute_[kComputeSlots]{};
    };

    // Native game-produced independent L/R eyes may be copied directly into
    // matching OpenXR array slices. Unlike an SBS atlas this is already one
    // complete full-size image per eye, so there is no UV crop or color
    // conversion to perform. Keep the shader path for every other case.
    [[nodiscard]] inline bool CopyToStereoSwapchainCompatible(
        const D3D11_TEXTURE2D_DESC& left,
        const D3D11_TEXTURE2D_DESC& right,
        const D3D11_TEXTURE2D_DESC& projection) noexcept
    {
        const bool exactColor =
            left.Format == DXGI_FORMAT_B8G8R8A8_UNORM ||
            left.Format == DXGI_FORMAT_R8G8B8A8_UNORM;
        const auto source = [&](const D3D11_TEXTURE2D_DESC& d) noexcept {
            return d.Width != 0u && d.Height != 0u &&
                d.Width == left.Width && d.Height == left.Height &&
                d.Format == left.Format && d.MipLevels == 1u &&
                d.ArraySize == 1u && d.SampleDesc.Count == 1u &&
                d.SampleDesc.Quality == 0u &&
                d.Usage == D3D11_USAGE_DEFAULT && d.CPUAccessFlags == 0u &&
                d.MiscFlags == 0u &&
                (d.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0u;
        };
        return exactColor && source(left) && source(right) &&
            projection.Width == left.Width &&
            projection.Height == left.Height &&
            projection.Format == left.Format &&
            projection.ArraySize == 2u && projection.MipLevels == 1u &&
            projection.SampleDesc.Count == 1u &&
            projection.SampleDesc.Quality == 0u &&
            projection.Usage == D3D11_USAGE_DEFAULT &&
            projection.CPUAccessFlags == 0u &&
            (projection.BindFlags & D3D11_BIND_RENDER_TARGET) != 0u;
    }

    // Copy native gameplay eyes to the OpenXR array only when the selected
    // source route, the immediate context, BOTH hold eyes and destination all
    // belong to the same live D3D11 device. On a classic SBS fallback or XR
    // device recreation, stale global hold textures may still have perfectly
    // matching dimensions; copying them would silently replace the selected
    // game frame. The caller keeps the regular shader path on any rejection.
    // Templates defer COM type requirements for the portable DXGI tests.
    template <typename Canonical, typename Context, typename Device,
              typename Texture, typename InterfaceId>
    [[nodiscard]] inline bool CopyDirectEyesToStereoArray(
        Context* context, Device* device, Texture* left, Texture* right,
        Texture* projection, bool copyOptIn, bool directRoute,
        bool validatedFrame, const InterfaceId& unknownIid) noexcept
    {
        if (!copyOptIn || !directRoute || !validatedFrame ||
            !context || !device || !left || !right || !projection ||
            // Only the active immediate GPU command stream can carry the
            // native gameplay eye pair to the current OpenXR frame.
            context->GetType() != decltype(context->GetType()){})
            return false;
        Device* contextOwner = nullptr;
        context->GetDevice(&contextOwner);
        const bool sameContextDevice =
            contextOwner != nullptr && contextOwner == device;
        if (contextOwner) contextOwner->Release();
        if (!sameContextDevice ||
            !TextureOwnedByDevice(left, device) ||
            !TextureOwnedByDevice(right, device) ||
            !TextureOwnedByDevice(projection, device) ||
            !DistinctSourceAllocations<Canonical>(
                left, right, unknownIid))
            return false;
        D3D11_TEXTURE2D_DESC leftDesc{}, rightDesc{}, xrDesc{};
        left->GetDesc(&leftDesc);
        right->GetDesc(&rightDesc);
        projection->GetDesc(&xrDesc);
        if (!CopyToStereoSwapchainCompatible(leftDesc, rightDesc, xrDesc))
            return false;

        // A live game/menu compositor may have an OM target and multiple
        // MRTs bound when the native XR eye pair is selected. Both sources
        // must be unbound for the GPU copy, but the next game/HUD pass must
        // get EXACTLY its previous RTV/DSV attachments back, including
        // RT1..RT7. Never leave the host pointing at no render target.
        ScopedNativeEyeCopyBindings<Context> savedOutput(context);
        context->CopySubresourceRegion(
            projection, 0u, 0u, 0u, 0u, left, 0u, nullptr);
        context->CopySubresourceRegion(
            projection, 1u, 0u, 0u, 0u, right, 0u, nullptr);
        return true;
    }


    // The x64 compositor's real DirectGPU route copies independently rendered
    // game eyes into persistent host holds. Before queuing either CopyResource,
    // prove the immediate context, both game sources and BOTH reused holds
    // belong to one live device and are four distinct GPU allocations.
    // A rejected pair queues NO commands, so a classic SBS fallback can run.
    template <typename Canonical, typename Context, typename Device,
              typename Texture, typename InterfaceId>
    [[nodiscard]] inline bool CopyDirectEyesToHold(
        Context* context, Device* device, Texture* holdLeft, Texture* holdRight,
        Texture* sourceLeft, Texture* sourceRight,
        const InterfaceId& unknownIid) noexcept
    {
        // D3D11_DEVICE_CONTEXT_IMMEDIATE is the zero-valued context type.
        // Use its dependent GetType() return type so this template also parses
        // with descriptor-only D3D11 stubs before a real context is instantiated.
        if (!context || !device || !holdLeft || !holdRight ||
            !sourceLeft || !sourceRight ||
            context->GetType() != decltype(context->GetType()){})
            return false;
        Device* contextOwner = nullptr;
        context->GetDevice(&contextOwner);
        const bool current = contextOwner && contextOwner == device;
        if (contextOwner) contextOwner->Release();
        if (!current ||
            !TextureOwnedByDevice(holdLeft, device) ||
            !TextureOwnedByDevice(holdRight, device) ||
            !TextureOwnedByDevice(sourceLeft, device) ||
            !TextureOwnedByDevice(sourceRight, device))
            return false;
        // Canonical COM identity catches aliasing even when different
        // texture interface pointers or legacy shared handles are supplied.
        Texture* textures[4]{holdLeft, holdRight, sourceLeft, sourceRight};
        for (unsigned a = 0; a < 4; ++a)
            for (unsigned c = a + 1; c < 4; ++c)
                if (!DistinctSourceAllocations<Canonical>(
                        textures[a], textures[c], unknownIid))
                    return false;

        D3D11_TEXTURE2D_DESC holdL{}, holdR{}, gameL{}, gameR{};
        holdLeft->GetDesc(&holdL);
        holdRight->GetDesc(&holdR);
        sourceLeft->GetDesc(&gameL);
        sourceRight->GetDesc(&gameR);
        const auto gameEye = [](const D3D11_TEXTURE2D_DESC& desc) noexcept {
            return desc.Width && desc.Height &&
                desc.MipLevels == 1u && desc.ArraySize == 1u &&
                desc.SampleDesc.Count == 1u &&
                desc.SampleDesc.Quality == 0u &&
                desc.Usage == D3D11_USAGE_DEFAULT &&
                desc.CPUAccessFlags == 0u &&
                (desc.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0u &&
                IsSupportedSourceFormat(desc.Format);
        };
        const auto holdMatches = [&](const D3D11_TEXTURE2D_DESC& h) noexcept {
            return h.Width == gameL.Width && h.Height == gameL.Height &&
                h.Format == gameL.Format && h.MipLevels == 1u &&
                h.ArraySize == 1u && h.SampleDesc.Count == 1u &&
                h.SampleDesc.Quality == 0u &&
                h.Usage == D3D11_USAGE_DEFAULT &&
                h.CPUAccessFlags == 0u && h.MiscFlags == 0u &&
                (h.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0u;
        };
        if (!gameEye(gameL) || !gameEye(gameR) ||
            gameL.Width != gameR.Width || gameL.Height != gameR.Height ||
            gameL.Format != gameR.Format ||
            !holdMatches(holdL) || !holdMatches(holdR))
            return false;

        // Source eyes can still be bound as native menu/vehicle/race RTVs
        // when R23 imports the pair. Temporarily detach ALL OM outputs before
        // the actual GPU transfers and restore the full MRT/DSV set afterward.
        // A one-target restore would silently discard the next game's HUD RT1.
        ScopedNativeEyeCopyBindings<Context> savedOutput(context);
        context->CopyResource(holdLeft, sourceLeft);
        context->CopyResource(holdRight, sourceRight);
        return true;
    }

    // Exact two-eye source admission shared by the real x64 DirectGPU importer
    // and the R23 OpenXR projection staging path. Never treat duplicated
    // handles or incompatible CopyResource shapes as a stereo game frame.
    inline bool Compatible(
        std::uint32_t leftHandle, std::uint32_t rightHandle,
        std::uint32_t generation, std::uint32_t width, std::uint32_t height,
        const D3D11_TEXTURE2D_DESC& left,
        const D3D11_TEXTURE2D_DESC& right) noexcept
    {
        if (!leftHandle || !rightHandle || leftHandle == rightHandle ||
            !generation || !width || !height)
            return false;
        const auto usable = [&](const D3D11_TEXTURE2D_DESC& d) noexcept {
            return d.Width == width && d.Height == height &&
                d.MipLevels == 1 && d.ArraySize == 1 &&
                d.SampleDesc.Count == 1 && d.SampleDesc.Quality == 0 &&
                d.Usage == D3D11_USAGE_DEFAULT && d.CPUAccessFlags == 0 &&
                (d.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0 &&
                IsSupportedSourceFormat(d.Format);
        };
        return usable(left) && usable(right) &&
            left.Format == right.Format;
    }
}
