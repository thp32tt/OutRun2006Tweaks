#include "runtime/menu_content_aspect.hpp"
#include <cmath>
#include <limits>

using OutRunVrMenuAspect::PlanCenteredContent;
using OutRunVrMenuAspect::ShouldCropConfiguredMenu;
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

int main()
{
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
        PlanVisibleCenteredContent(
            -2400, 0, 1040, 1440, 3440, 1440, 0, 0,
            1040.f / 3440.f, 1, 4.f / 3.f).crop ||
        PlanVisibleCenteredContent(
            0, 0, 3440, 1440, 3440, 1440,
            std::numeric_limits<float>::quiet_NaN(), 0, 1, 1,
            4.f / 3.f).crop)
        return 19;

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
    // Two asymmetric Quest-style FOVs must average the actual tangent
    // plane. tan(mean angle) causes a different apparent menu aspect.
    const float l0 = -0.72f, r0 = 0.81f, d0 = -0.65f, u0 = 0.83f;
    const float l1 = -1.06f, r1 = 0.91f, d1 = -0.87f, u1 = 0.76f;
    const auto shared = PlanCommonFovTangents(
        l0, r0, d0, u0, l1, r1, d1, u1);
    if (!shared.valid ||
        std::fabs(shared.left - 0.5f * (std::tan(l0) + std::tan(l1))) > 1e-6f ||
        std::fabs(shared.right - 0.5f * (std::tan(r0) + std::tan(r1))) > 1e-6f ||
        std::fabs(shared.down - 0.5f * (std::tan(d0) + std::tan(d1))) > 1e-6f ||
        std::fabs(shared.up - 0.5f * (std::tan(u0) + std::tan(u1))) > 1e-6f)
        return 2;
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
