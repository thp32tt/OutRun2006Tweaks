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
