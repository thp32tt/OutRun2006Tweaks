#pragma once
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// Grow on capacity misses only. Exact game vertex/index data is uploaded on
// every diagnostic draw, but a stable scene no longer creates three resources
// per draw. Do not cache D3D9 mutable texture contents by pointer identity.
constexpr std::uint32_t next_native_stream_capacity(
    std::uint32_t needed, std::uint32_t existing) noexcept {
    if (!needed) return 0u;
    std::uint32_t bytes = existing >= 256u ? existing : 256u;
    while (bytes < needed) {
        if (bytes > std::numeric_limits<std::uint32_t>::max() / 2u)
            return needed; // no wrapping on large valid source buffers
        bytes *= 2u;
    }
    return bytes;
}
static_assert(next_native_stream_capacity(0u, 0u) == 0u);
static_assert(next_native_stream_capacity(80u, 0u) == 256u);
static_assert(next_native_stream_capacity(257u, 0u) == 512u);
static_assert(next_native_stream_capacity(512u, 1024u) == 1024u);
static_assert(next_native_stream_capacity(2049u, 512u) == 4096u);
static_assert(next_native_stream_capacity(0xffffffffu, 0x80000000u) == 0xffffffffu);
} // namespace outrun::vr::dx11::live_game_frame
