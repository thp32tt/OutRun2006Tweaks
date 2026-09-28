#pragma once

#include <array>
#include <cstdint>
#include <d3d11.h>
#include <wrl/client.h>

#include "vr/core/transport.hpp"
#include "vr/ipc/protocol.hpp"

namespace outrun::vr::dx11
{
    struct SharedEyeSlot
    {
        Microsoft::WRL::ComPtr<ID3D11Texture2D> eye[2];
        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv[2];
        Microsoft::WRL::ComPtr<ID3D11Query> producer_fence;
        HANDLE shared_handle[2]{};

        std::uint64_t frame_id{};
        bool write_leased = false;
        bool producer_pending = false;
        bool published = false;
    };

    class NativeSharedEyeRing final
    {
    public:
        // Identity is mandatory. Native DX11 transport is not allowed to create
        // a reusable shared ring without the same producer/consumer run identity
        // that protects the proven D3D9Ex DirectGPU path.
        bool initialize(
            ID3D11Device* device,
            std::uint32_t width,
            std::uint32_t height,
            DXGI_FORMAT format,
            std::uint32_t producer_pid,
            std::uint32_t consumer_pid,
            std::uint32_t run_generation,
            std::uint32_t transport_generation) noexcept;
        void shutdown() noexcept;

        [[nodiscard]] bool ready() const noexcept
        {
            return ready_ && !synchronization_faulted_;
        }
        [[nodiscard]] bool synchronization_faulted() const noexcept
        {
            return synchronization_faulted_;
        }
        [[nodiscard]] std::uint32_t width() const noexcept { return width_; }
        [[nodiscard]] std::uint32_t height() const noexcept { return height_; }
        [[nodiscard]] DXGI_FORMAT format() const noexcept { return format_; }
        [[nodiscard]] std::uint32_t producer_pid() const noexcept
        {
            return producer_pid_;
        }
        [[nodiscard]] std::uint32_t consumer_pid() const noexcept
        {
            return consumer_pid_;
        }
        [[nodiscard]] std::uint32_t run_generation() const noexcept
        {
            return run_generation_;
        }
        [[nodiscard]] std::uint32_t transport_generation() const noexcept
        {
            return transport_generation_;
        }

        // Acquire only an unleased slot whose producer EVENT is complete and
        // whose previously published frame has received an exact consumer ACK.
        [[nodiscard]] bool acquire_writable_slot(
            ID3D11DeviceContext* context,
            std::uint64_t frame_id,
            std::uint32_t preferred_slot,
            std::uint32_t& out_slot) noexcept;

        // Release a lease if native rendering failed before an EVENT was issued.
        bool abandon_writable_slot(
            std::uint32_t slot,
            std::uint64_t frame_id) noexcept;

        // End() the per-slot EVENT after all eye rendering/copies have been
        // queued. Publication remains forbidden until GetData reports S_OK.
        bool signal_producer_complete(
            ID3D11DeviceContext* context,
            std::uint32_t slot,
            std::uint64_t frame_id) noexcept;

        // Non-blocking publication. S_FALSE keeps the slot producer-pending;
        // query errors quarantine the ring instead of making reuse assumptions.
        [[nodiscard]] bool publish_completed(
            ID3D11DeviceContext* context,
            std::uint32_t slot,
            std::uint64_t frame_id,
            OutRunVR::Core::FrameSlot& out_slot) noexcept;

        // Only the intended consumer, same producer run/transport generation,
        // same slot and an ACK covering the published frame can release a slot.
        [[nodiscard]] bool acknowledge(
            const OutRunVR::Core::FrameAck& ack) noexcept;

        [[nodiscard]] ID3D11Texture2D* eye(
            std::uint32_t slot, std::uint32_t eye_index) const noexcept;
        [[nodiscard]] ID3D11RenderTargetView* rtv(
            std::uint32_t slot, std::uint32_t eye_index) const noexcept;
        [[nodiscard]] HANDLE shared_handle(
            std::uint32_t slot, std::uint32_t eye_index) const noexcept;
        [[nodiscard]] ID3D11Query* producer_fence(
            std::uint32_t slot) const noexcept;

    private:
        enum class FenceState : std::uint8_t
        {
            Complete,
            Pending,
            Error,
        };

        [[nodiscard]] FenceState poll_producer_fence(
            ID3D11DeviceContext* context,
            SharedEyeSlot& slot) noexcept;
        [[nodiscard]] bool describe_published_slot(
            std::uint32_t slot,
            OutRunVR::Core::FrameSlot& out_slot) const noexcept;

        std::array<SharedEyeSlot, OutRunVR::RenderFrameRingSize> slots_{};
        std::uint32_t width_{};
        std::uint32_t height_{};
        DXGI_FORMAT format_ = DXGI_FORMAT_UNKNOWN;
        std::uint32_t producer_pid_{};
        std::uint32_t consumer_pid_{};
        std::uint32_t run_generation_{};
        std::uint32_t transport_generation_{};
        bool ready_ = false;
        bool synchronization_faulted_ = false;
    };

    static_assert(OutRunVR::RenderFrameRingSize == 4);
}
