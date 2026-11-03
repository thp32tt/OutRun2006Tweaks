#pragma once
// D3D11 native-game RAW pixel provenance: allow genuine multisample game
// color, but only via an actual on-GPU resolve of the exact source resource.
#include <cstdint>
namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_raw_msaa_capture_samples_supported(
    std::uint32_t samples) noexcept {
    // D3D11 sample count 1-32, powers of two. Actual device+format support
    // remains a mandatory live GPU query before staging/resolving pixels.
    return samples && samples <= 32u &&
           (samples & (samples - 1u)) == 0u;
}
[[nodiscard]] constexpr bool native_raw_msaa_resolve_required(
    std::uint32_t samples) noexcept {
    return samples > 1u && native_raw_msaa_capture_samples_supported(samples);
}
static_assert(native_raw_msaa_capture_samples_supported(1u));
static_assert(native_raw_msaa_capture_samples_supported(4u));
static_assert(native_raw_msaa_resolve_required(8u));
static_assert(!native_raw_msaa_resolve_required(1u));
static_assert(!native_raw_msaa_capture_samples_supported(0u));
static_assert(!native_raw_msaa_capture_samples_supported(3u));
static_assert(!native_raw_msaa_capture_samples_supported(64u));
} // namespace outrun::vr::dx11
