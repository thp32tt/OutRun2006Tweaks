#include "../src/vr/d3d11/native_game_raw_fvf_clip_capture.hpp"
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
    // Keep existing safety boundary: do not infer native RGB from
    // authentic W=0 source vertices even if a projected area seems plausible.
    Vertex eye[]{
        {{0.f,0.f,0.f,0.f},{1,1,1,1,1,1}},
        {{0.5f,-0.5f,0.5f,1.f},{1,1,1,1,1,1}},
        {{-0.5f,-0.5f,0.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan nearEye{eye,sizeof(Vertex),3u};
    assert(!native_raw_fvf_projected_raster(nearEye,0,0,100,100,xy));
}
