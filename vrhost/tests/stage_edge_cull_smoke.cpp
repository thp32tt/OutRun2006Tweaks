#include "vr/game/stage_edge_cull_projection.hpp"
#include <cmath>
#include <limits>

int main()
{
    using OutRunVrStageCull::CorrectBallProjection;
    const auto near = [](float x, float y) noexcept {
        return std::fabs(x - y) < 0.002f;
    };
    // The canonical 4:3 camera must retain exactly the original values.
    const auto native = CorrectBallProjection(100.f, 50.f, 1280.f, 960.f);
    if (!native.valid || !near(native.x, 100.f) ||
        !near(native.y, 50.f))
        return 1;

    // Preserve the original wide/ultrawide/portrait edge visibility
    // transform, including the exact original float arithmetic order.
    for (const auto widthHeight : {
        1920.f / 1080.f, 3440.f / 1440.f, 2496.f / 2688.f })
    {
        const float width = widthHeight * 1440.f;
        const float height = 1440.f;
        const auto corrected = CorrectBallProjection(75.f, -18.f,
            width, height);
        const float oldX = (75.f / (width / height)) * (4.f / 3.f);
        const float oldY = (-18.f * (width / height)) / (4.f / 3.f);
        if (!corrected.valid || corrected.x != oldX ||
            corrected.y != oldY)
            return 2;
    }

    // No partially corrected sphere can be published during native/DX9Ex
    // Resize, Reset/ResetEx, missing viewport, malformed settings, or a
    // finite source coordinate whose second correction overflows.
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float inf = std::numeric_limits<float>::infinity();
    const float maxFloat = std::numeric_limits<float>::max();
    if (CorrectBallProjection(5.f, 9.f, 3440.f, 0.f).valid ||
        CorrectBallProjection(5.f, 9.f, 0.f, 1440.f).valid ||
        CorrectBallProjection(5.f, 9.f, -3440.f, 1440.f).valid ||
        CorrectBallProjection(5.f, 9.f, 3440.f, nan).valid ||
        CorrectBallProjection(5.f, 9.f, 3440.f, inf).valid ||
        CorrectBallProjection(nan, 9.f, 3440.f, 1440.f).valid ||
        CorrectBallProjection(5.f, inf, 3440.f, 1440.f).valid ||
        CorrectBallProjection(5.f, maxFloat, 3440.f, 1440.f).valid ||
        CorrectBallProjection(5.f, 9.f, maxFloat, 0.1f).valid)
        return 3;

    // A later coherent valid frame recovers with no previous-frame cache.
    const auto recovered = CorrectBallProjection(
        75.f, -18.f, 1920.f, 1080.f);
    return recovered.valid && std::isfinite(recovered.x) &&
        std::isfinite(recovered.y) ? 0 : 4;
}
