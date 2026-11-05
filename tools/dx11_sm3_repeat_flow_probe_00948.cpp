#include "../src/vr/d3d11/native_sm3_repeat_flow.hpp"
#include "../src/vr/d3d11/native_sm3_conditional_flow.hpp"
#include <array>
#include <cassert>
#include <string>

int main() {
    using namespace outrun::vr::dx11;
    unsigned count = 0;
    assert(native_sm3_static_repeat_count({3u, 0u, 0u, 0u}, count));
    assert(count == 3u);
    assert(!native_sm3_static_repeat_count({0u, 0u, 0u, 0u}, count));
    assert(!native_sm3_static_repeat_count({0xffffffffu, 0u, 0u, 0u}, count));
    assert(!native_sm3_static_repeat_count({17u, 0u, 0u, 0u}, count));
    std::string hlsl;
    assert(append_native_sm3_repeat_begin(hlsl, 3u, 21u));
    assert(hlsl.find("[loop] for (int r283_repeat_21 = 0;") != std::string::npos);
    const auto before = hlsl;
    assert(!append_native_sm3_repeat_begin(hlsl, 0u, 22u));
    assert(!append_native_sm3_repeat_begin(hlsl, 17u, 22u));
    assert(!append_native_sm3_repeat_begin(hlsl, 1u, 512u));
    assert(hlsl == before);

    NativeSm3StructuredFlow flow;
    assert(!flow.end_if() && !flow.end_repeat() && !flow.otherwise());
    assert(flow.begin_repeat(4));
    assert(flow.begin_if());
    assert(!flow.end_repeat());
    assert(flow.otherwise());
    assert(!flow.otherwise());
    assert(flow.end_if());
    assert(flow.begin_repeat(16));
    assert(!flow.begin_repeat(2)); // 4*16*2 exceeds nested bound
    assert(flow.end_repeat());
    assert(flow.end_repeat());
    assert(flow.empty());
    assert(flow.begin_if());
    assert(flow.begin_repeat(2));
    assert(!flow.end_if()); // cannot end IF across REP
    assert(flow.end_repeat());
    assert(flow.end_if());
    assert(flow.empty());
    assert(flow.begin_repeat(16));
    assert(flow.begin_repeat(4));
    assert(flow.end_repeat() && flow.end_repeat());

    // At least one static repetition executes the body; the IF merge
    // still requires all conditional arms to write a consumed component.
    NativeSm3ConditionalFlow masks;
    NativeSm3ConditionalFlow::Temps temps{};
    NativeSm3ConditionalFlow::Outputs outputs{};
    assert(masks.begin(temps, outputs));
    temps[1] = 15u;
    outputs[0] = 15u;
    assert(masks.otherwise(temps, outputs));
    assert(temps[1] == 0u && outputs[0] == 0u);
    temps[1] = 3u;
    outputs[0] = 15u;
    assert(masks.end(temps, outputs));
    assert(temps[1] == 3u && outputs[0] == 15u);
    return 0;
}
