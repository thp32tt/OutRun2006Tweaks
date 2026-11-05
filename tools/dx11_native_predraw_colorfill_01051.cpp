// Real menu/car/race pre-Draw CPU/GDI color is NOT an offscreen camera fill.
#include "../src/vr/d3d11/native_game_pre_draw_surface.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using outrun::vr::dx11::live_game_frame::GameNativePreDrawSurface;
int main() {
    GameNativePreDrawSurface s;
    constexpr std::uintptr_t device = 0x1000u, bb = 0x2000u, camera = 0x3000u;
    const std::vector<std::uint8_t> pixels{17,26,35,255,44,53,62,255,71,80,89,255,98,107,116,255};
    assert(GameNativePreDrawSurface::capture_allowed(true,true,true,false,false));
    assert(s.record(device,bb,2,2,21,pixels));
    // Full ColorFill on two noncanonical targets cannot drop main pixels.
    s.discard_if_canonical_full_write(device,camera);
    s.discard_if_canonical_full_write(0x4000u,bb);
    s.discard_if_canonical_full_write(0u,bb);
    assert(s.matches(device,bb,2,2,21));
    assert(s.pixels==pixels);
    // The later real full ColorFill of main RT0 supersedes copied color.
    s.discard_if_canonical_full_write(device,bb);
    assert(!s.active() && s.pixels.empty());
    // Following successful LockRect/ReleaseDC or UpdateSurface may restage.
    assert(s.record(device,bb,2,2,21,pixels));
    assert(!GameNativePreDrawSurface::capture_allowed(true,true,true,false,true));
    assert(GameNativePreDrawSurface::capture_allowed(true,true,true,false,true,true));
    s.discard();
    assert(!s.active());
}
