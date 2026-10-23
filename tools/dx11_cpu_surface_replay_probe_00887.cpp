#include "../src/vr/d3d11/native_game_cpu_surface_ticket.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::GameNativeCpuSurfaceTicket;
int main() {
    GameNativeCpuSurfaceTicket t{};
    assert(!t.active());
    assert(!t.permits_finish(false));
    assert(!t.begin(0,9,0,0,32,32,64,64));
    assert(!t.begin(4,9,40,0,32,32,64,64));
    assert(!t.begin(4,9,0,0,65,32,64,64));
    assert(t.begin(4,9,8,12,40,48,64,64));
    assert(!t.begin(4,9,0,0,64,64,64,64));
    assert(!t.matches(5,9,8,12,40,48));
    assert(!t.matches(4,10,8,12,40,48));
    assert(!t.matches(4,9,0,0,64,64));
    assert(t.matches(4,9,8,12,40,48));
    assert(t.permits_finish(false));
    assert(!t.permits_finish(true)); // ReleaseDC cannot complete LockRect
    t.reset();
    assert(!t.active());
    assert(t.begin(4,9,0,0,64,64,64,64,true));
    assert(t.permits_finish(true));
    assert(!t.permits_finish(false)); // UnlockRect cannot complete GetDC
    assert(!t.begin(4,9,0,0,64,64,64,64,false));
    t.reset();
    assert(!t.permits_finish(true));
    return 0;
}
