#include "../src/vr/d3d11/native_game_raw_fvf_clip_capture.hpp"
#include "../src/vr/d3d11/native_game_raw_fvf_island_sampling.hpp"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <limits>
using namespace outrun::vr::dx11;
struct Vertex { float clip[4]; float user[6]; };
constexpr auto offset = offsetof(Vertex,user);
int main() {
    Vertex tri[]{
        {{-0.8f,-0.8f,0.5f,1.f},{-0.8f,-0.8f,1,1,1,1}},
        {{ 0.8f,-0.8f,0.5f,1.f},{ 0.8f,-0.8f,1,1,1,1}},
        {{ 0.0f, 0.8f,0.5f,1.f},{ 0.0f, 0.8f,1,1,1,1}}
    };
    NativeRawFvfClipSpan span{tri,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    NativeRawDrawExtent all{},xOnly{},xy{};
    assert(native_raw_fvf_projected_raster(span,0,0,100,100,all));
    assert(all.left<20 && all.top<20 && all.right>80 && all.bottom>80);
    span.clipDistanceMask=1u;
    assert(native_raw_fvf_projected_raster(span,0,0,100,100,xOnly));
    assert(xOnly.left>=47 && xOnly.right==all.right &&
           xOnly.bottom==all.bottom);
    span.clipDistanceMask=3u;
    assert(native_raw_fvf_projected_raster(span,0,0,100,100,xy));
    assert(xy.left>=xOnly.left && xy.bottom<=53);
    // Positive and negative source-clip/unknown-plane cases.
    tri[0].user[1]=std::numeric_limits<float>::quiet_NaN();
    span.clipDistanceMask=1u;
    assert(native_raw_fvf_projected_raster(span,0,0,100,100,xOnly));
    span.clipDistanceMask=3u;
    assert(!native_raw_fvf_projected_raster(span,0,0,100,100,xy));
    tri[0].user[1]=-0.8f;
    span.clipDistanceMask=0x40u;
    assert(!native_raw_fvf_projected_raster(span,0,0,100,100,xy));
    span.clipDistanceMask=1u;
    span.clipDistanceOffset=sizeof(Vertex)-sizeof(float)*5u;
    assert(!native_raw_fvf_projected_raster(span,0,0,100,100,xy));
    span.clipDistanceOffset=offset;
    for(auto& v:tri) v.user[0]=-1.f;
    assert(!native_raw_fvf_projected_raster(span,0,0,100,100,xy));
    // Indexed source only uses real DrawIndexed vertices, not unused VB.
    Vertex vb[]{tri[0],tri[1],tri[2],tri[0]};
    for(auto& v:vb) v.user[0]=1.f;
    vb[3].clip[0]=99.f;
    const std::uint32_t ib[]{0u,1u,2u};
    NativeRawFvfClipSpan idx{vb,sizeof(Vertex),4u,ib,3u,
        NativeRawFvfAssembly::TriangleList,offset,1u};
    assert(native_raw_fvf_projected_raster(idx,0,0,100,100,xy));
    assert(xy.right==all.right);
    // An all-zero homogeneous vector is projectively undefined and must
    // remain fail-closed even when nearby vertices would survive clipping.
    Vertex eye[]{
        {{0.f,0.f,0.f,0.f},{1,1,1,1,1,1}},
        {{0.5f,-0.5f,0.5f,1.f},{1,1,1,1,1,1}},
        {{-0.5f,-0.5f,0.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan nearEye{eye,sizeof(Vertex),3u};
    assert(!native_raw_fvf_projected_raster(nearEye,0,0,100,100,xy));
    // A genuine world-space D3D9 WVP triangle may intersect the camera at
    // finite, nonzero XYZ/W=0. The native clipped point/triangle GPU Draw
    // must guide its own PRE/POST sampling rather than reverting to an
    // unrelated viewport. This is sampling placement, NOT a fabricated RGB.
    eye[0]={{-0.5f,-0.5f,0.5f,0.f},{1,1,1,1,1,1}};
    NativeRawFvfInteriorSample nearEyeInterior{};
    assert(native_raw_fvf_projected_raster(
        nearEye,0,0,100,100,xy,nullptr,nullptr,&nearEyeInterior));
    assert(xy.right>xy.left && xy.bottom>xy.top);
    assert(nearEyeInterior.pixelX>=xy.left &&
           nearEyeInterior.pixelX<xy.right &&
           nearEyeInterior.pixelY>=xy.top &&
           nearEyeInterior.pixelY<xy.bottom);
    // Nonzero eye crossings are still subject to the real GPU scissor,
    // source ClipDistance and homogeneous depth plane.
    // ClipDistance0 belongs to Vertex::user, not the leading clip[4].
    // Without this source-authentic offset the negative regression reads
    // a clip-space X coordinate and falsely treats it as a user plane.
    nearEye.clipDistanceOffset=offset;
    nearEye.clipDistanceMask=1u;
    assert(native_raw_fvf_projected_raster(nearEye,0,0,100,100,xy));
    for (auto& v:eye) v.user[0]=-1.f;
    assert(!native_raw_fvf_projected_raster(nearEye,0,0,100,100,xy));
    for (auto& v:eye) v.user[0]=1.f;
    nearEye.clipDistanceMask=0u;
    // Point/line IA can never be certified by a triangle-fan polygon.
    // Their geometry must be routed to the native stroke capture helper.
    nearEye.assembly=NativeRawFvfAssembly::LineStrip;
    assert(!native_raw_fvf_projected_raster(nearEye,0,0,100,100,xy));
    nearEye.assembly=NativeRawFvfAssembly::PointList;
    assert(!native_raw_fvf_projected_raster(nearEye,0,0,100,100,xy));
    nearEye.assembly=NativeRawFvfAssembly::TriangleList;
    const std::uint32_t trailing[]{0u,1u,2u,0u};
    nearEye.indices=trailing;
    nearEye.indexCount=4u;
    assert(!native_raw_fvf_projected_raster(nearEye,0,0,100,100,xy));
    nearEye.indices=nullptr;
    nearEye.indexCount=0u;
    assert(native_raw_fvf_projected_raster(nearEye,0,0,100,100,xy));
    // A real FVF D3DFILL_WIREFRAME Draw colors edge fragments, not the
    // interior of its source-authentic clipped triangle. Verify that
    // bound D3D11 wire RS directs the same native PRE/POST GPU copies to
    // those actual line footprints without modifying solid Draws.
    Vertex wire[]{
        {{-0.95f,-0.72f,0.5f,1.f},{-0.95f,1,1,1,1,1}},
        {{ 0.90f,-0.55f,0.5f,1.f},{ 0.90f,1,1,1,1,1}},
        {{-0.30f, 0.86f,0.5f,1.f},{-0.30f,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan wireSource{
        wire,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,1u};
    NativeRawFvfRaster solidRs{NativeRawFvfCull::None,false,true,false};
    NativeRawFvfRaster wireRs{NativeRawFvfCull::None,false,true,true};
    NativeRawFvfInteriorSample solidAnchor{},edgeAnchor{};
    NativeRawDrawExtent solidRaster{},wireRaster{};
    assert(native_raw_fvf_projected_raster(
        wireSource,0,0,3440,1440,solidRaster,nullptr,
        &solidRs,&solidAnchor));
    assert(native_raw_fvf_projected_raster(
        wireSource,0,0,3440,1440,wireRaster,nullptr,
        &wireRs,&edgeAnchor));
    assert(solidRaster.left==wireRaster.left &&
           solidRaster.right==wireRaster.right &&
           solidRaster.top==wireRaster.top &&
           solidRaster.bottom==wireRaster.bottom);
    assert(edgeAnchor.sparseDiagonal &&
           (edgeAnchor.pixelX != solidAnchor.pixelX ||
            edgeAnchor.pixelY != solidAnchor.pixelY));
    NativeRawDualTile gpuWire{};
    assert(native_raw_fvf_island_dual_draw_tile(
        wireSource,0,0,3440,1440,3440,1440,512,288,
        {0,0,3440,1440},0u,gpuWire,&wireRs));
    assert(edgeAnchor.pixelX >= gpuWire.first.x &&
           edgeAnchor.pixelX < gpuWire.first.x+512 &&
           edgeAnchor.pixelY >= gpuWire.first.y &&
           edgeAnchor.pixelY < gpuWire.first.y+288 &&
           (!gpuWire.hasSecond ||
            native_raw_source_tiles_disjoint(
                gpuWire.first,gpuWire.second,512,288)));
    // Source user-plane clipping also constrains wireframe edge locations.
    // Bad clip-plane masks/nonfinite inputs and W=0 remain fail closed.
    wireSource.clipDistanceMask=3u;
    assert(native_raw_fvf_projected_raster(
        wireSource,0,0,3440,1440,wireRaster,nullptr,&wireRs));
    wire[0].user[1]=std::numeric_limits<float>::quiet_NaN();
    assert(!native_raw_fvf_projected_raster(
        wireSource,0,0,3440,1440,wireRaster,nullptr,&wireRs));
    wire[0].user[1]=1.f;
    wireSource.clipDistanceMask=0x40u;
    assert(!native_raw_fvf_projected_raster(
        wireSource,0,0,3440,1440,wireRaster,nullptr,&wireRs));
    wireSource.clipDistanceMask=1u;
    wire[1].clip[0]=0.f;
    wire[1].clip[1]=0.f;
    wire[1].clip[2]=0.f;
    wire[1].clip[3]=0.f; // all-zero remains malformed, unlike W=0/XYZ!=0
    assert(!native_raw_fvf_island_dual_draw_tile(
        wireSource,0,0,3440,1440,3440,1440,512,288,
        {0,0,3440,1440},0u,gpuWire,&wireRs));
}
