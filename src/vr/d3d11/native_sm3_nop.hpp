#pragma once

// An authentic Shader Model 3 NOP has opcode zero, no control bits and no
// operand DWORDs. A predicated or malformed token is never a silent no-op.
#include <cstddef>
#include <cstdint>

namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_sm3_nop_admissible(
    std::uint32_t instructionToken, std::size_t operandCount) noexcept {
    return instructionToken == 0u && operandCount == 0u;
}
} // namespace outrun::vr::dx11
