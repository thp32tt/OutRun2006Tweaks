#pragma once
namespace outrun::vr::dx11::live_game_frame {
// Native full-frame fixed-function Draw admission rejects stencil-enabled
// game Draws (supported_game_state). Thus a *whole* main-backbuffer stencil
// Clear cannot alter native RTV/DSV results in this admitted subset. The
// D3D9 stencil surface is still cleared by the original game. Any later
// stencil-dependent Draw fails native admission and retains D3D9 fallback.
// Never infer safety from RT0 alone: both original backbuffer and Z/S owner
// identities must be verified before retaining a menu/car/race batch.
struct GameNativeMainStencilClear {
    [[nodiscard]] static constexpr bool may_ignore(
        bool nativeFullFrame, bool originalMainColorSeed,
        bool sameMainDepthStencil, bool fullClearCoverage,
        bool nativeBatchOpen) noexcept {
        return nativeFullFrame && originalMainColorSeed &&
               sameMainDepthStencil && fullClearCoverage && nativeBatchOpen;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
