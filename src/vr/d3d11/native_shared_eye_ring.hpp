#pragma once

#include <array>
#include <cstdint>
#include <d3d11.h>
#include <wrl/client.h>

#include "vr/core/transport.hpp"
#include "vr/ipc/protocol.hpp"

namespace outrun::vr::dx11
{
    enum class SharedEyeSlotState : std::uint32_t
    {
        Free = 0,
        Acquired,
        ProducerPending,
        Published,
    };

    struct SharedEyeSlot
    {
        Microsoft::WRL::ComPtr<ID3D11Texture2D> eye[2];
        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv[2];
        Microsoft::WRL::ComPtr<ID3D11Query> producer_fence;
        HANDLE shared_handle[2]{};
        std::uint64_t frame_id{};
        SharedEyeSlotState state{SharedEyeSlotState::Free};
    };

    // R118 immutable handoff evidence. A caller may advertise a native eye pair
    // only while this exact lifetime/slot/frame snapshot is still Published.
    struct NativeSharedEyePublication
    {
        OutRunVR::Core::TransportIdentity identity{};
        std::uint32_t slot{};
        std::uint64_t frame_id{};
        HANDLE left_handle{};
        HANDLE right_handle{};
        std::uint32_t width{};
        std::uint32_t height{};
        DXGI_FORMAT format{DXGI_FORMAT_UNKNOWN};
    };

    class NativeSharedEyeRing final
    {
    public:
        bool initialize(
            ID3D11Device* device,
            std::uint32_t width,
            std::uint32_t height,
            DXGI_FORMAT format) noexcept;
        void shutdown() noexcept;

        // Resource allocation alone is not enough to activate the native path.
        // The exact producer/consumer process pair, producer run generation and
        // transport generation must be bound first. A different identity cannot
        // replace an in-flight generation; recreate the ring to retire it.
        bool bind_lifetime(
            std::uint32_t producer_pid,
            std::uint32_t consumer_pid,
            std::uint32_t run_generation,
            std::uint32_t transport_generation) noexcept;
        void invalidate_lifetime() noexcept;

        [[nodiscard]] bool ready() const noexcept { return ready_; }
        [[nodiscard]] bool activation_ready() const noexcept
        {
            return ready_ && producer_device_ && !synchronization_faulted_ &&
                OutRunVR::Core::TransportIdentityValid(identity_);
        }
        [[nodiscard]] bool synchronization_faulted() const noexcept
        {
            return synchronization_faulted_;
        }
        [[nodiscard]] bool all_slots_idle() const noexcept;
        [[nodiscard]] const OutRunVR::Core::TransportIdentity&
            identity() const noexcept { return identity_; }

        [[nodiscard]] std::uint32_t width() const noexcept { return width_; }
        [[nodiscard]] std::uint32_t height() const noexcept { return height_; }
        [[nodiscard]] DXGI_FORMAT format() const noexcept { return format_; }

        // Reserve a free slot for frame_id. Producer-pending slots are reclaimed
        // only after their EVENT query completes. Published slots remain immutable
        // until an ACK with the exact lifetime identity, slot and frame is seen.
        bool try_acquire_slot(
            ID3D11DeviceContext* context,
            std::uint64_t frame_id,
            const OutRunVR::Core::FrameAck* ack,
            std::uint32_t& out_slot) noexcept;
        bool cancel_acquired_slot(
            std::uint32_t slot,
            std::uint64_t frame_id) noexcept;

        // Call after both eye writes/copies have been recorded. The EVENT query
        // is ended immediately and the slot is quarantined until completion.
        bool signal_producer_fence(
            ID3D11DeviceContext* context,
            std::uint32_t slot,
            std::uint64_t frame_id) noexcept;

        // Only a completed EVENT query can move ProducerPending -> Published.
        // The caller may advertise shared handles only after this returns true.
        bool publish_if_fence_complete(
            ID3D11DeviceContext* context,
            std::uint32_t slot,
            std::uint64_t frame_id) noexcept;

        // Snapshot only a fully Published frame. The snapshot is immutable
        // evidence for a later IPC handoff; validation fails after ACK,
        // lifetime invalidation, generation replacement or hard retirement.
        bool snapshot_published_frame(
            std::uint32_t slot,
            std::uint64_t frame_id,
            NativeSharedEyePublication& out) const noexcept;
        [[nodiscard]] bool validate_publication_snapshot(
            const NativeSharedEyePublication& publication) const noexcept;

        // Consumer ACK retirement is exact-identity and exact-slot gated.
        bool retire_acknowledged(
            const OutRunVR::Core::FrameAck& ack) noexcept;

        [[nodiscard]] SharedEyeSlotState slot_state(
            std::uint32_t slot) const noexcept;
        [[nodiscard]] std::uint64_t slot_frame_id(
            std::uint32_t slot) const noexcept;

        [[nodiscard]] ID3D11Texture2D* eye(
            std::uint32_t slot, std::uint32_t eye_index) const noexcept;
        [[nodiscard]] ID3D11RenderTargetView* rtv(
            std::uint32_t slot, std::uint32_t eye_index) const noexcept;
        [[nodiscard]] HANDLE shared_handle(
            std::uint32_t slot, std::uint32_t eye_index) const noexcept;
        [[nodiscard]] ID3D11Query* producer_fence(
            std::uint32_t slot) const noexcept;

    private:
        // A frame fence belongs to the producer's exact immediate D3D11 context.
        // Reject foreign/deferred contexts without mutating live frame slots.
        [[nodiscard]] bool same_producer_context(
            ID3D11DeviceContext* context) const noexcept;
        void reset_slot_lifetime(SharedEyeSlot& slot) noexcept;
        bool refresh_unpublished_fence(
            ID3D11DeviceContext* context,
            SharedEyeSlot& slot) noexcept;

        Microsoft::WRL::ComPtr<ID3D11Device> producer_device_;
        std::array<SharedEyeSlot, OutRunVR::RenderFrameRingSize> slots_{};
        OutRunVR::Core::TransportIdentity identity_{};
        std::uint32_t width_{};
        std::uint32_t height_{};
        DXGI_FORMAT format_ = DXGI_FORMAT_UNKNOWN;
        bool ready_ = false;
        // Any unexpected GetData result leaves GPU completion unknowable.
        // Quarantine the allocation until shutdown() recreates the resources.
        bool synchronization_faulted_ = false;
    };

    static_assert(OutRunVR::RenderFrameRingSize == 4);
}
