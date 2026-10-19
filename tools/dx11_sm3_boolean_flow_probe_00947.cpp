#include "../src/vr/d3d11/native_sm3_conditional_flow.hpp"
#include "../src/vr/d3d11/native_sm3_constant_codegen.hpp"
#include <cassert>
#include <string>

int main() {
    using namespace outrun::vr::dx11;
    std::string hlsl;
    assert(append_native_sm3_defb(hlsl, 0u, 0u));
    assert(append_native_sm3_defb(hlsl, 15u, 1u));
    assert(hlsl.find("r283_b0 = false;") != std::string::npos);
    assert(hlsl.find("r283_b15 = true;") != std::string::npos);
    const std::string before = hlsl;
    assert(!append_native_sm3_defb(hlsl, 16u, 1u));
    assert(!append_native_sm3_defb(hlsl, 1u, 2u));
    assert(hlsl == before);
    std::string condition;
    assert(native_sm3_bool_reference(15u, true, condition));
    assert(condition == "r283_b15");
    assert(!native_sm3_bool_reference(0u, false, condition));
    assert(!native_sm3_bool_reference(16u, true, condition));

    NativeSm3ConditionalFlow flow;
    NativeSm3ConditionalFlow::Temps temps{};
    NativeSm3ConditionalFlow::Outputs outputs{};
    assert(flow.begin(temps, outputs));
    temps[3] = 0x03u;
    outputs[0] = 0x0fu;
    assert(flow.otherwise(temps, outputs));
    assert(temps[3] == 0u && outputs[0] == 0u);
    temps[3] = 0x05u;
    outputs[0] = 0x0fu;
    assert(flow.end(temps, outputs));
    assert(temps[3] == 0x01u && outputs[0] == 0x0fu);

    assert(flow.begin(temps, outputs));
    assert(flow.begin(temps, outputs));
    temps[4] = 0x0fu;
    assert(flow.end(temps, outputs));
    assert(temps[4] == 0u);
    assert(flow.otherwise(temps, outputs));
    temps[4] = 0x03u;
    assert(flow.end(temps, outputs));
    assert(temps[4] == 0u && flow.empty());
    assert(!flow.end(temps, outputs));
    return 0;
}
