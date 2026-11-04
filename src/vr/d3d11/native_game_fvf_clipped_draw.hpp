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
[[nodiscard]] inline bool native_game_fvf_fully_clipped_draw(
    NativeRawFvfClipSpan source,
    bool depthClipEnable = true) noexcept {
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
    const auto* bytes = static_cast<const std::uint8_t*>(source.firstClip);
    for (std::size_t primitive = 0u; primitive < primitives; ++primitive) {
        std::array<std::array<double, 13u>, 3u> distances{};
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
            d[6] = double(clip[3]) - 0.00001;
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
        bool invisible = false;
        // Proving ONE plane excludes an entire assembled primitive suffices.
        // A polygon whose corners are outside DIFFERENT planes can still
        // cross the game viewport: never discard that actual native Draw.
        for (unsigned plane = 0u; plane < 13u; ++plane) {
            if (!depthClipEnable && (plane == 4u || plane == 5u))
                continue;
            if (plane >= 7u &&
                !(source.clipDistanceMask & (1u << (plane - 7u))))
                continue;
            bool allOutside = true;
            for (unsigned corner = 0u; corner < corners; ++corner)
                allOutside = allOutside && distances[corner][plane] < 0.0;
            if (allOutside) { invisible = true; break; }
        }
        if (!invisible) return false;
    }
    return true;
}
} // namespace outrun::vr::dx11
