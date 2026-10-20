#include "../src/vr/d3d11/native_sm3_conditional_flow.hpp"
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;

// Covers all three actual game float-control opcodes (IFC/BREAKC/SETP).
// No game/Quest3 outcome is inferred from portable shader source checks.
static_assert(native_sm3_scalar_condition_required_components(0xe4u, 0u) == 1u);
static_assert(native_sm3_scalar_condition_required_components(0x1bu, 9u) == 0x0au);
static_assert(native_sm3_scalar_condition_required_components(0x1bu, 10u) == 0x09u);
static_assert(native_sm3_scalar_condition_required_components(0x00u, 9u) == 1u);
static_assert(native_sm3_scalar_condition_required_components(256u, 0u) == 0u);
static_assert(native_sm3_scalar_condition_required_components(0xe4u, 13u) == 0u);

int main() {
    // A game branch can compare r0.w against a modified c register,
    // preserving actual swizzle and the source-side D3D9 operation.
    for (unsigned modifier = 0u; modifier <= 12u; ++modifier) {
        std::string value = "r283_t0";
        assert(append_native_sm3_scalar_condition_operand(value, 0x1bu, modifier));
        assert(value.find("r283_t0.wzyx") != std::string::npos);
        assert(value.size() > 2u && value.substr(value.size()-2u) == ".x");
    }
    std::string projective = "r283_t3";
    assert(append_native_sm3_scalar_condition_operand(projective, 0x1bu, 9u));
    assert(projective.find(".zzzz") != std::string::npos);
    assert(projective.find(".x") != std::string::npos);
    std::string denominator = "input.r1";
    assert(append_native_sm3_scalar_condition_operand(denominator, 0xe4u, 10u));
    assert(denominator.find(".wwww") != std::string::npos);
    // Neither the branch source nor its provenance can be fabricated.
    for (unsigned invalid : {13u, 14u, 15u, 255u}) {
        std::string unchanged = "r283_t0";
        assert(!append_native_sm3_scalar_condition_operand(unchanged, 0xe4u, invalid));
        assert(unchanged == "r283_t0");
    }
    std::string unchanged = "r283_t0";
    assert(!append_native_sm3_scalar_condition_operand(unchanged, 256u, 0u));
    assert(unchanged == "r283_t0");
    unchanged.clear();
    assert(!append_native_sm3_scalar_condition_operand(unchanged, 0xe4u, 0u));
    // Existing then/else TEMP ownership stays strict when branches diverge.
    NativeSm3ConditionalFlow written;
    NativeSm3ConditionalFlow::Temps temps{};
    NativeSm3ConditionalFlow::Outputs outputs{};
    assert(written.begin(temps, outputs));
    temps[0] = 0x0fu;
    assert(written.otherwise(temps, outputs));
    temps[0] = 0x01u;
    assert(written.end(temps, outputs) && temps[0] == 0u);
    assert(written.empty());
}
