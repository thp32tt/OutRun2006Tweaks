#pragma once
// Original D3D9 FVF D3DFILL_POINT must cull its source TRIANGLES before
// lowering surviving vertex occurrences to D3D11 POINTLIST. D3D11 does not
// apply face culling to POINTLIST. Preserve this source-only conversion when
// every input triangle is fully inside the native clip volume; clipped,
// malformed or unknown source falls back to the original D3D9 Draw.
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
    // CULL_NONE keeps the previously established unfiltered native path.
    if (!packed || stride < 4u * sizeof(float) || stride > 4096u ||
        !vertexCount || vertexCount > 1048576u ||
        vertexCount > (std::numeric_limits<std::size_t>::max)() / stride ||
        elements < 3u || elements > 1048576u ||
        (topology != 4u && topology != 5u) ||
        (cullMode != 2u && cullMode != 3u) ||
        (topology == 4u && elements % 3u != 0u) ||
        (clipDistanceMask & ~0x3fu) ||
        (clipDistanceMask &&
         (stride < 6u * sizeof(float) ||
          clipDistanceOffset > stride - 6u * sizeof(float))))
        return false;
    const std::uint32_t triangles =
        topology == 4u ? elements / 3u : elements - 2u;
    if (!triangles || triangles > maxIndices / 3u) return false;
    struct ScreenVertex { double x{}, y{}; };
    const auto* bytes = static_cast<const std::uint8_t*>(packed);
    const auto read = [&](std::uint32_t element, ScreenVertex& out,
                          std::uint32_t& sourceIndex) noexcept {
        sourceIndex = indices ? indices[element] : element;
        if (sourceIndex >= vertexCount) return false;
        float clip[4]{};
        std::memcpy(clip, bytes + std::size_t{sourceIndex} * stride,
                    sizeof(clip));
        for (float f : clip) if (!std::isfinite(f)) return false;
        // Projection/scissor crossing changes the set of POINT vertices.
        // Never approximate the resulting clip-generated source corners.
        if (!(clip[3] > 0.00001f) ||
            std::abs(double{clip[0]}) > double{clip[3]} ||
            std::abs(double{clip[1]}) > double{clip[3]} ||
            clip[2] < 0.0f || clip[2] > clip[3]) return false;
        if (clipDistanceMask) {
            float distance[6]{};
            std::memcpy(distance,
                bytes + std::size_t{sourceIndex} * stride + clipDistanceOffset,
                sizeof(distance));
            for (unsigned plane = 0u; plane < 6u; ++plane) {
                if (!(clipDistanceMask & (1u << plane))) continue;
                if (!std::isfinite(distance[plane]) ||
                    distance[plane] < 0.0f) return false;
            }
        }
        out.x = double{clip[0]} / double{clip[3]};
        out.y = double{clip[1]} / double{clip[3]};
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
