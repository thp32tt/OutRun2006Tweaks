#pragma once
#include "native_game_offscreen_color_provenance.hpp"
#include <array>
#include <cstddef>
#include <cstdint>

namespace outrun::vr::dx11 {
// Only successful, source-proven GAME GPU Copy/Stretch destinations may
// contribute to a full native XR eye. A single small menu postpass must
// never be mistaken for the entire game color frame. Keep exact rectangles:
// copying a camera's full source does not certify an unclipped destination.
class NativeGameEyePostpassCoverage final {
public:
    static constexpr std::size_t kCapacity = 32u;
    void reset() noexcept { count_ = 0u; }
    void record(NativeGameOffscreenColorRegion region) noexcept {
        if (!native_game_offscreen_color_region_valid(region)) return;
        // Collapse only exact rectangular unions, including bridged strips.
        // This never fills an L-shaped corner, a foreign patch or a gap.
        bool merged = true;
        while (merged) {
            merged = false;
            for (std::size_t i = 0u; i < count_; ++i) {
                NativeGameOffscreenColorRegion joined{};
                if (!native_game_offscreen_exact_rect_union(
                        region, regions_[i], joined)) continue;
                region = joined;
                regions_[i] = regions_[--count_];
                merged = true;
                break;
            }
        }
        if (count_ < kCapacity) {
            regions_[count_++] = region;
            return;
        }
        // Overlapping camera tiles may form an exact non-slicing mosaic.
        // Admit it ONLY if their real pixel union covers its full envelope.
        // Otherwise drop this additional proof and keep the D3D9 fallback.
        const auto mosaic = native_game_offscreen_color_mosaic_compaction(
            region, regions_, count_);
        if (mosaic.left == region.left && mosaic.top == region.top &&
            mosaic.right == region.right && mosaic.bottom == region.bottom)
            return;
        std::size_t kept = 0u;
        for (std::size_t i = 0u; i < count_; ++i) {
            const auto& old = regions_[i];
            if (old.left >= mosaic.left && old.top >= mosaic.top &&
                old.right <= mosaic.right && old.bottom <= mosaic.bottom)
                continue;
            regions_[kept++] = old;
        }
        count_ = kept;
        if (count_ < kCapacity) regions_[count_++] = mosaic;
    }
    // Chronological native game GPU compositing: a later unproven but
    // otherwise valid game Copy/Stretch really overwrites destination pixels.
    // Remove only those pixels from earlier proven postpasses. Keeping the
    // old proof would publish a partially foreign menu/vehicle/race XR eye.
    // Preserve unaffected tiles, with a conservative reset on fragmentation
    // overflow so the authoritative D3D9 renderer remains the fallback.
    // Return whether the exact remaining region ledger was retained.
    // A proven-color ledger may safely drop all proof on overflow, but an
    // *unproven* overwrite ledger must latch fail-closed instead.
    bool invalidate(NativeGameOffscreenColorRegion overwritten) noexcept {
        if (!native_game_offscreen_color_region_valid(overwritten) || !count_)
            return true;
        std::array<NativeGameOffscreenColorRegion, kCapacity> survivors{};
        std::size_t kept = 0u;
        const auto retain = [&](NativeGameOffscreenColorRegion fragment) noexcept {
            if (!native_game_offscreen_color_region_valid(fragment))
                return true;
            if (kept >= kCapacity) return false;
            survivors[kept++] = fragment;
            return true;
        };
        for (std::size_t i = 0u; i < count_; ++i) {
            const auto existing = regions_[i];
            if (!native_game_offscreen_color_regions_intersect(existing, overwritten)) {
                if (!retain(existing)) { reset(); return false; }
                continue;
            }
            const NativeGameOffscreenColorRegion hit{
                (std::max)(existing.left, overwritten.left),
                (std::max)(existing.top, overwritten.top),
                (std::min)(existing.right, overwritten.right),
                (std::min)(existing.bottom, overwritten.bottom)};
            // Disjoint strips are the EXACT rectangle difference, including
            // a hole fully inside a valid camera composite. Never replace
            // them with an enclosing (falsely color-proven) bounding box.
            if (!retain({existing.left, existing.top, existing.right, hit.top}) ||
                !retain({existing.left, hit.bottom, existing.right, existing.bottom}) ||
                !retain({existing.left, hit.top, hit.left, hit.bottom}) ||
                !retain({hit.right, hit.top, existing.right, hit.bottom})) {
                reset();
                return false;
            }
        }
        regions_ = survivors;
        count_ = kept;
        return true;
    }
    [[nodiscard]] bool empty() const noexcept { return count_ == 0u; }
    [[nodiscard]] bool at_capacity() const noexcept { return count_ >= kCapacity; }
    [[nodiscard]] bool full_eye(std::uint32_t width,
                                std::uint32_t height) const noexcept {
        if (!width || !height || !count_) return false;
        return native_game_offscreen_color_region_fully_covered(
            {0u, 0u, width, height}, regions_, count_);
    }
private:
    std::array<NativeGameOffscreenColorRegion, kCapacity> regions_{};
    std::size_t count_{};
};
// Real game GPU composites can replace authentic native-eye Draw/Clear
// pixels after those commands executed. Track this physical chronology
// separately from source draw counters: an untracked GPU overwrite requires
// a later completely proven camera repaint or a newer full TARGET Clear.
class NativeGameEyeColorChronology final {
public:
    void reset_after_full_target_clear() noexcept {
        postpasses_.reset();
        unprovenGpuRegions_.reset();
        unknownLedgerOverflow_ = false;
        completeUnknownReplacement_ = false;
    }
    // Physically later native GPU camera pixels supersede earlier foreign
    // pixels, but only for their exact clipped destination rectangle.
    void record_proven_gpu_postpass(NativeGameOffscreenColorRegion dest) noexcept {
        if (!native_game_offscreen_color_region_valid(dest)) return;
        if (!unprovenGpuRegions_.invalidate(dest))
            unknownLedgerOverflow_ = true;
        postpasses_.record(dest);
        if (unprovenGpuRegions_.empty() && !unknownLedgerOverflow_)
            completeUnknownReplacement_ = false;
    }
    // Actual game TARGET Clears repaint their clipped pixels. They do not
    // constitute a camera Copy/Stretch, so they must REMOVE rather than
    // manufacture source-proven GPU postpass coverage.
    void record_authored_target_clear(NativeGameOffscreenColorRegion dest) noexcept {
        if (!native_game_offscreen_color_region_valid(dest)) return;
        (void)postpasses_.invalidate(dest);
        if (!unprovenGpuRegions_.invalidate(dest))
            unknownLedgerOverflow_ = true;
        if (unprovenGpuRegions_.empty() && !unknownLedgerOverflow_)
            completeUnknownReplacement_ = false;
    }
    void record_unproven_gpu_postpass(
        NativeGameOffscreenColorRegion dest,
        std::uint32_t eyeWidth = 0u, std::uint32_t eyeHeight = 0u) noexcept {
        if (!native_game_offscreen_color_region_valid(dest)) return;
        (void)postpasses_.invalidate(dest);
        // Later partial geometry cannot prove it repainted the foreign
        // region. Keep the native XR frame fail-closed until source-proven
        // GPU work covers the entire eye, or a real full-eye Clear resets it.
        // Separate the GPU region covered by the unverified intermediate
        // from unrelated native scene Draw/Clear pixels. Small, real game
        // postpasses are valid overlays over an existing native scene, while
        // a complete unverified eye replacement cannot certify that scene.
        // On ledger saturation fail closed instead of dropping any unknown
        // source rectangles and manufacturing coverage.
        if (unprovenGpuRegions_.at_capacity())
            unknownLedgerOverflow_ = true;
        unprovenGpuRegions_.record(dest);
        // Once untracked GPU work has physically replaced the entire eye,
        // a later tiny authentic paint cannot make the unknown remainder safe.
        // Latch this fact across subsequent partial Clear/Copy/Stretch writes;
        // clear it only after every unknown pixel was actually repainted.
        if (eyeWidth && eyeHeight &&
            unprovenGpuRegions_.full_eye(eyeWidth, eyeHeight))
            completeUnknownReplacement_ = true;
    }
    [[nodiscard]] bool full_postpass_eye(std::uint32_t width,
                                         std::uint32_t height) const noexcept {
        return postpasses_.full_eye(width, height);
    }
    [[nodiscard]] bool publication_safe(std::uint32_t width,
                                        std::uint32_t height) const noexcept {
        return (!unknownLedgerOverflow_ && !completeUnknownReplacement_ &&
                !unprovenGpuRegions_.full_eye(width, height)) ||
               postpasses_.full_eye(width, height);
    }
private:
    NativeGameEyePostpassCoverage postpasses_{};
    NativeGameEyePostpassCoverage unprovenGpuRegions_{};
    bool unknownLedgerOverflow_{};
    bool completeUnknownReplacement_{};
};
} // namespace outrun::vr::dx11
