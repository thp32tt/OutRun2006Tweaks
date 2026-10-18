#pragma once
// Native SM3 ps_3_0 TEXKILL: discard a fragment if any TEMP xyz value is
// negative. The D3D9 opcode contract requires ALL FOUR TEMP components to
// have been previously written, even though the kill test reads only xyz.
// Preserve this instruction-time mask, not the final program write mask.
#include <string>

namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_sm3_texkill_ready(
    unsigned tempRegister, unsigned priorWrittenMask) noexcept {
    return tempRegister < 32u && priorWrittenMask == 0x0fu;
}

inline bool append_native_sm3_texkill(std::string& out,
                                      unsigned tempRegister,
                                      unsigned priorWrittenMask,
                                      unsigned ordinal) {
    if (!native_sm3_texkill_ready(tempRegister, priorWrittenMask) ||
        ordinal >= 512u)
        return false;
    out += "    clip(r283_t" + std::to_string(tempRegister) + ".xyz);\n";
    return true;
}
} // namespace outrun::vr::dx11
