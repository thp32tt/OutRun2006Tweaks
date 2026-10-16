#include "runtime/menu_content_aspect.hpp"
#include "vr/ui/ui_side_spacing.hpp"
#include "vr/ui/menu_quad_transform.hpp"
#include <cmath>
#include <limits>

// Original game HUD side spacing must use the SAME 4:3 min-axis
// containment as the menu sprite renderer on portrait VDXR eye sizes.
// Preserve the existing 16:9 and 21:9 OnlineArcade rail widths.
using OutRunVrUiAspect::ContainedSidePaddingPixels;
static_assert(ContainedSidePaddingPixels(1920.f, 640.f, 3.f, 2.25f) == 240.f);
static_assert(ContainedSidePaddingPixels(3440.f, 640.f, 5.375f, 3.f) == 760.f);
static_assert(ContainedSidePaddingPixels(2064.f, 640.f, 3.225f, 4.6f) == 0.f);
static_assert(ContainedSidePaddingPixels(2496.f, 640.f, 3.9f, 5.4f) == 0.f);
// Invalid or narrow dimensions cannot manufacture a negative padding.
static_assert(ContainedSidePaddingPixels(0.f, 640.f, 1.f, 1.f) == 0.f);
static_assert(ContainedSidePaddingPixels(1024.f, 640.f, 2.f, 2.f) == 0.f);

using OutRunVrMenuAspect::PlanCenteredContent;
using OutRunVrMenuAspect::ShouldCropConfiguredMenu;
using OutRunVrMenuAspect::ShouldAutoCropVerifiedFourThree;
// Requested letterboxing is only an INI condition, never proof that actual
// right/left captured pixels are empty. Native 21:9 car-selection content
// must survive with either historical UILetterboxing=1 or 2.
static_assert(!ShouldAutoCropVerifiedFourThree(true, false));
static_assert(!ShouldAutoCropVerifiedFourThree(false, true));
static_assert(!ShouldAutoCropVerifiedFourThree(false, false));
static_assert(ShouldAutoCropVerifiedFourThree(true, true));
// Live Quest3 user profile (UIScalingMode=1, UILetterboxing=1) must crop
// the game's 4:3 letterbox by default, not require a manual environment flag.
static_assert(ShouldCropConfiguredMenu(1, 1));
static_assert(ShouldCropConfiguredMenu(2, 1));
static_assert(ShouldCropConfiguredMenu(1, 2));
// Never cut off full-width vanilla/online menus or a disabled letterbox.
static_assert(!ShouldCropConfiguredMenu(0, 1));
static_assert(!ShouldCropConfiguredMenu(1, 0));
static_assert(!ShouldCropConfiguredMenu(2, 0));
static_assert(!ShouldCropConfiguredMenu(-1, 1));
static_assert(!ShouldCropConfiguredMenu(3, 1));
static_assert(!ShouldCropConfiguredMenu(1, 3));


constexpr auto native43 = PlanCenteredContent(4.0f / 3.0f, 4.0f / 3.0f);
static_assert(!native43.crop && native43.width == 1.0f &&
    native43.offsetX == 0.0f);
constexpr auto wide169 = PlanCenteredContent(16.0f / 9.0f, 4.0f / 3.0f);
static_assert(wide169.crop && wide169.width > 0.749f &&
    wide169.width < 0.751f && wide169.offsetX > 0.124f &&
    wide169.offsetX < 0.126f);
constexpr auto wide219 = PlanCenteredContent(3440.0f / 1440.0f, 4.0f / 3.0f);
static_assert(wide219.crop && wide219.width > 0.557f &&
    wide219.width < 0.559f && wide219.offsetX > 0.220f &&
    wide219.offsetX < 0.222f);
constexpr auto portrait = PlanCenteredContent(2496.0f / 2688.0f, 4.0f / 3.0f);
static_assert(portrait.crop && portrait.width == 1.0f &&
    portrait.offsetY > 0.151f && portrait.offsetY < 0.153f &&
    portrait.height > 0.696f && portrait.height < 0.697f);
constexpr auto invalidZero = PlanCenteredContent(0.0f, 4.0f / 3.0f);
static_assert(!invalidZero.crop);
constexpr auto invalidTarget = PlanCenteredContent(16.0f / 9.0f, -1.0f);
static_assert(!invalidTarget.crop);

// Recycled game HWND must not reuse a different process's menu crop.
// Existing same-run INI polling and invalid-window fallback remain bounded.
using OutRunVrMenuAspect::ShouldRefreshMenuLetterboxConfig;
static_assert(ShouldRefreshMenuLetterboxConfig(0, 0, 0, 0x1234u, 101, 10));
static_assert(!ShouldRefreshMenuLetterboxConfig(
    0x1234u, 101, 2510, 0x1234u, 101, 2509));
static_assert(ShouldRefreshMenuLetterboxConfig(
    0x1234u, 101, 2510, 0x1234u, 102, 200));
static_assert(ShouldRefreshMenuLetterboxConfig(
    0x1234u, 101, 2510, 0x4567u, 101, 200));
static_assert(ShouldRefreshMenuLetterboxConfig(
    0x1234u, 101, 2510, 0x1234u, 0, 200));
static_assert(ShouldRefreshMenuLetterboxConfig(
    0x1234u, 101, 2510, 0, 0, 200));
static_assert(ShouldRefreshMenuLetterboxConfig(
    0x1234u, 101, 2510, 0x1234u, 101, 2510));
static_assert(!ShouldRefreshMenuLetterboxConfig(
    0x1234u, 102, 2700, 0x1234u, 102, 2510));

int main()
{
    // Original 2D game sprite corners: native 4:3, 16:9, 21:9, VDXR
    // portrait and protected non-front-end fallback all remain separated.
    using OutRunVrMenuQuad::BuildPixelMap;
    using OutRunVrMenuQuad::ProjectX;
    using OutRunVrMenuQuad::ProjectY;
    const auto q43 = BuildPixelMap(true,false,2,2,1280,960,640,480);
    const auto q169 = BuildPixelMap(true,false,3,2.25f,1920,1080,640,480);
    const auto q219 = BuildPixelMap(true,false,5.375f,3,3440,1440,640,480);
    const auto qPortrait = BuildPixelMap(true,false,3.9f,5.6f,2496,2688,640,480);
    const auto qVanilla = BuildPixelMap(false,true,5.375f,3,3440,1440,640,480);
    const auto qGameplay = BuildPixelMap(false,false,5.375f,3,3440,1440,640,480);
    auto nearQuad = [](float a,float b) { return std::fabs(a-b) < 1.e-4f; };
    if (!q43.valid || !q169.valid || !q219.valid ||
        !qPortrait.valid || !qVanilla.valid || !qGameplay.valid ||
        !nearQuad(ProjectX(q43,0),0.5f) ||
        !nearQuad(ProjectX(q43,640),1280.5f) ||
        !nearQuad(ProjectY(q43,480),960.5f) ||
        !nearQuad(ProjectX(q169,0),240.5f) ||
        !nearQuad(ProjectX(q169,640),1680.5f) ||
        !nearQuad(ProjectY(q169,480),1080.5f) ||
        !nearQuad(ProjectX(q219,0),760.5f) ||
        !nearQuad(ProjectX(q219,640),2680.5f) ||
        !nearQuad(ProjectY(q219,480),1440.5f) ||
        !nearQuad(ProjectX(qPortrait,640),2496.5f) ||
        !nearQuad(ProjectY(qPortrait,0),408.5f) ||
        !nearQuad(ProjectY(qPortrait,480),2280.5f) ||
        !nearQuad(ProjectX(qVanilla,640),3440.5f) ||
        !nearQuad(ProjectY(qVanilla,480),1440.5f) ||
        !nearQuad(ProjectX(qGameplay,640),1920.5f) ||
        BuildPixelMap(true,false,3,2.25f,0,1080,640,480).valid ||
        BuildPixelMap(true,false,3,2.25f,1920,1080,-640,480).valid ||
        BuildPixelMap(false,true,
            std::numeric_limits<float>::quiet_NaN(),3,3440,1440,640,480).valid ||
        BuildPixelMap(false,true,5.375f,0,3440,1440,640,480).valid)
        return 46;

    // Exact Quest3 A/B failure: a 3440x1440 or 1920x1080 captured
    // a verified letterbox matte may look physically ultrawide with crop OFF.
    // Preserve ALL original UV pixels and only normalize aspect with positive
    // image-matte evidence. Unverified full-width 16:9/21:9 must never be
    // squashed into a second theater. Crop ON, nonletterboxed, partially captured clients,
    // native 4:3/portrait and explicit rollback must remain unaffected.
    using OutRunVrMenuAspect::PlanUncroppedAuthoredMenuAspect;
    const float ultraWide = 3440.f / 1440.f;
    const float wide = 1920.f / 1080.f;
    const float fourThree = 4.f / 3.f;
    if (std::fabs(PlanUncroppedAuthoredMenuAspect(
            ultraWide, ultraWide, true, true, false, false, true) -
            fourThree) > 1e-5f ||
        std::fabs(PlanUncroppedAuthoredMenuAspect(
            wide, wide, true, true, false, false, true) - fourThree) > 1e-5f ||
        // Regression: an INI-only letterbox must NEVER compress complete
        // uncropped 16:9 and 21:9 captures into a nested 4:3 VR screen.
        PlanUncroppedAuthoredMenuAspect(
            ultraWide, ultraWide, true, true, false, false) != ultraWide ||
        PlanUncroppedAuthoredMenuAspect(
            wide, wide, true, true, false, false) != wide ||
        // Proof alone is insufficient without the user's configured mode.
        PlanUncroppedAuthoredMenuAspect(
            ultraWide, ultraWide, false, true, false, false, true) != ultraWide ||
        PlanUncroppedAuthoredMenuAspect(
            ultraWide, ultraWide, false, true, false, false) != ultraWide ||
        PlanUncroppedAuthoredMenuAspect(
            ultraWide, ultraWide, true, false, false, false) != ultraWide ||
        PlanUncroppedAuthoredMenuAspect(
            ultraWide, ultraWide, true, true, true, false) != ultraWide ||
        PlanUncroppedAuthoredMenuAspect(
            ultraWide, ultraWide, true, true, false, true) != ultraWide ||
        PlanUncroppedAuthoredMenuAspect(
            fourThree, fourThree, true, true, false, false) != fourThree ||
        PlanUncroppedAuthoredMenuAspect(
            2496.f / 2688.f, 2496.f / 2688.f,
            true, true, false, false) != 2496.f / 2688.f ||
        !std::isnan(PlanUncroppedAuthoredMenuAspect(
            std::numeric_limits<float>::quiet_NaN(), wide,
            true, true, false, false)) ||
        PlanUncroppedAuthoredMenuAspect(
            ultraWide, std::numeric_limits<float>::infinity(),
            true, true, false, false) != ultraWide)
        return 41;
    using OutRunVrMenuAspect::PlanCapturedAspect;
    constexpr float desktopAspect = 3440.0f / 1440.0f;
    // Fully visible 21:9 and 4:3 mirrors keep exact source proportions.
    if (std::fabs(PlanCapturedAspect(3440, 1440, 1.0f, 1.0f,
            16.0f / 9.0f) - desktopAspect) > 1e-5f ||
        std::fabs(PlanCapturedAspect(1280, 960, 1.0f, 1.0f,
            16.0f / 9.0f) - 4.0f / 3.0f) > 1e-5f)
        return 13;
    // Desktop Duplication / resolution-change: GetGameUv has clipped
    // a half-visible source; uncorrected client aspect would stretch the
    // LOCAL menu 2x. Recompute both portrait and landscape cropped UV.
    if (std::fabs(PlanCapturedAspect(3440, 1440, 0.5f, 1.0f,
            desktopAspect) - desktopAspect * 0.5f) > 1e-5f ||
        std::fabs(PlanCapturedAspect(1920, 1080, 1.0f, 0.5f,
            desktopAspect) - 32.0f / 9.0f) > 1e-5f ||
        std::fabs(PlanCapturedAspect(1920, 1080, 0.5f, 1.0f,
            desktopAspect) - 8.0f / 9.0f) > 1e-5f)
        return 14;
    // Reset, invalid dimensions/UVs, nonfinite and untrusted partial eye
    // publication: never project a NaN, zero or out-of-bounds capture.
    const float fallback = 16.0f / 9.0f;
    const float bad = std::numeric_limits<float>::quiet_NaN();
    const float infUv = std::numeric_limits<float>::infinity();
    if (PlanCapturedAspect(0, 1080, 1.0f, 1.0f, fallback) != fallback ||
        PlanCapturedAspect(1920, 0, 1.0f, 1.0f, fallback) != fallback ||
        PlanCapturedAspect(1920, 1080, 0.0f, 1.0f, fallback) != fallback ||
        PlanCapturedAspect(1920, 1080, 1.01f, 1.0f, fallback) != fallback ||
        PlanCapturedAspect(1920, 1080, bad, 1.0f, fallback) != fallback ||
        PlanCapturedAspect(1920, 1080, 1.0f, infUv, fallback) != fallback ||
        PlanCapturedAspect(1920, 1080, 0.01f, 1.0f, fallback) != fallback ||
        std::fabs(PlanCapturedAspect(1440, 1080, 1.0f, 1.0f,
            fallback) - 4.0f / 3.0f) > 1e-5f)
        return 15;

    // Issue #119: the window's 4:3 authored content must be cropped from
    // ORIGINAL client coordinates even after Desktop Duplication clipped
    // the game client at a monitor edge. Never crop the centre of a
    // partially visible UV as if it still contained the entire client.
    using OutRunVrMenuAspect::PlanVisibleCenteredContent;
    auto near = [](float a, float b) { return std::fabs(a - b) < 1e-4f; };
    const auto visible219 = PlanVisibleCenteredContent(
        0, 0, 3440, 1440, 3440, 1440, 0, 0, 1, 1, 4.f / 3.f);
    if (!visible219.crop ||
        !near(visible219.offsetX, wide219.offsetX) ||
        !near(visible219.width, wide219.width) ||
        !near(visible219.aspect, 4.f / 3.f))
        return 16;
    const auto offLeft = PlanVisibleCenteredContent(
        -320, 0, 3120, 1440, 3440, 1440, 0, 0,
        3120.f / 3440.f, 1, 4.f / 3.f);
    const auto offRight = PlanVisibleCenteredContent(
        280, 0, 3720, 1440, 3440, 1440, 280.f / 3440.f, 0,
        3160.f / 3440.f, 1, 4.f / 3.f);
    if (!offLeft.crop || !offRight.crop ||
        !near(offLeft.offsetX, 440.f / 3120.f) ||
        !near(offLeft.width, 1920.f / 3120.f) ||
        !near(offRight.offsetX, 760.f / 3160.f) ||
        !near(offRight.width, 1920.f / 3160.f) ||
        !near(offLeft.aspect, 4.f / 3.f) ||
        !near(offRight.aspect, 4.f / 3.f))
        return 17;
    // A top-clipped window keeps the sampled physical aspect of the
    // actually visible texture; it must not stretch the missing 360 rows.
    const auto offTop = PlanVisibleCenteredContent(
        0, -360, 3440, 1080, 3440, 1440, 0, 0, 1,
        1080.f / 1440.f, 4.f / 3.f);
    if (!offTop.crop || !near(offTop.aspect, 16.f / 9.f))
        return 18;
    // Visible pixels are a SUB-RECTANGLE of the original authored 4:3
    // geometry. Moving the window may clip the capture but must not zoom
    // the surviving pixels up to the entire HMD menu plane.
    if (!near(visible219.visibleOffsetX, 0.f) ||
        !near(visible219.visibleOffsetY, 0.f) ||
        !near(visible219.visibleWidthScale, 1.f) ||
        !near(visible219.visibleHeightScale, 1.f) ||
        !near(offLeft.visibleOffsetX, 0.f) ||
        !near(offLeft.visibleWidthScale, 1.f) ||
        !near(offRight.visibleOffsetX, 0.f) ||
        !near(offRight.visibleWidthScale, 1.f) ||
        !near(offTop.visibleOffsetY, 0.25f) ||
        !near(offTop.visibleHeightScale, 0.75f))
        return 20;
    // Both edges cropped at once: check the original 4:3 centre and
    // both XY scales, not only the sampled UV's effective aspect.
    const auto partialMenu = PlanVisibleCenteredContent(
        -1240, -360, 2200, 1080, 3440, 1440, 0, 0,
        2200.f / 3440.f, 1080.f / 1440.f, 4.f / 3.f);
    if (!partialMenu.crop ||
        !near(partialMenu.visibleOffsetX, 0.25f) ||
        !near(partialMenu.visibleOffsetY, 0.25f) ||
        !near(partialMenu.visibleWidthScale, 0.75f) ||
        !near(partialMenu.visibleHeightScale, 0.75f) ||
        !near(partialMenu.aspect, 4.f / 3.f))
        return 21;
    // Do not crop native 4:3, stale capture UV after a monitor move,
    // missing/reset source or a strip that cannot fit a coherent menu.
    if (PlanVisibleCenteredContent(
            0, 0, 1280, 960, 1920, 1080, 0, 0,
            1280.f / 1920.f, 960.f / 1080.f, 4.f / 3.f).crop ||
        PlanVisibleCenteredContent(
            0, 0, 3440, 1440, 3440, 1440, 0.3f, 0, 0.7f,
            1, 4.f / 3.f).crop ||
        PlanVisibleCenteredContent(
            0, 0, 3440, 1440, 0, 1440, 0, 0, 1, 1,
            4.f / 3.f).crop ||
        // Only a genuine <5%-of-sampled-width content sliver is too
        // small to keep; the old -2400 offset still exposes a valid
        // 280px-wide authored fragment and must no longer be rejected.
        PlanVisibleCenteredContent(
            -2660, 0, 780, 1440, 3440, 1440, 0, 0,
            780.f / 3440.f, 1, 4.f / 3.f).crop ||
        PlanVisibleCenteredContent(
            0, 0, 3440, 1440, 3440, 1440,
            std::numeric_limits<float>::quiet_NaN(), 0, 1, 1,
            4.f / 3.f).crop)
        return 19;

    // Severe edge clipping can legitimately leave an aspect outside the
    // 0.5..5 FULL-CLIENT range. Never drop the menu's original optical
    // rectangle and inflate these surviving pixels to the full quad.
    // 3440x1440 authored content width is 1920, centred in the client:
    // after shifting left by 2300, only x=[0,380] of the authored content
    // remains visible in the 1140-pixel captured strip.
    const auto narrowLeft = PlanVisibleCenteredContent(
        -2300, 0, 1140, 1440, 3440, 1440, 0, 0,
        1140.f / 3440.f, 1, 4.f / 3.f);
    if (!narrowLeft.crop ||
        !near(narrowLeft.aspect, 380.f / 1440.f) ||
        !near(narrowLeft.offsetX, 0.f) ||
        !near(narrowLeft.width, 380.f / 1140.f) ||
        !near(narrowLeft.visibleOffsetX, 1540.f / 1920.f) ||
        !near(narrowLeft.visibleWidthScale, 380.f / 1920.f) ||
        !near(narrowLeft.visibleHeightScale, 1.f))
        return 31;
    // The corresponding portrait case leaves only 230 of 1872 content
    // rows; its valid tall sampled aspect is >5. This must not zoom or
    // re-centre the strip after a desktop move or recenter.
    const auto narrowTop = PlanVisibleCenteredContent(
        0, -2050, 2496, 638, 2496, 2688, 0, 0,
        1, 638.f / 2688.f, 4.f / 3.f);
    if (!narrowTop.crop ||
        !near(narrowTop.aspect, 2496.f / 230.f) ||
        !near(narrowTop.offsetY, 0.f) ||
        !near(narrowTop.height, 230.f / 638.f) ||
        !near(narrowTop.visibleOffsetY, 1642.f / 1872.f) ||
        !near(narrowTop.visibleHeightScale, 230.f / 1872.f) ||
        !near(narrowTop.visibleWidthScale, 1.f))
        return 32;
    // Even a plausible UV must be rejected if it is stale after a move;
    // the full unclipped 4:3, portrait and 21:9 cases above still apply.
    if (PlanVisibleCenteredContent(
            -2300, 0, 1140, 1440, 3440, 1440, 0.02f, 0,
            1140.f / 3440.f, 1, 4.f / 3.f).crop ||
        PlanVisibleCenteredContent(
            0, -2050, 2496, 638, 2496, 2688, 0, 0.02f,
            1, 638.f / 2688.f, 4.f / 3.f).crop)
        return 33;

    // 2496x2688 portrait menu has 408px upper/lower matte around
    // 2496x1872 authentic 4:3 content. Remove the Y matte from the source.
    const auto portraitFull = PlanVisibleCenteredContent(
        0, 0, 2496, 2688, 2496, 2688, 0, 0, 1, 1, 4.f / 3.f);
    if (!portraitFull.crop ||
        !near(portraitFull.offsetX, 0.f) ||
        !near(portraitFull.width, 1.f) ||
        !near(portraitFull.offsetY, 408.f / 2688.f) ||
        !near(portraitFull.height, 1872.f / 2688.f) ||
        !near(portraitFull.aspect, 4.f / 3.f) ||
        !near(portraitFull.visibleOffsetY, 0.f) ||
        !near(portraitFull.visibleHeightScale, 1.f))
        return 23;
    // Moving the same client off an output top edge must show only the
    // surviving original menu fragment, NOT zoom to a complete 4:3 quad.
    const auto portraitClipped = PlanVisibleCenteredContent(
        0, -800, 2496, 1888, 2496, 2688, 0, 0, 1,
        1888.f / 2688.f, 4.f / 3.f);
    if (!portraitClipped.crop ||
        !near(portraitClipped.offsetY, 0.f) ||
        !near(portraitClipped.height, 1480.f / 1888.f) ||
        !near(portraitClipped.visibleOffsetY, 392.f / 1872.f) ||
        !near(portraitClipped.visibleHeightScale, 1480.f / 1872.f) ||
        !near(portraitClipped.aspect, 2496.f / 1480.f))
        return 24;
    if (PlanVisibleCenteredContent(
            0, 0, 2496, 2688, 2496, 2688,
            0, 0.22f, 1, 0.78f, 4.f / 3.f).crop)
        return 25;

    // Native 4:3 menus have no black matte, but a partially off-output
    // source still occupies only a fragment of the ORIGINAL 4:3 quad.
    // Old behavior returned crop=false and centered the fragment at full
    // optical size, stretching/repositioning it on both Quest eyes.
    const auto native43Left = PlanVisibleCenteredContent(
        -320, 0, 960, 960, 1920, 1080, 0, 0,
        960.f / 1920.f, 960.f / 1080.f, 4.f / 3.f);
    const auto native43Top = PlanVisibleCenteredContent(
        0, -240, 1280, 720, 1920, 1080, 0, 0,
        1280.f / 1920.f, 720.f / 1080.f, 4.f / 3.f);
    const auto native43Right = PlanVisibleCenteredContent(
        1280, 0, 2560, 960, 1920, 1080,
        1280.f / 1920.f, 0, 640.f / 1920.f,
        960.f / 1080.f, 4.f / 3.f);
    if (!native43Left.crop || !native43Top.crop ||
        !native43Right.crop ||
        !near(native43Left.offsetX, 0.f) ||
        !near(native43Left.width, 1.f) ||
        !near(native43Left.visibleOffsetX, 0.25f) ||
        !near(native43Left.visibleWidthScale, 0.75f) ||
        !near(native43Left.aspect, 1.f) ||
        !near(native43Top.visibleOffsetY, 0.25f) ||
        !near(native43Top.visibleHeightScale, 0.75f) ||
        !near(native43Top.aspect, 16.f / 9.f) ||
        !near(native43Right.visibleOffsetX, -0.5f) ||
        !near(native43Right.visibleWidthScale, 0.5f))
        return 26;
    // Full 4:3 visibility must restore no-crop/no-fragment behavior.
    // A stale UV after a monitor change must NOT synthesize a transform.
    if (PlanVisibleCenteredContent(
            0, 0, 1280, 960, 1920, 1080, 0, 0,
            1280.f / 1920.f, 960.f / 1080.f, 4.f / 3.f).crop ||
        PlanVisibleCenteredContent(
            -320, 0, 960, 960, 1920, 1080, 0.05f, 0,
            960.f / 1920.f, 960.f / 1080.f, 4.f / 3.f).crop ||
        PlanVisibleCenteredContent(
            -320, 0, 960, 960, 1920, 1080, 0, 0,
            960.f / 1920.f, 960.f / 1080.f, 4.1f).crop)
        return 27;

    using OutRunVrMenuAspect::PlanCommonFovTangents;
    // Two asymmetric Quest-style FOVs must intersect both eyes' actual
    // tangent planes. Averaging their edges would expose pixels outside
    // one physical eye and clip the shared menu or vehicle selection.
    const float l0 = -0.72f, r0 = 0.81f, d0 = -0.65f, u0 = 0.83f;
    const float l1 = -1.06f, r1 = 0.91f, d1 = -0.87f, u1 = 0.76f;
    const auto shared = PlanCommonFovTangents(
        l0, r0, d0, u0, l1, r1, d1, u1);
    if (!shared.valid ||
        std::fabs(shared.left - (std::max)(std::tan(l0), std::tan(l1))) > 1e-6f ||
        std::fabs(shared.right - (std::min)(std::tan(r0), std::tan(r1))) > 1e-6f ||
        std::fabs(shared.down - (std::max)(std::tan(d0), std::tan(d1))) > 1e-6f ||
        std::fabs(shared.up - (std::min)(std::tan(u0), std::tan(u1))) > 1e-6f)
        return 2;
    // Per-axis disjoint or vanishing binocular overlap is not an eye pair.
    // Fail closed to the existing mono-menu fallback without stretching
    // either HMD eye. Keep the optical plan invalid for rejected pairs.
    const auto disjointHorizontal = PlanCommonFovTangents(
        -1.1f, -0.4f, -0.6f, 0.6f,
         0.4f,  1.1f, -0.6f, 0.6f);
    const auto disjointVertical = PlanCommonFovTangents(
        -0.6f, 0.6f, -1.1f, -0.4f,
        -0.6f, 0.6f,  0.4f,  1.1f);
    if (disjointHorizontal.valid || disjointVertical.valid ||
        OutRunVrMenuAspect::PlanOpticallyCenteredClip(
            disjointHorizontal, 4.f / 3.f).valid ||
        OutRunVrMenuAspect::PlanOpticallyCenteredClip(
            disjointVertical, 4.f / 3.f).valid)
        return 35;
    // The same reconstructed common FOV must be published in each
    // XrCompositionLayerProjectionView, otherwise the shared menu raster
    // would be warped again by OpenXR's per-eye projection.
    if (std::fabs(std::tan(std::atan(shared.left)) - shared.left) > 1e-6f ||
        std::fabs(std::tan(std::atan(shared.right)) - shared.right) > 1e-6f ||
        std::fabs(std::tan(std::atan(shared.down)) - shared.down) > 1e-6f ||
        std::fabs(std::tan(std::atan(shared.up)) - shared.up) > 1e-6f)
        return 7;
    const float oldHorizontal =
        std::tan(0.5f * (r0 + r1)) - std::tan(0.5f * (l0 + l1));
    if (std::fabs((shared.right - shared.left) - oldHorizontal) < 0.002f)
        return 3;
    const auto identical = PlanCommonFovTangents(
        l0, r0, d0, u0, l0, r0, d0, u0);
    if (!identical.valid ||
        std::fabs(identical.right - std::tan(r0)) > 1e-6f)
        return 4;
    // One invalid or inverted eye must never authorize a distorted LOCAL
    // projection, including during intermittent XR extent/FOV transitions.
    if (PlanCommonFovTangents(l0, r0, d0, u0, r1, l1, d1, u1).valid ||
        PlanCommonFovTangents(l0, r0, d0, u0, l1, r1, u1, d1).valid ||
        PlanCommonFovTangents(l0, r0, d0, u0, l1, 1.56f, d1, u1).valid ||
        PlanCommonFovTangents(l0, r0, d0, u0, l1, r1, d1,
            std::numeric_limits<float>::quiet_NaN()).valid)
        return 5;
    // Prior near-pole positive/inverted-free FOVs passed the individual
    // angle guard: one eye's >10 tangent span can still stretch the common
    // menu rectangle in both eyes. Reject per-eye X/Y before averaging.
    // Retain legitimate asymmetric Quest FOV above and reset restoration.
    const auto invalidHorizontal = PlanCommonFovTangents(
        -1.5f, 1.5f, d0, u0, l1, r1, d1, u1);
    const auto invalidVertical = PlanCommonFovTangents(
        l0, r0, d0, u0, l1, r1, -1.5f, 1.5f);
    if (invalidHorizontal.valid || invalidVertical.valid ||
        OutRunVrMenuAspect::PlanOpticallyCenteredClip(invalidHorizontal, 4.f / 3.f).valid ||
        OutRunVrMenuAspect::PlanOpticallyCenteredClip(invalidVertical, 4.f / 3.f).valid)
        return 34;

    // After Reset/recenter a new full eye pair must immediately restore
    // the shared aspect; the routine carries no stale state or UV.
    const auto restored = PlanCommonFovTangents(
        -0.8f, 0.8f, -0.7f, 0.7f, -0.8f, 0.8f, -0.7f, 0.7f);
    if (!restored.valid ||
        std::fabs((restored.right - restored.left) /
            (restored.up - restored.down) -
            std::tan(0.8f) / std::tan(0.7f)) > 1e-5f)
        return 6;

    // Issue #119: off-axis FOV center must map to the straight-ahead ray.
    // The old quad at NDC zero was displaced even with averaged tangents.
    using OutRunVrMenuAspect::PlanOpticallyCenteredClip;
    const auto optical = PlanOpticallyCenteredClip(shared, 4.0f / 3.0f);
    if (!optical.valid || std::fabs(optical.centerX) < 0.01f ||
        std::fabs(shared.left +
            (optical.centerX + 1.0f) * 0.5f *
            (shared.right - shared.left)) > 1e-5f ||
        std::fabs(shared.down +
            (optical.centerY + 1.0f) * 0.5f *
            (shared.up - shared.down)) > 1e-5f)
        return 8;
    // HMD 2026-10-13: a full-FOV theater is cropped/overlarge.
    // Shrink both axes uniformly while leaving the same optical centre,
    // authored 4:3 physical ratio and existing clip-safety checks.
    const auto compact = PlanOpticallyCenteredClip(
        shared, 4.0f / 3.0f, 0.78f);
    if (!compact.valid ||
        std::fabs(compact.centerX - optical.centerX) > 1e-6f ||
        std::fabs(compact.centerY - optical.centerY) > 1e-6f ||
        std::fabs(compact.halfWidth / optical.halfWidth - 0.78f) > 1e-5f ||
        std::fabs(compact.halfHeight / optical.halfHeight - 0.78f) > 1e-5f ||
        std::fabs(compact.halfWidth / compact.halfHeight *
            (shared.right - shared.left) / (shared.up - shared.down) -
            4.0f / 3.0f) > 1e-5f ||
        PlanOpticallyCenteredClip(shared, 4.0f / 3.0f, 0.f).valid ||
        PlanOpticallyCenteredClip(shared, 4.0f / 3.0f, 1.1f).valid ||
        PlanOpticallyCenteredClip(shared, 4.0f / 3.0f,
            std::numeric_limits<float>::quiet_NaN()).valid)
        return 22;
    // Both edges remain on the visible image; physical, not NDC, aspect
    // must equal the cropped 4:3 menu even for asymmetric Quest-style FOV.
    if (std::fabs(optical.centerX) + optical.halfWidth > 1.00001f ||
        std::fabs(optical.centerY) + optical.halfHeight > 1.00001f ||
        std::fabs(optical.halfWidth / optical.halfHeight *
            (shared.right - shared.left) / (shared.up - shared.down) -
            4.0f / 3.0f) > 1e-5f)
        return 9;
    const auto centered = PlanOpticallyCenteredClip(restored, 16.0f / 9.0f);
    if (!centered.valid || std::fabs(centered.centerX) > 1e-6f ||
        std::fabs(centered.centerY) > 1e-6f ||
        std::fabs(centered.halfWidth / centered.halfHeight *
            (restored.right - restored.left) / (restored.up - restored.down) -
            16.0f / 9.0f) > 1e-5f)
        return 10;
    // Reset, aspect change and transition: no cached centre or stale UV.
    const auto ultrawide = PlanOpticallyCenteredClip(
        shared, 3440.0f / 1440.0f);
    if (!ultrawide.valid ||
        !(ultrawide.halfHeight < optical.halfHeight) ||
        std::fabs(ultrawide.centerX - optical.centerX) > 1e-6f)
        return 11;
    if (PlanOpticallyCenteredClip(shared,
            std::numeric_limits<float>::quiet_NaN()).valid ||
        PlanOpticallyCenteredClip(
            {true, 0.10f, 0.50f, -0.7f, 0.8f},
            4.0f / 3.0f).valid ||
        PlanOpticallyCenteredClip(
            {true, -0.8f, 0.8f, -0.7f,
                std::numeric_limits<float>::infinity()},
            4.0f / 3.0f).valid)
        return 12;


    // Mono recovery theater is a distinct path from the shared-eye menu
    // projection. A partially off-output window must retain the original
    // content's physical pixel scale and camera-local fragment position.
    using OutRunVrMenuAspect::PlanVisibleMonoTheaterFragment;
    const auto theaterFull = PlanVisibleMonoTheaterFragment(
        0, 0, 1280, 960, 1920, 1080, 0, 0,
        1280.f / 1920.f, 960.f / 1080.f);
    const auto theaterLeft = PlanVisibleMonoTheaterFragment(
        -320, 0, 960, 960, 1920, 1080, 0, 0,
        960.f / 1920.f, 960.f / 1080.f);
    const auto theaterRight = PlanVisibleMonoTheaterFragment(
        1280, 0, 2560, 960, 1920, 1080,
        1280.f / 1920.f, 0, 640.f / 1920.f, 960.f / 1080.f);
    const auto theaterTop = PlanVisibleMonoTheaterFragment(
        0, -240, 1280, 720, 1920, 1080, 0, 0,
        1280.f / 1920.f, 720.f / 1080.f);
    if (!theaterFull.valid || theaterFull.partial ||
        !near(theaterFull.quadWidth, 2.f) ||
        !near(theaterFull.quadHeight, 1.5f) ||
        !theaterLeft.valid || !theaterLeft.partial ||
        !near(theaterLeft.quadWidth, 1.5f) ||
        !near(theaterLeft.quadHeight, 1.5f) ||
        !near(theaterLeft.offsetRight, 0.25f) ||
        !near(theaterLeft.offsetUp, 0.f) ||
        !theaterRight.valid || !theaterRight.partial ||
        !near(theaterRight.quadWidth, 1.f) ||
        !near(theaterRight.offsetRight, -0.5f) ||
        !theaterTop.valid || !theaterTop.partial ||
        !near(theaterTop.quadWidth, 2.f) ||
        !near(theaterTop.quadHeight, 1.125f) ||
        !near(theaterTop.offsetRight, 0.f) ||
        !near(theaterTop.offsetUp, -0.1875f))
        return 28;

    // Both axes clipped: the fragment's apparent aspect equals the actual
    // sampled pixels, and its local offset is NOT reset to the gaze centre.
    const auto theaterCorner = PlanVisibleMonoTheaterFragment(
        -320, -240, 960, 720, 1920, 1080, 0, 0,
        960.f / 1920.f, 720.f / 1080.f);
    if (!theaterCorner.valid || !theaterCorner.partial ||
        !near(theaterCorner.quadWidth, 1.5f) ||
        !near(theaterCorner.quadHeight, 1.125f) ||
        !near(theaterCorner.offsetRight, 0.25f) ||
        !near(theaterCorner.offsetUp, -0.1875f) ||
        !near(theaterCorner.quadWidth / theaterCorner.quadHeight,
            960.f / 720.f))
        return 29;

    // Invalid, nonfinite, stale or no-intersection capture must leave the
    // existing mono fallback in control. The separate SBS path never opts in.
    if (PlanVisibleMonoTheaterFragment(
            -320, 0, 960, 960, 1920, 1080, 0.1f, 0,
            960.f / 1920.f, 960.f / 1080.f).valid ||
        PlanVisibleMonoTheaterFragment(
            -320, 0, 960, 960, 1920, 1080,
            std::numeric_limits<float>::quiet_NaN(), 0,
            960.f / 1920.f, 960.f / 1080.f).valid ||
        PlanVisibleMonoTheaterFragment(
            2500, 0, 3780, 960, 1920, 1080, 0, 0, 1, 1).valid ||
        PlanVisibleMonoTheaterFragment(
            0, 0, 1280, 960, 0, 1080, 0, 0, 1, 1).valid)
        return 30;

    // Unletterboxed vanilla 16:9 and 21:9 menus also retain full-client
    // placement when capture supplies only a visible part of the window.
    const auto vanillaFull = PlanVisibleCenteredContent(
        0, 0, 1920, 1080, 1920, 1080, 0, 0, 1, 1, 16.f / 9.f);
    const auto vanillaLeft = PlanVisibleCenteredContent(
        -320, 0, 1600, 1080, 1920, 1080,
        0, 0, 1600.f / 1920.f, 1, 16.f / 9.f);
    const auto vanillaBottom = PlanVisibleCenteredContent(
        0, 270, 1920, 1350, 1920, 1080,
        0, 270.f / 1080.f, 1, 810.f / 1080.f, 16.f / 9.f);
    const auto vanillaCorner219 = PlanVisibleCenteredContent(
        -440, -180, 3000, 1260, 3440, 1440,
        0, 0, 3000.f / 3440.f, 1260.f / 1440.f,
        3440.f / 1440.f);
    if (vanillaFull.crop || !vanillaLeft.crop ||
        !vanillaBottom.crop || !vanillaCorner219.crop ||
        !near(vanillaLeft.visibleOffsetX, 320.f / 1920.f) ||
        !near(vanillaLeft.visibleWidthScale, 1600.f / 1920.f) ||
        !near(vanillaBottom.visibleOffsetY, -270.f / 1080.f) ||
        !near(vanillaBottom.visibleHeightScale, 810.f / 1080.f) ||
        !near(vanillaCorner219.visibleOffsetX, 440.f / 3440.f) ||
        !near(vanillaCorner219.visibleOffsetY, 180.f / 1440.f) ||
        !near(vanillaCorner219.visibleWidthScale, 3000.f / 3440.f) ||
        !near(vanillaCorner219.visibleHeightScale, 1260.f / 1440.f))
        return 31;
    // The composed binocular quad must have the physical aspect of the
    // surviving pixels without stretching or optical recentring.
    const auto nativeOptical = PlanOpticallyCenteredClip(
        shared, 16.f / 9.f);
    if (!nativeOptical.valid ||
        !near(nativeOptical.halfWidth * vanillaLeft.visibleWidthScale /
            (nativeOptical.halfHeight * vanillaLeft.visibleHeightScale) *
            (shared.right - shared.left) / (shared.up - shared.down),
            1600.f / 1080.f) ||
        !near(nativeOptical.halfWidth * vanillaBottom.visibleWidthScale /
            (nativeOptical.halfHeight * vanillaBottom.visibleHeightScale) *
            (shared.right - shared.left) / (shared.up - shared.down),
            1920.f / 810.f))
        return 32;
    // After reset/output move, stale UV or invalid capture is not a crop.
    if (PlanVisibleCenteredContent(
            -320, 0, 1600, 1080, 1920, 1080,
            0.1f, 0, 1600.f / 1920.f, 1, 16.f / 9.f).crop ||
        PlanVisibleCenteredContent(
            0, 0, 1920, 1080, 0, 1080, 0, 0, 1, 1,
            16.f / 9.f).crop)
        return 33;

    const auto nan = PlanCenteredContent(
        std::numeric_limits<float>::quiet_NaN(), 4.0f / 3.0f);
    const auto inf = PlanCenteredContent(
        std::numeric_limits<float>::infinity(), 4.0f / 3.0f);
    const auto changed = PlanCenteredContent(1920.0f / 1080.0f, 4.0f / 3.0f);
    const auto recovered = PlanCenteredContent(1280.0f / 960.0f, 4.0f / 3.0f);
    // Resolution/reset must recalculate a fresh plan; no stale cached UV.
    return !nan.crop && !inf.crop && changed.crop &&
        !recovered.crop && std::fabs(wide219.aspect - 4.0f / 3.0f) < 0.0001f
        ? 0 : 1;
}