#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// D3D9 stage-1 DIFFUSE/CURRENT/TFACTOR arithmetic, signed-add pair and alpha-weighted blends, no second texture.
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
// Stage-1 transition brightness: signed add offsets the sum by one half;
// the 2X variant scales BEFORE clamping, for RGB and independent alpha.
constexpr std::uint32_t kStage1AddSigned = 8u;
constexpr std::uint32_t kStage1AddSigned2X = 9u;
constexpr std::uint32_t kStage1Subtract = 10u;
constexpr std::uint32_t kStage1AddSmooth = 11u;
// Game-authored menu/race RGB and independent alpha fades.
// Each operation blends ARG1 by the named alpha and ARG2 by its inverse.
constexpr std::uint32_t kStage1BlendDiffuseAlpha = 12u;
constexpr std::uint32_t kStage1BlendFactorAlpha = 14u;
constexpr std::uint32_t kStage1BlendCurrentAlpha = 16u;
// Cross-channel RGB operators are COLOROP-only. ALPHAOP must never admit 18..21.
constexpr std::uint32_t kStage1ModulateAlphaAddColor = 18u;
constexpr std::uint32_t kStage1ModulateColorAddAlpha = 19u;
constexpr std::uint32_t kStage1ModulateInvAlphaAddColor = 20u;
constexpr std::uint32_t kStage1ModulateInvColorAddAlpha = 21u;
constexpr bool stage1_cross_channel_color_operation(std::uint32_t op) noexcept {
    return op == kStage1ModulateAlphaAddColor ||
           op == kStage1ModulateColorAddAlpha ||
           op == kStage1ModulateInvAlphaAddColor ||
           op == kStage1ModulateInvColorAddAlpha;
}
// The two three-input texture transitions are an integrated stage-1 RGB/alpha
// family. The third D3D9 operand is COLORARG0/ALPHAARG0 (not a stage-1 texture).
// Dot product and bump-map operations remain fail-closed.
constexpr std::uint32_t kStage1MultiplyAdd = 25u;
constexpr std::uint32_t kStage1Lerp = 26u;
constexpr bool stage1_three_source_operation(std::uint32_t op) noexcept {
    return op == kStage1MultiplyAdd || op == kStage1Lerp;
}
constexpr bool stage1_alpha_blend_operation(std::uint32_t operation) noexcept {
    return operation == kStage1BlendDiffuseAlpha ||
           operation == kStage1BlendFactorAlpha ||
           operation == kStage1BlendCurrentAlpha;
}
constexpr std::uint32_t kStage1Diffuse = 0u;
constexpr std::uint32_t kStage1Current = 1u;
constexpr std::uint32_t kStage1Factor = 3u;
// Game FVF SPECULAR is a distinct interpolated vertex channel; no synthetic white.
constexpr std::uint32_t kStage1Specular = 4u;
// Stage-local constant is independent of D3DRS_TEXTUREFACTOR.
constexpr std::uint32_t kStage1Constant = 6u;
constexpr std::uint32_t kStage1ArgMask = 0x0fu;
constexpr std::uint32_t kStage1Complement = 0x10u;
constexpr std::uint32_t kStage1AlphaReplicate = 0x20u;
constexpr bool stage1_operand_supported(std::uint32_t operand) noexcept {
    constexpr std::uint32_t allowedBits = kStage1ArgMask |
        kStage1Complement | kStage1AlphaReplicate;
    const auto source = operand & kStage1ArgMask;
    return (operand & ~allowedBits) == 0u &&
           (source == kStage1Diffuse || source == kStage1Current ||
            source == kStage1Factor || source == kStage1Specular ||
            source == kStage1Constant);
}
constexpr bool stage1_combiner_supported(std::uint32_t operation,
                                          std::uint32_t arg1,
                                          std::uint32_t arg2) noexcept {
    if (operation == kStage1SelectArg1) return stage1_operand_supported(arg1);
    if (operation == kStage1SelectArg2) return stage1_operand_supported(arg2);
    return (operation == kStage1Modulate || operation == kStage1Modulate2X ||
            operation == kStage1Modulate4X || operation == kStage1Add ||
            operation == kStage1AddSigned || operation == kStage1AddSigned2X ||
            operation == kStage1Subtract || operation == kStage1AddSmooth ||
            stage1_alpha_blend_operation(operation) ||
            stage1_cross_channel_color_operation(operation)) &&
            stage1_operand_supported(arg1) && stage1_operand_supported(arg2);
}
constexpr bool stage1_alpha_supported(std::uint32_t operation,
                                       std::uint32_t arg1,
                                       std::uint32_t arg2) noexcept {
    return operation == kStage1Disable ||
        (!stage1_cross_channel_color_operation(operation) &&
         stage1_combiner_supported(operation, arg1, arg2));
}
// Neither the existing two-source admission nor its unused-argument checks
// may accidentally admit a three-source operation without reading ARG0.
constexpr bool stage1_three_source_supported(std::uint32_t operation,
                                             std::uint32_t arg0,
                                             std::uint32_t arg1,
                                             std::uint32_t arg2) noexcept {
    return stage1_three_source_operation(operation) &&
           stage1_operand_supported(arg0) &&
           stage1_operand_supported(arg1) &&
           stage1_operand_supported(arg2);
}
constexpr bool stage1_three_source_reads_diffuse(std::uint32_t operation,
                                                 std::uint32_t arg0,
                                                 std::uint32_t arg1,
                                                 std::uint32_t arg2) noexcept {
    return stage1_three_source_operation(operation) &&
           ((arg0 & kStage1ArgMask) == kStage1Diffuse ||
            (arg1 & kStage1ArgMask) == kStage1Diffuse ||
            (arg2 & kStage1ArgMask) == kStage1Diffuse);
}
// SPECULAR may be an independent RGB and alpha operand in either source family.
// No FVF SPECULAR field means a complete native Draw rejection, not white input.
constexpr bool stage1_operation_reads_specular(std::uint32_t op,
                                               std::uint32_t arg1,
                                               std::uint32_t arg2) noexcept {
    if (op == kStage1Disable) return false;
    if (op == kStage1SelectArg1) return (arg1 & kStage1ArgMask) == kStage1Specular;
    if (op == kStage1SelectArg2) return (arg2 & kStage1ArgMask) == kStage1Specular;
    return (arg1 & kStage1ArgMask) == kStage1Specular ||
           (arg2 & kStage1ArgMask) == kStage1Specular;
}
constexpr bool stage1_three_source_reads_specular(std::uint32_t op,
                                                  std::uint32_t arg0,
                                                  std::uint32_t arg1,
                                                  std::uint32_t arg2) noexcept {
    return stage1_three_source_operation(op) &&
           ((arg0 & kStage1ArgMask) == kStage1Specular ||
            (arg1 & kStage1ArgMask) == kStage1Specular ||
            (arg2 & kStage1ArgMask) == kStage1Specular);
}
// SELECTARG and disabled alpha do not consume inactive operands.
constexpr bool stage1_operation_reads_constant(std::uint32_t op,
                                               std::uint32_t arg1, std::uint32_t arg2) noexcept {
    if (op == kStage1Disable) return false;
    if (op == kStage1SelectArg1) return (arg1 & kStage1ArgMask) == kStage1Constant;
    if (op == kStage1SelectArg2) return (arg2 & kStage1ArgMask) == kStage1Constant;
    return (arg1 & kStage1ArgMask) == kStage1Constant ||
           (arg2 & kStage1ArgMask) == kStage1Constant;
}
constexpr bool stage1_three_source_reads_constant(std::uint32_t op,
    std::uint32_t arg0, std::uint32_t arg1, std::uint32_t arg2) noexcept {
    return stage1_three_source_operation(op) &&
        ((arg0 & kStage1ArgMask) == kStage1Constant ||
         (arg1 & kStage1ArgMask) == kStage1Constant ||
         (arg2 & kStage1ArgMask) == kStage1Constant);
}
static_assert(stage1_operation_reads_constant(kStage1SelectArg1,kStage1Constant,kStage1Current));
static_assert(!stage1_operation_reads_constant(kStage1SelectArg1,kStage1Current,kStage1Constant));
static_assert(stage1_three_source_reads_constant(kStage1Lerp,kStage1Constant,kStage1Current,kStage1Factor));
static_assert(stage1_combiner_supported(kStage1Add, kStage1Specular,
                                        kStage1Current));
static_assert(stage1_alpha_supported(kStage1SelectArg1, kStage1Specular,
                                      kStage1Factor));
static_assert(stage1_three_source_supported(kStage1Lerp, kStage1Specular,
                                             kStage1Current, kStage1Factor));
static_assert(stage1_operation_reads_specular(kStage1SelectArg2,
                                               kStage1Current, kStage1Specular));
static_assert(!stage1_operation_reads_specular(kStage1SelectArg1,
                                                kStage1Current, kStage1Specular));
static_assert(stage1_three_source_reads_specular(kStage1Lerp,
                                                  kStage1Current, kStage1Specular,
                                                  kStage1Factor));
static_assert(!stage1_operand_supported(5u));
static_assert(stage1_three_source_supported(kStage1MultiplyAdd, kStage1Factor,
                                             kStage1Current, kStage1Diffuse));
static_assert(stage1_three_source_supported(kStage1Lerp, kStage1Current,
                                             kStage1Factor, kStage1Current));
static_assert(!stage1_three_source_supported(kStage1MultiplyAdd, 2u,
                                              kStage1Current, kStage1Factor));
static_assert(!stage1_combiner_supported(kStage1MultiplyAdd,
                                         kStage1Current, kStage1Factor));
static_assert(!stage1_three_source_supported(24u, kStage1Current,
                                              kStage1Current, kStage1Factor));
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
static_assert(stage1_combiner_supported(kStage1AddSigned, kStage1Current, kStage1Factor));
static_assert(stage1_alpha_supported(kStage1AddSigned2X, kStage1Diffuse, kStage1Factor));
static_assert(!stage1_combiner_supported(13u, kStage1Current, kStage1Factor));
static_assert(stage1_alpha_blend_operation(kStage1BlendDiffuseAlpha) &&
              stage1_alpha_blend_operation(kStage1BlendFactorAlpha) &&
              stage1_alpha_blend_operation(kStage1BlendCurrentAlpha));
static_assert(!stage1_alpha_blend_operation(kStage1Add));
static_assert(stage1_combiner_supported(kStage1ModulateAlphaAddColor,
                                        kStage1Current, kStage1Factor));
static_assert(stage1_combiner_supported(kStage1ModulateInvColorAddAlpha,
                                        kStage1Diffuse, kStage1Current));
static_assert(!stage1_alpha_supported(kStage1ModulateAlphaAddColor,
                                      kStage1Current, kStage1Factor));
static_assert(!stage1_alpha_supported(kStage1ModulateInvColorAddAlpha,
                                      kStage1Current, kStage1Factor));
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
static_assert(!stage1_combiner_supported(kStage1Modulate, kStage1Current, 0x15u));
static_assert(!stage1_combiner_supported(kStage1Modulate, kStage1Current, 0x43u));
static_assert(!stage1_combiner_supported(kStage1SelectArg1, 0x12u, kStage1Factor));
} // namespace outrun::vr::dx11::live_game_frame
