// Source-only region geometry for real D3D9 UpdateSurface/StretchRect
// -> diagnostic full-size D3D11 native GPU postpass. No game/HMD inference.
#include "../src/vr/d3d11/native_game_surface_copy_region.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceCopyRegion;
int main() {
    constexpr auto ultrawide = GameNativeSurfaceCopyRegion::destination(
        0, 0, 3440, 1440, 3440, 1440);
    static_assert(ultrawide.valid && ultrawide.width() == 3440u &&
                  ultrawide.height() == 1440u);
    constexpr auto crop = GameNativeSurfaceCopyRegion::destination(
        5, 8, 65, 88, 3440, 1440);
    static_assert(crop.valid && crop.width() == 60u &&
                  crop.height() == 80u);
    constexpr auto updated = GameNativeSurfaceCopyRegion::update_surface(
        2, 3, 30, 40, 128, 64, 600, 700, 3440, 1440);
    static_assert(updated.valid && updated.left == 600u &&
                  updated.top == 700u && updated.right == 628u &&
                  updated.bottom == 737u);
    static_assert(!GameNativeSurfaceCopyRegion::destination(
        10, 10, 9, 12, 3440, 1440).valid);
    static_assert(!GameNativeSurfaceCopyRegion::destination(
        2, 2, 4096, 1440, 3440, 1440).valid);
    static_assert(!GameNativeSurfaceCopyRegion::destination(
        -1, 0, 100, 100, 3440, 1440).valid);
    static_assert(!GameNativeSurfaceCopyRegion::destination(
        0, 0, 8192, 8192, 8192, 8192).valid);
    static_assert(!GameNativeSurfaceCopyRegion::update_surface(
        0, 0, 30, 30, 20, 20, 0, 0, 3440, 1440).valid);
    static_assert(!GameNativeSurfaceCopyRegion::update_surface(
        0, 0, 30, 30, 30, 30, -1, 4, 3440, 1440).valid);
    static_assert(!GameNativeSurfaceCopyRegion::update_surface(
        0, 0, 500, 500, 500, 500, 3200, 1300, 3440, 1440).valid);
    static_assert(!GameNativeSurfaceCopyRegion::update_surface(
        0, 0, 500, 500, 500, 500,
        0x7fffffffffffffffLL, 0, 3440, 1440).valid);
    assert(GameNativeSurfaceCopyRegion::destination(
        0, 0, 1920, 1080, 1920, 1080).valid);
    return 0;
}
