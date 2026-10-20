#include "../src/vr/d3d11/native_sm3_arithmetic_codegen.hpp"
#include <cassert>
#include <string>

using namespace outrun::vr::dx11;

// Genuine SM3 projective modifiers are extra per-operand reads, not merely
// an HLSL string rewrite. No unwritten source TEMP z/w may reach native GPU.
static_assert(native_sm3_source_modifier_components(0x01u, 9u) == 0x05u);
static_assert(native_sm3_source_modifier_components(0x02u, 10u) == 0x0au);
static_assert(native_sm3_source_modifier_components(0x0fu, 9u) == 0x0fu);
static_assert(native_sm3_source_modifier_components(0x00u, 9u) == 0u);
static_assert(native_sm3_source_modifier_components(0x10u, 10u) == 0u);
static_assert(native_sm3_swizzled_components(
    native_sm3_source_modifier_components(0x01u, 9u), 0x1bu) == 0x0cu);

int main() {
    std::string dz = "r283_t1.wzyx";
    assert(append_native_sm3_source_modifier(dz, 9u));
    assert(dz.find("(r283_t1.wzyx).zzzz") != std::string::npos);
    std::string dw = "input.r0.xyzw";
    assert(append_native_sm3_source_modifier(dw, 10u));
    assert(dw.find("(input.r0.xyzw).wwww") != std::string::npos);
    std::string shader;
    assert(append_native_sm3_arithmetic(
        shader, NativeSm3ArithmeticOpcode::Multiply, "r283_t0", 0x03u,
        std::array<std::string, 3>{dz, dw, {}}, 2u, 0u));
    assert(shader.find("r283_t0.xy =") != std::string::npos);
    assert(shader.find(".zzzz") != std::string::npos);
    assert(shader.find(".wwww") != std::string::npos);
    // Unsupported bool/relative/predicate source modifiers cannot be
    // accepted or accidentally mutate the translated operand.
    std::string invalid = "r283_t1";
    assert(!append_native_sm3_source_modifier(invalid, 13u));
    assert(invalid == "r283_t1");
    assert(!append_native_sm3_source_modifier(invalid, 255u));
    assert(invalid == "r283_t1");
}
