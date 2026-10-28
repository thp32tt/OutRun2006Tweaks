#pragma once
// Safe visual-only FVF fog admission for an explicitly enabled native GPU
// RAW diagnostic tile. The FVF DX11 shader deliberately omits active fog.
// Never use this helper to certify full native source-frame color parity.
#include <cmath>
#include <cstdint>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool native_raw_fvf_fog_visual_admission(
    bool rawVisualOptIn, bool allSourceQueriesSucceeded,
    std::uint32_t tableMode, std::uint32_t vertexMode,
    std::uint32_t rangeFog, float start, float end, float density) noexcept {
    // D3D9 fog enum: NONE=0, EXP=1, EXP2=2, LINEAR=3.
    // Actual disabled/inert fog uses the regular exact FVF route instead.
    if (!rawVisualOptIn || !allSourceQueriesSucceeded ||
        tableMode > 3u || vertexMode > 3u ||
        (tableMode == 0u && vertexMode == 0u) ||
        (rangeFog != 0u && rangeFog != 1u)) return false;
    // A broken float state or reversed linear interval is NOT a visual-only
    // mismatch with known source behavior. Keep the D3D9 fallback untouched.
    if (!std::isfinite(start) || !std::isfinite(end) ||
        !std::isfinite(density) || density < 0.0f ||
        ((tableMode == 3u || vertexMode == 3u) && !(end > start)))
        return false;
    return true;
}
} // namespace outrun::vr::dx11
