#pragma once
// Lossless union of one successful game-authored post-Draw D3D9 Clear call.
// All rectangles in the call have the SAME TARGET color and/or Z value:
// only exact rectangular unions may be coalesced before D3D11 GPU replay.
// This keeps large menu/car/race tiled Clears inside the existing 32 GPU
// region budget, without clearing bounding-box gaps or changing D3D9 input.
#include "native_game_source_mutation.hpp"
#include <array>
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
struct GameNativePostDrawClearBatch {
    using Region = GameNativeSourceMutation::TargetClearRect;
    static constexpr std::uint32_t kMaxSourceRects = 128u;
    static constexpr std::uint32_t kMaxGpuRegions =
        GameNativeSourceMutation::kMaxPartialTargetClearRects;

    template<class SourceRect>
    [[nodiscard]] static constexpr bool build(
        std::uint32_t w, std::uint32_t h,
        std::uint32_t vx, std::uint32_t vy,
        std::uint32_t vw, std::uint32_t vh,
        std::uint32_t count, const SourceRect* source,
        std::array<Region, kMaxGpuRegions>& output,
        std::uint32_t& outputCount) noexcept {
        if (count > kMaxSourceRects || (count && !source))
            return false;
        // Stage every original rectangle before native GPU writes. Never
        // falsely reject a 128-strip scene at intermediate 33+ rectangles.
        std::array<Region, kMaxSourceRects> staged{};
        std::uint32_t used = 0u;
        const std::uint32_t n = count ? count : 1u;
        for (std::uint32_t i = 0u; i < n; ++i) {
            const std::int64_t left = count
                ? static_cast<std::int64_t>(source[i].x1) : vx;
            const std::int64_t top = count
                ? static_cast<std::int64_t>(source[i].y1) : vy;
            const std::int64_t right = count
                ? static_cast<std::int64_t>(source[i].x2)
                : static_cast<std::int64_t>(vx) + vw;
            const std::int64_t bottom = count
                ? static_cast<std::int64_t>(source[i].y2)
                : static_cast<std::int64_t>(vy) + vh;
            Region clipped{};
            const auto kind = GameNativeSourceMutation::classify_target_clear_rect(
                left, top, right, bottom, vx, vy, vw, vh, w, h, clipped);
            if (kind == GameNativeSourceMutation::TargetClearClip::Invalid)
                return false;
            if (kind == GameNativeSourceMutation::TargetClearClip::Pixels)
                staged[used++] = clipped;
        }
        // D3D9 Clear's single color and Z permit any intra-call order; all
        // resulting regions have identical pixel values. Remove containment
        // and repeatedly merge only unions that remain exact rectangles.
        const auto covers = [](const Region& a, const Region& b) constexpr {
            return a.left <= b.left && a.top <= b.top &&
                a.right >= b.right && a.bottom >= b.bottom;
        };
        bool changed = true;
        while (changed) {
            changed = false;
            for (std::uint32_t i = 0u; i < used && !changed; ++i) {
                for (std::uint32_t j = i + 1u; j < used; ++j) {
                    Region joined = staged[i];
                    bool mayCombine = false;
                    if (covers(staged[j], joined)) {
                        joined = staged[j];
                        mayCombine = true;
                    } else if (covers(joined, staged[j])) {
                        mayCombine = true;
                    } else {
                        mayCombine = game_native_merge_ordered_overwrite(
                            joined, staged[j]);
                    }
                    if (!mayCombine) continue;
                    staged[i] = joined;
                    for (std::uint32_t k = j + 1u; k < used; ++k)
                        staged[k - 1u] = staged[k];
                    --used;
                    changed = true;
                    break;
                }
            }
        }
        // Unrepresentable fragmented source remains owned by D3D9. A failed
        // transaction has not changed the caller's existing native ledger.
        if (used > kMaxGpuRegions) return false;
        for (std::uint32_t i = 0u; i < used; ++i)
            output[i] = staged[i];
        outputCount = used;
        return true;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
