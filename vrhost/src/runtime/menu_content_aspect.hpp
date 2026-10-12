#pragma once
// Opt-in center-content crop for the captured, already-letterboxed 4:3
// OutRun menu. The LOCAL-fixed two-eye clip must use the SAME resulting
// content aspect and UV, not the ultrawide desktop aspect with black rails.
namespace OutRunVrMenuAspect
{
    struct CropPlan
    {
        bool crop = false;
        float offsetX = 0.0f;  // fraction of the captured game client width
        float width = 1.0f;
        float aspect = 0.0f;
    };

    constexpr CropPlan PlanCenteredContent(
        float sourceAspect, float intendedAspect) noexcept
    {
        // Reject NaN/Inf, invalid client sizes and nonsensical overrides.
        // Failing closed preserves the existing complete-client projection.
        if (!(sourceAspect >= 0.5f && sourceAspect <= 5.0f) ||
            !(intendedAspect >= 0.5f && intendedAspect <= 4.0f) ||
            sourceAspect <= intendedAspect)
            return { false, 0.0f, 1.0f, sourceAspect };

        const float width = intendedAspect / sourceAspect;
        return { true, (1.0f - width) * 0.5f, width, intendedAspect };
    }
}
