#include "../src/vr/d3d11/native_game_srgb_draw.hpp"
using outrun::vr::dx11::live_game_frame::GameNativeSrgbDraw;
static_assert(GameNativeSrgbDraw::admit(0u, false));
static_assert(GameNativeSrgbDraw::admit(0u, true));
static_assert(!GameNativeSrgbDraw::admit(1u, false)); // no inset sRGB RTV
static_assert(GameNativeSrgbDraw::admit(1u, true));   // full frame sRGB RTV
static_assert(!GameNativeSrgbDraw::admit(2u, true));
static_assert(!GameNativeSrgbDraw::admit(0xffffffffu, true));
static_assert(!GameNativeSrgbDraw::uses_srgb(0u));
static_assert(GameNativeSrgbDraw::uses_srgb(1u));
int main() { return 0; }
