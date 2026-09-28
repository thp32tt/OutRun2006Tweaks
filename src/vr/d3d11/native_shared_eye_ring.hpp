#pragma once

#include <array>
#include <cstdint>
#include <d3d11.h>
#include <wrl/client.h>

#include "vr/ipc/protocol.hpp"

namespace outrun::vr::dx11
{
    struct SharedEyeSlot
    {
        Microsoft::WRL::ComPtr<ID3D11Texture2D> eye[2];
        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> rtv[2];
        Microsoft::WRL::ComPtr<ID3D11Query> producer_fence;
        HANDLE shared_handle[2]{};
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

        [[nodiscard]] bool ready() const noexcept { return ready_; }
        [[nodiscard]] std::uint32_t width() const noexcept { return width_; }
        [[nodiscard]] std::uint32_t height() const noexcept { return height_; }
        [[nodiscard]] DXGI_FORMAT format() const noexcept { return format_; }

        [[nodiscard]] ID3D11Texture2D* eye(
            std::uint32_t slot, std::uint32_t eye_index) const noexcept;
        [[nodiscard]] ID3D11RenderTargetView* rtv(
            std::uint32_t slot, std::uint32_t eye_index) const noexcept;
        [[nodiscard]] HANDLE shared_handle(
            std::uint32_t slot, std::uint32_t eye_index) const noexcept;
        [[nodiscard]] ID3D11Query* producer_fence(
            std::uint32_t slot) const noexcept;

    private:
        std::array<SharedEyeSlot, OutRunVR::RenderFrameRingSize> slots_{};
        std::uint32_t width_{};
        std::uint32_t height_{};
        DXGI_FORMAT format_ = DXGI_FORMAT_UNKNOWN;
        bool ready_ = false;
    };

    static_assert(OutRunVR::RenderFrameRingSize == 4);
}
