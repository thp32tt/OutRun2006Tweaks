#include "../src/vr/d3d11/native_game_raw_fvf_stroke_sampling.hpp"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <limits>
using namespace outrun::vr::dx11;
struct Vertex { float clip[4]; float user[6]; };
constexpr std::size_t userOffset = offsetof(Vertex, user);
int main() {
    // Source-authentic two distant menu/HUD native line Draws: GPU captures
    // must visit their actual strokes, not the empty merged AABB center.
    Vertex lines[] {
        {{-0.90f,-0.72f,0.5f,1.f},{1,1,1,1,1,1}},
        {{-0.45f,-0.72f,0.5f,1.f},{1,1,1,1,1,1}},
        {{ 0.45f, 0.72f,0.5f,1.f},{1,1,1,1,1,1}},
        {{ 0.90f, 0.72f,0.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan line{
        lines,sizeof(Vertex),4u,nullptr,0u,
        NativeRawFvfAssembly::LineList,userOffset,0u};
    NativeRawDrawExtent boundsA{}, boundsB{};
    NativeRawDualTile captureA{}, captureB{};
    constexpr NativeRawDrawExtent full{0,0,3440,1440};
    assert(native_raw_fvf_stroke_dual_draw_tile(
        line,0,0,3440,1440,3440,1440,400,200,
        full,0u,boundsA,captureA));
    assert(native_raw_fvf_stroke_dual_draw_tile(
        line,0,0,3440,1440,3440,1440,400,200,
        full,1u,boundsB,captureB));
    assert(boundsA.left < 350 && boundsA.right > 3000);
    assert(boundsA.top < 230 && boundsA.bottom > 1200);
    assert(boundsA.left==boundsB.left && boundsA.right==boundsB.right);
    assert(captureA.first.x < 1500 && captureB.first.x > 1900);
    assert(captureA.first.y > 850 && captureB.first.y < 500);
    assert(captureA.hasSecond &&
           native_raw_source_tiles_disjoint(
               captureA.first,captureA.second,400,200));

    // Source scissor excludes the second line entirely. No hidden primitive
    // may become native GPU evidence, even though its bounding box exists.
    NativeRawDrawExtent scissored{};
    NativeRawDualTile scissorTiles{};
    assert(native_raw_fvf_stroke_dual_draw_tile(
        line,0,0,3440,1440,3440,1440,400,200,
        {0,700,1720,1440},3u,scissored,scissorTiles));
    assert(scissored.right <= 1720 && scissored.top >= 700 &&
           scissorTiles.first.x < 1500);

    // REAL source user ClipDistance clips the first line at x=midpoint.
    // A NaN in any enabled plane or malformed mask rejects the hint.
    line.clipDistanceMask=1u;
    lines[0].user[0]=-1.f;
    NativeRawDrawExtent clipped{};
    NativeRawDualTile clippedTiles{};
    assert(native_raw_fvf_stroke_dual_draw_tile(
        line,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));
    assert(clipped.left > boundsA.left);
    lines[0].user[0]=std::numeric_limits<float>::quiet_NaN();
    assert(!native_raw_fvf_stroke_dual_draw_tile(
        line,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));
    lines[0].user[0]=1.f;
    line.clipDistanceMask=0x40u;
    assert(!native_raw_fvf_stroke_dual_draw_tile(
        line,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));

    // Connected LINESTRIP keeps each true segment and the alternating
    // capture origins, including source-authentic indexed IA.
    const std::uint32_t indices[]{0u,1u,2u,3u};
    NativeRawFvfClipSpan strip{
        lines,sizeof(Vertex),4u,indices,4u,
        NativeRawFvfAssembly::LineStrip,userOffset,0u};
    assert(native_raw_fvf_stroke_dual_draw_tile(
        strip,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));
    assert(clipped.right>3000 && clipped.left<350);
    const std::uint32_t invalidIndices[]{0u,1u,2u,5u};
    strip.indices=invalidIndices;
    assert(!native_raw_fvf_stroke_dual_draw_tile(
        strip,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));
    strip.indices=indices;
    // Source WVP clip-space lines can cross the camera eye at W=0 or
    // negative W. Retain their real visible clipped segment for native
    // GPU PRE/POST sampling, as the corresponding FVF polygon path does.
    lines[1].clip[3]=0.f;
    assert(native_raw_fvf_stroke_dual_draw_tile(
        strip,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));
    assert(clipped.right > clipped.left && clipped.bottom > clipped.top);
    lines[1].clip[3]=-0.5f;
    assert(native_raw_fvf_stroke_dual_draw_tile(
        strip,0,0,3440,1440,3440,1440,400,200,
        full,1u,clipped,clippedTiles));
    // A zero clip-space vector is not a valid source intersection.
    lines[1].clip[0]=0.f;
    lines[1].clip[1]=0.f;
    lines[1].clip[2]=0.f;
    lines[1].clip[3]=0.f;
    assert(!native_raw_fvf_stroke_dual_draw_tile(
        strip,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));
    assert(clipped.left==0 && clipped.right==0 && !clippedTiles.hasSecond);
    lines[1]={{-0.45f,-0.72f,0.5f,1.f},{1,1,1,1,1,1}};

    // LINELIST's entire IA must be even-sized: a dangling or malformed
    // final index is not a safe native source even if earlier lines draw.
    const std::uint32_t oddIndices[]{0u,1u,99u};
    NativeRawFvfClipSpan oddList{
        lines,sizeof(Vertex),4u,oddIndices,3u,
        NativeRawFvfAssembly::LineList,userOffset,0u};
    assert(!native_raw_fvf_stroke_dual_draw_tile(
        oddList,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));
    oddList.indices=nullptr;
    oddList.indexCount=0u;
    oddList.count=3u;
    assert(!native_raw_fvf_stroke_dual_draw_tile(
        oddList,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));

    // Pointlist captures only valid point pixels; a bound outside clip
    // space is not treated as a large imaginary FVF triangle.
    Vertex points[]{
        {{-0.8f,0.8f,0.5f,1.f},{1,1,1,1,1,1}},
        {{ 0.8f,-0.8f,0.5f,1.f},{1,1,1,1,1,1}},
        {{ 3.0f,0.f,0.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan point{
        points,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::PointList,userOffset,0u};
    assert(native_raw_fvf_stroke_dual_draw_tile(
        point,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));
    assert(clipped.left < 400 && clipped.right > 3000);
    assert(clippedTiles.hasSecond &&
           native_raw_source_tiles_disjoint(
               clippedTiles.first,clippedTiles.second,400,200));
    // Native D3D11 DepthClipEnable=FALSE only ignores Z, NEVER XY/W.
    points[0].clip[2]=2.f;
    points[1].clip[2]=2.f;
    assert(!native_raw_fvf_stroke_dual_draw_tile(
        point,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles));
    NativeRawFvfRaster noZClip{};
    noZClip.depthClipEnable=false;
    assert(native_raw_fvf_stroke_dual_draw_tile(
        point,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles,&noZClip));
    points[0].clip[3]=0.f;
    assert(!native_raw_fvf_stroke_dual_draw_tile(
        point,0,0,3440,1440,3440,1440,400,200,
        full,0u,clipped,clippedTiles,&noZClip));
}
