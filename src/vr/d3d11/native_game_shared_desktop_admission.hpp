#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// A GPU-only D3D11->D3D9Ex backbuffer transfer must cover the actual
// source and destination frame. Cropped/menu dirty updates stay on the
// original D3D9 or independently verified CPU tile-upload path.
struct NativeSharedDesktopAdmission {
    [[nodiscard]] static constexpr bool allowed(
        bool optIn, bool full, bool complete, bool writable,
        bool sameOwner, bool fullSourceRegion, bool completeDirty,
        bool compatibleBgra, bool nonMsaa,
        std::uint32_t width, std::uint32_t height,
        std::uint64_t generation) noexcept {
        return optIn && full && complete && writable && sameOwner &&
            fullSourceRegion && completeDirty && compatibleBgra && nonMsaa &&
            width > 0 && height > 0 && generation > 0;
    }
};
static_assert(NativeSharedDesktopAdmission::allowed(
    true,true,true,true,true,true,true,true,true,1920,1080,1));
static_assert(!NativeSharedDesktopAdmission::allowed(
    true,true,true,true,true,false,true,true,true,1920,1080,1));
} // namespace outrun::vr::dx11::live_game_frame
