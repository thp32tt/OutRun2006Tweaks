#include "../src/vr/d3d11/native_game_color_fill.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
#include <cstdint>
using outrun::vr::dx11::native_game_color_fill_retires_draw_batch;
using outrun::vr::dx11::native_game_color_fill_rgba;
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
static_assert(!native_game_color_fill_retires_draw_batch(false, true));
static_assert(!native_game_color_fill_retires_draw_batch(true, false));
static_assert(native_game_color_fill_retires_draw_batch(true, true));
static_assert(native_game_color_fill_rgba(0x00563412u, true)[3] == 1.0f);
static_assert(native_game_color_fill_rgba(0x00563412u, false)[3] == 0.0f);
static_assert(native_game_color_fill_rgba(0xff563412u, false)[3] == 1.0f);
int main() {
    const auto x8=native_game_color_fill_rgba(0x00563412u,true);
    const auto a8=native_game_color_fill_rgba(0x00563412u,false);
    assert(x8[0]==a8[0] && x8[1]==a8[1] && x8[2]==a8[2]);
    assert(x8[3]==1.0f && a8[3]==0.0f);
    const auto left=native_game_color_fill_rgba(0x11884422u,true);
    const auto right=native_game_color_fill_rgba(0x11884422u,false);
    assert(left[3]==1.0f && right[3]>0.0f && right[3]<1.0f);
    // A real, recorded Draw cannot survive a later full ColorFill of RT0.
    GameNativeFrameBatch batch{};
    batch.record_source_draw(0u);
    batch.succeeded(false);
    assert(batch.publishable(true));
    if(native_game_color_fill_retires_draw_batch(true,batch.submitted!=0u))
        batch.abort();
    assert(!batch.publishable(true));
    // A clipped partial ColorFill is an in-place GPU replay, not a full
    // scene epoch. The previous native Draw remains valid when mirrored.
    GameNativeFrameBatch partial{};
    partial.record_source_draw(0u);
    partial.succeeded(false);
    if(native_game_color_fill_retires_draw_batch(false,partial.submitted!=0u))
        partial.abort();
    assert(partial.publishable(true));
}
