#pragma once
// Per-D3D9-Draw scalar/partial TEMP origin for the native SM3 shader writer.
// Records only definitely draw-uniform physical lanes. All divergent,
// predicated, texture-derived and undefined writes poison their destination
// lanes, preserving the existing fail-closed D3D9Ex Draw fallback.
#include <array>

namespace outrun::vr::dx11 {
// A real game SM3 M4x4/M4x3/M3x4/M3x3/M3x2 computes dot products
// across immutable per-Draw c# or DEF rows. If its vector came only from
// draw-uniform c#/TEMP lanes, all physically written result lanes may feed
// a quad-uniform IFC and native implicit TEX. Relative c[a0]/c[aL] and
// conditional writes deliberately remain pixel-dependent for admission.
[[nodiscard]] constexpr bool native_sm3_matrix_draw_uniform(
    unsigned rows, unsigned vectorComponents, unsigned writtenMask,
    bool absoluteConstantRows) noexcept {
    const bool dimensions =
        (vectorComponents == 4u && (rows == 4u || rows == 3u)) ||
        (vectorComponents == 3u && (rows == 4u || rows == 3u || rows == 2u));
    return absoluteConstantRows && dimensions && writtenMask != 0u &&
           (writtenMask & ~((1u << rows) - 1u)) == 0u;
}
// Track actual game uniform IF/ELSE writes to TEMP physical lanes, not
// HLSL's zero-initialized placeholders. Divergent arms and BREAK-bearing
// loops never gain uniformity. This does not promote runtime Draw readiness.
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
        masks_[reg] = (masks_[reg] & ~writtenMask) |
            ((allSourcesUniform && straightLine && uniform_flow())
                ? writtenMask : 0u);
    }
    [[nodiscard]] bool begin_if(bool uniform) {
        if (depth_ >= frames_.size()) return false;
        frames_[depth_++] = {false, uniform, false, masks_, {}};
        return true;
    }
    [[nodiscard]] bool otherwise() noexcept {
        if (depth_ == 0u || frames_[depth_ - 1u].loop || frames_[depth_ - 1u].hasElse)
            return false;
        auto& f = frames_[depth_ - 1u];
        f.thenMasks = masks_;
        masks_ = f.entryMasks;
        f.hasElse = true;
        return true;
    }
    [[nodiscard]] bool end_if() noexcept {
        if (depth_ == 0u || frames_[depth_ - 1u].loop) return false;
        const auto f = frames_[depth_ - 1u];
        --depth_;
        const auto& other = f.hasElse ? f.thenMasks : f.entryMasks;
        for (unsigned i = 0u; i < masks_.size(); ++i)
            masks_[i] &= other[i];
        return true;
    }
    [[nodiscard]] bool begin_loop() {
        if (depth_ >= frames_.size()) return false;
        frames_[depth_++] = {true, false, false, masks_, {}};
        return true;
    }
    [[nodiscard]] bool end_loop() noexcept {
        if (depth_ == 0u || !frames_[depth_ - 1u].loop) return false;
        const auto entry = frames_[depth_ - 1u].entryMasks;
        --depth_;
        // BREAK or a dynamic count may skip a loop write; retain only
        // lanes that were definitely uniform both before and after it.
        for (unsigned i = 0u; i < masks_.size(); ++i)
            masks_[i] &= entry[i];
        return true;
    }
    [[nodiscard]] constexpr bool uniform_flow() const noexcept {
        for (unsigned i = 0u; i < depth_; ++i)
            if (frames_[i].loop || !frames_[i].uniform) return false;
        return true;
    }
    [[nodiscard]] bool empty() const noexcept { return depth_ == 0u; }
    constexpr void invalidate(unsigned reg) noexcept {
        if (reg < masks_.size()) masks_[reg] = 0u;
    }
private:
    struct Frame {
        bool loop;
        bool uniform;
        bool hasElse;
        std::array<unsigned, 32> entryMasks;
        std::array<unsigned, 32> thenMasks;
    };
    std::array<unsigned, 32> masks_{};
    std::array<Frame, 8> frames_{};
    unsigned depth_{};
};
} // namespace outrun::vr::dx11
