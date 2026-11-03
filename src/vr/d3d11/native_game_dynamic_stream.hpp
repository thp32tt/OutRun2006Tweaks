#pragma once
#include <cstddef>
#include <cstring>

namespace outrun::vr::dx11::live_game_frame {
// Copies one exact live D3D9 vertex/index span into the CURRENTLY MAPPED
// D3D11_USAGE_DYNAMIC resource. Caller owns Map(WRITE_DISCARD)/Unmap so
// earlier game Draws keep their in-flight storage rather than being overwritten.
// On invalid source/destination/capacity leave GPU bytes unchanged; original
// D3D9 draw and gamepad always proceed through their own callsite.
[[nodiscard]] inline bool game_native_copy_dynamic_stream(
    void* mapped, std::size_t capacity, const void* source,
    std::size_t bytes) noexcept {
    if (!mapped || !source || bytes == 0u || bytes > capacity) return false;
    std::memcpy(mapped, source, bytes);
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
