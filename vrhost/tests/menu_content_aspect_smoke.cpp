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
