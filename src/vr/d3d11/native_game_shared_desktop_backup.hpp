#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// Reusable rollback surfaces belong to one real D3D9Ex device and native
// output generation. Rect positions may move between menu/car/race Presents;
// only the tile allocation shape, format and lifetime define reusability.
// No stale tile pixels may be consumed: every Present snapshots its original
// D3D9 backbuffer into the selected surface before the first native blit.
struct NativeSharedDesktopBackupKey {
    std::uint32_t width{};
    std::uint32_t height{};
    std::uint32_t format{};
    std::uint64_t generation{};
    std::uintptr_t device{};

    [[nodiscard]] constexpr bool valid() const noexcept {
        return width != 0u && height != 0u && format != 0u &&
               generation != 0u && device != 0u;
    }
    [[nodiscard]] constexpr bool reusable_for(
        const NativeSharedDesktopBackupKey& requested) const noexcept {
        return valid() && requested.valid() &&
            width == requested.width && height == requested.height &&
            format == requested.format &&
            generation == requested.generation &&
            device == requested.device;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
