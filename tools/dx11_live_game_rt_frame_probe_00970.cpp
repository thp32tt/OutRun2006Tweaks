#include "../src/vr/d3d11/live_game_render_target_readback.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame::native_rt_readback;
static_assert(bounded_gpu_snapshot(1920, 1080, 1, Layout::argb8));
static_assert(bounded_gpu_snapshot(2048, 2048, 12, Layout::argb8));
static_assert(bounded_gpu_snapshot(4096, 1024, 13, Layout::a8b8g8r8));
static_assert(bounded_gpu_snapshot(2048, 2048, 12, Layout::rgb565));
static_assert(!bounded_gpu_snapshot(4096, 2048, 13, Layout::argb8));
static_assert(!bounded_gpu_snapshot(4096, 4096, 1, Layout::rgb565));
static_assert(!bounded_gpu_snapshot(2048, 2048, 13, Layout::argb8));
static_assert(!bounded_gpu_snapshot(8192, 512, 1, Layout::argb8));
static_assert(!bounded_gpu_snapshot(0, 1080, 1, Layout::argb8));
static_assert(!bounded_gpu_snapshot(1920, 1080, 0, Layout::argb8));
static_assert(!bounded_gpu_snapshot(1920, 1080, 12, Layout::unsupported));
static_assert(!bounded_gpu_snapshot(1, 1, 2, Layout::argb8));
static_assert(source_texel_bytes(Layout::rgb565) == 2u);
static_assert(source_texel_bytes(Layout::argb8) == 4u);
int main() {
  assert(bounded_gpu_snapshot(1920, 1080, 1, Layout::argb8));
  assert(!bounded_gpu_snapshot(4096, 2048, 1, Layout::argb8));
}
