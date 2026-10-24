#include "../src/vr/d3d11/live_game_stage1_factor.hpp"
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;

namespace {
float reference(std::uint32_t op, float a, float b,
                float currentAlpha, float diffuseAlpha, float factorAlpha) {
    const float weight = op == kStage1BlendDiffuseAlpha ? diffuseAlpha :
                         op == kStage1BlendFactorAlpha ? factorAlpha : currentAlpha;
    return a * weight + b * (1.0f - weight);
}
bool near(float x, float y) { return std::fabs(x - y) < 0.00001f; }
}
int main() {
    constexpr std::array<std::uint32_t, 3> modes{
        kStage1BlendDiffuseAlpha, kStage1BlendFactorAlpha,
        kStage1BlendCurrentAlpha};
    constexpr std::array<std::uint32_t, 3> sources{
        kStage1Diffuse, kStage1Current, kStage1Factor};
    constexpr std::array<std::uint32_t, 4> modifiers{
        0u, kStage1Complement, kStage1AlphaReplicate,
        kStage1Complement | kStage1AlphaReplicate};
    unsigned variants = 0;
    for (auto op : modes) for (auto lhs : sources) for (auto rhs : sources)
        for (auto left : modifiers) for (auto right : modifiers) {
            if (!stage1_combiner_supported(op, lhs | left, rhs | right) ||
                !stage1_alpha_supported(op, lhs | left, rhs | right))
                return 1;
            const bool needsDiffuse = op == kStage1BlendDiffuseAlpha ||
                 lhs == kStage1Diffuse || rhs == kStage1Diffuse;
            if (stage1_operation_reads_diffuse(op, lhs | left, rhs | right) !=
                needsDiffuse)
                return 2;
            ++variants;
        }
    // One color and one independent-alpha interpolation sample per source.
    // This verifies that the weighted sources are distinct for menu fading.
    constexpr std::array<float, 3> current{0.f, 0.5f, 1.f};
    constexpr std::array<float, 3> diffuse{1.f, 0.f, 0.25f};
    constexpr std::array<float, 3> factor{0.25f, 1.f, 0.f};
    for (std::size_t i = 0; i < current.size(); ++i) {
        if (!near(reference(kStage1BlendCurrentAlpha, 0.8f, 0.2f,
                            current[i], diffuse[i], factor[i]),
                  0.2f + 0.6f * current[i]) ||
            !near(reference(kStage1BlendDiffuseAlpha, 0.8f, 0.2f,
                            current[i], diffuse[i], factor[i]),
                  0.2f + 0.6f * diffuse[i]) ||
            !near(reference(kStage1BlendFactorAlpha, 0.8f, 0.2f,
                            current[i], diffuse[i], factor[i]),
                  0.2f + 0.6f * factor[i]))
            return 3;
    }
    if (!stage1_operation_reads_diffuse(kStage1BlendDiffuseAlpha,
                                          kStage1Current, kStage1Factor) ||
        stage1_operation_reads_diffuse(kStage1BlendFactorAlpha,
                                         kStage1Current, kStage1Factor) ||
        stage1_operation_reads_diffuse(kStage1Disable,
                                         kStage1Diffuse, kStage1Diffuse) ||
        stage1_combiner_supported(kStage1BlendFactorAlpha, 2u, kStage1Current) ||
        stage1_combiner_supported(kStage1BlendCurrentAlpha,
                                   kStage1Current | 0x40u, kStage1Factor) ||
        stage1_combiner_supported(13u, kStage1Current, kStage1Factor) ||
        stage1_combiner_supported(15u, kStage1Current, kStage1Factor))
        return 4;
    std::printf("00702: %u RGB/alpha blend selector combinations, fallback + 9 samples PASS\n",
                variants);
    return variants == 432u ? 0 : 5;
}
