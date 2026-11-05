#include "../src/vr/d3d11/native_sm3_predicated_instruction.hpp"
#include <cassert>
#include <string>
int main() {
    using namespace outrun::vr::dx11;
    bool inverted = true;
    assert(!native_sm3_scalar_predicate(false, 0u, 0u, 13u, inverted));
    assert(!native_sm3_scalar_predicate(true, 0xe4u, 0u, 13u, inverted));
    assert(!native_sm3_scalar_predicate(true, 0u, 1u, 13u, inverted));
    assert(native_sm3_scalar_predicate(true, 0u, 0u, 13u, inverted) && !inverted);
    assert(native_sm3_scalar_predicate(true, 0u, 13u, 13u, inverted) && inverted);
    assert(native_sm3_predicated_write_mask(0u, 15u, true) == 0u);
    assert(native_sm3_predicated_write_mask(3u, 12u, true) == 3u);
    assert(native_sm3_predicated_write_mask(3u, 12u, false) == 15u);
    std::string hlsl;
    assert(append_native_sm3_predicated_begin(hlsl, false));
    hlsl += "    r283_t0.xy = r283_t1.xy;\n";
    append_native_sm3_predicated_end(hlsl);
    assert(append_native_sm3_predicated_begin(hlsl, true));
    hlsl += "    output.r0 = r283_t0;\n";
    append_native_sm3_predicated_end(hlsl);
    assert(hlsl.find("if (r283_p0) {\n") != std::string::npos);
    assert(hlsl.find("if (!r283_p0) {\n") != std::string::npos);
    return 0;
}
