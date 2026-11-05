#pragma once
#include <cstdint>
#include <array>
namespace outrun::vr::dx11::live_game_frame {
// Actual D3D9 menu/car/race RT0 GPU Draw admission, not a no-op Draw shortcut.
// The optional one-RT D3D11 native renderer cannot reproduce extra MRT writes
// or conditional stencil, but can render through genuinely inert bindings.
struct GameNativeStencilEvidence {
    bool enabled = false;
    bool known = false;
    bool twoSided = false;
    std::uint32_t frontCompare = 0u;
    std::uint32_t backCompare = 0u;
    std::uint32_t writeMask = 0xffffffffu;
    bool operationsKnown = false;
    std::array<std::uint32_t, 3> frontOps{};
    std::array<std::uint32_t, 3> backOps{};
};
struct GameNativeInertStencilMrt {
    static constexpr std::uint32_t kCompareAlways = 8u; // D3DCMP_ALWAYS
    [[nodiscard]] static constexpr bool stencil_equivalent_to_disabled(
        bool enabled, bool known, std::uint32_t compare,
        std::uint32_t writeMask, bool twoSided) noexcept {
        return !enabled || (known && compare == kCompareAlways &&
                            writeMask == 0u && !twoSided);
    }
    // A D3D9 stencil binding can be omitted from the native D3D11 OM only
    // if EVERY front/back fragment passes the test AND no fragment writes
    // stencil. A zero write mask is sufficient even with non-KEEP ops.
    // A nonzero mask is inert only when all relevant operations are KEEP.
    // An unknown comparison, operation or back-face mode is never admitted.
    [[nodiscard]] static constexpr bool draw_inert(
        const GameNativeStencilEvidence& s) noexcept {
        if (!s.enabled) return true;
        if (!s.known || s.frontCompare != kCompareAlways ||
            (s.twoSided && s.backCompare != kCompareAlways)) return false;
        if (s.writeMask == 0u) return true;
        if (!s.operationsKnown) return false;
        for (const auto op : s.frontOps) if (op != 1u) return false;
        if (s.twoSided)
            for (const auto op : s.backOps) if (op != 1u) return false;
        return true;
    }
    [[nodiscard]] static constexpr bool extra_target_inert(
        bool stateKnown, std::uint32_t writeMask) noexcept {
        return stateKnown && writeMask == 0u;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
