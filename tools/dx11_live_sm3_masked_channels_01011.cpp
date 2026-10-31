// Regression for the game SM3 -> native D3D11 Draw/DrawIndexed shader translator.
// Each actual D3D9 destination channel mask must constrain HLSL source reads.
#include "native_sm3_arithmetic_codegen.hpp"
#include <array>
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    const std::array<std::string, 3> sources{
        "r283_t0.xyzw", "r283_t1.xyzw", "r283_t2.xyzw"};
    const auto emit = [&](NativeSm3ArithmeticOpcode opcode, unsigned mask, unsigned count) {
        std::string out;
        const bool admitted = append_native_sm3_arithmetic(
            out, opcode, "r283_color", mask, sources, count, 19u);
        assert(admitted);
        assert(out.find("r283_color.") != std::string::npos);
        return out;
    };
    const auto mov = emit(NativeSm3ArithmeticOpcode::Move, 1u, 1u);
    assert(mov.find("(r283_t0.xyzw).x") != std::string::npos);
    assert(mov.find("(r283_t0.xyzw).y") == std::string::npos);
    assert(mov.find("0.0f, 0.0f, 0.0f") != std::string::npos);
    const auto add = emit(NativeSm3ArithmeticOpcode::Add, 3u, 2u);
    assert(add.find("(r283_t0.xyzw).x + (r283_t1.xyzw).x") != std::string::npos);
    assert(add.find("(r283_t0.xyzw).y + (r283_t1.xyzw).y") != std::string::npos);
    assert(add.find("(r283_t0.xyzw).z") == std::string::npos);
    const auto mad = emit(NativeSm3ArithmeticOpcode::MultiplyAdd, 4u, 3u);
    assert(mad.find("(r283_t2.xyzw).z") != std::string::npos);
    assert(mad.find("(r283_t2.xyzw).x") == std::string::npos);
    const auto cmp = emit(NativeSm3ArithmeticOpcode::Compare, 8u, 3u);
    assert(cmp.find("(r283_t0.xyzw).w >= 0.0f") != std::string::npos);
    assert(cmp.find("(r283_t0.xyzw).x") == std::string::npos);
    const auto minval = emit(NativeSm3ArithmeticOpcode::Minimum, 1u, 2u);
    assert(minval.find("min((r283_t0.xyzw).x, (r283_t1.xyzw).x)") != std::string::npos);
    assert(minval.find("(r283_t0.xyzw).y") == std::string::npos);
    const auto ddx = emit(NativeSm3ArithmeticOpcode::DerivativeX, 2u, 1u);
    assert(ddx.find("ddx((r283_t0.xyzw).y)") != std::string::npos);
    assert(ddx.find("ddx((r283_t0.xyzw).x)") == std::string::npos);
    const auto lrp = emit(NativeSm3ArithmeticOpcode::LinearInterpolate, 4u, 3u);
    assert(lrp.find("(r283_t2.xyzw).z") != std::string::npos);
    assert(lrp.find("(r283_t2.xyzw).w") == std::string::npos);
    const auto sign = emit(NativeSm3ArithmeticOpcode::Sign, 1u, 3u);
    assert(sign.find("sign((r283_t0.xyzw).x)") != std::string::npos);
    // Whole-register game arithmetic and cross-lane DP3 still run in native HLSL.
    const auto full = emit(NativeSm3ArithmeticOpcode::Multiply, 15u, 2u);
    assert(full.find("(r283_t0.xyzw * r283_t1.xyzw)") != std::string::npos);
    const auto dp3 = emit(NativeSm3ArithmeticOpcode::Dot3, 1u, 2u);
    assert(dp3.find("dot((r283_t0.xyzw).xyz") != std::string::npos);
    std::string invalid = "untouched";
    assert(!append_native_sm3_arithmetic(invalid, NativeSm3ArithmeticOpcode::Move,
                                          "r283_color", 0u, sources, 1u, 19u));
    assert(invalid == "untouched");
}