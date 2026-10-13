#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// D3D9 fixed-function stage-1 CONSTANT/CURRENT combiner, no second texture.
// Exact argument enums only: complement, alpha-replicate and stage-2
// dependencies must stay on the unmodified original D3D9 Draw.
constexpr std::uint32_t kStage1Disable = 1u;
constexpr std::uint32_t kStage1SelectArg1 = 2u;
constexpr std::uint32_t kStage1SelectArg2 = 3u;
constexpr std::uint32_t kStage1Modulate = 4u;
constexpr std::uint32_t kStage1Modulate2X = 5u;
constexpr std::uint32_t kStage1Modulate4X = 6u;
constexpr std::uint32_t kStage1Add = 7u;
constexpr std::uint32_t kStage1Subtract = 10u;
constexpr std::uint32_t kStage1AddSmooth = 11u;
constexpr std::uint32_t kStage1Current = 1u;
constexpr std::uint32_t kStage1Factor = 3u;
constexpr bool stage1_operand_supported(std::uint32_t operand) noexcept {
    return operand == kStage1Current || operand == kStage1Factor;
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
static_assert(stage1_combiner_supported(kStage1Modulate, kStage1Current, kStage1Factor));
static_assert(!stage1_combiner_supported(kStage1Modulate, kStage1Current, 0x13u));
static_assert(!stage1_combiner_supported(kStage1SelectArg1, 0x11u, kStage1Factor));
} // namespace outrun::vr::dx11::live_game_frame
