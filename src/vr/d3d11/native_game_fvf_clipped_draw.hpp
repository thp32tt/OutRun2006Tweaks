#pragma once
// Classify a genuinely pixel-neutral original FVF Draw/DrawIndexed before
// recording its source ordinal or spending a native GPU PRE/POST capture.
// A positive result proves EVERY assembled primitive lies strictly outside
// at least one authenticated homogeneous (or enabled user) clip plane.
// Indices, vertex payloads and every active plane must be valid. Failure or
// uncertainty means normal native admission/RAW capture with D3D9 fallback.
#include "native_game_raw_fvf_clip_capture.hpp"
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>

namespace outrun::vr::dx11 {
// An exact D3D11 source-viewport/scissor mapping for the original FVF draw.
// A confirmed scissor-excluded polygon has no color, Z or stencil samples;
// invalid/unknown viewport or rectangle must use the ordinary GPU route.
struct NativeRawFvfScissorClip {
    double viewportX{}, viewportY{}, viewportWidth{}, viewportHeight{};
    std::int64_t left{}, top{}, right{}, bottom{};
};
[[nodiscard]] inline bool native_game_fvf_fully_clipped_draw(
    NativeRawFvfClipSpan source,
    bool depthClipEnable = true,
    const NativeRawFvfScissorClip* scissor = nullptr,
    const NativeRawFvfRaster* nativeRaster = nullptr,
    bool solidTriangleRaster = false) noexcept {
    if (!source.firstClip || source.vertexStride < 4u * sizeof(float) ||
        source.vertexStride > 4096u || source.count == 0u ||
        source.count > 1048576u ||
        source.count > (std::numeric_limits<std::size_t>::max)() /
                           source.vertexStride ||
        (source.indices == nullptr) != (source.indexCount == 0u) ||
        (source.clipDistanceMask & ~0x3fu) ||
        (source.clipDistanceMask &&
         (source.vertexStride < 6u * sizeof(float) ||
          source.clipDistanceOffset >
              source.vertexStride - 6u * sizeof(float))))
        return false;
    // Hardware depth clipping can be disabled by the bound D3D11 rasterizer.
    // Never certify a source Draw as pixel-neutral from Z near/far planes
    // when EITHER the caller or authenticated native RS says clipping is off.
    // Original D3D9 Draw and native GPU routing stay authoritative.
    const bool effectiveDepthClip = depthClipEnable &&
        (!nativeRaster || nativeRaster->depthClipEnable);
    const std::size_t active = source.indices ? source.indexCount : source.count;
    unsigned corners = 0u;
    std::size_t primitives = 0u;
    switch (source.assembly) {
    case NativeRawFvfAssembly::TriangleList:
        if (active < 3u || active % 3u) return false;
        corners = 3u; primitives = active / 3u; break;
    case NativeRawFvfAssembly::TriangleStrip:
    case NativeRawFvfAssembly::TriangleFan:
        if (active < 3u) return false;
        corners = 3u; primitives = active - 2u; break;
    case NativeRawFvfAssembly::LineList:
        if (active < 2u || (active & 1u)) return false;
        corners = 2u; primitives = active / 2u; break;
    case NativeRawFvfAssembly::LineStrip:
        if (active < 2u) return false;
        corners = 2u; primitives = active - 1u; break;
    case NativeRawFvfAssembly::PointList:
        if (!active) return false;
        corners = 1u; primitives = active; break;
    default: return false;
    }
    // Bounded source-authentic scan; oversized valid game IA retains the
    // established normal GPU path rather than a speculative no-op shortcut.
    if (!primitives || primitives > 8192u) return false;
    // Convert the ACTUALLY bound scissor pixel edges into homogeneous
    // halfspaces. This excludes diagonals entirely outside a narrow
    // menu/car viewport without confusing overlapping AABBs with pixels.
    // All arithmetic uses double; any invalid mapping retains native Draw.
    double ndcLeft = -1.0, ndcRight = 1.0;
    double ndcBottom = -1.0, ndcTop = 1.0;
    if (scissor) {
        if (!std::isfinite(scissor->viewportX) ||
            !std::isfinite(scissor->viewportY) ||
            !std::isfinite(scissor->viewportWidth) ||
            !std::isfinite(scissor->viewportHeight) ||
            !(scissor->viewportWidth > 0.0) ||
            !(scissor->viewportHeight > 0.0) ||
            scissor->left >= scissor->right ||
            scissor->top >= scissor->bottom)
            return false;
        // A D3D11 aliased one-pixel line and a wireframe triangle can
        // touch a scissored sample even when its mathematical centreline is
        // just outside the integer scissor edge. MSAA sample locations and
        // edge-rounding must not turn a genuine source pixel into an empty
        // source ordinal. Prove emptiness against a conservatively expanded
        // ONE-pixel rectangle, but leave the actual bound D3D11 scissor,
        // viewport, Draw and GPU PRE/POST readback completely unchanged.
        // The wider test may miss a no-op, never certify a visible Draw.
        constexpr double kRasterFootprintGuardPixels = 1.0;
        ndcLeft = 2.0 * (double(scissor->left) -
                         kRasterFootprintGuardPixels -
                         scissor->viewportX) /
            scissor->viewportWidth - 1.0;
        ndcRight = 2.0 * (double(scissor->right) +
                          kRasterFootprintGuardPixels -
                          scissor->viewportX) /
            scissor->viewportWidth - 1.0;
        ndcTop = 1.0 - 2.0 * (double(scissor->top) -
                              kRasterFootprintGuardPixels -
                              scissor->viewportY) /
            scissor->viewportHeight;
        ndcBottom = 1.0 - 2.0 * (double(scissor->bottom) +
                                 kRasterFootprintGuardPixels -
                                 scissor->viewportY) /
            scissor->viewportHeight;
        if (!std::isfinite(ndcLeft) || !std::isfinite(ndcRight) ||
            !std::isfinite(ndcTop) || !std::isfinite(ndcBottom) ||
            !(ndcLeft < ndcRight) || !(ndcBottom < ndcTop))
            return false;
    }
    const auto* bytes = static_cast<const std::uint8_t*>(source.firstClip);
    for (std::size_t primitive = 0u; primitive < primitives; ++primitive) {
        std::array<std::array<double, 17u>, 3u> distances{};
        for (unsigned corner = 0u; corner < corners; ++corner) {
            std::size_t element = 0u;
            switch (source.assembly) {
            case NativeRawFvfAssembly::TriangleList:
                element = primitive * 3u + corner; break;
            case NativeRawFvfAssembly::TriangleStrip:
                element = primitive + corner; break; // winding irrelevant to clipping
            case NativeRawFvfAssembly::TriangleFan:
                element = corner == 0u ? 0u : primitive + corner; break;
            case NativeRawFvfAssembly::LineList:
                element = primitive * 2u + corner; break;
            case NativeRawFvfAssembly::LineStrip:
                element = primitive + corner; break;
            case NativeRawFvfAssembly::PointList:
                element = primitive; break;
            default: return false;
            }
            if (element >= active) return false;
            const std::size_t index = source.indices ? source.indices[element] : element;
            if (index >= source.count) return false;
            float clip[4]{};
            std::memcpy(clip, bytes + index * source.vertexStride, sizeof(clip));
            for (float value : clip) if (!std::isfinite(value)) return false;
            if (!clip[0] && !clip[1] && !clip[2] && !clip[3])
                return false; // zero homogeneous vector is not proven geometry
            auto& d = distances[corner];
            d[0] = double(clip[0]) + clip[3];
            d[1] = double(clip[3]) - clip[0];
            d[2] = double(clip[1]) + clip[3];
            d[3] = double(clip[3]) - clip[1];
            d[4] = clip[2];
            d[5] = double(clip[3]) - clip[2];
            d[6] = clip[3]; // never discard positive-W genuine raster pixels
            if (scissor) {
                d[13] = double(clip[0]) - ndcLeft * double(clip[3]);
                d[14] = ndcRight * double(clip[3]) - double(clip[0]);
                d[15] = double(clip[1]) - ndcBottom * double(clip[3]);
                d[16] = ndcTop * double(clip[3]) - double(clip[1]);
                for (unsigned plane = 13u; plane < 17u; ++plane)
                    if (!std::isfinite(d[plane])) return false;
            }
            if (source.clipDistanceMask) {
                float user[6]{};
                std::memcpy(user, bytes + index * source.vertexStride +
                                  source.clipDistanceOffset, sizeof(user));
                for (unsigned p = 0u; p < 6u; ++p) {
                    if (!(source.clipDistanceMask & (1u << p))) continue;
                    if (!std::isfinite(user[p])) return false;
                    d[p + 7u] = user[p];
                }
            }
        }
        // 01234: an original D3D9 FVF source Draw is also pixel-neutral
        // when every authentic triangle is fully backface-culled by the
        // bound D3D11 RS. Only wholly inside positive-W triangles qualify:
        // clipping, eye-plane crossings and degenerate winding keep the real
        // GPU Draw/DrawIndexed and the existing D3D9 fallback.
        if (nativeRaster && nativeRaster->cull != NativeRawFvfCull::None &&
            corners == 3u &&
            (source.assembly == NativeRawFvfAssembly::TriangleList ||
             source.assembly == NativeRawFvfAssembly::TriangleStrip ||
             source.assembly == NativeRawFvfAssembly::TriangleFan)) {
            bool inside = true;
            for (unsigned c = 0u; c < 3u && inside; ++c) {
                const auto& d = distances[c];
                if (!(d[6] > 0.0)) { inside = false; break; }
                for (unsigned p = 0u; p < (scissor ? 17u : 13u); ++p) {
                    if ((!effectiveDepthClip && (p == 4u || p == 5u)) ||
                        (p >= 7u && p < 13u &&
                         !(source.clipDistanceMask & (1u << (p - 7u)))))
                        continue;
                    if (d[p] < 0.0) { inside = false; break; }
                }
            }
            if (inside) {
                std::array<double, 3u> x{}, y{};
                for (unsigned c = 0u; c < 3u; ++c) {
                    const auto& d = distances[c];
                    x[c] = (d[0] - d[1]) / (2.0 * d[6]);
                    y[c] = (d[2] - d[3]) / (2.0 * d[6]);
                    if (!std::isfinite(x[c]) || !std::isfinite(y[c]))
                        return false;
                }
                double area = (x[1] - x[0]) * (y[2] - y[0]) -
                              (y[1] - y[0]) * (x[2] - x[0]);
                if (!std::isfinite(area)) return false;
                // Native triangle-strip flips two original IA corners on
                // odd triangles; a fan always retains its zero anchor.
                if (source.assembly == NativeRawFvfAssembly::TriangleStrip &&
                    (primitive & 1u)) area = -area;
                if (std::abs(area) > 1.0e-12) {
                    const bool front = nativeRaster->frontCounterClockwise
                        ? area > 0.0 : area < 0.0;
                    if ((front && nativeRaster->cull == NativeRawFvfCull::Front) ||
                        (!front && nativeRaster->cull == NativeRawFvfCull::Back))
                        continue; // proven source-raster no-op
                }
            }
        }
        // A real game-authored SOLID triangle with two coincident
        // homogeneous screen positions has zero projected area even when
        // its vertices carry different Z/UV/color. This is a source-raster
        // no-op, not a manufactured D3D11 Draw. Restrict the proof to
        // strictly interior positive-W triangles: any clipping, boundary
        // contact, wireframe or point-filled polygon keeps the original
        // GPU submission. Compare the exact affine X+W/Y+W/W values,
        // without a near-zero area epsilon that could drop thin road/HUD
        // triangles which still cover a pixel.
        if (solidTriangleRaster && nativeRaster && !nativeRaster->wireframe &&
            corners == 3u &&
            (source.assembly == NativeRawFvfAssembly::TriangleList ||
             source.assembly == NativeRawFvfAssembly::TriangleStrip ||
             source.assembly == NativeRawFvfAssembly::TriangleFan)) {
            bool strictInterior = true;
            for (unsigned corner = 0u; corner < 3u && strictInterior; ++corner) {
                const auto& d = distances[corner];
                if (!(d[6u] > 0.0)) { strictInterior = false; break; }
                for (unsigned plane = 0u; plane < (scissor ? 17u : 13u); ++plane) {
                    if ((!effectiveDepthClip && (plane == 4u || plane == 5u)) ||
                        (plane >= 7u && plane < 13u &&
                         !(source.clipDistanceMask & (1u << (plane - 7u)))))
                        continue;
                    if (!(d[plane] > 0.0)) { strictInterior = false; break; }
                }
            }
            if (strictInterior) {
                // Projective equality matters, not identical source W.
                // Original FVF vertices can carry different positive W/Z/UV
                // yet land on the EXACT same homogeneous screen point.
                // Products of two source float values are represented exactly
                // in double (including subnormals); unlike an epsilon or
                // approximate divide, this cannot erase a thin real pixel.
                // Strict interior/positive-W admission above remains required.
                const auto sameScreenCorner = [&](unsigned a, unsigned b) noexcept {
                    const double wa = distances[a][6u], wb = distances[b][6u];
                    const double xa = distances[a][0u] - wa;
                    const double xb = distances[b][0u] - wb;
                    const double ya = distances[a][2u] - wa;
                    const double yb = distances[b][2u] - wb;
                    return xa * wb == xb * wa && ya * wb == yb * wa;
                };
                std::array<std::array<double, 4u>, 3u> sourceClip{};
                for (unsigned corner = 0u; corner < 3u; ++corner) {
                    const auto& d = distances[corner];
                    sourceClip[corner] = {{d[0u] - d[6u],
                                          d[2u] - d[6u], d[4u], d[6u]}};
                }
                // Different XY/W positions can still lie EXACTLY along
                // one homogeneous screen axis (e.g. collapsed road seam).
                // Only interior solid triangles qualify; all nonzero-area,
                // wireframe, point-filled and uncertain source geometry
                // keeps its real native Draw and D3D9 fallback.
                if (sameScreenCorner(0u, 1u) ||
                    sameScreenCorner(1u, 2u) ||
                    sameScreenCorner(2u, 0u) ||
                    native_raw_fvf_axis_collinear_positive_w(sourceClip))
                    continue; // proven no color/Z/stencil sample
            }
        }
        bool invisible = false;
        bool hasNonpositiveEyeW = false;
        for (unsigned corner = 0u; corner < corners; ++corner)
            hasNonpositiveEyeW = hasNonpositiveEyeW ||
                distances[corner][6u] <= 0.0;
        // Proving ONE plane excludes an entire assembled primitive suffices.
        // A polygon whose corners are outside DIFFERENT planes can still
        // cross the game viewport: never discard that actual native Draw.
        for (unsigned plane = 0u; plane < (scissor ? 17u : 13u); ++plane) {
            if (!effectiveDepthClip && (plane == 4u || plane == 5u))
                continue;
            // Only planes 7..12 are optional D3D9 ClipDistance0..5.
            // Scissor planes 13..16 are independent ACTUAL RS halfspaces.
            // Applying the user-mask here would silently disable every
            // scissor exclusion whenever user ClipDistance is off.
            if (plane >= 7u && plane < 13u &&
                !(source.clipDistanceMask & (1u << (plane - 7u))))
                continue;
            bool allOutside = true;
            for (unsigned corner = 0u; corner < corners; ++corner)
                allOutside = allOutside && distances[corner][plane] < 0.0;
            if (allOutside) { invisible = true; break; }
        }
        if (!invisible) {
            // Fast path: a source vertex inside every active hardware,
            // user and scissor plane makes an empty-Draw certificate unsafe.
            // Most genuine menu/car/race Draws leave here without costly
            // clipping. A triangle can also cross a visible region with NO
            // inside vertices; that case needs an exact polygon intersection.
            bool hasInsideVertex = false;
            for (unsigned corner = 0u; corner < corners; ++corner) {
                bool inside = true;
                for (unsigned plane = 0u; plane < (scissor ? 17u : 13u); ++plane) {
                    if ((!effectiveDepthClip && (plane == 4u || plane == 5u)) ||
                        (plane >= 7u && plane < 13u &&
                         !(source.clipDistanceMask & (1u << (plane - 7u)))))
                        continue;
                    if (distances[corner][plane] < 0.0) {
                        inside = false;
                        break;
                    }
                }
                if (inside) { hasInsideVertex = true; break; }
            }
            if (hasInsideVertex || hasNonpositiveEyeW) return false;

            // An actual source primitive may be outside the INTERSECTION
            // of two scissor/ClipDistance planes while crossing each plane
            // individually. Use bounded homogeneous Sutherland-Hodgman
            // clipping of the original Draw's assembled primitives. Each
            // signed distance is affine along an original GPU clip edge;
            // it remains valid for the newly generated intersection points.
            // Never claim a no-op for a touching/degenerate boundary, W=0
            // ambiguity, invalid index or numerically uncertain crossing.
            std::array<std::array<double, 17u>, 24u> polygon{}, clipped{};
            std::size_t polygonCount = corners;
            for (unsigned corner = 0u; corner < corners; ++corner)
                polygon[corner] = distances[corner];
            for (unsigned plane = 0u;
                 plane < (scissor ? 17u : 13u) && polygonCount; ++plane) {
                if ((!effectiveDepthClip && (plane == 4u || plane == 5u)) ||
                    (plane >= 7u && plane < 13u &&
                     !(source.clipDistanceMask & (1u << (plane - 7u)))))
                    continue;
                std::size_t nextCount = 0u;
                auto previous = polygon[polygonCount - 1u];
                bool previousInside = previous[plane] >= 0.0;
                for (std::size_t vertex = 0u; vertex < polygonCount; ++vertex) {
                    const auto& current = polygon[vertex];
                    const bool currentInside = current[plane] >= 0.0;
                    if (previousInside != currentInside) {
                        const double denominator =
                            previous[plane] - current[plane];
                        if (!std::isfinite(denominator) ||
                            denominator == 0.0 || nextCount >= clipped.size())
                            return false;
                        const double fraction = previous[plane] / denominator;
                        if (!std::isfinite(fraction) ||
                            fraction < 0.0 || fraction > 1.0)
                            return false;
                        auto& intersection = clipped[nextCount++];
                        for (unsigned component = 0u; component < 17u; ++component) {
                            intersection[component] = previous[component] +
                                fraction * (current[component] - previous[component]);
                            if (!std::isfinite(intersection[component]))
                                return false;
                        }
                        intersection[plane] = 0.0;
                    }
                    if (currentInside) {
                        if (nextCount >= clipped.size()) return false;
                        clipped[nextCount++] = current;
                    }
                    previous = current;
                    previousInside = currentInside;
                }
                polygonCount = nextCount;
                polygon.swap(clipped);
            }
            invisible = polygonCount == 0u;
        }
        if (!invisible) return false;
    }
    return true;
}
} // namespace outrun::vr::dx11
