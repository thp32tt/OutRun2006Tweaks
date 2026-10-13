#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// D3D9 stage-1 DIFFUSE/CURRENT/TFACTOR arithmetic and three alpha-weighted blend ops, no second texture.
// Complement and alpha-replicate modifiers are native only for these three
// sources; TEXTURE/TEMP/unsupported bits and stage 2 fall back
// to the original D3D9 Draw/DrawIndexed and gamepad path.
constexpr std::uint32_t kStage1Disable = 1u;
constexpr std::uint32_t kStage1SelectArg1 = 2u;
constexpr std::uint32_t kStage1SelectArg2 = 3u;
constexpr std::uint32_t kStage1Modulate = 4u;
constexpr std::uint32_t kStage1Modulate2X = 5u;
constexpr std::uint32_t kStage1Modulate4X = 6u;
constexpr std::uint32_t kStage1Add = 7u;
constexpr std::uint32_t kStage1Subtract = 10u;
constexpr std::uint32_t kStage1AddSmooth = 11u;
// Game-authored menu/race RGB and independent alpha fades.
// Each operation blends ARG1 by the named alpha and ARG2 by its inverse.
constexpr std::uint32_t kStage1BlendDiffuseAlpha = 12u;
constexpr std::uint32_t kStage1BlendFactorAlpha = 14u;
constexpr std::uint32_t kStage1BlendCurrentAlpha = 16u;
constexpr bool stage1_alpha_blend_operation(std::uint32_t operation) noexcept {
    return operation == kStage1BlendDiffuseAlpha ||
           operation == kStage1BlendFactorAlpha ||
           operation == kStage1BlendCurrentAlpha;
}
constexpr std::uint32_t kStage1Diffuse = 0u;
constexpr std::uint32_t kStage1Current = 1u;
constexpr std::uint32_t kStage1Factor = 3u;
constexpr std::uint32_t kStage1ArgMask = 0x0fu;
constexpr std::uint32_t kStage1Complement = 0x10u;
constexpr std::uint32_t kStage1AlphaReplicate = 0x20u;
constexpr bool stage1_operand_supported(std::uint32_t operand) noexcept {
    constexpr std::uint32_t allowedBits = kStage1ArgMask |
        kStage1Complement | kStage1AlphaReplicate;
    const auto source = operand & kStage1ArgMask;
    return (operand & ~allowedBits) == 0u &&
           (source == kStage1Diffuse || source == kStage1Current ||
            source == kStage1Factor);
}
constexpr bool stage1_combiner_supported(std::uint32_t operation,
                                          std::uint32_t arg1,
                                          std::uint32_t arg2) noexcept {
    if (operation == kStage1SelectArg1) return stage1_operand_supported(arg1);
    if (operation == kStage1SelectArg2) return stage1_operand_supported(arg2);
    return (operation == kStage1Modulate || operation == kStage1Modulate2X ||
            operation == kStage1Modulate4X || operation == kStage1Add ||
            operation == kStage1Subtract || operation == kStage1AddSmooth ||
            stage1_alpha_blend_operation(operation)) &&
            stage1_operand_supported(arg1) && stage1_operand_supported(arg2);
}
constexpr bool stage1_alpha_supported(std::uint32_t operation,
                                       std::uint32_t arg1,
                                       std::uint32_t arg2) noexcept {
    return operation == kStage1Disable ||
        stage1_combiner_supported(operation, arg1, arg2);
}
// Evaluate only active operands: a disabled alpha stage or an unused
// SELECTARG operand must not require a vertex DIFFUSE channel.
constexpr bool stage1_operation_reads_diffuse(std::uint32_t operation,
                                               std::uint32_t arg1,
                                               std::uint32_t arg2) noexcept {
    if (operation == kStage1Disable) return false;
    // BLENDDIFFUSEALPHA samples vertex diffuse alpha even if both arguments
    // are CURRENT/TFACTOR; never invent white diffuse on a texture-only FVF.
    if (operation == kStage1BlendDiffuseAlpha) return true;
    if (operation == kStage1SelectArg1)
        return (arg1 & kStage1ArgMask) == kStage1Diffuse;
    if (operation == kStage1SelectArg2)
        return (arg2 & kStage1ArgMask) == kStage1Diffuse;
    return (arg1 & kStage1ArgMask) == kStage1Diffuse ||
           (arg2 & kStage1ArgMask) == kStage1Diffuse;
}
static_assert(stage1_alpha_blend_operation(kStage1BlendDiffuseAlpha) &&
              stage1_alpha_blend_operation(kStage1BlendFactorAlpha) &&
              stage1_alpha_blend_operation(kStage1BlendCurrentAlpha));
static_assert(!stage1_alpha_blend_operation(kStage1Add));
static_assert(stage1_combiner_supported(kStage1BlendDiffuseAlpha,
                                        kStage1Current, kStage1Factor));
static_assert(stage1_alpha_supported(kStage1BlendCurrentAlpha,
                                     kStage1Factor, kStage1Current));
static_assert(stage1_operation_reads_diffuse(kStage1BlendDiffuseAlpha,
                                              kStage1Factor, kStage1Current));
static_assert(!stage1_operation_reads_diffuse(kStage1BlendFactorAlpha,
                                               kStage1Factor, kStage1Current));
static_assert(stage1_operand_supported(kStage1Diffuse));
static_assert(stage1_operand_supported(kStage1Diffuse | kStage1Complement |
                                      kStage1AlphaReplicate));
static_assert(stage1_operation_reads_diffuse(kStage1Modulate, kStage1Diffuse,
                                             kStage1Factor));
static_assert(!stage1_operation_reads_diffuse(kStage1SelectArg1, kStage1Factor,
                                              kStage1Diffuse));
static_assert(!stage1_operation_reads_diffuse(kStage1Disable, kStage1Diffuse,
                                              kStage1Diffuse));
static_assert(stage1_combiner_supported(kStage1Modulate, kStage1Current, kStage1Factor));
static_assert(stage1_combiner_supported(
    kStage1Modulate, kStage1Current | kStage1AlphaReplicate,
    kStage1Factor | kStage1Complement));
static_assert(stage1_alpha_supported(
    kStage1AddSmooth, kStage1Current | kStage1Complement,
    kStage1Factor | kStage1AlphaReplicate));
static_assert(!stage1_combiner_supported(kStage1Modulate, kStage1Current, 0x14u));
static_assert(!stage1_combiner_supported(kStage1Modulate, kStage1Current, 0x43u));
static_assert(!stage1_combiner_supported(kStage1SelectArg1, 0x12u, kStage1Factor));
} // namespace outrun::vr::dx11::live_game_frame
