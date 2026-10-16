#pragma once
// Native R84 Calc3D2D exact vehicle/rival rank marker eye-space mapping.
// Pure math for portable positive/negative regressions.
#include <cmath>
namespace OutRunVR::RankMarker
{
    struct StereoNdcShift
    {
        float baseX = 0.0f, baseY = 0.0f;
        float deltaX[2]{}, deltaY[2]{};
    };
    // The two rank eyes are one logical submission. A stale pose or Reset
    // must not publish a left-eye position if the right eye is invalid.
    // Double intermediates also avoid overflow in finite viewport products.
    inline bool RemapScreenPair(
        float sourceX, float sourceY, float viewportX, float viewportY,
        float viewportW, float viewportH, float markerScale,
        const StereoNdcShift& shift, float (&outX)[2], float (&outY)[2]) noexcept
    {
        if (!(viewportW > 0.0f && viewportH > 0.0f) ||
            !(markerScale > 0.0f && markerScale <= 2.0f) ||
            !std::isfinite(sourceX) || !std::isfinite(sourceY) ||
            !std::isfinite(viewportX) || !std::isfinite(viewportY) ||
            !std::isfinite(viewportW) || !std::isfinite(viewportH) ||
            !std::isfinite(markerScale) ||
            !std::isfinite(shift.baseX) || !std::isfinite(shift.baseY))
            return false;
        const double ndcX = ((double(sourceX) - double(viewportX)) /
            double(viewportW)) * 2.0 - 1.0;
        const double ndcY = 1.0 - ((double(sourceY) - double(viewportY)) /
            double(viewportH)) * 2.0;
        const double scale = double(markerScale);
        float stagedX[2]{}, stagedY[2]{};
        for (int eye = 0; eye < 2; ++eye)
        {
            if (!std::isfinite(shift.deltaX[eye]) ||
                !std::isfinite(shift.deltaY[eye]))
                return false;
            const double mappedX = scale * ndcX +
                double(shift.deltaX[eye]) + (1.0 - scale) * double(shift.baseX);
            const double mappedY = scale * ndcY +
                double(shift.deltaY[eye]) + (1.0 - scale) * double(shift.baseY);
            const double x = double(viewportX) +
                (mappedX + 1.0) * double(viewportW) * 0.5;
            const double y = double(viewportY) +
                (1.0 - mappedY) * double(viewportH) * 0.5;
            if (!std::isfinite(x) || !std::isfinite(y))
                return false;
            stagedX[eye] = static_cast<float>(x);
            stagedY[eye] = static_cast<float>(y);
            if (!std::isfinite(stagedX[eye]) || !std::isfinite(stagedY[eye]))
                return false;
        }
        for (int eye = 0; eye < 2; ++eye)
        {
            outX[eye] = stagedX[eye];
            outY[eye] = stagedY[eye];
        }
        return true;
    }

    // Preserve the older per-eye diagnostic API independently of the pair.
    // A missing second eye must not suppress the first eye's safe arithmetic.
    inline bool RemapScreenPoint(
        float sourceX, float sourceY, float viewportX, float viewportY,
        float viewportW, float viewportH, float markerScale,
        const StereoNdcShift& shift, int eye, float& outX, float& outY) noexcept
    {
        if (eye < 0 || eye > 1 || !(viewportW > 0.0f && viewportH > 0.0f) ||
            !(markerScale > 0.0f && markerScale <= 2.0f) ||
            !std::isfinite(sourceX) || !std::isfinite(sourceY) ||
            !std::isfinite(viewportX) || !std::isfinite(viewportY) ||
            !std::isfinite(viewportW) || !std::isfinite(viewportH) ||
            !std::isfinite(markerScale) ||
            !std::isfinite(shift.baseX) || !std::isfinite(shift.baseY) ||
            !std::isfinite(shift.deltaX[eye]) ||
            !std::isfinite(shift.deltaY[eye]))
            return false;
        const double ndcX = ((double(sourceX) - double(viewportX)) /
            double(viewportW)) * 2.0 - 1.0;
        const double ndcY = 1.0 - ((double(sourceY) - double(viewportY)) /
            double(viewportH)) * 2.0;
        const double scale = double(markerScale);
        const double mappedX = scale * ndcX + double(shift.deltaX[eye]) +
            (1.0 - scale) * double(shift.baseX);
        const double mappedY = scale * ndcY + double(shift.deltaY[eye]) +
            (1.0 - scale) * double(shift.baseY);
        const double x = double(viewportX) +
            (mappedX + 1.0) * double(viewportW) * 0.5;
        const double y = double(viewportY) +
            (1.0 - mappedY) * double(viewportH) * 0.5;
        if (!std::isfinite(x) || !std::isfinite(y))
            return false;
        const float stagedX = static_cast<float>(x);
        const float stagedY = static_cast<float>(y);
        if (!std::isfinite(stagedX) || !std::isfinite(stagedY))
            return false;
        outX = stagedX;
        outY = stagedY;
        return true;
    }
}
