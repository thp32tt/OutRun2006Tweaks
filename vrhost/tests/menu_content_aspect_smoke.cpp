#include "runtime/menu_content_aspect.hpp"
#include <cmath>
#include <limits>

using OutRunVrMenuAspect::PlanCenteredContent;

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
constexpr auto portrait = PlanCenteredContent(9.0f / 16.0f, 4.0f / 3.0f);
static_assert(!portrait.crop && portrait.width == 1.0f);
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
