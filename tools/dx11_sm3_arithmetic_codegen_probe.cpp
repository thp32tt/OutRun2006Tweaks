#include "../src/vr/d3d11/native_sm3_arithmetic_codegen.hpp"
#include "../src/vr/d3d11/native_sm3_fragment_codegen.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
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
    assert(emit(NativeSm3ArithmeticOpcode::Absolute, 15u, 1u));
    assert(emit(NativeSm3ArithmeticOpcode::Fraction, 3u, 1u));
    assert(emit(NativeSm3ArithmeticOpcode::SetLessThan, 15u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::SetGreaterEqual, 15u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::Compare, 15u, 3u));
    assert(emit(NativeSm3ArithmeticOpcode::Reciprocal, 15u, 1u));
    assert(emit(NativeSm3ArithmeticOpcode::ReciprocalSquareRoot, 15u, 1u));
    assert(emit(NativeSm3ArithmeticOpcode::Exponential2, 15u, 1u));
    assert(emit(NativeSm3ArithmeticOpcode::Logarithm2, 15u, 1u));
    assert(emit(NativeSm3ArithmeticOpcode::Power, 15u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::LinearInterpolate, 15u, 3u));
    assert(emit(NativeSm3ArithmeticOpcode::Normalize3, 7u, 1u));
    assert(emit(NativeSm3ArithmeticOpcode::Cross3, 7u, 2u));
    assert(emit(NativeSm3ArithmeticOpcode::Dot2Add, 15u, 3u));
    assert(emit(NativeSm3ArithmeticOpcode::DerivativeX, 3u, 1u));
    assert(emit(NativeSm3ArithmeticOpcode::DerivativeY, 12u, 1u));
    assert(out.find("ddx(input.r0.xyzw)") != std::string::npos);
    assert(out.find("ddy(input.r0.xyzw)") != std::string::npos);
    assert(out.find("rsqrt(abs(") != std::string::npos);
    assert(out.find("exp2(") != std::string::npos);
    assert(out.find("log2(abs(") != std::string::npos);
    assert(out.find("pow(abs(") != std::string::npos);
    assert(out.find("normalize((input.r0.xyzw).xyz)") != std::string::npos);
    assert(out.find("cross((input.r0.xyzw).xyz") != std::string::npos);
    assert(out.find("dot((input.r0.xyzw).xy") != std::string::npos);
    assert(out.find("output.r0.xy = r283_value_1.xy;") != std::string::npos);
    assert(out.find("dot((input.r0.xyzw).xyz, (r283_t0.yxwz).xyz)") !=
           std::string::npos);
    assert(out.find("dot((input.r0.xyzw).xyzw, (r283_t0.yxwz).xyzw)") !=
           std::string::npos);
    assert(out.find("abs(input.r0.xyzw)") != std::string::npos);
    assert(out.find("frac(input.r0.xyzw)") != std::string::npos);
    assert(out.find("(input.r0.xyzw).x < (r283_t0.yxwz).x ? 1.0f : 0.0f") != std::string::npos);
    assert(out.find("(input.r0.xyzw).x >= (r283_t0.yxwz).x ? 1.0f : 0.0f") != std::string::npos);
    assert(out.find("(input.r0.xyzw).x >= 0.0f ? (r283_t0.yxwz).x : (-(input.r1.xyzw)).x") != std::string::npos);
    const auto before = out;
    assert(!emit(NativeSm3ArithmeticOpcode::Move, 0u, 1u));
    assert(!emit(NativeSm3ArithmeticOpcode::Move, 16u, 1u));
    assert(!emit(NativeSm3ArithmeticOpcode::MultiplyAdd, 15u, 2u));
    assert(!emit(NativeSm3ArithmeticOpcode::Compare, 15u, 2u));
    assert(!emit(NativeSm3ArithmeticOpcode::Fraction, 15u, 2u));
    assert(!emit(NativeSm3ArithmeticOpcode::Normalize3, 15u, 1u));
    assert(!emit(NativeSm3ArithmeticOpcode::Cross3, 15u, 2u));
    assert(!emit(NativeSm3ArithmeticOpcode::Dot2Add, 15u, 2u));
    std::string operand = "input.r0.xyzw";
    assert(append_native_sm3_source_modifier(operand, 11u));
    assert(operand == "abs(input.r0.xyzw)");
    assert(append_native_sm3_source_modifier(operand, 12u));
    assert(operand == "-abs(abs(input.r0.xyzw))");
    assert(!append_native_sm3_source_modifier(operand, 9u));
    assert(!append_native_sm3_source_modifier(operand, 10u));
    assert(!append_native_sm3_source_modifier(operand, 13u));
    assert(operand == "-abs(abs(input.r0.xyzw))");
    assert(!emit(static_cast<NativeSm3ArithmeticOpcode>(255), 15u, 3u));
    assert(out == before);
    // Pixel programmable texture instructions share actual sN/tN bindings.
    // Only xy and (for projected/bias/LOD) w are consumed from coordinates.
    using TM = NativeSm3Texture2DMode;
    static_assert(native_sm3_texture_source_components(TM::Implicit, 0u) == 3u);
    static_assert(native_sm3_texture_source_components(TM::Bias, 0u) == 11u);
    static_assert(native_sm3_texture_source_components(TM::ExplicitLod, 0u) == 11u);
    static_assert(native_sm3_texture_source_components(TM::Projected, 0u) == 11u);
    static_assert(native_sm3_texture_source_components(TM::Gradients, 0u) == 3u);
    static_assert(native_sm3_texture_source_components(TM::Gradients, 2u) == 3u);
    static_assert(native_sm3_texture_source_components(TM::Gradients, 3u) == 3u);
    static_assert(native_sm3_texture_source_components(TM::Gradients, 1u) == 0u);
    std::string textureSource;
    assert(append_native_sm3_texture2d_declarations(textureSource, 2u));
    assert(append_native_sm3_texture2d_sample(
        textureSource, "output.r0", 15u, "input.r0", 2u, 0u));
    assert(append_native_sm3_texture2d_sample(
        textureSource, "output.r0", 3u, "input.r0", 2u, 1u, TM::Projected));
    assert(append_native_sm3_texture2d_sample(
        textureSource, "output.r0", 15u, "input.r0", 2u, 2u, TM::Bias));
    assert(append_native_sm3_texture2d_sample(
        textureSource, "output.r0", 15u, "input.r0", 2u, 3u, TM::ExplicitLod));
    assert(append_native_sm3_texture2d_sample(
        textureSource, "output.r0", 15u, "input.r0", 2u, 4u,
        TM::Gradients, "r283_t1", "r283_t2"));
    assert(textureSource.find(".Sample(r283_sampler2, (input.r0).xy)") != std::string::npos);
    assert(textureSource.find("((input.r0).xy / (input.r0).w)") != std::string::npos);
    assert(textureSource.find(".SampleBias(") != std::string::npos);
    assert(textureSource.find(".SampleLevel(") != std::string::npos);
    assert(textureSource.find(".SampleGrad(") != std::string::npos);
    const auto validTexture = textureSource;
    assert(!append_native_sm3_texture2d_sample(
        textureSource, "output.r0", 15u, "input.r0", 2u, 5u, TM::Gradients));
    assert(!append_native_sm3_texture2d_sample(
        textureSource, "output.r0", 15u, "input.r0", 16u, 5u));
    assert(!append_native_sm3_texture2d_sample(
        textureSource, "output.r0", 15u, "input.r0", 2u, 5u,
        static_cast<TM>(255u)));
    assert(textureSource == validTexture);
    // Game ps_3_0 frequently writes a TEMP one lane at a time before
    // consuming one swizzled lane. Identity xyzw must not demand yzw.
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Move, 1u, 0u) == 1u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::DerivativeX, 2u, 0u) == 2u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::DerivativeY, 4u, 0u) == 4u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::DerivativeX, 2u, 1u) == 0u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::MultiplyAdd, 3u, 2u) == 3u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Compare, 8u, 1u) == 8u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Dot3, 1u, 0u) == 7u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Dot4, 1u, 1u) == 15u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Normalize3, 1u, 0u) == 7u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Reciprocal, 8u, 0u) == 1u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Power, 8u, 1u) == 1u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Dot2Add, 1u, 2u) == 1u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Dot2Add, 1u, 1u) == 3u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Move, 1u, 1u) == 0u);
    static_assert(native_sm3_source_components(
        NativeSm3ArithmeticOpcode::Move, 16u, 0u) == 0u);
    static_assert(native_sm3_swizzled_components(1u, 0xe4u) == 1u);
    static_assert(native_sm3_swizzled_components(2u, 0xb1u) == 1u);
    static_assert(native_sm3_swizzled_components(3u, 0xe4u) == 3u);
    static_assert(native_sm3_swizzled_components(7u, 0xe4u) == 7u);
    static_assert(native_sm3_swizzled_components(1u, 0xffu) == 8u);
    static_assert(native_sm3_swizzled_components(0u, 0xe4u) == 0u);
    static_assert(native_sm3_swizzled_components(16u, 0xe4u) == 0u);
    static_assert(native_sm3_swizzled_components(1u, 256u) == 0u);
    // Pixel-only TEXKILL reads all three prior TEMP lanes; no fabricated
    // zeros may turn an unwritten channel into a native pixel discard.
    std::string killSource;
    static_assert(native_sm3_texkill_ready(2u, 15u));
    static_assert(!native_sm3_texkill_ready(2u, 7u));
    static_assert(!native_sm3_texkill_ready(2u, 0u));
    static_assert(!native_sm3_texkill_ready(32u, 15u));
    assert(append_native_sm3_texkill(killSource, 2u, 15u, 0u));
    assert(killSource == "    clip(r283_t2.xyz);\n");
    assert(!append_native_sm3_texkill(killSource, 2u, 7u, 1u));
    assert(!append_native_sm3_texkill(killSource, 32u, 15u, 1u));
    assert(killSource == "    clip(r283_t2.xyz);\n");
    // Real backend rejects unwritten lanes even after a partial write.
    const unsigned tempWrittenX = 1u;
    const unsigned movReadX = native_sm3_swizzled_components(
        native_sm3_source_components(NativeSm3ArithmeticOpcode::Move, 1u, 0u),
        0xe4u);
    const unsigned movReadY = native_sm3_swizzled_components(
        native_sm3_source_components(NativeSm3ArithmeticOpcode::Move, 2u, 0u),
        0xe4u);
    assert((tempWrittenX & movReadX) == movReadX);
    assert((tempWrittenX & movReadY) != movReadY);
    const unsigned dotRead = native_sm3_swizzled_components(
        native_sm3_source_components(NativeSm3ArithmeticOpcode::Dot3, 1u, 0u),
        0xe4u);
    assert((tempWrittenX & dotRead) != dotRead);
}
