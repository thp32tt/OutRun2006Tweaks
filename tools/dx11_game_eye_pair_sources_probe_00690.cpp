#include "../src/vr/d3d11/native_game_eye_pair_sources.hpp"
#include <array>
#include <cstdint>
using outrun::vr::dx11::native_game_eye_pair_sources_admitted;
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
