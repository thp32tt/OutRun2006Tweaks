#include "../../src/vr/d3d9/r30_projection_inverse_cache.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>

struct Matrix4 { float m[16]; };
static Matrix4 Projection(float x, float y, float depth)
{
    Matrix4 value{};
    value.m[0] = x; value.m[5] = y;
    value.m[10] = depth; value.m[15] = 1.0f;
    return value;
}
int main()
{
    using Cache = OutRunVR::R30Projection::ExactInverseCache<Matrix4>;
    Cache cache;
    int calls = 0;
    auto invert = [&](const Matrix4& source, Matrix4& output) noexcept {
        ++calls;
        if (!std::isfinite(source.m[0]) || source.m[0] == 0.0f ||
            !std::isfinite(source.m[5]) || source.m[5] == 0.0f ||
            !std::isfinite(source.m[10]) || source.m[10] == 0.0f)
            return false;
        output = Projection(1.0f/source.m[0], 1.0f/source.m[5],
                            1.0f/source.m[10]);
        return true;
    };
    Matrix4 out{};
    const auto original = Projection(1.4f, 1.8f, 2.0f);
    assert(cache.get(original, out, invert) && calls == 1);
    const float firstInverse = out.m[0];
    // Different R84 consumers must share the SAME original base inverse.
    for (int i = 0; i < 5000; ++i)
        assert(cache.get(original, out, invert) && calls == 1 &&
               out.m[0] == firstInverse);
    auto changedFov = Projection(1.3f, 1.8f, 2.0f);
    assert(cache.get(changedFov, out, invert) && calls == 2 &&
           out.m[0] != firstInverse);
    auto changedDepth = Projection(1.3f, 1.8f, 3.0f);
    assert(cache.get(changedDepth, out, invert) && calls == 3 &&
           out.m[10] == 1.0f/3.0f);
    // The full matrix, including signed-zero bits, is the identity key.
    auto bitDifferent = changedDepth;
    bitDifferent.m[1] = -0.0f;
    assert(cache.get(bitDifferent, out, invert) && calls == 4);
    // The failed new matrix cannot revive its older successful inverse.
    const auto invalid = Projection(0.0f, 1.8f, 3.0f);
    assert(!cache.get(invalid, out, invert) && calls == 5);
    assert(cache.get(changedDepth, out, invert) && calls == 6);
    cache.invalidate();
    assert(cache.get(changedDepth, out, invert) && calls == 7);
}
