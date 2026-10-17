#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// A real DX11 menu/car/race GPU color source can be copied directly when
// single-sampled, or resolved into a private one-sample texture before the
// existing fenced D3D9Ex shared-desktop transfer. All other cases keep the
// original game Draw/Present/input path and do not expose partial pixels.
enum class NativeSharedDesktopSourceTransfer : std::uint8_t {
    Reject, Copy, Resolve
};
[[nodiscard]] constexpr NativeSharedDesktopSourceTransfer
native_shared_desktop_source_transfer(
    std::uint32_t mipLevels, std::uint32_t arraySize,
    std::uint32_t samples, std::uint32_t sampleQuality,
    bool renderTarget, bool formatSupportsResolve) noexcept {
    if (mipLevels != 1u || arraySize != 1u ||
        samples == 0u || samples > 32u)
        return NativeSharedDesktopSourceTransfer::Reject;
    if (samples == 1u)
        return sampleQuality == 0u
            ? NativeSharedDesktopSourceTransfer::Copy
            : NativeSharedDesktopSourceTransfer::Reject;
    return renderTarget && formatSupportsResolve
        ? NativeSharedDesktopSourceTransfer::Resolve
        : NativeSharedDesktopSourceTransfer::Reject;
}
static_assert(native_shared_desktop_source_transfer(
    1u, 1u, 1u, 0u, false, false) ==
    NativeSharedDesktopSourceTransfer::Copy);
static_assert(native_shared_desktop_source_transfer(
    1u, 1u, 4u, 0u, true, true) ==
    NativeSharedDesktopSourceTransfer::Resolve);
static_assert(native_shared_desktop_source_transfer(
    1u, 1u, 4u, 0u, true, false) ==
    NativeSharedDesktopSourceTransfer::Reject);
} // namespace outrun::vr::dx11::live_game_frame
