#pragma once
#include <cstdint>

namespace outrun::vr::dx11 {

// D3D9 shader declarations may consist of a 12-byte FLOAT3 POSITION or
// one 4-byte packed element. The old R30 16-byte cutoff discarded genuine
// VB/IB/UP game draws before the native declaration could validate them.
// This only allows CPU shadow capture. Every field offset, element width,
// source epoch, vertex budget and shader signature is still checked before
// native Draw/DrawIndexed; invalid sources retain the original D3D9 path.
constexpr bool game_native_source_stride_valid(std::uint32_t stride) noexcept {
    return stride >= 4u && stride <= 512u;
}

} // namespace outrun::vr::dx11
