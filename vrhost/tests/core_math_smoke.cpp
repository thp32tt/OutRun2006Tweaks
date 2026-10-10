#include "vr/core/matrix.hpp"

#include <cmath>
#include <limits>

namespace
{
    bool Near(float a, float b, float epsilon = 1.0e-5f)
    {
        return std::fabs(a - b) <= epsilon;
    }
}

int main()
{
    using namespace OutRunVR::Core;

    Matrix4 base{};
    base[0][0] = 1.3f;
    base[1][1] = 1.7f;
    base[2][2] = -1.001f;
    base[2][3] = -1.0f;
    base[3][2] = -0.1f;

    Fov symmetric{-0.7f, 0.7f, 0.6f, -0.6f};
    Matrix4 projection{};
    if (!ProjectionFromOpenXrFov(base, symmetric, projection))
        return 1;
    if (!Near(projection[2][0], 0.0f) || !Near(projection[2][1], 0.0f))
        return 2;
    if (!Near(projection[2][2], base[2][2]) ||
        !Near(projection[2][3], base[2][3]) ||
        !Near(projection[3][2], base[3][2]))
        return 3;

    Quaternion q{};
    Vector3 p{1.0f, 2.0f, -3.0f};
    const Matrix4 rigid = RigidTransform(q, p, 2.0f);
    if (!Near(rigid[3][0], 2.0f) || !Near(rigid[3][1], 4.0f) || !Near(rigid[3][2], -6.0f))
        return 4;

    const Matrix4 inverseRigid = InverseRigid(rigid);
    const Matrix4 identity = Multiply(rigid, inverseRigid);
    for (int r = 0; r < 4; ++r)
        for (int c = 0; c < 4; ++c)
            if (!Near(identity[r][c], r == c ? 1.0f : 0.0f))
                return 5;

    Matrix4 inverse{};
    if (!Invert(rigid, inverse))
        return 6;
    const Matrix4 identity2 = Multiply(rigid, inverse);
    for (int r = 0; r < 4; ++r)
        for (int c = 0; c < 4; ++c)
            if (!Near(identity2[r][c], r == c ? 1.0f : 0.0f))
                return 7;

    // A rejected FOV must neither mirror the view nor poison the last
    // published finite projection. These checks also run under Release/NDEBUG.
    const Matrix4 validProjection = projection;
    Fov invalid{};
    if (ProjectionFromOpenXrFov(base, invalid, projection))
        return 8;
    if (!Near(projection[0][0], validProjection[0][0]))
        return 9;

    const Fov reversedHorizontal{0.7f, -0.7f, 0.6f, -0.6f};
    if (ProjectionFromOpenXrFov(base, reversedHorizontal, projection))
        return 10;
    const Fov reversedVertical{-0.7f, 0.7f, -0.6f, 0.6f};
    if (ProjectionFromOpenXrFov(base, reversedVertical, projection))
        return 11;
    if (!Near(projection[0][0], validProjection[0][0]) ||
        !Near(projection[1][1], validProjection[1][1]))
        return 12;

    const Fov nonfinite{
        -0.7f, (std::numeric_limits<float>::quiet_NaN)(), 0.6f, -0.6f};
    if (ProjectionFromOpenXrFov(base, nonfinite, projection))
        return 13;

    Matrix4 badBase = base;
    badBase[2][2] = (std::numeric_limits<float>::infinity)();
    if (ProjectionFromOpenXrFov(badBase, symmetric, projection))
        return 14;
    if (!Near(projection[2][2], validProjection[2][2]) ||
        !Near(projection[2][3], validProjection[2][3]))
        return 15;

    // A finite, asymmetric runtime FOV remains valid.
    const Fov asymmetric{-0.8f, 0.7f, 0.65f, -0.6f};
    if (!ProjectionFromOpenXrFov(base, asymmetric, projection) ||
        !MatrixFinite(projection) ||
        Near(projection[2][0], 0.0f) ||
        Near(projection[2][1], 0.0f))
        return 16;

    return 0;
}
