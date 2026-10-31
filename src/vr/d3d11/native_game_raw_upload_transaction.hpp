#pragma once
// Stage every source-authenticated D3D11 GPU RGB region before publishing any
// of them through the original D3D9 Present. This does not make the incomplete
// RAW diagnostic a native full frame, and a D3D9 device error during commit
// cannot be rolled back. No heap allocations, GPU stall, or synthetic pixels.
#include <cstdint>

namespace outrun::vr::dx11 {
template <class Prepare, class Publish>
[[nodiscard]] inline bool native_raw_preflight_publish_islands(
    std::uint32_t count, Prepare&& prepare, Publish&& publish,
    std::uint32_t& committed) noexcept {
    committed = 0u;
    if (!count || count > 4u) return false;
    for (std::uint32_t i = 0u; i < count; ++i)
        if (!prepare(i)) return false;
    for (std::uint32_t i = 0u; i < count; ++i) {
        if (!publish(i)) return false;
        ++committed;
    }
    return true;
}
} // namespace outrun::vr::dx11
