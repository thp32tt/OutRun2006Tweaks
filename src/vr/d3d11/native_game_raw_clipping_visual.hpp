#pragma once
// Authentic D3D9 CLIPPING render state admission for the live native game
// Draw and DrawIndexed paths. D3D11 performs homogeneous clipping even when
// the source D3D9 rasterizer was instructed to suppress it. Such geometry is
// at best a visual-only diagnostic approximation, NEVER a full native frame.
#include <cstdint>

namespace outrun::vr::dx11 {
enum class NativeGameClippingMode : std::uint8_t {
    Reject, Exact, RawDiagnostic
};
[[nodiscard]] constexpr NativeGameClippingMode native_game_clipping_mode(
    std::uint32_t sourceClipping, bool rawVisualOptIn) noexcept {
    // A failed COM read is rejected by the caller. Unknown DWORDs are not
    // interpreted as boolean true, even in the opt-in preview.
    if (sourceClipping == 1u) return NativeGameClippingMode::Exact;
    if (sourceClipping == 0u && rawVisualOptIn)
        return NativeGameClippingMode::RawDiagnostic;
    return NativeGameClippingMode::Reject;
}
// CLIPPING=FALSE disables effective D3D9 user-plane clipping too. Keep the
// authenticated source register read, but never synthesize clip distances
// in the intentionally incomplete RAW diagnostic. Exact native Draws still
// use the entire proven source mask and fall back on unsafe coefficients.
[[nodiscard]] constexpr std::uint32_t native_game_user_clip_mask(
    std::uint32_t sourceMask, NativeGameClippingMode mode) noexcept {
    return mode == NativeGameClippingMode::RawDiagnostic ? 0u : sourceMask;
}
} // namespace outrun::vr::dx11
