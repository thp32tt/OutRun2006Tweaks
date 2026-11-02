#include "src/vr/d3d11/native_game_raw_dual_tile.hpp"
#include "src/vr/d3d11/native_game_raw_color_transport.hpp"
#include "src/vr/d3d11/native_game_raw_color_write_admission.hpp"
#include "src/vr/d3d11/native_game_raw_fvf_clip_capture.hpp"
#include "src/vr/d3d11/native_game_raw_fvf_island_sampling.hpp"
#include "src/vr/d3d11/native_game_raw_changed_pixel_window.hpp"
#include "src/vr/d3d11/native_game_raw_present_coverage.hpp"
#include "src/vr/d3d11/native_game_raw_source_target_identity.hpp"
#include <array>
#include <cassert>
#include <cstdio>
#include <limits>
#include "src/vr/d3d11/native_game_raw_msaa_capture.hpp"
using namespace outrun::vr::dx11;
// Sweep authentic 512x288 paired GPU tiles across a 3440x1440 race
// source, including interior fragments missed by center/corner anchors.
constexpr bool native_raw_swept_source_coverage_regression() {
    constexpr std::uint32_t w = 3440u, h = 1440u;
    constexpr std::uint32_t tw = 512u, th = 288u;
    NativeRawDualTile pair{};
    if (!native_raw_swept_dual_draw_tile(
            w, h, tw, th, {0, 0, w, h}, 0u, pair) ||
        !pair.hasSecond || pair.first.x != 0u || pair.first.y != 0u ||
        !native_raw_source_tiles_disjoint(
            pair.first, pair.second, tw, th))
        return false;
    for (std::uint32_t gy = 0u; gy < 5u; ++gy) {
        for (std::uint32_t gx = 0u; gx < 7u; ++gx) {
            const auto px = (std::min)(gx * tw, w - tw) + tw / 2u;
            const auto py = (std::min)(gy * th, h - th) + th / 2u;
            bool witnessed = false;
            for (std::uint32_t ordinal = 0u; ordinal < 35u; ++ordinal) {
                if (!native_raw_swept_dual_draw_tile(
                        w, h, tw, th, {0, 0, w, h}, ordinal, pair))
                    return false;
                if (pair.first.x > w - tw || pair.first.y > h - th ||
                    (pair.hasSecond &&
                     (pair.second.x > w - tw || pair.second.y > h - th ||
                      !native_raw_source_tiles_disjoint(
                          pair.first, pair.second, tw, th))))
                    return false;
                const auto in = [=](NativeRawTileOrigin o) constexpr {
                    return px >= o.x && px - o.x < tw &&
                           py >= o.y && py - o.y < th;
                };
                witnessed = witnessed || in(pair.first) ||
                    (pair.hasSecond && in(pair.second));
            }
            if (!witnessed) return false;
        }
    }
    if (!native_raw_swept_dual_draw_tile(
            w, h, tw, th, {1300, 200, 3000, 1000}, 6u, pair) ||
        pair.first.x + tw <= 1300u || pair.first.x >= 3000u ||
        pair.first.y + th <= 200u || pair.first.y >= 1000u)
        return false;
    if (!native_raw_swept_dual_draw_tile(
            512, 288, tw, th, {0, 0, 512, 288}, 0u, pair) ||
        pair.hasSecond)
        return false;
    if (native_raw_swept_dual_draw_tile(
            511, 288, tw, th, {0, 0, 511, 288}, 0u, pair))
        return false;
    if (!native_raw_swept_dual_draw_tile(
            1024, 288, tw, th, {0, 0, 1024, 288}, 0u, pair) ||
        !pair.hasSecond || pair.first.x != 0u ||
        pair.second.x != 512u)
        return false;
    return true;
}
static_assert(native_raw_swept_source_coverage_regression(),
              "authentic large-raster native GPU source sweep");
// Real menu and vehicle-select viewports often have EVEN numbers of GPU
// capture cells (including 4x3). Paired 2-cell strides used to starve half
// of those source pixels for the entire session. Check complete coverage
// over one cycle on full and scissor-clipped authentic source rasters.
constexpr bool native_raw_even_grid_source_coverage_regression() {
    constexpr std::uint32_t tw = 512u, th = 288u;
    for (std::uint32_t mode = 0u; mode != 2u; ++mode) {
        const std::uint32_t sw = mode ? 3440u : 2048u;
        const std::uint32_t sh = mode ? 1440u : 864u;
        const std::uint32_t l = mode ? 300u : 0u;
        const std::uint32_t t = mode ? 200u : 0u;
        const std::uint32_t r = mode ? 1900u : sw;
        const std::uint32_t b = mode ? 900u : sh;
        constexpr std::uint32_t columns = 4u, rows = 3u;
        for (std::uint32_t gy = 0u; gy < rows; ++gy) {
            for (std::uint32_t gx = 0u; gx < columns; ++gx) {
                const auto px = (std::min)(l + gx * tw + tw / 2u, r - 1u);
                const auto py = (std::min)(t + gy * th + th / 2u, b - 1u);
                bool witnessed = false;
                for (std::uint32_t ordinal = 0u; ordinal < columns * rows;
                     ++ordinal) {
                    NativeRawDualTile pair{};
                    if (!native_raw_swept_dual_draw_tile(
                            sw, sh, tw, th, {l, t, r, b}, ordinal, pair) ||
                        !pair.hasSecond ||
                        !native_raw_source_tiles_disjoint(
                            pair.first, pair.second, tw, th))
                        return false;
                    const auto inside = [=](NativeRawTileOrigin origin) constexpr {
                        return origin.x <= sw - tw && origin.y <= sh - th &&
                            px >= origin.x && px - origin.x < tw &&
                            py >= origin.y && py - origin.y < th;
                    };
                    witnessed = witnessed || inside(pair.first) ||
                        inside(pair.second);
                    if (ordinal == 0u) {
                        NativeRawDualTile wrapped{};
                        if (!native_raw_swept_dual_draw_tile(
                                sw, sh, tw, th, {l, t, r, b},
                                columns * rows, wrapped) ||
                            wrapped.first.x != pair.first.x ||
                            wrapped.first.y != pair.first.y)
                            return false;
                    }
                }
                if (!witnessed) return false;
            }
        }
    }
    return true;
}
static_assert(native_raw_even_grid_source_coverage_regression(),
              "even-grid game Draw GPU source tiles must not starve pixels");

// XRGB source game RGB must not propagate an undefined source X as A8.
static_assert(native_raw_requires_opaque_alpha(true, false));
static_assert(native_raw_requires_opaque_alpha(true, true));
static_assert(native_raw_requires_opaque_alpha(false, true));
static_assert(!native_raw_requires_opaque_alpha(false, false));
// Source GPU color evidence is per-Draw. An alpha-only/depth-only
// menu/vehicle Draw must not occupy the single pending RGB sample and
// starve the later native game Draw which actually writes the source RTV.
constexpr bool native_raw_source_color_write_selection_regression() {
    constexpr NativeRawBoundRgbState scene[] = {
        {true,true,false,0x0fu}, // depth-only: no PS output
        {true,true,true,0x08u},  // alpha only: no RGB mutation
        {true,false,true,0x0fu}, // foreign color target
        {false,false,true,0x0fu},// no bound color target
        {true,true,true,0x02u},  // real green-only GPU output
        {true,true,true,0x0fu}   // next real draw (not a second sample)
    };
    bool queued = false;
    unsigned selected = 0u;
    for (unsigned i = 0u; i < sizeof(scene)/sizeof(scene[0]); ++i)
        if (!queued && native_raw_bound_rgb_capture_admitted(scene[i])) {
            queued = true; selected = i;
        }
    return queued && selected == 4u &&
        native_raw_bound_rgb_capture_admitted({true,true,true,0x07u}) &&
        !native_raw_bound_rgb_capture_admitted({true,true,true,0x08u}) &&
        !native_raw_bound_rgb_capture_admitted({true,true,true,0x00u}) &&
        !native_raw_bound_rgb_capture_admitted({true,true,false,0x0fu}) &&
        !native_raw_bound_rgb_capture_admitted({true,false,true,0x0fu}) &&
        !native_raw_bound_rgb_capture_admitted({false,true,true,0x0fu});
}
static_assert(native_raw_source_color_write_selection_regression(),
    "RAW PRE/POST must sample an attributable RGB-writing game Draw");
// The protected GPU copy scope intentionally detaches RTV0. Always pass
// the authentic pre-detach source observation into the later queue site.
static_assert([]() constexpr {
    const NativeRawBoundRgbState beforeDetach{true,true,true,0x0fu};
    const NativeRawBoundRgbState duringCopy{false,false,true,0x0fu};
    const bool originalSourceRgb =
        native_raw_bound_rgb_capture_admitted(beforeDetach);
    return originalSourceRgb &&
        !native_raw_bound_rgb_capture_admitted(duringCopy);
}(), "RAW source capture admission must precede OM transfer detachment");


// FVF menu/HUD triangles on the right edge previously selected GPU readback
// tiles from the entire 3440x1440 viewport. The native pass-through VS
// receives these exact clip-space coordinates, so source sampling may focus
// on the real triangle without altering source Draw, RGB or Present proof.
bool native_raw_fvf_clip_capture_regression() {
    const auto reject = [](int line) noexcept {
        std::fprintf(stderr, "FVF source raster regression failed at line %d\n", line);
        return false;
    };
    constexpr std::array<std::array<float, 4>, 3> verts{{
        {{0.78f, 0.25f, 0.5f, 1.0f}},
        {{0.95f, 0.25f, 0.5f, 1.0f}},
        {{0.90f, 0.52f, 0.5f, 1.0f}}
    }};
    NativeRawDrawExtent rect{};
    const NativeRawFvfClipSpan span{verts.data(), sizeof(verts[0]), verts.size()};
    if (!native_raw_fvf_projected_raster(span, 0, 0, 3440, 1440, rect) ||
        rect.left < 3000 || rect.right > 3440 ||
        rect.top < 300 || rect.bottom > 550)
        return reject(__LINE__);
    NativeRawDualTile source{};
    if (!native_raw_swept_dual_draw_tile(3440, 1440, 512, 288,
            rect, 0u, source) || source.first.x < 2500u)
        return reject(__LINE__);
    auto invalidW = verts;
    invalidW[1][3] = 0.0f;
    if (native_raw_fvf_projected_raster(
            {invalidW.data(), sizeof(invalidW[0]), invalidW.size()},
            0, 0, 3440, 1440, rect))
        return reject(__LINE__);
    // Mixed-sign homogeneous W is a valid D3D11 clipped game Draw.
    // Validate both original source rectangle and the integrated native
    // PRE/POST dual-GPU capture origin, without relaxing invalid W=0.
    constexpr std::array<std::array<float,4>,3> crossingEye{{
        {{-0.7f,-0.1f,0.5f,1.f}}, {{0.7f,-0.1f,0.5f,1.f}},
        {{0.0f,0.2f,-0.5f,-0.5f}}
    }};
    const NativeRawFvfClipSpan crossingEyeIa{
        crossingEye.data(),sizeof(crossingEye[0]),crossingEye.size()};
    NativeRawDrawExtent nearRaster{};
    if (!native_raw_fvf_projected_raster(
            crossingEyeIa,0,0,3440,1440,nearRaster) ||
        nearRaster.left < -2 || nearRaster.top < -2 ||
        nearRaster.right > 3442 || nearRaster.bottom > 1442 ||
        nearRaster.right <= nearRaster.left ||
        nearRaster.bottom <= nearRaster.top)
        return reject(__LINE__);
    NativeRawDualTile nearGpu{};
    if (!native_raw_fvf_island_dual_draw_tile(
            crossingEyeIa,0,0,3440,1440,3440,1440,512,288,
            {0,0,3440,1440},0u,nearGpu) ||
        nearGpu.first.x > 3440u - 512u ||
        nearGpu.first.y > 1440u - 288u)
        return reject(__LINE__);
    auto fullyBehind = crossingEye;
    for (auto& v : fullyBehind) v[3] = -1.f;
    if (native_raw_fvf_projected_raster(
            {fullyBehind.data(),sizeof(fullyBehind[0]),fullyBehind.size()},
            0,0,3440,1440,nearRaster))
        return reject(__LINE__);
    auto badEye = crossingEye;
    badEye[1][3] = (std::numeric_limits<float>::quiet_NaN)();
    if (native_raw_fvf_projected_raster(
            {badEye.data(),sizeof(badEye[0]),badEye.size()},
            0,0,3440,1440,nearRaster))
        return reject(__LINE__);
    auto invalidNaN = verts;
    invalidNaN[2][0] = (std::numeric_limits<float>::quiet_NaN)();
    if (native_raw_fvf_projected_raster(
            {invalidNaN.data(), sizeof(invalidNaN[0]), invalidNaN.size()},
            0, 0, 3440, 1440, rect))
        return reject(__LINE__);
    if (native_raw_fvf_projected_raster(span, 0, 0, 0, 1440, rect) ||
        native_raw_fvf_projected_raster({}, 0, 0, 3440, 1440, rect))
        return reject(__LINE__);

    // The actual indexed native menu/vehicle/HUD GPU Draw references only
    // the three far-right vertices; the other positions in its VB are not
    // submitted. Bounding all VB vertices used to steer both 512x288 RGB
    // source captures away from the real shaded pixels on a 3440x1440 game.
    constexpr std::array<std::array<float, 4>, 6> indexedVerts{{
        {{-0.95f,-0.80f,0.5f,1.f}}, {{-0.85f,-0.70f,0.5f,1.f}},
        {{-0.80f,-0.75f,0.5f,1.f}},
        {{0.78f,0.25f,0.5f,1.f}}, {{0.95f,0.25f,0.5f,1.f}},
        {{0.90f,0.52f,0.5f,1.f}}
    }};
    constexpr std::array<std::uint32_t, 3> used{{3u,4u,5u}};
    const NativeRawFvfClipSpan indexed{
        indexedVerts.data(), sizeof(indexedVerts[0]), indexedVerts.size(),
        used.data(), used.size()};
    NativeRawDrawExtent indexedRect{}, broad{};
    if (!native_raw_fvf_projected_raster(
            indexed, 0, 0, 3440, 1440, indexedRect) ||
        indexedRect.left < 3000 || indexedRect.right > 3440 ||
        !native_raw_fvf_projected_raster(
            {indexedVerts.data(), sizeof(indexedVerts[0]),
             indexedVerts.size()}, 0, 0, 3440, 1440, broad) ||
        broad.left > 300 || indexedRect.left <= broad.left)
        return reject(__LINE__);
    NativeRawDualTile indexedGpu{};
    if (!native_raw_swept_dual_draw_tile(
            3440, 1440, 512, 288, indexedRect, 0u, indexedGpu) ||
        indexedGpu.first.x < 2500u)
        return reject(__LINE__);

    // Real menu and vehicle geometry may include fully offscreen and
    // depth-clipped D3D11 triangles in the SAME IA draw. Their vertices
    // must not drag a 512x288 source GPU tile away from visible right HUD.
    constexpr std::array<std::array<float,4>, 9> clippedMenu{{
        {{-20.f, 0.0f, 0.5f,1.f}}, {{-19.f,0.5f,0.5f,1.f}},
        {{-19.f,-0.5f,0.5f,1.f}}, // fully left-clipped
        {{-0.9f,-0.7f,-2.f,1.f}}, {{-0.8f,-0.7f,-2.f,1.f}},
        {{-0.8f,-0.6f,-2.f,1.f}}, // fully near-plane clipped
        {{0.78f,0.25f,0.5f,1.f}}, {{0.95f,0.25f,0.5f,1.f}},
        {{0.90f,0.52f,0.5f,1.f}}
    }};
    NativeRawDrawExtent clippedRect{};
    if (!native_raw_fvf_projected_raster(
            {clippedMenu.data(),sizeof(clippedMenu[0]),clippedMenu.size()},
            0,0,3440,1440,clippedRect) ||
        clippedRect.left != indexedRect.left ||
        clippedRect.right != indexedRect.right ||
        clippedRect.top != indexedRect.top ||
        clippedRect.bottom != indexedRect.bottom)
        return reject(__LINE__);
    // Cross the right clip plane: a genuine partly visible triangle
    // survives while its offscreen corner cannot widen capture beyond RT.
    auto crossing = verts;
    crossing[1][0] = 20.0f;
    if (!native_raw_fvf_projected_raster(
            {crossing.data(), sizeof(crossing[0]), crossing.size()},
            0,0,3440,1440,clippedRect) ||
        clippedRect.left < 3000 || clippedRect.right > 3442)
        return reject(__LINE__);
    // Triangle strip and triangle fan must follow actual GPU IA assembly.
    // A far out-of-frustum tail must not inflate the visible first tri.
    constexpr std::array<std::array<float,4>,4> stripVerts{{
        {{0.78f,0.25f,0.5f,1.f}}, {{0.95f,0.25f,0.5f,1.f}},
        {{0.90f,0.52f,0.5f,1.f}}, {{20.f,0.5f,0.5f,1.f}}
    }};
    for (auto assembly : {NativeRawFvfAssembly::TriangleStrip,
                          NativeRawFvfAssembly::TriangleFan}) {
        if (!native_raw_fvf_projected_raster(
                {stripVerts.data(),sizeof(stripVerts[0]),stripVerts.size(),
                 nullptr,0u,assembly},0,0,3440,1440,clippedRect) ||
            clippedRect.left < 3000 || clippedRect.right > 3442)
            return reject(__LINE__);
    }
    // Active malformed IA still fails closed, never dereferencing VB OOB.
    const std::array<std::uint32_t,4> badStrip{{0u,1u,2u,99u}};
    if (native_raw_fvf_projected_raster(
            {stripVerts.data(),sizeof(stripVerts[0]),stripVerts.size(),
             badStrip.data(),badStrip.size(),NativeRawFvfAssembly::TriangleStrip},
            0,0,3440,1440,clippedRect))
        return reject(__LINE__);
    // Malformed/unknown IA always falls back to the original broad GPU
    // source viewport capture. No index may read outside the live VB.
    auto malformed = used;
    malformed[2] = 6u;
    auto badSpan = indexed;
    badSpan.indices = malformed.data();
    if (native_raw_fvf_projected_raster(
            badSpan, 0, 0, 3440, 1440, rect) ||
        rect.left != 0 || rect.right != 0)
        return reject(__LINE__);
    badSpan = indexed;
    badSpan.indexCount = 0u;
    if (native_raw_fvf_projected_raster(
            badSpan, 0, 0, 3440, 1440, rect))
        return reject(__LINE__);
    badSpan = indexed;
    badSpan.indices = nullptr;
    if (native_raw_fvf_projected_raster(
            badSpan, 0, 0, 3440, 1440, rect))
        return reject(__LINE__);
    auto invalidActive = indexedVerts;
    invalidActive[5][3] = 0.0f;
    if (native_raw_fvf_projected_raster(
            {invalidActive.data(), sizeof(invalidActive[0]),
             invalidActive.size(), used.data(), used.size()},
            0, 0, 3440, 1440, rect))
        return reject(__LINE__);
    // Invalid UNREFERENCED VB clip data cannot silence the real indexed GPU
    // triangle: these positions never reach the native DrawIndexed raster.
    invalidActive = indexedVerts;
    invalidActive[0][3] = 0.0f;
    if (!native_raw_fvf_projected_raster(
            {invalidActive.data(), sizeof(invalidActive[0]),
             invalidActive.size(), used.data(), used.size()},
            0, 0, 3440, 1440, rect) ||
        rect.left != indexedRect.left || rect.right != indexedRect.right)
        return reject(__LINE__);
    return true;
}

// One real FVF Draw can span disjoint left-menu and right-HUD islands.
// Its merged rectangle can direct BOTH legacy GPU captures to empty space.
bool native_raw_fvf_island_regression() {
    const auto fail = [](int line) noexcept {
        std::fprintf(stderr, "FVF island regression failed at line %d\\n", line);
        return false;
    };
    constexpr std::array<std::array<float,4>,6> vertices{{
        {{-0.96f,-0.3f,0.5f,1.f}}, {{-0.84f,-0.3f,0.5f,1.f}},
        {{-0.9f,0.1f,0.5f,1.f}},
        {{0.84f,-0.3f,0.5f,1.f}}, {{0.96f,-0.3f,0.5f,1.f}},
        {{0.9f,0.1f,0.5f,1.f}}
    }};
    const NativeRawFvfClipSpan original{
        vertices.data(),sizeof(vertices[0]),vertices.size()};
    const NativeRawDrawExtent canvas{0,0,3440,1440};
    NativeRawDualTile tile{};
    const auto capture = [&](NativeRawFvfClipSpan span,
        NativeRawDrawExtent clip, std::uint32_t turn) {
        return native_raw_fvf_island_dual_draw_tile(
            span,0,0,3440,1440,3440,1440,512,288,clip,turn,tile);
    };
    if (!capture(original,canvas,0u) || !tile.hasSecond ||
        tile.first.x > 512u || tile.second.x < 2400u ||
        !native_raw_source_tiles_disjoint(tile.first,tile.second,512,288))
        return fail(__LINE__);
    if (!capture(original,canvas,1u) || !tile.hasSecond ||
        tile.first.x < 2400u || tile.second.x > 512u)
        return fail(__LINE__);
    constexpr std::array<std::uint32_t,6> reversed{{3,4,5,0,1,2}};
    const NativeRawFvfClipSpan indexed{
        vertices.data(),sizeof(vertices[0]),vertices.size(),
        reversed.data(),reversed.size()};
    if (!capture(indexed,canvas,0u) || !tile.hasSecond ||
        tile.first.x < 2400u || tile.second.x > 512u)
        return fail(__LINE__);
    // A scissor that excludes the right polygon cannot sample it.
    if (!capture(original,{0,0,800,1440},1u) ||
        tile.first.x > 512u ||
        (tile.hasSecond && tile.second.x > 512u)) return fail(__LINE__);
    auto malformed = reversed;
    malformed[4] = 99u;
    if (capture({vertices.data(),sizeof(vertices[0]),vertices.size(),
                 malformed.data(),malformed.size()},canvas,0u))
        return fail(__LINE__);
    auto invalid = vertices;
    invalid[4][3] = 0.f;
    if (capture({invalid.data(),sizeof(invalid[0]),invalid.size()},
                canvas,0u)) return fail(__LINE__);
    // A large single primitive must still produce two independent GPU
    // source regions under the original swept sampling algorithm.
    constexpr std::array<std::array<float,4>,3> broad{{
        {{-0.9f,-0.9f,0.5f,1.f}},{{0.9f,-0.9f,0.5f,1.f}},
        {{0.f,0.9f,0.5f,1.f}}
    }};
    return capture({broad.data(),sizeof(broad[0]),broad.size()},
                   canvas,0u) && tile.hasSecond;
}

// A single real Draw can contain TWO large, widely separated source triangles.
// Repeating the same scene must reach their inner GPU pixels, not just the
// first 512x288 corner on every revisit of an authentic source island.
bool native_raw_fvf_large_island_phase_regression() {
    const auto fail = [](int line) noexcept {
        std::fprintf(stderr, "FVF phased GPU island regression failed at line %d\\n", line);
        return false;
    };
    constexpr std::array<std::array<float,4>,6> triangles{{
        {{-0.94f,-0.90f,0.5f,1.f}}, {{-0.18f,-0.90f,0.5f,1.f}},
        {{-0.56f, 0.85f,0.5f,1.f}},
        {{ 0.18f,-0.90f,0.5f,1.f}}, {{ 0.94f,-0.90f,0.5f,1.f}},
        {{ 0.56f, 0.85f,0.5f,1.f}}
    }};
    constexpr auto sw=3440u, sh=1440u, tw=512u, th=288u;
    const NativeRawFvfClipSpan ia{
        triangles.data(), sizeof(triangles[0]), triangles.size()};
    const auto sample = [&](std::uint32_t ordinal, NativeRawDualTile& pair,
                            NativeRawDrawExtent clip = {0,0,3440,1440}) {
        return native_raw_fvf_island_dual_draw_tile(
            ia,0,0,sw,sh,sw,sh,tw,th,clip,ordinal,pair);
    };
    NativeRawDualTile left0{},right0{},left1{},right1{};
    if (!sample(0u,left0) || !sample(1u,right0) ||
        !sample(2u,left1) || !sample(3u,right1))
        return fail(__LINE__);
    if (!left0.hasSecond || !right0.hasSecond ||
        !left1.hasSecond || !right1.hasSecond ||
        left0.first.x >= 1600u || right0.first.x <= 1800u ||
        left0.second.x <= 1800u || right0.second.x >= 1600u)
        return fail(__LINE__);
    // Both large source islands must advance their OWN real raster origin;
    // a rotating triangle index by itself is not pixel-coverage progress.
    if (left0.first.x == left1.first.x &&
        left0.first.y == left1.first.y) return fail(__LINE__);
    if (right0.first.x == right1.first.x &&
        right0.first.y == right1.first.y) return fail(__LINE__);
    for (std::uint32_t turn = 0; turn < 32u; ++turn) {
        NativeRawDualTile pair{};
        if (!sample(turn,pair) || !pair.hasSecond ||
            !native_raw_source_tiles_disjoint(
                pair.first,pair.second,tw,th) ||
            pair.first.x > sw-tw || pair.first.y > sh-th ||
            pair.second.x > sw-tw || pair.second.y > sh-th)
            return fail(__LINE__);
    }
    // The admitted source scissor can clip away a second primitive.
    // Sampling must remain in the first real source footprint, never
    // inventing an off-scissor right island.
    NativeRawDualTile clipped{};
    for (std::uint32_t turn : {0u,1u,2u,9u}) {
        if (!sample(turn,clipped,{0,0,1500,1440}) ||
            clipped.first.x >= 1500u ||
            (clipped.hasSecond && clipped.second.x >= 1500u))
            return fail(__LINE__);
    }
    // Most of a full IA mesh can be outside the viewport. Only TWO
    // original triangles contribute native GPU pixels. Their capture sweep
    // must progress after two captures, not after all 32 IA triangles.
    std::array<std::array<float,4>,96> sparse{};
    for (auto& vertex : sparse)
        vertex = {{5.f,5.f,0.5f,1.f}}; // valid but entirely clip-rejected
    for (std::size_t i = 0u; i < triangles.size(); ++i)
        sparse[i] = triangles[i];
    const NativeRawFvfClipSpan sparseIa{
        sparse.data(), sizeof(sparse[0]), sparse.size()};
    const auto sparseSample = [&](std::uint32_t turn,
                                  NativeRawDrawExtent clip,
                                  NativeRawDualTile& result) {
        return native_raw_fvf_island_dual_draw_tile(
            sparseIa,0,0,sw,sh,sw,sh,tw,th,clip,turn,result);
    };
    NativeRawDualTile sparse0{}, sparse2{}, clipped0{}, clipped1{};
    const NativeRawDrawExtent canvas{0,0,3440,1440};
    // The original IA has 32 valid triangles but only TWO actual
    // scissor-visible RGB islands. The capture must rotate over the
    // survivors on every Draw (even after ordinal 2), rather than
    // repeatedly returning the first real menu/vehicle/race polygon.
    for (std::uint32_t ordinal = 0u; ordinal < 8u; ++ordinal) {
        NativeRawDualTile rotating{};
        if (!sparseSample(ordinal,canvas,rotating) ||
            (ordinal % 2u == 0u ? rotating.first.x >= 1600u :
                                   rotating.first.x <= 1800u))
            return fail(__LINE__);
    }
    // Exercise nonzero source IA offsets too: genuine menu triangles can
    // be scattered among dozens of correctly rejected offscreen ones.
    auto displaced = sparse;
    for (std::size_t i = 0u; i < triangles.size(); ++i) {
        displaced[i] = {{5.f,5.f,0.5f,1.f}};
        displaced[7u * 3u + i % 3u + (i / 3u) * 20u * 3u] = triangles[i];
    }
    const NativeRawFvfClipSpan displacedIa{
        displaced.data(),sizeof(displaced[0]),displaced.size()};
    for (std::uint32_t ordinal = 0u; ordinal < 8u; ++ordinal) {
        NativeRawDualTile rotating{};
        if (!native_raw_fvf_island_dual_draw_tile(
                displacedIa,0,0,sw,sh,sw,sh,tw,th,canvas,
                ordinal,rotating) ||
            (ordinal % 2u == 0u ? rotating.first.x >= 1600u :
                                   rotating.first.x <= 1800u))
            return fail(__LINE__);
    }
    if (!sparseSample(0u,canvas,sparse0) ||
        !sparseSample(2u,canvas,sparse2) ||
        !sparse0.hasSecond || !sparse2.hasSecond ||
        (sparse0.first.x == sparse2.first.x &&
         sparse0.first.y == sparse2.first.y) ||
        !native_raw_source_tiles_disjoint(
            sparse2.first,sparse2.second,tw,th))
        return fail(__LINE__);
    // When the scissor admits only the left original island, its local
    // sweep must advance every capture without sampling the excluded right.
    const NativeRawDrawExtent leftOnly{0,0,1500,1440};
    if (!sparseSample(0u,leftOnly,clipped0) ||
        !sparseSample(1u,leftOnly,clipped1) ||
        (clipped0.first.x == clipped1.first.x &&
         clipped0.first.y == clipped1.first.y) ||
        clipped0.first.x >= 1500u || clipped1.first.x >= 1500u ||
        (clipped1.hasSecond && clipped1.second.x >= 1500u))
        return fail(__LINE__);
    // A triangular menu primitive can have an AABB intersecting the
    // source scissor even though NONE of its pixels fall in that corner.
    // Scissor must clip the actual polygon before admitting a GPU source
    // island; a real second primitive inside the same source Draw survives.
    constexpr std::array<std::array<float,4>,3> cornerMiss{{
        {{0.0f,0.8f,0.5f,1.f}},{{0.8f,0.0f,0.5f,1.f}},
        {{0.8f,0.8f,0.5f,1.f}}
    }};
    constexpr std::array<std::array<float,4>,3> cornerHit{{
        {{0.13f,0.13f,0.5f,1.f}},{{0.27f,0.13f,0.5f,1.f}},
        {{0.20f,0.27f,0.5f,1.f}}
    }};
    constexpr NativeRawDrawExtent cornerScissor{550,350,650,450};
    const NativeRawFvfClipSpan miss{
        cornerMiss.data(),sizeof(cornerMiss[0]),cornerMiss.size()};
    const NativeRawFvfClipSpan hit{
        cornerHit.data(),sizeof(cornerHit[0]),cornerHit.size()};
    NativeRawDrawExtent aabb{}, clippedPolygon{};
    NativeRawDualTile tile{}; // malformed/off-scissor source must not queue RGB
    if (!native_raw_fvf_projected_raster(
            miss,0,0,1000,1000,aabb) ||
        aabb.left >= cornerScissor.right ||
        aabb.right <= cornerScissor.left ||
        aabb.top >= cornerScissor.bottom ||
        aabb.bottom <= cornerScissor.top)
        return fail(__LINE__); // deliberately intersecting AABB
    if (native_raw_fvf_projected_raster(
            miss,0,0,1000,1000,clippedPolygon,&cornerScissor) ||
        clippedPolygon.right != 0 ||
        native_raw_fvf_island_dual_draw_tile(
            miss,0,0,1000,1000,1000,1000,64,64,
            cornerScissor,0u,tile))
        return fail(__LINE__);
    if (!native_raw_fvf_projected_raster(
            hit,0,0,1000,1000,clippedPolygon,&cornerScissor) ||
        clippedPolygon.left < cornerScissor.left ||
        clippedPolygon.right > cornerScissor.right ||
        clippedPolygon.top < cornerScissor.top ||
        clippedPolygon.bottom > cornerScissor.bottom)
        return fail(__LINE__);
    constexpr std::array<std::array<float,4>,6> mixed{{
        cornerMiss[0], cornerMiss[1], cornerMiss[2],
        cornerHit[0], cornerHit[1], cornerHit[2]
    }};
    const NativeRawFvfClipSpan mixedSource{
        mixed.data(),sizeof(mixed[0]),mixed.size()};
    for (std::uint32_t ordinal = 0u; ordinal < 3u; ++ordinal) {
        NativeRawDualTile inside{};
        if (!native_raw_fvf_island_dual_draw_tile(
                mixedSource,0,0,1000,1000,1000,1000,64,64,
                cornerScissor,ordinal,inside) ||
            inside.first.x + 64u <= 550u || inside.first.x >= 650u ||
            inside.first.y + 64u <= 350u || inside.first.y >= 450u)
            return fail(__LINE__);
    }
    // No visible source triangle is NOT an admitted fabricated GPU region.
    auto allClipped = sparse;
    for (auto& vertex : allClipped)
        vertex = {{5.f,5.f,0.5f,1.f}};
    NativeRawDualTile absent{};
    if (native_raw_fvf_island_dual_draw_tile(
            {allClipped.data(),sizeof(allClipped[0]),allClipped.size()},
            0,0,sw,sh,sw,sh,tw,th,canvas,0u,absent))
        return fail(__LINE__);
    return true;
}


bool native_raw_fvf_live_cull_gpu_capture_regression() {
    const auto reject = [](int line) noexcept {
        std::fprintf(stderr, "FVF native GPU cull capture failed at %d\\n", line);
        return false;
    };
    // Native game RS front faces are clockwise in screen coordinates
    // unless FrontCounterClockwise is set. Opposite-facing game triangles
    // occupy disjoint screen islands, so sampling the wrong face misses
    // all real GPU-generated RGB even when the Draw succeeds.
    constexpr std::array<std::array<float,4>,6> positions{{
        {{-0.95f,-0.10f,0.5f,1.f}}, {{-0.70f,-0.10f,0.5f,1.f}},
        {{-0.80f, 0.30f,0.5f,1.f}}, // back-facing left island
        {{ 0.70f, 0.20f,0.5f,1.f}}, {{ 0.80f, 0.40f,0.5f,1.f}},
        {{ 0.95f, 0.20f,0.5f,1.f}}  // front-facing right island
    }};
    const NativeRawFvfClipSpan scene{
        positions.data(),sizeof(positions[0]),positions.size()};
    const NativeRawFvfRaster cullBack{NativeRawFvfCull::Back,false};
    const NativeRawFvfRaster cullFront{NativeRawFvfCull::Front,false};
    const NativeRawFvfRaster flipped{NativeRawFvfCull::Back,true};
    // NULL D3D11 RS means DEFAULT BACK CULL, not CULL_NONE. Explicit
    // D3D11 enum values remain distinct; malformed ones cannot guide a
    // GPU sample to an unverified source geometry.
    NativeRawFvfRaster defaultState{}, explicitNone{}, explicitFront{};
    NativeRawFvfRaster explicitBack{}, invalidRaster{};
    if (!native_raw_fvf_raster_from_d3d11(
            false,0u,true,true,defaultState) ||
        defaultState.cull != NativeRawFvfCull::Back ||
        defaultState.frontCounterClockwise ||
        !native_raw_fvf_raster_from_d3d11(
            true,1u,false,true,explicitNone) ||
        explicitNone.cull != NativeRawFvfCull::None ||
        !native_raw_fvf_raster_from_d3d11(
            true,2u,true,true,explicitFront) ||
        explicitFront.cull != NativeRawFvfCull::Front ||
        !explicitFront.frontCounterClockwise ||
        !native_raw_fvf_raster_from_d3d11(
            true,3u,false,true,explicitBack) ||
        explicitBack.cull != NativeRawFvfCull::Back ||
        native_raw_fvf_raster_from_d3d11(
            true,0u,false,true,invalidRaster) ||
        native_raw_fvf_raster_from_d3d11(
            true,4u,false,true,invalidRaster))
        return reject(__LINE__);
    NativeRawDrawExtent front{}, back{}, opposite{}, unculled{};
    if (!native_raw_fvf_projected_raster(
            scene,0,0,3440,1440,front,nullptr,&cullBack) ||
        !native_raw_fvf_projected_raster(
            scene,0,0,3440,1440,back,nullptr,&cullFront) ||
        !native_raw_fvf_projected_raster(
            scene,0,0,3440,1440,opposite,nullptr,&flipped) ||
        !native_raw_fvf_projected_raster(
            scene,0,0,3440,1440,unculled) ||
        front.left < 2900 || back.right > 520 ||
        (opposite.left != back.left || opposite.top != back.top ||
         opposite.right != back.right || opposite.bottom != back.bottom) ||
        unculled.left > back.left ||
        unculled.right < front.right)
        return reject(__LINE__);
    // The capture callsite now passes the real physical scissor/viewport
    // to polygon clipping. The left (back-facing) island must not survive
    // default BACK culling even when its AABB overlaps that scissor.
    const NativeRawDrawExtent leftHalf{0,0,1720,1440};
    const NativeRawDrawExtent rightHalf{1720,0,3440,1440};
    NativeRawDrawExtent nativeDefault{}, nativeLeft{};
    if (!native_raw_fvf_projected_raster(
            scene,0,0,3440,1440,nativeDefault,&rightHalf,&defaultState) ||
        nativeDefault.left < rightHalf.left ||
        nativeDefault.right > rightHalf.right ||
        native_raw_fvf_projected_raster(
            scene,0,0,3440,1440,nativeLeft,&leftHalf,&defaultState) ||
        nativeLeft.right != 0 ||
        !native_raw_fvf_projected_raster(
            scene,0,0,3440,1440,nativeLeft,&leftHalf,&explicitNone) ||
        nativeLeft.right > leftHalf.right ||
        native_raw_fvf_projected_raster(
            scene,0,0,3440,1440,nativeLeft,&leftHalf,&explicitFront) )
        return reject(__LINE__);
    NativeRawDualTile gpu{};
    if (!native_raw_fvf_island_dual_draw_tile(
            scene,0,0,3440,1440,3440,1440,512,288,
            {0,0,3440,1440},0u,gpu,&cullBack) ||
        gpu.first.x < 2800u ||
        !native_raw_fvf_island_dual_draw_tile(
            scene,0,0,3440,1440,3440,1440,512,288,
            {0,0,3440,1440},0u,gpu,&cullFront) ||
        gpu.first.x > 520u)
        return reject(__LINE__);
    // The hardware flips triangle-strip winding on each primitive.
    // Explicitly assembled list and actual strip MUST produce the same
    // visible two-triangle screen footprint with CullBack enabled.
    constexpr std::array<std::array<float,4>,4> strip{{
        {{-0.6f,-0.4f,0.5f,1.f}}, {{-0.3f,0.4f,0.5f,1.f}},
        {{ 0.0f,-0.4f,0.5f,1.f}}, {{ 0.3f,0.4f,0.5f,1.f}}
    }};
    constexpr std::array<std::uint32_t,6> triangleList{{0,1,2,2,1,3}};
    const NativeRawFvfClipSpan stripSource{
        strip.data(),sizeof(strip[0]),strip.size(),nullptr,0,
        NativeRawFvfAssembly::TriangleStrip};
    const NativeRawFvfClipSpan listSource{
        strip.data(),sizeof(strip[0]),strip.size(),
        triangleList.data(),triangleList.size(),
        NativeRawFvfAssembly::TriangleList};
    NativeRawDrawExtent stripRaster{}, listRaster{};
    if (!native_raw_fvf_projected_raster(
            stripSource,0,0,3440,1440,stripRaster,nullptr,&cullBack) ||
        !native_raw_fvf_projected_raster(
            listSource,0,0,3440,1440,listRaster,nullptr,&cullBack) ||
        stripRaster.left != listRaster.left ||
        stripRaster.right != listRaster.right ||
        stripRaster.top != listRaster.top ||
        stripRaster.bottom != listRaster.bottom)
        return reject(__LINE__);
    NativeRawDualTile stripGpu{}, listGpu{};
    if (!native_raw_fvf_island_dual_draw_tile(
            stripSource,0,0,3440,1440,3440,1440,512,288,
            {0,0,3440,1440},1u,stripGpu,&cullBack) ||
        !native_raw_fvf_island_dual_draw_tile(
            listSource,0,0,3440,1440,3440,1440,512,288,
            {0,0,3440,1440},1u,listGpu,&cullBack) ||
        stripGpu.first.x != listGpu.first.x ||
        stripGpu.first.y != listGpu.first.y)
        return reject(__LINE__);
    // Invalid W and unreferenced vertices must remain fail closed, even
    // when the other submitted triangle is front-facing.
    auto invalid = positions;
    invalid[5][3] = 0.f;
    if (native_raw_fvf_projected_raster(
            {invalid.data(),sizeof(invalid[0]),invalid.size()},
            0,0,3440,1440,front,nullptr,&cullBack))
        return reject(__LINE__);
    const NativeRawFvfRaster noCull{NativeRawFvfCull::None,false};
    if (!native_raw_fvf_projected_raster(
            scene,0,0,3440,1440,front,nullptr,&noCull) ||
        front.left != unculled.left || front.right != unculled.right)
        return reject(__LINE__);
    return true;
}

bool native_raw_fvf_depth_clip_disabled_gpu_capture_regression() {
    // D3D11's live rasterizer drops z near/far planes, NOT x/y, W,
    // scissor, real IA identity or face culling. Real menu and vehicle
    // surfaces outside z[0,w] can still produce genuine native RGB.
    NativeRawFvfRaster defaultRs{}, depthOff{}, depthOn{};
    if (!native_raw_fvf_raster_from_d3d11(
            false,0u,false,false,defaultRs) ||
        !defaultRs.depthClipEnable || // unbound RS uses hardware defaults
        !native_raw_fvf_raster_from_d3d11(
            true,1u,false,false,depthOff) ||
        depthOff.depthClipEnable ||
        !native_raw_fvf_raster_from_d3d11(
            true,1u,false,true,depthOn) ||
        !depthOn.depthClipEnable) return false;
    const std::array<std::array<float,4>,3> beyondNear{{
        {{-0.65f,-0.65f,-0.4f,1.f}},
        {{ 0.65f,-0.65f,-0.4f,1.f}},
        {{ 0.00f, 0.65f,-0.4f,1.f}}}};
    const auto nearSpan = NativeRawFvfClipSpan{
        beyondNear.data(),sizeof(beyondNear[0]),beyondNear.size()};
    NativeRawDrawExtent nearOff{}, nearOn{};
    if (native_raw_fvf_projected_raster(
            nearSpan,0,0,3440,1440,nearOn,nullptr,&depthOn) ||
        !native_raw_fvf_projected_raster(
            nearSpan,0,0,3440,1440,nearOff,nullptr,&depthOff) ||
        nearOff.left >= 1720 || nearOff.right <= 1720)
        return false;
    auto beyondFar = beyondNear;
    for (auto& point : beyondFar) point[2] = 1.4f;
    const auto farSpan = NativeRawFvfClipSpan{
        beyondFar.data(),sizeof(beyondFar[0]),beyondFar.size()};
    if (native_raw_fvf_projected_raster(
            farSpan,0,0,3440,1440,nearOn,nullptr,&depthOn) ||
        !native_raw_fvf_projected_raster(
            farSpan,0,0,3440,1440,nearOff,nullptr,&depthOff))
        return false;
    // With z clip disabled, real source-scissor sampling must still follow
    // the original triangle, not sample the other half of the viewport.
    const NativeRawDrawExtent rightHalf{1720,0,3440,1440};
    if (!native_raw_fvf_projected_raster(
            nearSpan,0,0,3440,1440,nearOff,&rightHalf,&depthOff) ||
        // Native raster rectangles intentionally have a 2px outward
        // GPU edge-sampling safety margin; shipping callsite intersects
        // the result with the exact physical source scissor again.
        nearOff.left < rightHalf.left - 2) return false;
    NativeRawDualTile samples{};
    if (!native_raw_fvf_island_dual_draw_tile(
            nearSpan,0,0,3440,1440,3440,1440,512,288,
            rightHalf,3u,samples,&depthOff) ||
        samples.first.x + 512u <= 1720u ||
        (samples.hasSecond &&
         !native_raw_source_tiles_disjoint(
             samples.first,samples.second,512,288))) return false;
    // A triangle straddling W=0 remains clipped at the eye plane even
    // with depth clip disabled; malformed zero W is never admitted.
    auto acrossEye = beyondNear;
    acrossEye[2][3] = -1.0f;
    const NativeRawFvfClipSpan eyeSpan{
        acrossEye.data(),sizeof(acrossEye[0]),acrossEye.size()};
    if (!native_raw_fvf_projected_raster(
            eyeSpan,0,0,3440,1440,nearOff,nullptr,&depthOff))
        return false;
    acrossEye[2][3] = 0.0f;
    if (native_raw_fvf_projected_raster(
            eyeSpan,0,0,3440,1440,nearOff,nullptr,&depthOff))
        return false;
    // Out-of-range original indexed IA remains fail-closed.
    constexpr std::array<std::uint32_t,3> badIndex{{0u,1u,9u}};
    const NativeRawFvfClipSpan malformed{
        beyondNear.data(),sizeof(beyondNear[0]),beyondNear.size(),
        badIndex.data(),badIndex.size(),NativeRawFvfAssembly::TriangleList};
    return !native_raw_fvf_projected_raster(
        malformed,0,0,3440,1440,nearOff,nullptr,&depthOff);
}
 // Real large diagonal FVF menu/vehicle triangles can fill less than 2% of
// their giant bounding box. The default corner sweep then captures zero
// native GPU pixels even though the source Draw covers its interior.
bool native_raw_fvf_sparse_diagonal_gpu_capture_regression() {
    constexpr std::array<std::array<float,4>,3> diagonal{{
        {{-0.95f,-0.94f,0.5f,1.0f}},
        {{ 0.94f, 0.95f,0.5f,1.0f}},
        {{ 0.95f, 0.93f,0.5f,1.0f}}
    }};
    const NativeRawFvfClipSpan source{
        diagonal.data(),sizeof(diagonal[0]),diagonal.size()};
    constexpr std::uint32_t sw=3440u,sh=1440u,tw=512u,th=288u;
    const NativeRawDrawExtent viewport{0,0,sw,sh};
    NativeRawDrawExtent bounds{};
    NativeRawFvfInteriorSample anchor{};
    if (!native_raw_fvf_projected_raster(
            source,0,0,sw,sh,bounds,&viewport,nullptr,&anchor) ||
        !anchor.sparseDiagonal || anchor.pixelX < 1800 ||
        anchor.pixelX > 2700 || anchor.pixelY < 250 ||
        anchor.pixelY > 800) return false;
    NativeRawDualTile first{},late{};
    if (!native_raw_fvf_island_dual_draw_tile(
            source,0,0,sw,sh,sw,sh,tw,th,viewport,0u,first) ||
        anchor.pixelX < first.first.x ||
        anchor.pixelX >= static_cast<std::int64_t>(first.first.x)+tw ||
        anchor.pixelY < first.first.y ||
        anchor.pixelY >= static_cast<std::int64_t>(first.first.y)+th)
        return false;
    // A centered sparse-diagonal native GPU capture must keep the genuine
    // first disjoint source-sweep region as its SECOND GPU capture. The old
    // fallback dropped this valid region and substituted the sweep's other
    // region (which could overlap the polygon interior). This is two
    // independent native source PRE/POST copies, never CPU pixel evidence.
    NativeRawDualTile sourceSweep{};
    if (!native_raw_swept_dual_draw_tile(
            sw,sh,tw,th,bounds,0u,sourceSweep) ||
        !sourceSweep.hasSecond ||
        !native_raw_source_tiles_disjoint(
            first.first,sourceSweep.first,tw,th) ||
        !first.hasSecond ||
        first.second.x != sourceSweep.first.x ||
        first.second.y != sourceSweep.first.y)
        return false;
    bool witnessedSecond = false;
    for (std::uint32_t phase = 0u; phase < 48u; ++phase) {
        NativeRawDualTile capture{};
        if (!native_raw_fvf_island_dual_draw_tile(
                source,0,0,sw,sh,sw,sh,tw,th,viewport,phase,capture) ||
            capture.first.x > sw-tw || capture.first.y > sh-th ||
            (capture.hasSecond &&
             (capture.second.x > sw-tw || capture.second.y > sh-th ||
              !native_raw_source_tiles_disjoint(
                  capture.first,capture.second,tw,th))))
            return false;
        witnessedSecond = witnessedSecond || capture.hasSecond;
    }
    if (!witnessedSecond) return false;
    // Later captures continue sweeping authentic source pixels, not a
    // permanently stationary or fabricated pixel/ROI.
    if (!native_raw_fvf_island_dual_draw_tile(
            source,0,0,sw,sh,sw,sh,tw,th,viewport,3u,late) ||
        (late.first.x == first.first.x &&
         late.first.y == first.first.y)) return false;
    // Physical source scissor and original cull winding stay authoritative.
    const NativeRawDrawExtent excluded{0,0,300,150};
    NativeRawDualTile none{};
    if (native_raw_fvf_island_dual_draw_tile(
            source,0,0,sw,sh,sw,sh,tw,th,excluded,0u,none))
        return false;
    auto invalid=diagonal;
    invalid[2][3]=0.0f;
    if (native_raw_fvf_island_dual_draw_tile(
            {invalid.data(),sizeof(invalid[0]),invalid.size()},
            0,0,sw,sh,sw,sh,tw,th,viewport,0u,none))
        return false;
    // Broad triangles are intentionally NOT replaced by an interior-only
    // anchor: existing dual-GPU source sweep remains available.
    constexpr std::array<std::array<float,4>,3> broad{{
        {{-0.9f,-0.9f,0.5f,1.f}},
        {{ 0.9f,-0.9f,0.5f,1.f}},
        {{ 0.f, 0.9f,0.5f,1.f}}
    }};
    if (!native_raw_fvf_projected_raster(
            {broad.data(),sizeof(broad[0]),broad.size()},
            0,0,sw,sh,bounds,&viewport,nullptr,&anchor) ||
        anchor.sparseDiagonal) return false;
    return true;
}

int main() {
    assert(native_raw_fvf_sparse_diagonal_gpu_capture_regression());
    assert(native_raw_fvf_depth_clip_disabled_gpu_capture_regression());
    assert(native_raw_fvf_live_cull_gpu_capture_regression());
    assert(native_raw_fvf_clip_capture_regression());
    assert(native_raw_fvf_large_island_phase_regression());
    assert(native_raw_fvf_island_regression());
    assert(native_raw_source_color_write_selection_regression());
    {
        constexpr std::uint32_t w=2u,h=2u;
        const std::array<std::uint8_t,16u> pre{};
        const std::array<std::uint8_t,16u> post{{
            11u,21u,31u,0u,12u,22u,32u,7u,
            13u,23u,33u,91u,14u,24u,34u,203u}};
        const NativeRawPresentTile tile{0u,0u,w,h,130,240};
        std::array<std::uint8_t,16u> dst{};
        // Source B8G8R8X8 -> original game A8: opaque, authentic RGB.
        assert(native_raw_copy_packed_present_island(
            dst.data(),w*4u,pre.data(),w*4u,post.data(),w*4u,
            w,h,tile,NativeRawColorByteOrder::Bgra,
            native_raw_requires_opaque_alpha(true,false)));
        for(std::uint32_t p=0u;p<w*h;++p) {
            assert(dst[p*4u]==post[p*4u] &&
                   dst[p*4u+1u]==post[p*4u+1u] &&
                   dst[p*4u+2u]==post[p*4u+2u] &&
                   dst[p*4u+3u]==255u);
        }
        // Source A8 alpha remains real, not forced opaque.
        assert(native_raw_copy_packed_present_island(
            dst.data(),w*4u,pre.data(),w*4u,post.data(),w*4u,
            w,h,tile,NativeRawColorByteOrder::Bgra,
            native_raw_requires_opaque_alpha(false,false)));
        for(std::uint32_t p=0u;p<w*h;++p)
            assert(dst[p*4u+3u]==post[p*4u+3u]);
        // R8G8B8A8 native source retains its correct channel swizzle.
        assert(native_raw_copy_packed_present_island(
            dst.data(),w*4u,pre.data(),w*4u,post.data(),w*4u,
            w,h,tile,NativeRawColorByteOrder::Rgba,false));
        assert(dst[0]==31u && dst[1]==21u &&
               dst[2]==11u && dst[3]==0u);
        const auto prior=dst;
        auto invalid=tile;invalid.sourceX=w;
        assert(!native_raw_copy_packed_present_island(
            dst.data(),w*4u,pre.data(),w*4u,post.data(),w*4u,
            w,h,invalid,NativeRawColorByteOrder::Bgra,true));
        assert(dst==prior);
    }
    // The same real source-native RT must resolve both PRE and POST tiles.
    for (unsigned samples : {1u, 2u, 4u, 8u, 16u, 32u}) {
        assert(native_raw_msaa_capture_samples_supported(samples));
        assert(native_raw_msaa_resolve_required(samples) == (samples != 1u));
    }
    for (unsigned bad : {0u, 3u, 5u, 6u, 7u, 33u, 64u, 0xffffffffu}) {
        assert(!native_raw_msaa_capture_samples_supported(bad));
        assert(!native_raw_msaa_resolve_required(bad));
    }
    assert(native_raw_swept_source_coverage_regression());
    assert(native_raw_even_grid_source_coverage_regression());
    // Different D3D9 interface pointers may identify the same canonical
    // game backbuffer. Never accept an unrelated or unavailable IUnknown.
    int drawSurface = 0, presentedSurface = 0, canonical = 0, foreign = 0;
    assert(native_raw_canonical_source_target_is_presented(
        &drawSurface, &presentedSurface, &canonical, &canonical));
    assert(!native_raw_canonical_source_target_is_presented(
        &drawSurface, &presentedSurface, &canonical, &foreign));
    assert(!native_raw_canonical_source_target_is_presented(
        &drawSurface, &presentedSurface, &canonical,
        static_cast<int*>(nullptr)));
    assert(!native_raw_canonical_source_target_is_presented(
        static_cast<int*>(nullptr), &presentedSurface,
        &canonical, &canonical));
    // Source-coincident RAW publishing previously rejected the ENTIRE
    // 64x40 tile if the game repainted only a smaller legitimate dirty island.
    // This must preserve exactly the GPU source coordinates and RGB evidence.
    {
        constexpr std::uint32_t w = 96u, h = 64u;
        std::array<std::uint8_t, w * h * 4u> prior{};
        auto after = prior;
        after[(22u * w + 65u) * 4u + 2u] = 201u;
        NativeRawChangedPixelWindow delta;
        delta.capture(prior.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion island{};
        island.headerVerified = true;
        island.count = 1u;
        island.rectangles[0] = {160, 220, 173, 236};
        island.boundLeft = 160; island.boundTop = 220;
        island.boundRight = 173; island.boundBottom = 236;
        const NativeRawPresentTile fullGpuTile{10u, 10u, 64u, 40u, 110, 210};
        NativeRawPresentTile cropped{};
        std::uint32_t realRgb = 0u;
        assert(!native_raw_dirty_region_covers_tile(
            1920, 1080, island, fullGpuTile));
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, island, fullGpuTile, delta, cropped, realRgb));
        assert(realRgb == 1u && cropped.sourceX == 60u &&
               cropped.sourceY == 20u && cropped.copyWidth == 13u &&
               cropped.copyHeight == 16u && cropped.destinationX == 160 &&
               cropped.destinationY == 220);
        assert(delta.changed_pixels(cropped) == realRgb);
        // A second independent native Draw on the SAME original
        // backbuffer can repaint a DIFFERENT-size dirty island. Keep the
        // actual source-pixel coordinates and both GPU RGB contributions.
        NativeRawPresentDirtyRegion twoIslands = island;
        twoIslands.count = 2u;
        twoIslands.rectangles[1] = {356, 220, 374, 246};
        twoIslands.boundRight = 374;
        twoIslands.boundBottom = 246;
        const NativeRawPresentTile secondDraw{5u, 5u, 64u, 40u, 310, 210};
        NativeRawPresentTile secondCrop{};
        std::uint32_t secondRgb = 0u;
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, twoIslands, secondDraw, delta,
            secondCrop, secondRgb));
        assert(secondRgb == 1u && secondCrop.sourceX == 51u &&
               secondCrop.sourceY == 15u && secondCrop.copyWidth == 18u &&
               secondCrop.copyHeight == 26u &&
               secondCrop.destinationX == 356 &&
               secondCrop.destinationY == 220);
        assert(native_raw_dirty_region_covers_tile(
            1920, 1080, twoIslands, cropped));
        assert(native_raw_dirty_region_covers_tile(
            1920, 1080, twoIslands, secondCrop));
        assert(native_raw_can_show_source_aligned_pair(
            false, true, true, cropped, secondCrop));
        // More than two contiguous real game dirty rectangles may cover a
        // single native GPU Draw RGB island. Select their true rectangular
        // union instead of discarding all but one source fragment.
        {
            std::array<std::uint8_t, w * h * 4u> fragmentedBefore{};
            auto fragmentedAfter = fragmentedBefore;
            fragmentedAfter[(22u * w + 65u) * 4u] = 71u;
            fragmentedAfter[(22u * w + 75u) * 4u + 1u] = 83u;
            NativeRawChangedPixelWindow rgbUnion;
            rgbUnion.capture(fragmentedBefore.data(), w * 4u,
                             fragmentedAfter.data(), w * 4u, w, h);
            // Unlike the prior 64px sample, the fragmented full crop must
            // cover the second authentic RGB pixel at source x=75.
            const NativeRawPresentTile fragmentedGpu{10u, 10u, 76u, 40u, 110, 210};
            NativeRawPresentDirtyRegion fragments{};
            fragments.headerVerified = true;
            fragments.count = 3u;
            fragments.rectangles[0] = {160, 220, 166, 236};
            fragments.rectangles[1] = {166, 220, 172, 236};
            fragments.rectangles[2] = {172, 220, 180, 236};
            fragments.boundLeft = 160; fragments.boundTop = 220;
            fragments.boundRight = 180; fragments.boundBottom = 236;
            NativeRawPresentTile multi{};
            std::uint32_t rgbCount = 0u;
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, fragments, fragmentedGpu, rgbUnion,
                multi, rgbCount));
            assert(rgbCount == 2u && multi.sourceX == 60u &&
                   multi.sourceY == 20u && multi.copyWidth == 20u &&
                   multi.copyHeight == 16u && multi.destinationX == 160 &&
                   multi.destinationY == 220);
            assert(native_raw_dirty_region_covers_tile(
                1920, 1080, fragments, multi));
            // Missing ONE real destination pixel breaks the union:
            // never stretch a native GPU fragment across a D3D9 dirty gap.
            fragments.rectangles[2].left = 173;
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, fragments, fragmentedGpu, rgbUnion,
                multi, rgbCount));
            assert(rgbCount == 1u && multi.copyWidth < 20u);
            // Repaint geometry is untrusted until rcBound agrees with
            // every member. Even a real RGB source pixel cannot override it.
            fragments.boundRight = 181;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, fragments, fragmentedGpu, rgbUnion,
                multi, rgbCount));
            // Vertical fragmented game repaint is equally source-coincident.
            fragmentedAfter[(33u * w + 65u) * 4u + 2u] = 93u;
            rgbUnion.capture(fragmentedBefore.data(), w * 4u,
                             fragmentedAfter.data(), w * 4u, w, h);
            fragments = {};
            fragments.headerVerified = true;
            fragments.count = 2u;
            fragments.rectangles[0] = {160, 220, 180, 228};
            fragments.rectangles[1] = {160, 228, 180, 236};
            fragments.boundLeft = 160; fragments.boundTop = 220;
            fragments.boundRight = 180; fragments.boundBottom = 236;
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, fragments, fragmentedGpu, rgbUnion,
                multi, rgbCount));
            assert(rgbCount == 3u && multi.copyWidth == 20u &&
                   multi.copyHeight == 16u && multi.destinationX == 160 &&
                   multi.destinationY == 220);
        }
        // The real DX11 PRE/POST RGB can land at OPPOSITE corners of
        // nine 16x16 D3D9 menu/vehicle repaint cells. A thin attached tail
        // makes the whole connected component bounding box non-rectangular.
        // Neither the per-member nor connected-bounds crop can preserve both.
        {
            std::array<std::uint8_t, w * h * 4u> gridBefore{};
            auto gridAfter = gridBefore;
            // Original backbuffer (130,230) and (170,260), not relocated.
            gridAfter[(20u * w + 20u) * 4u + 0u] = 51u;
            gridAfter[(50u * w + 60u) * 4u + 2u] = 92u;
            NativeRawChangedPixelWindow gridRgb{};
            gridRgb.capture(gridBefore.data(), w * 4u,
                            gridAfter.data(), w * 4u, w, h);
            NativeRawPresentDirtyRegion grid{};
            grid.headerVerified = true;
            grid.count = 10u;
            for (std::uint32_t gy = 0u; gy < 3u; ++gy)
                for (std::uint32_t gx = 0u; gx < 3u; ++gx)
                    grid.rectangles[gy * 3u + gx] = {
                        125 + std::int64_t{gx} * 16,
                        220 + std::int64_t{gy} * 16,
                        141 + std::int64_t{gx} * 16,
                        236 + std::int64_t{gy} * 16};
            grid.rectangles[9] = {173, 220, 185, 232};
            grid.boundLeft = 125; grid.boundTop = 220;
            grid.boundRight = 185; grid.boundBottom = 268;
            const NativeRawPresentTile entireGpu{0u, 0u, w, h, 110, 210};
            NativeRawPresentTile chosen{};
            std::uint32_t rgb = 0u;
            assert(!native_raw_dirty_region_covers_tile(
                1920, 1080, grid, entireGpu));
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, grid, entireGpu, gridRgb, chosen, rgb));
            assert(rgb == 2u && chosen.sourceX == 15u &&
                   chosen.sourceY == 10u && chosen.copyWidth == 48u &&
                   chosen.copyHeight == 48u && chosen.destinationX == 125 &&
                   chosen.destinationY == 220);
            assert(native_raw_dirty_region_covers_tile(
                1920, 1080, grid, chosen));
            assert(gridRgb.changed_pixels(chosen) == 2u);
            // Remove the painted centre: bounding-box and component proofs
            // must not stretch GPU pixels across the missing D3D9 rectangle.
            grid.rectangles[4] = {185, 220, 189, 232};
            grid.boundRight = 189;
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, grid, entireGpu, gridRgb, chosen, rgb));
            assert(rgb == 1u);
            // A forged rcBound invalidates the ENTIRE region, not just the
            // candidate whose box happens to match it.
            grid.boundRight = 190;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, grid, entireGpu, gridRgb, chosen, rgb));
            assert(rgb == 0u);
            // Source alpha cannot masquerade as real GPU-generated RGB.
            grid = {};
            grid.headerVerified = true; grid.count = 1u;
            grid.rectangles[0] = {125, 220, 173, 268};
            grid.boundLeft = 125; grid.boundTop = 220;
            grid.boundRight = 173; grid.boundBottom = 268;
            gridAfter = gridBefore;
            gridAfter[(20u * w + 20u) * 4u + 3u] = 255u;
            gridRgb.capture(gridBefore.data(), w * 4u,
                            gridAfter.data(), w * 4u, w, h);
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, grid, entireGpu, gridRgb, chosen, rgb));
        }
        // One authentic native GPU Draw can change two DISJOINT
        // original D3D9 menu/car dirty islands. The second needs its own
        // UpdateSurface rect, not a widened hole-filling bounding box.
        {
            constexpr std::uint32_t pw = 96u, ph = 64u;
            std::array<std::uint8_t, pw * ph * 4u> beforePair{};
            auto afterPair = beforePair;
            afterPair[(20u * pw + 20u) * 4u] = 31u;
            afterPair[(35u * pw + 70u) * 4u + 2u] = 91u;
            NativeRawChangedPixelWindow pairRgb{};
            pairRgb.capture(beforePair.data(), pw * 4u,
                            afterPair.data(), pw * 4u, pw, ph);
            NativeRawPresentDirtyRegion islands{};
            islands.headerVerified = true;
            islands.count = 2u;
            islands.rectangles[0] = {110, 210, 140, 235};
            islands.rectangles[1] = {160, 225, 180, 255};
            islands.boundLeft = 110; islands.boundTop = 210;
            islands.boundRight = 180; islands.boundBottom = 255;
            const NativeRawPresentTile fullCapture{0u, 0u, pw, ph, 100, 200};
            NativeRawPresentTile primary{}, remainder{};
            std::uint32_t primaryRgb = 0u, remainderRgb = 0u;
            assert(!native_raw_dirty_region_covers_tile(
                1920, 1080, islands, fullCapture));
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                primary, primaryRgb));
            assert(primaryRgb == 1u && primary.destinationX == 110 &&
                   primary.destinationY == 210);
            assert(native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                remainder, remainderRgb, &primary));
            assert(remainderRgb == 1u && remainder.destinationX == 160 &&
                   remainder.destinationY == 225 &&
                   native_raw_disjoint_present_tiles(primary, remainder));
            assert(pairRgb.changed_pixels(primary) == 1u &&
                   pairRgb.changed_pixels(remainder) == 1u);
            // Repeated passes may not redisplay the same real source pixel.
            NativeRawPresentTile third{};
            std::uint32_t thirdRgb = 99u;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                third, thirdRgb, &fullCapture));
            assert(thirdRgb == 0u);
            // A forged rcBound never permits either GPU upload.
            islands.boundRight = 181;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                third, thirdRgb, &primary));
            assert(thirdRgb == 0u);
            islands.boundRight = 180;
            // Alpha-only output in the second island is not native RGB.
            afterPair[(35u * pw + 70u) * 4u + 2u] = 0u;
            afterPair[(35u * pw + 70u) * 4u + 3u] = 255u;
            pairRgb.capture(beforePair.data(), pw * 4u,
                            afterPair.data(), pw * 4u, pw, ph);
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, islands, fullCapture, pairRgb,
                remainder, remainderRgb, &primary));
            assert(remainderRgb == 0u);
        }
        // A live GPU Draw can change FOUR disjoint menu/vehicle repaint
        // regions. Each source-aligned UpdateSurface needs an independent
        // immutable staging surface and a non-overlapping exact-source crop.
        {
            constexpr std::uint32_t mw = 128u, mh = 96u;
            std::array<std::uint8_t, mw * mh * 4u> beforeMulti{};
            auto afterMulti = beforeMulti;
            const std::uint32_t xs[4]{16u, 56u, 16u, 106u};
            const std::uint32_t ys[4]{16u, 16u, 61u, 61u};
            NativeRawPresentDirtyRegion four{};
            four.headerVerified = true;
            four.count = 4u;
            for (std::uint32_t i = 0u; i < four.count; ++i) {
                afterMulti[(ys[i] * mw + xs[i]) * 4u + (i % 3u)] =
                    static_cast<std::uint8_t>(50u + i);
                four.rectangles[i] = {200 + std::int64_t{xs[i]} - 6,
                    300 + std::int64_t{ys[i]} - 6,
                    200 + std::int64_t{xs[i]} + 6,
                    300 + std::int64_t{ys[i]} + 6};
            }
            four.boundLeft = 210; four.boundTop = 310;
            four.boundRight = 312; four.boundBottom = 367;
            NativeRawChangedPixelWindow multiRgb{};
            multiRgb.capture(beforeMulti.data(), mw * 4u,
                             afterMulti.data(), mw * 4u, mw, mh);
            const NativeRawPresentTile full{0u, 0u, mw, mh, 200, 300};
            std::array<NativeRawPresentTile, 4> picks{};
            std::uint32_t count = 0u, totalRgb = 0u;
            for (; count < picks.size(); ++count) {
                std::uint32_t rgb = 0u;
                assert(native_raw_dirty_source_rgb_crop(
                    1920, 1080, four, full, multiRgb, picks[count],
                    rgb, count ? picks.data() : nullptr, count ? count : 1u));
                assert(rgb == 1u && native_raw_dirty_region_covers_tile(
                    1920, 1080, four, picks[count]));
                for (std::uint32_t j = 0u; j < count; ++j)
                    assert(native_raw_disjoint_present_tiles(picks[count], picks[j]));
                totalRgb += rgb;
            }
            assert(totalRgb == 4u);
            NativeRawPresentTile extra{};
            std::uint32_t extraRgb = 99u;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, four, full, multiRgb, extra, extraRgb,
                picks.data(), 4u) && extraRgb == 0u);
            // Reject an invalid exclusion budget and forged dirty bounds.
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, four, full, multiRgb, extra, extraRgb,
                picks.data(), 5u) && extraRgb == 0u);
            four.boundRight = 313;
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, four, full, multiRgb, extra, extraRgb,
                picks.data(), 1u) && extraRgb == 0u);
            // A last island with only an alpha mutation is not RGB evidence.
            four.boundRight = 312;
            afterMulti[(ys[3] * mw + xs[3]) * 4u] = 0u;
            afterMulti[(ys[3] * mw + xs[3]) * 4u + 3u] = 255u;
            multiRgb.capture(beforeMulti.data(), mw * 4u,
                             afterMulti.data(), mw * 4u, mw, mh);
            // The other three still produce RGB, the fourth must not.
            count = 0u;
            for (; count < 3u; ++count) {
                std::uint32_t rgb = 0u;
                assert(native_raw_dirty_source_rgb_crop(
                    1920, 1080, four, full, multiRgb, picks[count],
                    rgb, count ? picks.data() : nullptr, count ? count : 1u));
                assert(rgb == 1u);
            }
            assert(!native_raw_dirty_source_rgb_crop(
                1920, 1080, four, full, multiRgb, extra, extraRgb,
                picks.data(), 3u) && extraRgb == 0u);
        }
        // Two disjoint authentic GPU PRE/POST sources may each contain TWO
        // separately repainted menu/car pixels. Retain both sources in one
        // exact-Present upload batch, not just one island per source.
        {
            constexpr std::uint32_t tw = 96u, th = 64u;
            std::array<std::uint8_t, tw * th * 4u> beforeA{}, beforeB{};
            auto afterA = beforeA, afterB = beforeB;
            afterA[(14u * tw + 12u) * 4u] = 21u;
            afterA[(14u * tw + 52u) * 4u + 1u] = 41u;
            afterB[(41u * tw + 12u) * 4u + 2u] = 61u;
            afterB[(41u * tw + 75u) * 4u] = 81u;
            NativeRawChangedPixelWindow rgbA{}, rgbB{};
            rgbA.capture(beforeA.data(), tw * 4u, afterA.data(), tw * 4u, tw, th);
            rgbB.capture(beforeB.data(), tw * 4u, afterB.data(), tw * 4u, tw, th);
            NativeRawPresentDirtyRegion repaint{};
            repaint.headerVerified = true;
            repaint.count = 4u;
            repaint.rectangles[0] = {208, 310, 216, 318};
            repaint.rectangles[1] = {248, 310, 256, 318};
            repaint.rectangles[2] = {408, 337, 416, 345};
            repaint.rectangles[3] = {471, 337, 479, 345};
            repaint.boundLeft = 208; repaint.boundTop = 310;
            repaint.boundRight = 479; repaint.boundBottom = 345;
            const NativeRawPresentTile sourceA{0u, 0u, tw, th, 200, 300};
            const NativeRawPresentTile sourceB{0u, 0u, tw, th, 400, 300};
            NativeRawSourceIslandBatch batch{};
            assert(batch.append(1920, 1080, repaint, sourceA, rgbA, false));
            assert(batch.append(1920, 1080, repaint, sourceB, rgbB, true));
            assert(batch.append(1920, 1080, repaint, sourceA, rgbA, false));
            assert(batch.append(1920, 1080, repaint, sourceB, rgbB, true));
            assert(batch.count == 4u && !batch.alternate[0] &&
                   batch.alternate[1] && !batch.alternate[2] &&
                   batch.alternate[3]);
            std::uint32_t total = 0u;
            for (std::uint32_t i = 0u; i < batch.count; ++i) {
                total += batch.rgbPixels[i];
                assert(batch.rgbPixels[i] == 1u);
                assert(native_raw_dirty_region_covers_tile(
                    1920, 1080, repaint, batch.tiles[i]));
                for (std::uint32_t j = 0u; j < i; ++j)
                    assert(native_raw_disjoint_present_tiles(
                        batch.tiles[i], batch.tiles[j]));
            }
            assert(total == 4u);
            assert(!batch.append(1920, 1080, repaint, sourceA, rgbA, false));
            repaint.boundRight = 480; // forged union is never eligible
            NativeRawSourceIslandBatch invalid{};
            assert(!invalid.append(1920, 1080, repaint, sourceA, rgbA, false));
            repaint.boundRight = 479;
            // Alpha-only writes cannot create the second source RGB island.
            afterB[(41u * tw + 75u) * 4u] = 0u;
            afterB[(41u * tw + 75u) * 4u + 3u] = 255u;
            rgbB.capture(beforeB.data(), tw * 4u, afterB.data(), tw * 4u, tw, th);
            NativeRawSourceIslandBatch three{};
            assert(three.append(1920, 1080, repaint, sourceA, rgbA, false));
            assert(three.append(1920, 1080, repaint, sourceB, rgbB, true));
            assert(three.append(1920, 1080, repaint, sourceA, rgbA, false));
            assert(!three.append(1920, 1080, repaint, sourceB, rgbB, true));
            assert(three.count == 3u);
        }
        // Alpha-only mutations must not create native RGB evidence.
        after[(22u * w + 65u) * 4u + 2u] = 0u;
        after[(22u * w + 65u) * 4u + 3u] = 255u;
        delta.capture(prior.data(), w * 4u, after.data(), w * 4u, w, h);
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, island, fullGpuTile, delta, cropped, realRgb));
        // Malformed dirty bounds or a disjoint repaint must fail closed.
        after[(22u * w + 65u) * 4u + 2u] = 201u;
        delta.capture(prior.data(), w * 4u, after.data(), w * 4u, w, h);
        island.boundRight = 174;
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, island, fullGpuTile, delta, cropped, realRgb));
        island.boundRight = 173;
        island.rectangles[0] = {400, 400, 413, 416};
        island.boundLeft = 400; island.boundTop = 400;
        island.boundRight = 413; island.boundBottom = 416;
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, island, fullGpuTile, delta, cropped, realRgb));
    }
    // Overlapping real Draw extents must not erase non-overlapping GPU RGB
    // contributions at their authentic original-game Present coordinates.
    {
        constexpr std::uint32_t w = 64u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto afterA = before, afterB = before;
        afterA[(10u * w + 8u) * 4u] = 71u;
        afterB[(10u * w + 55u) * 4u + 2u] = 91u;
        NativeRawChangedPixelWindow a{}, b{};
        a.capture(before.data(), w * 4u, afterA.data(), w * 4u, w, h);
        b.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true; dirty.count = 1u;
        dirty.rectangles[0] = {300, 400, 364, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 364; dirty.boundBottom = 432;
        const NativeRawPresentTile first{0u, 0u, 32u, 32u, 300, 400};
        const NativeRawPresentTile overlap{20u, 0u, 44u, 32u, 320, 400};
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920, 1080, dirty, first, a, false));
        assert(batch.append(1920, 1080, dirty, overlap, b, true));
        assert(batch.count == 2u && !batch.alternate[0] &&
               batch.alternate[1] && batch.tiles[1].destinationX == 332 &&
               batch.tiles[1].sourceX == 32u &&
               batch.tiles[1].copyWidth == 32u &&
               batch.rgbPixels[0] == 1u && batch.rgbPixels[1] == 1u &&
               native_raw_disjoint_present_tiles(batch.tiles[0], batch.tiles[1]));
        // Two previously uploaded islands divide a third authentic Draw
        // into three possible disjoint bands. The changed pixel survives.
        const NativeRawPresentTile used[2]{
            {0u, 0u, 20u, 32u, 320, 400},
            {0u, 0u, 8u, 32u, 356, 400}
        };
        NativeRawPresentTile remainder{};
        std::uint32_t rgb = 0u;
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty,
            NativeRawPresentTile{0u, 0u, 64u, 32u, 300, 400},
            b, remainder, rgb, used, 2u));
        assert(rgb == 1u && remainder.destinationX == 340 &&
               remainder.sourceX == 40u && remainder.copyWidth == 16u &&
               native_raw_disjoint_present_tiles(remainder, used[0]) &&
               native_raw_disjoint_present_tiles(remainder, used[1]));
        // Invalid old upload, forged dirty union and alpha-only changes
        // cannot make the later GPU region appear as valid game RGB.
        const NativeRawPresentTile foreign{0u, 0u, 12u, 8u, 1200, 400};
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, overlap, b, remainder, rgb, &foreign));
        dirty.boundRight = 365;
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, overlap, b, remainder, rgb,
            batch.tiles.data()));
        dirty.boundRight = 364;
        afterB[(10u * w + 55u) * 4u + 2u] = 0u;
        afterB[(10u * w + 55u) * 4u + 3u] = 255u;
        b.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        assert(!native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, overlap, b, remainder, rgb,
            batch.tiles.data()));
    }
    // Overlapping live GPU Draw sample boxes need not overlap their actual
    // changed RGB. Preserve both authentic game source pixels, not just one.
    {
        constexpr std::uint32_t w = 64u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto afterA = before, afterB = before;
        afterA[(10u * w + 8u) * 4u] = 71u;
        afterB[(10u * w + 55u) * 4u + 2u] = 91u;
        NativeRawChangedPixelWindow rgbA{}, rgbB{};
        rgbA.capture(before.data(), w * 4u, afterA.data(), w * 4u, w, h);
        rgbB.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true; dirty.count = 1u;
        dirty.rectangles[0] = {300, 400, 364, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 364; dirty.boundBottom = 432;
        const NativeRawPresentTile source{0u, 0u, w, h, 300, 400};
        NativeRawSourceIslandBatch legacy{};
        assert(legacy.append(1920, 1080, dirty, source, rgbA, false));
        assert(!legacy.append(1920, 1080, dirty, source, rgbB, true));
        NativeRawSourceIslandBatch tight{};
        assert(tight.append(1920, 1080, dirty, source, rgbA, false, true));
        assert(tight.append(1920, 1080, dirty, source, rgbB, true, true));
        assert(tight.count == 2u && tight.rgbPixels[0] == 1u &&
               tight.rgbPixels[1] == 1u &&
               tight.tiles[0].sourceX == 8u &&
               tight.tiles[0].sourceY == 10u &&
               tight.tiles[0].destinationX == 308 &&
               tight.tiles[0].destinationY == 410 &&
               tight.tiles[0].copyWidth == 1u &&
               tight.tiles[0].copyHeight == 1u &&
               tight.tiles[1].sourceX == 55u &&
               tight.tiles[1].destinationX == 355 &&
               native_raw_disjoint_present_tiles(tight.tiles[0], tight.tiles[1]));
        // A 2x2 changed block retains all its authentic pixels and mapping.
        auto afterWide = before;
        for (std::uint32_t y = 18u; y < 20u; ++y)
            for (std::uint32_t x = 26u; x < 28u; ++x)
                afterWide[(y * w + x) * 4u + 1u] = 123u;
        NativeRawChangedPixelWindow rgbWide{};
        rgbWide.capture(before.data(), w * 4u,
                        afterWide.data(), w * 4u, w, h);
        NativeRawPresentTile bounded{};
        std::uint32_t realRgb = 0u;
        assert(rgbWide.tighten_to_rgb_bounds(source, bounded, realRgb));
        assert(realRgb == 4u && bounded.sourceX == 26u &&
               bounded.sourceY == 18u && bounded.destinationX == 326 &&
               bounded.destinationY == 418 && bounded.copyWidth == 2u &&
               bounded.copyHeight == 2u &&
               rgbWide.changed_pixels(bounded) == realRgb);
        assert(tight.append(1920, 1080, dirty, source, rgbWide, false, true));
        assert(!tight.append(1920, 1080, dirty, source, rgbWide, false, true));
        // Alpha-only content, forged source dirty geometry: fail closed.
        afterB[(10u * w + 55u) * 4u + 2u] = 0u;
        afterB[(10u * w + 55u) * 4u + 3u] = 255u;
        rgbB.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        NativeRawPresentTile alphaTile{};
        assert(!rgbB.tighten_to_rgb_bounds(source, alphaTile, realRgb));
        assert(realRgb == 0u);
        dirty.boundRight = 365;
        NativeRawSourceIslandBatch invalid{};
        assert(!invalid.append(1920, 1080, dirty, source,
                               rgbA, false, true));
    }
    // One genuine source Draw changes two separated RGB runs, while a
    // second native Draw changes a pixel INSIDE their sparse bounding box.
    // Preserve three genuine source contributions, in original coordinates,
    // without treating unchanged pixels as owned by the first Draw.
    {
        constexpr std::uint32_t w = 64u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto afterFirst = before, afterSecond = before;
        afterFirst[(9u * w + 7u) * 4u] = 71u;
        afterFirst[(9u * w + 51u) * 4u + 1u] = 61u;
        afterSecond[(9u * w + 29u) * 4u + 2u] = 91u;
        NativeRawChangedPixelWindow first{}, second{};
        first.capture(before.data(), w * 4u,
                      afterFirst.data(), w * 4u, w, h);
        second.capture(before.data(), w * 4u,
                       afterSecond.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true;
        dirty.count = 1u;
        dirty.rectangles[0] = {300, 400, 364, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 364; dirty.boundBottom = 432;
        const NativeRawPresentTile source{0u, 0u, w, h, 300, 400};
        NativeRawPresentTile enclosing{}, solid{};
        std::uint32_t pixels = 0u, denseRgb = 0u;
        assert(first.tighten_to_rgb_bounds(source, enclosing, pixels));
        assert(pixels == 2u && enclosing.copyWidth == 45u &&
               enclosing.copyHeight == 1u);
        assert(first.select_solid_rgb_tile(enclosing, solid, denseRgb));
        assert(denseRgb == 1u && solid.sourceX == 7u &&
               solid.destinationX == 307 && solid.destinationY == 409 &&
               solid.copyWidth == 1u);
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920, 1080, dirty, source, first, false, true));
        assert(batch.append(1920, 1080, dirty, source, second, true, true));
        assert(batch.append(1920, 1080, dirty, source, first, false, true));
        assert(batch.count == 3u && batch.rgbPixels[0] == 1u &&
               batch.rgbPixels[1] == 1u && batch.rgbPixels[2] == 1u &&
               batch.tiles[0].destinationX == 307 &&
               batch.tiles[1].destinationX == 329 &&
               batch.tiles[2].destinationX == 351);
        for (std::uint32_t i = 0u; i < batch.count; ++i) {
            assert(batch.tiles[i].destinationY == 409 &&
                   batch.tiles[i].copyWidth == 1u &&
                   batch.tiles[i].copyHeight == 1u);
            for (std::uint32_t j = 0u; j < i; ++j)
                assert(native_raw_disjoint_present_tiles(
                    batch.tiles[i], batch.tiles[j]));
        }
        assert(!batch.append(1920, 1080, dirty, source, first,
                             false, true));
        // Dense 2x2 source pixels remain one original-coordinate upload.
        auto wide = before;
        for (std::uint32_t y = 15u; y < 17u; ++y)
            for (std::uint32_t x = 33u; x < 35u; ++x)
                wide[(y * w + x) * 4u] = 142u;
        first.capture(before.data(), w * 4u, wide.data(), w * 4u, w, h);
        NativeRawSourceIslandBatch wideBatch{};
        assert(wideBatch.append(1920, 1080, dirty, source, first,
                                false, true));
        assert(wideBatch.count == 1u && wideBatch.rgbPixels[0] == 4u &&
               wideBatch.tiles[0].copyWidth == 2u &&
               wideBatch.tiles[0].copyHeight == 2u &&
               wideBatch.tiles[0].destinationX == 333 &&
               wideBatch.tiles[0].destinationY == 415);
        // Alpha-only Draw and forged D3D9 rcBound cannot borrow RGB proof.
        afterSecond = before;
        afterSecond[(9u * w + 29u) * 4u + 3u] = 255u;
        second.capture(before.data(), w * 4u,
                       afterSecond.data(), w * 4u, w, h);
        NativeRawPresentTile absent{};
        assert(!second.select_solid_rgb_tile(source, absent, denseRgb));
        assert(denseRgb == 0u);
        dirty.boundRight = 365;
        NativeRawSourceIslandBatch forged{};
        assert(!forged.append(1920, 1080, dirty, source,
                              first, false, true));
    }
    // A wide changed top row plus many narrower RGB rows must publish the
    // largest genuine GPU rectangle, not the first maximal horizontal run.
    // The latter misses one native row and wastes the four-island budget.
    {
        constexpr std::uint32_t w = 64u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto afterA = before, afterB = before;
        for (std::uint32_t x = 10u; x <= 20u; ++x)
            afterA[(10u * w + x) * 4u] = 111u;
        for (std::uint32_t y = 11u; y <= 17u; ++y)
            for (std::uint32_t x = 13u; x <= 17u; ++x)
                afterA[(y * w + x) * 4u + 1u] = 77u;
        afterB[(12u * w + 11u) * 4u + 2u] = 199u;
        NativeRawChangedPixelWindow a{}, b{};
        a.capture(before.data(), w * 4u, afterA.data(), w * 4u, w, h);
        b.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        const NativeRawPresentTile original{0u, 0u, w, h, 300, 400};
        NativeRawPresentTile solid{};
        std::uint32_t pixels = 0u;
        assert(a.select_solid_rgb_tile(original, solid, pixels));
        assert(pixels == 40u && solid.copyWidth == 5u &&
               solid.copyHeight == 8u && solid.sourceX == 13u &&
               solid.sourceY == 10u && solid.destinationX == 313 &&
               solid.destinationY == 410);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true;
        dirty.count = 1u;
        dirty.rectangles[0] = {300, 400, 364, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 364; dirty.boundBottom = 432;
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920, 1080, dirty, original, a, false, true));
        assert(batch.append(1920, 1080, dirty, original, b, true, true));
        assert(batch.count == 2u && batch.rgbPixels[0] == 40u &&
               batch.rgbPixels[1] == 1u &&
               batch.tiles[0].destinationX == 313 &&
               batch.tiles[1].destinationX == 311 &&
               batch.tiles[1].destinationY == 412 &&
               native_raw_disjoint_present_tiles(batch.tiles[0],
                                                 batch.tiles[1]));
        // Alpha alone is not a D3D11 RGB pixel; malformed game RGNDATA
        // must never become permission to overwrite the D3D9 Present.
        afterB = before;
        afterB[(12u * w + 11u) * 4u + 3u] = 255u;
        b.capture(before.data(), w * 4u, afterB.data(), w * 4u, w, h);
        assert(!b.select_solid_rgb_tile(original, solid, pixels));
        dirty.boundRight = 365;
        NativeRawSourceIslandBatch forged{};
        assert(!forged.append(1920, 1080, dirty, original,
                              a, false, true));
    }
    // Two separated ORIGINAL D3D9 dirty menu panels: 20 scattered real
    // native RGB pixels on the first panel compete with a dense 4x4 real
    // GPU rectangle on the second. Sparse RGB-count selection (legacy)
    // chooses the first panel and later shrinks it to just one pixel.
    // The opt-in multi-Draw path must rank the final solid GPU upload and
    // retain all 16 authentic pixels in the second original screen panel.
    {
        constexpr std::uint32_t w = 80u, h = 32u;
        std::array<std::uint8_t, w * h * 4u> before{}, after{};
        for (std::uint32_t y = 0u; y < 2u; ++y)
            for (std::uint32_t x = 0u; x < 10u; ++x)
                after[((1u + y * 3u) * w + x * 3u) * 4u] = 81u;
        for (std::uint32_t y = 10u; y < 14u; ++y)
            for (std::uint32_t x = 53u; x < 57u; ++x)
                after[(y * w + x) * 4u + 1u] = 193u;
        NativeRawChangedPixelWindow gpu{};
        gpu.capture(before.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true;
        dirty.count = 2u;
        dirty.rectangles[0] = {300, 400, 332, 432};
        dirty.rectangles[1] = {348, 400, 380, 432};
        dirty.boundLeft = 300; dirty.boundTop = 400;
        dirty.boundRight = 380; dirty.boundBottom = 432;
        const NativeRawPresentTile source{0u, 0u, w, h, 300, 400};
        NativeRawPresentTile legacy{}, dense{};
        std::uint32_t legacyRgb = 0u, denseRgb = 0u;
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, source, gpu, legacy, legacyRgb));
        assert(legacyRgb == 20u && legacy.destinationX == 300);
        assert(native_raw_dirty_source_rgb_crop(
            1920, 1080, dirty, source, gpu, dense, denseRgb,
            nullptr, 1u, true));
        assert(denseRgb == 16u && dense.sourceX == 53u &&
               dense.sourceY == 10u && dense.destinationX == 353 &&
               dense.destinationY == 410 && dense.copyWidth == 4u &&
               dense.copyHeight == 4u &&
               native_raw_dirty_region_covers_tile(
                   1920, 1080, dirty, dense));
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920, 1080, dirty, source, gpu,
                            false, true));
        assert(batch.count == 1u && batch.rgbPixels[0] == 16u &&
               batch.tiles[0].destinationX == 353);
        // The remaining sparse panel can still contribute one unscaled
        // authentic RGB pixel; it never inherits the first panel's count.
        assert(batch.append(1920, 1080, dirty, source, gpu,
                            false, true));
        assert(batch.count == 2u && batch.rgbPixels[1] == 1u &&
               batch.tiles[1].destinationX >= 300 &&
               batch.tiles[1].destinationX < 332 &&
               native_raw_disjoint_present_tiles(
                   batch.tiles[0], batch.tiles[1]));
        // Alpha-only GPU output cannot displace the dense RGB evidence.
        auto alpha = after;
        for (std::uint32_t y = 10u; y < 14u; ++y)
            for (std::uint32_t x = 53u; x < 57u; ++x) {
                alpha[(y * w + x) * 4u + 1u] = 0u;
                alpha[(y * w + x) * 4u + 3u] = 255u;
            }
        gpu.capture(before.data(), w * 4u,
                    alpha.data(), w * 4u, w, h);
        NativeRawSourceIslandBatch alphaBatch{};
        assert(alphaBatch.append(1920, 1080, dirty, source, gpu,
                                 false, true));
        assert(alphaBatch.rgbPixels[0] == 1u &&
               alphaBatch.tiles[0].destinationX < 332);
        // Neither malformed rcBound nor a repaint-gap bridging rectangle
        // is allowed to publish even a genuine native GPU pixel.
        dirty.boundRight = 381;
        NativeRawSourceIslandBatch forged{};
        assert(!forged.append(1920, 1080, dirty, source, gpu,
                              false, true));
    }
    // A single real GPU capture can contain TWO separate native RGB repaint
    // panels farther apart than the legacy 24x24 preview window. Use the
    // entire physical capture (clipped to the actual D3D9 Present crop) to
    // recover both unscaled game-source islands. No invented RGB or holes.
    {
        constexpr std::uint32_t w = 96u, h = 64u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto after = before;
        for (std::uint32_t y = 25u; y < 29u; ++y)
            for (std::uint32_t x = 20u; x < 24u; ++x)
                after[(y * w + x) * 4u] = 31u;
        for (std::uint32_t y = 35u; y < 39u; ++y)
            for (std::uint32_t x = 70u; x < 74u; ++x)
                after[(y * w + x) * 4u + 2u] = 197u;
        NativeRawChangedPixelWindow gpu{};
        gpu.capture(before.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawPresentTile preview{0u, 0u, 24u, 24u, 0, 0};
        NativeRawPresentTile selected{};
        std::uint32_t previewPixels = 0u;
        assert(gpu.select(preview, selected, previewPixels));
        assert(previewPixels == 16u); // one window cannot reach both panels

        NativeRawPresentTile source{};
        assert(native_raw_source_capture_clip_tile(
            100u, 200u, w, h, 1920u, 1080u, 1920u, 1080u,
            115, 215, 180, 256, source));
        assert(source.sourceX == 15u && source.sourceY == 15u &&
               source.copyWidth == 65u && source.copyHeight == 41u &&
               source.destinationX == 115 && source.destinationY == 215);
        NativeRawPresentDirtyRegion dirty{};
        dirty.headerVerified = true;
        dirty.count = 2u;
        dirty.rectangles[0] = {118, 221, 137, 240};
        dirty.rectangles[1] = {163, 230, 179, 253};
        dirty.boundLeft = 118; dirty.boundTop = 221;
        dirty.boundRight = 179; dirty.boundBottom = 253;
        assert(!native_raw_dirty_region_covers_tile(
            1920u, 1080u, dirty, source));
        NativeRawSourceIslandBatch batch{};
        assert(batch.append(1920u, 1080u, dirty, source,
                            gpu, false, true));
        assert(batch.append(1920u, 1080u, dirty, source,
                            gpu, false, true));
        assert(batch.count == 2u && batch.rgbPixels[0] == 16u &&
               batch.rgbPixels[1] == 16u);
        assert(batch.tiles[0].destinationX == 120 &&
               batch.tiles[0].destinationY == 225 &&
               batch.tiles[1].destinationX == 170 &&
               batch.tiles[1].destinationY == 235 &&
               batch.tiles[0].sourceX == 20u &&
               batch.tiles[1].sourceX == 70u &&
               native_raw_disjoint_present_tiles(
                   batch.tiles[0], batch.tiles[1]));
        assert(!batch.append(1920u, 1080u, dirty, source,
                             gpu, false, true));
        // A crop without intersection, mismatched canonical game target,
        // capture outside source bounds, or forged D3D9 rcBound fails closed.
        assert(!native_raw_source_capture_clip_tile(
            100u, 200u, w, h, 1280u, 720u, 1920u, 1080u,
            115, 215, 180, 256, source));
        assert(source.copyWidth == 0u);
        assert(!native_raw_source_capture_clip_tile(
            1900u, 200u, w, h, 1920u, 1080u, 1920u, 1080u,
            115, 215, 180, 256, source));
        assert(!native_raw_source_capture_clip_tile(
            100u, 200u, w, h, 1920u, 1080u, 1920u, 1080u,
            200, 215, 210, 256, source));
        assert(native_raw_source_capture_clip_tile(
            100u, 200u, w, h, 1920u, 1080u, 1920u, 1080u,
            115, 215, 180, 256, source));
        dirty.boundRight = 180;
        NativeRawSourceIslandBatch forged{};
        assert(!forged.append(1920u, 1080u, dirty, source,
                              gpu, false, true));
        // An alpha-only second panel does not count as real GPU RGB.
        dirty.boundRight = 179;
        for (std::uint32_t y = 35u; y < 39u; ++y)
            for (std::uint32_t x = 70u; x < 74u; ++x) {
                after[(y * w + x) * 4u + 2u] = 0u;
                after[(y * w + x) * 4u + 3u] = 255u;
            }
        gpu.capture(before.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawSourceIslandBatch alpha{};
        assert(alpha.append(1920u, 1080u, dirty, source,
                            gpu, false, true));
        assert(!alpha.append(1920u, 1080u, dirty, source,
                             gpu, false, true));
        assert(alpha.count == 1u && alpha.rgbPixels[0] == 16u);
    }
    // A verified FULL original game Present has no dirty RGNDATA. It must
    // still show separate real GPU RGB geometry/color islands across the
    // physical source capture, without reserving gaps as native pixels.
    {
        constexpr std::uint32_t w = 96u, h = 64u;
        std::array<std::uint8_t, w * h * 4u> before{};
        auto after = before;
        for (std::uint32_t y = 10u; y < 14u; ++y)
            for (std::uint32_t x = 10u; x < 14u; ++x)
                after[(y * w + x) * 4u] = 21u;
        for (std::uint32_t y = 20u; y < 24u; ++y)
            for (std::uint32_t x = 40u; x < 44u; ++x)
                after[(y * w + x) * 4u + 1u] = 91u;
        for (std::uint32_t y = 35u; y < 39u; ++y)
            for (std::uint32_t x = 75u; x < 79u; ++x)
                after[(y * w + x) * 4u + 2u] = 174u;
        NativeRawChangedPixelWindow rgb{};
        rgb.capture(before.data(), w * 4u, after.data(), w * 4u, w, h);
        NativeRawPresentDirtyRegion full{};
        assert(!native_raw_verified_full_source_crop_region(
            false, 1920u, 1080u, 100, 200, 300, 280, full));
        assert(!full.headerVerified && full.count == 0u);
        assert(!native_raw_verified_full_source_crop_region(
            true, 1920u, 1080u, 100, 200, 1921, 280, full));
        assert(!native_raw_verified_full_source_crop_region(
            true, 1920u, 1080u, 300, 200, 100, 280, full));
        assert(native_raw_verified_full_source_crop_region(
            true, 1920u, 1080u, 100, 200, 300, 280, full));
        NativeRawPresentTile source{};
        assert(native_raw_source_capture_clip_tile(
            105u, 205u, w, h, 1920u, 1080u, 1920u, 1080u,
            100, 200, 300, 280, source));
        NativeRawSourceIslandBatch batch{};
        for (std::uint32_t i = 0u; i < 3u; ++i)
            assert(batch.append(1920u, 1080u, full, source,
                                rgb, false, true));
        assert(!batch.append(1920u, 1080u, full, source,
                             rgb, false, true));
        assert(batch.count == 3u);
        assert(batch.tiles[0].destinationX == 115 &&
               batch.tiles[0].destinationY == 215 &&
               batch.tiles[1].destinationX == 145 &&
               batch.tiles[1].destinationY == 225 &&
               batch.tiles[2].destinationX == 180 &&
               batch.tiles[2].destinationY == 240);
        for (std::uint32_t i = 0u; i < 3u; ++i) {
            assert(batch.rgbPixels[i] == 16u);
            assert(batch.tiles[i].copyWidth == 4u &&
                   batch.tiles[i].copyHeight == 4u);
            assert(rgb.changed_pixels(batch.tiles[i]) == 16u);
        }
        // A verified partial crop is still clipped to original coordinates.
        NativeRawPresentDirtyRegion narrow{};
        assert(native_raw_verified_full_source_crop_region(
            true, 1920u, 1080u, 100, 200, 135, 225, narrow));
        NativeRawPresentTile narrowSource{};
        assert(native_raw_source_capture_clip_tile(
            105u, 205u, w, h, 1920u, 1080u, 1920u, 1080u,
            100, 200, 135, 225, narrowSource));
        NativeRawSourceIslandBatch onlyInside{};
        assert(onlyInside.append(1920u, 1080u, narrow,
                                 narrowSource, rgb, false, true));
        assert(!onlyInside.append(1920u, 1080u, narrow,
                                  narrowSource, rgb, false, true));
        assert(onlyInside.count == 1u && onlyInside.rgbPixels[0] == 16u);
        // An alpha-only Draw has no GPU RGB to present, full repaint or not.
        auto alpha = before;
        for (std::uint32_t y = 10u; y < 14u; ++y)
            for (std::uint32_t x = 10u; x < 14u; ++x)
                alpha[(y * w + x) * 4u + 3u] = 255u;
        rgb.capture(before.data(), w * 4u, alpha.data(), w * 4u, w, h);
        NativeRawSourceIslandBatch zero{};
        assert(!zero.append(1920u, 1080u, full, source,
                            rgb, false, true));
    }
    // Two authenticated GPU source byte orders yield identical displayed
    // D3D9 BGRA pixels, with XRGB opaque and ARGB alpha retained.
    const std::uint8_t nativeRgba[8]{17, 31, 241, 77, 9, 128, 255, 2};
    const std::uint8_t nativeBgra[8]{241, 31, 17, 77, 255, 128, 9, 2};
    std::uint8_t dst[8]{};
    native_raw_copy_to_d3d9_bgra(dst, nativeRgba, 2u,
                                 NativeRawColorByteOrder::Rgba, false);
    for (std::uint32_t i = 0u; i < 8u; ++i)
        assert(dst[i] == nativeBgra[i]);
    native_raw_copy_to_d3d9_bgra(dst, nativeBgra, 2u,
                                 NativeRawColorByteOrder::Bgra, true);
    for (std::uint32_t i = 0u; i < 8u; ++i)
        assert(dst[i] == (i % 4u == 3u ? 255u : nativeBgra[i]));
    native_raw_copy_to_d3d9_bgra(dst, nativeRgba, 2u,
                                 NativeRawColorByteOrder::Rgba, true);
    for (std::uint32_t i = 0u; i < 8u; ++i)
        assert(dst[i] == (i % 4u == 3u ? 255u : nativeBgra[i]));
    NativeRawDualTile t{};
    NativeRawDrawExtent fractional{};
    assert(native_raw_viewport_pixel_extent(3440, 1440,
        166.125f, 80.125f, 1.125f, 0.5f, fractional));
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        fractional, 2u, t));
    assert(t.first.x <= 167u && t.first.x + 256u >= 167u);
    assert(t.first.y <= 80u && t.first.y + 144u >= 80u);
    assert(!native_raw_viewport_pixel_extent(3440, 1440,
        3440.125f, 80.f, 1.f, 50.f, fractional));
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{0,0,3440,1440}, 0, t));
    assert(t.hasSecond);
    assert(t.first.x != t.second.x || t.first.y != t.second.y);
    assert(t.first.x + 256 <= 3440 && t.second.x + 256 <= 3440);
    assert(t.first.y + 144 <= 1440 && t.second.y + 144 <= 1440);
    assert(native_raw_source_tiles_disjoint(t.first, t.second, 256, 144));
    // Real 512x144 menu strip contains two exact disjoint GPU source
    // windows. A center-first sampler alone would falsely miss the pair.
    assert(native_raw_dual_draw_tile(512, 144, 256, 144,
        NativeRawDrawExtent{0, 0, 512, 144}, 0u, t));
    assert(t.hasSecond && t.first.x == 0u && t.second.x == 256u);
    assert(t.first.y == 0u && t.second.y == 0u);
    assert(native_raw_source_tiles_disjoint(t.first, t.second, 256, 144));
    // Regression order: evaluate two authenticated source regions before
    // the deliberate single-tile/no-overlap case changes hasSecond.
    assert(native_raw_choose_second_tile(0, 21, t.hasSecond));
    assert(!native_raw_choose_second_tile(21, 21, t.hasSecond));
    assert(!native_raw_choose_second_tile(21, 0, t.hasSecond));
    // Source-aligned Draw pixels outrank a displaced, denser legacy tile.
    // Retain the dual output only when final destinations are disjoint.
    {
        constexpr NativeRawPresentTile legacyFirst{0, 0, 64, 48, 100, 100};
        constexpr NativeRawPresentTile legacySecond{0, 0, 64, 48, 172, 100};
        constexpr NativeRawPresentTile alignedFirst{0, 0, 64, 48, 170, 100};
        constexpr NativeRawPresentTile alignedSecond{0, 0, 64, 48, 300, 100};
        static_assert(native_raw_can_show_source_aligned_pair(
            true, false, false, legacyFirst, legacySecond));
        static_assert(!native_raw_can_show_source_aligned_pair(
            true, true, false, alignedFirst, legacySecond));
        static_assert(native_raw_can_show_source_aligned_pair(
            false, true, true, alignedFirst, alignedSecond));
        // Source-coincident menu/vehicle repaint islands may clip two
        // independently completed GPU Draws to DIFFERENT sizes. The
        // previous equal-size pair predicate silently lost one draw.
        constexpr NativeRawPresentTile smallDirty{60, 20, 13, 16, 160, 220};
        constexpr NativeRawPresentTile largeDirty{51, 15, 18, 26, 356, 220};
        static_assert(native_raw_can_show_source_aligned_pair(
            false, true, true, smallDirty, largeDirty));
        static_assert(!native_raw_disjoint_equal_tiles(
            smallDirty, largeDirty));
        static_assert(!native_raw_can_show_source_aligned_pair(
            true, true, false, smallDirty, largeDirty));
        static_assert(!native_raw_can_show_source_aligned_pair(
            true, false, true, smallDirty, largeDirty));
        constexpr NativeRawPresentTile overlapDirty{51, 15, 18, 26, 165, 222};
        static_assert(!native_raw_can_show_source_aligned_pair(
            false, true, true, smallDirty, overlapDirty));
        constexpr NativeRawPresentTile emptyDirty{51, 15, 0, 26, 356, 220};
        static_assert(!native_raw_can_show_source_aligned_pair(
            false, true, true, smallDirty, emptyDirty));
        constexpr NativeRawPresentTile negativeDirty{51, 15, 18, 26, -1, 220};
        static_assert(!native_raw_can_show_source_aligned_pair(
            false, true, true, smallDirty, negativeDirty));
        static_assert(!native_raw_can_show_source_aligned_pair(
            false, true, false, alignedFirst, legacySecond));
        static_assert(native_raw_choose_source_aligned_second_tile(
            800u, 1u, false, true, true));
        static_assert(!native_raw_choose_source_aligned_second_tile(
            1u, 800u, true, false, true));
        static_assert(native_raw_choose_source_aligned_second_tile(
            1u, 800u, true, true, true));
        static_assert(!native_raw_choose_source_aligned_second_tile(
            800u, 1u, false, false, true));
        static_assert(!native_raw_choose_source_aligned_second_tile(
            1u, 800u, false, true, false));
    }
    // A narrow source raster can intersect multiple nominal tile origins,
    // but the same GPU RGB bytes must NEVER count as two native Draw tiles.
    assert(native_raw_dual_draw_tile(640, 480, 256, 144,
        NativeRawDrawExtent{100, 100, 180, 180}, 0u, t));
    assert(!t.hasSecond);
    assert(!native_raw_source_tiles_disjoint(
        NativeRawTileOrigin{0, 0}, NativeRawTileOrigin{120, 50}, 256, 144));
    assert(native_raw_source_tiles_disjoint(
        NativeRawTileOrigin{0, 0}, NativeRawTileOrigin{256, 20}, 256, 144));
    assert(!native_raw_source_tiles_disjoint(
        NativeRawTileOrigin{0, 0}, NativeRawTileOrigin{1, 1}, 0, 144));
    assert(native_raw_dual_draw_tile(256, 144, 256, 144,
        NativeRawDrawExtent{0,0,256,144}, 3, t));
    assert(!t.hasSecond && !native_raw_choose_second_tile(0, 1, t.hasSecond));
    assert(!native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{100,100,100,200}, 0, t));
    assert(!t.hasSecond);
    assert(native_raw_dual_draw_tile(3440, 1440, 256, 144,
        NativeRawDrawExtent{100,100,900,600}, 4, t));
    assert(t.hasSecond);
    // A source color fill that only overlaps the alternate GPU tile
    // must revoke the entire pair. Unknown/full writes remain fail closed.
    constexpr NativeRawSourcePixelRect onlySecond[] = {{500, 500, 650, 650}};
    constexpr NativeRawSourcePixelRect noHit[] = {{0, 0, 80, 80}};
    constexpr NativeRawSourcePixelRect onlyFirst[] = {{105, 105, 140, 140}};
    assert(native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, onlySecond, 1));
    assert(native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, onlyFirst, 1));
    assert(!native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, noHit, 1));
    assert(!native_raw_dual_source_write_overlaps(
        100, 100, false, 500, 500, 256, 144, onlySecond, 1));
    assert(native_raw_dual_source_write_overlaps(
        100, 100, true, 500, 500, 256, 144, nullptr, 0));
    assert(native_raw_dual_source_write_overlaps(
        0xffffffffu, 0, true, 500, 500, 256, 144, noHit, 1));
    // Distinct game-visible RAW regions: large desktop supports side by
    // side; narrow menus may use vertical placement; tiny crop fails closed.
    NativeRawPresentTile primary{}, secondary{};
    assert(native_raw_partial_present_tile(800, 450, 0, 0, 800, 450,
                                          256, 144, primary));
    assert(native_raw_secondary_present_tile(primary, 0, 0, 800, 450,
                                             secondary));
    assert(secondary.destinationX + secondary.copyWidth + 8 ==
           primary.destinationX);
    assert(secondary.destinationY == primary.destinationY);
    assert(native_raw_partial_present_tile(300, 440, 0, 0, 300, 440,
                                          256, 144, primary));
    assert(native_raw_secondary_present_tile(primary, 0, 0, 300, 440,
                                             secondary));
    assert(secondary.destinationX == primary.destinationX);
    assert(secondary.destinationY ==
           primary.destinationY + primary.copyHeight + 8);
    assert(native_raw_partial_present_tile(300, 185, 0, 0, 300, 185,
                                          256, 144, primary));
    assert(!native_raw_secondary_present_tile(primary, 0, 0, 300, 185,
                                              secondary));
    assert(!native_raw_secondary_present_tile(
        NativeRawPresentTile{}, 0, 0, 800, 450, secondary));
    assert(!native_raw_secondary_present_tile(
        NativeRawPresentTile{0, 0, 256, 144, -2, 8},
        0, 0, 800, 450, secondary));

    // End-to-end compact actual GPU staging + RGB-window crop path: a
    // 96x64 menu target must not be rejected by the old 256x144 minimum.
    constexpr std::uint32_t compactW = 96u, compactH = 64u;
    assert(native_raw_dual_draw_tile(compactW, compactH, compactW, compactH,
        NativeRawDrawExtent{0, 0, 96, 64}, 0u, t));
    assert(!t.hasSecond && t.first.x == 0u && t.first.y == 0u);
    NativeRawChangedPixelWindow changedWindow{};
    std::array<std::uint8_t, compactW * compactH * 4u> before{};
    auto after = before;
    after[(60u * compactW + 94u) * 4u + 0u] = 213u;
    // A restricted source crop can still select a real edge RGB pixel.
    NativeRawPresentTile compactOriginal{};
    NativeRawPresentTile compactSelected{};
    std::uint32_t realPixels = 0u;
    assert(native_raw_partial_present_tile(
        88, 58, 0, 0, 88, 58, compactW, compactH, compactOriginal));
    changedWindow.capture(before.data(), compactW * 4u,
                          after.data(), compactW * 4u, compactW, compactH);
    assert(changedWindow.select(compactOriginal, compactSelected, realPixels));
    assert(realPixels == 1u);
    // Real split 30x30 menu dirty repaint: 96x64 native GPU capture
    // now reaches the D3D9 source crop without guessed/upscaled pixels.
    NativeRawPresentDirtyRegion narrow{};
    narrow.headerVerified = true;
    narrow.count = 2u;
    narrow.rectangles[0] = {100, 120, 130, 135};
    narrow.rectangles[1] = {100, 135, 130, 150};
    narrow.boundLeft = 100; narrow.boundTop = 120;
    narrow.boundRight = 130; narrow.boundBottom = 150;
    NativeRawPresentTile tight{}, gpuCrop{};
    assert(native_raw_dirty_region_place_tile(
        1920, 1080, 0, 0, 1920, 1080, narrow,
        compactW, compactH, tight, nullptr, true));
    assert(tight.copyWidth == 24u && tight.copyHeight == 24u);
    assert(native_raw_dirty_region_covers_tile(1920, 1080, narrow, tight));
    assert(changedWindow.select(tight, gpuCrop, realPixels));
    assert(realPixels == 1u && gpuCrop.sourceX <= 94u &&
           gpuCrop.sourceX + gpuCrop.copyWidth > 94u);
    // One missing original-game dirty row never grants publication.
    narrow.rectangles[1].top = 136;
    assert(!native_raw_dirty_region_place_tile(
        1920, 1080, 0, 0, 1920, 1080, narrow,
        compactW, compactH, tight, nullptr, true));
    assert(compactSelected.sourceX <= 94u &&
           compactSelected.sourceX + compactSelected.copyWidth > 94u);
    assert(compactSelected.sourceY <= 60u &&
           compactSelected.sourceY + compactSelected.copyHeight > 60u);
    // Invalid pitch, zero dimensions or unsupported larger GPU extents
    // cannot turn stale prefix data into a visible native pixel.
    changedWindow.capture(before.data(), 3u, after.data(), compactW * 4u,
                          compactW, compactH);
    assert(!changedWindow.select(compactOriginal, compactSelected, realPixels));
    changedWindow.capture(before.data(), compactW * 4u,
                          after.data(), compactW * 4u, 257u, compactH);
    assert(!changedWindow.select(compactOriginal, compactSelected, realPixels));


    // Real source RGB panels can be much smaller than the 256x144 mapped
    // GPU copy. A D3D9 UpdateSurface only consumes this island source RECT;
    // modifying other staging bytes is wasted work and must not be required.
    // Probe both RGBA/BGRA, padded pitches, magenta incomplete borders,
    // alpha-only pixels, a second disjoint panel, and fail-closed bounds.
    {
        constexpr std::uint32_t w = 14u, h = 12u;
        constexpr std::size_t sourcePitch = w * 4u + 4u;
        constexpr std::size_t dstPitch = w * 4u + 8u;
        std::array<std::uint8_t, sourcePitch * h> before{}, after{};
        std::array<std::uint8_t, dstPitch * h> output{};
        const auto rgba = [&](std::uint32_t x, std::uint32_t y,
                              std::uint8_t r, std::uint8_t g,
                              std::uint8_t b, std::uint8_t a) {
            auto* pixel = after.data() + y * sourcePitch + x * 4u;
            pixel[0] = r; pixel[1] = g; pixel[2] = b; pixel[3] = a;
        };
        const NativeRawPresentTile panel{2u, 1u, 10u, 10u, 100, 200};
        rgba(2u, 1u, 90u, 60u, 40u, 80u); // changed REAL border pixel
        rgba(6u, 6u, 10u, 20u, 30u, 40u); // changed inner pixel
        rgba(7u, 6u, 0u, 0u, 0u, 40u); // alpha-only is NOT RGB evidence
        output.fill(0x5au);
        assert(native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, panel,
            NativeRawColorByteOrder::Rgba, false));
        const auto pixel = [&](std::uint32_t x, std::uint32_t y) {
            return output.data() + y * dstPitch + x * 4u;
        };
        assert(pixel(2u, 1u)[0] == 40u &&
               pixel(2u, 1u)[1] == 60u &&
               pixel(2u, 1u)[2] == 90u &&
               pixel(2u, 1u)[3] == 80u);
        assert(pixel(6u, 6u)[0] == 30u &&
               pixel(6u, 6u)[1] == 20u &&
               pixel(6u, 6u)[2] == 10u &&
               pixel(6u, 6u)[3] == 40u);
        assert(pixel(3u, 2u)[0] == 255u &&
               pixel(3u, 2u)[1] == 0u &&
               pixel(3u, 2u)[2] == 255u); // incomplete border
        assert(pixel(7u, 6u)[0] == 0u &&
               pixel(7u, 6u)[1] == 0u &&
               pixel(7u, 6u)[2] == 0u &&
               pixel(7u, 6u)[3] == 40u);
        assert(pixel(0u, 0u)[0] == 0x5au &&
               pixel(13u, 11u)[0] == 0x5au);
        // Another independent source-aligned panel on the same D3D9
        // staging buffer must not change the first/other-pixel receipts.
        rgba(12u, 10u, 51u, 52u, 53u, 54u);
        const NativeRawPresentTile other{12u, 10u, 2u, 2u, 400, 200};
        assert(native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, other,
            NativeRawColorByteOrder::Bgra, true));
        assert(pixel(12u, 10u)[0] == 51u &&
               pixel(12u, 10u)[1] == 52u &&
               pixel(12u, 10u)[2] == 53u &&
               pixel(12u, 10u)[3] == 255u);
        assert(pixel(6u, 6u)[0] == 30u &&
               pixel(6u, 6u)[2] == 10u);
        // Incomplete or invalid native source extents cannot stage even
        // one pixel, and no destination byte is touched on failure.
        const auto priorOutput = output;
        NativeRawPresentTile invalid = other;
        invalid.copyWidth = 3u; // extends beyond GPU readback
        assert(!native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, invalid,
            NativeRawColorByteOrder::Bgra, false));
        assert(!native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), 8u,
            after.data(), sourcePitch, w, h, other,
            NativeRawColorByteOrder::Bgra, false));
        assert(!native_raw_copy_present_island(
            output.data(), dstPitch, before.data(), sourcePitch,
            after.data(), sourcePitch, w, h, NativeRawPresentTile{},
            NativeRawColorByteOrder::Bgra, false));
        assert(output == priorOutput);
    }

}
