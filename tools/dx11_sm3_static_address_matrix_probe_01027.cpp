#include "native_sm3_constant_codegen.hpp"
#include "native_sm3_temp_draw_uniformity.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    assert(native_sm3_matrix_source_span_accepted(255, 4, 256, true, true));
    assert(!native_sm3_matrix_source_span_accepted(255, 4, 256, false, false));
    assert(!native_sm3_matrix_source_span_accepted(255, 4, 256, true, false));
    assert(native_sm3_matrix_source_span_accepted(252, 4, 256, true, false));
    assert(!native_sm3_matrix_source_span_accepted(253, 4, 256, true, false));
    assert(native_sm3_matrix_source_span_accepted(253, 4, 256, true, true));
    assert(!native_sm3_matrix_source_span_accepted(256, 4, 256, true, true));
    assert(!native_sm3_matrix_source_span_accepted(255, 1, 256, true, true));
    assert(!native_sm3_matrix_source_span_accepted(255, 5, 256, true, true));
    std::array<bool, 256> defs{};
    std::array<std::uint16_t, 16> bounds{};
    std::array<std::string, 4> rows{};
    bool live = false;
    assert(native_sm3_relative_matrix_references(
        255, 4, 256, true, -3, false, 0, 0, 0, defs, bounds, rows, live));
    assert(rows[0] == "r283_c[252]" && rows[1] == "r283_c[253]" &&
           rows[2] == "r283_c[254]" && rows[3] == "r283_c[255]" && live);
    defs[253] = true;
    assert(native_sm3_relative_matrix_references(
        255, 4, 256, true, -3, false, 0, 0, 0, defs, bounds, rows, live));
    assert(rows[1] == "r283_def253" && live);
    defs[253] = false;
    assert(!native_sm3_relative_matrix_references(
        255, 4, 256, true, -2, false, 0, 0, 0, defs, bounds, rows, live));
    assert(!native_sm3_relative_matrix_references(
        0, 4, 256, true, -1, false, 0, 0, 0, defs, bounds, rows, live));
    assert(!native_sm3_relative_matrix_references(
        255, 4, 256, true, -3, true, 0, 0, 0, defs, bounds, rows, live));
    assert(native_sm3_addressed_const_draw_uniform(false, false));
    assert(native_sm3_addressed_const_draw_uniform(true, true));
    assert(!native_sm3_addressed_const_draw_uniform(true, false));
    assert(native_sm3_matrix_draw_uniform(4, 4, 15,
            native_sm3_addressed_const_draw_uniform(true, true)));
    assert(!native_sm3_matrix_draw_uniform(4, 4, 15,
            native_sm3_addressed_const_draw_uniform(true, false)));
    NativeSm3TempDrawUniformity temp;
    temp.write(3, 15, native_sm3_addressed_const_draw_uniform(true, true), true);
    assert(temp.contains(3, 15));
    assert(temp.begin_if(false));
    temp.write(3, 15, false, true);
    assert(temp.end_if());
    assert(!temp.contains(3, 15));
    return 0;
}
