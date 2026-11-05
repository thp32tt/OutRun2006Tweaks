#pragma once
// Original D3D9 partial TARGET|ZBUFFER Clear before the FIRST real native
// Draw: stage color and depth together, then replay in their respective
// D3D11 RTV/DSV paths. No half-published ledgers on a failed D3D9 call.
#include "native_game_pre_draw_depth.hpp"
namespace outrun::vr::dx11::live_game_frame {
struct GameNativePreDrawCombinedClear {
    template<class Rect>
    [[nodiscard]] static constexpr bool record(
        GameNativePreDrawFills& colors, GameNativePreDrawDepth& depths,
        std::uintptr_t owner, std::uintptr_t rt, std::uintptr_t ds,
        std::uint32_t w, std::uint32_t h,
        std::uint32_t vx, std::uint32_t vy,
        std::uint32_t vw, std::uint32_t vh,
        std::uint32_t count, const Rect* rects,
        std::uint32_t argb, float z) noexcept {
        // Main D3D9 Z ownership and the pending full-depth seed must
        // additionally be verified by the real-game hook before this call.
        if (!owner || !rt || !ds || !(z >= 0.f && z <= 1.f))
            return false;
        auto stagedColor = colors;
        auto stagedDepth = depths;
        if (!stagedColor.record_target_clear(
                owner, rt, w, h, vx, vy, vw, vh, count, rects, argb) ||
            !stagedDepth.record(
                owner, rt, ds, w, h, vx, vy, vw, vh, count, rects, z))
            return false;
        colors = stagedColor;
        depths = stagedDepth;
        return true;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
