#pragma once
// A raw PRE/POST GPU color sample is useful only for a real native Draw
// capable of modifying RGB on the SAME currently bound render target.
// This controls diagnostic sampling, NEVER execution of the game Draw.
#include <cstdint>
namespace outrun::vr::dx11 {
struct NativeRawBoundRgbState {
    bool renderTargetBound = false;
    bool exactSourceResource = false;
    bool pixelShaderBound = false;
    std::uint8_t renderTargetWriteMask = 0u;
};
[[nodiscard]] constexpr bool native_raw_bound_rgb_capture_admitted(
    NativeRawBoundRgbState s) noexcept {
    // D3D11_COLOR_WRITE_ENABLE_RED/GREEN/BLUE are 1/2/4.
    // An ALPHA-only mask, a depth-only draw, or a foreign RTV cannot
    // produce attributable source GPU RGB pixels. Preserve the pair
    // budget for a later color-producing game Draw in the same Present.
    return s.renderTargetBound && s.exactSourceResource &&
           s.pixelShaderBound && (s.renderTargetWriteMask & 0x07u) != 0u;
}
static_assert(native_raw_bound_rgb_capture_admitted({true,true,true,0x0fu}));
static_assert(native_raw_bound_rgb_capture_admitted({true,true,true,0x01u}));
static_assert(!native_raw_bound_rgb_capture_admitted({true,true,true,0x08u}));
static_assert(!native_raw_bound_rgb_capture_admitted({true,true,true,0x00u}));
static_assert(!native_raw_bound_rgb_capture_admitted({true,false,true,0x0fu}));
static_assert(!native_raw_bound_rgb_capture_admitted({true,true,false,0x0fu}));
static_assert(!native_raw_bound_rgb_capture_admitted({false,true,true,0x0fu}));
} // namespace outrun::vr::dx11
