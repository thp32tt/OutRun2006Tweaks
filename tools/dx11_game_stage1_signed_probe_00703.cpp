#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
float signed_add(std::uint32_t op, float a, float b) {
    const float signedSum = a + b - 0.5f;
    const float value = op == kStage1AddSigned2X ? 2.0f * signedSum : signedSum;
    return value < 0.0f ? 0.0f : (value > 1.0f ? 1.0f : value);
}
bool eq(float a, float b) { return std::fabs(a - b) < 0.00001f; }
}
int main() {
    constexpr std::array<std::uint32_t, 2> ops{
        kStage1AddSigned, kStage1AddSigned2X};
    constexpr std::array<std::uint32_t, 3> sources{
        kStage1Diffuse, kStage1Current, kStage1Factor};
    constexpr std::array<std::uint32_t, 4> modifiers{
        0u, kStage1Complement, kStage1AlphaReplicate,
        kStage1Complement | kStage1AlphaReplicate};
    unsigned variants = 0;
    for (const auto op : ops)
        for (const auto lhs : sources) for (const auto rhs : sources)
            for (const auto left : modifiers) for (const auto right : modifiers) {
                if (!stage1_combiner_supported(op, lhs | left, rhs | right) ||
                    !stage1_alpha_supported(op, lhs | left, rhs | right))
                    return 1;
                const bool needsDiffuse = lhs == kStage1Diffuse || rhs == kStage1Diffuse;
                if (stage1_operation_reads_diffuse(op, lhs | left, rhs | right) != needsDiffuse)
                    return 2;
                ++variants;
            }
    // Independent channel arithmetic: do not let RGB saturation overwrite
    // alpha, or clamp the 2X result before multiplying.
    for (const auto op : ops) {
        const float rgb = signed_add(op, 0.4f, 0.35f);
        const float alpha = signed_add(op, 0.3f, 0.4f);
        const float scale = op == kStage1AddSigned2X ? 2.0f : 1.0f;
        if (!eq(rgb, 0.25f * scale) || !eq(alpha, 0.2f * scale) ||
            !eq(signed_add(op, 0.1f, 0.1f), 0.0f) ||
            !eq(signed_add(op, 0.9f, 0.9f), 1.0f))
            return 3;
    }
    if (stage1_combiner_supported(13u, kStage1Current, kStage1Factor) ||
        stage1_alpha_supported(15u, kStage1Current, kStage1Factor) ||
        stage1_combiner_supported(17u, kStage1Current, kStage1Factor) ||
        stage1_combiner_supported(kStage1AddSigned, kStage1Current, 2u) ||
        stage1_alpha_supported(kStage1AddSigned2X, kStage1Factor | 0x40u, kStage1Current) ||
        !stage1_alpha_supported(kStage1Disable, 0xffu, 0xffu) ||
        stage1_operation_reads_diffuse(kStage1Disable, kStage1Diffuse, kStage1Diffuse) ||
        stage1_operation_reads_diffuse(kStage1SelectArg1, kStage1Factor, kStage1Diffuse))
        return 4;
    std::printf("00703: %u signed RGB/independent-alpha selector cases and fail-closed regression PASS\n", variants);
    return variants == 288u ? 0 : 5;
}
