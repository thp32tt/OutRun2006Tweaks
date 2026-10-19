#include "../src/vr/d3d11/native_sm3_repeat_flow.hpp"
#include "../src/vr/d3d11/native_sm3_conditional_flow.hpp"
#include <cassert>
#include <string>

int main() {
    using namespace outrun::vr::dx11;
    NativeSm3StructuredFlow flow;
    NativeSm3StructuredFlow::Temps temps{};
    NativeSm3StructuredFlow::Outputs outputs{};
    assert(!flow.record_break());
    assert(!flow.end_repeat(temps, outputs));
    assert(flow.begin_if());
    assert(!flow.record_break());
    assert(flow.end_if());
    temps[1] = 3u; outputs[0] = 1u;
    assert(flow.begin_repeat(4u, temps, outputs));
    assert(flow.begin_if());
    temps[1] = 15u; outputs[0] = 15u;
    assert(flow.record_break());
    assert(flow.end_if());
    assert(!flow.end_repeat());
    assert(flow.end_repeat(temps, outputs));
    assert(temps[1] == 3u && outputs[0] == 1u && flow.empty());
    temps[2] = 0u; outputs[1] = 0u;
    assert(flow.begin_repeat(2u, temps, outputs));
    temps[2] = 15u; outputs[1] = 15u;
    assert(flow.end_repeat(temps, outputs));
    assert(temps[2] == 15u && outputs[1] == 15u);
    assert(flow.begin_repeat(2u, temps, outputs));
    assert(flow.begin_repeat(3u, temps, outputs));
    temps[2] = 1u; outputs[1] = 1u;
    assert(flow.record_break());
    assert(flow.end_repeat(temps, outputs));
    assert(temps[2] == 15u && outputs[1] == 15u);
    temps[2] = 7u;
    assert(flow.end_repeat(temps, outputs));
    assert(temps[2] == 7u && flow.empty());
    temps[3] = 0u;
    assert(flow.begin_repeat(16u, temps, outputs));
    temps[3] = 15u;
    assert(flow.record_break());
    assert(flow.end_repeat(temps, outputs));
    assert(temps[3] == 0u);

    std::string hlsl;
    assert(append_native_sm3_repeat_begin(hlsl, 4u, 7u));
    assert(append_native_sm3_break(hlsl, ""));
    assert(append_native_sm3_break(hlsl, "r283_t1.x >= r283_c[2].y"));
    hlsl += "    }\n";
    assert(hlsl.find("    break;\n") != std::string::npos);
    assert(hlsl.find("if (r283_t1.x >= r283_c[2].y) break;\n")
           != std::string::npos);
    return 0;
}
