#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
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

    struct EngineHapticEstimate
    {
        float rpmNorm = 0.0f;
        float frequencyHz = 0.0f;
        float amplitudeScale = 0.0f;
    };

    // OutRun does not expose a verified engine-RPM field in EVWORK_CAR yet.
    // Estimate normalized RPM from vehicle speed, current gear and throttle so
    // the haptic can be swapped to a real RPM source later without changing the
    // output path or UI. Frequencies stay below 20 Hz for a stable 60 Hz FFB loop.
    inline EngineHapticEstimate estimate_engine_haptics(
        float speedNorm, unsigned int gear, float throttleNorm)
    {
        speedNorm = std::isfinite(speedNorm)
            ? std::clamp(speedNorm, 0.0f, 1.0f) : 0.0f;
        throttleNorm = std::isfinite(throttleNorm)
            ? std::clamp(throttleNorm, 0.0f, 1.0f) : 0.0f;

        // Approximate normalized road speed at redline for gears 1..6.
        // Only the relative drop/rise matters for tactile frequency shaping.
        static constexpr std::array<float, 6> GearRedlineSpeed = {
            0.17f, 0.30f, 0.44f, 0.60f, 0.78f, 1.00f
        };
        const unsigned int forwardGear = std::clamp(gear, 1u, 6u);
        const float coupledRpm =
            speedNorm / GearRedlineSpeed[forwardGear - 1u];
        const float idleFloor = 0.10f + 0.05f * throttleNorm;
        const float freeRev = (gear == 0 || speedNorm < 0.025f)
            ? 0.10f + 0.55f * throttleNorm
            : 0.0f;

        EngineHapticEstimate out{};
        out.rpmNorm = std::clamp(
            std::max({ coupledRpm, idleFloor, freeRev }), 0.08f, 1.0f);
        // Keep the texture above the heavy low-frequency pulse region while
        // remaining below the 60 Hz FFB loop Nyquist limit.
        out.frequencyHz = 13.0f + 11.0f * out.rpmNorm;
        out.amplitudeScale = std::clamp(
            0.45f + 0.40f * out.rpmNorm + 0.15f * throttleNorm,
            0.0f, 1.0f);
        return out;
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

    // Reference peak of Fy * pneumatic trail. The absolute units are not
    // available from OutRun, so this keeps SteeringWeight near its established
    // scale while the relative trail terms shape the torque curve.
    inline constexpr float PneumaticReferencePeak = 0.838899081f;

    // Lateral force and pneumatic trail have different transient behaviour.
    // forceAlpha is the filtered tyre-force slip, while trailAlpha may be a
    // modest phase-led version used only by the pneumatic lever arm.
    inline float pneumatic_sat_shape(float forceAlpha, float trailAlpha)
    {
        if (!std::isfinite(forceAlpha) || !std::isfinite(trailAlpha)) return 0.0f;
        const float raw =
            lateral_force_shape(forceAlpha) * pneumatic_trail_factor(trailAlpha);
        return std::clamp(raw / PneumaticReferencePeak, 0.0f, 1.0f);
    }

    inline float pneumatic_sat_shape(float alpha)
    {
        return pneumatic_sat_shape(alpha, alpha);
    }

    // Mechanical/caster trail contributes whenever front lateral force exists;
    // it is not a substitute that appears only after pneumatic trail collapses.
    // The setting is a normalized pseudo-trail ratio, not a physical distance.
    inline float mechanical_sat_shape(float forceAlpha, float mechanicalTrailRatio)
    {
        if (!std::isfinite(forceAlpha)) return 0.0f;
        const float ratio = std::clamp(mechanicalTrailRatio, 0.0f, 0.60f);
        const float denominator = PneumaticReferencePeak + ratio;
        return denominator > 0.0f
            ? std::clamp(lateral_force_shape(forceAlpha) * ratio / denominator, 0.0f, 1.0f)
            : 0.0f;
    }

    // Total aligning moment follows Fy * (pneumatic trail + mechanical trail).
    // Normalize the total pseudo-trail so enabling mechanical trail reshapes
    // the SAT curve without silently turning SteeringWeight into a second gain.
    inline float combined_sat_shape(
        float forceAlpha, float trailAlpha, float mechanicalTrailRatio)
    {
        if (!std::isfinite(forceAlpha) || !std::isfinite(trailAlpha)) return 0.0f;
        const float ratio = std::clamp(mechanicalTrailRatio, 0.0f, 0.60f);
        const float denominator = PneumaticReferencePeak + ratio;
        if (denominator <= 0.0f)
            return 0.0f;
        const float raw = lateral_force_shape(forceAlpha) *
            (pneumatic_trail_factor(trailAlpha) + ratio);
        return std::clamp(raw / denominator, 0.0f, 1.0f);
    }

    inline float combined_sat_shape(float alpha, float mechanicalTrailRatio)
    {
        return combined_sat_shape(alpha, alpha, mechanicalTrailRatio);
    }

    // Kept as a compatibility alias for older host tests/tools. Production
    // Physics SAT uses the decomposed functions above explicitly.
    inline float trail_shape(float alpha)
    {
        return pneumatic_sat_shape(alpha);
    }

    // Guarded native steering-force candidate for v0.3. actionforce_DBC is
    // still an unverified X-Force candidate, so this state machine treats the
    // memory value as data rather than assuming every in-range sample is useful.
    // Durations are expressed in seconds rather than fixed physics ticks so the
    // safety behavior remains stable if the host update cadence ever changes.
    inline constexpr float XForceNominalFullScale = 62.0f;
    inline constexpr float XForceAbsoluteSafetyLimit = 128.0f;
    inline constexpr float XForceNoiseFloor = 0.20f;
    inline constexpr float XForceResponseThreshold = 0.05f;
    inline constexpr float XForceStoppedSpeed = 0.025f;
    inline constexpr float XForceResumeSpeed = 0.040f;
    inline constexpr float XForceFreshDelta = 0.020f;
    inline constexpr float XForceUnresponsiveSeconds = 0.50f;
    inline constexpr float XForceBlendInSeconds = 0.20f;
    inline constexpr float XForceBlendOutSeconds = 0.10f;

    inline float sanitize_frame_seconds(float deltaSeconds)
    {
        if (!std::isfinite(deltaSeconds) || deltaSeconds <= 0.0f)
            return 1.0f / 60.0f;
        return std::clamp(deltaSeconds, 1.0f / 240.0f, 0.10f);
    }

    struct XForceGuardSample
    {
        bool finite = false;
        bool rangeValid = false;
        bool responseObserved = false;
        bool responsive = false;
        bool freshAfterStop = false;
        bool valid = false;
        bool stopped = true;
        float normalized = 0.0f;
        float motionGate = 0.0f;
        float nativeBlend = 0.0f;
        float unresponsiveSeconds = 0.0f;
    };

    class XForceGuard
    {
    public:
        void reset()
        {
            responseObserved_ = false;
            stopped_ = true;
            awaitingFreshAfterStop_ = true;
            stoppedRaw_ = 0.0f;
            lastNormalized_ = 0.0f;
            nativeBlend_ = 0.0f;
            unresponsiveSeconds_ = 0.0f;
        }

        XForceGuardSample update(
            float raw, float speedNorm, float steerAbs, bool invert,
            float deltaSeconds = 1.0f / 60.0f)
        {
            XForceGuardSample out{};
            deltaSeconds = sanitize_frame_seconds(deltaSeconds);
            speedNorm = std::isfinite(speedNorm)
                ? std::clamp(speedNorm, 0.0f, 1.0f) : 0.0f;
            steerAbs = std::isfinite(steerAbs)
                ? std::clamp(steerAbs, 0.0f, 1.0f) : 0.0f;

            out.finite = std::isfinite(raw);
            out.rangeValid = out.finite &&
                std::abs(raw) <= XForceAbsoluteSafetyLimit;

            // Hysteresis prevents near-zero speed noise from repeatedly
            // entering/leaving the stopped state. Stopped native torque is a
            // hard zero because the source can retain its last value at rest.
            if (stopped_)
            {
                if (speedNorm < XForceResumeSpeed)
                {
                    if (out.rangeValid)
                        stoppedRaw_ = raw;
                    nativeBlend_ = 0.0f;
                    lastNormalized_ = 0.0f;
                    unresponsiveSeconds_ = 0.0f;
                    out.responseObserved = responseObserved_;
                    out.stopped = true;
                    return out;
                }
                stopped_ = false;
                awaitingFreshAfterStop_ = true;
            }
            else if (speedNorm <= XForceStoppedSpeed)
            {
                stopped_ = true;
                awaitingFreshAfterStop_ = true;
                if (out.rangeValid)
                    stoppedRaw_ = raw;
                nativeBlend_ = 0.0f;
                lastNormalized_ = 0.0f;
                unresponsiveSeconds_ = 0.0f;
                out.responseObserved = responseObserved_;
                out.stopped = true;
                return out;
            }

            if (out.rangeValid && steerAbs >= 0.05f &&
                std::abs(raw) >= XForceResponseThreshold)
            {
                responseObserved_ = true;
            }

            // A non-zero value frozen at the stop point must not be replayed
            // when the car starts moving. Zero is safe to accept immediately;
            // otherwise wait until the game changes the source value.
            if (awaitingFreshAfterStop_ && out.rangeValid &&
                (std::abs(raw) < XForceResponseThreshold ||
                 std::abs(raw - stoppedRaw_) >= XForceFreshDelta))
            {
                awaitingFreshAfterStop_ = false;
            }

            // A true zero crossing is allowed. Only call the candidate dead
            // after about half a second of near-zero output while the driver is
            // clearly steering a moving car. The timer is cadence-independent.
            if (out.rangeValid && steerAbs >= 0.15f && speedNorm >= 0.08f)
            {
                if (std::abs(raw) < XForceResponseThreshold)
                    unresponsiveSeconds_ = std::min(
                        XForceUnresponsiveSeconds, unresponsiveSeconds_ + deltaSeconds);
                else
                    unresponsiveSeconds_ = 0.0f;
            }
            else
            {
                unresponsiveSeconds_ = 0.0f;
            }
            const bool responsiveNow = responseObserved_ &&
                unresponsiveSeconds_ < XForceUnresponsiveSeconds;

            float currentNormalized = 0.0f;
            if (out.rangeValid)
            {
                const float magnitude = std::max(
                    0.0f, std::abs(raw) - XForceNoiseFloor);
                const float normalizedMagnitude = std::clamp(
                    magnitude / (XForceNominalFullScale - XForceNoiseFloor),
                    0.0f, 1.0f);
                currentNormalized = std::copysign(normalizedMagnitude, raw);
                if (invert)
                    currentNormalized = -currentNormalized;
            }

            out.valid = out.rangeValid && responsiveNow &&
                !awaitingFreshAfterStop_;
            if (out.valid)
                lastNormalized_ = currentNormalized;

            const float targetBlend = out.valid ? 1.0f : 0.0f;
            const float blendInStep = deltaSeconds / XForceBlendInSeconds;
            const float blendOutStep = deltaSeconds / XForceBlendOutSeconds;
            const float delta = targetBlend - nativeBlend_;
            nativeBlend_ += std::clamp(delta, -blendOutStep, blendInStep);
            nativeBlend_ = std::clamp(nativeBlend_, 0.0f, 1.0f);

            out.responseObserved = responseObserved_;
            out.responsive = responsiveNow;
            out.freshAfterStop = !awaitingFreshAfterStop_;
            out.stopped = false;
            out.normalized = out.valid ? currentNormalized : lastNormalized_;
            out.motionGate = smoothstep01(
                (speedNorm - XForceResumeSpeed) / 0.12f);
            out.nativeBlend = nativeBlend_;
            out.unresponsiveSeconds = unresponsiveSeconds_;
            return out;
        }

    private:
        bool responseObserved_ = false;
        bool stopped_ = true;
        bool awaitingFreshAfterStop_ = true;
        float stoppedRaw_ = 0.0f;
        float lastNormalized_ = 0.0f;
        float nativeBlend_ = 0.0f;
        float unresponsiveSeconds_ = 0.0f;
    };

    struct XForceMixResult
    {
        float torque = 0.0f;
        float nativeShare = 0.0f;
    };

    inline XForceMixResult mix_xforce_character(
        float modernTorque,
        float nativeTorque,
        int feedbackCharacter,
        float configuredMix,
        float guardBlend)
    {
        modernTorque = std::isfinite(modernTorque) ? modernTorque : 0.0f;
        nativeTorque = std::isfinite(nativeTorque) ? nativeTorque : 0.0f;
        configuredMix = std::isfinite(configuredMix)
            ? std::clamp(configuredMix, 0.0f, 1.0f) : 0.50f;
        guardBlend = std::isfinite(guardBlend)
            ? std::clamp(guardBlend, 0.0f, 1.0f) : 0.0f;
        feedbackCharacter = std::clamp(feedbackCharacter, 0, 2);

        XForceMixResult out{};
        if (feedbackCharacter == 1)
            out.nativeShare = guardBlend;
        else if (feedbackCharacter == 2)
            out.nativeShare = configuredMix * guardBlend;
        out.torque = modernTorque +
            (nativeTorque - modernTorque) * out.nativeShare;
        return out;
    }


    struct XForceAnalysisSnapshot
    {
        std::uint64_t samples = 0;
        float corrSteer = 0.0f;
        float corrModernSat = 0.0f;
        float corrFrontSlip = 0.0f;
        float corrYawRate = 0.0f;
        float confidence = 0.0f;
        bool frozenSuspicious = false;
        float frozenSeconds = 0.0f;
        float p50Abs = 0.0f;
        float p90Abs = 0.0f;
        float p95Abs = 0.0f;
        float p99Abs = 0.0f;
        float maxAbs = 0.0f;
    };

    // Diagnostic-only analyzer for proving what actionforce_DBC represents.
    // Confidence and freeze detection never gate wheel torque; they exist to
    // collect evidence before any stronger native-force assumptions are made.
    class XForceSignalAnalyzer
    {
    public:
        void reset()
        {
            samples_.fill(Sample{});
            histogram_.fill(0);
            writeIndex_ = 0;
            count_ = 0;
            totalSamples_ = 0;
            maxAbs_ = 0.0f;
            previousValid_ = false;
            previousRaw_ = 0.0f;
            previousSteer_ = 0.0f;
            previousFrontSlip_ = 0.0f;
            previousYawRate_ = 0.0f;
            frozenSeconds_ = 0.0f;
        }

        void update(
            float raw, float speedNorm, float steer, float modernSat,
            float frontSlip, float yawRate,
            float deltaSeconds = 1.0f / 60.0f)
        {
            deltaSeconds = sanitize_frame_seconds(deltaSeconds);
            speedNorm = std::isfinite(speedNorm)
                ? std::clamp(speedNorm, 0.0f, 1.0f) : 0.0f;
            if (!std::isfinite(raw) ||
                std::abs(raw) > XForceAbsoluteSafetyLimit ||
                speedNorm < XForceResumeSpeed)
            {
                previousValid_ = false;
                frozenSeconds_ = std::max(0.0f, frozenSeconds_ - deltaSeconds * 2.0f);
                return;
            }

            steer = std::isfinite(steer) ? std::clamp(steer, -1.0f, 1.0f) : 0.0f;
            modernSat = std::isfinite(modernSat) ? modernSat : 0.0f;
            frontSlip = std::isfinite(frontSlip) ? frontSlip : 0.0f;
            yawRate = std::isfinite(yawRate) ? yawRate : 0.0f;

            const Sample sample{ raw, steer, modernSat, frontSlip, yawRate };
            samples_[writeIndex_ % WindowSamples] = sample;
            ++writeIndex_;
            count_ = std::min<std::size_t>(count_ + 1, WindowSamples);

            const float absRaw = std::abs(raw);
            const std::size_t bin = std::min<std::size_t>(
                HistogramBins - 1,
                static_cast<std::size_t>(std::lround(
                    absRaw * static_cast<float>(HistogramBins - 1) /
                    XForceAbsoluteSafetyLimit)));
            ++histogram_[bin];
            ++totalSamples_;
            maxAbs_ = std::max(maxAbs_, absRaw);

            if (previousValid_ && speedNorm >= 0.08f &&
                absRaw >= XForceResponseThreshold)
            {
                const bool stateChanged =
                    std::abs(steer - previousSteer_) >= 0.025f ||
                    std::abs(frontSlip - previousFrontSlip_) >= 0.005f ||
                    std::abs(yawRate - previousYawRate_) >= 0.020f;
                const bool rawFrozen = std::abs(raw - previousRaw_) < 0.010f;
                if (stateChanged && rawFrozen)
                    frozenSeconds_ += deltaSeconds;
                else
                    frozenSeconds_ = std::max(
                        0.0f, frozenSeconds_ - deltaSeconds * 2.0f);
            }
            else
            {
                frozenSeconds_ = std::max(0.0f, frozenSeconds_ - deltaSeconds);
            }

            previousValid_ = true;
            previousRaw_ = raw;
            previousSteer_ = steer;
            previousFrontSlip_ = frontSlip;
            previousYawRate_ = yawRate;
        }

        XForceAnalysisSnapshot snapshot() const
        {
            XForceAnalysisSnapshot out{};
            out.samples = totalSamples_;
            out.corrSteer = correlation(&Sample::steer);
            out.corrModernSat = correlation(&Sample::modernSat);
            out.corrFrontSlip = correlation(&Sample::frontSlip);
            out.corrYawRate = correlation(&Sample::yawRate);
            out.frozenSeconds = frozenSeconds_;
            out.frozenSuspicious = frozenSeconds_ >= 0.50f;
            out.p50Abs = percentile(0.50);
            out.p90Abs = percentile(0.90);
            out.p95Abs = percentile(0.95);
            out.p99Abs = percentile(0.99);
            out.maxAbs = maxAbs_;

            const float primary = std::max({
                std::abs(out.corrSteer),
                std::abs(out.corrModernSat),
                std::abs(out.corrFrontSlip) });
            const float secondary = std::max(
                std::abs(out.corrFrontSlip), std::abs(out.corrYawRate));
            const float sampleRamp = std::clamp(
                static_cast<float>(count_) / 120.0f, 0.0f, 1.0f);
            const float freezePenalty = out.frozenSuspicious ? 0.35f : 1.0f;
            out.confidence = std::clamp(
                (0.70f * primary + 0.30f * secondary) * sampleRamp * freezePenalty,
                0.0f, 1.0f);
            return out;
        }

    private:
        struct Sample
        {
            float raw = 0.0f;
            float steer = 0.0f;
            float modernSat = 0.0f;
            float frontSlip = 0.0f;
            float yawRate = 0.0f;
        };

        static constexpr std::size_t WindowSamples = 180;
        static constexpr std::size_t HistogramBins = 257;

        using SampleMember = float Sample::*;
        float correlation(SampleMember member) const
        {
            if (count_ < 12)
                return 0.0f;
            double sx = 0.0, sy = 0.0, sxx = 0.0, syy = 0.0, sxy = 0.0;
            for (std::size_t i = 0; i < count_; ++i)
            {
                const double x = samples_[i].raw;
                const double y = samples_[i].*member;
                sx += x;
                sy += y;
                sxx += x * x;
                syy += y * y;
                sxy += x * y;
            }
            const double n = static_cast<double>(count_);
            const double vx = n * sxx - sx * sx;
            const double vy = n * syy - sy * sy;
            if (vx <= 1.0e-9 || vy <= 1.0e-9)
                return 0.0f;
            const double value = (n * sxy - sx * sy) / std::sqrt(vx * vy);
            return static_cast<float>(std::clamp(value, -1.0, 1.0));
        }

        float percentile(double q) const
        {
            if (totalSamples_ == 0)
                return 0.0f;
            const std::uint64_t target = std::max<std::uint64_t>(
                1, static_cast<std::uint64_t>(std::ceil(totalSamples_ * q)));
            std::uint64_t cumulative = 0;
            for (std::size_t i = 0; i < histogram_.size(); ++i)
            {
                cumulative += histogram_[i];
                if (cumulative >= target)
                {
                    return static_cast<float>(i) *
                        (XForceAbsoluteSafetyLimit /
                         static_cast<float>(HistogramBins - 1));
                }
            }
            return XForceAbsoluteSafetyLimit;
        }

        std::array<Sample, WindowSamples> samples_{};
        std::array<std::uint64_t, HistogramBins> histogram_{};
        std::size_t writeIndex_ = 0;
        std::size_t count_ = 0;
        std::uint64_t totalSamples_ = 0;
        float maxAbs_ = 0.0f;
        bool previousValid_ = false;
        float previousRaw_ = 0.0f;
        float previousSteer_ = 0.0f;
        float previousFrontSlip_ = 0.0f;
        float previousYawRate_ = 0.0f;
        float frozenSeconds_ = 0.0f;
    };

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
