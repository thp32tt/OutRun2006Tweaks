#pragma once
// Safe visual-only FVF fog admission for an explicitly enabled native GPU
// RAW diagnostic tile. The FVF DX11 shader deliberately omits active fog.
// Never use this helper to certify full native source-frame color parity.
#include <cmath>
#include <cstdint>
#include "live_game_sm3_table_fog.hpp" // common D3D9 table-over-vertex equation
#include "native_game_fvf_fog_dispatch.hpp" // source SPECULAR shading

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
// Never use RAW admission as proof of complete source-frame color parity.
[[nodiscard]] inline bool native_raw_fvf_specular_fog_visual_admission(
    bool rawOptIn, bool known, bool sourceHasSpecular, bool specularEnabled,
    unsigned shadeMode, std::uint32_t tableMode, std::uint32_t vertexMode,
    std::uint32_t rangeFog, float start, float end, float density) noexcept {
    return sourceHasSpecular && specularEnabled &&
        native_fvf_vertex_specular_shade_admitted(shadeMode) &&
        native_raw_fvf_fog_visual_admission(
            rawOptIn, known, tableMode, vertexMode,
            rangeFog, start, end, density);
}
} // namespace outrun::vr::dx11
