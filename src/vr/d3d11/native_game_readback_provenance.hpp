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
    // Preserve Present crop/dirty-mode identity while asynchronous D3D11
    // readback is in flight. Default values preserve legacy aggregate probes.
    std::int64_t sourceLeft = 0, sourceTop = 0;
    std::int64_t sourceRight = 0, sourceBottom = 0;
    bool hasDirtyRegion = false;
    [[nodiscard]] constexpr bool valid() const noexcept {
        return device != 0u && width != 0u && height != 0u && format != 0u &&
               backbufferIdentity != 0u;
    }
    [[nodiscard]] constexpr bool same(const GameOutputSignature& other) const noexcept {
        return valid() && other.valid() && device == other.device &&
               width == other.width && height == other.height && format == other.format &&
               backbufferIdentity == other.backbufferIdentity &&
               sourceLeft == other.sourceLeft &&
               sourceTop == other.sourceTop &&
               sourceRight == other.sourceRight &&
               sourceBottom == other.sourceBottom &&
               hasDirtyRegion == other.hasDirtyRegion;
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
    // Native full-backbuffer readbacks replace the whole game image. If the
    // *current* D3D9 draw stream was not fully mirrored, retire even pending
    // GPU-fenced copies from earlier Presents by advancing outputGeneration.
    // The bounded inset remains diagnostic and may use a lagged sample.
    [[nodiscard]] static constexpr bool quarantine_full_frame(
        bool fullMode, bool currentFullFrameComplete,
        bool outputWritable) noexcept {
        return fullMode && (!currentFullFrameComplete || !outputWritable);
    }
    // Full-resolution output replaces the entire game backbuffer. Unlike the
    // diagnostic inset, it must originate from THIS Present, not one or two
    // game frames ago with a still-matching COM backbuffer identity.
    [[nodiscard]] constexpr bool may_present(
        std::uint64_t currentPresent, bool fullMode) const noexcept {
        return sourceDraws != 0u &&
            (fullMode ? capturedAtPresent == currentPresent
                      : may_overlay(currentPresent));
    }
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
