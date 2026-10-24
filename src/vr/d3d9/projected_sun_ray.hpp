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
        Matrix& output, bool sourceCameraSynced = false) noexcept
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
            !finite(eyeProjection))
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
            headRotation.m[3][axis] = 0.0f;
            eyeRotation.m[3][axis] = 0.0f;
        }
        const Matrix candidate = multiply(multiply(multiply(
            multiply(stockWvp, inverseBaseProjection), headRotation),
            eyeRotation), eyeProjection);
        if (!finite(candidate))
            return false;
        output = candidate;
        return true;
    }
}
