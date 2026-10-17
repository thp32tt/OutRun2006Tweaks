#include "native_shared_eye_ring.hpp"
#include "native_game_eye_pair_sources.hpp"

#include <dxgi.h>

namespace outrun::vr::dx11
{
    namespace
    {
        bool create_shared_eye(
            ID3D11Device* device,
            const D3D11_TEXTURE2D_DESC& desc,
            Microsoft::WRL::ComPtr<ID3D11Texture2D>& texture,
            Microsoft::WRL::ComPtr<ID3D11RenderTargetView>& rtv,
            HANDLE& handle) noexcept
        {
            handle = nullptr;
            if (FAILED(device->CreateTexture2D(
                    &desc, nullptr, texture.ReleaseAndGetAddressOf())) ||
                !texture)
                return false;

            if (FAILED(device->CreateRenderTargetView(
                    texture.Get(), nullptr, rtv.ReleaseAndGetAddressOf())) ||
                !rtv)
                return false;

            Microsoft::WRL::ComPtr<IDXGIResource> dxgiResource;
            if (FAILED(texture->QueryInterface(
                    __uuidof(IDXGIResource),
                    reinterpret_cast<void**>(
                        dxgiResource.ReleaseAndGetAddressOf()))) ||
                !dxgiResource)
                return false;

            // Legacy shared handles are deliberate here. The current x64 host
            // consumes producer handles through ID3D11Device::OpenSharedResource,
            // so using NT handles would require a new protocol/open path.
            if (FAILED(dxgiResource->GetSharedHandle(&handle)) || !handle)
                return false;

            return true;
        }
    }

    bool NativeSharedEyeRing::initialize(
        ID3D11Device* device,
        std::uint32_t width,
        std::uint32_t height,
        DXGI_FORMAT format) noexcept
    {
        shutdown();
        if (!device || width == 0 || height == 0 ||
            format == DXGI_FORMAT_UNKNOWN)
            return false;

        D3D11_TEXTURE2D_DESC desc{};
        desc.Width = width;
        desc.Height = height;
        desc.MipLevels = 1;
        desc.ArraySize = 1;
        desc.Format = format;
        desc.SampleDesc.Count = 1;
        desc.Usage = D3D11_USAGE_DEFAULT;
        desc.BindFlags =
            D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;
        desc.MiscFlags = D3D11_RESOURCE_MISC_SHARED;

        D3D11_QUERY_DESC query{};
        query.Query = D3D11_QUERY_EVENT;

        for (auto& slot : slots_)
        {
            for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
            {
                if (!create_shared_eye(
                        device, desc,
                        slot.eye[eyeIndex],
                        slot.rtv[eyeIndex],
                        slot.shared_handle[eyeIndex]))
                {
                    shutdown();
                    return false;
                }
            }

            if (FAILED(device->CreateQuery(
                    &query, slot.producer_fence.ReleaseAndGetAddressOf())) ||
                !slot.producer_fence)
            {
                shutdown();
                return false;
            }
            reset_slot_lifetime(slot);
        }

        producer_device_ = device;
        width_ = width;
        height_ = height;
        format_ = format;
        synchronization_faulted_ = false;
        ready_ = true;
        return true;
    }

    void NativeSharedEyeRing::shutdown() noexcept
    {
        identity_ = {};
        frame_id_high_watermark_ = 0u;
        for (auto& slot : slots_)
        {
            reset_slot_lifetime(slot);
            slot.producer_fence.Reset();
            for (std::uint32_t eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
            {
                slot.rtv[eyeIndex].Reset();
                slot.eye[eyeIndex].Reset();
                // GetSharedHandle returns a legacy shared-resource handle whose
                // lifetime follows the resource; do not CloseHandle it.
                slot.shared_handle[eyeIndex] = nullptr;
            }
        }
        producer_device_.Reset();
        width_ = 0;
        height_ = 0;
        format_ = DXGI_FORMAT_UNKNOWN;
        ready_ = false;
        synchronization_faulted_ = false;
    }

    bool NativeSharedEyeRing::same_producer_context(
        ID3D11DeviceContext* context) const noexcept
    {
        if (!ready_ || !producer_device_ || !context ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> observedDevice;
        context->GetDevice(observedDevice.GetAddressOf());
        return observedDevice && observedDevice.Get() == producer_device_.Get();
    }

    bool NativeSharedEyeRing::bind_lifetime(
        std::uint32_t producer_pid,
        std::uint32_t consumer_pid,
        std::uint32_t run_generation,
        std::uint32_t transport_generation) noexcept
    {
        const OutRunVR::Core::TransportIdentity next{
            producer_pid,
            consumer_pid,
            run_generation,
            transport_generation,
        };

        if (!ready_ || synchronization_faulted_ ||
            !OutRunVR::Core::TransportIdentityValid(next))
            return false;
        if (identity_ == next)
            return true;

        // A lifetime transition may make old shared handles/ACKs stale. Never
        // retag an active allocation in place: the caller must let all slots
        // drain or recreate the ring, which retires the old COM resources.
        if (!all_slots_idle())
            return false;

        identity_ = next;
        frame_id_high_watermark_ = 0u;
        return true;
    }

    void NativeSharedEyeRing::invalidate_lifetime() noexcept
    {
        // Do not clear per-slot state here. If a transition invalidates the
        // consumer identity while work is in flight, keeping those slots busy
        // prevents an accidental rebind/reuse. shutdown() is the hard retirement
        // path for the old allocation.
        identity_ = {};
    }

    bool NativeSharedEyeRing::all_slots_idle() const noexcept
    {
        for (const auto& slot : slots_)
        {
            if (slot.state != SharedEyeSlotState::Free ||
                slot.frame_id != 0)
                return false;
        }
        return true;
    }

    void NativeSharedEyeRing::reset_slot_lifetime(
        SharedEyeSlot& slot) noexcept
    {
        slot.frame_id = 0;
        slot.gpu_copy_queued = false;
        slot.state = SharedEyeSlotState::Free;
    }

    bool NativeSharedEyeRing::refresh_unpublished_fence(
        ID3D11DeviceContext* context,
        SharedEyeSlot& slot) noexcept
    {
        if (slot.state != SharedEyeSlotState::ProducerPending)
            return true;
        if (!same_producer_context(context) || !slot.producer_fence)
            return false;

        const HRESULT status = context->GetData(
            slot.producer_fence.Get(), nullptr, 0,
            D3D11_ASYNC_GETDATA_DONOTFLUSH);
        if (status == S_OK)
        {
            // This unpublished frame's GPU writes are complete and it missed
            // its advertisement window, so no consumer could have observed it.
            reset_slot_lifetime(slot);
            return true;
        }
        if (status == S_FALSE)
            return false;

        // A query error does not prove GPU completion. Keep ProducerPending
        // intact and quarantine the entire allocation until shutdown() creates
        // a fresh transport generation; reusing this texture could overlap the
        // still-running old GPU write with a new frame.
        synchronization_faulted_ = true;
        return false;
    }

    bool NativeSharedEyeRing::try_acquire_slot(
        ID3D11DeviceContext* context,
        std::uint64_t frame_id,
        const OutRunVR::Core::FrameAck* ack,
        std::uint32_t& out_slot) noexcept
    {
        out_slot = static_cast<std::uint32_t>(slots_.size());
        if (!activation_ready() || !same_producer_context(context) ||
            frame_id == 0)
            return false;
        const std::uint64_t ackCursor =
            ack && OutRunVR::Core::TransportAckIdentityMatches(*ack, identity_)
                ? ack->frameId : 0u;
        if (!native_game_eye_frame_id_admitted(
                frame_id, frame_id_high_watermark_, ackCursor))
            return false;

        // One transport frame has one slot owner. A duplicate acquisition
        // could advertise the same frame in two slots, leaving one consumer ACK
        // unable to unambiguously retire both allocations. Reject before any
        // pending-fence refresh or ACK-driven state mutation.
        for (const auto& entry : slots_)
        {
            if (entry.frame_id == frame_id)
                return false;
        }

        const std::uint32_t preferred = static_cast<std::uint32_t>(
            (frame_id - 1u) % slots_.size());

        for (std::uint32_t offset = 0;
             offset < static_cast<std::uint32_t>(slots_.size()); ++offset)
        {
            const std::uint32_t index = static_cast<std::uint32_t>(
                (preferred + offset) % slots_.size());
            auto& slot = slots_[index];

            if (slot.state == SharedEyeSlotState::ProducerPending &&
                !refresh_unpublished_fence(context, slot))
            {
                if (synchronization_faulted_)
                    return false;
                continue;
            }

            if (slot.state == SharedEyeSlotState::Published)
            {
                if (!ack ||
                    !OutRunVR::Core::TransportAckReleasesFrame(
                        *ack, identity_, index, slot.frame_id))
                    continue;
                frame_id_high_watermark_ = native_game_eye_frame_high_watermark(
                    frame_id_high_watermark_, ack->frameId);
                reset_slot_lifetime(slot);
            }

            if (slot.state != SharedEyeSlotState::Free ||
                slot.frame_id != 0)
                continue;

            slot.frame_id = frame_id;
            slot.state = SharedEyeSlotState::Acquired;
            frame_id_high_watermark_ = native_game_eye_frame_high_watermark(
                frame_id_high_watermark_, frame_id);
            out_slot = index;
            return true;
        }

        return false;
    }

    bool NativeSharedEyeRing::cancel_acquired_slot(
        std::uint32_t slot,
        std::uint64_t frame_id) noexcept
    {
        // R178: an invalidated identity or failed producer fence may still
        // have GPU writes recorded against this acquired slot. Cancel is safe
        // only while the original live transport generation is authoritative.
        // Otherwise preserve the slot as busy until hard retirement.
        if (!activation_ready() || slot >= slots_.size())
            return false;
        auto& entry = slots_[slot];
        if (entry.state != SharedEyeSlotState::Acquired ||
            entry.frame_id != frame_id || frame_id == 0 ||
            !native_game_eye_copy_cancelable(entry.gpu_copy_queued))
            return false;

        reset_slot_lifetime(entry);
        return true;
    }

    // R306 native-eye producer: one submitted stereo pair, one EVENT and
    // one exact frame/slot lifetime. Do not advertise a half-updated pair.
    bool NativeSharedEyeRing::submit_eye_pair(
        ID3D11DeviceContext* context,
        std::uint32_t slot,
        std::uint64_t frame_id,
        ID3D11Texture2D* left_source,
        ID3D11Texture2D* right_source,
        UINT left_array_slice, UINT right_array_slice) noexcept
    {
        if (!activation_ready() || same_producer_context(context) == false ||
            slot >= slots_.size() || frame_id == 0 ||
            !left_source || !right_source)
            return false;

        auto& entry = slots_[slot];
        if (entry.state != SharedEyeSlotState::Acquired ||
            entry.frame_id != frame_id || !entry.producer_fence ||
            entry.gpu_copy_queued || !entry.eye[0] || !entry.eye[1])
            return false;

        const auto exact_source = [&](ID3D11Texture2D* source,
                                      D3D11_TEXTURE2D_DESC& desc) noexcept {
            source->GetDesc(&desc);
            if (desc.Width != width_ || desc.Height != height_ ||
                desc.Format != format_ || desc.MipLevels == 0 ||
                desc.ArraySize == 0 || desc.SampleDesc.Count == 0 ||
                (desc.SampleDesc.Count == 1 && desc.SampleDesc.Quality != 0) ||
                desc.Usage != D3D11_USAGE_DEFAULT || desc.CPUAccessFlags != 0 ||
                // Accept only a locally owned color target, not a shared handle
                // that could alias an in-flight OpenXR ring eye allocation.
                !(native_game_eye_local_render_target_admitted(
                    desc.BindFlags, desc.MiscFlags,
                    D3D11_BIND_RENDER_TARGET,
                    D3D11_RESOURCE_MISC_SHARED |
                    D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
                    D3D11_RESOURCE_MISC_SHARED_NTHANDLE) ||
                  native_game_eye_gpu_copy_only_source_admitted(
                    desc.BindFlags, desc.MiscFlags, desc.SampleDesc.Count,
                    D3D11_RESOURCE_MISC_SHARED |
                    D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
                    D3D11_RESOURCE_MISC_SHARED_NTHANDLE) ||
                  native_game_eye_gpu_compute_source_admitted(
                    desc.BindFlags, desc.MiscFlags, desc.SampleDesc.Count,
                    D3D11_BIND_UNORDERED_ACCESS, D3D11_BIND_RENDER_TARGET,
                    D3D11_BIND_DEPTH_STENCIL,
                    D3D11_RESOURCE_MISC_SHARED |
                    D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
                    D3D11_RESOURCE_MISC_SHARED_NTHANDLE)))

                return false;
            Microsoft::WRL::ComPtr<ID3D11Device> owner;
            source->GetDevice(owner.GetAddressOf());
            return owner && owner.Get() == producer_device_.Get();
        };

        // Validate both resource descriptors and owning devices up front.
        // Any rejection leaves the Acquired slot unchanged and records no
        // native GPU commands, so the original DX9Ex frame remains usable.
        D3D11_TEXTURE2D_DESC leftDesc{}, rightDesc{};
        if (!exact_source(left_source, leftDesc) ||
            !exact_source(right_source, rightDesc))
            return false;
        // Game-authored left/right cameras can occupy separate full-size
        // array slices of the SAME D3D11 texture, with a mip chain. Only
        // mip zero represents the actual full-resolution eye frame.
        if (left_array_slice >= leftDesc.ArraySize ||
            right_array_slice >= rightDesc.ArraySize ||
            (leftDesc.SampleDesc.Count > 1u && leftDesc.MipLevels != 1u) ||
            (rightDesc.SampleDesc.Count > 1u && rightDesc.MipLevels != 1u))
            return false;
        // ResolveSubresource is only legal for formats the actual producer
        // device advertises as resolvable; check before either eye is written.
        bool formatSupportsResolve = false;
        if (leftDesc.SampleDesc.Count > 1u) {
            UINT formatSupport = 0;
            if (FAILED(producer_device_->CheckFormatSupport(format_, &formatSupport)))
                return false;
            formatSupportsResolve =
                (formatSupport & D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE) != 0u;
        }
        const auto transfer = native_game_eye_transfer(
            leftDesc.SampleDesc.Count, leftDesc.SampleDesc.Quality,
            rightDesc.SampleDesc.Count, rightDesc.SampleDesc.Quality,
            formatSupportsResolve);
        if (transfer == NativeGameEyeTransfer::Reject) return false;
        // Even when texture interfaces differ, both eyes may alias the same
        // underlying COM allocation. No ring-owned output from ANY slot may
        // become a producer source: published eyes remain immutable until ACK.
        // Canonical IUnknown identity is stable while the ring owns resources.
        const auto canonical_identity = [](
            ID3D11Texture2D* source,
            Microsoft::WRL::ComPtr<IUnknown>& identity) noexcept {
            return source && SUCCEEDED(source->QueryInterface(
                __uuidof(IUnknown),
                reinterpret_cast<void**>(identity.GetAddressOf()))) &&
                identity.Get() != nullptr;
        };
        Microsoft::WRL::ComPtr<IUnknown> leftIdentity, rightIdentity;
        if (!canonical_identity(left_source, leftIdentity) ||
            !canonical_identity(right_source, rightIdentity))
            return false;
        std::array<std::uintptr_t, OutRunVR::RenderFrameRingSize * 2u> owned{};
        for (std::size_t n = 0; n < slots_.size(); ++n) {
            for (std::size_t eyeIndex = 0; eyeIndex < 2u; ++eyeIndex) {
                Microsoft::WRL::ComPtr<IUnknown> identity;
                if (!canonical_identity(slots_[n].eye[eyeIndex].Get(), identity))
                    return false;
                owned[n * 2u + eyeIndex] =
                    reinterpret_cast<std::uintptr_t>(identity.Get());
            }
        }
        // Same allocation is stereo only when its two actual physical
        // camera slices are different. Alias interfaces and source views
        // of a shared ring output remain forbidden before any GPU write.
        if (leftIdentity.Get() == rightIdentity.Get()) {
            if (left_array_slice == right_array_slice) return false;
            for (const auto identity : owned) {
                if (!identity || identity ==
                    reinterpret_cast<std::uintptr_t>(leftIdentity.Get()))
                    return false;
            }
        } else if (!native_game_eye_pair_sources_admitted(
                reinterpret_cast<std::uintptr_t>(leftIdentity.Get()),
                reinterpret_cast<std::uintptr_t>(rightIdentity.Get()),
                owned)) {
            return false;
        }
        // Game camera RT0/RT1 can still be OM-bound at the native eye
        // handoff (menu and vehicle postpasses do not necessarily unbind).
        // Unbind ALL producer outputs before CopyResource/ResolveSubresource,
        // then restore the exact MRT/depth attachments for the next game
        // Draw or the original D3D9Ex fallback. Never leave a source RTV
        // bound while scheduling its GPU transfer to the shared-eye ring.
        struct ScopedStereoSourceOutputs final {
            ID3D11DeviceContext* context{};
            ID3D11RenderTargetView* targets[
                D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]{};
            ID3D11DepthStencilView* depth{};
            // Game camera color may also be bound as a compute UAV by a
            // postpass. A native eye GPU copy must not read a live UAV output;
            // preserve ALL caller compute outputs, including unrelated slots.
            // Preserve PS/OM pixel UAVs as well as CS outputs across the
            // actual game-eye Copy/Resolve; RTV-only restore drops them.
            ID3D11UnorderedAccessView* pixelOutputs[
                D3D11_PS_CS_UAV_REGISTER_COUNT]{};
            ID3D11UnorderedAccessView* computeOutputs[
                D3D11_PS_CS_UAV_REGISTER_COUNT]{};
            explicit ScopedStereoSourceOutputs(ID3D11DeviceContext* ctx) noexcept
                : context(ctx) {
                context->OMGetRenderTargetsAndUnorderedAccessViews(
                    D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
                    targets, &depth, 0u,
                    D3D11_PS_CS_UAV_REGISTER_COUNT, pixelOutputs);
                context->CSGetUnorderedAccessViews(
                    0u, D3D11_PS_CS_UAV_REGISTER_COUNT, computeOutputs);
                ID3D11UnorderedAccessView* unbound[
                    D3D11_PS_CS_UAV_REGISTER_COUNT]{};
                context->CSSetUnorderedAccessViews(
                    0u, D3D11_PS_CS_UAV_REGISTER_COUNT, unbound, nullptr);
                // Detach both writable GPU stages before copying game
                // source textures into the independently rendered XR eyes.
                context->OMSetRenderTargetsAndUnorderedAccessViews(
                    0u, nullptr, nullptr, 0u,
                    D3D11_PS_CS_UAV_REGISTER_COUNT, unbound, nullptr);
            }
            ~ScopedStereoSourceOutputs() noexcept {
                // Restore the occupied RT prefix and the remaining OM UAV
                // slots in one D3D11 OM operation. Binding RTVs alone would
                // erase the game's PS UAV postpass state between eye frames.
                UINT rtCount = 0u;
                for (UINT i = 0u; i < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++i)
                    if (targets[i]) rtCount = i + 1u;
                UINT keepCounters[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
                for (auto& counter : keepCounters) counter = UINT(-1);
                const UINT uavCount = D3D11_PS_CS_UAV_REGISTER_COUNT - rtCount;
                context->OMSetRenderTargetsAndUnorderedAccessViews(
                    rtCount, rtCount ? targets : nullptr, depth,
                    rtCount, uavCount,
                    uavCount ? pixelOutputs + rtCount : nullptr,
                    uavCount ? keepCounters + rtCount : nullptr);
                // Preserve append/consume counters in both OM and CS stages.
                context->CSSetUnorderedAccessViews(
                    0u, D3D11_PS_CS_UAV_REGISTER_COUNT,
                    computeOutputs, keepCounters);
                for (auto* output : pixelOutputs)
                    if (output) output->Release();
                for (auto* output : computeOutputs)
                    if (output) output->Release();
                for (auto* target : targets)
                    if (target) target->Release();
                if (depth) depth->Release();
            }
        } sourceOutputs{context};

        // All rejection paths precede both GPU commands. After this point
        // a failed fence arm must quarantine, not cancel/reissue, the slot:
        // the D3D11 command stream may still write either shared eye.
        entry.gpu_copy_queued = true;
        if (transfer == NativeGameEyeTransfer::Resolve) {
            if (left_array_slice == 0u && right_array_slice == 0u) {
                context->ResolveSubresource(entry.eye[0].Get(), 0u, left_source, 0u, format_);
                context->ResolveSubresource(entry.eye[1].Get(), 0u, right_source, 0u, format_);
            } else {
                // MSAA arrays have one mip: array slice is the subresource.
                context->ResolveSubresource(entry.eye[0].Get(), 0u,
                    left_source, left_array_slice, format_);
                context->ResolveSubresource(entry.eye[1].Get(), 0u,
                    right_source, right_array_slice, format_);
            }
        } else {
            if (leftDesc.MipLevels == 1u && leftDesc.ArraySize == 1u &&
                rightDesc.MipLevels == 1u && rightDesc.ArraySize == 1u) {
                context->CopyResource(entry.eye[0].Get(), left_source);
                context->CopyResource(entry.eye[1].Get(), right_source);
            } else {
                // Keep the game's independent full-resolution mip-zero eye
                // pixels on GPU; never copy an entire array/mip allocation.
                context->CopySubresourceRegion(entry.eye[0].Get(), 0u,
                    0u, 0u, 0u, left_source,
                    D3D11CalcSubresource(0u, left_array_slice, leftDesc.MipLevels),
                    nullptr);
                context->CopySubresourceRegion(entry.eye[1].Get(), 0u,
                    0u, 0u, 0u, right_source,
                    D3D11CalcSubresource(0u, right_array_slice, rightDesc.MipLevels),
                    nullptr);
            }
        }
        if (!signal_producer_fence(context, slot, frame_id)) {
            // GPU copies/resolves have already been recorded; a failed
            // fence arm cannot prove they finished. Quarantine this ring
            // until shutdown retires the shared allocations.
            synchronization_faulted_ = true;
            return false;
        }
        return true;
    }

    // Native game stereo can render two independent camera views directly
    // into the two shared color attachments. Publication still uses the SAME
    // EVENT fence and exact lifetime/slot/ACK path as source-eye GPU copies.
    bool NativeSharedEyeRing::render_eye_pair(
        ID3D11DeviceContext* context,
        std::uint32_t slot,
        std::uint64_t frame_id,
        NativeEyeDrawRecorder recorder,
        void* user) noexcept
    {
        if (!activation_ready() || !same_producer_context(context) ||
            slot >= slots_.size() || frame_id == 0 || !recorder)
            return false;

        auto& entry = slots_[slot];
        if (entry.state != SharedEyeSlotState::Acquired ||
            entry.frame_id != frame_id || entry.gpu_copy_queued ||
            !entry.eye[0] || !entry.eye[1] ||
            !entry.rtv[0] || !entry.rtv[1] || !entry.producer_fence)
            return false;

        // Once handed to the real Draw recorder, even its failure may have
        // queued GPU commands. Never permit cancel/reuse across a partially
        // rendered pair or publish a single eye with stale pixels.
        entry.gpu_copy_queued = true;
        if (!recorder(user, context, entry.rtv[0].Get(), entry.rtv[1].Get())) {
            synchronization_faulted_ = true;
            return false;
        }
        if (!signal_producer_fence(context, slot, frame_id)) {
            synchronization_faulted_ = true;
            return false;
        }
        return true;
    }

    bool NativeSharedEyeRing::signal_producer_fence(
        ID3D11DeviceContext* context,
        std::uint32_t slot,
        std::uint64_t frame_id) noexcept
    {
        if (!activation_ready() || !same_producer_context(context) ||
            slot >= slots_.size() || frame_id == 0)
            return false;

        auto& entry = slots_[slot];
        if (entry.state != SharedEyeSlotState::Acquired ||
            entry.frame_id != frame_id ||
            !entry.producer_fence)
            return false;

        // End is recorded immediately after both eye writes/copies. No blocking
        // wait is introduced on the game thread; completion is polled later.
        context->End(entry.producer_fence.Get());
        // GetData below deliberately uses DONOTFLUSH; submit the EVENT and
        // both preceding eye writes here so a caller can poll asynchronously
        // without an unrelated Present or an external Flush dependency.
        // Flush submits commands to the GPU, it does not wait for completion.
        context->Flush();
        entry.state = SharedEyeSlotState::ProducerPending;
        return true;
    }

    bool NativeSharedEyeRing::publish_if_fence_complete(
        ID3D11DeviceContext* context,
        std::uint32_t slot,
        std::uint64_t frame_id) noexcept
    {
        if (!activation_ready() || !same_producer_context(context) ||
            slot >= slots_.size() || frame_id == 0)
            return false;

        auto& entry = slots_[slot];
        if (entry.state != SharedEyeSlotState::ProducerPending ||
            entry.frame_id != frame_id ||
            !entry.producer_fence)
            return false;

        const HRESULT status = context->GetData(
            entry.producer_fence.Get(), nullptr, 0,
            D3D11_ASYNC_GETDATA_DONOTFLUSH);
        if (status == S_FALSE)
            return false;
        if (status != S_OK)
        {
            // The frame was never advertised, but a query error still does not
            // prove its GPU writes completed. Preserve ProducerPending and
            // quarantine the ring; only shutdown() may retire this allocation.
            synchronization_faulted_ = true;
            return false;
        }

        entry.state = SharedEyeSlotState::Published;
        return true;
    }

    bool NativeSharedEyeRing::snapshot_published_frame(
        std::uint32_t slot,
        std::uint64_t frame_id,
        NativeSharedEyePublication& out) const noexcept
    {
        out = {};
        if (!activation_ready() || slot >= slots_.size() || frame_id == 0)
            return false;

        const auto& entry = slots_[slot];
        if (entry.state != SharedEyeSlotState::Published ||
            entry.frame_id != frame_id ||
            !entry.shared_handle[0] || !entry.shared_handle[1] ||
            width_ == 0 || height_ == 0 || format_ == DXGI_FORMAT_UNKNOWN)
            return false;

        out.identity = identity_;
        out.slot = slot;
        out.frame_id = frame_id;
        out.left_handle = entry.shared_handle[0];
        out.right_handle = entry.shared_handle[1];
        out.width = width_;
        out.height = height_;
        out.format = format_;
        return true;
    }

    bool NativeSharedEyeRing::validate_publication_snapshot(
        const NativeSharedEyePublication& publication) const noexcept
    {
        if (!activation_ready() ||
            publication.identity != identity_ ||
            publication.slot >= slots_.size() ||
            publication.frame_id == 0 ||
            !publication.left_handle || !publication.right_handle ||
            publication.width != width_ ||
            publication.height != height_ ||
            publication.format != format_)
            return false;

        NativeSharedEyePublication current{};
        if (!snapshot_published_frame(
                publication.slot, publication.frame_id, current))
            return false;

        return current.identity == publication.identity &&
            current.slot == publication.slot &&
            current.frame_id == publication.frame_id &&
            current.left_handle == publication.left_handle &&
            current.right_handle == publication.right_handle &&
            current.width == publication.width &&
            current.height == publication.height &&
            current.format == publication.format;
    }

    bool NativeSharedEyeRing::retire_acknowledged(
        const OutRunVR::Core::FrameAck& ack) noexcept
    {
        if (!activation_ready() || ack.slot >= slots_.size())
            return false;

        auto& entry = slots_[ack.slot];
        if (entry.state != SharedEyeSlotState::Published ||
            entry.frame_id == 0 ||
            !OutRunVR::Core::TransportAckReleasesFrame(
                ack, identity_, ack.slot, entry.frame_id))
            return false;

        frame_id_high_watermark_ = native_game_eye_frame_high_watermark(
            frame_id_high_watermark_, ack.frameId);
        reset_slot_lifetime(entry);
        return true;
    }

    SharedEyeSlotState NativeSharedEyeRing::slot_state(
        std::uint32_t slot) const noexcept
    {
        if (slot >= slots_.size())
            return SharedEyeSlotState::Free;
        return slots_[slot].state;
    }

    std::uint64_t NativeSharedEyeRing::slot_frame_id(
        std::uint32_t slot) const noexcept
    {
        if (slot >= slots_.size())
            return 0;
        return slots_[slot].frame_id;
    }

    ID3D11Texture2D* NativeSharedEyeRing::eye(
        std::uint32_t slot, std::uint32_t eye_index) const noexcept
    {
        if (slot >= slots_.size() || eye_index >= 2)
            return nullptr;
        return slots_[slot].eye[eye_index].Get();
    }

    ID3D11RenderTargetView* NativeSharedEyeRing::rtv(
        std::uint32_t slot, std::uint32_t eye_index) const noexcept
    {
        if (slot >= slots_.size() || eye_index >= 2)
            return nullptr;
        return slots_[slot].rtv[eye_index].Get();
    }

    HANDLE NativeSharedEyeRing::shared_handle(
        std::uint32_t slot, std::uint32_t eye_index) const noexcept
    {
        if (slot >= slots_.size() || eye_index >= 2)
            return nullptr;
        return slots_[slot].shared_handle[eye_index];
    }

    ID3D11Query* NativeSharedEyeRing::producer_fence(
        std::uint32_t slot) const noexcept
    {
        if (slot >= slots_.size())
            return nullptr;
        return slots_[slot].producer_fence.Get();
    }
}
