#pragma once
// Safe visual-only FVF fog admission for an explicitly enabled native GPU
// RAW diagnostic tile. The FVF DX11 shader deliberately omits active fog.
// Never use this helper to certify full native source-frame color parity.
#include <cmath>
#include <cstdint>
#include "live_game_sm3_table_fog.hpp" // common D3D9 table-over-vertex equation

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool native_raw_fvf_fog_visual_admission(
    bool rawVisualOptIn, bool allSourceQueriesSucceeded,
    std::uint32_t tableMode, std::uint32_t vertexMode,
    std::uint32_t rangeFog, float start, float end, float density) noexcept {
    // RANGEFOGENABLE is a live source boolean, not permission to infer a
    // vertex fog equation. The active table equation overrides inherited
    // vertex fog: unused start/end/density register payload is immaterial
    // ONLY when the corresponding getter was intentionally not required.
    // Preserve strict source-query, mode and opt-in checks from SM3 RAW.
    if (rangeFog != 0u && rangeFog != 1u) return false;
    return native_sm3_raw_visual_fog_omission(
        rawVisualOptIn, allSourceQueriesSucceeded,
        tableMode, vertexMode, start, end, density);
}
} // namespace outrun::vr::dx11
