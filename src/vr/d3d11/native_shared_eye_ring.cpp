#include "native_shared_eye_ring.hpp"

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
                reset_slot_lifetime(slot);
            }

            if (slot.state != SharedEyeSlotState::Free ||
                slot.frame_id != 0)
                continue;

            slot.frame_id = frame_id;
            slot.state = SharedEyeSlotState::Acquired;
            out_slot = index;
            return true;
        }

        return false;
    }

    bool NativeSharedEyeRing::cancel_acquired_slot(
        std::uint32_t slot,
        std::uint64_t frame_id) noexcept
    {
        if (slot >= slots_.size())
            return false;
        auto& entry = slots_[slot];
        if (entry.state != SharedEyeSlotState::Acquired ||
            entry.frame_id != frame_id ||
            frame_id == 0)
            return false;

        reset_slot_lifetime(entry);
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
