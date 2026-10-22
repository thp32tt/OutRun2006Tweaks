#pragma once
// Genuine D3D9 SM3 oDepth.x must use a writable native depth target.
// Reject guessed color-channel aliases, conditional writes and missing DSVs.
namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_sm3_depth_destination(
    unsigned registerIndex, unsigned mask, bool predicated) noexcept {
    return registerIndex == 0u && mask == 1u && !predicated;
}
[[nodiscard]] constexpr bool native_sm3_depth_target(
    bool sourceZEnabled, bool sourceZWritable, bool nativeDsvReady,
    bool alphaTest, bool tableFog) noexcept {
    return sourceZEnabled && sourceZWritable && nativeDsvReady &&
           !alphaTest && !tableFog;
}
} // namespace outrun::vr::dx11
