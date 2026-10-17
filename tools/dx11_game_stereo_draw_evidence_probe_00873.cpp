#include "../src/vr/d3d11/native_game_stereo_draw_evidence.hpp"
#include "../src/vr/d3d11/native_game_stretch_source.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::live_game_stereo::may_issue_instanced;
using outrun::vr::dx11::live_game_stereo::color_certifiable;
using outrun::vr::dx11::live_game_stereo::authored_color_output_ready;
using outrun::vr::dx11::live_game_stereo::full_eye_target_rect;
using outrun::vr::dx11::live_game_stereo::NativeDepthClearRoute;
using outrun::vr::dx11::live_game_stereo::depth_clear_route;
int main() {
    // Real stereo game GPU postpass scratch: same-device reuse requires
    // identical typed extents and bind flags. A camera resize, DXGI format
    // change, SRV-vs-copy-only mode or Reset must not alias old content.
    using outrun::vr::dx11::native_game_postpass_scratch_matches;
    static_assert(native_game_postpass_scratch_matches(
        {3440u, 1440u, 87u, 8u}, {3440u, 1440u, 87u, 8u}));
    static_assert(!native_game_postpass_scratch_matches(
        {3440u, 1440u, 87u, 8u}, {1920u, 1080u, 87u, 8u}));
    static_assert(!native_game_postpass_scratch_matches(
        {3440u, 1440u, 87u, 8u}, {3440u, 1440u, 28u, 8u}));
    static_assert(!native_game_postpass_scratch_matches(
        {3440u, 1440u, 87u, 8u}, {3440u, 1440u, 87u, 0u}));
    static_assert(!native_game_postpass_scratch_matches(
        {3440u, 1440u, 87u, 8u}, {0u, 1440u, 87u, 8u}));
    // Menu/car/race native eye callback: both indexed and non-indexed
    // multi-instance commands preserve ONE genuine source draw ordinal.
    static_assert(may_issue_instanced(3u, 1u, 0u));
    static_assert(may_issue_instanced(6u, 12u, 123u));
    static_assert(may_issue_instanced(4096u, 2u, 5000u));
    // Zero-element/zero-instance calls never fabricate stereo color.
    static_assert(!may_issue_instanced(0u, 2u, 0u));
    static_assert(!may_issue_instanced(3u, 0u, 0u));
    static_assert(!may_issue_instanced(
        3u, 2u, (std::numeric_limits<std::uint64_t>::max)()));
    // Both ordinary and instanced calls must preserve a depth-only draw's
    // command ordinal but reject fabricated color when GPU predication,
    // an absent pixel shader or disabled color output prevents visibility.
    static_assert(color_certifiable(true, true));
    static_assert(!color_certifiable(true, false));
    static_assert(!color_certifiable(false, true));
    // Full-size TARGET rectangles take D3D11.0 ClearRenderTargetView on both
    // eyes, so native game scene replay can run without a D3D11.1 context.
    // Cropped menu/HUD rectangles use ClearView or the bounded D3D11.0
    // GPU raster fallback; invalid targets/unsupported paths still reject.
    static_assert(full_eye_target_rect(0, 0, 3440, 1440, 3440u, 1440u));
    static_assert(!full_eye_target_rect(0, 0, 3440, 1439, 3440u, 1440u));
    static_assert(!full_eye_target_rect(3, 0, 3440, 1440, 3440u, 1440u));
    static_assert(!full_eye_target_rect(-1, 0, 3440, 1440, 3440u, 1440u));
    static_assert(!full_eye_target_rect(0, 0, 3440, 1440, 0u, 1440u));
    // A cropped authored TARGET Clear must preserve pixels outside its own
    // rectangle even on D3D11.0. Never turn it into a full-eye Clear when
    // ClearView is unavailable or promote an unsupported shader/format.
    using outrun::vr::dx11::live_game_stereo::NativeColorClearRoute;
    using outrun::vr::dx11::live_game_stereo::color_clear_route;
    static_assert(color_clear_route(true, 16, 12, 160, 80, 1920u, 1080u,
        false, true) == NativeColorClearRoute::ShaderRaster);
    static_assert(color_clear_route(true, 16, 12, 160, 80, 1920u, 1080u,
        true, false) == NativeColorClearRoute::ClearView);
    static_assert(color_clear_route(true, 16, 12, 160, 80, 1920u, 1080u,
        false, false) == NativeColorClearRoute::Reject);
    static_assert(color_clear_route(true, 0, 0, 1920, 1080, 1920u, 1080u,
        false, false) == NativeColorClearRoute::FullRtv);
    static_assert(color_clear_route(false, 0, 0, 0, 0, 1920u, 1080u,
        false, false) == NativeColorClearRoute::FullRtv);
    static_assert(color_clear_route(true, -1, 0, 50, 50, 1920u, 1080u,
        false, true) == NativeColorClearRoute::Reject);
    static_assert(color_clear_route(true, 0, 0, 0, 50, 1920u, 1080u,
        false, true) == NativeColorClearRoute::Reject);
    static_assert(color_clear_route(true, 0, 0, 1921, 1080, 1920u, 1080u,
        false, true) == NativeColorClearRoute::Reject);
    // Game camera Z/stencil command replay: implicit and explicit full-eye
    // rectangles clear the actual per-eye DSV on D3D11.0 without a fabricated
    // Draw or shader; cropped menu/HUD rectangles retain bounded rasterization.
    // Invalid source coordinates are rejected before either eye is recorded.
    static_assert(depth_clear_route(false, 0, 0, 0, 0, 3440u, 1440u) ==
        NativeDepthClearRoute::FullDsv);
    static_assert(depth_clear_route(true, 0, 0, 3440, 1440, 3440u, 1440u) ==
        NativeDepthClearRoute::FullDsv);
    static_assert(depth_clear_route(true, 0, 0, 1920, 1080, 3440u, 1440u) ==
        NativeDepthClearRoute::PartialRaster);
    static_assert(depth_clear_route(true, 1, 0, 3440, 1440, 3440u, 1440u) ==
        NativeDepthClearRoute::PartialRaster);
    static_assert(depth_clear_route(true, 0, 0, 0, 0, 3440u, 1440u) ==
        NativeDepthClearRoute::Reject);
    static_assert(depth_clear_route(true, -1, 0, 3440, 1440, 3440u, 1440u) ==
        NativeDepthClearRoute::Reject);
    static_assert(depth_clear_route(true, 0, 0, 3441, 1440, 3440u, 1440u) ==
        NativeDepthClearRoute::Reject);
    static_assert(depth_clear_route(true, 0, 0, 3440, 1440, 0u, 1440u) ==
        NativeDepthClearRoute::Reject);
    // Original D3D9 TARGET Clear is authentic eye color, not fabricated
    // geometry. Admit depth-only draws following a full seed, while rejecting
    // a terminal Clear that erased the last native game geometry.
    static_assert(authored_color_output_ready(5u, 0u, 0u, 1u, 0u));
    static_assert(authored_color_output_ready(5u, 0u, 0u, 2u, 4u));
    static_assert(!authored_color_output_ready(5u, 0u, 0u, 2u, 5u));
    static_assert(!authored_color_output_ready(0u, 0u, 0u, 1u, 0u));
    static_assert(authored_color_output_ready(5u, 0u, 1u, 2u, 5u));
    assert(color_certifiable(true,true) &&
           !color_certifiable(false,false) &&
           authored_color_output_ready(5u, 0u, 0u, 1u, 0u) &&
           !authored_color_output_ready(5u, 0u, 0u, 1u, 5u));
}
