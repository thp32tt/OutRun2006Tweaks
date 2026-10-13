#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace outrun::vr::dx11 {
// Accept only locally allocated native game color targets. A shared resource
// opened via a new transport view may alias a ring-owned output allocation
// even when the local COM identity no longer matches the original object.
[[nodiscard]] constexpr bool native_game_eye_local_render_target_admitted(
    std::uint32_t bindFlags, std::uint32_t miscFlags,
    std::uint32_t renderTargetFlag, std::uint32_t sharedFlags) noexcept {
    return renderTargetFlag != 0u &&
        (bindFlags & renderTargetFlag) == renderTargetFlag &&
        (miscFlags & sharedFlags) == 0u;
}
// Source eyes are local game-rendered RTs; the ring publishes single-sample
// shared textures. A multisampled stereo pair needs an explicit DX11 GPU
// resolve, never a CopyResource into a single-sample allocation. Reject
// mismatched eye sample modes and missing format resolve support before any
// GPU commands, leaving the acquired slot and original D3D9 frame intact.
enum class NativeGameEyeTransfer : std::uint8_t { Reject, Copy, Resolve };
[[nodiscard]] constexpr NativeGameEyeTransfer native_game_eye_transfer(
    std::uint32_t leftSamples, std::uint32_t leftQuality,
    std::uint32_t rightSamples, std::uint32_t rightQuality,
    bool formatSupportsResolve) noexcept {
    if (leftSamples == 0u || leftSamples > 32u ||
        leftSamples != rightSamples ||
        leftQuality != rightQuality)
        return NativeGameEyeTransfer::Reject;
    if (leftSamples == 1u)
        return leftQuality == 0u
            ? NativeGameEyeTransfer::Copy
            : NativeGameEyeTransfer::Reject;
    return formatSupportsResolve
        ? NativeGameEyeTransfer::Resolve
        : NativeGameEyeTransfer::Reject;
}
// Compare canonical IUnknown identities, not interface pointers: two views of
// one eye or an in-flight ring output must never enter CopyResource as a source.
// Reject partially initialized rings rather than trust incomplete provenance.
template <std::size_t N>
[[nodiscard]] constexpr bool native_game_eye_pair_sources_admitted(
    std::uintptr_t left, std::uintptr_t right,
    const std::array<std::uintptr_t, N>& ringOwned) noexcept {
    if (!left || !right || left == right) return false;
    for (const auto identity : ringOwned)
        if (!identity || identity == left || identity == right) return false;
    return true;
}
} // namespace outrun::vr::dx11
