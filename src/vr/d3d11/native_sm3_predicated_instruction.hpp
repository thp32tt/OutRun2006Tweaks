#pragma once
// D3D9 SM3 bit 28 appends a p0 predicate source to arithmetic/texture
// instructions. Translate only proven scalar p0.x and preserve conditional
// destination writes; all unsupported vector/derivative cases fail closed.
#include <string>
namespace outrun::vr::dx11 {
[[nodiscard]] inline bool native_sm3_scalar_predicate(
    bool predicateInitialized, unsigned sourceSwizzle,
    unsigned sourceModifier, unsigned negatedModifier,
    bool& negate) noexcept {
    negate = false;
    if (!predicateInitialized || sourceSwizzle != 0u ||
        (sourceModifier != 0u && sourceModifier != negatedModifier))
        return false;
    negate = sourceModifier == negatedModifier;
    return true;
}
[[nodiscard]] inline unsigned native_sm3_predicated_write_mask(
    unsigned definiteWritten, unsigned destinationMask,
    bool predicated) noexcept {
    return predicated ? definiteWritten : (definiteWritten | destinationMask);
}
inline bool append_native_sm3_predicated_begin(std::string& translated,
                                               bool negate) {
    translated += negate ? "    if (!r283_p0) {\n"
                        : "    if (r283_p0) {\n";
    return true;
}
inline void append_native_sm3_predicated_end(std::string& translated) {
    translated += "    }\n";
}
} // namespace outrun::vr::dx11
