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
} // namespace outrun::vr::dx11
