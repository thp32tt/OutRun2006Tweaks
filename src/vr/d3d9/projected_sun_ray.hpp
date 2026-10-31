#pragma once
#include <cmath>

namespace OutRunVR::LensCentre
{
    // Original C993 sun geometry is built on artificial view planes (-1,
    // -0.2 and far distance), not at a physical stereo depth. Recover its
    // game-camera direction, rotate it once, then project for the actual eye.
    // Matrix has D3D row-vector layout (m[4][4]); no D3D dependency in the test.
    template<class Matrix>
    bool BuildProjectedSunRay(const Matrix& stockWvp,
        const Matrix& inverseBaseProjection, const Matrix& headInverse,
        const Matrix& eyeInverse, const Matrix& eyeProjection,
        Matrix& output, bool sourceCameraSynced = false,
        float visualScale = 1.0f,
        float stereoTranslationScale = 0.0f) noexcept
    {
        const auto finite = [](const Matrix& value) {
            for (int row = 0; row < 4; ++row)
                for (int col = 0; col < 4; ++col)
                    if (!std::isfinite(value.m[row][col]))
                        return false;
            return true;
        };
        if (!finite(stockWvp) || !finite(inverseBaseProjection) ||
            !finite(headInverse) || !finite(eyeInverse) ||
            !finite(eyeProjection) ||
            !std::isfinite(visualScale) ||
            !std::isfinite(stereoTranslationScale) ||
            visualScale < 0.20f || visualScale > 1.50f ||
            stereoTranslationScale < 0.0f ||
            stereoTranslationScale > 0.25f)
            return false;
        const auto multiply = [](const Matrix& left, const Matrix& right) {
            Matrix result{};
            for (int row = 0; row < 4; ++row)
                for (int col = 0; col < 4; ++col)
                    for (int k = 0; k < 4; ++k)
                        result.m[row][col] += left.m[row][k] * right.m[k][col];
            return result;
        };
        Matrix headRotation = headInverse;
        Matrix eyeRotation = eyeInverse;
        Matrix localScale{};
        for (int axis = 0; axis < 4; ++axis)
            localScale.m[axis][axis] = 1.0f;
        // Scale each flare quad around its own authored local origin. The PMT
        // translation/ray is untouched, so the 11-disc axis spacing remains
        // original while the oversized HMD sprites become physically smaller.
        localScale.m[0][0] = visualScale;
        localScale.m[1][1] = visualScale;
        // Calc3D2D may already have used the HMD-synchronized game camera.
        // That source owns the common head rotation; never apply it twice.
        if (sourceCameraSynced)
        {
            headRotation = Matrix{};
            for (int axis = 0; axis < 4; ++axis)
                headRotation.m[axis][axis] = 1.0f;
        }
        for (int axis = 0; axis < 3; ++axis)
        {
            // Sun/flare stays effectively distant from head translation.
            headRotation.m[3][axis] = 0.0f;
            // Keep only a very small fraction of eye translation. Zero made
            // the repaired flare optically infinite/flat; full fake-plane IPD
            // would recreate the old double image. The caller owns the factor.
            eyeRotation.m[3][axis] *= stereoTranslationScale;
        }
        const Matrix candidate = multiply(multiply(multiply(
            multiply(multiply(localScale, stockWvp),
                inverseBaseProjection), headRotation),
            eyeRotation), eyeProjection);
        if (!finite(candidate))
            return false;
        output = candidate;
        return true;
    }
}
