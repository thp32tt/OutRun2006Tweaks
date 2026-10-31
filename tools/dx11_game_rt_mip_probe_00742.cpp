#include "src/vr/d3d11/live_game_render_target_readback.hpp"
using outrun::vr::dx11::live_game_frame::native_rt_readback::matching_mip_extent;
static_assert(matching_mip_extent(1024u, 512u, 0u, 1024u, 512u));
static_assert(matching_mip_extent(1024u, 512u, 1u, 512u, 256u));
static_assert(matching_mip_extent(1024u, 512u, 9u, 2u, 1u));
static_assert(matching_mip_extent(1024u, 512u, 10u, 1u, 1u));
static_assert(matching_mip_extent(3u, 5u, 2u, 1u, 1u));
static_assert(!matching_mip_extent(1024u, 512u, 9u, 1024u, 512u));
static_assert(!matching_mip_extent(1024u, 512u, 9u, 1u, 2u));
static_assert(!matching_mip_extent(1024u, 512u, 10u, 0u, 1u));
static_assert(!matching_mip_extent(1024u, 512u, 32u, 1u, 1u));
static_assert(!matching_mip_extent(0u, 512u, 0u, 1u, 512u));
static_assert(!matching_mip_extent(1024u, 0u, 0u, 1024u, 1u));
int main() { return 0; }
