#pragma once
namespace outrun::vr::dx11::live_game_frame {
// An authentic original-game whole-backbuffer ColorFill may seed the first
// native GPU Draw without a D3D9 TARGET Clear. Never infer geometry or
// publication from ColorFill alone; no skipped, aborted or foreign draws.
[[nodiscard]] constexpr bool native_game_full_color_fill_can_seed(
    bool fullSurface, bool noExistingSeed,
    bool noPriorSourceDraw, bool noPriorNativeDraw,
    bool pristineScene, bool canonicalGameOwner,
    bool boundGameBackbuffer, bool matchingExtents,
    bool compatibleFormat, bool noMsaa) noexcept {
    return fullSurface && noExistingSeed && noPriorSourceDraw &&
        noPriorNativeDraw && pristineScene && canonicalGameOwner &&
        boundGameBackbuffer && matchingExtents && compatibleFormat && noMsaa;
}
} // namespace outrun::vr::dx11::live_game_frame
