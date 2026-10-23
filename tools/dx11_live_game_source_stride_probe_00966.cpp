// CONVERSION-DX11-00966: real-game 4/12-byte source capture boundary.
// Portable semantic test only; GPU game/HMD runtime remains UNTESTED.
#include "../src/vr/d3d11/live_game_source_stride.hpp"
using outrun::vr::dx11::game_native_source_stride_valid;
static_assert(game_native_source_stride_valid(4u), "one packed D3D9 input");
static_assert(game_native_source_stride_valid(12u), "FLOAT3 POSITION-only input");
static_assert(game_native_source_stride_valid(16u), "existing FLOAT4 input");
static_assert(game_native_source_stride_valid(512u), "max source stride");
static_assert(!game_native_source_stride_valid(0u), "empty source");
static_assert(!game_native_source_stride_valid(1u), "sub-element source");
static_assert(!game_native_source_stride_valid(3u), "undersized source");
static_assert(!game_native_source_stride_valid(513u), "oversized source");
static_assert(!game_native_source_stride_valid(0xffffffffu), "overflow stride");
int main() { return 0; }
