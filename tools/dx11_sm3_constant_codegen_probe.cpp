#include "../src/vr/d3d11/native_sm3_constant_codegen.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    std::string ref;
    assert(native_sm3_const_reference(0, 256, false, ref) && ref == "r283_c[0]");
    assert(native_sm3_const_reference(223, 224, true, ref) && ref == "r283_def223");
    assert(!native_sm3_const_reference(224, 224, false, ref));
    assert(!native_sm3_const_reference(256, 256, false, ref));
    std::string defs;
    assert(append_native_sm3_def(defs, 13, {0x3f800000u, 0xbf800000u, 0x80000000u, 0x7fc00001u}));
    assert(defs.find("r283_def13") != std::string::npos);
    assert(defs.find("asfloat(0x3f800000u)") != std::string::npos);
    assert(defs.find("asfloat(0x7fc00001u)") != std::string::npos);
    assert(!append_native_sm3_def(defs, 256, {0u,0u,0u,0u}));
    const std::array<std::string, 4> rows{"r283_c[0]", "r283_c[1]", "r283_def2", "r283_c[3]"};
    std::string out;
    assert(append_native_sm3_matrix(out, "output.r0", 15, "input.r0.xyzw", rows, 4, 12));
    assert(out.find("dot((input.r0.xyzw).xyzw, (r283_def2).xyzw)") != std::string::npos);
    assert(out.find("output.r0.xyzw = r283_matrix_12.xyzw;") != std::string::npos);
    assert(append_native_sm3_matrix(out, "r283_t0", 7, "input.r0", rows, 3, 14));
    assert(out.find("r283_t0.xyz = r283_matrix_14.xyz;") != std::string::npos);
    const auto before = out;
    assert(!append_native_sm3_matrix(out, "r283_t0", 8, "input.r0", rows, 3, 16));
    assert(!append_native_sm3_matrix(out, "r283_t0", 0, "input.r0", rows, 4, 17));
    assert(!append_native_sm3_matrix(out, "r283_t0", 15, "", rows, 4, 18));
    assert(out == before);
}
