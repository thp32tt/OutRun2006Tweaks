#include "../src/vr/d3d11/native_sm3_destination_output.hpp"
#include <cassert>
#include <string>
int main() {
    using namespace outrun::vr::dx11;
    for (unsigned modifier = 0u; modifier <= 1u; ++modifier)
        for (unsigned shift : {0u, 1u, 2u, 3u, 13u, 14u, 15u})
            assert(native_sm3_destination_modifiers_accepted(modifier, shift));
    for (unsigned bad : {4u, 8u, 12u, 16u, 255u})
        assert(!native_sm3_destination_modifiers_accepted(0u, bad));
    assert(!native_sm3_destination_modifiers_accepted(2u, 0u));
    assert(!native_sm3_destination_modifiers_accepted(4u, 0u));
    std::string shader;
    assert(append_native_sm3_destination_postprocess(shader,"r283_t1",3u,0u,0u));
    assert(shader.empty());
    assert(append_native_sm3_destination_postprocess(shader,"output.r0",3u,1u,2u));
    assert(shader == "    output.r0.xy = saturate((output.r0.xy * 4.0f));\n");
    assert(append_native_sm3_destination_postprocess(shader,"r283_color",8u,0u,13u));
    assert(shader.find("r283_color.w = (r283_color.w * 0.125f);") != std::string::npos);
    assert(append_native_sm3_destination_postprocess(shader,"r283_t0",5u,1u,0u));
    assert(shader.find("r283_t0.xz = saturate(r283_t0.xz);") != std::string::npos);
    const std::string baseline = shader;
    assert(!append_native_sm3_destination_postprocess(shader,"",15u,1u,2u));
    assert(!append_native_sm3_destination_postprocess(shader,"output.r0",0u,1u,2u));
    assert(!append_native_sm3_destination_postprocess(shader,"output.r0",16u,1u,2u));
    assert(!append_native_sm3_destination_postprocess(shader,"output.r0",3u,2u,2u));
    assert(!append_native_sm3_destination_postprocess(shader,"output.r0",3u,1u,4u));
    assert(shader == baseline);
    // Predication owner encloses destination processing in the same dynamic IF.
    std::string predicated = "    if (r283_p0) {\n";
    assert(append_native_sm3_destination_postprocess(predicated,"output.r0",15u,1u,0u));
    predicated += "    }\n";
    assert(predicated.find("if (r283_p0) {\n    output.r0.xyzw = saturate(output.r0.xyzw);\n    }") != std::string::npos);
}
