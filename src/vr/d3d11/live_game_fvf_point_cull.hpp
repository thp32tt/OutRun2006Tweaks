#pragma once
// Original D3D9 FVF D3DFILL_POINT must cull its source TRIANGLES before
// lowering surviving vertex occurrences to D3D11 POINTLIST. D3D11 does not
// apply face culling to POINTLIST. Preserve this source-only conversion when
// surviving source triangle is fully inside the native clip volume. A whole
// triangle outside one homogeneous/user plane produces no points and can be
// omitted; intersecting triangles need new clip-generated corners and keep
// the original D3D9 fallback. No cull mode (including NONE) bypasses clipping.
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <vector>

namespace outrun::vr::dx11::live_game_frame {
[[nodiscard]] inline bool game_fvf_culled_point_indices(
    const void* packed, std::size_t stride, std::uint32_t vertexCount,
    const std::uint32_t* indices, std::uint32_t elements,
    std::uint32_t topology, std::uint32_t cullMode,
    std::size_t clipDistanceOffset, std::uint32_t clipDistanceMask,
    std::uint32_t maxIndices,
    std::vector<std::uint32_t>& destination) noexcept {
    // D3D9: TRIANGLELIST=4, TRIANGLESTRIP=5, CULL_CW=2, CULL_CCW=3.
    // CULL_NONE=1 still requires source clip classification before POINTLIST.
    if (!packed || stride < 4u * sizeof(float) || stride > 4096u ||
        !vertexCount || vertexCount > 1048576u ||
        vertexCount > (std::numeric_limits<std::size_t>::max)() / stride ||
        elements < 3u || elements > 1048576u ||
        (topology != 4u && topology != 5u) ||
        (cullMode != 1u && cullMode != 2u && cullMode != 3u) ||
        (topology == 4u && elements % 3u != 0u) ||
        (clipDistanceMask & ~0x3fu) ||
        (clipDistanceMask &&
         (stride < 6u * sizeof(float) ||
          clipDistanceOffset > stride - 6u * sizeof(float))))
        return false;
    const std::uint32_t triangles =
        topology == 4u ? elements / 3u : elements - 2u;
    if (!triangles || triangles > maxIndices / 3u) return false;
    struct ScreenVertex {
        double x{}, y{};
        // Homogeneous left/right/top/bottom/near/far, then six user planes.
        std::array<double, 12> clipPlane{};
    };
    const auto* bytes = static_cast<const std::uint8_t*>(packed);
    const auto read = [&](std::uint32_t element, ScreenVertex& out,
                          std::uint32_t& sourceIndex) noexcept {
        sourceIndex = indices ? indices[element] : element;
        if (sourceIndex >= vertexCount) return false;
        float clip[4]{};
        std::memcpy(clip, bytes + std::size_t{sourceIndex} * stride,
                    sizeof(clip));
        for (float f : clip) if (!std::isfinite(f)) return false;
        // Positive W is required for authentic perspective and winding.
        // Do not mistake an eye-plane crossing for a trivially invisible
        // triangle: only THREE valid vertices can prove outside coverage.
        if (!(clip[3] > 0.00001f)) return false;
        const double x = double{clip[0]}, y = double{clip[1]};
        const double z = double{clip[2]}, w = double{clip[3]};
        out.clipPlane = {w + x, w - x, w + y, w - y, z, w - z,
                         0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
        if (clipDistanceMask) {
            float distance[6]{};
            std::memcpy(distance,
                bytes + std::size_t{sourceIndex} * stride + clipDistanceOffset,
                sizeof(distance));
            for (unsigned plane = 0u; plane < 6u; ++plane) {
                if (!(clipDistanceMask & (1u << plane))) continue;
                if (!std::isfinite(distance[plane])) return false;
                out.clipPlane[plane + 6u] = double{distance[plane]};
            }
        }
        out.x = x / w;
        out.y = y / w;
        return std::isfinite(out.x) && std::isfinite(out.y);
    };
    try {
        std::vector<std::uint32_t> next;
        next.reserve(std::size_t{triangles} * 3u);
        for (std::uint32_t t = 0u; t < triangles; ++t) {
            // D3D9 strip odd triangles swap their first two IA corners.
            const std::uint32_t first = topology == 4u ? 3u * t :
                                         t + (t & 1u);
            const std::uint32_t second = topology == 4u ? first + 1u :
                                          t + 1u - (t & 1u);
            const std::uint32_t third = topology == 4u ? first + 2u :
                                         t + 2u;
            ScreenVertex a{}, b{}, c{};
            std::uint32_t ia{}, ib{}, ic{};
            if (!read(first, a, ia) || !read(second, b, ib) ||
                !read(third, c, ic)) return false;
            // A triangle wholly outside ANY one source clip plane has no
            // native point pixels. Only skip it after checking every genuine
            // source index and finite plane value. A partly clipped triangle
            // can generate intersection corners: never approximate that
            // topology as the original three D3D11 POINTLIST vertices.
            bool triviallyInvisible = false;
            bool partlyClipped = false;
            for (unsigned plane = 0u; plane < 12u; ++plane) {
                if (plane >= 6u &&
                    !(clipDistanceMask & (1u << (plane - 6u)))) continue;
                const bool outsideA = a.clipPlane[plane] < 0.0;
                const bool outsideB = b.clipPlane[plane] < 0.0;
                const bool outsideC = c.clipPlane[plane] < 0.0;
                triviallyInvisible |= outsideA && outsideB && outsideC;
                partlyClipped |= outsideA || outsideB || outsideC;
            }
            if (triviallyInvisible) continue;
            if (partlyClipped) return false;
            const double signedArea =
                (b.x - a.x) * (c.y - a.y) -
                (b.y - a.y) * (c.x - a.x);
            // Zero-area rasterization is driver-sensitive for point fill.
            // Keep such a Draw on D3D9 rather than inventing native pixels.
            if (!std::isfinite(signedArea) ||
                std::abs(signedArea) <= 1.0e-12) return false;
            // D3D11 viewport flips Y: negative NDC winding is screen-CW.
            const bool clockwise = signedArea < 0.0;
            if ((cullMode == 2u && clockwise) ||
                (cullMode == 3u && !clockwise)) continue;
            next.push_back(ia);
            next.push_back(ib);
            next.push_back(ic);
        }
        // A fully culled Draw has no authentic native GPU point pixels.
        // Keep the original D3D9 Draw without issuing an empty GPU command.
        if (next.empty()) return false;
        destination.swap(next);
        return true;
    } catch (...) {
        return false;
    }
}
} // namespace outrun::vr::dx11::live_game_frame
