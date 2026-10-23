#pragma once
// Per-D3D9-Draw scalar/partial TEMP origin for the native SM3 shader writer.
// Records only definitely draw-uniform physical lanes. All divergent,
// predicated, texture-derived and undefined writes poison their destination
// lanes, preserving the existing fail-closed D3D9Ex Draw fallback.
#include <array>

namespace outrun::vr::dx11 {
class NativeSm3TempDrawUniformity final {
public:
    [[nodiscard]] constexpr bool contains(unsigned reg,
                                          unsigned requiredMask) const noexcept {
        return reg < masks_.size() && requiredMask != 0u &&
               (requiredMask & ~0x0fu) == 0u &&
               (masks_[reg] & requiredMask) == requiredMask;
    }
    constexpr void write(unsigned reg, unsigned writtenMask,
                         bool allSourcesUniform, bool straightLine) noexcept {
        if (reg >= masks_.size()) return;
        writtenMask &= 0x0fu;
        // D3D9 destination masks are per lane. A partial varying overwrite
        // cannot erase the provenance of unrelated known-uniform channels.
        masks_[reg] = (masks_[reg] & ~writtenMask) |
                      ((allSourcesUniform && straightLine) ? writtenMask : 0u);
    }
    constexpr void invalidate(unsigned reg) noexcept {
        if (reg < masks_.size()) masks_[reg] = 0u;
    }
private:
    std::array<unsigned, 32> masks_{};
};
} // namespace outrun::vr::dx11
