#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
struct GameOutputSignature {
    std::uintptr_t device = 0u;
    std::uint32_t width = 0u, height = 0u, format = 0u;
    // Canonical Present backbuffer IUnknown identity. A same-mode surface
    // replacement can occur during menu/car/race transitions without a
    // device, width, height or format change.
    std::uintptr_t backbufferIdentity = 0u;
    [[nodiscard]] constexpr bool valid() const noexcept {
        return device != 0u && width != 0u && height != 0u && format != 0u &&
               backbufferIdentity != 0u;
    }
    [[nodiscard]] constexpr bool same(const GameOutputSignature& other) const noexcept {
        return valid() && other.valid() && device == other.device &&
               width == other.width && height == other.height && format == other.format &&
               backbufferIdentity == other.backbufferIdentity;
    }
};
// A completed GPU event might contain a previous game menu/car/race scene.
// Bound diagnostic presentation by real game Present count, without CPU waits.
struct GameReadbackProvenance {
    static constexpr std::uint64_t kMaxPresentLag = 2u;
    std::uint64_t capturedAtPresent = 0u;
    std::uint64_t sourceDraws = 0u;
    std::uintptr_t sourceDevice = 0u;
    std::uint64_t outputGeneration = 0u;
    [[nodiscard]] constexpr bool same_output(std::uint64_t currentGeneration) const noexcept {
        return outputGeneration != 0u && outputGeneration == currentGeneration;
    }
    [[nodiscard]] constexpr bool same_device(std::uintptr_t presentDevice) const noexcept {
        return sourceDevice != 0u && presentDevice == sourceDevice;
    }
    [[nodiscard]] constexpr bool may_overlay(std::uint64_t currentPresent) const noexcept {
        return sourceDraws != 0u && currentPresent > capturedAtPresent &&
               currentPresent - capturedAtPresent <= kMaxPresentLag;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
