#pragma once
#include <algorithm>
#include <cmath>

namespace WheelFFBMath
{
    // Unit peak at 0.16 rad. Preserve the original curve except for a short
    // C1 Hermite join on the falling side (0.16..0.176 rad).
    inline float trail_shape(float alpha)
    {
        if (!std::isfinite(alpha)) return 0.0f;
        const float x = std::abs(alpha) / 0.16f;
        constexpr float HalfPi = 1.57079632679f;
        if (x <= 1.0f) return std::sin(x * HalfPi);
        if (x >= 1.1f) return std::exp(-(x - 1.0f) * 0.90f);
        const float t = (x - 1.0f) / 0.1f;
        const float end = std::exp(-0.09f);
        const float endSlope = -0.09f * end;
        return (2*t*t*t - 3*t*t + 1) + (-2*t*t*t + 3*t*t)*end
            + (t*t*t - t*t)*endSlope;
    }

    inline float physics_return_relief(float alpha, float steerRate)
    {
        // Relieve only torque doing positive work on the moving wheel.
        // Steering centre is irrelevant to front-tyre SAT direction.
        const float t = -alpha * steerRate > 0.0f
            ? std::clamp(std::abs(steerRate) / 0.08f, 0.0f, 1.0f) : 0.0f;
        return 1.0f - 0.15f * t*t*(3.0f - 2.0f*t);
    }
}
