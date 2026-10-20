#pragma once
// D3D9 SM3 MOVA a0.x -> D3D11 VS/PS constant address, only when the
// original shader's own DEF literal establishes an exact integral address.
// Input-derived / game-dependent a0 remains untranslatable and falls back.
#include <cmath>
#include <cstdint>
#include <cstring>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool native_sm3_static_mova_address(
    std::uint32_t literalBits, unsigned modifier, unsigned& address) noexcept {
    address = 0u;
    if (modifier > 1u) return false; // NONE or NEG; no lossy source modifiers
    float value = 0.0f;
    static_assert(sizeof(value) == sizeof(literalBits));
    std::memcpy(&value, &literalBits, sizeof(value));
    if (modifier == 1u) value = -value;
    if (!std::isfinite(value) || value < 0.0f || value > 255.0f ||
        std::trunc(value) != value) return false;
    address = static_cast<unsigned>(value);
    return true;
}

// Static a0.x can address VS c0..c255 and PS c0..c223. DEF overrides
// are resolved by the materializer, and unsigned arithmetic never wraps.
[[nodiscard]] inline bool native_sm3_static_address_const_index(
    unsigned base, unsigned address, unsigned stageLimit,
    unsigned& index) noexcept {
    index = 0u;
    if (stageLimit == 0u || stageLimit > 256u || base >= stageLimit ||
        address >= stageLimit - base) return false;
    index = base + address;
    return true;
}
} // namespace outrun::vr::dx11
