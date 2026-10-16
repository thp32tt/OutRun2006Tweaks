#include "../src/vr/d3d11/native_sm3_arithmetic_codegen.hpp"
#include <array>
#include <cassert>
#include <string>

using namespace outrun::vr::dx11;

int main() {
    std::string out;
    const std::array<std::string, 3> sources{
        "input.r0.xyzw", "r283_t0.yxwz", "-(input.r1.xyzw)"};
    const auto emit = [&](NativeSm3ArithmeticOpcode op,
                          unsigned mask, unsigned count) {
        return append_native_sm3_arithmetic(out, op, "output.r0",
                                            mask, sources, count, 1u);
    };
    assert(emit(NativeSm3ArithmeticOpcode::Move, 15u, 1u));
    assert(emit(NativeSm3ArithmeticOpcode::Add, 3u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::Subtract, 15u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::Multiply, 15u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::MultiplyAdd, 15u, 3u));
    assert(emit(NativeSm3ArithmeticOpcode::Dot3, 15u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::Dot4, 15u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::Minimum, 15u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::Maximum, 15u, 2u));
    assert(out.find("output.r0.xy = r283_value_1.xy;") != std::string::npos);
    assert(out.find("dot((input.r0.xyzw).xyz, (r283_t0.yxwz).xyz)") !=
           std::string::npos);
    assert(out.find("dot((input.r0.xyzw).xyzw, (r283_t0.yxwz).xyzw)") !=
           std::string::npos);
    const auto before = out;
    assert(!emit(NativeSm3ArithmeticOpcode::Move, 0u, 1u));
    assert(!emit(NativeSm3ArithmeticOpcode::Move, 16u, 1u));
    assert(!emit(NativeSm3ArithmeticOpcode::MultiplyAdd, 15u, 2u));
    assert(!emit(static_cast<NativeSm3ArithmeticOpcode>(255), 15u, 3u));
    assert(out == before);
}
