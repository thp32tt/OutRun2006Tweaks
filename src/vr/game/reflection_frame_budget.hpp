#pragma once

#include <algorithm>
#include <cmath>

namespace OutRunVR::ReflectionFrameBudget
{
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