#pragma once
// Native SM3 ps_3_0 TEXKILL: discard a fragment when any already-defined
// TEMP xyz component is negative. D3D9 input/FFB stays untouched; the
// bytecode owner must establish xyz liveness BEFORE calling this emitter.
#include <string>

namespace outrun::vr::dx11 {
inline bool append_native_sm3_texkill(std::string& out,
                                      unsigned tempRegister,
                                      unsigned ordinal) {
    if (tempRegister >= 32u || ordinal >= 512u) return false;
    out += "    clip(r283_t" + std::to_string(tempRegister) + ".xyz);\n";
    return true;
}
} // namespace outrun::vr::dx11
