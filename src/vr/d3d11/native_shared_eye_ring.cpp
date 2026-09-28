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
        DXGI_FORMAT format,
        std::uint32_t producer_pid,
        std::uint32_t consumer_pid,
        std::uint32_t run_generation,
        std::uint32_t transport_generation) noexcept
    {
        shutdown();
        if (!device || width == 0 || height == 0 ||
            format == DXGI_FORMAT_UNKNOWN ||
            producer_pid == 0 || consumer_pid == 0 ||
            run_generation == 0 || transport_generation == 0)
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
        }

        width_ = width;
        height_ = height;
        format_ = format;
        producer_pid_ = producer_pid;
        consumer_pid_ = consumer_pid;
        run_generation_ = run_generation;
        transport_generation_ = transport_generation;
        synchronization_faulted_ = false;
        ready_ = true;
        return true;
    }

    void NativeSharedEyeRing::shutdown() noexcept
    {
        for (auto& slot : slots_)
        {
            slot.frame_id = 0;
            slot.write_leased = false;
            slot.producer_pending = false;
            slot.published = false;
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
        width_ = 0;
        height_ = 0;
        format_ = DXGI_FORMAT_UNKNOWN;
        producer_pid_ = 0;
        consumer_pid_ = 0;
        run_generation_ = 0;
        transport_generation_ = 0;
        ready_ = false;
        synchronization_faulted_ = false;
    }

    NativeSharedEyeRing::FenceState NativeSharedEyeRing::poll_producer_fence(
        ID3D11DeviceContext* context,
        SharedEyeSlot& slot) noexcept
    {
        if (!slot.producer_pending)
            return FenceState::Complete;
        if (!context || !slot.producer_fence)
        {
            synchronization_faulted_ = true;
            return FenceState::Error;
        }

        const HRESULT hr = context->GetData(
            slot.producer_fence.Get(), nullptr, 0,
            D3D11_ASYNC_GETDATA_DONOTFLUSH);
        if (hr == S_OK)
        {
            slot.producer_pending = false;
            return FenceState::Complete;
        }
        if (hr == S_FALSE)
            return FenceState::Pending;

        // Completion is unknowable. Never clear the pending marker or reuse any
        // ring slot after a query error; a later activation layer must rebuild
        // the whole transport generation.
        synchronization_faulted_ = true;
        return FenceState::Error;
    }

    bool NativeSharedEyeRing::acquire_writable_slot(
        ID3D11DeviceContext* context,
        std::uint64_t frame_id,
        std::uint32_t preferred_slot,
        std::uint32_t& out_slot) noexcept
    {
        out_slot = OutRunVR::RenderFrameRingSize;
        if (!ready() || !context || frame_id == 0)
            return false;

        const std::uint32_t first =
            preferred_slot % static_cast<std::uint32_t>(slots_.size());
        for (std::uint32_t offset = 0;
             offset < static_cast<std::uint32_t>(slots_.size()); ++offset)
        {
            const std::uint32_t index =
                (first + offset) % static_cast<std::uint32_t>(slots_.size());
            auto& slot = slots_[index];
            if (slot.write_leased)
                continue;

            const FenceState fence = poll_producer_fence(context, slot);
            if (fence == FenceState::Error)
                return false;
            if (fence == FenceState::Pending)
                continue;

            if (slot.published)
                continue;

            // A completed but unpublished frame missed its publication window.
            // No consumer can reference it, so the slot can be recycled now.
            slot.frame_id = frame_id;
            slot.write_leased = true;
            out_slot = index;
            return true;
        }
        return false;
    }

    bool NativeSharedEyeRing::abandon_writable_slot(
        std::uint32_t slot_index,
        std::uint64_t frame_id) noexcept
    {
        if (!ready() || slot_index >= slots_.size())
            return false;
        auto& slot = slots_[slot_index];
        if (!slot.write_leased || slot.producer_pending ||
            slot.published || slot.frame_id != frame_id)
            return false;

        slot.write_leased = false;
        slot.frame_id = 0;
        return true;
    }

    bool NativeSharedEyeRing::signal_producer_complete(
        ID3D11DeviceContext* context,
        std::uint32_t slot_index,
        std::uint64_t frame_id) noexcept
    {
        if (!ready() || !context || slot_index >= slots_.size())
            return false;
        auto& slot = slots_[slot_index];
        if (!slot.write_leased || slot.producer_pending || slot.published ||
            slot.frame_id != frame_id || !slot.producer_fence)
            return false;

        // D3D11 End(EVENT) orders all prior commands on this immediate context.
        // Publication is deferred until poll_producer_fence observes S_OK.
        context->End(slot.producer_fence.Get());
        slot.write_leased = false;
        slot.producer_pending = true;
        return true;
    }

    bool NativeSharedEyeRing::describe_published_slot(
        std::uint32_t slot_index,
        OutRunVR::Core::FrameSlot& out_slot) const noexcept
    {
        out_slot = {};
        if (!ready() || slot_index >= slots_.size())
            return false;
        const auto& slot = slots_[slot_index];
        if (!slot.published || slot.frame_id == 0 ||
            !slot.shared_handle[0] || !slot.shared_handle[1])
            return false;

        out_slot.producerPid = producer_pid_;
        out_slot.consumerPid = consumer_pid_;
        out_slot.runGeneration = run_generation_;
        out_slot.generation = transport_generation_;
        out_slot.slot = slot_index;
        out_slot.frameId = slot.frame_id;
        out_slot.leftHandle =
            reinterpret_cast<std::uintptr_t>(slot.shared_handle[0]);
        out_slot.rightHandle =
            reinterpret_cast<std::uintptr_t>(slot.shared_handle[1]);
        out_slot.width = width_;
        out_slot.height = height_;
        out_slot.format = static_cast<std::uint32_t>(format_);
        return OutRunVR::Core::FrameSlotIdentityValid(out_slot);
    }

    bool NativeSharedEyeRing::publish_completed(
        ID3D11DeviceContext* context,
        std::uint32_t slot_index,
        std::uint64_t frame_id,
        OutRunVR::Core::FrameSlot& out_slot) noexcept
    {
        out_slot = {};
        if (!ready() || !context || slot_index >= slots_.size() ||
            frame_id == 0)
            return false;

        auto& slot = slots_[slot_index];
        if (slot.published)
            return slot.frame_id == frame_id &&
                describe_published_slot(slot_index, out_slot);
        if (slot.write_leased || !slot.producer_pending ||
            slot.frame_id != frame_id)
            return false;

        const FenceState fence = poll_producer_fence(context, slot);
        if (fence != FenceState::Complete)
            return false;

        slot.published = true;
        return describe_published_slot(slot_index, out_slot);
    }

    bool NativeSharedEyeRing::acknowledge(
        const OutRunVR::Core::FrameAck& ack) noexcept
    {
        if (!ready() || ack.slot >= slots_.size())
            return false;

        OutRunVR::Core::FrameSlot published{};
        if (!describe_published_slot(ack.slot, published) ||
            !OutRunVR::Core::ConsumerAckCoversFrame(published, ack))
            return false;

        auto& slot = slots_[ack.slot];
        slot.published = false;
        slot.frame_id = 0;
        return true;
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
