#include "../src/vr/d3d11/live_game_cube_rt_readback.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::cube_rt_readback::bounded_six_face_bgra8;
static_assert(bounded_six_face_bgra8(512u, 10u), "complete 512-cube fits");
static_assert(bounded_six_face_bgra8(1024u, 1u), "single 1024 face set fits");
static_assert(!bounded_six_face_bgra8(1024u, 11u), "24 MiB applies to all six faces");
static_assert(!bounded_six_face_bgra8(512u, 11u), "cannot read nonexistent mip");
static_assert(!bounded_six_face_bgra8(0u, 1u), "missing cube");
static_assert(!bounded_six_face_bgra8(2048u, 1u), "oversized cube");
static_assert(bounded_six_face_bgra8(1u, 1u), "terminal mip");
int main() { assert(bounded_six_face_bgra8(256u, 9u)); }
