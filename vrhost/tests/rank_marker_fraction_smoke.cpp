#include "vr/game/rank_marker_fraction.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <limits>

struct MockNode
{
    std::uint32_t kind_C = 0;
    struct { float float24 = 0, float28 = 0; } args_10;
    struct { struct { float _11 = 2, _12 = 0, _21 = 0, _22 = 3, _41 = 0, _42 = 0; } mtx_14; } args2_58;
};

int main()
{
    using OutRunVR::RankMarker::RestoreFraction;
    MockNode clip{};
    clip.args_10.float24 = 100.0f;
    clip.args_10.float28 = 200.0f;
    assert(RestoreFraction(clip, 0.375f, -0.25f));
    assert(clip.args_10.float24 == 100.375f && clip.args_10.float28 == 199.75f);

    MockNode quad{};
    quad.kind_C = 1;
    quad.args2_58.mtx_14._41 = 50.0f;
    quad.args2_58.mtx_14._42 = 60.0f;
    const float beforeX = 4.0f * quad.args2_58.mtx_14._11 + quad.args2_58.mtx_14._41;
    const float beforeY = 5.0f * quad.args2_58.mtx_14._22 + quad.args2_58.mtx_14._42;
    assert(RestoreFraction(quad, 0.5f, -0.5f));
    assert(4.0f * quad.args2_58.mtx_14._11 + quad.args2_58.mtx_14._41 == beforeX + 0.5f);
    assert(5.0f * quad.args2_58.mtx_14._22 + quad.args2_58.mtx_14._42 == beforeY - 0.5f);
    assert(quad.args2_58.mtx_14._11 == 2.0f && quad.args2_58.mtx_14._22 == 3.0f);

    const float oldX = quad.args2_58.mtx_14._41, oldY = quad.args2_58.mtx_14._42;
    const auto infinity = std::numeric_limits<float>::infinity();
    assert(!RestoreFraction(quad, infinity, 0.5f));
    assert(!RestoreFraction(quad, 1.125f, 0.0f));
    assert(quad.args2_58.mtx_14._41 == oldX && quad.args2_58.mtx_14._42 == oldY);
    quad.kind_C = 9;
    assert(!RestoreFraction(quad, 0.5f, 0.5f));
    quad.kind_C = 1;
    quad.args2_58.mtx_14._41 = infinity;
    assert(!RestoreFraction(quad, 0.25f, 0.25f));
    assert(quad.args2_58.mtx_14._42 == oldY);
    return 0;
}
