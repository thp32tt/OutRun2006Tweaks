#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// A completed GPU event might contain a previous game menu/car/race scene.
// Bound diagnostic presentation by real game Present count, without CPU waits.
struct GameReadbackProvenance {
    static constexpr std::uint64_t kMaxPresentLag = 2u;
    std::uint64_t capturedAtPresent = 0u;
    std::uint64_t sourceDraws = 0u;
    std::uintptr_t sourceDevice = 0u;
    [[nodiscard]] constexpr bool same_device(std::uintptr_t presentDevice) const noexcept {
        return sourceDevice != 0u && presentDevice == sourceDevice;
    }
    [[nodiscard]] constexpr bool may_overlay(std::uint64_t currentPresent) const noexcept {
        return sourceDraws != 0u && currentPresent > capturedAtPresent &&
               currentPresent - capturedAtPresent <= kMaxPresentLag;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
