from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8", newline="\n")


def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: expected one match, got {count}: {old[:100]!r}")
    write(rel, text.replace(old, new, 1))


def replace_count(rel, old, new, expected):
    text = read(rel)
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{rel}: expected {expected} matches, got {count}: {old[:100]!r}")
    write(rel, text.replace(old, new))


# ---------------------------------------------------------------------------
# Shared production math: pneumatic + mechanical/caster trail decomposition,
# plus a validated per-wheel response LUT.
# ---------------------------------------------------------------------------
write("src/wheel_ffb_math.hpp", r'''#pragma once
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
            valueStream >> value;
            valueStream >> std::ws;
            if (!valueStream || !valueStream.eof() || !std::isfinite(value) ||
                value < 0.0f || value > 1.0f)
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
''')

write("src/wheel_ffb_runtime.hpp", r'''#pragma once
#include <cstdint>

struct WheelFFBHeadroomSnapshot
{
    std::uint64_t samples = 0;
    float currentDemand = 0.0f;
    float peakDemand = 0.0f;
    float p95Demand = 0.0f;
    float p99Demand = 0.0f;
    float softKneePercent = 0.0f;
    float hardClipPercent = 0.0f;
    float suggestedOverall = 0.0f;
};

void WheelFFB_RequestDirectionTest(int direction);
void WheelFFB_RequestSettingsTransition();
WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot();
void WheelFFB_ResetHeadroomStats();
''')

# ---------------------------------------------------------------------------
# Vehicle-state estimator: retain the bicycle-model proxy, but expose raw
# signals and make transient filtering faster with speed (relaxation-length
# inspired) instead of using a fixed time lag at every vehicle speed.
# ---------------------------------------------------------------------------
rel = "src/hooks_wheel_vehicle_dynamics.hpp"
old = """        bodySlip_ = 0.0f;\n        yawRate_ = 0.0f;\n        frontSlip_ = 0.0f;\n        vLong_ = 0.0f;\n"""
new = """        bodySlip_ = 0.0f;\n        yawRate_ = 0.0f;\n        frontSlip_ = 0.0f;\n        rawBodySlip_ = 0.0f;\n        rawYawRate_ = 0.0f;\n        rawFrontSlip_ = 0.0f;\n        bodySlipBlend_ = 0.18f;\n        yawRateBlend_ = 0.20f;\n        frontSlipBlend_ = 0.24f;\n        vLong_ = 0.0f;\n"""
replace_count(rel, old, new, 2)

replace_once(rel,
"""        const float rawBodySlip = std::clamp(\n            std::atan2(vLat_, std::max(std::abs(vLong_), 0.00001f)),\n            -0.70f, 0.70f);\n        bodySlip_ += (rawBodySlip - bodySlip_) * 0.18f;\n""",
"""        rawBodySlip_ = std::clamp(\n            std::atan2(vLat_, std::max(std::abs(vLong_), 0.00001f)),\n            -0.70f, 0.70f);\n\n        // Tyre transient response is fundamentally distance-based (relaxation\n        // length), so a fixed time-domain low-pass becomes increasingly late as\n        // speed rises. OutRun does not expose a physical metres/second scale,\n        // therefore use a conservative speed-adaptive blend while retaining\n        // smoothing at parking/launch speeds.\n        const float transientT0 = std::clamp(\n            (speedNorm - 0.08f) / 0.72f, 0.0f, 1.0f);\n        const float transientT =\n            transientT0 * transientT0 * (3.0f - 2.0f * transientT0);\n        bodySlipBlend_ = 0.18f + (0.34f - 0.18f) * transientT;\n        yawRateBlend_ = 0.20f + (0.38f - 0.20f) * transientT;\n        frontSlipBlend_ = 0.24f + (0.58f - 0.24f) * transientT;\n        bodySlip_ += (rawBodySlip_ - bodySlip_) * bodySlipBlend_;\n""")

replace_once(rel,
"""        const float rawYawRate = std::clamp(headingDelta * 60.0f, -3.5f, 3.5f);\n        yawRate_ += (rawYawRate - yawRate_) * 0.20f;\n""",
"""        rawYawRate_ = std::clamp(headingDelta * 60.0f, -3.5f, 3.5f);\n        yawRate_ += (rawYawRate_ - yawRate_) * yawRateBlend_;\n""")

replace_once(rel,
"""        const float rawFrontSlip = std::clamp(\n            roadWheelAngle - bodySlip_ - yawRate_ * yawLeadSeconds,\n            -0.70f, 0.70f);\n        frontSlip_ += (rawFrontSlip - frontSlip_) * 0.22f;\n""",
"""        rawFrontSlip_ = std::clamp(\n            roadWheelAngle - bodySlip_ - yawRate_ * yawLeadSeconds,\n            -0.70f, 0.70f);\n        frontSlip_ += (rawFrontSlip_ - frontSlip_) * frontSlipBlend_;\n""")

replace_once(rel,
"""    float bodySlip() const { return bodySlip_; }\n    float yawRate() const { return yawRate_; }\n    float frontSlip() const { return frontSlip_; }\n""",
"""    float bodySlip() const { return bodySlip_; }\n    float yawRate() const { return yawRate_; }\n    float frontSlip() const { return frontSlip_; }\n    float rawBodySlip() const { return rawBodySlip_; }\n    float rawYawRate() const { return rawYawRate_; }\n    float rawFrontSlip() const { return rawFrontSlip_; }\n    float bodySlipBlend() const { return bodySlipBlend_; }\n    float yawRateBlend() const { return yawRateBlend_; }\n    float frontSlipBlend() const { return frontSlipBlend_; }\n""")

replace_once(rel,
"""        bodySlip_ *= 0.55f;\n        yawRate_ *= 0.55f;\n        frontSlip_ *= 0.55f;\n        activationBlend_ *= 0.85f;\n""",
"""        bodySlip_ *= 0.55f;\n        yawRate_ *= 0.55f;\n        frontSlip_ *= 0.55f;\n        rawBodySlip_ *= 0.55f;\n        rawYawRate_ *= 0.55f;\n        rawFrontSlip_ *= 0.55f;\n        activationBlend_ *= 0.85f;\n""")

replace_once(rel,
"""    float bodySlip_ = 0.0f;\n    float yawRate_ = 0.0f;\n    float frontSlip_ = 0.0f;\n    float vLong_ = 0.0f;\n""",
"""    float bodySlip_ = 0.0f;\n    float yawRate_ = 0.0f;\n    float frontSlip_ = 0.0f;\n    float rawBodySlip_ = 0.0f;\n    float rawYawRate_ = 0.0f;\n    float rawFrontSlip_ = 0.0f;\n    float bodySlipBlend_ = 0.18f;\n    float yawRateBlend_ = 0.20f;\n    float frontSlipBlend_ = 0.24f;\n    float vLong_ = 0.0f;\n""")

# ---------------------------------------------------------------------------
# Main FFB engine: decomposed SAT, headroom analysis, wheel-specific response
# correction. Keep Natural SAT, low-speed spring, damping and DD safety intact.
# ---------------------------------------------------------------------------
rel = "src/hooks_wheel_ffb.cpp"
replace_once(rel, "#include <algorithm>\n#include <cmath>\n", "#include <algorithm>\n#include <array>\n#include <cmath>\n")
replace_once(rel, "#include \"wheel_ffb_math.hpp\"\n#include \"overlay/overlay.hpp\"\n", "#include \"wheel_ffb_math.hpp\"\n#include \"wheel_ffb_runtime.hpp\"\n#include \"overlay/overlay.hpp\"\n")

replace_once(rel,
"""    Setting<std::string> WheelFFBDeviceGuid{\n        \"WheelFFB\", \"DeviceGuid\", \"\",\n        \"Exact DirectInput instance GUID selected by F11 Wheel Setup; a saved GUID never falls back to a different device automatically.\"\n    };\n\n""",
"""    Setting<std::string> WheelFFBDeviceGuid{\n        \"WheelFFB\", \"DeviceGuid\", \"\",\n        \"Exact DirectInput instance GUID selected by F11 Wheel Setup; a saved GUID never falls back to a different device automatically.\"\n    };\n\n    Setting<bool> WheelFFBResponseCorrection{\n        \"WheelFFB\", \"ResponseCorrection\", false,\n        \"Optional wheel-specific ConstantForce response correction. Store this with the wheel profile, not a force-feel profile.\"\n    };\n\n    Setting<std::string> WheelFFBResponseLUT{\n        \"WheelFFB\", \"ResponseLUT\", \"0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0\",\n        \"Eleven monotonic command samples for desired torque 0..100% in 10% steps. Linear by default.\"\n    };\n\n    Setting<float> WheelFFBMaxTorqueNm{\n        \"WheelFFB\", \"MaxTorqueNm\", 0.0f,\n        \"Optional physical wheel peak torque for diagnostics only. 0 means unknown.\",\n        Range<float>{ 0.0f, 30.0f }\n    };\n\n""")

replace_once(rel,
"""    Setting<float> WheelFFBSteeringWeight{\n        \"WheelFFB\", \"SteeringWeight\", 1.45f,\n        \"Self-aligning torque strength. Physics SAT direction/trail comes from front slip; field_264/268 only scale lateral load.\", Range<float>{ 0.0f, 2.0f }\n    };\n\n""",
"""    Setting<float> WheelFFBSteeringWeight{\n        \"WheelFFB\", \"SteeringWeight\", 1.45f,\n        \"Self-aligning torque strength. Physics SAT direction/trail comes from front slip; field_264/268 only scale lateral load.\", Range<float>{ 0.0f, 2.0f }\n    };\n\n    Setting<float> WheelFFBMechanicalTrail{\n        \"WheelFFB\", \"MechanicalTrail\", 0.25f,\n        \"Physics SAT mechanical/caster-trail contribution after pneumatic trail begins to fade. Not a centre spring.\",\n        Range<float>{ 0.0f, 0.60f }\n    };\n\n""")

old_sat = """            // Physics SAT force shaping lives here, separate from the vehicle\n            // estimator. Front slip determines both direction and the pneumatic-\n            // trail-like rise/fall. Body slide only applies a mild rear-slide\n            // relief so counter-steer SAT is not double-unloaded.\n            const float frontSlip = vehicleDynamics_.frontSlip();\n            float physicsSatTorque = 0.0f;\n            const float trailShape = WheelFFBMath::trail_shape(frontSlip);\n            const float physicsLoad = 0.62f + 0.48f * lateralLoadSmooth;\n            const float rearSlideRelief = 1.0f - 0.15f * gripLoss * bodySlide;\n            if (vehicleDynamics_.calibrated() && vehicleDynamics_.sampleValid())\n            {\n                const float physicsReturnRelief =\n                    WheelFFBMath::physics_return_relief(frontSlip, steerRate);\n\n                physicsSatTorque =\n                    (frontSlip > 0.0f ? -1.0f : 1.0f) *\n                    trailShape * satSpeed * physicsLoad * rearSlideRelief *\n                    physicsReturnRelief * satStrength;\n                if (!std::isfinite(physicsSatTorque))\n                    physicsSatTorque = 0.0f;\n            }\n"""
new_sat = """            // Physics SAT separates tyre pneumatic trail from a bounded\n            // mechanical/caster-trail contribution. Both are driven by the\n            // front lateral-force proxy, so the mechanical term cannot become\n            // an artificial speed-dependent centre spring. Pneumatic SAT drops\n            // first near understeer while mechanical trail keeps useful rack\n            // torque alive instead of making the wheel suddenly go dead.\n            const float frontSlip = vehicleDynamics_.frontSlip();\n            float physicsSatTorque = 0.0f;\n            const float lateralForceShape = WheelFFBMath::lateral_force_shape(frontSlip);\n            const float pneumaticTrail = WheelFFBMath::pneumatic_trail_factor(frontSlip);\n            const float pneumaticSatShape = WheelFFBMath::pneumatic_sat_shape(frontSlip);\n            const float configuredMechanicalTrail =\n                static_cast<float>(Settings::WheelFFBMechanicalTrail);\n            const float mechanicalTrailMix = std::isfinite(configuredMechanicalTrail)\n                ? std::clamp(configuredMechanicalTrail, 0.0f, 0.60f)\n                : 0.25f;\n            const float mechanicalContribution =\n                mechanicalTrailMix * lateralForceShape * (1.0f - pneumaticSatShape);\n            const float physicsShape =\n                WheelFFBMath::combined_sat_shape(frontSlip, mechanicalTrailMix);\n            const float trailShape = pneumaticSatShape; // legacy telemetry field name\n            const float physicsLoad = 0.62f + 0.48f * lateralLoadSmooth;\n            const float rearSlideRelief = 1.0f - 0.15f * gripLoss * bodySlide;\n            if (vehicleDynamics_.calibrated() && vehicleDynamics_.sampleValid())\n            {\n                const float physicsReturnRelief =\n                    WheelFFBMath::physics_return_relief(frontSlip, steerRate);\n\n                physicsSatTorque =\n                    (frontSlip > 0.0f ? -1.0f : 1.0f) *\n                    physicsShape * satSpeed * physicsLoad * rearSlideRelief *\n                    physicsReturnRelief * satStrength;\n                if (!std::isfinite(physicsSatTorque))\n                    physicsSatTorque = 0.0f;\n            }\n"""
replace_once(rel, old_sat, new_sat)

replace_once(rel,
"""            float structural = 0.0f;\n            if (crashImpulseTimer_ <= CrashCooldownFrames)\n                structural = (softwareSpring + selfAligningTorque) * loadMod + damper;\n\n            float events = update_event_force();\n\n            // Sustained steering and short events have different timing needs.\n""",
"""            float structural = 0.0f;\n            if (crashImpulseTimer_ <= CrashCooldownFrames)\n                structural = (softwareSpring + selfAligningTorque) * loadMod + damper;\n\n            // Headroom analysis uses sustained structural steering only. Do not\n            // let a wall hit, gear thunk, startup ramp or nearly-stopped frame\n            // teach the gain recommendation the wrong lesson.\n            const bool headroomEligible =\n                crashImpulseTimer_ <= 0 && gearShiftTimer_ <= 0 &&\n                warmupScale >= 0.999f && recreateScale >= 0.999f &&\n                speedNorm > 0.08f;\n\n            float events = update_event_force();\n\n            // Sustained steering and short events have different timing needs.\n""")

replace_once(rel,
"""            float total = structural * outputStrength * forceDirection * outputRamp;\n            float eventOutput = events * outputStrength * forceDirection * outputRamp;\n            if (!std::isfinite(total))\n                total = 0.0f;\n            if (!std::isfinite(eventOutput))\n                eventOutput = 0.0f;\n\n            // Preserve ordinary SAT linearly; bend only near the force cap.\n""",
"""            float total = structural * outputStrength * forceDirection * outputRamp;\n            float eventOutput = events * outputStrength * forceDirection * outputRamp;\n            if (!std::isfinite(total))\n                total = 0.0f;\n            if (!std::isfinite(eventOutput))\n                eventOutput = 0.0f;\n            record_headroom(std::abs(total), headroomEligible);\n\n            // Preserve ordinary SAT linearly; bend only near the force cap.\n""")

replace_once(rel,
"""            const LONG level = baseSteeringLevel + vibrationLevel;\n\n            if (std::abs(level - prevConstantLevel_) > 15 || eventLevel != 0 ||\n                (level != 0 && GetTickCount() - lastConstantWriteTick_ >= FFB_EFFECT_REFRESH_MS))\n                set_constant_force(level);\n""",
"""            const LONG levelBeforeResponse = baseSteeringLevel + vibrationLevel;\n            const LONG level = apply_response_correction(levelBeforeResponse);\n\n            if (std::abs(level - prevConstantLevel_) > 15 || eventLevel != 0 ||\n                (level != 0 && GetTickCount() - lastConstantWriteTick_ >= FFB_EFFECT_REFRESH_MS))\n                set_constant_force(level);\n""")

replace_once(rel,
"""                // Raw horizontal bases allow row/column x X/Z candidates to be\n                // compared offline without changing the active steering model.\n""",
"""                spdlog::info(\n                    \"WheelFFB SATMODEL t={} rawBodySlip={} bodySlip={} bodyBlend={} rawYawRate={} yawRate={} yawBlend={} rawFrontSlip={} frontSlip={} frontBlend={} fyShape={} pneumaticTrail={} pneumaticShape={} mechanicalMix={} mechanicalContribution={} combinedShape={} diPreResponse={} diCorrected={} responseCorrection={}\",\n                    telemetryNow,\n                    vehicleDynamics_.rawBodySlip(), vehicleDynamics_.bodySlip(), vehicleDynamics_.bodySlipBlend(),\n                    vehicleDynamics_.rawYawRate(), vehicleDynamics_.yawRate(), vehicleDynamics_.yawRateBlend(),\n                    vehicleDynamics_.rawFrontSlip(), vehicleDynamics_.frontSlip(), vehicleDynamics_.frontSlipBlend(),\n                    lateralForceShape, pneumaticTrail, pneumaticSatShape, mechanicalTrailMix,\n                    mechanicalContribution, physicsShape, levelBeforeResponse, level,\n                    bool(Settings::WheelFFBResponseCorrection));\n                // Raw horizontal bases allow row/column x X/Z candidates to be\n                // compared offline without changing the active steering model.\n""")

replace_once(rel,
"""        bool output_owner_active() const\n        {\n            return Settings::WheelFFBEnable && initialized_ && device_ &&\n                deviceAcquired_ && !deviceReinitPending_ && !panicStopped_;\n        }\n\n""",
"""        bool output_owner_active() const\n        {\n            return Settings::WheelFFBEnable && initialized_ && device_ &&\n                deviceAcquired_ && !deviceReinitPending_ && !panicStopped_;\n        }\n\n        WheelFFBHeadroomSnapshot headroom_snapshot() const\n        {\n            WheelFFBHeadroomSnapshot result{};\n            result.samples = headroomSamples_;\n            result.currentDemand = headroomCurrentDemand_;\n            result.peakDemand = headroomPeakDemand_;\n\n            const auto percentile = [&](double q)\n            {\n                if (headroomSamples_ == 0)\n                    return 0.0f;\n                const std::uint64_t target = std::max<std::uint64_t>(\n                    1, static_cast<std::uint64_t>(std::ceil(headroomSamples_ * q)));\n                std::uint64_t cumulative = 0;\n                for (size_t i = 0; i < headroomHistogram_.size(); ++i)\n                {\n                    cumulative += headroomHistogram_[i];\n                    if (cumulative >= target)\n                    {\n                        return static_cast<float>(i) *\n                            (HeadroomHistogramMax / static_cast<float>(HeadroomHistogramBins - 1));\n                    }\n                }\n                return HeadroomHistogramMax;\n            };\n\n            result.p95Demand = percentile(0.95);\n            result.p99Demand = percentile(0.99);\n            if (headroomSamples_ > 0)\n            {\n                const float inv = 100.0f / static_cast<float>(headroomSamples_);\n                result.softKneePercent = static_cast<float>(headroomSoftKneeSamples_) * inv;\n                result.hardClipPercent = static_cast<float>(headroomHardClipSamples_) * inv;\n            }\n\n            const float currentOverall = std::clamp(\n                static_cast<float>(Settings::WheelFFBGlobalStrength), 0.0f, 1.5f);\n            result.suggestedOverall = currentOverall;\n            if (headroomSamples_ >= 600 && result.p99Demand > 0.05f)\n            {\n                result.suggestedOverall = std::clamp(\n                    currentOverall * (0.90f / result.p99Demand),\n                    0.05f, 1.5f);\n            }\n            return result;\n        }\n\n        void reset_headroom_stats()\n        {\n            headroomHistogram_.fill(0);\n            headroomSamples_ = 0;\n            headroomSoftKneeSamples_ = 0;\n            headroomHardClipSamples_ = 0;\n            headroomCurrentDemand_ = 0.0f;\n            headroomPeakDemand_ = 0.0f;\n        }\n\n""")

replace_once(rel,
"""        void settings_transition()\n        {\n            manualTestFrames_ = 0;\n            if (initialized_ && device_ && deviceAcquired_ && !panicStopped_)\n                zero_all_forces();\n            reset_signal_state();\n""",
"""        void settings_transition()\n        {\n            manualTestFrames_ = 0;\n            if (initialized_ && device_ && deviceAcquired_ && !panicStopped_)\n                zero_all_forces();\n            reset_signal_state();\n            reset_headroom_stats();\n""")

replace_once(rel,
"""        static constexpr int CrashTimerFrames = 90;\n        static constexpr int CrashCooldownFrames = 80;\n\n""",
"""        static constexpr int CrashTimerFrames = 90;\n        static constexpr int CrashCooldownFrames = 80;\n        static constexpr size_t HeadroomHistogramBins = 201;\n        static constexpr float HeadroomHistogramMax = 2.0f;\n\n""")

replace_once(rel,
"""        void set_constant_force(LONG requestedLevel)\n        {\n""",
"""        void record_headroom(float demand, bool eligible)\n        {\n            if (!std::isfinite(demand))\n                return;\n            demand = std::max(0.0f, demand);\n            headroomCurrentDemand_ = demand;\n            if (!eligible)\n                return;\n\n            headroomPeakDemand_ = std::max(headroomPeakDemand_, demand);\n            ++headroomSamples_;\n            if (demand > 0.75f)\n                ++headroomSoftKneeSamples_;\n            if (demand >= 1.35f)\n                ++headroomHardClipSamples_;\n\n            const float normalized = std::clamp(demand / HeadroomHistogramMax, 0.0f, 1.0f);\n            const size_t bin = std::min<size_t>(\n                HeadroomHistogramBins - 1,\n                static_cast<size_t>(std::lround(\n                    normalized * static_cast<float>(HeadroomHistogramBins - 1))));\n            ++headroomHistogram_[bin];\n        }\n\n        LONG apply_response_correction(LONG requestedLevel)\n        {\n            if (!Settings::WheelFFBResponseCorrection || requestedLevel == 0)\n                return requestedLevel;\n\n            const std::string spec = Settings::WheelFFBResponseLUT.get();\n            if (spec != responseLutSpec_)\n            {\n                responseLutSpec_ = spec;\n                WheelFFBMath::ResponseLUT parsed{};\n                responseLutValid_ = WheelFFBMath::parse_response_lut(spec, parsed);\n                if (responseLutValid_)\n                {\n                    responseLut_ = parsed;\n                    spdlog::info(\"WheelFFB: loaded valid wheel response LUT\");\n                }\n                else\n                {\n                    responseLut_ = WheelFFBMath::linear_response_lut();\n                    spdlog::warn(\n                        \"WheelFFB: invalid ResponseLUT; leaving ConstantForce linear until corrected\");\n                }\n            }\n\n            if (!responseLutValid_)\n                return requestedLevel;\n\n            const float normalized =\n                static_cast<float>(requestedLevel) / static_cast<float>(DI_FFNOMINALMAX);\n            const float corrected = WheelFFBMath::apply_response_lut(normalized, responseLut_);\n            return std::clamp(\n                static_cast<LONG>(std::lround(corrected * static_cast<float>(DI_FFNOMINALMAX))),\n                -static_cast<LONG>(DI_FFNOMINALMAX),\n                static_cast<LONG>(DI_FFNOMINALMAX));\n        }\n\n        void set_constant_force(LONG requestedLevel)\n        {\n""")

replace_once(rel,
"""            initialized_ = true;\n            deviceReinitPending_ = false;\n            deviceFailureSince_ = 0;\n            deviceReinitAfter_ = 0;\n            retryAfter_ = 0;\n            reset_signal_state();\n\n""",
"""            initialized_ = true;\n            deviceReinitPending_ = false;\n            deviceFailureSince_ = 0;\n            deviceReinitAfter_ = 0;\n            retryAfter_ = 0;\n            reset_signal_state();\n            reset_headroom_stats();\n\n""")

replace_once(rel,
"""        float smoothedSteerRate_ = 0.0f;\n        bool steerSampleValid_ = false;\n        WheelVehicleDynamics vehicleDynamics_{};\n        float crashImpulseForce_ = 0.0f;\n""",
"""        float smoothedSteerRate_ = 0.0f;\n        bool steerSampleValid_ = false;\n        WheelVehicleDynamics vehicleDynamics_{};\n\n        std::array<std::uint64_t, HeadroomHistogramBins> headroomHistogram_{};\n        std::uint64_t headroomSamples_ = 0;\n        std::uint64_t headroomSoftKneeSamples_ = 0;\n        std::uint64_t headroomHardClipSamples_ = 0;\n        float headroomCurrentDemand_ = 0.0f;\n        float headroomPeakDemand_ = 0.0f;\n\n        WheelFFBMath::ResponseLUT responseLut_ = WheelFFBMath::linear_response_lut();\n        std::string responseLutSpec_;\n        bool responseLutValid_ = true;\n\n        float crashImpulseForce_ = 0.0f;\n""")

replace_once(rel,
"""void WheelFFB_RequestSettingsTransition()\n{\n    gWheelFFB.settings_transition();\n}\n""",
"""void WheelFFB_RequestSettingsTransition()\n{\n    gWheelFFB.settings_transition();\n}\n\nWheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot()\n{\n    return gWheelFFB.headroom_snapshot();\n}\n\nvoid WheelFFB_ResetHeadroomStats()\n{\n    gWheelFFB.reset_headroom_stats();\n}\n""")

# ---------------------------------------------------------------------------
# Profile ownership: response correction and physical max torque are wheel
# hardware properties, so they follow the Input/wheel profile and are excluded
# from named FFB feel profiles. Mechanical trail remains a feel setting.
# ---------------------------------------------------------------------------
rel = "src/wheel_profile_store.hpp"
replace_once(rel,
"""    extern Setting<std::string> WheelFFBDeviceName;\n    extern Setting<std::string> WheelFFBDeviceGuid;\n""",
"""    extern Setting<std::string> WheelFFBDeviceName;\n    extern Setting<std::string> WheelFFBDeviceGuid;\n    extern Setting<bool> WheelFFBResponseCorrection;\n    extern Setting<std::string> WheelFFBResponseLUT;\n    extern Setting<float> WheelFFBMaxTorqueNm;\n""")

replace_once(rel,
"""        std::string ffbDeviceName;\n        std::string ffbDeviceGuid;\n""",
"""        std::string ffbDeviceName;\n        std::string ffbDeviceGuid;\n        std::string ffbResponseCorrection;\n        std::string ffbResponseLut;\n        std::string ffbMaxTorqueNm;\n""")

replace_once(rel,
"""            Settings::WheelFFBDeviceName.to_string(),\n            Settings::WheelFFBDeviceGuid.to_string(),\n""",
"""            Settings::WheelFFBDeviceName.to_string(),\n            Settings::WheelFFBDeviceGuid.to_string(),\n            Settings::WheelFFBResponseCorrection.to_string(),\n            Settings::WheelFFBResponseLUT.to_string(),\n            Settings::WheelFFBMaxTorqueNm.to_string(),\n""")

replace_once(rel,
"""        Settings::WheelFFBDeviceName.set_from_string(snapshot.ffbDeviceName);\n        Settings::WheelFFBDeviceGuid.set_from_string(snapshot.ffbDeviceGuid);\n""",
"""        Settings::WheelFFBDeviceName.set_from_string(snapshot.ffbDeviceName);\n        Settings::WheelFFBDeviceGuid.set_from_string(snapshot.ffbDeviceGuid);\n        Settings::WheelFFBResponseCorrection.set_from_string(snapshot.ffbResponseCorrection);\n        Settings::WheelFFBResponseLUT.set_from_string(snapshot.ffbResponseLut);\n        Settings::WheelFFBMaxTorqueNm.set_from_string(snapshot.ffbMaxTorqueNm);\n""")

replace_once(rel,
"""        file << \"FFBDeviceName = \" << Settings::WheelFFBDeviceName.to_string() << \"\\n\";\n        file << \"FFBDeviceGuid = \" << Settings::WheelFFBDeviceGuid.to_string() << \"\\n\";\n""",
"""        file << \"FFBDeviceName = \" << Settings::WheelFFBDeviceName.to_string() << \"\\n\";\n        file << \"FFBDeviceGuid = \" << Settings::WheelFFBDeviceGuid.to_string() << \"\\n\";\n        file << \"FFBResponseCorrection = \" << Settings::WheelFFBResponseCorrection.to_string() << \"\\n\";\n        file << \"FFBResponseLUT = \" << Settings::WheelFFBResponseLUT.to_string() << \"\\n\";\n        file << \"FFBMaxTorqueNm = \" << Settings::WheelFFBMaxTorqueNm.to_string() << \"\\n\";\n""")

replace_once(rel,
"""            !apply(\"BypassGameSensitivity\", Settings::BypassGameSensitivity) ||\n            !apply(\"FFBDeviceName\", Settings::WheelFFBDeviceName) ||\n            !apply(\"FFBDeviceGuid\", Settings::WheelFFBDeviceGuid))\n""",
"""            !apply(\"BypassGameSensitivity\", Settings::BypassGameSensitivity) ||\n            !apply(\"FFBDeviceName\", Settings::WheelFFBDeviceName) ||\n            !apply(\"FFBDeviceGuid\", Settings::WheelFFBDeviceGuid) ||\n            !apply(\"FFBResponseCorrection\", Settings::WheelFFBResponseCorrection) ||\n            !apply(\"FFBResponseLUT\", Settings::WheelFFBResponseLUT) ||\n            !apply(\"FFBMaxTorqueNm\", Settings::WheelFFBMaxTorqueNm))\n""")

replace_once(rel,
"""        return key != \"DeviceName\" && key != \"DeviceGuid\" &&\n            key != \"Telemetry\" && key != \"DebugLog\";\n""",
"""        return key != \"DeviceName\" && key != \"DeviceGuid\" &&\n            key != \"Telemetry\" && key != \"DebugLog\" &&\n            key != \"ResponseCorrection\" && key != \"ResponseLUT\" &&\n            key != \"MaxTorqueNm\";\n""")

# ---------------------------------------------------------------------------
# F11 UI: group physical/feel/effects, expose mechanical trail, hardware LUT,
# and provide non-invasive clipping/headroom diagnostics.
# ---------------------------------------------------------------------------
rel = "src/overlay/wheel_setup_ui.cpp"
replace_once(rel,
"""#include \"overlay.hpp\"\n#include \"wheel_profile_store.hpp\"\n\nvoid WheelFFB_RequestDirectionTest(int direction);\nvoid WheelFFB_RequestSettingsTransition();\n""",
"""#include \"overlay.hpp\"\n#include \"wheel_ffb_math.hpp\"\n#include \"wheel_ffb_runtime.hpp\"\n#include \"wheel_profile_store.hpp\"\n""")

replace_once(rel,
"""    extern Setting<float> WheelFFBSteeringWeight;\n    extern Setting<bool> WheelFFBPhysicsSat;\n""",
"""    extern Setting<float> WheelFFBSteeringWeight;\n    extern Setting<float> WheelFFBMechanicalTrail;\n    extern Setting<bool> WheelFFBPhysicsSat;\n""")
replace_once(rel,
"""    extern Setting<bool> WheelFFBTelemetry;\n\n""",
"""    extern Setting<bool> WheelFFBTelemetry;\n    extern Setting<bool> WheelFFBResponseCorrection;\n    extern Setting<std::string> WheelFFBResponseLUT;\n    extern Setting<float> WheelFFBMaxTorqueNm;\n\n""")

replace_once(rel,
"""            ImGui::TextWrapped(\"Save several force-feel setups and switch between them. Profiles store force behavior only; the selected FFB Output wheel and diagnostic logging stay global.\");\n""",
"""            ImGui::TextWrapped(\"Save several force-feel setups and switch between them. Profiles store force behavior only; the selected FFB Output wheel, hardware response correction and diagnostic logging stay with the wheel/global setup.\");\n""")

replace_once(rel,
"""            const auto track_ffb_change = [this](bool changed)\n            {\n                if (changed)\n                    ffbDirty_ = true;\n                return changed;\n            };\n""",
"""            const auto track_ffb_change = [this](bool changed)\n            {\n                if (changed)\n                {\n                    ffbDirty_ = true;\n                    WheelFFB_ResetHeadroomStats();\n                }\n                return changed;\n            };\n""")

old_controls = """            ImGui::SeparatorText(\"Simulation FFB\");\n            track_ffb_change(ImGui::Checkbox(\"Enable Force Feedback\", Settings::WheelFFBEnable.ptr()));\n            ImGui::TextDisabled(\"gameplay FFB follows the exact selected DirectInput GUID.\");\n            ImGui::TextWrapped(\n                \"Single-owner wheel FFB: DirectInput COM only. field_264/268 are lateral load only; body slip releases damping, while front slip drives Physics SAT and tire scrub. Centering Spring remains a low-speed stabilizer.\");\n            ImGui::TextDisabled(\"Settings > WheelFFB is hidden; changes on this page apply live. Gamepad rumble is suppressed only while DirectInput FFB owns an output device.\");\n\n            track_ffb_change(ImGui::SliderFloat(\"Overall Strength\", Settings::WheelFFBGlobalStrength.ptr(), 0.0f, 1.5f, \"%.2f\"));\n            if (Settings::WheelFFBGlobalStrength.get() > 1.0f)\n                ImGui::TextColored(ImVec4(1.0f, 0.65f, 0.25f, 1.0f),\n                    \"Above 100% trades force-detail contrast for extra weight.\");\n            track_ffb_change(ImGui::SliderFloat(\"Centering Spring (low speed)\", Settings::WheelFFBSpringStrength.ptr(), 0.0f, 1.0f, \"%.2f\"));\n            track_ffb_change(ImGui::SliderFloat(\"Dynamic Damping\", Settings::WheelFFBDamperStrength.ptr(), 0.0f, 1.0f, \"%.2f\"));\n            track_ffb_change(ImGui::SliderFloat(\"Self-aligning Torque (SAT)\", Settings::WheelFFBSteeringWeight.ptr(), 0.0f, 2.00f, \"%.2f\"));\n            track_ffb_change(ImGui::Checkbox(\"Physics SAT (body slip + yaw)\", Settings::WheelFFBPhysicsSat.ptr()));\n            if (ImGui::IsItemHovered())\n                ImGui::SetTooltip(\"Uses post-physics OutRun car motion/body heading to estimate front slip. Disable for the Natural SAT comparison.\");\n            track_ffb_change(ImGui::SliderFloat(\"Grip-loss Response\", Settings::WheelFFBGripLoss.ptr(), 0.0f, 1.0f, \"%.2f\"));\n            track_ffb_change(ImGui::SliderFloat(\"Road Detail\", Settings::WheelFFBRoadTexture.ptr(), 0.0f, 0.50f, \"%.2f\"));\n            track_ffb_change(ImGui::SliderFloat(\"Tire Slip\", Settings::WheelFFBTireSlip.ptr(), 0.0f, 0.50f, \"%.2f\"));\n            track_ffb_change(ImGui::SliderFloat(\"Collision\", Settings::WheelFFBWallImpact.ptr(), 0.0f, 1.0f, \"%.2f\"));\n            track_ffb_change(ImGui::Checkbox(\"Hardware GUID_Spring\", Settings::WheelFFBUseHardwareSpring.ptr()));\n            ImGui::SameLine();\n            track_ffb_change(ImGui::Checkbox(\"Hardware GUID_Damper\", Settings::WheelFFBUseHardwareDamper.ptr()));\n            track_ffb_change(ImGui::Checkbox(\"Hardware road/slip sine effects\", Settings::WheelFFBUsePeriodicEffects.ptr()));\n"""
new_controls = """            ImGui::SeparatorText(\"Simulation FFB\");\n            track_ffb_change(ImGui::Checkbox(\"Enable Force Feedback\", Settings::WheelFFBEnable.ptr()));\n            ImGui::TextDisabled(\"gameplay FFB follows the exact selected DirectInput GUID.\");\n            ImGui::TextWrapped(\n                \"Single-owner wheel FFB: DirectInput COM only. field_264/268 are lateral load only; front slip drives a pneumatic + mechanical/caster SAT model, while body/front slip release damping. Centering Spring remains a low-speed stabilizer.\");\n            ImGui::TextDisabled(\"Settings > WheelFFB is hidden; changes on this page apply live. Gamepad rumble is suppressed only while DirectInput FFB owns an output device.\");\n\n            ImGui::SeparatorText(\"Physics / Structural\");\n            track_ffb_change(ImGui::SliderFloat(\"Overall Strength\", Settings::WheelFFBGlobalStrength.ptr(), 0.0f, 1.5f, \"%.2f\"));\n            if (Settings::WheelFFBGlobalStrength.get() > 1.0f)\n                ImGui::TextColored(ImVec4(1.0f, 0.65f, 0.25f, 1.0f),\n                    \"Above 100% trades force-detail contrast for extra weight.\");\n            track_ffb_change(ImGui::SliderFloat(\"Self-aligning Torque (SAT)\", Settings::WheelFFBSteeringWeight.ptr(), 0.0f, 2.00f, \"%.2f\"));\n            track_ffb_change(ImGui::Checkbox(\"Physics SAT (body slip + yaw)\", Settings::WheelFFBPhysicsSat.ptr()));\n            if (ImGui::IsItemHovered())\n                ImGui::SetTooltip(\"Uses post-physics OutRun car motion/body heading to estimate front slip. Disable for the Natural SAT comparison.\");\n            if (Settings::WheelFFBPhysicsSat)\n            {\n                track_ffb_change(ImGui::SliderFloat(\"Mechanical / Caster Trail\", Settings::WheelFFBMechanicalTrail.ptr(), 0.0f, 0.60f, \"%.2f\"));\n                if (ImGui::IsItemHovered())\n                    ImGui::SetTooltip(\"Adds bounded front-lateral-force restoring torque as pneumatic trail fades. This is not a centre spring; 0 disables the mechanical/caster contribution.\");\n            }\n            track_ffb_change(ImGui::SliderFloat(\"Grip-loss Response\", Settings::WheelFFBGripLoss.ptr(), 0.0f, 1.0f, \"%.2f\"));\n\n            ImGui::SeparatorText(\"Steering Feel\");\n            track_ffb_change(ImGui::SliderFloat(\"Centering Spring (low speed)\", Settings::WheelFFBSpringStrength.ptr(), 0.0f, 1.0f, \"%.2f\"));\n            track_ffb_change(ImGui::SliderFloat(\"Dynamic Damping\", Settings::WheelFFBDamperStrength.ptr(), 0.0f, 1.0f, \"%.2f\"));\n            track_ffb_change(ImGui::Checkbox(\"Hardware GUID_Spring\", Settings::WheelFFBUseHardwareSpring.ptr()));\n            ImGui::SameLine();\n            track_ffb_change(ImGui::Checkbox(\"Hardware GUID_Damper\", Settings::WheelFFBUseHardwareDamper.ptr()));\n\n            ImGui::SeparatorText(\"Effects\");\n            track_ffb_change(ImGui::SliderFloat(\"Road Detail\", Settings::WheelFFBRoadTexture.ptr(), 0.0f, 0.50f, \"%.2f\"));\n            track_ffb_change(ImGui::SliderFloat(\"Tire Slip\", Settings::WheelFFBTireSlip.ptr(), 0.0f, 0.50f, \"%.2f\"));\n            track_ffb_change(ImGui::SliderFloat(\"Collision\", Settings::WheelFFBWallImpact.ptr(), 0.0f, 1.0f, \"%.2f\"));\n            track_ffb_change(ImGui::Checkbox(\"Hardware road/slip sine effects\", Settings::WheelFFBUsePeriodicEffects.ptr()));\n"""
replace_once(rel, old_controls, new_controls)

replace_once(rel,
"""                track_ffb_change(ImGui::SliderFloat(\"Force Slew Rate\", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, \"%.3f\"));\n                if (ImGui::IsItemHovered())\n                    ImGui::SetTooltip(\"Maximum structural-force change per 60 Hz tick. Lower is smoother/slower; higher responds faster.\");\n                ImGui::TextDisabled(\"Advanced values apply live like the main controls; use Save Force Feedback to persist them.\");\n""",
"""                track_ffb_change(ImGui::SliderFloat(\"Force Slew Rate\", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, \"%.3f\"));\n                if (ImGui::IsItemHovered())\n                    ImGui::SetTooltip(\"Maximum structural-force change per 60 Hz tick. Lower is smoother/slower; higher responds faster.\");\n\n                ImGui::SeparatorText(\"Wheel hardware calibration\");\n                track_ffb_change(ImGui::Checkbox(\"Enable wheel response correction\", Settings::WheelFFBResponseCorrection.ptr()));\n                track_ffb_change(ImGui::SliderFloat(\"Wheel peak torque (Nm, 0=unknown)\", Settings::WheelFFBMaxTorqueNm.ptr(), 0.0f, 30.0f, \"%.1f\"));\n\n                WheelFFBMath::ResponseLUT responseLut{};\n                const bool responseLutValid = WheelFFBMath::parse_response_lut(\n                    Settings::WheelFFBResponseLUT.get(), responseLut);\n                if (!responseLutValid)\n                {\n                    ImGui::TextColored(ImVec4(1.0f, 0.4f, 0.3f, 1.0f),\n                        \"Response LUT is invalid; output remains linear.\");\n                    if (ImGui::Button(\"Reset response LUT to linear\"))\n                    {\n                        Settings::WheelFFBResponseLUT = WheelFFBMath::format_response_lut(\n                            WheelFFBMath::linear_response_lut());\n                        track_ffb_change(true);\n                    }\n                }\n                else if (Settings::WheelFFBResponseCorrection)\n                {\n                    ImGui::TextDisabled(\"Desired torque -> DirectInput command. Endpoints stay fixed at 0%% / 100%%.\");\n                    for (size_t point = 1; point + 1 < responseLut.size(); ++point)\n                    {\n                        float value = responseLut[point];\n                        char label[64]{};\n                        std::snprintf(label, sizeof(label), \"%u%% desired torque##ResponseLut%u\",\n                            static_cast<unsigned>(point * 10), static_cast<unsigned>(point));\n                        if (ImGui::SliderFloat(label, &value, responseLut[point - 1], responseLut[point + 1], \"%.3f\"))\n                        {\n                            responseLut[point] = value;\n                            Settings::WheelFFBResponseLUT = WheelFFBMath::format_response_lut(responseLut);\n                            track_ffb_change(true);\n                        }\n                    }\n                }\n                ImGui::TextDisabled(\"Response correction / max torque are stored with the wheel profile, not named FFB feel profiles. Leave correction off for a linear DD wheel unless measured.\");\n                ImGui::TextDisabled(\"Advanced values apply live like the main controls; use Save Force Feedback to persist them.\");\n""")

replace_once(rel,
"""            if (ImGui::Button(ffbDirty_ ? \"Save Force Feedback*\" : \"Save Force Feedback\"))\n            {\n                if (Settings::write(Module::UserIniPath))\n                {\n                    ffbDirty_ = false;\n                    status_ = \"Force feedback settings saved.\";\n                }\n                else\n                    status_ = \"Could not save force feedback settings.\";\n            }\n\n            ImGui::SeparatorText(\"Safe direction test\");\n""",
"""            if (ImGui::Button(ffbDirty_ ? \"Save Force Feedback*\" : \"Save Force Feedback\"))\n            {\n                if (Settings::write(Module::UserIniPath))\n                {\n                    ffbDirty_ = false;\n                    status_ = \"Force feedback settings saved.\";\n                }\n                else\n                    status_ = \"Could not save force feedback settings.\";\n            }\n\n            ImGui::SeparatorText(\"FFB Headroom / Clipping\");\n            const WheelFFBHeadroomSnapshot headroom = WheelFFB_GetHeadroomSnapshot();\n            ImGui::Text(\"Current structural demand: %.0f%%   Peak: %.0f%%\",\n                headroom.currentDemand * 100.0f, headroom.peakDemand * 100.0f);\n            ImGui::Text(\"P95: %.0f%%   P99: %.0f%%   samples: %llu (%.1fs)\",\n                headroom.p95Demand * 100.0f, headroom.p99Demand * 100.0f,\n                static_cast<unsigned long long>(headroom.samples),\n                static_cast<float>(headroom.samples) / 60.0f);\n            ImGui::Text(\"Soft-knee demand (>75%%): %.1f%%   hard-cap demand (>=135%%): %.2f%%\",\n                headroom.softKneePercent, headroom.hardClipPercent);\n            if (Settings::WheelFFBMaxTorqueNm.get() > 0.0f && headroom.samples > 0)\n            {\n                ImGui::TextDisabled(\"P99 requested equivalent: %.2f Nm on a %.1f Nm wheel (before hardware LUT/cap).\",\n                    headroom.p99Demand * Settings::WheelFFBMaxTorqueNm.get(),\n                    Settings::WheelFFBMaxTorqueNm.get());\n            }\n            if (headroom.samples >= 600)\n                ImGui::Text(\"Suggested Overall Strength: %.2f  (targets structural P99 near 90%% before wheel LUT)\",\n                    headroom.suggestedOverall);\n            else\n                ImGui::TextDisabled(\"Drive normally for at least 10 seconds; 20-30 seconds with several corners is better before trusting the suggestion.\");\n            ImGui::TextDisabled(\"Collision, gear events, startup/recreate ramps and near-stop frames are excluded from the statistics.\");\n            if (ImGui::Button(\"Reset headroom analysis\"))\n                WheelFFB_ResetHeadroomStats();\n\n            ImGui::SeparatorText(\"Safe direction test\");\n""")

replace_count(rel,
"""                Settings::WheelFFBSteeringWeight = 1.45f;\n                Settings::WheelFFBGripLoss = 0.65f;\n""",
"""                Settings::WheelFFBSteeringWeight = 1.45f;\n                Settings::WheelFFBMechanicalTrail = 0.25f;\n                Settings::WheelFFBGripLoss = 0.65f;\n""", 1)
replace_count(rel,
"""                Settings::WheelFFBSteeringWeight = 1.75f;\n                Settings::WheelFFBGripLoss = 0.65f;\n""",
"""                Settings::WheelFFBSteeringWeight = 1.75f;\n                Settings::WheelFFBMechanicalTrail = 0.25f;\n                Settings::WheelFFBGripLoss = 0.65f;\n""", 1)
replace_once(rel,
"""                    status_ = \"Loaded MOZA R3 Physics SAT: lateral load, body slide and front scrub are separated; diagnostic logging enabled. Saved to user.ini.\";\n""",
"""                    status_ = \"Loaded MOZA R3 Physics SAT: speed-adaptive front slip plus pneumatic/mechanical trail SAT; diagnostic logging enabled. Saved to user.ini.\";\n""")

# ---------------------------------------------------------------------------
# Shipped defaults/documentation for the new model and hardware calibration.
# ---------------------------------------------------------------------------
rel = "OutRun2006Tweaks.ini"
replace_once(rel,
"""[WheelFFB]\n; Opt-in 10 Hz diagnostics. Force Feedback > Save Force Feedback persists changes.\nTelemetry = false\n""",
"""[WheelFFB]\n; Physics SAT retains pneumatic-trail falloff while a bounded mechanical/caster\n; contribution keeps useful steering torque through deeper front slip.\nMechanicalTrail = 0.25\n\n; Optional wheel-specific response correction. Leave disabled for a linear DD\n; base unless you have measured a correction curve. LUT entries are DirectInput\n; commands for desired torque 0%,10%,...,100%. These values belong in wheel\n; profiles and are intentionally excluded from named FFB feel profiles.\nResponseCorrection = false\nResponseLUT = 0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0\nMaxTorqueNm = 0.0\n\n; Opt-in 10 Hz diagnostics. Force Feedback > Save Force Feedback persists changes.\nTelemetry = false\n""")

# ---------------------------------------------------------------------------
# Production-header tests. These run without Windows/DirectInput and protect
# the new curve/transient/LUT behavior numerically.
# ---------------------------------------------------------------------------
write("tools/test_wheel_ffb_current.cpp", r'''// Host-only tests execute production headers. No Windows/DirectInput device needed.
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
struct D3DVECTOR { float x=0, y=0, z=0; };
struct D3DMATRIX { float _11=1,_12=0,_13=0,_14=0,_21=0,_22=1,_23=0,_24=0,_31=0,_32=0,_33=1; };
struct EVWORK_CAR { D3DVECTOR position_14, spd_mb_20; D3DMATRIX matrix_70; };
#include "hooks_wheel_vehicle_dynamics.hpp"
#include "wheel_ffb_math.hpp"
static int checks = 0;
void require(bool b, const char* msg) { ++checks; if (!b) { std::cerr << msg << '\n'; std::exit(1); } }
void heading(EVWORK_CAR& c, float a) { c.matrix_70._11=std::cos(a);c.matrix_70._13=-std::sin(a);c.matrix_70._31=std::sin(a);c.matrix_70._33=std::cos(a); }
void step(WheelVehicleDynamics& d, EVWORK_CAR& c, float a=0, float beta=0, float steer=0, float speed=.5f) {
 heading(c,a);c.position_14.x+=std::sin(a+beta);c.position_14.z+=std::cos(a+beta);d.update(&c,steer,speed,0);
}
int main() {
 using namespace WheelFFBMath;
 require(pneumatic_sat_shape(0)==0,"SAT zero");
 require(pneumatic_sat_shape(std::numeric_limits<float>::quiet_NaN())==0,"SAT NaN");
 require(lateral_force_shape(.32f)>.999f,"Fy proxy saturates in deep slip");
 require(pneumatic_sat_shape(.12f)>.90f,"pneumatic SAT strong in normal loaded corner");
 require(pneumatic_sat_shape(.16f)>.98f,"pneumatic SAT peaks near prior 0.16rad region");
 require(pneumatic_sat_shape(.32f)<.50f,"pneumatic trail falls in deep understeer");
 require(combined_sat_shape(.16f,.25f)<=1.000001f,"combined SAT bounded");
 require(combined_sat_shape(.32f,.25f)>pneumatic_sat_shape(.32f),"mechanical trail preserves deep-slip torque");
 require(combined_sat_shape(.32f,0.0f)==pneumatic_sat_shape(.32f),"mechanical trail zero is pure pneumatic");
 require(std::abs(combined_sat_shape(.32f,.25f)-combined_sat_shape(-.32f,.25f))<1e-6f,"SAT shape symmetry");
 for(int i=0;i<=7000;++i) {float a=i*.0001f;float p=pneumatic_sat_shape(a),c=combined_sat_shape(a,.25f);require(std::isfinite(p)&&p>=0&&p<=1.000001f,"pneumatic bounds");require(std::isfinite(c)&&c>=0&&c<=1.000001f,"combined bounds");}
 require(soft_saturate(.5f)==.5f,"soft clip linear midrange");
 require(std::abs(soft_saturate(-.5f)+.5f)<1e-6,"soft clip symmetry");
 require(soft_saturate(1.0f)>.90f&&soft_saturate(1.0f)<1.0f,"soft clip late knee");
 require(soft_saturate(2.0f)==1.0f&&soft_saturate(-2.0f)==-1.0f,"soft clip cap");
 float clipPrev=0; for(int i=0;i<=2000;++i){float x=i*.001f,y=soft_saturate(x);require(std::isfinite(y)&&y>=clipPrev-1e-6f&&y<=1.000001f,"soft clip monotonic");clipPrev=y;}
 require(physics_return_relief(.15f,-.08f)==.85f,"countersteer relief");
 require(physics_return_relief(.15f,.08f)==1,"opposing work no relief");
 ResponseLUT linear{}; require(parse_response_lut("0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1",linear),"linear LUT parses");
 require(std::abs(apply_response_lut(.55f,linear)-.55f)<1e-5f,"linear LUT identity");
 ResponseLUT boosted{}; require(parse_response_lut("0,0.15,0.25,0.35,0.45,0.55,0.65,0.75,0.84,0.92,1",boosted),"boost LUT parses");
 require(apply_response_lut(.10f,boosted)>.10f,"LUT can compensate low-force deadzone");
 require(!parse_response_lut("0,0.2,0.1,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1",boosted),"non-monotonic LUT rejected");
 require(!parse_response_lut("0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1,1",boosted),"nonzero LUT origin rejected");
 WheelVehicleDynamics gap; EVWORK_CAR gapCar; gap.reset();
 for(int i=0;i<80;++i)step(gap,gapCar);
 gap.update(nullptr,0,.5,0);
 step(gap,gapCar,.2f);step(gap,gapCar,.2f);
 require(std::abs(gap.yawRate())<.01f,"short-gap derivative baseline");
 WheelVehicleDynamics resume; EVWORK_CAR resumeCar;resume.reset();for(int i=0;i<80;++i)step(resume,resumeCar);
 require(resume.calibrated()&&resume.motionScale()>0,"resume baseline ready");
 resume.reset_dynamic();
 require(resume.calibrated()&&resume.motionScale()==0&&!resume.sampleValid(),"dynamic reset preserves basis but clears motion scale");
 WheelVehicleDynamics d; EVWORK_CAR c;d.reset();for(int i=0;i<80;++i)step(d,c);
 require(d.calibrated()&&d.forwardAxis()==3,"straight basis calibration");require(d.sampleValid()&&d.activationBlend()==1,"activation");
 for(int i=0;i<40;++i)step(d,c,i*.01f,.20f,.5f);
 require(std::abs(d.yawRate()-.6f)<.02f,"known yaw");require(std::abs(d.bodySlip()-.2f)<.003f,"known beta");
 require(std::isfinite(d.rawFrontSlip())&&d.frontSlipBlend()>.24f,"raw/filtered front slip telemetry active");
 WheelVehicleDynamics low; EVWORK_CAR lowCar; low.reset(); for(int i=0;i<80;++i)step(low,lowCar,0,0,0,.15f); step(low,lowCar,.01f,0,.2f,.15f);
 WheelVehicleDynamics high; EVWORK_CAR highCar; high.reset(); for(int i=0;i<80;++i)step(high,highCar,0,0,0,.90f); step(high,highCar,.01f,0,.2f,.90f);
 require(high.frontSlipBlend()>low.frontSlipBlend(),"front-slip transient speeds up with vehicle speed");
 float beta=d.bodySlip();d.update(nullptr,0,.5,0);require(d.bodySlip()<beta&&!d.sampleValid(),"invalid decay");
 for(int i=0;i<4;++i)d.update(nullptr,0,.5,0);
 require(d.bodySlip()==0&&d.yawRate()==0&&d.frontSlip()==0&&d.activationBlend()==0,"five-invalid clear");
 step(d,c,1);step(d,c,1);step(d,c,1);require(std::abs(d.yawRate())<.001,"reentry does not treat missing interval as one tick");
 c.position_14.x+=1000;d.update(&c,0,.5,0);require(d.discontinuityCount()>0&&d.frontSlip()==0,"warp clear");
 for(int i=0;i<30;++i)step(d,c,0);
 c.position_14.z-=1;d.update(&c,0,.5,0);require(!d.sampleValid()&&d.frontSlip()==0,"reverse proxy disabled");
 d.update(&c,0,0,0);require(d.frontSlip()==0&&d.yawRate()==0&&!d.sampleValid(),"stop clear and invalid dynamic sample");
 std::cout<<checks<<" production-header invariants passed\n";
}
''')

# ---------------------------------------------------------------------------
# Current-source verifier: replace the old single-trail assertion and add
# regression guards for every new research-informed feature.
# ---------------------------------------------------------------------------
rel = "tools/verify_wheel_ffb_current.py"
text = read(rel)
text = text.replace(
    "profiles = read('src/wheel_profile_store.hpp')\nini = read('OutRun2006Tweaks.ini')\n",
    "profiles = read('src/wheel_profile_store.hpp')\nruntime = read('src/wheel_ffb_runtime.hpp')\nini = read('OutRun2006Tweaks.ini')\n")
text = text.replace(
    "req(ffb, 'WheelFFBMath::trail_shape(frontSlip)', 'production SAT curve shared with compiled tests')\n",
    "req(ffb, 'WheelFFBMath::pneumatic_sat_shape(frontSlip)', 'production pneumatic SAT curve shared with compiled tests')\nreq(ffb, 'WheelFFBMath::combined_sat_shape(frontSlip, mechanicalTrailMix)', 'Physics SAT combines pneumatic and mechanical trail')\n")
anchor = "req(ffb, 'void WheelFFB_RequestSettingsTransition()', 'FFB settings transition exported to UI')\n"
if anchor not in text:
    raise SystemExit("verify anchor missing")
addition = r'''req(dyn, 'rawFrontSlip_', 'raw front-slip telemetry retained')
req(dyn, 'frontSlipBlend_ = 0.24f + (0.58f - 0.24f) * transientT;', 'front-slip transient accelerates with speed')
req(dyn, 'bodySlipBlend_ = 0.18f + (0.34f - 0.18f) * transientT;', 'body-slip transient accelerates with speed')
req(dyn, 'yawRateBlend_ = 0.20f + (0.38f - 0.20f) * transientT;', 'yaw transient accelerates with speed')
req(math, 'lateral_force_shape(float alpha)', 'front lateral-force proxy curve')
req(math, 'pneumatic_trail_factor(float alpha)', 'pneumatic trail separated')
req(math, 'combined_sat_shape(float alpha, float mechanicalTrailMix)', 'mechanical/caster trail separated')
req(ffb, 'WheelFFBMechanicalTrail', 'mechanical trail setting')
req(ffb, 'WheelFFB SATMODEL', 'raw/filtered and decomposed SAT telemetry')
req(runtime, 'WheelFFBHeadroomSnapshot', 'shared headroom snapshot API')
req(ffb, 'record_headroom(std::abs(total), headroomEligible);', 'structural headroom analyzer')
req(ffb, 'headroomSamples_ >= 600', 'gain recommendation waits for enough driving')
req(wheel_ui, 'FFB Headroom / Clipping', 'headroom UI exposed')
req(wheel_ui, 'Suggested Overall Strength', 'headroom gain recommendation exposed')
req(wheel_ui, 'Physics / Structural', 'FFB UI groups structural physics')
req(wheel_ui, 'Steering Feel', 'FFB UI groups steering feel')
req(wheel_ui, 'Effects', 'FFB UI groups tactile effects')
req(wheel_ui, 'Mechanical / Caster Trail', 'mechanical trail tuning exposed')
req(ffb, 'WheelFFBResponseCorrection', 'optional response correction setting')
req(ffb, 'WheelFFBResponseLUT', 'per-wheel response LUT setting')
req(math, 'parse_response_lut', 'response LUT validation')
req(math, 'apply_response_lut', 'response LUT application')
req(ffb, 'apply_response_correction(levelBeforeResponse)', 'response correction is final ConstantForce mapping')
req(profiles, 'FFBResponseCorrection = ', 'wheel profile stores response correction enable')
req(profiles, 'FFBResponseLUT = ', 'wheel profile stores response LUT')
req(profiles, 'FFBMaxTorqueNm = ', 'wheel profile stores physical max torque')
req(profiles, 'key != "ResponseCorrection" && key != "ResponseLUT"', 'FFB feel profiles exclude hardware response curve')
req(profiles, 'key != "MaxTorqueNm"', 'FFB feel profiles exclude physical torque rating')
req(wheel_ui, 'Leave correction off for a linear DD wheel unless measured.', 'response correction UI defaults to measurement-first guidance')
req(ini, 'MechanicalTrail = 0.25', 'shipped mechanical trail default')
req(ini, 'ResponseCorrection = false', 'shipped response correction disabled')
req(ini, 'MaxTorqueNm = 0.0', 'shipped wheel max torque unknown')
'''
text = text.replace(anchor, anchor + addition)
write(rel, text)

# ---------------------------------------------------------------------------
# Documentation: concise architecture/operator notes. Avoid pretending the
# arcade game exposes real tyre forces; document every proxy and limitation.
# ---------------------------------------------------------------------------
for rel, heading, body in [
    ("WHEEL_FFB.md", "## Research-informed SAT and wheel-response model", r'''

## Research-informed SAT and wheel-response model

Physics SAT now separates a **pneumatic-trail** component from a bounded **mechanical/caster-trail** component. Both are driven by the estimated front-slip/lateral-force proxy; mechanical trail is not a centre spring. Pneumatic SAT peaks around the normal loaded-corner region and falls first as front slip grows, while the mechanical contribution preserves some steering authority through deeper understeer instead of letting the wheel go artificially dead.

The vehicle estimator keeps the existing bicycle-model-inspired `roadWheelAngle - bodySlip - yawRate * yawLeadSeconds` relation, but its body-slip/yaw/front-slip filters are now speed-adaptive. This is a relaxation-length-inspired approximation: at higher vehicle speed the same fixed time low-pass created too much countersteer/SAT lag. Telemetry records both raw and filtered states plus the active blend values (`WheelFFB SATMODEL`).

`Force Feedback -> FFB Headroom / Clipping` measures sustained structural demand only. Crash/gear events, startup/recreate ramps and near-stop frames are excluded. P95/P99, soft-knee occupancy and hard-cap demand are reported, with a non-automatic Overall Strength suggestion targeting roughly 90% P99 demand.

Wheel-specific response correction is optional and **off by default**. A wheel profile can store `ResponseCorrection`, an 11-point monotonic `ResponseLUT` (desired torque 0..100% in 10% steps -> DirectInput command), and optional `MaxTorqueNm` for diagnostics. These hardware properties are deliberately excluded from named FFB feel profiles. Leave correction linear/off on a DD wheel unless a measured response curve justifies it.
'''),
    ("README.md", "### Research-informed steering force model", r'''

### Research-informed steering force model

Physics SAT uses a split pneumatic + mechanical/caster trail model instead of one all-purpose falloff curve. Front-slip filtering accelerates with vehicle speed to reduce countersteer lag, while the existing Natural SAT remains the full fallback whenever Physics SAT telemetry is not valid. F11 also includes structural FFB headroom/P95/P99 diagnostics and an optional per-wheel response LUT; hardware correction is disabled by default and should only be enabled from measured wheel behavior.
'''),
]:
    text = read(rel)
    if heading not in text:
        text = text.rstrip() + body + "\n"
        write(rel, text)

print("research-informed FFB source patch applied")
