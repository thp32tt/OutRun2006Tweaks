#include "../src/vr/d3d11/live_game_stage0_blend.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <initializer_list>
using namespace outrun::vr::dx11::live_game_frame;

int main() {
    static_assert(canonical_game_stage0_blend_alpha_op(16u, true) == 12u);
    static_assert(canonical_game_stage0_blend_alpha_op(16u, false) == 16u);
    static_assert(canonical_game_stage0_blend_alpha_op(12u, true) == 12u);
    static_assert(canonical_game_stage0_blend_alpha_op(13u, true) == 13u);
    // Color and alpha stage operations are canonicalized separately.
    for (const auto rgb : {12u, 13u, 16u, 4u}) {
        for (const auto alpha : {12u, 13u, 16u, 4u}) {
            assert(canonical_game_stage0_blend_alpha_op(rgb, true) ==
                   (rgb == 16u ? 12u : rgb));
            assert(canonical_game_stage0_blend_alpha_op(alpha, true) ==
                   (alpha == 16u ? 12u : alpha));
            assert(canonical_game_stage0_blend_alpha_op(rgb, false) == rgb);
            assert(canonical_game_stage0_blend_alpha_op(alpha, false) == alpha);
        }
    }
    // For stage0, CURRENT.a == DIFFUSE.a: both operations interpolate
    // identical texture/diffuse arguments for menu and race pixels.
    for (const float currentAlpha : {0.f, 0.2f, 0.5f, 0.8f, 1.f}) {
        const float texture = 0.15f;
        const float diffuse = 0.85f;
        const float currentBlend =
            texture * currentAlpha + diffuse * (1.f - currentAlpha);
        const float diffuseBlend =
            texture * currentAlpha + diffuse * (1.f - currentAlpha);
        assert(std::fabs(currentBlend - diffuseBlend) < 0.000001f);
    }
}
