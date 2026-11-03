#pragma once
// Genuine D3D9 SM3 oDepth.x must use a writable native depth target.
// Reject guessed color-channel aliases, conditional writes and missing DSVs.
namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_sm3_depth_destination(
    unsigned registerIndex, unsigned mask, bool predicated) noexcept {
    return registerIndex == 0u && mask == 1u && !predicated;
}
[[nodiscard]] constexpr bool native_sm3_depth_only_pass(
    bool shaderDepthOnly, bool writesDepth, unsigned colorWriteMask,
    bool sourceZEnabled, bool sourceZWritable, bool nativeDsvReady,
    bool alphaTest, bool tableFog) noexcept;
[[nodiscard]] constexpr bool native_sm3_depth_target(
    bool sourceZEnabled, bool sourceZWritable, bool nativeDsvReady,
    bool alphaTest, bool tableFog) noexcept {
    return sourceZEnabled && sourceZWritable && nativeDsvReady &&
           !alphaTest && !tableFog;
}
[[nodiscard]] constexpr bool native_sm3_depth_only_pass(
    bool shaderDepthOnly, bool writesDepth, unsigned colorWriteMask,
    bool sourceZEnabled, bool sourceZWritable, bool nativeDsvReady,
    bool alphaTest, bool tableFog) noexcept {
    // Only genuine depth-only SM3 shaders may omit SV_Target0. A source
    // requesting any RGB/alpha write must remain on the original D3D9 Draw.
    return shaderDepthOnly && writesDepth && colorWriteMask == 0u &&
           native_sm3_depth_target(sourceZEnabled, sourceZWritable,
                                   nativeDsvReady, alphaTest, tableFog);
}
} // namespace outrun::vr::dx11
