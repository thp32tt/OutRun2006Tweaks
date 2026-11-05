#pragma once
// Constant-fold genuine game VS 3.0 DEF -> MOVA a0.x -> c[base+a0.x].
// D3D9 MOVA rounds a signed float to the nearest integer. Hardware tie
// rounding is not assumed: ambiguous exact-half literals fail closed.
// Non-DEF/game-dependent a0 and out-of-bank effective addresses stay DX9Ex.
#include <cmath>
#include <cstdint>
#include <cstring>

namespace outrun::vr::dx11 {
[[nodiscard]] inline bool native_sm3_static_mova_address(
    std::uint32_t literalBits, unsigned modifier, int& address) noexcept {
    address = 0;
    if (modifier > 1u) return false; // NONE or NEG; no unmodeled modifiers
    float value = 0.0f;
    static_assert(sizeof(value) == sizeof(literalBits));
    std::memcpy(&value, &literalBits, sizeof(value));
    if (modifier == 1u) value = -value;
    // Bank access cannot require an offset outside [-255,255] when the
    // source register index is in [0,255]. Avoid int overflow/NaN/Inf.
    if (!std::isfinite(value) || value < -255.5f || value > 255.5f)
        return false;
    const float lower = std::floor(value);
    const float fraction = value - lower;
    if (fraction == 0.5f) return false; // unspecified hardware tie behavior
    const float nearest = lower + (fraction > 0.5f ? 1.0f : 0.0f);
    if (nearest < -255.0f || nearest > 255.0f) return false;
    address = static_cast<int>(nearest);
    return true;
}

// Preserve the historical unsigned helper for nonnegative clients; signed
// offsets use the overload above, including genuine negative a0.x.
[[nodiscard]] inline bool native_sm3_static_mova_address(
    std::uint32_t literalBits, unsigned modifier, unsigned& address) noexcept {
    address = 0u;
    int signedAddress = 0;
    if (!native_sm3_static_mova_address(
            literalBits, modifier, signedAddress) || signedAddress < 0)
        return false;
    address = static_cast<unsigned>(signedAddress);
    return true;
}

// A negative signed MOVA offset is legal when the final c[base+a0] is in
// range. Validate AFTER signed addition, never cast negative a0 to unsigned.
[[nodiscard]] inline bool native_sm3_static_address_const_index(
    unsigned base, int address, unsigned stageLimit,
    unsigned& index) noexcept {
    index = 0u;
    if (stageLimit == 0u || stageLimit > 256u || base >= stageLimit)
        return false;
    const auto resolved = static_cast<long long>(base) + address;
    if (resolved < 0 || resolved >= static_cast<long long>(stageLimit))
        return false;
    index = static_cast<unsigned>(resolved);
    return true;
}

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
