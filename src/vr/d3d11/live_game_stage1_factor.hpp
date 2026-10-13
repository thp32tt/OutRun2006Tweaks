#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// D3D9 fixed-function stage-1 DIFFUSE/CURRENT/TFACTOR combiner, no second texture.
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
            operation == kStage1Subtract || operation == kStage1AddSmooth) &&
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
    if (operation == kStage1SelectArg1)
        return (arg1 & kStage1ArgMask) == kStage1Diffuse;
    if (operation == kStage1SelectArg2)
        return (arg2 & kStage1ArgMask) == kStage1Diffuse;
    return (arg1 & kStage1ArgMask) == kStage1Diffuse ||
           (arg2 & kStage1ArgMask) == kStage1Diffuse;
}
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
