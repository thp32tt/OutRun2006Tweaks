#pragma once

#include <algorithm>
#include <cmath>

namespace OutRunVR::ReflectionFrameBudget
{
    // QPC inter-frame cadence, independent of the nominal 60-Hz reflection
    // update rate. A fixed 18-ms cutoff misses 90/120-Hz headset overruns:
    // a 12-ms frame is late at 120 Hz even though it is below 18 ms.
    // Only healthy, plausible intervals teach the tracker; a stutter, pause,
    // invalid counter or loading gap never increases the reference period.
    // This affects only the existing late-frame reflection face budget.
    struct AdaptiveFrameCadence final
    {
        double referenceSeconds = 0.0;
        unsigned healthySamples = 0;
        // A stable lower XR refresh rate must be allowed to re-lock after
        // a headset mode switch. A single late GPU frame cannot teach it.
        double slowerCandidateSeconds = 0.0;
        unsigned slowerCandidateSamples = 0;

        void ClearSlowerCandidate() noexcept
        {
            slowerCandidateSeconds = 0.0;
            slowerCandidateSamples = 0;
        }

        void Reset() noexcept
        {
            referenceSeconds = 0.0;
            healthySamples = 0;
            ClearSlowerCandidate();
        }

        bool Observe(double elapsedSeconds) noexcept
        {
            if (!std::isfinite(elapsedSeconds) || elapsedSeconds <= 0.0)
            {
                Reset();
                return false;
            }

            constexpr double OriginalLateSeconds = 0.018;
            constexpr double FastestPlausible = 1.0 / 150.0;
            constexpr double SlowestPlausible = 1.0 / 55.0;
            const bool cadenceMiss = healthySamples >= 4 &&
                elapsedSeconds > referenceSeconds * 1.20 + 0.0005;
            const bool late = elapsedSeconds > OriginalLateSeconds || cadenceMiss;

            // Learn real 72/80/90/120-Hz submissions (and 60-Hz desktop)
            // without requiring the user to force a specific headset rate.
            // Fast recovery follows a newly faster eye cadence; gradual
            // upward adaptation tolerates normal clock jitter without
            // learning an actual GPU-late frame as the new target.
            if (!late && elapsedSeconds >= FastestPlausible &&
                elapsedSeconds <= SlowestPlausible)
            {
                if (healthySamples == 0 || elapsedSeconds < referenceSeconds)
                    referenceSeconds = elapsedSeconds;
                else
                    referenceSeconds += (elapsedSeconds - referenceSeconds) * 0.02;
                if (healthySamples < 4)
                    ++healthySamples;
            }
            if (!late)
            {
                ClearSlowerCandidate();
                return false;
            }

            // 120->90/80/72/60 Hz and 90->72 Hz used to stay "late" forever:
            // the late branch intentionally did not learn a new slow target.
            // Distinguish a sustained nominal refresh transition from isolated
            // 12-ms missed-120-Hz frames and nonstandard overloaded cadence.
            // Never relearn from a >18-ms spike, a load/pause gap or bad QPC.
            if (!cadenceMiss || elapsedSeconds > OriginalLateSeconds ||
                elapsedSeconds < FastestPlausible ||
                elapsedSeconds > SlowestPlausible)
            {
                ClearSlowerCandidate();
                return true;
            }
            constexpr double nominalPeriods[] = {
                1.0 / 60.0, 1.0 / 72.0, 1.0 / 80.0,
                1.0 / 90.0, 1.0 / 120.0
            };
            double match = 0.0;
            for (double period : nominalPeriods)
            {
                if (period > referenceSeconds * 1.20 + 0.0005 &&
                    std::fabs(elapsedSeconds - period) <= period * 0.015)
                {
                    match = period;
                    break;
                }
            }
            if (match == 0.0)
            {
                ClearSlowerCandidate();
                return true;
            }
            if (match != slowerCandidateSeconds)
            {
                slowerCandidateSeconds = match;
                slowerCandidateSamples = 1;
            }
            else if (slowerCandidateSamples < 24u)
                ++slowerCandidateSamples;
            if (slowerCandidateSamples >= 24u)
            {
                referenceSeconds = match;
                healthySamples = 4;
                ClearSlowerCandidate();
                return false;
            }
            return true;
        }
    };

    struct StepResult
    {
        float pendingFaces = 0.f;
        int faces = 0;
    };

    // The original PC game renders up to 3 reflection cube faces every
    // 60 Hz frame. At high HMD cadence we time-budget those same faces,
    // with a hard cap after a long/pause/loading frame; no accumulated
    // cubemap work may burst into the critical stereo submission frame.
    inline StepResult Advance(float previous, float requestedRate,
        float elapsed60, bool vrNormalized, bool lateFrame) noexcept
    {
        // A malformed hot-swapped INI value must never generate negative
        // faces or turn into an unbounded cube-map redraw.
        if (!std::isfinite(previous) || previous < 0.f)
            previous = 0.f;
        if (!std::isfinite(requestedRate) || requestedRate < 0.f)
            requestedRate = 0.f;
        if (!std::isfinite(elapsed60))
            elapsed60 = 0.f;
        const float rate = std::clamp(requestedRate, 0.f, 1.f);
        // Disabling cubemap updates invalidates deferred face debt from the
        // previous enabled period; otherwise stale expensive GPU faces
        // continue running after a live INI toggle or menu transition.
        if (rate == 0.f)
            return {0.f, 0};

        const float scaled = vrNormalized
            ? (lateFrame ? 0.5f : std::clamp(elapsed60, 0.f, 1.f))
            : 1.f;
        // Use double for long-running fractional accumulation. The old
        // visible 60 Hz steady-state cadence is preserved by this formula.
        const double requested =
            double(previous) + 6.0 * double(rate) * double(scaled);
        const int limit = vrNormalized ? (lateFrame ? 2 : 3) : 6;
        const int faces = static_cast<int>(std::min<double>(
            limit, std::max<double>(0., requested)));
        const float retained = static_cast<float>(
            std::clamp(requested - faces, 0.0, vrNormalized ? 1.0 : 6.0));
        return {retained, faces};
    }
}