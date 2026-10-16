#include "../../src/vr/d3d9/pause_menu_eye_affine.hpp"
#include <cmath>
#include <cstring>
#include <iostream>
#include <limits>

struct Matrix {
    float _11,_12,_13,_14, _21,_22,_23,_24;
    float _31,_32,_33,_34, _41,_42,_43,_44;
};
static float YNdc(const Matrix& m, const float v[4])
{
    const float y = v[0]*m._12 + v[1]*m._22 +
                    v[2]*m._32 + v[3]*m._42;
    const float w = v[0]*m._14 + v[1]*m._24 +
                    v[2]*m._34 + v[3]*m._44;
    return y / w;
}
static bool Near(float a, float b)
{
    return std::isfinite(a) && std::isfinite(b) &&
        std::fabs(a-b) < 0.00002f;
}
int main()
{
    using OutRunVrPauseEye::ApplyPostProjectionVerticalShift;
    // Two differently canted/asymmetric eye matrices. X/Y/depth changes
    // must not change the precise signed pause pixel offset.
    const Matrix eye[2]{
        {1.2f,0.1f,0.0f,0.04f, 0.0f,1.7f,0.0f,0.02f,
         0.0f,-0.15f,1.0f,0.8f, 0.0f,0.11f,0.2f,1.4f},
        {0.9f,-0.05f,0.0f,0.03f, 0.0f,1.3f,0.0f,-0.01f,
         0.0f,0.24f,1.0f,1.0f, 0.0f,-0.14f,0.2f,1.6f}};
    const float samples[][4]{
        {0.0f,0.0f,0.0f,1.0f},
        {0.3f,-0.6f,0.7f,1.0f},
        {-0.8f,0.3f,0.2f,1.0f}};
    for (const auto& m : eye)
    {
        for (float shift : {-0.50f,-0.12f,0.18f,0.50f})
        {
            const Matrix shifted =
                ApplyPostProjectionVerticalShift(m,shift);
            for (const auto& v : samples)
                if (!Near(YNdc(shifted,v), YNdc(m,v)+shift))
                    return 1;
            // No optical scaling, depth, W or X should be modified.
            if (shifted._11 != m._11 || shifted._22 != m._22 ||
                shifted._14 != m._14 || shifted._34 != m._34 ||
                shifted._44 != m._44)
                return 2;
        }
        const auto unmodified =
            ApplyPostProjectionVerticalShift(m,0.0f);
        if (std::memcmp(&m,&unmodified,sizeof(m)) != 0)
            return 3;
        const auto invalid = ApplyPostProjectionVerticalShift(
            m,std::numeric_limits<float>::quiet_NaN());
        if (std::memcmp(&m,&invalid,sizeof(m)) != 0)
            return 4;
    }
    std::cout << "R84 ESC clip-space shader/XYZRHW vertical alignment PASS\n";
    return 0;
}
