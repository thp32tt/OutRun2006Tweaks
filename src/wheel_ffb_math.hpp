#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <string>
#include <string_view>

namespace WheelFFBMath
{
    inline float smoothstep01(float t)
    {
        t = std::clamp(t, 0.0f, 1.0f);
        return t * t * (3.0f - 2.0f * t);
    }

    // Saturating proxy for front-tyre lateral force. OutRun does not expose
    // per-tyre Fy, so use front slip only for the curve shape and keep the
    // game's lateral signal as a separate load modifier in WheelFFBEngine.
    // The 0.20 rad scale is deliberately broad: normal loaded corners remain
    // progressive while deep understeer approaches a force plateau.
    inline float lateral_force_shape(float alpha)
    {
        if (!std::isfinite(alpha)) return 0.0f;
        constexpr float HalfPi = 1.57079632679f;
        const float x = std::clamp(std::abs(alpha) / 0.20f, 0.0f, 1.0f);
        return std::sin(x * HalfPi);
    }

    // Pneumatic trail remains near full in the linear tyre region, then falls
    // as slip grows. Keep a small residual rather than forcing the pneumatic
    // lever arm mathematically to zero because this is an arcade-state proxy,
    // not a fitted tyre dataset.
    inline float pneumatic_trail_factor(float alpha)
    {
        if (!std::isfinite(alpha)) return 0.0f;
        constexpr float FullTrailUntil = 0.08f;
        constexpr float TrailFallComplete = 0.42f;
        constexpr float ResidualTrail = 0.15f;
        const float t = smoothstep01(
            (std::abs(alpha) - FullTrailUntil) /
            (TrailFallComplete - FullTrailUntil));
        return 1.0f - (1.0f - ResidualTrail) * t;
    }

    // Fy * pneumatic trail. Normalize the empirically-known peak of the two
    // analytic curves so SteeringWeight keeps roughly the same normal-corner
    // authority as the previous single trail_shape() implementation.
    inline float pneumatic_sat_shape(float alpha)
    {
        if (!std::isfinite(alpha)) return 0.0f;
        constexpr float RawPeak = 0.838899081f;
        const float raw = lateral_force_shape(alpha) * pneumatic_trail_factor(alpha);
        return std::clamp(raw / RawPeak, 0.0f, 1.0f);
    }

    // Add a bounded mechanical/caster-trail component without turning it into
    // an artificial steering-centre spring. It is driven by the same front Fy
    // proxy and becomes relatively important only as pneumatic trail fades.
    inline float combined_sat_shape(float alpha, float mechanicalTrailMix)
    {
        const float pneumatic = pneumatic_sat_shape(alpha);
        const float fy = lateral_force_shape(alpha);
        const float mix = std::clamp(mechanicalTrailMix, 0.0f, 0.60f);
        const float mechanical = mix * fy * (1.0f - pneumatic);
        return std::clamp(pneumatic + mechanical, 0.0f, 1.0f);
    }

    // Kept as a compatibility alias for older host tests/tools. Production
    // Physics SAT uses the decomposed functions above explicitly.
    inline float trail_shape(float alpha)
    {
        return pneumatic_sat_shape(alpha);
    }

    // Symmetric C1 soft limiter. Preserve low/mid-range force exactly, then
    // bend only the final quarter toward the DirectInput cap. This keeps SAT
    // detail and weight intact while still preventing hard clipping at 100%.
    inline float soft_saturate(float value)
    {
        if (!std::isfinite(value)) return 0.0f;
        const float sign = value < 0.0f ? -1.0f : 1.0f;
        const float x = std::abs(value);
        constexpr float Knee = 0.75f;
        constexpr float Limit = 1.35f;
        if (x <= Knee) return value;
        if (x >= Limit) return sign;

        const float span = Limit - Knee;
        const float t = (x - Knee) / span;
        const float t2 = t * t;
        const float t3 = t2 * t;
        const float h00 = 2.0f * t3 - 3.0f * t2 + 1.0f;
        const float h10 = t3 - 2.0f * t2 + t;
        const float h01 = -2.0f * t3 + 3.0f * t2;
        const float y = h00 * Knee + h10 * span + h01;
        return sign * y;
    }

    inline float physics_return_relief(float alpha, float steerRate)
    {
        // Relieve only torque doing positive work on the moving wheel.
        // Steering centre is irrelevant to front-tyre SAT direction.
        const float t = -alpha * steerRate > 0.0f
            ? std::clamp(std::abs(steerRate) / 0.08f, 0.0f, 1.0f) : 0.0f;
        return 1.0f - 0.15f * t*t*(3.0f - 2.0f*t);
    }

    using ResponseLUT = std::array<float, 11>;

    inline ResponseLUT linear_response_lut()
    {
        ResponseLUT lut{};
        for (size_t i = 0; i < lut.size(); ++i)
            lut[i] = static_cast<float>(i) / 10.0f;
        return lut;
    }

    // Eleven output-command samples for desired torque 0%, 10%, ... 100%.
    // The curve must be monotonic, start at zero and finish at full scale.
    inline bool parse_response_lut(std::string_view spec, ResponseLUT& out)
    {
        std::stringstream stream{std::string(spec)};
        ResponseLUT parsed{};
        for (size_t i = 0; i < parsed.size(); ++i)
        {
            std::string token;
            if (!std::getline(stream, token, ','))
                return false;
            std::stringstream valueStream{token};
            float value = 0.0f;
            if (!(valueStream >> value) || !std::isfinite(value) ||
                value < 0.0f || value > 1.0f)
                return false;
            valueStream >> std::ws;
            if (!valueStream.eof())
                return false;
            if (i > 0 && value + 0.000001f < parsed[i - 1])
                return false;
            parsed[i] = value;
        }

        std::string extra;
        if (std::getline(stream, extra, ','))
        {
            if (extra.find_first_not_of(" \t\r\n") != std::string::npos)
                return false;
        }
        if (parsed.front() > 0.001f || parsed.back() < 0.999f)
            return false;
        out = parsed;
        return true;
    }

    inline std::string format_response_lut(const ResponseLUT& lut)
    {
        std::ostringstream stream;
        stream << std::fixed << std::setprecision(3);
        for (size_t i = 0; i < lut.size(); ++i)
        {
            if (i) stream << ',';
            stream << std::clamp(lut[i], 0.0f, 1.0f);
        }
        return stream.str();
    }

    inline float apply_response_lut(float value, const ResponseLUT& lut)
    {
        if (!std::isfinite(value)) return 0.0f;
        const float sign = value < 0.0f ? -1.0f : 1.0f;
        const float x = std::clamp(std::abs(value), 0.0f, 1.0f);
        const float scaled = x * 10.0f;
        const size_t index = std::min<size_t>(9, static_cast<size_t>(scaled));
        const float fraction = std::clamp(scaled - static_cast<float>(index), 0.0f, 1.0f);
        const float y = lut[index] + (lut[index + 1] - lut[index]) * fraction;
        return sign * std::clamp(y, 0.0f, 1.0f);
    }
}
