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
    // Original game Clear has succeeded before this observation. Stencil-only
    // Clear has no native DSV depth effect; Z-containing Clear does.
    // Caller must independently prove the canonical main Z/S COM identity.
    [[nodiscard]] static constexpr bool preserves_clear_coverage(
        bool clearsDepth, bool coversWholeDepth) noexcept {
        return !clearsDepth || coversWholeDepth;
    }
    [[nodiscard]] static constexpr bool may_ignore(
        bool nativeFullFrame, bool originalMainColorSeed,
        bool sameMainDepthStencil, bool fullClearCoverage,
        bool nativeBatchOpen) noexcept {
        return nativeFullFrame && originalMainColorSeed &&
               sameMainDepthStencil && fullClearCoverage && nativeBatchOpen;
    }

    // Before the FIRST native Draw, stencil-only or TARGET|Z|STENCIL
    // partial Clears can retain an owned full-frame color/Z seed. Unlike
    // post-Draw ClearView, no native DSV exists yet: require the verified
    // canonical D3D9 Z/S COM surface, a pristine source Draw ordinal,
    // bounded rectangles and fail-closed native stencil-free admission.
    // Actual Z rectangles are staged separately and atomically with color.
    // For Z|STENCIL without TARGET, the existing first-Draw depth-only tile
    // recorder applies the Z pixels. Stencil neutrality never implies that
    // a real D3D9 depth write can be discarded.
    [[nodiscard]] static constexpr bool may_ignore_pre_draw(
        bool nativeFullFrame, bool originalMainColorSeed,
        bool sameMainDepthStencil, bool beforeFirstSourceDraw,
        bool boundedSourceRects) noexcept {
        return nativeFullFrame && originalMainColorSeed &&
               sameMainDepthStencil && beforeFirstSourceDraw &&
               boundedSourceRects;
    }

    // A clipped main TARGET/Z/STENCIL Clear is stencil-neutral to admitted
    // native Draws (whose stencil test and writes are disabled). The caller
    // must FIRST prove a live Draw, canonical main depth owner, bounded game
    // rectangles and an owned native D32 depth view. This never permits an
    // unknown stencil-dependent geometry Draw or foreign depth attachment.
    [[nodiscard]] static constexpr bool may_ignore_cropped(
        bool nativeFullFrame, bool originalMainColorSeed,
        bool sameMainDepthStencil, bool liveNativeDraw,
        bool boundedSourceRects, bool ownedNativeDepthReady) noexcept {
        return nativeFullFrame && originalMainColorSeed &&
               sameMainDepthStencil && liveNativeDraw &&
               boundedSourceRects && ownedNativeDepthReady;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
