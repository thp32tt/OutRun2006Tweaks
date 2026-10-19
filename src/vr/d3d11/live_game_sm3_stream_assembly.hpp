#pragma once
// Original D3D9 SM3 declaration streams, already shadowed in one physical
// index order, become a single shader-visible D3D11 FLOAT4 vertex stream.
#include "live_game_sm3_vertex_unpack.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>
namespace outrun::vr::dx11::live_game_frame {
struct GameSm3StreamView {
    const std::uint8_t* data{};
    std::uint32_t stride{};
    std::uint32_t vertexCount{};
};
struct GameSm3ElementRef {
    std::uint8_t stream{};
    std::uint16_t offset{};
    std::uint8_t type{};
};
[[nodiscard]] inline bool game_sm3_assemble_streams(
    const std::vector<GameSm3ElementRef>& elements,
    const std::array<GameSm3StreamView,4>& streams,
    std::uint32_t count, std::vector<std::uint8_t>& destination) noexcept {
    constexpr std::uint64_t kMaxBytes = 1ull << 25u;
    if (elements.empty() || elements.size() > 32u || !count) return false;
    const auto nativeStride = static_cast<std::uint64_t>(elements.size()) * 16u;
    if (nativeStride * count > kMaxBytes) return false;
    for (const auto& e : elements) {
        if (e.stream >= streams.size()) return false;
        const auto& src = streams[e.stream];
        const auto width = game_sm3_decl_width(e.type);
        if (!src.data || !src.stride || src.vertexCount < count ||
            !width || static_cast<std::uint32_t>(e.offset) + width > src.stride)
            return false;
    }
    try {
        std::vector<std::uint8_t> candidate(
            static_cast<std::size_t>(nativeStride * count));
        for (std::uint32_t v = 0u; v < count; ++v)
            for (std::size_t i = 0u; i < elements.size(); ++i) {
                const auto& e = elements[i];
                const auto& src = streams[e.stream];
                std::array<float,4> decoded{};
                if (!game_sm3_unpack_attribute(e.type,
                        src.data + static_cast<std::size_t>(v) * src.stride +
                            e.offset, decoded)) return false;
                std::memcpy(candidate.data() +
                    static_cast<std::size_t>(v) * nativeStride + i * 16u,
                    decoded.data(), sizeof(decoded));
            }
        destination.swap(candidate); // no partial mesh visible on failure
        return true;
    } catch (...) { return false; }
}
} // namespace outrun::vr::dx11::live_game_frame
