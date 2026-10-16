#pragma once
#include <cstdint>
#include "native_game_partial_dirty_upload.hpp"

namespace outrun::vr::dx11::live_game_frame {
// A GPU-only D3D11->D3D9Ex backbuffer transfer must cover the actual
// source and destination frame. Cropped/menu dirty updates stay on the
// original D3D9 or independently verified CPU tile-upload path.
struct NativeSharedDesktopRegion {
    GameNativePresentRegion source{};
    bool valid = false;
};
struct NativeSharedDesktopAdmission {
    // A full native game GPU frame can update one precise visible region
    // without touching game-owned backbuffer pixels outside that rectangle.
    // Whole/partitioned dirty regions covering the visible crop collapse to
    // a single copy; incomplete multi-rect regions remain on the D3D9/CPU path.
    [[nodiscard]] static constexpr NativeSharedDesktopRegion select_region(
        std::uint32_t width, std::uint32_t height,
        GameNativePresentRegion present, bool hasDirty, bool oneDirty,
        bool fullDirty, bool cropDirty, bool partitionCrop,
        GameNativePartialDirtySelection partial) noexcept {
        if (!present.full_frame_placement(width,height,width,height).valid)
            return {};
        if (!hasDirty || fullDirty || cropDirty || partitionCrop)
            return {present, true};
        if (oneDirty && partial.valid &&
            partial.source.full_frame_placement(width,height,width,height).valid &&
            partial.source.left >= present.left &&
            partial.source.top >= present.top &&
            partial.source.right <= present.right &&
            partial.source.bottom <= present.bottom)
            return {partial.source, true};
        return {};
    }
    // BGRA8 native shared memory is imported on D3D9Ex as A8R8G8B8.
    // Both A8 and X8 game backbuffers have identical RGB channel storage:
    // D3D9 StretchRect drops alpha for X8, and a failed format conversion
    // returns to the original game-owned Draw/Present without CPU readback.
    [[nodiscard]] static constexpr bool destination_compatible(
        std::uint32_t actual, std::uint32_t argb, std::uint32_t xrgb) noexcept {
        return actual == argb || actual == xrgb;
    }
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
