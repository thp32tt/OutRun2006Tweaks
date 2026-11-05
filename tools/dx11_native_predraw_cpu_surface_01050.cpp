#include "../src/vr/d3d11/native_game_cpu_surface_ticket.hpp"
#include "../src/vr/d3d11/native_game_pre_draw_surface.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using outrun::vr::dx11::live_game_frame::GameNativeCpuSurfaceTicket;
using outrun::vr::dx11::live_game_frame::GameNativePreDrawSurface;
int main() {
    using S = GameNativePreDrawSurface;
    static_assert(S::capture_allowed(true, true, true, false, false));
    static_assert(!S::capture_allowed(true, true, true, false, true));
    static_assert(S::capture_allowed(true, true, true, false, true, true));
    static_assert(!S::capture_allowed(true, false, true, false, true, true));
    static_assert(!S::capture_allowed(true, true, false, false, true, true));
    static_assert(!S::capture_allowed(true, true, true, true, true, true));
    static_assert(!S::capture_allowed(false, true, true, false, true, true));
    static_assert(S::size_allowed(3440u, 1440u));
    static_assert(!S::size_allowed(65536u, 65536u));
    constexpr std::uintptr_t device = 0x44u, backbuffer = 0x55u;
    GameNativeCpuSurfaceTicket ticket{};
    S snapshot{};
    std::vector<std::uint8_t> gamePixels(4u * 4u * 4u, 0x10u);
    // Partial LockRect before native Draw: retain untouched game pixels.
    assert(ticket.begin(device, backbuffer, 1u, 1u, 3u, 3u, 4u, 4u));
    assert(ticket.active());
    assert(!ticket.begin(device, backbuffer, 0u, 0u, 4u, 4u, 4u, 4u));
    assert(!S::capture_allowed(true, true, true, false, ticket.active()));
    assert(ticket.permits_finish(false) && !ticket.permits_finish(true));
    assert(!ticket.matches(device + 1u, backbuffer, 1u, 1u, 3u, 3u));
    assert(!ticket.matches(device, backbuffer, 0u, 0u, 4u, 4u));
    gamePixels[(1u * 4u + 1u) * 4u] = 0x70u;
    assert(ticket.matches(device, backbuffer, 1u, 1u, 3u, 3u));
    assert(S::capture_allowed(true, true, true, false, ticket.active(), true));
    assert(snapshot.record(device, backbuffer, 4u, 4u, 21u, gamePixels));
    ticket.reset(); // Successful original UnlockRect.
    assert(!ticket.active() && snapshot.matches(device, backbuffer, 4u, 4u, 21u));
    assert(snapshot.pixels[(1u * 4u + 1u) * 4u] == 0x70u);
    assert(snapshot.pixels[(0u * 4u + 0u) * 4u] == 0x10u);
    // A later authentic GDI ReleaseDC refreshes all pixels in source order.
    assert(ticket.begin(device, backbuffer, 0u, 0u, 4u, 4u, 4u, 4u, true));
    assert(ticket.permits_finish(true) && !ticket.permits_finish(false));
    gamePixels[(3u * 4u + 3u) * 4u] = 0x90u;
    assert(snapshot.record(device, backbuffer, 4u, 4u, 21u, gamePixels));
    ticket.reset();
    assert(snapshot.pixels[(1u * 4u + 1u) * 4u] == 0x70u);
    assert(snapshot.pixels[(3u * 4u + 3u) * 4u] == 0x90u);
    assert(!snapshot.matches(device + 1u, backbuffer, 4u, 4u, 21u));
    assert(!snapshot.matches(device, backbuffer + 1u, 4u, 4u, 21u));
    assert(!snapshot.record(device, backbuffer, 4u, 5u, 21u, gamePixels));
    snapshot.discard(); // Failed readback/finish: original D3D9 fallback.
    assert(!snapshot.active());
    return 0;
}
