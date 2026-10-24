#include <array>
#include <cassert>
#include <cstdint>
#include "native_sm3_repeat_flow.hpp"
using namespace outrun::vr::dx11;
int main() {
    std::array<int, 64> draw{};
    std::array<std::uint16_t, 16> ends{};
    draw[0] = 3; draw[1] = 6; draw[2] = 2;
    ends[0] = 36; // VS c[220+aL] for VS c[256].
    assert(native_sm3_live_loop_payload_valid(draw, 1u));
    assert(native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    ends[0] = 11;
    assert(native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    ends[0] = 10;
    assert(!native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    ends[0] = 4; // e.g., PS c[220+aL] for PS c[224].
    assert(!native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    ends[0] = 10; draw[1] = 8; draw[2] = -2;
    assert(native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    draw[1] = 3;
    assert(!native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    draw[1] = 8; draw[2] = 2; draw[0] = 17;
    assert(!native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    draw[0] = 3; draw[3] = 1;
    assert(!native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    draw[3] = 0; ends[0] = 257;
    assert(!native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    ends[0] = 16; ends[1] = 8;
    draw[4] = 2; draw[5] = 4; draw[6] = 2;
    assert(native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    ends[1] = 6;
    assert(!native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    ends.fill(0);
    assert(native_sm3_live_loop_indexed_bounds_valid(draw, ends));
    return 0;
}
