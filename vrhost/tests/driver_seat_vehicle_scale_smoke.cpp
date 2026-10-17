#include "vr/game/driver_seat_vehicle_scale.hpp"
#include <cmath>
#include <limits>
struct Matrix {
    float _11, _12, _13, _14;
    float _21, _22, _23, _24;
    float _31, _32, _33, _34;
    float _41, _42, _43, _44;
};
static Matrix Original() {
    return {1,0,0,0, 0,1,0,0, 0,0,1,0, 7,8,9,1};
}
int main() {
    using OutRunVR::DriverSeatVehicle::TryScaleModelBasis;
    auto m = Original();
    if (!TryScaleModelBasis(m, 1.15f) ||
        std::fabs(m._11 - 1.15f) > 0.0001f ||
        std::fabs(m._22 - 1.15f) > 0.0001f ||
        std::fabs(m._33 - 1.15f) > 0.0001f ||
        m._41 != 7 || m._42 != 8 || m._43 != 9 || m._44 != 1)
        return 1;
    m = Original();
    if (!TryScaleModelBasis(m, 1.0f) || m._11 != 1 || m._41 != 7)
        return 2;
    m = Original();
    if (!TryScaleModelBasis(m, 0.85f) ||
        !TryScaleModelBasis(m, 1.35f) ||
        !std::isfinite(m._11)) return 3;
    m = Original();
    if (TryScaleModelBasis(m, 1.5f) || m._11 != 1 ||
        TryScaleModelBasis(m, std::numeric_limits<float>::quiet_NaN()) ||
        m._11 != 1) return 4;
    m = Original();
    m._23 = std::numeric_limits<float>::infinity();
    if (TryScaleModelBasis(m, 1.15f) || m._11 != 1 || !std::isinf(m._23))
        return 5;
    m = Original();
    m._41 = std::numeric_limits<float>::quiet_NaN();
    if (TryScaleModelBasis(m, 1.15f) || m._11 != 1) return 6;
    m = Original();
    if (!TryScaleModelBasis(m, 1.15f)) return 7;
    return 0;
}
