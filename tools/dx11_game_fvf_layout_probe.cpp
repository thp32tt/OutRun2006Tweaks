#include "../src/vr/d3d11/live_game_fvf_layout.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    GameFvfLayout layout{};
    const auto original = layout;
    assert(!game_fvf_layout(kGameFvfXyz | kGameFvfTex3 | 0x900u, layout));
    assert(layout.minStride == original.minStride);
    assert(!game_fvf_layout(kGameFvfXyz, layout));
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfXyz | kGameFvfTex1, layout));
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfNormal | kGameFvfTex1, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex1, layout));
    assert(layout.pretransformed && layout.textured && !layout.hasDiffuse);
    assert(layout.positionBytes == 16 && layout.texcoordOffset == 16 && layout.minStride == 24);
    struct RhwUv { float x, y, z, rhw, u, v; } rhwUv{11,22,0.5f,2,0.25f,0.75f};
    GameFvfSample sample{};
    assert(game_fvf_decode_vertex(&rhwUv, sizeof(rhwUv), layout, sample));
    assert(sample.position[3] == 2.f && sample.diffuse == 0xffffffffu);
    assert(sample.uv[0] == 0.25f && sample.uv[1] == 0.75f);
    const auto before = sample;
    assert(!game_fvf_decode_vertex(&rhwUv, 23, layout, sample));
    assert(sample.uv[1] == before.uv[1] && sample.diffuse == before.diffuse);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfTex1, layout));
    assert(!layout.pretransformed && !layout.hasDiffuse && layout.minStride == 20);
    struct XyzUv { float x,y,z,u,v; } xyzUv{1,2,3,.4f,.8f};
    assert(game_fvf_decode_vertex(&xyzUv, sizeof(xyzUv), layout, sample));
    assert(sample.position[3] == 1.f && sample.uv[0] == .4f);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfDiffuse | kGameFvfTex1, layout));
    assert(layout.texcoordOffset == 20 && layout.minStride == 28 && layout.hasDiffuse);
    struct ColoredRhwUv {float x,y,z,rhw; std::uint32_t color; float u,v;};
    ColoredRhwUv colored{1,2,3,1,0xaabbccdd,.2f,.6f};
    assert(game_fvf_decode_vertex(&colored, sizeof(colored), layout, sample));
    assert(sample.diffuse == 0xaabbccddu && sample.uv[0] == .2f);
    // TEX2: the live stage 0 can source either UV set from real vertex bytes.
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex2, layout));
    assert(layout.texcoordCount == 2u && layout.minStride == 32u);
    struct RhwUv2 {float x,y,z,rhw,u0,v0,u1,v1;};
    RhwUv2 twice{1,2,.4f,1,.1f,.2f,.7f,.8f};
    assert(game_fvf_decode_vertex(&twice, sizeof(twice), layout, sample));
    float chosen[2] = {-1.f, -1.f};
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .7f && chosen[1] == .8f);
    assert(game_fvf_select_uv(sample, layout, 0u, chosen));
    assert(chosen[0] == .1f && chosen[1] == .2f);
    const auto safe = sample;
    assert(!game_fvf_decode_vertex(&twice, 31u, layout, sample));
    assert(sample.uv1[0] == safe.uv1[0]);
    assert(!game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .1f && chosen[1] == .2f);
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex3 | 0x400u, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex2 | 0x00020000u, layout));
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfDiffuse | kGameFvfTex2, layout));
    assert(layout.texcoordOffset == 16u && layout.minStride == 32u);
    struct XyzColorUv2 {float x,y,z; std::uint32_t color; float u0,v0,u1,v1;};
    XyzColorUv2 color2{1,2,3,0xff010203u,.1f,.2f,.3f,.4f};
    assert(game_fvf_decode_vertex(&color2, sizeof(color2), layout, sample));
    assert(sample.diffuse == 0xff010203u && sample.uv1[0] == .3f);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfTex1, layout));
    assert(!game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .1f);
    // Game-authored TEX3 stage-0 can select UV2 for native D3D11 sampling.
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex3, layout));
    assert(layout.texcoordCount == 3u && layout.minStride == 40u);
    struct RhwUv3 {float x,y,z,rhw,u0,v0,u1,v1,u2,v2;};
    RhwUv3 three{10,20,.5f,1,.1f,.2f,.3f,.4f,.7f,.9f};
    assert(game_fvf_decode_vertex(&three, sizeof(three), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .7f && chosen[1] == .9f);
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .3f && chosen[1] == .4f);
    assert(game_fvf_select_uv(sample, layout, 0u, chosen));
    assert(chosen[0] == .1f && chosen[1] == .2f);
    const auto thirdGood = sample;
    assert(!game_fvf_decode_vertex(&three, 39u, layout, sample));
    assert(sample.uv2[0] == thirdGood.uv2[0]);
    assert(!game_fvf_select_uv(sample, layout, 3u, chosen));
    assert(chosen[0] == .1f);
    assert(!game_fvf_layout(kGameFvfXyzRhw | 0x900u, layout));
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex3 | 0x20000u, layout));
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfDiffuse | kGameFvfTex3, layout));
    assert(layout.texcoordOffset == 16u && layout.minStride == 40u);
    struct XyzColorUv3 {float x,y,z; std::uint32_t color; float u0,v0,u1,v1,u2,v2;};
    XyzColorUv3 color3{1,2,3,0xff102030u,.1f,.2f,.3f,.4f,.5f,.6f};
    assert(game_fvf_decode_vertex(&color3, sizeof(color3), layout, sample));
    assert(sample.diffuse == 0xff102030u && sample.uv2[0] == .5f);
    assert(game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .5f && chosen[1] == .6f);
    // TEX4 live-game FVF: decode UV3 and route indexed stage0 3.
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex4, layout));
    assert(layout.texcoordCount == 4u && layout.minStride == 48u);
    struct RhwUv4 {float x,y,z,rhw,u0,v0,u1,v1,u2,v2,u3,v3;};
    RhwUv4 four{10,20,.5f,1,.1f,.2f,.3f,.4f,.5f,.6f,.75f,.95f};
    assert(game_fvf_decode_vertex(&four, sizeof(four), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 3u, chosen));
    assert(chosen[0] == .75f && chosen[1] == .95f);
    assert(game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .5f && chosen[1] == .6f);
    const auto fourthGood = sample;
    assert(!game_fvf_decode_vertex(&four, 47u, layout, sample));
    assert(sample.uv3[0] == fourthGood.uv3[0]);
    assert(!game_fvf_select_uv(sample, layout, 4u, chosen));
    assert(chosen[0] == .5f && chosen[1] == .6f);
    assert(!game_fvf_layout(kGameFvfXyzRhw | 0x900u, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex4 | 0x00020000u, layout));
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfDiffuse | kGameFvfTex4, layout));
    assert(layout.texcoordOffset == 16u && layout.minStride == 48u);
    struct XyzColorUv4 {float x,y,z; std::uint32_t color; float u0,v0,u1,v1,u2,v2,u3,v3;};
    XyzColorUv4 color4{1,2,3,0xff102030u,.1f,.2f,.3f,.4f,.5f,.6f,.7f,.8f};
    assert(game_fvf_decode_vertex(&color4, sizeof(color4), layout, sample));
    assert(sample.diffuse == 0xff102030u && sample.uv3[0] == .7f);
    assert(game_fvf_select_uv(sample, layout, 3u, chosen));
    assert(chosen[0] == .7f && chosen[1] == .8f);

    // Live D3D9 TEX5..TEX8 is used by the same native Draw/DrawIndexed path.
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex8, layout));
    assert(layout.texcoordCount == 8u && layout.minStride == 80u);
    struct RhwUv8 {float x,y,z,rhw; float uv[8][2];};
    RhwUv8 eight{10,20,.5f,1,
        {{.1f,.2f},{.2f,.3f},{.3f,.4f},{.4f,.5f},
         {.5f,.6f},{.6f,.7f},{.7f,.8f},{.85f,.95f}}};
    assert(sizeof(eight) == 80u);
    assert(game_fvf_decode_vertex(&eight, sizeof(eight), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 4u, chosen));
    assert(chosen[0] == .5f && chosen[1] == .6f);
    assert(game_fvf_select_uv(sample, layout, 5u, chosen));
    assert(chosen[0] == .6f && chosen[1] == .7f);
    assert(game_fvf_select_uv(sample, layout, 6u, chosen));
    assert(chosen[0] == .7f && chosen[1] == .8f);
    assert(game_fvf_select_uv(sample, layout, 7u, chosen));
    assert(chosen[0] == .85f && chosen[1] == .95f);
    const auto eightSaved = sample;
    assert(!game_fvf_decode_vertex(&eight, 79u, layout, sample));
    assert(sample.uv7[1] == eightSaved.uv7[1]);
    assert(!game_fvf_select_uv(sample, layout, 8u, chosen));
    assert(chosen[0] == .85f && chosen[1] == .95f);
    auto badEight = layout;
    badEight.texcoordOffset -= 8u;
    assert(!game_fvf_decode_vertex(&eight, sizeof(eight), badEight, sample));
    assert(sample.uv7[1] == eightSaved.uv7[1]);
    assert(!game_fvf_layout(kGameFvfXyzRhw | 0x900u, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex8 | 0x00010000u, layout));
    assert(layout.texcoord3DMask == 1u && layout.minStride == 84u);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfNormal |
                           kGameFvfDiffuse | kGameFvfSpecular | kGameFvfTex5, layout));
    assert(layout.texcoordCount == 5u && layout.texcoordOffset == 32u &&
           layout.minStride == 72u);
    struct WorldUv5 {
        float x,y,z,nx,ny,nz; std::uint32_t diffuse,specular; float uv[5][2];
    };
    WorldUv5 world5{1,2,3,0,1,0,0xff010203u,0xff040506u,
                    {{.1f,.2f},{.2f,.3f},{.3f,.4f},{.4f,.5f},{.55f,.65f}}};
    assert(sizeof(world5) == 72u);
    assert(game_fvf_decode_vertex(&world5, sizeof(world5), layout, sample));
    assert(sample.diffuse == 0xff010203u);
    assert(game_fvf_select_uv(sample, layout, 4u, chosen));
    assert(chosen[0] == .55f && chosen[1] == .65f);
    assert(!game_fvf_select_uv(sample, layout, 5u, chosen));
    // OutRun object-space world FVF: NORMAL before DIFFUSE/SPECULAR/TEX2.
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfNormal |
                           kGameFvfDiffuse | kGameFvfSpecular | kGameFvfTex2, layout));
    assert(layout.hasNormal && layout.hasSpecular && layout.hasDiffuse);
    assert(layout.normalBytes == 12u && layout.diffuseOffset == 24u);
    assert(layout.texcoordOffset == 32u && layout.minStride == 48u);
    struct WorldNormalSpecUv2 {
        float x,y,z,nx,ny,nz; std::uint32_t diffuse,specular;
        float u0,v0,u1,v1;
    };
    WorldNormalSpecUv2 world{1,2,3,0,0,1,0xff123456u,0xffabcdefu,.1f,.2f,.6f,.8f};
    assert(sizeof(world) == 48u);
    assert(game_fvf_decode_vertex(&world, sizeof(world), layout, sample));
    assert(sample.position[2] == 3.f && sample.diffuse == 0xff123456u);
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .6f && chosen[1] == .8f);
    const auto safeWorld = sample;
    assert(!game_fvf_decode_vertex(&world, 47u, layout, sample));
    assert(sample.diffuse == safeWorld.diffuse && sample.uv1[1] == safeWorld.uv1[1]);
    auto corrupted = layout;
    corrupted.diffuseOffset -= 12u;
    assert(!game_fvf_decode_vertex(&world, sizeof(world), corrupted, sample));
    assert(sample.diffuse == safeWorld.diffuse);
    corrupted = layout;
    corrupted.texcoordOffset -= 4u;
    assert(!game_fvf_decode_vertex(&world, sizeof(world), corrupted, sample));
    assert(sample.uv1[1] == safeWorld.uv1[1]);
    assert(!game_fvf_select_uv(sample, layout, 2u, chosen));
    // No diffuse: texture-only mode must skip SPECULAR and select the true UV.
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfNormal |
                           kGameFvfSpecular | kGameFvfTex1, layout));
    assert(!layout.hasDiffuse && layout.hasSpecular);
    assert(layout.diffuseOffset == 24u && layout.texcoordOffset == 28u);
    assert(layout.minStride == 36u);
    struct WorldSpecUv {float x,y,z,nx,ny,nz; std::uint32_t spec; float u,v;};
    WorldSpecUv texturedWorld{1,2,3,0,1,0,0x12345678u,.2f,.9f};
    assert(game_fvf_decode_vertex(&texturedWorld, sizeof(texturedWorld), layout, sample));
    assert(sample.diffuse == 0xffffffffu);
    assert(game_fvf_select_uv(sample, layout, 0u, chosen));
    assert(chosen[0] == .2f && chosen[1] == .9f);
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfNormal |
                            kGameFvfSpecular | kGameFvfTex1, layout));
    // PSIZE occupies one float after NORMAL and before vertex COLOR/UV.
    // This is the live game's diagnostic Draw/DrawIndexed FVF decoder.
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfNormal | kGameFvfPsize |
                           kGameFvfDiffuse | kGameFvfSpecular | kGameFvfTex2, layout));
    assert(layout.hasPointSize && layout.pointSizeBytes == 4u);
    assert(layout.normalBytes == 12u && layout.diffuseOffset == 28u);
    assert(layout.texcoordOffset == 36u && layout.minStride == 52u);
    struct WorldPoint {
        float x,y,z,nx,ny,nz,pointSize;
        std::uint32_t diffuse,specular;
        float u0,v0,u1,v1;
    } worldPoint{1,2,3,0,0,1,10.f,0xff223344u,0xff556677u,.125f,.25f,.875f,.75f};
    assert(sizeof(worldPoint) == 52u);
    assert(game_fvf_decode_vertex(&worldPoint, sizeof(worldPoint), layout, sample));
    assert(sample.position[2] == 3.f && sample.diffuse == 0xff223344u);
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .875f && chosen[1] == .75f);
    const auto savedPoint = sample;
    assert(!game_fvf_decode_vertex(&worldPoint, 51u, layout, sample));
    assert(sample.diffuse == savedPoint.diffuse && sample.uv1[1] == savedPoint.uv1[1]);
    auto invalidPoint = layout;
    invalidPoint.pointSizeBytes = 0u;
    assert(!game_fvf_decode_vertex(&worldPoint, sizeof(worldPoint), invalidPoint, sample));
    invalidPoint = layout;
    invalidPoint.diffuseOffset -= 4u;
    assert(!game_fvf_decode_vertex(&worldPoint, sizeof(worldPoint), invalidPoint, sample));
    // XYZRHW menu draw with per-vertex point size must read COLOR/TEX1 correctly.
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfPsize |
                           kGameFvfDiffuse | kGameFvfTex1, layout));
    assert(layout.diffuseOffset == 20u && layout.texcoordOffset == 24u &&
           layout.minStride == 32u);
    struct MenuPoint { float x,y,z,rhw,pointSize; std::uint32_t diffuse; float u,v; }
    menuPoint{11,22,.5f,1.f,32.f,0xff112233u,.375f,.625f};
    assert(sizeof(menuPoint) == 32u);
    assert(game_fvf_decode_vertex(&menuPoint, sizeof(menuPoint), layout, sample));
    assert(sample.diffuse == 0xff112233u && sample.uv[0] == .375f);
    assert(!game_fvf_decode_vertex(&menuPoint, 31u, layout, sample));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfPsize | kGameFvfTex1, layout));
    assert(!layout.hasDiffuse && layout.texcoordOffset == 20u && layout.minStride == 28u);
    struct MenuPointUv { float x,y,z,rhw,pointSize,u,v; }
    menuOnly{1,2,.4f,1.f,5.f,.2f,.8f};
    assert(game_fvf_decode_vertex(&menuOnly, sizeof(menuOnly), layout, sample));
    assert(sample.diffuse == 0xffffffffu && sample.uv[0] == .2f);
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfNormal |
                            kGameFvfPsize | kGameFvfTex1, layout));
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfPsize | kGameFvfTex1 |
                           0x00010000u, layout));
    assert(layout.texcoord3DMask == 1u && layout.minStride == 28u);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfDiffuse, layout));
    assert(!layout.hasPointSize && layout.pointSizeBytes == 0u);
    assert(!layout.textured && layout.minStride == 16);

    // 00610: one-dimensional D3D9 stage0 UV feeds native Draw/DrawIndexed.
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex1 | 0x00010000u, layout));
    assert(layout.texcoord3DMask == 1u && layout.minStride == 28u);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex1 | 0x00020000u, layout));
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTexcoordSize1_0 | kGameFvfDiffuse, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex1 | kGameFvfTexcoordSize1_0, layout));
    assert(layout.firstTexcoord1D && layout.texcoordCount == 1u && layout.minStride == 20u);
    struct MenuOneDim {float x,y,z,rhw,u;} menuOneDim{10,20,.5f,1.f,.625f};
    assert(sizeof(menuOneDim) == 20u);
    assert(game_fvf_decode_vertex(&menuOneDim, sizeof(menuOneDim), layout, sample));
    assert(sample.uv[0] == .625f && sample.uv[1] == 0.f);
    const auto menuSaved = sample;
    assert(!game_fvf_decode_vertex(&menuOneDim, 19u, layout, sample));
    assert(sample.uv[0] == menuSaved.uv[0] && sample.uv[1] == menuSaved.uv[1]);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfDiffuse |
                           kGameFvfTex2 | kGameFvfTexcoordSize1_0, layout));
    assert(layout.firstTexcoord1D && layout.texcoordOffset == 20u && layout.minStride == 32u);
    struct VehicleUv1Uv2 {float x,y,z,rhw; std::uint32_t diffuse; float u0,u1,v1;};
    VehicleUv1Uv2 vehicleUv{1,2,.4f,1.f,0xff112233u,.125f,.75f,.875f};
    assert(sizeof(vehicleUv) == 32u);
    assert(game_fvf_decode_vertex(&vehicleUv, sizeof(vehicleUv), layout, sample));
    assert(sample.diffuse == 0xff112233u);
    assert(game_fvf_select_uv(sample, layout, 0u, chosen));
    assert(chosen[0] == .125f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .75f && chosen[1] == .875f);
    const auto vehicleSaved = sample;
    assert(!game_fvf_decode_vertex(&vehicleUv, 31u, layout, sample));
    assert(sample.uv1[1] == vehicleSaved.uv1[1]);
    auto corruptDimension = layout;
    corruptDimension.firstTexcoord1D = false;
    assert(!game_fvf_decode_vertex(&vehicleUv, sizeof(vehicleUv), corruptDimension, sample));
    assert(sample.uv1[1] == vehicleSaved.uv1[1]);
    // 00611: game-authored UV1 U-only feeds TEXCOORDINDEX=1 native Draw.
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex1 |
                            kGameFvfTexcoordSize1_1, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex2 | 0x00040000u, layout));
    assert(layout.texcoord3DMask == 2u && layout.minStride == 36u);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex2 | 0x00080000u, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex2 |
                           kGameFvfTexcoordSize1_1, layout));
    assert(!layout.firstTexcoord1D && layout.secondTexcoord1D);
    assert(layout.minStride == 28u);
    struct VehicleSecondU {float x,y,z,rhw,u0,v0,u1;};
    VehicleSecondU vehicleSecond{1,2,.4f,1.f,.125f,.25f,.875f};
    assert(sizeof(vehicleSecond) == 28u);
    assert(game_fvf_decode_vertex(&vehicleSecond, sizeof(vehicleSecond), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .875f && chosen[1] == 0.f);
    const auto secondSaved = sample;
    assert(!game_fvf_decode_vertex(&vehicleSecond, 27u, layout, sample));
    assert(sample.uv1[0] == secondSaved.uv1[0]);
    auto badSecond = layout;
    badSecond.secondTexcoord1D = false;
    assert(!game_fvf_decode_vertex(&vehicleSecond, sizeof(vehicleSecond), badSecond, sample));
    assert(sample.uv1[0] == secondSaved.uv1[0]);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfNormal | kGameFvfDiffuse |
                           kGameFvfTex3 | kGameFvfTexcoordSize1_0 |
                           kGameFvfTexcoordSize1_1, layout));
    assert(layout.firstTexcoord1D && layout.secondTexcoord1D);
    assert(layout.texcoordOffset == 28u && layout.minStride == 44u);
    struct RaceMixedUV {float x,y,z,nx,ny,nz;std::uint32_t color;float u0,u1,u2,v2;};
    RaceMixedUV raceMixed{1,2,3,0,0,1,0xff123456u,.2f,.4f,.6f,.8f};
    assert(sizeof(raceMixed) == 44u);
    assert(game_fvf_decode_vertex(&raceMixed, sizeof(raceMixed), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 0u, chosen));
    assert(chosen[0] == .2f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .4f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .6f && chosen[1] == .8f);
    const auto raceSaved = sample;
    assert(!game_fvf_decode_vertex(&raceMixed, 43u, layout, sample));
    assert(sample.uv2[0] == raceSaved.uv2[0]);
    // 00612: TEX3 UV2 U-only must reach the game-authored native stage0 UV.
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex2 |
                            kGameFvfTexcoordSize1_2, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex3 | 0x00100000u, layout));
    assert(layout.texcoord3DMask == 4u && layout.minStride == 44u);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex3 | 0x00200000u, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex3 |
                           kGameFvfTexcoordSize1_2, layout));
    assert(layout.thirdTexcoord1D && layout.minStride == 36u);
    struct VehicleThirdU {float x,y,z,rhw,u0,v0,u1,v1,u2;};
    VehicleThirdU vehicleThird{1,2,.4f,1.f,.1f,.2f,.3f,.4f,.875f};
    assert(sizeof(vehicleThird) == 36u);
    assert(game_fvf_decode_vertex(&vehicleThird, sizeof(vehicleThird), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .875f && chosen[1] == 0.f);
    const auto goodThird = sample;
    assert(!game_fvf_decode_vertex(&vehicleThird, 35u, layout, sample));
    assert(sample.uv2[0] == goodThird.uv2[0]);
    auto corruptThird = layout;
    corruptThird.thirdTexcoord1D = false;
    assert(!game_fvf_decode_vertex(&vehicleThird, sizeof(vehicleThird), corruptThird, sample));
    assert(sample.uv2[0] == goodThird.uv2[0]);
    // TEX4: three U-only coordinates followed by a full UV3 float2.
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfNormal | kGameFvfDiffuse |
                           kGameFvfTex4 | kGameFvfTexcoordSize1_0 |
                           kGameFvfTexcoordSize1_1 | kGameFvfTexcoordSize1_2, layout));
    assert(layout.firstTexcoord1D && layout.secondTexcoord1D && layout.thirdTexcoord1D);
    assert(layout.texcoordOffset == 28u && layout.minStride == 48u);
    struct RaceThirdPacked {float x,y,z,nx,ny,nz; std::uint32_t color;
                            float u0,u1,u2,u3,v3;};
    RaceThirdPacked raceThird{1,2,3,0,1,0,0xffaabbccu,.1f,.2f,.3f,.8f,.9f};
    assert(sizeof(raceThird) == 48u);
    assert(game_fvf_decode_vertex(&raceThird, sizeof(raceThird), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 0u, chosen));
    assert(chosen[0] == .1f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .2f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .3f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 3u, chosen));
    assert(chosen[0] == .8f && chosen[1] == .9f);
    const auto goodRaceThird = sample;
    assert(!game_fvf_decode_vertex(&raceThird, 47u, layout, sample));
    assert(sample.uv3[1] == goodRaceThird.uv3[1]);
    corruptThird = layout;
    corruptThird.texcoordCount = 2u;
    assert(!game_fvf_decode_vertex(&raceThird, sizeof(raceThird), corruptThird, sample));
    // 00612 retry: game-authored TEXCOORDSIZE1(3) is a packed fourth U-only
    // slot, and its missing V must not consume the fifth UV pair.
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex3 |
                            kGameFvfTexcoordSize1_3, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex4 | 0x00400000u, layout));
    assert(layout.texcoord3DMask == 8u && layout.minStride == 52u);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex4 | 0x00800000u, layout));
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex4 |
                           kGameFvfTexcoordSize1_3, layout));
    assert(layout.fourthTexcoord1D && layout.minStride == 44u);
    struct VehicleFourthU { float x,y,z,rhw,u0,v0,u1,v1,u2,v2,u3; };
    VehicleFourthU vehicleFourth{1,2,.4f,1.f,.1f,.2f,.3f,.4f,.5f,.6f,.875f};
    assert(sizeof(vehicleFourth) == 44u);
    assert(game_fvf_decode_vertex(&vehicleFourth, sizeof(vehicleFourth), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 3u, chosen));
    assert(chosen[0] == .875f && chosen[1] == 0.f);
    const auto goodFourth = sample;
    assert(!game_fvf_decode_vertex(&vehicleFourth, 43u, layout, sample));
    assert(sample.uv3[0] == goodFourth.uv3[0]);
    auto corruptFourth = layout;
    corruptFourth.fourthTexcoord1D = false;
    assert(!game_fvf_decode_vertex(&vehicleFourth, sizeof(vehicleFourth), corruptFourth, sample));
    assert(sample.uv3[0] == goodFourth.uv3[0]);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex4 |
                           kGameFvfTexcoordSize1_0 | kGameFvfTexcoordSize1_1 |
                           kGameFvfTexcoordSize1_2 | kGameFvfTexcoordSize1_3, layout));
    assert(layout.minStride == 32u);
    struct MenuFourPackedU { float x,y,z,rhw,u0,u1,u2,u3; };
    MenuFourPackedU menuFour{1,2,.4f,1.f,.1f,.2f,.3f,.75f};
    assert(sizeof(menuFour) == 32u);
    assert(game_fvf_decode_vertex(&menuFour, sizeof(menuFour), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 3u, chosen));
    assert(chosen[0] == .75f && chosen[1] == 0.f);
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfNormal | kGameFvfDiffuse |
                           kGameFvfTex5 | kGameFvfTexcoordSize1_3, layout));
    assert(layout.texcoordOffset == 28u && layout.minStride == 64u);
    struct RaceFourthPacked { float x,y,z,nx,ny,nz; std::uint32_t color;
                              float u0,v0,u1,v1,u2,v2,u3,u4,v4; };
    RaceFourthPacked raceFourth{1,2,3,0,1,0,0xffaabbccu,
                               .1f,.2f,.3f,.4f,.5f,.6f,.7f,.8f,.9f};
    assert(sizeof(raceFourth) == 64u);
    assert(game_fvf_decode_vertex(&raceFourth, sizeof(raceFourth), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 3u, chosen));
    assert(chosen[0] == .7f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 4u, chosen));
    assert(chosen[0] == .8f && chosen[1] == .9f);
    assert(!game_fvf_decode_vertex(&raceFourth, 63u, layout, sample));
    assert(sample.uv4[1] == .9f);

    // 00613: MENU / VEHICLE / RACE game FVF TEX5..8 tail slots are
    // packed U-only. The live capture coordIndex can select all eight UVs.
    for (std::uint32_t slot = 4u; slot < 8u; ++slot) {
        const std::uint32_t sizeFlag = kGameFvfTexcoordSize1_4 << (2u * (slot - 4u));
        const std::uint32_t texCount = (slot + 1u) << 8u;
        assert(!game_fvf_layout(kGameFvfXyzRhw | (texCount - kGameFvfTex1) |
                                sizeFlag, layout));
        assert(!game_fvf_layout(kGameFvfXyzRhw | texCount |
                                (sizeFlag & ~(1u << (16u + 2u * slot))), layout));
        assert(game_fvf_layout(kGameFvfXyzRhw | texCount | sizeFlag, layout));
        assert(layout.minStride == 16u + 8u * (slot + 1u) - 4u);
    }
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex8 |
                           kGameFvfTexcoordSize1_4 | kGameFvfTexcoordSize1_5 |
                           kGameFvfTexcoordSize1_6 | kGameFvfTexcoordSize1_7, layout));
    assert(layout.minStride == 64u);
    struct MenuTailPackedU { float x,y,z,rhw, u0,v0,u1,v1,u2,v2,u3,v3, u4,u5,u6,u7; };
    MenuTailPackedU menuTail{1,2,.4f,1.f,.1f,.2f,.3f,.4f,.5f,.6f,.7f,.8f,
                             .41f,.52f,.63f,.74f};
    assert(sizeof(menuTail) == 64u);
    assert(game_fvf_decode_vertex(&menuTail, sizeof(menuTail), layout, sample));
    for (std::uint32_t slot = 4u; slot < 8u; ++slot) {
        assert(game_fvf_select_uv(sample, layout, slot, chosen));
        assert(chosen[1] == 0.f);
    }
    assert(game_fvf_select_uv(sample, layout, 7u, chosen));
    assert(chosen[0] == .74f && chosen[1] == 0.f);
    const auto goodTail = sample;
    assert(!game_fvf_decode_vertex(&menuTail, 63u, layout, sample));
    assert(sample.uv7[0] == goodTail.uv7[0]);
    auto corruptTail = layout;
    corruptTail.eighthTexcoord1D = false;
    assert(!game_fvf_decode_vertex(&menuTail, sizeof(menuTail), corruptTail, sample));
    assert(sample.uv7[0] == goodTail.uv7[0]);

    // U-only stage4 must not shift later stage5..7 float2, including the
    // actually selected stage7 UV. Normal/diffuse bytes precede UV capture.
    assert(game_fvf_layout(kGameFvfXyz | kGameFvfNormal | kGameFvfDiffuse |
                           kGameFvfTex8 | kGameFvfTexcoordSize1_4, layout));
    assert(layout.minStride == 28u + 8u * 8u - 4u);
    struct RaceTailMixed { float x,y,z,nx,ny,nz; std::uint32_t color;
                           float u0,v0,u1,v1,u2,v2,u3,v3,u4,u5,v5,u6,v6,u7,v7; };
    RaceTailMixed raceTail{1,2,3,0,1,0,0xffaabbccu,.1f,.2f,.3f,.4f,.5f,.6f,
                           .7f,.8f,.9f,.15f,.25f,.35f,.45f,.85f,.95f};
    assert(sizeof(raceTail) == 88u);
    assert(game_fvf_decode_vertex(&raceTail, sizeof(raceTail), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 4u, chosen));
    assert(chosen[0] == .9f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 7u, chosen));
    assert(chosen[0] == .85f && chosen[1] == .95f);
    assert(!game_fvf_decode_vertex(&raceTail, 87u, layout, sample));
    assert(sample.uv7[1] == .95f);
    // 00614: real menu/vehicle/race FVF float3 UV captures must advance
    // each subsequent slot by 12 source bytes, not the native float2 8.
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex3 |
                           kGameFvfTexcoordSize3_0, layout));
    assert(layout.texcoord3DMask == 1u && layout.minStride == 44u);
    struct Menu3DUv { float x,y,z,rhw,u0,v0,w0,u1,v1,u2,v2; };
    Menu3DUv menu3D{1,2,.4f,1.f,.1f,.2f,777.f,.3f,.4f,.85f,.95f};
    assert(sizeof(menu3D) == 44u);
    assert(game_fvf_decode_vertex(&menu3D, sizeof(menu3D), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 0u, chosen));
    assert(chosen[0] == .1f && chosen[1] == .2f);
    assert(game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .85f && chosen[1] == .95f);
    const auto valid3D = sample;
    assert(!game_fvf_decode_vertex(&menu3D, 43u, layout, sample));
    assert(sample.uv2[1] == valid3D.uv2[1]);
    auto corrupted3D = layout;
    corrupted3D.texcoord3DMask = 0u;
    assert(!game_fvf_decode_vertex(&menu3D, sizeof(menu3D), corrupted3D, sample));
    assert(sample.uv2[0] == valid3D.uv2[0]);

    // Mixed packed stage4 U-only + stage7 float3 with live TEXCOORDINDEX=7.
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex8 |
                           kGameFvfTexcoordSize1_4 | kGameFvfTexcoordSize3_7, layout));
    assert(layout.texcoord3DMask == 0x80u && layout.minStride == 80u);
    struct Race3DMixed { float x,y,z,rhw,u0,v0,u1,v1,u2,v2,u3,v3,
                               u4,u5,v5,u6,v6,u7,v7,w7; };
    Race3DMixed race3D{1,2,.4f,1.f,.1f,.2f,.3f,.4f,.5f,.6f,.7f,.8f,
                       .9f,.15f,.25f,.35f,.45f,.85f,.95f,888.f};
    assert(sizeof(race3D) == 80u);
    assert(game_fvf_decode_vertex(&race3D, sizeof(race3D), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 4u, chosen));
    assert(chosen[0] == .9f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 7u, chosen));
    assert(chosen[0] == .85f && chosen[1] == .95f);
    assert(!game_fvf_decode_vertex(&race3D, 79u, layout, sample));
    assert(sample.uv7[1] == .95f);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex8 | 0x80000000u, layout));
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex7 |
                            kGameFvfTexcoordSize3_7, layout));
    // 00615: game-authored 4D FVF UV source skips both extra floats.
    assert(kGameFvfTexcoordSize4_0 == 0x00020000u);
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex3 |
                           kGameFvfTexcoordSize4_0 |
                           kGameFvfTexcoordSize1_1 |
                           0x00200000u, layout));
    assert(layout.texcoord4DMask == 0x05u && layout.minStride == 52u);
    struct Race4DPacked { float x,y,z,rhw,u0,v0,z0,q0,u1,u2,v2,z2,q2; };
    Race4DPacked race4D{1,2,.5f,1.f,.125f,.25f,700.f,900.f,
                        .75f,.875f,.9375f,333.f,444.f};
    assert(sizeof(race4D) == 52u);
    assert(game_fvf_decode_vertex(&race4D, sizeof(race4D), layout, sample));
    assert(game_fvf_select_uv(sample, layout, 0u, chosen));
    assert(chosen[0] == .125f && chosen[1] == .25f);
    assert(game_fvf_select_uv(sample, layout, 1u, chosen));
    assert(chosen[0] == .75f && chosen[1] == 0.f);
    assert(game_fvf_select_uv(sample, layout, 2u, chosen));
    assert(chosen[0] == .875f && chosen[1] == .9375f);
    const auto saved4D = sample;
    assert(!game_fvf_decode_vertex(&race4D, 51u, layout, sample));
    assert(sample.uv2[1] == saved4D.uv2[1]);
    auto corrupted4D = layout;
    corrupted4D.texcoord4DMask = 0u;
    assert(!game_fvf_decode_vertex(&race4D, sizeof(race4D), corrupted4D, sample));
    corrupted4D = layout;
    corrupted4D.texcoord3DMask = corrupted4D.texcoord4DMask;
    assert(!game_fvf_decode_vertex(&race4D, sizeof(race4D), corrupted4D, sample));
    assert(!game_fvf_layout(kGameFvfXyzRhw | kGameFvfTex2 |
                            kGameFvfTexcoordSize4_7, layout));
    return 0;
}
