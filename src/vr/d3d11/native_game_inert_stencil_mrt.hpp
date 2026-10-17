#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Actual D3D9 menu/car/race RT0 GPU Draw admission, not a no-op Draw shortcut.
// The optional one-RT D3D11 native renderer cannot reproduce extra MRT writes
// or conditional stencil, but can render through genuinely inert bindings.
struct GameNativeInertStencilMrt {
    static constexpr std::uint32_t kCompareAlways = 8u; // D3DCMP_ALWAYS
    [[nodiscard]] static constexpr bool stencil_equivalent_to_disabled(
        bool enabled, bool known, std::uint32_t compare,
        std::uint32_t writeMask, bool twoSided) noexcept {
        return !enabled || (known && compare == kCompareAlways &&
                            writeMask == 0u && !twoSided);
    }
    [[nodiscard]] static constexpr bool extra_target_inert(
        bool stateKnown, std::uint32_t writeMask) noexcept {
        return stateKnown && writeMask == 0u;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
