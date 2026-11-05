#include <array>
#include <cassert>
#include <cstdint>
#include <string>
#include "native_sm3_repeat_flow.hpp"
#include "native_sm3_constant_codegen.hpp"
using namespace outrun::vr::dx11;
int main() {
    unsigned count = 0u; int start = 0, stride = 0;
    assert(native_sm3_static_loop_parameters(
        {3u, static_cast<std::uint32_t>(-3), 2u, 0u}, count, start, stride));
    assert(count == 3u && start == -3 && stride == 2);
    assert(!native_sm3_static_loop_parameters(
        {2u, static_cast<std::uint32_t>(-255),
         static_cast<std::uint32_t>(-1), 0u}, count, start, stride));
    assert(!native_sm3_static_loop_parameters({2u, 255u, 1u, 0u},
        count, start, stride));
    std::array<int, 64> game{};
    std::array<std::uint16_t, 16> ends{};
    std::array<std::int16_t, 16> lowers{};
    lowers.fill(-255);
    game[0] = 3; game[1] = -3; game[2] = 2;
    ends[0] = 3; lowers[0] = -3;
    assert(native_sm3_live_loop_payload_valid(game, 1u));
    assert(native_sm3_live_loop_indexed_bounds_valid(game, lowers, ends));
    assert(!native_sm3_live_loop_indexed_bounds_valid(game, ends));
    lowers[0] = -2;
    assert(!native_sm3_live_loop_indexed_bounds_valid(game, lowers, ends));
    lowers[0] = -3; ends[0] = 1;
    assert(!native_sm3_live_loop_indexed_bounds_valid(game, lowers, ends));
    ends[0] = 3; game[1] = 1; game[2] = -2;
    assert(native_sm3_live_loop_indexed_bounds_valid(game, lowers, ends));
    game[1] = -4;
    assert(!native_sm3_live_loop_indexed_bounds_valid(game, lowers, ends));
    game[1] = -3; game[2] = 2; game[3] = 1;
    assert(!native_sm3_live_loop_indexed_bounds_valid(game, lowers, ends));
    game[3] = 0; ends[0] = 257;
    assert(!native_sm3_live_loop_indexed_bounds_valid(game, lowers, ends));
    ends[0] = 3;
    std::array<bool, 256> defs{};
    std::array<std::string, 4> rows{};
    bool live = false;
    assert(native_sm3_relative_matrix_references(
        220, 4, 224, false, 0, false, -2, -2, 0, defs, ends, rows, live));
    assert(rows[0] == "r283_c[220 + r283_aL]" && live);
    ends.fill(0); lowers.fill(-255);
    assert(native_sm3_relative_matrix_references(
        220, 4, 224, false, 0, true, 0, 15, 2, defs, ends, rows, live, &lowers));
    assert(ends[2] == 1u && lowers[2] == -220);
    game.fill(0); game[8] = 3; game[9] = -2; game[10] = 1;
    assert(native_sm3_live_loop_indexed_bounds_valid(game, lowers, ends));
    game[9] = -221;
    assert(!native_sm3_live_loop_indexed_bounds_valid(game, lowers, ends));
    defs[219] = true;
    assert(!native_sm3_relative_matrix_references(
        220, 4, 224, false, 0, true, 0, 15, 2, defs, ends, rows, live, &lowers));
    return 0;
}
