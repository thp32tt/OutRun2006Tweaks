#pragma once
// Authentic D3D9 Present source-crop coverage for the opt-in native GPU tile.
// The caller verifies each dirty rectangle's bounds and union; a populated
// dirty-region pointer alone is NOT evidence that the game will present our
// overlay. Do not use this for full native frame or stereo publication.
namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_raw_preview_present_coverage(
    bool hasDirtyRegion, bool fullBackbufferCovered,
    bool sourceCropCovered, bool sourceCropPartitionCovered) noexcept {
    return !hasDirtyRegion || fullBackbufferCovered ||
           sourceCropCovered || sourceCropPartitionCovered;
}

} // namespace outrun::vr::dx11

// A D3D9 Present may repaint only a small menu/car/race dirty subset.
// In RAW mode, check the ACTUAL selected diagnostic destination tile rather
// than requiring the full game crop to be dirty. This grants no full-frame
// or OpenXR publication and cannot accept a bounding RECT with holes.
#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include "native_game_raw_partial_present_tile.hpp"
#include "native_game_raw_changed_pixel_window.hpp"
namespace outrun::vr::dx11 {
struct NativeRawPresentDirtyRect {
    std::int64_t left{}, top{}, right{}, bottom{};
};
struct NativeRawPresentDirtyRegion {
    static constexpr std::uint32_t kMaxRects = 32u;
    bool headerVerified = false;
    std::uint32_t count{};
    std::int64_t boundLeft{}, boundTop{}, boundRight{}, boundBottom{};
    NativeRawPresentDirtyRect rectangles[kMaxRects]{};
};
[[nodiscard]] constexpr bool native_raw_dirty_region_covers_tile(
    std::uint32_t backWidth, std::uint32_t backHeight,
    const NativeRawPresentDirtyRegion& region,
    const NativeRawPresentTile& tile) noexcept {
    constexpr auto kMax = static_cast<std::uint32_t>(
        (std::numeric_limits<std::int32_t>::max)());
    if (!region.headerVerified || region.count == 0u ||
        region.count > NativeRawPresentDirtyRegion::kMaxRects ||
        !backWidth || !backHeight || backWidth > kMax || backHeight > kMax ||
        tile.copyWidth == 0u || tile.copyHeight == 0u ||
        tile.copyWidth > backWidth || tile.copyHeight > backHeight ||
        tile.destinationX < 0 || tile.destinationY < 0 ||
        tile.destinationX > static_cast<std::int64_t>(backWidth - tile.copyWidth) ||
        tile.destinationY > static_cast<std::int64_t>(backHeight - tile.copyHeight) ||
        region.boundLeft < 0 || region.boundTop < 0 ||
        region.boundRight <= region.boundLeft ||
        region.boundBottom <= region.boundTop ||
        region.boundRight > backWidth || region.boundBottom > backHeight)
        return false;
    std::int64_t minX = backWidth, minY = backHeight, maxX = 0, maxY = 0;
    for (std::uint32_t i = 0u; i < region.count; ++i) {
        const auto& r = region.rectangles[i];
        if (r.left < 0 || r.top < 0 || r.right <= r.left ||
            r.bottom <= r.top || r.right > backWidth || r.bottom > backHeight)
            return false;
        if (r.left < minX) minX = r.left;
        if (r.top < minY) minY = r.top;
        if (r.right > maxX) maxX = r.right;
        if (r.bottom > maxY) maxY = r.bottom;
    }
    // Validate rcBound against the actual rectangle population. A forged
    // full-crop bounding box alone must never authorize a RAW pixel upload.
    if (minX != region.boundLeft || minY != region.boundTop ||
        maxX != region.boundRight || maxY != region.boundBottom)
        return false;
    const auto right = tile.destinationX + tile.copyWidth;
    const auto bottom = tile.destinationY + tile.copyHeight;
    std::int64_t x = tile.destinationX;
    while (x < right) {
        std::int64_t nextX = right;
        for (std::uint32_t i = 0u; i < region.count; ++i) {
            const auto& r = region.rectangles[i];
            if (r.left > x && r.left < nextX) nextX = r.left;
            if (r.right > x && r.right < nextX) nextX = r.right;
        }
        if (nextX <= x) return false;
        std::int64_t y = tile.destinationY;
        for (std::uint32_t step = 0u; step < region.count && y < bottom; ++step) {
            std::int64_t reach = y;
            for (std::uint32_t i = 0u; i < region.count; ++i) {
                const auto& r = region.rectangles[i];
                if (r.left <= x && r.right >= nextX &&
                    r.top <= y && r.bottom > reach)
                    reach = r.bottom < bottom ? r.bottom : bottom;
            }
            if (reach == y) return false;
            y = reach;
        }
        if (y != bottom) return false;
        x = nextX;
    }
    return true;
}
// An exact, original-screen source-only batch paints directly from the
// canonical backbuffer and never needs a displaced RAW diagnostic tile.
// Requiring legacy 24px placement here rejects genuine 1..23px D3D9 dirty
// menu/HUD Presents before their authenticated GPU RGB can be uploaded.
[[nodiscard]] constexpr bool native_raw_requires_legacy_dirty_placement(
    bool dirtyPresent, bool fullRepaintVerified,
    bool authenticatedSourceOnly) noexcept {
    return dirtyPresent && !fullRepaintVerified && !authenticatedSourceOnly;
}
// A small game source crop may be repainted by an authentic D3D9 dirty
// RGNDATA union even when the Present caller did not certify a full repaint.
// Prove every pixel of the VISIBLE crop, not rcBound or an intersecting
// rectangle. The GPU/source backbuffer identity check remains at the caller;
// this grants no displaced inset or full-game-frame authorization.
[[nodiscard]] constexpr bool native_raw_dirty_covers_small_source_crop(
    std::uint32_t backWidth, std::uint32_t backHeight,
    std::int64_t left, std::int64_t top,
    std::int64_t right, std::int64_t bottom,
    const NativeRawPresentDirtyRegion& dirty) noexcept {
    if (left < 0 || top < 0 || right <= left || bottom <= top ||
        right > static_cast<std::int64_t>(backWidth) ||
        bottom > static_cast<std::int64_t>(backHeight) ||
        (right - left >= 40 && bottom - top >= 40))
        return false;
    const NativeRawPresentTile crop{
        0u, 0u, static_cast<std::uint32_t>(right - left),
        static_cast<std::uint32_t>(bottom - top), left, top};
    return native_raw_dirty_region_covers_tile(
        backWidth, backHeight, dirty, crop);
}
// A large original D3D9 Present may contain a single 1px/short menu dirty
// member. Legacy displaced RAW placement cannot fit there, but a source-owned
// D3D11 Draw can still put its real RGB at that SAME original game pixel.
// Admit only a deferred SOURCE-ALIGNED batch after the caller has checked the
// Draw/Present canonical surface identity. This does not itself authorize a
// pixel upload: the batch must still prove per-pixel GPU RGB and complete
// original RGNDATA coverage, or Present fails closed without an inset.
[[nodiscard]] constexpr bool native_raw_source_only_dirty_crop_can_defer_placement(
    bool canonicalDrawPresentIdentity,
    std::uint32_t sourceTargetWidth, std::uint32_t sourceTargetHeight,
    std::uint32_t backWidth, std::uint32_t backHeight,
    std::int64_t cropLeft, std::int64_t cropTop,
    std::int64_t cropRight, std::int64_t cropBottom,
    const NativeRawPresentDirtyRegion& dirty) noexcept {
    if (!canonicalDrawPresentIdentity || !backWidth || !backHeight ||
        sourceTargetWidth != backWidth || sourceTargetHeight != backHeight ||
        cropLeft < 0 || cropTop < 0 ||
        cropRight <= cropLeft || cropBottom <= cropTop ||
        cropRight > backWidth || cropBottom > backHeight ||
        !dirty.headerVerified || !dirty.count ||
        dirty.count > NativeRawPresentDirtyRegion::kMaxRects)
        return false;
    // Validate ALL members and rcBound using the existing exact-coverage
    // contract. Only a real member overlapping the Present source crop can
    // serve as the seed. A broad rcBound, malformed member or hole cannot.
    for (std::uint32_t i = 0u; i < dirty.count; ++i) {
        const auto& r = dirty.rectangles[i];
        const auto l = (std::max)(cropLeft, r.left);
        const auto t = (std::max)(cropTop, r.top);
        const auto right = (std::min)(cropRight, r.right);
        const auto bottom = (std::min)(cropBottom, r.bottom);
        if (right <= l || bottom <= t) continue;
        const NativeRawPresentTile seed{
            0u, 0u, static_cast<std::uint32_t>(right - l),
            static_cast<std::uint32_t>(bottom - t), l, t};
        if (native_raw_dirty_region_covers_tile(
                backWidth, backHeight, dirty, seed)) return true;
    }
    return false;
}
// A declaration permits bounded disjoint-crop selection before the shared
// destination-overlap helper definition below.
[[nodiscard]] constexpr bool native_raw_disjoint_present_tiles(
    const NativeRawPresentTile&, const NativeRawPresentTile&) noexcept;
// Keep real D3D11 changed RGB on its ORIGINAL D3D9 screen coordinate
// when a small game dirty island intersects only part of a larger capture.
// Candidate source bytes are an unscaled subset of the SAME GPU capture;
// never move pixels into a different game coordinate or claim a full frame.
[[nodiscard]] inline bool native_raw_dirty_source_rgb_crop(
    std::uint32_t backWidth, std::uint32_t backHeight,
    const NativeRawPresentDirtyRegion& dirty,
    const NativeRawPresentTile& sourceAligned,
    const NativeRawChangedPixelWindow& gpuDelta,
    NativeRawPresentTile& cropped,
    std::uint32_t& changedRgb,
    const NativeRawPresentTile* exclude = nullptr,
    std::uint32_t excludeCount = 1u,
    bool preferSolidRgb = false) noexcept {
    cropped = {};
    changedRgb = 0u;
    if (!sourceAligned.copyWidth || !sourceAligned.copyHeight ||
        sourceAligned.destinationX < 0 || sourceAligned.destinationY < 0 ||
        sourceAligned.copyWidth > backWidth ||
        sourceAligned.copyHeight > backHeight ||
        sourceAligned.destinationX >
            std::int64_t{backWidth - sourceAligned.copyWidth} ||
        sourceAligned.destinationY >
            std::int64_t{backHeight - sourceAligned.copyHeight} ||
        !dirty.headerVerified || !dirty.count ||
        dirty.count > NativeRawPresentDirtyRegion::kMaxRects ||
        (exclude && (!excludeCount || excludeCount > 4u)))
        return false;
    // Exclusion is a claim of a previous original-game upload. Reject
    // foreign/forged destination claims before considering any fragments.
    if (exclude)
        for (std::uint32_t i = 0u; i < excludeCount; ++i)
            if (!native_raw_dirty_region_covers_tile(
                    backWidth, backHeight, dirty, exclude[i]))
                return false;
    const auto right = sourceAligned.destinationX + sourceAligned.copyWidth;
    const auto bottom = sourceAligned.destinationY + sourceAligned.copyHeight;
    std::uint64_t bestArea = 0u;
    // A single authentic game repaint can be split into several RGNDATA
    // rectangles. The old per-member selection discarded RGB from adjoining
    // fragments, even though their whole union reached the D3D9 Present.
    // Proposals below never confer visibility: validate the ORIGINAL entire
    // dirty region, the exact candidate pixels, and the native GPU RGB delta.
    const auto evaluateCandidate = [&](std::int64_t left, std::int64_t top,
                              std::int64_t rectRight,
                              std::int64_t rectBottom) noexcept {
        const auto l = (std::max)(sourceAligned.destinationX, left);
        const auto t = (std::max)(sourceAligned.destinationY, top);
        const auto r = (std::min)(right, rectRight);
        const auto b = (std::min)(bottom, rectBottom);
        if (r <= l || b <= t) return;
        NativeRawPresentTile candidate = sourceAligned;
        const auto offsetX = static_cast<std::uint64_t>(
            l - sourceAligned.destinationX);
        const auto offsetY = static_cast<std::uint64_t>(
            t - sourceAligned.destinationY);
        if (offsetX > (std::numeric_limits<std::uint32_t>::max)() -
                          sourceAligned.sourceX ||
            offsetY > (std::numeric_limits<std::uint32_t>::max)() -
                          sourceAligned.sourceY) return;
        candidate.sourceX += static_cast<std::uint32_t>(offsetX);
        candidate.sourceY += static_cast<std::uint32_t>(offsetY);
        candidate.copyWidth = static_cast<std::uint32_t>(r - l);
        candidate.copyHeight = static_cast<std::uint32_t>(b - t);
        candidate.destinationX = l;
        candidate.destinationY = t;
        // A single real GPU Draw can modify two different original menu
        // repaint islands. The second upload must not overwrite a pixel of
        // the first exact-source upload, nor claim an inert RGB region.
        // Every earlier source-aligned GPU upload reserves its destination.
        // Multi-island batches never widen across an original D3D9 dirty gap.
        for (std::uint32_t i = 0u; exclude && i < excludeCount; ++i)
            if (!native_raw_disjoint_present_tiles(candidate, exclude[i]))
                return;
        auto rgb = gpuDelta.changed_pixels(candidate);
        if (!rgb || rgb < changedRgb ||
            (preferSolidRgb && rgb == changedRgb)) return;
        if (!native_raw_dirty_region_covers_tile(
                backWidth, backHeight, dirty, candidate)) return;
        // RAW multi-Draw presentation is bounded by four independent
        // source-aligned uploads. Ranking a sparse repaint by total RGB
        // BEFORE extracting its largest solid GPU island can spend a slot
        // on one pixel while missing a smaller, genuinely dense menu/car
        // repaint in another disjoint D3D9 dirty rectangle.
        // Rank the actual uploadable rectangle, never its sparse envelope.
        if (preferSolidRgb &&
            std::uint64_t{candidate.copyWidth} * candidate.copyHeight != rgb) {
            NativeRawPresentTile solid{};
            std::uint32_t solidRgb = 0u;
            if (!gpuDelta.select_solid_rgb_tile(
                    candidate, solid, solidRgb) || !solidRgb ||
                !native_raw_dirty_region_covers_tile(
                    backWidth, backHeight, dirty, solid))
                return;
            candidate = solid;
            rgb = solidRgb;
        }
        const auto area = std::uint64_t{candidate.copyWidth} *
                          candidate.copyHeight;
        if (rgb < changedRgb ||
            (rgb == changedRgb && area <= bestArea)) return;
        cropped = candidate;
        changedRgb = rgb;
        bestArea = area;
    };
    // Two real Draw source rectangles can overlap but affect different RGB
    // pixels. Subtract earlier source-aligned uploads, preserving later GPU
    // source coordinates and original game Present dirty-region coverage.
    const auto consider = [&](std::int64_t left, std::int64_t top,
                              std::int64_t rectRight,
                              std::int64_t rectBottom) noexcept {
        const auto l = (std::max)(sourceAligned.destinationX, left);
        const auto t = (std::max)(sourceAligned.destinationY, top);
        const auto r = (std::min)(right, rectRight);
        const auto b = (std::min)(bottom, rectBottom);
        if (r <= l || b <= t) return;
        if (!exclude) {
            evaluateCandidate(l, t, r, b);
            return;
        }
        bool intersects = false;
        for (std::uint32_t i = 0u; i < excludeCount; ++i) {
            const auto& q = exclude[i];
            if (l < q.destinationX + q.copyWidth && r > q.destinationX &&
                t < q.destinationY + q.copyHeight && b > q.destinationY) {
                intersects = true;
                break;
            }
        }
        if (!intersects) {
            evaluateCandidate(l, t, r, b);
            return;
        }
        // Four exclusions create at most 1+3*4 disjoint pieces. No heap
        // allocation, uncertain coverage or partial overflow acceptance.
        constexpr std::size_t kMaxPieces = 13u;
        std::array<NativeRawPresentDirtyRect, kMaxPieces> pieces{}, next{};
        pieces[0] = {l, t, r, b};
        std::size_t count = 1u;
        for (std::uint32_t i = 0u; i < excludeCount; ++i) {
            const auto& q = exclude[i];
            const auto ql = q.destinationX, qt = q.destinationY;
            const auto qr = ql + q.copyWidth, qb = qt + q.copyHeight;
            std::size_t n = 0u;
            bool overflow = false;
            const auto push = [&](std::int64_t x0, std::int64_t y0,
                                  std::int64_t x1, std::int64_t y1) noexcept {
                if (x0 >= x1 || y0 >= y1) return;
                if (n >= kMaxPieces) { overflow = true; return; }
                next[n++] = {x0, y0, x1, y1};
            };
            for (std::size_t j = 0u; j < count; ++j) {
                const auto& p = pieces[j];
                const auto il = (std::max)(p.left, ql);
                const auto it = (std::max)(p.top, qt);
                const auto ir = (std::min)(p.right, qr);
                const auto ib = (std::min)(p.bottom, qb);
                if (il >= ir || it >= ib) {
                    push(p.left, p.top, p.right, p.bottom);
                    continue;
                }
                push(p.left, p.top, p.right, it);
                push(p.left, ib, p.right, p.bottom);
                push(p.left, it, il, ib);
                push(ir, it, p.right, ib);
            }
            if (overflow || !n) return;
            pieces = next;
            count = n;
        }
        for (std::size_t j = 0u; j < count; ++j) {
            const auto& p = pieces[j];
            evaluateCandidate(p.left, p.top, p.right, p.bottom);
        }
    };
    // Keep the original single-rectangle fast path and its stable tie-break.
    for (std::uint32_t i = 0u; i < dirty.count; ++i) {
        const auto& r = dirty.rectangles[i];
        consider(r.left, r.top, r.right, r.bottom);
    }
    // Two overlapping/touching dirty members may represent one original
    // game pixel island, or a useful rectangular portion of an L-shape.
    // At most 496 pair candidates; no guessed destination, resampling or
    // full-frame publication. A hole between them always fails union proof.
    for (std::uint32_t i = 0u; i < dirty.count; ++i) {
        const auto& a = dirty.rectangles[i];
        for (std::uint32_t j = i + 1u; j < dirty.count; ++j) {
            const auto& b = dirty.rectangles[j];
            if (a.left > b.right || b.left > a.right ||
                a.top > b.bottom || b.top > a.bottom)
                continue;
            consider((std::min)(a.left, b.left),
                     (std::min)(a.top, b.top),
                     (std::max)(a.right, b.right),
                     (std::max)(a.bottom, b.bottom));
        }
    }
    // Menus can split one STRIP into three or more adjacent dirty members.
    // A bounded connected-component traversal proposes their common bounds;
    // strict per-pixel union verification rejects L-shaped holes and
    // out-of-bounds / forged rcBound even for a connected component.
    bool visited[NativeRawPresentDirtyRegion::kMaxRects]{};
    for (std::uint32_t seed = 0u; seed < dirty.count; ++seed) {
        if (visited[seed]) continue;
        std::uint32_t queue[NativeRawPresentDirtyRegion::kMaxRects]{seed};
        std::uint32_t read = 0u, size = 1u;
        visited[seed] = true;
        auto left = dirty.rectangles[seed].left;
        auto top = dirty.rectangles[seed].top;
        auto rectRight = dirty.rectangles[seed].right;
        auto rectBottom = dirty.rectangles[seed].bottom;
        while (read < size) {
            const auto& current = dirty.rectangles[queue[read++]];
            for (std::uint32_t j = 0u; j < dirty.count; ++j) {
                if (visited[j]) continue;
                const auto& next = dirty.rectangles[j];
                if (next.left > current.right ||
                    next.right < current.left ||
                    next.top > current.bottom ||
                    next.bottom < current.top)
                    continue;
                visited[j] = true;
                queue[size++] = j;
                left = (std::min)(left, next.left);
                top = (std::min)(top, next.top);
                rectRight = (std::max)(rectRight, next.right);
                rectBottom = (std::max)(rectBottom, next.bottom);
            }
        }
        if (size > 1u) consider(left, top, rectRight, rectBottom);
    }

    // A genuine repaint can be partitioned in BOTH axes (menu tiles or
    // vehicle-selection panels) with an attached narrow update. Its connected
    // bounds have unpainted holes, and neither individual member nor pair
    // can retain RGB on opposite corners of the authenticated 2-D island.
    // Propose a rectangle between two ORIGINAL D3D9 member corners, then
    // require exact pixel coverage of the FULL original RGNDATA and real
    // D3D11 PRE/POST RGB before source-coincident D3D9 UpdateSurface.
    //
    // Bound the extra search to 32*32 proposals, and avoid the sweep when
    // the existing path has already retained all observed source RGB.
    // No guessed pixels, extent scaling or full-frame/eye publication.
    const auto allSourceRgb = gpuDelta.changed_pixels(sourceAligned);
    if (changedRgb < allSourceRgb) {
        for (std::uint32_t start = 0u; start < dirty.count; ++start) {
            const auto& first = dirty.rectangles[start];
            for (std::uint32_t end = 0u; end < dirty.count; ++end) {
                const auto& last = dirty.rectangles[end];
                if (first.left >= last.right || first.top >= last.bottom)
                    continue;
                consider(first.left, first.top, last.right, last.bottom);
                if (changedRgb == allSourceRgb) break;
            }
            if (changedRgb == allSourceRgb) break;
        }
    }
    return changedRgb > 0u;
}
// Use the WHOLE authenticated D3D11 PRE/POST capture when selecting RAW
// source-coincident game pixels. An earlier small diagnostic display window
// may contain only one of several disjoint menu/car RGB updates. Clip the
// captured physical game coordinates to the real D3D9 Present source crop,
// retaining source offsets for the mapped GPU staging bytes. Dirty RGNDATA
// and per-pixel delta are checked independently before ANY UpdateSurface.
[[nodiscard]] constexpr bool native_raw_source_capture_clip_tile(
    std::uint32_t captureOriginX, std::uint32_t captureOriginY,
    std::uint32_t captureWidth, std::uint32_t captureHeight,
    std::uint32_t sourceTargetWidth, std::uint32_t sourceTargetHeight,
    std::uint32_t backWidth, std::uint32_t backHeight,
    std::int64_t cropLeft, std::int64_t cropTop,
    std::int64_t cropRight, std::int64_t cropBottom,
    NativeRawPresentTile& clipped) noexcept {
    clipped = {};
    if (!captureWidth || !captureHeight ||
        captureWidth > NativeRawChangedPixelWindow::kWidth ||
        captureHeight > NativeRawChangedPixelWindow::kHeight ||
        !backWidth || !backHeight ||
        sourceTargetWidth != backWidth || sourceTargetHeight != backHeight ||
        captureOriginX > sourceTargetWidth ||
        captureOriginY > sourceTargetHeight ||
        captureWidth > sourceTargetWidth - captureOriginX ||
        captureHeight > sourceTargetHeight - captureOriginY ||
        cropLeft < 0 || cropTop < 0 || cropRight <= cropLeft ||
        cropBottom <= cropTop || cropRight > backWidth ||
        cropBottom > backHeight)
        return false;
    const auto l = (std::max)(std::int64_t{captureOriginX}, cropLeft);
    const auto t = (std::max)(std::int64_t{captureOriginY}, cropTop);
    const auto r = (std::min)(
        std::int64_t{captureOriginX} + captureWidth, cropRight);
    const auto b = (std::min)(
        std::int64_t{captureOriginY} + captureHeight, cropBottom);
    if (r <= l || b <= t) return false;
    clipped.sourceX = static_cast<std::uint32_t>(
        l - static_cast<std::int64_t>(captureOriginX));
    clipped.sourceY = static_cast<std::uint32_t>(
        t - static_cast<std::int64_t>(captureOriginY));
    clipped.copyWidth = static_cast<std::uint32_t>(r - l);
    clipped.copyHeight = static_cast<std::uint32_t>(b - t);
    clipped.destinationX = l;
    clipped.destinationY = t;
    return true;
}
// A full-source repaint can legitimately carry several independent native
// Draw RGB islands even when D3D9 passes no RGNDATA. Admit its source crop
// as ONE painted region only after the original Present caller has verified
// complete repaint; otherwise never synthesize dirty game pixels. The same
// exact RGB-delta and source-coincident batch admission applies afterward.
[[nodiscard]] constexpr bool native_raw_verified_full_source_crop_region(
    bool fullRepaintVerified, std::uint32_t backWidth,
    std::uint32_t backHeight, std::int64_t cropLeft,
    std::int64_t cropTop, std::int64_t cropRight,
    std::int64_t cropBottom,
    NativeRawPresentDirtyRegion& repaint) noexcept {
    repaint = {};
    const auto maxDim = static_cast<std::uint32_t>(
        (std::numeric_limits<std::int32_t>::max)());
    if (!fullRepaintVerified || !backWidth || !backHeight ||
        backWidth > maxDim || backHeight > maxDim ||
        cropLeft < 0 || cropTop < 0 ||
        cropRight <= cropLeft || cropBottom <= cropTop ||
        cropRight > backWidth || cropBottom > backHeight)
        return false;
    repaint.headerVerified = true;
    repaint.count = 1u;
    repaint.boundLeft = cropLeft;
    repaint.boundTop = cropTop;
    repaint.boundRight = cropRight;
    repaint.boundBottom = cropBottom;
    repaint.rectangles[0] = {
        cropLeft, cropTop, cropRight, cropBottom};
    return true;
}
// Preserve independently sampled genuine GPU Draw RGB islands in one bounded
// D3D9 Present transaction. Both source captures must already be authenticated
// to the same canonical game backbuffer, crop and Present epoch by the caller.
// A batch never fabricates full-frame or stereo coverage.
struct NativeRawSourceIslandBatch {
    static constexpr std::uint32_t kMaxIslands = 4u;
    std::array<NativeRawPresentTile, kMaxIslands> tiles{};
    std::array<std::uint32_t, kMaxIslands> rgbPixels{};
    std::array<bool, kMaxIslands> alternate{};
    std::uint32_t count = 0u;

    [[nodiscard]] bool append(
        std::uint32_t backWidth, std::uint32_t backHeight,
        const NativeRawPresentDirtyRegion& dirty,
        const NativeRawPresentTile& sourceAligned,
        const NativeRawChangedPixelWindow& sourceRgb,
        bool fromAlternate, bool tightRgbExtent = false) noexcept {
        if (count == kMaxIslands) return false;
        NativeRawPresentTile next{};
        std::uint32_t changed = 0u;
        if (!native_raw_dirty_source_rgb_crop(
                backWidth, backHeight, dirty, sourceAligned, sourceRgb,
                next, changed, count ? tiles.data() : nullptr,
                count ? count : 1u, tightRgbExtent))
            return false;
        // Shrink GPU-authentic pixels before claiming original game dirty
        // destinations. Keep inherited callers unchanged until they opt in.
        if (tightRgbExtent) {
            NativeRawPresentTile tight{};
            std::uint32_t trueRgb = 0u;
            if (!sourceRgb.tighten_to_rgb_bounds(next, tight, trueRgb) ||
                trueRgb != changed ||
                !native_raw_dirty_region_covers_tile(
                    backWidth, backHeight, dirty, tight))
                return false;
            for (std::uint32_t i = 0u; i < count; ++i)
                if (!native_raw_disjoint_present_tiles(tight, tiles[i]))
                    return false;
            // The dense-selection path returns an exact native RGB rectangle;
            // this remains a fail-closed check for legacy and future callers.
            // A tight bounding box can still contain an unchanged gap.
            // If another Draw changes RGB inside that gap, reserving the
            // whole box drops authentic source pixels from the later Draw.
            // Commit only a fully native-RGB rectangle and let the remaining
            // bounded slots recover other real islands on later append calls.
            if (std::uint64_t{tight.copyWidth} * tight.copyHeight != trueRgb) {
                NativeRawPresentTile solid{};
                std::uint32_t solidRgb = 0u;
                if (!sourceRgb.select_solid_rgb_tile(
                        tight, solid, solidRgb) || !solidRgb ||
                    !native_raw_dirty_region_covers_tile(
                        backWidth, backHeight, dirty, solid))
                    return false;
                tight = solid;
                changed = solidRgb;
            }
            next = tight;
        }
        tiles[count] = next;
        rgbPixels[count] = changed;
        alternate[count] = fromAlternate;
        ++count;
        return true;
    }
};
// Two individually source-authenticated native Draw crops can have
// DIFFERENT widths/heights after exact D3D9 dirty-island clipping. Their
// pixels are still independent and safe to show together when nonoverlapping.
// Callers verify each source, pixel delta, dirty union and backbuffer bounds.
[[nodiscard]] constexpr bool native_raw_disjoint_present_tiles(
    const NativeRawPresentTile& a, const NativeRawPresentTile& b) noexcept {
    if (!a.copyWidth || !a.copyHeight || !b.copyWidth || !b.copyHeight ||
        a.destinationX < 0 || a.destinationY < 0 ||
        b.destinationX < 0 || b.destinationY < 0)
        return false;
    const auto ax = static_cast<std::uint64_t>(a.destinationX);
    const auto ay = static_cast<std::uint64_t>(a.destinationY);
    const auto bx = static_cast<std::uint64_t>(b.destinationX);
    const auto by = static_cast<std::uint64_t>(b.destinationY);
    return ax + a.copyWidth <= bx || bx + b.copyWidth <= ax ||
           ay + a.copyHeight <= by || by + b.copyHeight <= ay;
}
// Legacy displaced inset pairs still require equal dimensions: the two
// native captures share one fixed GPU staging shape in that path.
[[nodiscard]] constexpr bool native_raw_disjoint_equal_tiles(
    const NativeRawPresentTile& a, const NativeRawPresentTile& b) noexcept {
    return a.copyWidth == b.copyWidth && a.copyHeight == b.copyHeight &&
           native_raw_disjoint_present_tiles(a, b);
}
// Source-coincident native GPU pixels take priority over displaced RAW
// insets. A pair is safe only if both final original-game destinations are
// disjoint after replacing either or both tiles with source coordinates.
[[nodiscard]] constexpr bool native_raw_can_show_source_aligned_pair(
    bool legacyPairVisible, bool firstAligned, bool secondAligned,
    const NativeRawPresentTile& first,
    const NativeRawPresentTile& second) noexcept {
    // The real source-aligned path carries independently clipped GPU
    // regions. Do not drop one real repaint solely because they differ
    // in size; displaced/mixed pairs retain the legacy equal-size rule.
    if (firstAligned && secondAligned)
        return native_raw_disjoint_present_tiles(first, second);
    return legacyPairVisible &&
           native_raw_disjoint_equal_tiles(first, second);
}
[[nodiscard]] constexpr bool native_raw_choose_source_aligned_second_tile(
    std::uint32_t firstChanged, std::uint32_t secondChanged,
    bool firstAligned, bool secondAligned, bool secondVisible) noexcept {
    return secondVisible &&
        (firstAligned != secondAligned
            ? secondAligned
            : secondChanged > firstChanged);
}
 // When a D3D9 menu/car Present updates only a subset, the default
 // top-right RAW diagnostic tile may be outside ALL genuine dirty pixels.
 // Keep it when fully covered; otherwise find the largest tile inside a
 // real intersecting dirty rectangle. Never expand the game's repaint.
 [[nodiscard]] constexpr bool native_raw_dirty_region_place_tile(
     std::uint32_t backWidth, std::uint32_t backHeight,
     std::int64_t cropLeft, std::int64_t cropTop,
     std::int64_t cropRight, std::int64_t cropBottom,
     const NativeRawPresentDirtyRegion& dirty,
     std::uint32_t sourceWidth, std::uint32_t sourceHeight,
     NativeRawPresentTile& placed,
     const NativeRawPresentTile* exclude = nullptr,
     bool allowCompactRaw = false) noexcept {
     placed = {};
     // Preserve legacy 40px minimum for every historical source proof.
     // Compact opt-in is connected solely from the matching native GPU
     // source-size path; dirty union coverage remains a strict requirement.
     const bool compact = allowCompactRaw &&
         (sourceWidth < 256u || sourceHeight < 144u);
     const std::int64_t minSpan = compact ? 24 : 40;
     // Only an authenticated first image may reserve painted D3D9 pixels.
     if (exclude && !native_raw_dirty_region_covers_tile(
             backWidth, backHeight, dirty, *exclude)) return false;
     NativeRawPresentTile ordinary{};
     if (!native_raw_partial_present_tile(
             backWidth, backHeight, cropLeft, cropTop,
             cropRight, cropBottom, sourceWidth, sourceHeight, ordinary,
             compact))
         return false;
     if ((!exclude || native_raw_disjoint_equal_tiles(ordinary, *exclude)) &&
         native_raw_dirty_region_covers_tile(
             backWidth, backHeight, dirty, ordinary)) {
         placed = ordinary;
         return true;
     }
     // Each candidate is verified against the WHOLE bounded region, not
     // against rcBound or merely an intersecting rectangle. A malformed
     // member anywhere in the region prevents publication.
     bool found = false;
     std::uint64_t largestArea = 0u;
     // D3D9 RGNDATA can split one repainted menu area into several
     // adjacent rectangles. The individual rectangles may each be too
     // small for a 24x24 RAW crop even when their authenticated UNION is
     // sufficient. The candidate is NEVER trusted just because its
     // bounding box intersects the Present: check every painted pixel
     // through native_raw_dirty_region_covers_tile before accepting it.
     const auto consider = [&](std::int64_t left, std::int64_t top,
                               std::int64_t right,
                               std::int64_t bottom) noexcept {
         NativeRawPresentTile candidate{};
         if (!native_raw_partial_present_tile(
                 backWidth, backHeight, left, top, right, bottom,
                 sourceWidth, sourceHeight, candidate, compact))
             return;
         const auto area = std::uint64_t{candidate.copyWidth} *
                           candidate.copyHeight;
         if ((found && area <= largestArea) ||
             (exclude && !native_raw_disjoint_equal_tiles(candidate, *exclude)) ||
             !native_raw_dirty_region_covers_tile(
                 backWidth, backHeight, dirty, candidate))
             return;
         found = true;
         largestArea = area;
         placed = candidate;
     };
     // Fast path for a complete, possibly fragmented source repaint.
     // A forged rcBound, gap or out-of-bounds member fails the union test.
     consider((std::max)(cropLeft, dirty.boundLeft),
              (std::max)(cropTop, dirty.boundTop),
              (std::min)(cropRight, dirty.boundRight),
              (std::min)(cropBottom, dirty.boundBottom));
     for (std::uint32_t i = 0u;
          i < dirty.count && i < NativeRawPresentDirtyRegion::kMaxRects; ++i) {
         const auto& rect = dirty.rectangles[i];
         consider((std::max)(cropLeft, rect.left),
                  (std::max)(cropTop, rect.top),
                  (std::min)(cropRight, rect.right),
                  (std::min)(cropBottom, rect.bottom));
     }
     // RGNDATA may fragment a genuine menu/car repaint into more than
     // two adjoining pieces (including >8 total members with outliers).
     // Enumerating pairs misses a valid native GPU tile in that case.
     // Discover each edge/overlap-connected repaint component in a bounded
     // flood fill (at most 32 rectangles and 32*32 adjacency probes overall).
     // The component bounds only propose a location: every candidate still
     // requires strict ORIGINAL full-region bounds and per-pixel union proof.
     // A gap, malformed member, or fabricated rcBound never earns coverage.
     if (!dirty.headerVerified || dirty.count == 0u ||
         dirty.count > NativeRawPresentDirtyRegion::kMaxRects)
         return false;
     bool visited[NativeRawPresentDirtyRegion::kMaxRects]{};
     for (std::uint32_t seed = 0u; seed < dirty.count; ++seed) {
         if (visited[seed]) continue;
         std::uint32_t queue[NativeRawPresentDirtyRegion::kMaxRects]{};
         std::uint32_t read = 0u, size = 1u;
         queue[0] = seed;
         visited[seed] = true;
         auto componentLeft = dirty.rectangles[seed].left;
         auto componentTop = dirty.rectangles[seed].top;
         auto componentRight = dirty.rectangles[seed].right;
         auto componentBottom = dirty.rectangles[seed].bottom;
         while (read < size) {
             const auto& current = dirty.rectangles[queue[read++]];
             for (std::uint32_t i = 0u; i < dirty.count; ++i) {
                 if (visited[i]) continue;
                 const auto& next = dirty.rectangles[i];
                 // Touching edges are contiguous D3D9 source pixels; a
                 // shared corner may widen bounds but cannot pass the
                 // independent exact per-pixel coverage test if hollow.
                 if (next.left > current.right ||
                     next.right < current.left ||
                     next.top > current.bottom ||
                     next.bottom < current.top)
                     continue;
                 visited[i] = true;
                 queue[size++] = i; // each source member enqueued once
                 componentLeft = (std::min)(componentLeft, next.left);
                 componentTop = (std::min)(componentTop, next.top);
                 componentRight = (std::max)(componentRight, next.right);
                 componentBottom = (std::max)(componentBottom, next.bottom);
             }
         }
         consider((std::max)(cropLeft, componentLeft),
                  (std::max)(cropTop, componentTop),
                  (std::min)(cropRight, componentRight),
                  (std::min)(cropBottom, componentBottom));
     }
     // Do not stop after finding an isolated SMALL repaint: a fragmented
     // two-axis region may still contain more original GPU RGB pixels.
     // Only a staging-sized result is provably optimal before the sweeps.
     if (found && largestArea ==
             std::uint64_t{sourceWidth} * sourceHeight) return true;
     // A connected component can be nonrectangular: e.g. three thin menu
     // strips make a real 48x48 island with an 8px-high attached tail.
     // Its full bounds place the RAW tile in the tail's unpainted neighbor,
     // and no single member is wide enough. Sweep source-authored Y edges
     // instead. Only members covering the ENTIRE band contribute X spans;
     // merging touching spans produces genuine rectangular repaint areas.
     // This is a fallback only, bounded by the original 32-member RGNDATA.
     for (std::uint32_t topIndex = 0u; topIndex < dirty.count; ++topIndex) {
         const auto top = (std::max)(cropTop, dirty.rectangles[topIndex].top);
         bool duplicateTop = false;
         for (std::uint32_t i = 0u; i < topIndex; ++i)
             if ((std::max)(cropTop, dirty.rectangles[i].top) == top)
                 duplicateTop = true;
         if (duplicateTop) continue;
         for (std::uint32_t bottomIndex = 0u;
              bottomIndex < dirty.count; ++bottomIndex) {
             const auto bottom = (std::min)(
                 cropBottom, dirty.rectangles[bottomIndex].bottom);
             // Even a tight source-painted crop needs 24 true unscaled pixels.
             if (bottom - top < minSpan) continue;
             bool duplicateBottom = false;
             for (std::uint32_t i = 0u; i < bottomIndex; ++i)
                 if ((std::min)(cropBottom, dirty.rectangles[i].bottom) == bottom)
                     duplicateBottom = true;
             if (duplicateBottom) continue;
             NativeRawPresentDirtyRect spans[NativeRawPresentDirtyRegion::kMaxRects]{};
             std::uint32_t count = 0u;
             for (std::uint32_t i = 0u; i < dirty.count; ++i) {
                 const auto& rect = dirty.rectangles[i];
                 if (rect.top > top || rect.bottom < bottom) continue;
                 const auto left = (std::max)(cropLeft, rect.left);
                 const auto right = (std::min)(cropRight, rect.right);
                 if (left >= right) continue;
                 std::uint32_t slot = count++;
                 while (slot && spans[slot - 1u].left > left) {
                     spans[slot] = spans[slot - 1u];
                     --slot;
                 }
                 spans[slot] = {left, top, right, bottom};
             }
             if (!count) continue;
             auto left = spans[0].left, right = spans[0].right;
             for (std::uint32_t i = 1u; i <= count; ++i) {
                 if (i < count && spans[i].left <= right) {
                     right = (std::max)(right, spans[i].right);
                     continue;
                 }
                 // Still authenticate against the ORIGINAL region, including
                 // all outliers and rcBound; sweep proposals grant no trust.
                 consider(left, top, right, bottom);
                 if (i < count) {
                     left = spans[i].left;
                     right = spans[i].right;
                 }
             }
         }
     }
     // The dual case is common in original D3D9 RGNDATA: a menu/car
     // repaint is sliced into short HORIZONTAL rows. None spans the
     // complete Y band above, and an attached rightward tail invalidates
     // the whole connected-component candidate. Sweep source-authored
     // X boundaries and merge vertically touching intervals instead.
     // This changes placement only in explicit RAW opt-in diagnostics.
     for (std::uint32_t leftIndex = 0u; leftIndex < dirty.count; ++leftIndex) {
         const auto left = (std::max)(cropLeft, dirty.rectangles[leftIndex].left);
         bool duplicateLeft = false;
         for (std::uint32_t i = 0u; i < leftIndex; ++i)
             if ((std::max)(cropLeft, dirty.rectangles[i].left) == left)
                 duplicateLeft = true;
         if (duplicateLeft) continue;
         for (std::uint32_t rightIndex = 0u;
              rightIndex < dirty.count; ++rightIndex) {
             const auto right = (std::min)(
                 cropRight, dirty.rectangles[rightIndex].right);
             // The native source crop still needs 24 true unscaled pixels.
             if (right - left < minSpan) continue;
             bool duplicateRight = false;
             for (std::uint32_t i = 0u; i < rightIndex; ++i)
                 if ((std::min)(cropRight, dirty.rectangles[i].right) == right)
                     duplicateRight = true;
             if (duplicateRight) continue;
             NativeRawPresentDirtyRect spans[NativeRawPresentDirtyRegion::kMaxRects]{};
             std::uint32_t count = 0u;
             for (std::uint32_t i = 0u; i < dirty.count; ++i) {
                 const auto& rect = dirty.rectangles[i];
                 if (rect.left > left || rect.right < right) continue;
                 const auto top = (std::max)(cropTop, rect.top);
                 const auto bottom = (std::min)(cropBottom, rect.bottom);
                 if (top >= bottom) continue;
                 std::uint32_t slot = count++;
                 while (slot && spans[slot - 1u].top > top) {
                     spans[slot] = spans[slot - 1u];
                     --slot;
                 }
                 spans[slot] = {left, top, right, bottom};
             }
             if (!count) continue;
             auto top = spans[0].top, bottom = spans[0].bottom;
             for (std::uint32_t i = 1u; i <= count; ++i) {
                 if (i < count && spans[i].top <= bottom) {
                     bottom = (std::max)(bottom, spans[i].bottom);
                     continue;
                 }
                 // These intervals are only CANDIDATES. Authentic D3D9
                 // bounds and every source-painted pixel are independently
                 // rechecked before the first GPU RGB byte is displayed.
                 consider(left, top, right, bottom);
                 if (i < count) {
                     top = spans[i].top;
                     bottom = spans[i].bottom;
                 }
             }
         }
     }
     // Authentic menus may partition one repaint in BOTH axes (for
     // example, a 3x3 grid of 16px cells), while an attached thin update
     // extends the connected component's bounding box. Neither one-axis
     // strip sweep can reconstruct this completely painted 2D island.
     // Seed a bounded 2D rectangle from two ORIGINAL member corners.
     // Both coordinates come from observed D3D9 source rectangles; the
     // resulting proposal is still checked pixel-for-pixel against the
     // entire validated RGNDATA union by consider(). No holes are filled,
     // no source crop is widened, and this is RAW opt-in only.
     for (std::uint32_t start = 0u; start < dirty.count; ++start) {
         const auto left = (std::max)(cropLeft, dirty.rectangles[start].left);
         const auto top = (std::max)(cropTop, dirty.rectangles[start].top);
         for (std::uint32_t end = 0u; end < dirty.count; ++end) {
             const auto right = (std::min)(
                 cropRight, dirty.rectangles[end].right);
             const auto bottom = (std::min)(
                 cropBottom, dirty.rectangles[end].bottom);
             if (right - left < minSpan || bottom - top < minSpan) continue;
             consider(left, top, right, bottom);
         }
     }
     return found;
 }
} // namespace outrun::vr::dx11

