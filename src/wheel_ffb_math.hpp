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
    // A candidate must first exceed the normalization noise floor by a
    // meaningful margin before it can prove that the native source is alive.
    // Once armed, true zero crossings remain valid for the timed grace period.
    inline constexpr float XForceResponseThreshold = 0.50f;
    inline constexpr float XForceNearZeroThreshold = 0.25f;
    inline constexpr float XForceStoppedSpeed = 0.025f;
    inline constexpr float XForceResumeSpeed = 0.040f;
    // A post-stop value must move at least one near-zero/noise-band unit before
    // a non-zero native source can be trusted again. This prevents sub-noise
    // jitter from certifying a stale actionforce_DBC sample as fresh.
    inline constexpr float XForceFreshDelta = 0.25f;
    inline constexpr float XForceUnresponsiveSeconds = 0.50f;
    inline constexpr float XForceBlendInSeconds = 0.20f;
    inline constexpr float XForceBlendOutSeconds = 0.10f;
    inline constexpr float XForceFreezeWindowSeconds = 0.20f;
    inline constexpr float XForceFrozenFallbackSeconds = 0.50f;

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
            baselineCaptured_ = false;
            stoppedRaw_ = 0.0f;
            lastNormalized_ = 0.0f;
            nativeBlend_ = 0.0f;
            unresponsiveSeconds_ = 0.0f;
        }

        XForceGuardSample update(
            float raw, float speedNorm, float steerAbs, bool invert,
            float deltaSeconds = 1.0f / 60.0f,
            bool sourceFrozen = false)
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
            // A real stop is also a trust boundary: a future launch must prove
            // freshness again rather than inheriting old session state.
            if (stopped_)
            {
                if (speedNorm < XForceResumeSpeed)
                {
                    if (out.rangeValid)
                    {
                        stoppedRaw_ = raw;
                        baselineCaptured_ = true;
                    }
                    else
                    {
                        // Invalid data at rest is still a hard trust fault. Do
                        // not retain a pre-fault stopped baseline into launch.
                        stoppedRaw_ = 0.0f;
                        baselineCaptured_ = false;
                    }
                    awaitingFreshAfterStop_ = true;
                    responseObserved_ = false;
                    nativeBlend_ = 0.0f;
                    lastNormalized_ = 0.0f;
                    unresponsiveSeconds_ = 0.0f;
                    out.responseObserved = false;
                    out.stopped = true;
                    return out;
                }

                // reset_signal_state() can run while the car is already
                // moving (for example after closing F11). In that case the
                // first moving native sample is only a baseline; it must not
                // certify its own freshness in the same frame.
                if (!baselineCaptured_)
                {
                    if (out.rangeValid)
                    {
                        stoppedRaw_ = raw;
                        baselineCaptured_ = true;
                    }
                    responseObserved_ = false;
                    nativeBlend_ = 0.0f;
                    lastNormalized_ = 0.0f;
                    unresponsiveSeconds_ = 0.0f;
                    out.responseObserved = false;
                    out.stopped = false;
                    return out;
                }

                stopped_ = false;
                awaitingFreshAfterStop_ = true;
            }
            else if (speedNorm <= XForceStoppedSpeed)
            {
                stopped_ = true;
                awaitingFreshAfterStop_ = true;
                baselineCaptured_ = false;
                if (out.rangeValid)
                {
                    stoppedRaw_ = raw;
                    baselineCaptured_ = true;
                }
                responseObserved_ = false;
                nativeBlend_ = 0.0f;
                lastNormalized_ = 0.0f;
                unresponsiveSeconds_ = 0.0f;
                out.responseObserved = false;
                out.stopped = true;
                return out;
            }

            const float motionGate = smoothstep01(
                (speedNorm - XForceResumeSpeed) / 0.12f);

            // NaN/Inf or an implausible magnitude is not an ordinary zero
            // crossing. Fail closed immediately and require a new moving
            // baseline before native torque may arm again. The downstream
            // structural slew limiter still smooths the physical wheel output.
            if (!out.rangeValid)
            {
                responseObserved_ = false;
                stopped_ = true;
                awaitingFreshAfterStop_ = true;
                baselineCaptured_ = false;
                nativeBlend_ = 0.0f;
                lastNormalized_ = 0.0f;
                unresponsiveSeconds_ = 0.0f;
                out.responseObserved = false;
                out.responsive = false;
                out.freshAfterStop = false;
                out.valid = false;
                out.stopped = false;
                out.normalized = 0.0f;
                out.motionGate = motionGate;
                out.nativeBlend = 0.0f;
                out.unresponsiveSeconds = 0.0f;
                return out;
            }

            // The analyzer observes signed steering, front slip and yaw over a
            // short time window. A confirmed non-zero freeze is therefore a
            // hard source fault, not something that should replay last torque
            // during the normal 100 ms crossfade. Force a fresh-baseline cycle.
            if (sourceFrozen)
            {
                responseObserved_ = false;
                stopped_ = true;
                awaitingFreshAfterStop_ = true;
                baselineCaptured_ = false;
                nativeBlend_ = 0.0f;
                lastNormalized_ = 0.0f;
                unresponsiveSeconds_ = 0.0f;
                out.responseObserved = false;
                out.responsive = false;
                out.freshAfterStop = false;
                out.valid = false;
                out.stopped = false;
                out.normalized = 0.0f;
                out.motionGate = motionGate;
                out.nativeBlend = 0.0f;
                out.unresponsiveSeconds = 0.0f;
                return out;
            }

            // Freshness is a prerequisite for liveness. A stale non-zero stop
            // value must never set responseObserved_ before it has changed.
            if (awaitingFreshAfterStop_ &&
                (std::abs(raw) < XForceNearZeroThreshold ||
                 std::abs(raw - stoppedRaw_) >= XForceFreshDelta))
            {
                awaitingFreshAfterStop_ = false;
            }

            if (!awaitingFreshAfterStop_ && steerAbs >= 0.05f &&
                std::abs(raw) >= XForceResponseThreshold)
            {
                responseObserved_ = true;
            }

            // A true zero crossing is allowed. Only call the candidate dead
            // after about half a second of near-zero output while the driver is
            // clearly steering a moving car. The timer is cadence-independent.
            if (steerAbs >= 0.15f && speedNorm >= 0.08f)
            {
                if (std::abs(raw) < XForceNearZeroThreshold)
                    unresponsiveSeconds_ = std::min(
                        XForceUnresponsiveSeconds, unresponsiveSeconds_ + deltaSeconds);
                else
                    unresponsiveSeconds_ = 0.0f;
            }
            else
            {
                unresponsiveSeconds_ = 0.0f;
            }

            // A confirmed dead source must not carry old session trust into a
            // later sample. A subsequent non-zero sample can prove liveness again.
            if (unresponsiveSeconds_ >= XForceUnresponsiveSeconds)
                responseObserved_ = false;

            const bool responsiveNow = responseObserved_ &&
                unresponsiveSeconds_ < XForceUnresponsiveSeconds &&
                !sourceFrozen;

            float currentNormalized = 0.0f;
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
            out.motionGate = motionGate;
            out.nativeBlend = nativeBlend_;
            out.unresponsiveSeconds = unresponsiveSeconds_;
            return out;
        }

    private:
        bool responseObserved_ = false;
        bool stopped_ = true;
        bool awaitingFreshAfterStop_ = true;
        bool baselineCaptured_ = false;
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
    // Confidence and freeze detection are evidence outputs; frozenSuspicious is
    // also consumed by XForceGuard as a fail-closed safety input.
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
            freezeWindowValid_ = false;
            freezeWindowRaw_ = 0.0f;
            freezeWindowSteer_ = 0.0f;
            freezeWindowFrontSlip_ = 0.0f;
            freezeWindowYawRate_ = 0.0f;
            freezeWindowSeconds_ = 0.0f;
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
                freezeWindowValid_ = false;
                freezeWindowSeconds_ = 0.0f;
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

            if (speedNorm >= 0.08f && absRaw >= XForceResponseThreshold)
            {
                if (!freezeWindowValid_)
                {
                    freezeWindowValid_ = true;
                    freezeWindowRaw_ = raw;
                    freezeWindowSteer_ = steer;
                    freezeWindowFrontSlip_ = frontSlip;
                    freezeWindowYawRate_ = yawRate;
                    freezeWindowSeconds_ = 0.0f;
                }
                else
                {
                    freezeWindowSeconds_ += deltaSeconds;
                    if (freezeWindowSeconds_ >= XForceFreezeWindowSeconds)
                    {
                        // Compare over a short window instead of one frame so
                        // ordinary smooth steering/body motion can still prove
                        // that a non-zero native value is suspiciously frozen.
                        const bool stateChanged =
                            std::abs(steer - freezeWindowSteer_) >= 0.025f ||
                            std::abs(frontSlip - freezeWindowFrontSlip_) >= 0.005f ||
                            std::abs(yawRate - freezeWindowYawRate_) >= 0.020f;
                        const bool rawFrozen =
                            std::abs(raw - freezeWindowRaw_) < 0.010f;
                        if (stateChanged && rawFrozen)
                            frozenSeconds_ += freezeWindowSeconds_;
                        else
                            frozenSeconds_ = std::max(
                                0.0f, frozenSeconds_ - freezeWindowSeconds_ * 2.0f);

                        freezeWindowRaw_ = raw;
                        freezeWindowSteer_ = steer;
                        freezeWindowFrontSlip_ = frontSlip;
                        freezeWindowYawRate_ = yawRate;
                        freezeWindowSeconds_ = 0.0f;
                    }
                }
            }
            else
            {
                freezeWindowValid_ = false;
                freezeWindowSeconds_ = 0.0f;
                frozenSeconds_ = std::max(0.0f, frozenSeconds_ - deltaSeconds);
            }
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
            out.frozenSuspicious =
                frozenSeconds_ >= XForceFrozenFallbackSeconds;
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
        bool freezeWindowValid_ = false;
        float freezeWindowRaw_ = 0.0f;
        float freezeWindowSteer_ = 0.0f;
        float freezeWindowFrontSlip_ = 0.0f;
        float freezeWindowYawRate_ = 0.0f;
        float freezeWindowSeconds_ = 0.0f;
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

    inline float native_oversteer_band(float normalizedRearSlip)
    {
        // rFuktor-inspired rear-slip cue: arrive around the tyre's peak-slip
        // region, stay strong through the useful catch window, then fade again
        // in a very large slide so a DD wheel does not keep winding itself up.
        if (!std::isfinite(normalizedRearSlip))
            return 0.0f;

        const float x = std::abs(normalizedRearSlip);
        constexpr float RiseStart = 0.85f;
        constexpr float RiseEnd = 1.15f;
        constexpr float FallStart = 1.45f;
        constexpr float FallEnd = 2.25f;

        const auto smooth01 = [](float t)
        {
            t = std::clamp(t, 0.0f, 1.0f);
            return t * t * (3.0f - 2.0f * t);
        };

        const float rise = smooth01((x - RiseStart) / (RiseEnd - RiseStart));
        const float fall = 1.0f - smooth01((x - FallStart) / (FallEnd - FallStart));
        return std::clamp(rise * fall, 0.0f, 1.0f);
    }

    inline float native_oversteer_direction(float rearSlipRad, bool invert)
    {
        // MOZA R3 hardware validation established that the canonical rear EE
        // sign must be preserved here. The old implementation negated it and
        // therefore required the UI "Reverse" switch for correct counter-steer.
        if (!std::isfinite(rearSlipRad))
            return 0.0f;
        float direction =
            rearSlipRad > 0.0f ? 1.0f :
            (rearSlipRad < 0.0f ? -1.0f : 0.0f);
        return invert ? -direction : direction;
    }

    inline float native_oversteer_headroom(float baseTorque)
    {
        // The rear cue is supplemental steering information. Reduce its share
        // as front/base SAT approaches full scale so a drift transition does
        // not pile a large additive kick on top of an already heavy wheel.
        if (!std::isfinite(baseTorque))
            return 0.0f;
        const float occupied = std::clamp(std::abs(baseTorque), 0.0f, 1.0f);
        return std::clamp(1.0f - 0.65f * occupied, 0.35f, 1.0f);
    }

    inline float drift_regrip_shape(float recovery)
    {
        if (!std::isfinite(recovery))
            return 0.0f;
        const float t = std::clamp(recovery, 0.0f, 1.0f);
        return t * t * (3.0f - 2.0f * t);
    }

    inline float drift_regrip_sat_scale(float recovery)
    {
        // A recovered rear axle can make the front-slip SAT estimate change sign
        // several times while the car straightens. Keep the rack informative but
        // temporarily reduce the new grip torque so a DD base does not ping-pong.
        return 1.0f - 0.45f * drift_regrip_shape(recovery);
    }

    inline float drift_regrip_damper_boost(float recovery)
    {
        // Brief extra damping controls wheel velocity during the same transition.
        // It fades completely once the car has settled, so sustained drift stays
        // free enough for natural counter-steer.
        return 0.12f * drift_regrip_shape(recovery);
    }

    inline float drift_regrip_build_scale(float recovery)
    {
        // Releasing stale torque remains fast. Only rebuilding the next sign is
        // slowed during re-grip, preventing repeated full-strength sign swaps.
        return 1.0f - 0.35f * drift_regrip_shape(recovery);
    }

    class DriftRegripGuard
    {
    public:
        float update(float bodySlide, float deltaSeconds)
        {
            if (!std::isfinite(bodySlide) || !std::isfinite(deltaSeconds) ||
                deltaSeconds <= 0.0f)
            {
                reset();
                return 0.0f;
            }

            const float slide = std::clamp(bodySlide, 0.0f, 1.0f);

            // Hysteresis: a real drift must first be established before a
            // low-slide sample can start the recovery envelope.
            if (slide >= 0.65f)
            {
                driftArmed_ = true;
                recovery_ = 0.0f;
            }
            else if (driftArmed_ && slide <= 0.25f)
            {
                driftArmed_ = false;
                recovery_ = 1.0f;
            }
            else if (recovery_ > 0.0f)
            {
                constexpr float RecoverySeconds = 0.45f;
                recovery_ = std::max(
                    0.0f, recovery_ - deltaSeconds / RecoverySeconds);
            }

            return recovery_;
        }

        void reset()
        {
            driftArmed_ = false;
            recovery_ = 0.0f;
        }

        bool drift_armed() const { return driftArmed_; }
        float recovery() const { return recovery_; }

    private:
        bool driftArmed_ = false;
        float recovery_ = 0.0f;
    };

    struct SurfaceWheelSignal
    {
        std::uint32_t materialMask = 0;
        float compressionRate = 0.0f;
        float normalLoad = 0.0f;
        float referenceLoad = 0.0f;
        bool valid = false;
    };

    struct SurfaceHapticsOutput
    {
        bool valid = false;
        float texture = 0.0f;
        float impact = 0.0f;
        float maxLoadDelta = 0.0f;
        float maxRateSpike = 0.0f;
        unsigned materialChanges = 0;
        unsigned validWheels = 0;
    };

    class SurfaceHapticsModel
    {
    public:
        SurfaceHapticsOutput update(
            const std::array<SurfaceWheelSignal, 4>& wheel,
            float deltaSeconds)
        {
            SurfaceHapticsOutput out{};
            if (!std::isfinite(deltaSeconds) || deltaSeconds <= 0.0f)
            {
                reset();
                return out;
            }

            float textureSum = 0.0f;
            float strongestImpact = 0.0f;

            for (std::size_t i = 0; i < wheel.size(); ++i)
            {
                const auto& in = wheel[i];
                const float refLoad = std::abs(in.referenceLoad);
                if (!in.valid ||
                    !std::isfinite(in.compressionRate) ||
                    !std::isfinite(in.normalLoad) ||
                    !std::isfinite(refLoad) ||
                    refLoad <= 1.0e-5f)
                {
                    continue;
                }

                ++out.validWheels;
                const float loadRatio = in.normalLoad / refLoad;
                if (!std::isfinite(loadRatio))
                    continue;

                const float rateAbs = std::abs(in.compressionRate);
                if (!initialized_[i])
                {
                    initialized_[i] = true;
                    previousMaterial_[i] = in.materialMask;
                    previousLoadRatio_[i] = loadRatio;
                    rateBaseline_[i] = std::max(rateAbs, 1.0e-5f);
                    continue;
                }

                const float loadDelta =
                    std::abs(loadRatio - previousLoadRatio_[i]);
                out.maxLoadDelta = std::max(out.maxLoadDelta, loadDelta);

                const float baseline =
                    std::max(rateBaseline_[i], 1.0e-5f);
                const float cappedForBaseline =
                    std::min(rateAbs, baseline * 2.5f + 0.0010f);
                rateBaseline_[i] +=
                    (cappedForBaseline - rateBaseline_[i]) * 0.035f;

                // Continuous road texture follows real suspension activity, not
                // a material->roughness lookup. Keep it intentionally small:
                // a full-time brick/stone road should be texture, not a curb.
                const float normalizedRate =
                    rateAbs / (rateAbs + baseline * 6.0f + 0.0015f);
                const float normalizedLoadMotion =
                    std::clamp(loadDelta / 0.10f, 0.0f, 1.0f);
                const float wheelTexture = std::clamp(
                    0.65f * normalizedRate +
                    0.35f * normalizedLoadMotion,
                    0.0f, 1.0f);
                textureSum += wheelTexture;

                // A curb/bump is a physical impulse. A material transition only
                // boosts a real suspension/load event; it can never create a
                // hit by itself.
                const bool materialChanged =
                    previousMaterial_[i] != 0 &&
                    in.materialMask != 0 &&
                    previousMaterial_[i] != in.materialMask;
                if (materialChanged)
                    ++out.materialChanges;

                const float excessRate = std::max(
                    0.0f,
                    rateAbs - (baseline * 2.5f + 0.0010f));
                const float rateSpike = std::clamp(
                    excessRate / (baseline * 6.0f + 0.0020f),
                    0.0f, 1.0f);
                out.maxRateSpike = std::max(out.maxRateSpike, rateSpike);

                const float loadImpulse = smoothstep01(
                    (loadDelta - 0.06f) / 0.34f);
                float physicalImpact = std::max(
                    loadImpulse,
                    rateSpike * 0.80f);

                if (materialChanged && physicalImpact > 0.08f)
                    physicalImpact = std::min(
                        1.0f,
                        physicalImpact * 1.15f + 0.08f);

                strongestImpact =
                    std::max(strongestImpact, physicalImpact);

                previousMaterial_[i] = in.materialMask;
                previousLoadRatio_[i] = loadRatio;
            }

            if (out.validWheels == 0)
            {
                reset();
                return out;
            }

            // Average all valid wheels instead of max(). The 0.12 ceiling is
            // deliberate: continuous texture must remain subtle even when all
            // four tyres are on a rough brick/stone material.
            const float meanTexture =
                textureSum / static_cast<float>(out.validWheels);
            out.texture = std::clamp(meanTexture * 0.12f, 0.0f, 0.12f);

            if (strongestImpact > impactEnvelope_)
                impactEnvelope_ = strongestImpact;
            else
            {
                constexpr float ImpactReleaseSeconds = 0.14f;
                impactEnvelope_ = std::max(
                    0.0f,
                    impactEnvelope_ - deltaSeconds / ImpactReleaseSeconds);
            }

            out.impact = std::clamp(impactEnvelope_, 0.0f, 1.0f);
            out.valid = true;
            return out;
        }

        void reset()
        {
            initialized_.fill(false);
            previousMaterial_.fill(0);
            previousLoadRatio_.fill(0.0f);
            rateBaseline_.fill(0.0f);
            impactEnvelope_ = 0.0f;
        }

    private:
        std::array<bool, 4> initialized_{};
        std::array<std::uint32_t, 4> previousMaterial_{};
        std::array<float, 4> previousLoadRatio_{};
        std::array<float, 4> rateBaseline_{};
        float impactEnvelope_ = 0.0f;
    };

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
