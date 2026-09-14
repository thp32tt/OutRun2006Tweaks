from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def write(rel, text):
    path = ROOT / rel
    with path.open('w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, got {count}')
    return text.replace(old, new, 1)


def replace_all_exact(text, old, new, expected, label):
    count = text.count(old)
    if count != expected:
        raise SystemExit(f'{label}: expected {expected} matches, got {count}')
    return text.replace(old, new)


# ---------------------------------------------------------------------------
# wheel_ffb_math.hpp: time-based guard + diagnostic analyzer
# ---------------------------------------------------------------------------
rel = 'src/wheel_ffb_math.hpp'
text = read(rel)
if '#include <cstdint>' not in text:
    text = text.replace('#include <cmath>\n', '#include <cmath>\n#include <cstdint>\n', 1)
start = text.index('    // Guarded native steering-force candidate for v0.3.')
end = text.index('    struct XForceMixResult', start)
new_guard = r'''    // Guarded native steering-force candidate for v0.3. actionforce_DBC is
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

'''
text = text[:start] + new_guard + text[end:]
marker = '    // Symmetric C1 soft limiter. Preserve low/mid-range force exactly, then\n'
analyzer = r'''
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
                    std::abs(frontSlip - previousFrontSlip_) >= 0.015f ||
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

'''
text = replace_once(text, marker, analyzer + marker, 'insert X-Force analyzer')
write(rel, text)


# ---------------------------------------------------------------------------
# runtime snapshot API
# ---------------------------------------------------------------------------
rel = 'src/wheel_ffb_runtime.hpp'
text = read(rel).replace('\r\n', '\n').replace('\r', '\n')
insert = r'''
struct WheelFFBXForceAnalysisSnapshot
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

'''
text = replace_once(text, 'void WheelFFB_RequestDirectionTest(int direction);\n', insert + 'void WheelFFB_RequestDirectionTest(int direction);\n', 'runtime analysis struct')
text = replace_once(text, 'WheelFFBGraphSnapshot WheelFFB_GetGraphSnapshot();\n', 'WheelFFBGraphSnapshot WheelFFB_GetGraphSnapshot();\nWheelFFBXForceAnalysisSnapshot WheelFFB_GetXForceAnalysisSnapshot();\n', 'runtime analysis accessor')
write(rel, text)


# ---------------------------------------------------------------------------
# core FFB engine
# ---------------------------------------------------------------------------
rel = 'src/hooks_wheel_ffb.cpp'
text = read(rel)
old = r'''    Setting<bool> WheelFFBXForceInvert{
        "WheelFFB", "XForceInvert", false,
        "Reverse only the native X-Force candidate before it is mixed with Modern SAT."
    };
'''
new = old + r'''
    Setting<float> WheelFFBXForceGain{
        "WheelFFB", "XForceGain", 1.00f,
        "Native X-Force candidate gain after normalization. Default 1.0; keep conservative until actionforce_DBC is proven.",
        Range<float>{ 0.0f, 2.0f }
    };

    Setting<bool> WheelFFBXForceCapture60Hz{
        "WheelFFB", "XForceCapture60Hz", false,
        "Very verbose 60 Hz X-Force validation capture in OutRun2006Tweaks.log. Diagnostic only; does not alter force selection."
    };
'''
text = replace_once(text, old, new, 'core X-Force settings')

old = r'''            const float xForceRaw = car->actionforce_DBC;
            const WheelFFBMath::XForceGuardSample xForceSample = xForceGuard_.update(
                xForceRaw, speedNorm, steerAbs, bool(Settings::WheelFFBXForceInvert));
            const float nativeXForceTorque =
                xForceSample.normalized * xForceSample.motionGate * satStrength;

            const int feedbackCharacter = std::clamp(
                static_cast<int>(Settings::WheelFFBFeedbackCharacter), 0, 2);
            const float configuredXForceMix =
                static_cast<float>(Settings::WheelFFBXForceMix);
            const float xForceMix = std::isfinite(configuredXForceMix)
                ? std::clamp(configuredXForceMix, 0.0f, 1.0f)
                : 0.50f;
            const WheelFFBMath::XForceMixResult xForceMixResult =
                WheelFFBMath::mix_xforce_character(
                    modernSelfAligningTorque, nativeXForceTorque,
                    feedbackCharacter, xForceMix, xForceSample.nativeBlend);
            const float selfAligningTorque = xForceMixResult.torque;
'''
new = r'''            const DWORD xForceNow = GetTickCount();
            float xForceDeltaSeconds = 1.0f / 60.0f;
            if (lastXForceFrameTick_ != 0)
            {
                xForceDeltaSeconds = std::clamp(
                    static_cast<float>(xForceNow - lastXForceFrameTick_) / 1000.0f,
                    1.0f / 240.0f, 0.10f);
            }
            lastXForceFrameTick_ = xForceNow;

            const float xForceRaw = car->actionforce_DBC;
            const WheelFFBMath::XForceGuardSample xForceSample = xForceGuard_.update(
                xForceRaw, speedNorm, steerAbs, bool(Settings::WheelFFBXForceInvert),
                xForceDeltaSeconds);

            const float configuredXForceMix = std::isfinite(
                    static_cast<float>(Settings::WheelFFBXForceMix))
                ? std::clamp(static_cast<float>(Settings::WheelFFBXForceMix), 0.0f, 1.0f)
                : 0.50f;
            const float configuredXForceGain = std::isfinite(
                    static_cast<float>(Settings::WheelFFBXForceGain))
                ? std::clamp(static_cast<float>(Settings::WheelFFBXForceGain), 0.0f, 2.0f)
                : 1.00f;
            const float tuneAlpha = 1.0f - std::exp(
                -xForceDeltaSeconds / 0.12f);
            if (smoothedXForceMix_ < 0.0f)
                smoothedXForceMix_ = configuredXForceMix;
            else
                smoothedXForceMix_ +=
                    (configuredXForceMix - smoothedXForceMix_) * tuneAlpha;
            if (smoothedXForceGain_ < 0.0f)
                smoothedXForceGain_ = configuredXForceGain;
            else
                smoothedXForceGain_ +=
                    (configuredXForceGain - smoothedXForceGain_) * tuneAlpha;

            const float nativeXForceTorque =
                xForceSample.normalized * xForceSample.motionGate * satStrength *
                smoothedXForceGain_;

            xForceAnalyzer_.update(
                xForceRaw, speedNorm, steer, modernSelfAligningTorque,
                frontSlip, vehicleDynamics_.yawRate(), xForceDeltaSeconds);
            const WheelFFBMath::XForceAnalysisSnapshot xForceAnalysis =
                xForceAnalyzer_.snapshot();

            const int feedbackCharacter = std::clamp(
                static_cast<int>(Settings::WheelFFBFeedbackCharacter), 0, 2);
            const float xForceMix = std::clamp(smoothedXForceMix_, 0.0f, 1.0f);
            const WheelFFBMath::XForceMixResult xForceMixResult =
                WheelFFBMath::mix_xforce_character(
                    modernSelfAligningTorque, nativeXForceTorque,
                    feedbackCharacter, xForceMix, xForceSample.nativeBlend);
            const float selfAligningTorque = xForceMixResult.torque;
'''
text = replace_once(text, old, new, 'core guarded X-Force path')

needle = r'''            record_graph_sample(
                total,
                compressed,
                static_cast<float>(structuralLevel) / static_cast<float>(DI_FFNOMINALMAX),
                static_cast<float>(level) / static_cast<float>(DI_FFNOMINALMAX),
                xForceSample.normalized, modernSelfAligningTorque,
                nativeXForceTorque, xForceMixResult.nativeShare);

'''
addition = needle + r'''            if (Settings::WheelFFBXForceCapture60Hz)
            {
                spdlog::info(
                    "WheelFFB XFORCE60 tick={} t={} dt={} raw={} speed={} steer={} frontSlip={} yaw={} modern={} native={} finalSat={} normalized={} valid={} blend={} share={} gain={} mix={} confidence={} corrSteer={} corrModern={} corrFront={} corrYaw={} frozen={} frozenSec={} p50={} p90={} p95={} p99={} max={}",
                    updateCounter_, xForceNow, xForceDeltaSeconds, xForceRaw,
                    speedNorm, steer, frontSlip, vehicleDynamics_.yawRate(),
                    modernSelfAligningTorque, nativeXForceTorque, selfAligningTorque,
                    xForceSample.normalized, xForceSample.valid,
                    xForceSample.nativeBlend, xForceMixResult.nativeShare,
                    smoothedXForceGain_, xForceMix, xForceAnalysis.confidence,
                    xForceAnalysis.corrSteer, xForceAnalysis.corrModernSat,
                    xForceAnalysis.corrFrontSlip, xForceAnalysis.corrYawRate,
                    xForceAnalysis.frozenSuspicious, xForceAnalysis.frozenSeconds,
                    xForceAnalysis.p50Abs, xForceAnalysis.p90Abs,
                    xForceAnalysis.p95Abs, xForceAnalysis.p99Abs,
                    xForceAnalysis.maxAbs);
            }

'''
text = replace_once(text, needle, addition, '60 Hz capture')

marker = r'''                spdlog::info(
                    "WheelFFB SATMODEL t={} rawBodySlip={} bodySlip={} bodyBlend={} rawYawRate={} yawRate={} yawBlend={} rawFrontSlip={} frontSlip={} frontBlend={} trailResponseSlip={} trailResponseLead={} fyShape={} pneumaticTrail={} pneumaticShape={} mechanicalMix={} mechanicalContribution={} combinedShape={} diPreResponse={} diCorrected={} responseCorrection={}",
'''
analysis_log = r'''                spdlog::info(
                    "WheelFFB XFORCE ANALYSIS t={} samples={} confidence={} corrSteer={} corrModern={} corrFront={} corrYaw={} frozen={} frozenSec={} p50={} p90={} p95={} p99={} max={} gain={}",
                    telemetryNow, xForceAnalysis.samples, xForceAnalysis.confidence,
                    xForceAnalysis.corrSteer, xForceAnalysis.corrModernSat,
                    xForceAnalysis.corrFrontSlip, xForceAnalysis.corrYawRate,
                    xForceAnalysis.frozenSuspicious, xForceAnalysis.frozenSeconds,
                    xForceAnalysis.p50Abs, xForceAnalysis.p90Abs,
                    xForceAnalysis.p95Abs, xForceAnalysis.p99Abs,
                    xForceAnalysis.maxAbs, smoothedXForceGain_);
'''
text = replace_once(text, marker, analysis_log + marker, '10 Hz X-Force analysis summary')

old = r'''            xForceGuard_.reset();
            prevStructuralLevel_ = 0;
'''
new = r'''            xForceGuard_.reset();
            xForceAnalyzer_.reset();
            lastXForceFrameTick_ = 0;
            smoothedXForceMix_ = -1.0f;
            smoothedXForceGain_ = -1.0f;
            prevStructuralLevel_ = 0;
'''
text = replace_once(text, old, new, 'reset X-Force diagnostic state')

marker = '        void reset_headroom_stats()\n'
method = r'''        WheelFFBXForceAnalysisSnapshot xforce_analysis_snapshot() const
        {
            const WheelFFBMath::XForceAnalysisSnapshot source = xForceAnalyzer_.snapshot();
            WheelFFBXForceAnalysisSnapshot out{};
            out.samples = source.samples;
            out.corrSteer = source.corrSteer;
            out.corrModernSat = source.corrModernSat;
            out.corrFrontSlip = source.corrFrontSlip;
            out.corrYawRate = source.corrYawRate;
            out.confidence = source.confidence;
            out.frozenSuspicious = source.frozenSuspicious;
            out.frozenSeconds = source.frozenSeconds;
            out.p50Abs = source.p50Abs;
            out.p90Abs = source.p90Abs;
            out.p95Abs = source.p95Abs;
            out.p99Abs = source.p99Abs;
            out.maxAbs = source.maxAbs;
            return out;
        }

'''
text = replace_once(text, marker, method + marker, 'analysis runtime method')

text = replace_once(text, '        DWORD lastTelemetryTick_ = 0;\n', '        DWORD lastTelemetryTick_ = 0;\n        DWORD lastXForceFrameTick_ = 0;\n', 'X-Force frame clock member')
text = replace_once(text, '        WheelFFBMath::XForceGuard xForceGuard_{};\n', '        WheelFFBMath::XForceGuard xForceGuard_{};\n        WheelFFBMath::XForceSignalAnalyzer xForceAnalyzer_{};\n', 'X-Force analyzer member')
text = replace_once(text, '        float smoothedLongAccel_ = 0.0f;\n', '        float smoothedLongAccel_ = 0.0f;\n        float smoothedXForceMix_ = -1.0f;\n        float smoothedXForceGain_ = -1.0f;\n', 'smoothed native controls')

old = r'''WheelFFBGraphSnapshot WheelFFB_GetGraphSnapshot()
{
    return gWheelFFB.graph_snapshot();
}

'''
new = old + r'''WheelFFBXForceAnalysisSnapshot WheelFFB_GetXForceAnalysisSnapshot()
{
    return gWheelFFB.xforce_analysis_snapshot();
}

'''
text = replace_once(text, old, new, 'runtime analysis export')
write(rel, text)


# ---------------------------------------------------------------------------
# F11 UI: diagnostics, native gain, capture, revert state
# ---------------------------------------------------------------------------
rel = 'src/overlay/wheel_setup_ui.cpp'
text = read(rel)
text = replace_once(text, '    extern Setting<bool> WheelFFBXForceInvert;\n', '    extern Setting<bool> WheelFFBXForceInvert;\n    extern Setting<float> WheelFFBXForceGain;\n    extern Setting<bool> WheelFFBXForceCapture60Hz;\n', 'UI X-Force externs')
text = replace_once(text, '            bool xForceInvert = false;\n', '            bool xForceInvert = false;\n            float xForceGain = 1.00f;\n            bool xForceCapture60Hz = false;\n', 'saved X-Force fields')
text = replace_once(text, '            savedFfb_.xForceInvert = Settings::WheelFFBXForceInvert;\n', '            savedFfb_.xForceInvert = Settings::WheelFFBXForceInvert;\n            savedFfb_.xForceGain = Settings::WheelFFBXForceGain;\n            savedFfb_.xForceCapture60Hz = Settings::WheelFFBXForceCapture60Hz;\n', 'capture X-Force fields')
text = replace_once(text, '            Settings::WheelFFBXForceInvert = savedFfb_.xForceInvert;\n', '            Settings::WheelFFBXForceInvert = savedFfb_.xForceInvert;\n            Settings::WheelFFBXForceGain = savedFfb_.xForceGain;\n            Settings::WheelFFBXForceCapture60Hz = savedFfb_.xForceCapture60Hz;\n', 'restore X-Force fields')

needle = r'''            if (feedbackCharacter != 0)
                ImGui::TextColored(ImVec4(1.0f, 0.75f, 0.25f, 1.0f),
                    "Experimental: actionforce_DBC is a strong X-Force candidate, not yet proven. Enable telemetry before judging the native signal.");

'''
new = needle + r'''            if (feedbackCharacter != 0)
            {
                const WheelFFBXForceAnalysisSnapshot xAnalysis =
                    WheelFFB_GetXForceAnalysisSnapshot();
                ImGui::Text("X-Force signal confidence: %.0f%%  samples: %llu",
                    xAnalysis.confidence * 100.0f,
                    static_cast<unsigned long long>(xAnalysis.samples));
                ImGui::TextDisabled(
                    "corr steer %.2f | Modern %.2f | front slip %.2f | yaw %.2f",
                    xAnalysis.corrSteer, xAnalysis.corrModernSat,
                    xAnalysis.corrFrontSlip, xAnalysis.corrYawRate);
                ImGui::TextDisabled(
                    "|raw| P50 %.1f  P90 %.1f  P95 %.1f  P99 %.1f  max %.1f",
                    xAnalysis.p50Abs, xAnalysis.p90Abs, xAnalysis.p95Abs,
                    xAnalysis.p99Abs, xAnalysis.maxAbs);
                if (xAnalysis.frozenSuspicious)
                    ImGui::TextColored(ImVec4(1.0f, 0.45f, 0.25f, 1.0f),
                        "Diagnostic: X-Force stayed fixed while vehicle/steering state changed (%.2fs). This does not auto-disable torque yet.",
                        xAnalysis.frozenSeconds);
            }

'''
text = replace_once(text, needle, new, 'X-Force analysis UI')

needle = r'''                    if (ImGui::IsItemHovered())
                        ImGui::SetTooltip("Use this only if Arcade/Hybrid steering force is reversed relative to Modern DD. Global Reverse SAT / ConstantForce still applies after the mix.");
                    if (advancedFeedbackCharacter != 2)
'''
new = r'''                    if (ImGui::IsItemHovered())
                        ImGui::SetTooltip("Use this only if Arcade/Hybrid steering force is reversed relative to Modern DD. Global Reverse SAT / ConstantForce still applies after the mix.");
                    track_ffb_change(ImGui::SliderFloat("Native X-Force Gain", Settings::WheelFFBXForceGain.ptr(), 0.0f, 2.0f, "%.2f"));
                    if (ImGui::IsItemHovered())
                        ImGui::SetTooltip("Post-normalization gain for the native candidate. Default 1.00. Live changes are smoothed; keep conservative until the source signal is proven.");
                    if (advancedFeedbackCharacter != 2)
'''
text = replace_once(text, needle, new, 'native gain UI')

needle = r'''            track_ffb_change(ImGui::Checkbox("Diagnostic logging", Settings::WheelFFBDebugLog.ptr()));
            track_ffb_change(ImGui::Checkbox("Record driving telemetry (10 Hz)", Settings::WheelFFBTelemetry.ptr()));
'''
new = needle + r'''            track_ffb_change(ImGui::Checkbox("Capture X-Force validation at 60 Hz (very verbose)", Settings::WheelFFBXForceCapture60Hz.ptr()));
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Writes one WheelFFB XFORCE60 line every physics update for short validation runs. This is diagnostic only and can grow the log quickly.");
'''
text = replace_once(text, needle, new, '60 Hz capture UI')

preset = r'''                Settings::WheelFFBFeedbackCharacter = 0;
                Settings::WheelFFBXForceMix = 0.50f;
                Settings::WheelFFBXForceInvert = false;
                Settings::WheelFFBGlobalStrength = 0.70f;
'''
preset_new = r'''                Settings::WheelFFBFeedbackCharacter = 0;
                Settings::WheelFFBXForceMix = 0.50f;
                Settings::WheelFFBXForceInvert = false;
                Settings::WheelFFBXForceGain = 1.00f;
                Settings::WheelFFBGlobalStrength = 0.70f;
'''
text = replace_all_exact(text, preset, preset_new, 2, 'UI presets native gain')
write(rel, text)


# ---------------------------------------------------------------------------
# named profile compatibility
# ---------------------------------------------------------------------------
rel = 'src/wheel_profile_store.hpp'
text = read(rel).replace('\r\n', '\n').replace('\r', '\n')
text = replace_once(text, '    extern Setting<bool> WheelFFBXForceInvert;\n', '    extern Setting<bool> WheelFFBXForceInvert;\n    extern Setting<float> WheelFFBXForceGain;\n', 'profile X-Force gain extern')
text = replace_once(text, '            key != "Telemetry" && key != "DebugLog" &&\n', '            key != "Telemetry" && key != "DebugLog" &&\n            key != "XForceCapture60Hz" &&\n', 'exclude 60 Hz diagnostics from feel profiles')
old = r'''            migrate_legacy_character(Settings::WheelFFBFeedbackCharacter, "0");
            migrate_legacy_character(Settings::WheelFFBXForceMix, "0.50");
            migrate_legacy_character(Settings::WheelFFBXForceInvert, "false");
        }

'''
new = r'''            migrate_legacy_character(Settings::WheelFFBFeedbackCharacter, "0");
            migrate_legacy_character(Settings::WheelFFBXForceMix, "0.50");
            migrate_legacy_character(Settings::WheelFFBXForceInvert, "false");
        }

        // Early v0.3 profiles predate the independent native gain. Preserve
        // their original behavior by supplying the neutral 1.00 default rather
        // than inheriting whatever live gain happened to be selected.
        if (values.find("xforcegain") == values.end())
        {
            const std::string oldValue = Settings::WheelFFBXForceGain.to_string();
            Settings::WheelFFBXForceGain.set_from_string("1.00");
            if (Settings::WheelFFBXForceGain.to_string() != oldValue)
                changed.push_back(&Settings::WheelFFBXForceGain);
        }

'''
text = replace_once(text, old, new, 'profile native gain migration')
write(rel, text)


# ---------------------------------------------------------------------------
# universal preset migration
# ---------------------------------------------------------------------------
rel = 'src/hooks_wheel_ffb_build.cpp'
text = read(rel)
old = r'''        Settings::WheelFFBFeedbackCharacter = 0;
        Settings::WheelFFBXForceMix = 0.50f;
        Settings::WheelFFBXForceInvert = false;
        Settings::WheelFFBGlobalStrength = 0.70f;
'''
new = r'''        Settings::WheelFFBFeedbackCharacter = 0;
        Settings::WheelFFBXForceMix = 0.50f;
        Settings::WheelFFBXForceInvert = false;
        Settings::WheelFFBXForceGain = 1.00f;
        Settings::WheelFFBGlobalStrength = 0.70f;
'''
text = replace_all_exact(text, old, new, 2, 'universal presets native gain')
write(rel, text)


# ---------------------------------------------------------------------------
# shipped INI defaults
# ---------------------------------------------------------------------------
rel = 'OutRun2006Tweaks.ini'
text = read(rel)
old = 'FeedbackCharacter = 0\nXForceMix = 0.50\nXForceInvert = false\n'
new = '''FeedbackCharacter = 0
XForceMix = 0.50
XForceInvert = false
; Neutral native gain. Tune only after reviewing the X-Force validation data.
XForceGain = 1.00
; Opt-in full-rate validation stream; very verbose and OFF by default.
XForceCapture60Hz = false
'''
text = replace_once(text, old, new, 'INI X-Force defaults')
write(rel, text)


# ---------------------------------------------------------------------------
# production math tests: cadence invariance + analyzer diagnostics
# ---------------------------------------------------------------------------
rel = 'tools/test_wheel_ffb_current.cpp'
text = read(rel)
start = text.index(' // v0.3 guarded native X-Force candidate.')
end = text.index(' WheelVehicleDynamics gap;', start)
new_tests = r''' // v0.3 guarded native X-Force candidate. These tests exercise the
 // production state machine, including cadence-independent timing.
 XForceGuard xg; xg.reset();
 auto xStop=xg.update(62.0f,0.0f,.5f,false);
 require(xStop.stopped&&xStop.nativeBlend==0.0f&&xStop.normalized==0.0f,"X-Force hard zero at stop");
 auto xResumeStale=xg.update(62.0f,.20f,.5f,false);
 require(!xResumeStale.valid&&xResumeStale.nativeBlend==0.0f,"X-Force stale stop value not replayed on resume");
 auto xFresh=xg.update(58.0f,.20f,.5f,false);
 require(xFresh.valid&&xFresh.freshAfterStop&&xFresh.nativeBlend>0.0f,"X-Force fresh post-stop sample arms native path");
 for(int i=0;i<14;++i)xFresh=xg.update(58.0f,.20f,.5f,false,1.0f/60.0f);
 require(xFresh.nativeBlend>.99f,"X-Force native path ramps fully in by elapsed time");
 auto xZero=xg.update(0.0f,.20f,.5f,false);
 require(xZero.valid&&xZero.responsive&&xZero.normalized==0.0f&&xZero.nativeBlend>.80f,"X-Force zero crossing stays valid after response observed");
 XForceGuard xd; xd.reset(); xd.update(0.0f,0.0f,.5f,false); xd.update(40.0f,.20f,.5f,false);
 auto xDead=xd.update(38.0f,.20f,.5f,false);
 for(int i=0;i<31;++i)xDead=xd.update(0.0f,.20f,.5f,false,1.0f/60.0f);
 require(!xDead.responsive&&!xDead.valid&&xDead.unresponsiveSeconds>=XForceUnresponsiveSeconds,"X-Force prolonged zero under steering falls back to Modern by elapsed time");
 auto xBad=xg.update(129.0f,.20f,.5f,false);
 require(!xBad.rangeValid&&!xBad.valid&&xBad.nativeBlend<xZero.nativeBlend,"X-Force out-of-range sample fades toward Modern");
 XForceGuard xi; xi.reset(); xi.update(0.0f,0.0f,.5f,true); xi.update(40.0f,.20f,.5f,true);
 auto xInvert=xi.update(38.0f,.20f,.5f,true);
 require(xInvert.valid&&xInvert.normalized<0.0f,"X-Force candidate-only inversion");
 XForceGuard xn; xn.reset();
 require(!xn.update(std::numeric_limits<float>::quiet_NaN(),.5f,.5f,false).rangeValid,"X-Force rejects NaN");

 // Equal elapsed time at 60/120 Hz must produce nearly the same native blend.
 XForceGuard x60; x60.reset(); x60.update(0.0f,0.0f,.5f,false); x60.update(40.0f,.2f,.5f,false,1.0f/60.0f);
 XForceGuard x120; x120.reset(); x120.update(0.0f,0.0f,.5f,false); x120.update(40.0f,.2f,.5f,false,1.0f/120.0f);
 XForceGuardSample s60{},s120{};
 for(int i=0;i<12;++i)s60=x60.update(40.0f,.2f,.5f,false,1.0f/60.0f);
 for(int i=0;i<24;++i)s120=x120.update(40.0f,.2f,.5f,false,1.0f/120.0f);
 require(std::abs(s60.nativeBlend-s120.nativeBlend)<.03f&&s60.nativeBlend>.99f,"X-Force blend is cadence independent");

 auto mixModern=mix_xforce_character(.4f,-.6f,0,.5f,1.0f);
 auto mixHalf=mix_xforce_character(.4f,-.6f,2,.5f,1.0f);
 auto mixArcade=mix_xforce_character(.4f,-.6f,1,.5f,1.0f);
 require(std::abs(mixModern.torque-.4f)<1e-6f&&mixModern.nativeShare==0.0f,"X-Force Modern character identity");
 require(std::abs(mixHalf.torque+.1f)<1e-6f&&std::abs(mixHalf.nativeShare-.5f)<1e-6f,"X-Force Hybrid 50 percent mix");
 require(std::abs(mixArcade.torque+.6f)<1e-6f&&mixArcade.nativeShare==1.0f,"X-Force Arcade full native after guard");

 // Diagnostic analyzer must identify a coherent signed steering signal without
 // affecting the torque guard, and flag only sustained frozen-data suspicion.
 XForceSignalAnalyzer xa; xa.reset();
 for(int i=0;i<180;++i){
   float phase=float(i)*.08f; float steerSig=std::sin(phase)*.7f;
   float raw=-steerSig*55.0f; float modern=-steerSig*.8f;
   xa.update(raw,.45f,steerSig,modern,steerSig*.12f,steerSig*.25f,1.0f/60.0f);
 }
 auto xaSnap=xa.snapshot();
 require(xaSnap.samples==180&&std::abs(xaSnap.corrSteer)>.95f&&std::abs(xaSnap.corrModernSat)>.95f,"X-Force analyzer correlations");
 require(xaSnap.confidence>.75f&&xaSnap.p95Abs>25.0f&&xaSnap.maxAbs>35.0f,"X-Force analyzer confidence/distribution");
 XForceSignalAnalyzer xf; xf.reset();
 for(int i=0;i<45;++i){
   float changing=float(i)*.04f;
   xf.update(20.0f,.40f,changing,changing,changing*.2f,changing*.3f,1.0f/60.0f);
 }
 auto xfSnap=xf.snapshot();
 require(xfSnap.frozenSuspicious&&xfSnap.frozenSeconds>=.50f,"X-Force diagnostic non-zero freeze detector");

'''
text = text[:start] + new_tests + text[end:]
write(rel, text)


# ---------------------------------------------------------------------------
# structural verifier: lock the new direction in
# ---------------------------------------------------------------------------
rel = 'tools/verify_wheel_ffb_current.py'
text = read(rel)
text = text.replace("req(math, 'XForceUnresponsiveLimitTicks = 30', 'prolonged dead native signal falls back after hysteresis')\n", "req(math, 'XForceUnresponsiveSeconds = 0.50f', 'prolonged dead native signal uses elapsed time')\n")
text = text.replace("req(math, 'BlendInPerTick = 1.0f / 12.0f', 'native X-Force ramps in instead of hard switching')\n", "req(math, 'XForceBlendInSeconds = 0.20f', 'native X-Force ramp-in is time based')\n")
text = text.replace("req(math, 'BlendOutPerTick = 1.0f / 6.0f', 'invalid native X-Force crossfades back to Modern promptly')\n", "req(math, 'XForceBlendOutSeconds = 0.10f', 'invalid native X-Force crossfade is time based')\n")
insert_after = "req(math, 'mix_xforce_character(', 'Modern/Arcade/Hybrid mix uses production helper')\n"
extra = r'''req(math, 'class XForceSignalAnalyzer', 'X-Force identity validation has a diagnostic production analyzer')
req(math, 'corrModernSat', 'X-Force analyzer compares candidate to Modern SAT')
req(math, 'frozenSuspicious', 'X-Force analyzer detects suspicious non-zero freezes')
req(math, 'p99Abs', 'X-Force analyzer reports high-percentile raw magnitude')
'''
text = replace_once(text, insert_after, insert_after + extra, 'verifier math analyzer guards')
insert_after = "req(ffb, 'xForceMixResult.nativeShare', 'native share controls hybrid and load-modulation ownership')\n"
extra = r'''req(ffb, 'WheelFFBXForceGain', 'native X-Force gain is independently tunable')
req(ffb, 'WheelFFBXForceCapture60Hz', 'full-rate X-Force capture is opt-in')
req(ffb, 'WheelFFB XFORCE60', '60 Hz X-Force capture marker')
req(ffb, 'xForceAnalyzer_.update(', 'runtime updates the X-Force diagnostic analyzer')
req(ffb, 'smoothedXForceMix_', 'live Hybrid mix changes are smoothed')
req(ffb, 'smoothedXForceGain_', 'live native gain changes are smoothed')
'''
text = replace_once(text, insert_after, insert_after + extra, 'verifier core deepening guards')
insert_after = "req(runtime, 'std::array<float, WheelFFBGraphCapacity> nativeShare{};', '60 Hz graph snapshot carries effective native share')\n"
extra = r'''req(runtime, 'struct WheelFFBXForceAnalysisSnapshot', 'runtime exposes X-Force validation statistics')
req(runtime, 'WheelFFB_GetXForceAnalysisSnapshot', 'UI can read X-Force validation statistics')
'''
text = replace_once(text, insert_after, insert_after + extra, 'verifier runtime analysis guards')
insert_after = "req(wheel_ui, 'Native share', 'F11 pipeline graph exposes native/fallback crossfade')\n"
extra = r'''req(wheel_ui, 'X-Force signal confidence', 'F11 displays native signal confidence')
req(wheel_ui, 'Native X-Force Gain', 'F11 exposes native gain after source normalization')
req(wheel_ui, 'Capture X-Force validation at 60 Hz', 'F11 exposes explicit high-rate capture')
req(profiles, 'key != "XForceCapture60Hz"', 'named feel profiles exclude verbose capture state')
'''
text = replace_once(text, insert_after, insert_after + extra, 'verifier UI deepening guards')
text = replace_once(text, "req(profiles, 'values.find(\"xforceinvert\") == values.end()', 'partial v0.3 X-Force profiles are not misclassified as legacy')\n", "req(profiles, 'values.find(\"xforceinvert\") == values.end()', 'partial v0.3 X-Force profiles are not misclassified as legacy')\nreq(profiles, 'values.find(\"xforcegain\") == values.end()', 'early v0.3 profiles receive neutral native gain migration')\n", 'verifier profile gain migration')
text = replace_once(text, "req(build, 'Settings::WheelFFBFeedbackCharacter = 0;', 'legacy preset migration explicitly selects Modern character')\n", "req(build, 'Settings::WheelFFBFeedbackCharacter = 0;', 'legacy preset migration explicitly selects Modern character')\nreq(build, 'Settings::WheelFFBXForceGain = 1.00f;', 'legacy preset migration resets native gain to neutral')\n", 'verifier preset gain')
write(rel, text)


# ---------------------------------------------------------------------------
# build payload regression checks
# ---------------------------------------------------------------------------
rel = '.github/workflows/build.yml'
text = read(rel)
text = replace_once(text, '            "WheelFFB XFORCE t={}",\n', '            "WheelFFB XFORCE t={}",\n            "WheelFFB XFORCE60",\n            "X-Force signal confidence",\n            "Native X-Force Gain",\n', 'compiled marker additions')
text = replace_once(text, '          if ($ini -notmatch \'(?m)^XForceInvert\\s*=\\s*false\\s*$\') { throw "v0.3 candidate direction override must ship disabled" }\n', '          if ($ini -notmatch \'(?m)^XForceInvert\\s*=\\s*false\\s*$\') { throw "v0.3 candidate direction override must ship disabled" }\n          if ($ini -notmatch \'(?m)^XForceGain\\s*=\\s*1\\.00\\s*$\') { throw "v0.3 native X-Force gain must ship neutral" }\n          if ($ini -notmatch \'(?m)^XForceCapture60Hz\\s*=\\s*false\\s*$\') { throw "v0.3 60 Hz X-Force capture must ship disabled" }\n', 'INI build checks')
write(rel, text)

print('v0.3 X-Force deepening patch applied')
