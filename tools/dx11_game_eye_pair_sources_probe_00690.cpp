#include "../src/vr/d3d11/native_game_eye_pair_sources.hpp"
#include <array>
#include <cstdint>
using outrun::vr::dx11::native_game_eye_pair_sources_admitted;
using outrun::vr::dx11::native_game_eye_local_render_target_admitted;
using outrun::vr::dx11::native_game_eye_gpu_copy_only_source_admitted;
// D3D11_BIND_RENDER_TARGET=0x20; SHARED/KEYEDMUTEX/NTHANDLE=0x902.
constexpr std::uint32_t kColorRt = 0x20u;
constexpr std::uint32_t kShared = 0x902u;
static_assert(native_game_eye_local_render_target_admitted(kColorRt, 0u, kColorRt, kShared));
static_assert(native_game_eye_local_render_target_admitted(kColorRt | 0x8u, 1u, kColorRt, kShared));
static_assert(!native_game_eye_local_render_target_admitted(0x8u, 0u, kColorRt, kShared));
static_assert(!native_game_eye_local_render_target_admitted(kColorRt, 0x2u, kColorRt, kShared));
static_assert(!native_game_eye_local_render_target_admitted(kColorRt, 0x100u, kColorRt, kShared));
static_assert(!native_game_eye_local_render_target_admitted(kColorRt, 0x800u, kColorRt, kShared));
static_assert(!native_game_eye_local_render_target_admitted(kColorRt, 0u, 0u, kShared));
// Game-created GPU CopyResource color postpasses can be bindless (DEFAULT),
// including two distinct physical camera slices of one array allocation.
static_assert(native_game_eye_gpu_copy_only_source_admitted(0u, 0u, 1u, kShared));
static_assert(native_game_eye_gpu_copy_only_source_admitted(0u, 1u, 1u, kShared));
static_assert(!native_game_eye_gpu_copy_only_source_admitted(0u, 0u, 4u, kShared));
static_assert(!native_game_eye_gpu_copy_only_source_admitted(0u, 0u, 0u, kShared));
static_assert(!native_game_eye_gpu_copy_only_source_admitted(kColorRt, 0u, 1u, kShared));
static_assert(!native_game_eye_gpu_copy_only_source_admitted(0x8u, 0u, 1u, kShared));
static_assert(!native_game_eye_gpu_copy_only_source_admitted(0x80u, 0u, 1u, kShared));
static_assert(!native_game_eye_gpu_copy_only_source_admitted(0u, 0x2u, 1u, kShared));
static_assert(!native_game_eye_gpu_copy_only_source_admitted(0u, 0x100u, 1u, kShared));
static_assert(!native_game_eye_gpu_copy_only_source_admitted(0u, 0x800u, 1u, kShared));
constexpr std::array<std::uintptr_t, 8> kRing{11, 12, 13, 14, 15, 16, 17, 18};
static_assert(native_game_eye_pair_sources_admitted(101, 102, kRing));
static_assert(!native_game_eye_pair_sources_admitted(101, 101, kRing));
static_assert(!native_game_eye_pair_sources_admitted(0, 102, kRing));
static_assert(!native_game_eye_pair_sources_admitted(101, 0, kRing));
static_assert(!native_game_eye_pair_sources_admitted(11, 102, kRing));
static_assert(!native_game_eye_pair_sources_admitted(101, 18, kRing));
static_assert(!native_game_eye_pair_sources_admitted(13, 14, kRing));
constexpr std::array<std::uintptr_t, 8> kIncomplete{11, 12, 13, 14, 15, 16, 0, 18};
static_assert(!native_game_eye_pair_sources_admitted(101, 102, kIncomplete));
int main() { return native_game_eye_pair_sources_admitted(101, 102, kRing) ? 0 : 1; }
