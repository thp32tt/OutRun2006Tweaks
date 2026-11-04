#include "../src/vr/d3d11/native_game_fvf_clipped_draw.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
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

    // 01230: actual menu/car/race FVF source Draw ordinals stay contiguous
    // when ALL of their genuine indexed or linear IA primitives are clipped.
    // Native GPU RAW sampling must also retain its PRE/POST slot for the
    // next visible real Draw, with no fabricated skipped fragments.
    Vertex offscreen[] {
        {{-4.f,-0.8f,0.5f,1.f},{1,1,1,1,1,1}},
        {{-3.f,-0.2f,0.5f,1.f},{1,1,1,1,1,1}},
        {{-2.f, 0.7f,0.5f,1.f},{1,1,1,1,1,1}},
        {{ 2.f,-0.8f,0.5f,1.f},{1,1,1,1,1,1}},
        {{ 3.f,-0.2f,0.5f,1.f},{1,1,1,1,1,1}},
        {{ 4.f, 0.7f,0.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan hidden{
        offscreen,sizeof(Vertex),6u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    assert(native_game_fvf_fully_clipped_draw(hidden));
    NativeRawDrawExtent hiddenRaster{};
    assert(!native_raw_fvf_projected_raster(
        hidden,0,0,100,100,hiddenRaster));
    // A crossing triangle has corners outside opposite planes, but clips
    // to visible screen pixels and may write game Z/stencil/color.
    offscreen[1].clip[0]=3.f;
    assert(!native_game_fvf_fully_clipped_draw(hidden));
    offscreen[1].clip[0]=-3.f;
    const std::uint32_t onlyHidden[]{0u,1u,2u,3u,4u,5u};
    hidden.indices=onlyHidden;
    hidden.indexCount=6u;
    assert(native_game_fvf_fully_clipped_draw(hidden));
    const std::uint32_t invalidLate[]{0u,1u,2u,3u,4u,9u};
    hidden.indices=invalidLate;
    assert(!native_game_fvf_fully_clipped_draw(hidden));
    const std::uint32_t dangling[]{0u,1u,2u,3u};
    hidden.indices=dangling;
    hidden.indexCount=4u;
    assert(!native_game_fvf_fully_clipped_draw(hidden));
    hidden.indices=nullptr; hidden.indexCount=0u;
    // A wholly clipped TriangleStrip and TriangleFan use their complete
    // original topology, not an assumed list of independent triangles.
    hidden.count=3u;
    hidden.assembly=NativeRawFvfAssembly::TriangleFan;
    assert(native_game_fvf_fully_clipped_draw(hidden));
    hidden.assembly=NativeRawFvfAssembly::TriangleStrip;
    assert(native_game_fvf_fully_clipped_draw(hidden));
    hidden.assembly=NativeRawFvfAssembly::LineStrip;
    assert(native_game_fvf_fully_clipped_draw(hidden));
    hidden.assembly=NativeRawFvfAssembly::LineList;
    assert(!native_game_fvf_fully_clipped_draw(hidden)); // dangling line
    hidden.assembly=NativeRawFvfAssembly::PointList;
    assert(native_game_fvf_fully_clipped_draw(hidden));
    // Source W=0 eye crossing with real XYZ is not automatically empty;
    // an invalid all-zero homogeneous vector cannot certify either outcome.
    hidden.assembly=NativeRawFvfAssembly::TriangleList;
    offscreen[1].clip[0]=0.f;
    offscreen[1].clip[3]=0.f;
    assert(!native_game_fvf_fully_clipped_draw(hidden));
    offscreen[1].clip[1]=0.f; offscreen[1].clip[2]=0.f;
    assert(!native_game_fvf_fully_clipped_draw(hidden));
    offscreen[1]={{-3.f,-0.2f,0.5f,1.f},{1,1,1,1,1,1}};
    // Exact enabled source ClipDistance can alone prove exclusion; missing
    // or nonfinite active plane payload never becomes a no-op certificate.
    for (auto& v:offscreen) v.clip[0]=0.f;
    for (unsigned i=0;i<3u;++i) offscreen[i].user[0]=-1.f;
    hidden.clipDistanceMask=1u;
    assert(native_game_fvf_fully_clipped_draw(hidden));
    offscreen[0].user[0]=0.f;
    assert(!native_game_fvf_fully_clipped_draw(hidden));
    offscreen[0].user[0]=std::numeric_limits<float>::quiet_NaN();
    assert(!native_game_fvf_fully_clipped_draw(hidden));
    hidden.clipDistanceMask=0x40u;
    assert(!native_game_fvf_fully_clipped_draw(hidden));
    // D3D11 DepthClipEnable=FALSE never cancels XY clipping.
    hidden.clipDistanceMask=0u;
    for (unsigned i=0;i<3u;++i) {
        offscreen[i].clip[0]=0.f;
        offscreen[i].clip[2]=2.f;
    }
    assert(native_game_fvf_fully_clipped_draw(hidden));
    assert(!native_game_fvf_fully_clipped_draw(hidden,false));
    // A positive but extremely small homogeneous W must NOT be replaced
    // by the sampling helper's epsilon eye-plane approximation. Even tiny
    // genuine rasterizable triangles require their real D3D9/D3D11 Draw.
    for (unsigned i=0;i<3u;++i) {
        offscreen[i].clip[0]=0.f;
        offscreen[i].clip[1]=0.f;
        offscreen[i].clip[2]=0.0000001f;
        offscreen[i].clip[3]=0.0000002f;
    }
    assert(!native_game_fvf_fully_clipped_draw(hidden));
    // 01231: Native D3D11 menu scissor can exclude every real source
    // triangle even when all homogeneous XY/Z planes still admit it.
    // Preserve its exact Draw ordinal without Z/cull/color GPU mutations.
    Vertex scissorVertices[]{
        {{-0.8f,-0.5f,0.5f,1.f},{1,1,1,1,1,1}},
        {{-0.4f, 0.6f,0.5f,1.f},{1,1,1,1,1,1}},
        {{-0.6f,-0.7f,0.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan scissorSource{
        scissorVertices,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    const NativeRawFvfScissorClip rightViewport{
        0.0,0.0,100.0,100.0,60,0,95,100};
    assert(!native_game_fvf_fully_clipped_draw(scissorSource));
    assert(native_game_fvf_fully_clipped_draw(
        scissorSource,true,&rightViewport));
    // Crossing either scissor edge must keep the REAL native GPU Draw.
    scissorVertices[1].clip[0]=0.6f;
    assert(!native_game_fvf_fully_clipped_draw(
        scissorSource,true,&rightViewport));
    scissorVertices[1].clip[0]=-0.4f;
    const NativeRawFvfScissorClip invalidViewport{
        0.0,0.0,0.0,100.0,60,0,95,100};
    assert(!native_game_fvf_fully_clipped_draw(
        scissorSource,true,&invalidViewport));
    const NativeRawFvfScissorClip invertedScissor{
        0.0,0.0,100.0,100.0,95,0,60,100};
    assert(!native_game_fvf_fully_clipped_draw(
        scissorSource,true,&invertedScissor));
    scissorSource.clipDistanceMask=1u;
    scissorVertices[2].user[0]=std::numeric_limits<float>::quiet_NaN();
    assert(!native_game_fvf_fully_clipped_draw(
        scissorSource,true,&rightViewport));
    // 01233: scissor bounds are pixel sample edges, not geometric line
    // centrelines. A real one-pixel line or wireframe triangle just outside
    // x=60 can still produce a covered scissored sample. Never consume
    // such an original D3D9 Draw as a pixel-neutral native frame ordinal.
    Vertex edgeStrokes[]{
        {{0.190f,-0.2f,0.5f,1.f},{1,1,1,1,1,1}},
        {{0.194f, 0.2f,0.5f,1.f},{1,1,1,1,1,1}},
        {{0.198f, 0.6f,0.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan edgeSource{
        edgeStrokes,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::LineStrip,offset,0u};
    const NativeRawFvfScissorClip edgeScissor{
        0.0,0.0,100.0,100.0,60,0,100,100};
    assert(!native_game_fvf_fully_clipped_draw(
        edgeSource,true,&edgeScissor));
    edgeSource.assembly=NativeRawFvfAssembly::TriangleList;
    assert(!native_game_fvf_fully_clipped_draw(
        edgeSource,true,&edgeScissor)); // native wireframe edges
    const std::uint32_t edgeIb[]{2u,0u,1u};
    edgeSource.indices=edgeIb;
    edgeSource.indexCount=3u;
    assert(!native_game_fvf_fully_clipped_draw(
        edgeSource,true,&edgeScissor)); // real DrawIndexed
    // A truly distant source stroke still qualifies as a no-pixel
    // ordinal; the expanded proof must not disable valid optimization.
    for (auto& v:edgeStrokes) v.clip[0]=-0.5f;
    assert(native_game_fvf_fully_clipped_draw(
        edgeSource,true,&edgeScissor));
    edgeSource.assembly=NativeRawFvfAssembly::LineStrip;
    assert(native_game_fvf_fully_clipped_draw(
        edgeSource,true,&edgeScissor));
    // The guard only widens raster/scissor proof, never an authenticated
    // user ClipDistance plane: active clipping remains source-authoritative.
    for (auto& v:edgeStrokes) { v.clip[0]=0.19f; v.user[0]=-1.f; }
    edgeSource.clipDistanceMask=1u;
    assert(native_game_fvf_fully_clipped_draw(
        edgeSource,true,&edgeScissor));
    edgeSource.clipDistanceMask=0u;
    assert(!native_game_fvf_fully_clipped_draw(edgeSource));
    // Bad native viewport mapping must never become an empty certificate.
    const NativeRawFvfScissorClip badEdgeScissor{
        0.0,0.0,0.0,100.0,60,0,100,100};
    assert(!native_game_fvf_fully_clipped_draw(
        edgeSource,true,&badEdgeScissor));
    edgeSource.indices=nullptr;
    edgeSource.indexCount=0u;

    // 01236: original SOLID FVF source triangles with EXACT coincident
    // homogeneous screen corners cannot write any native color, depth or
    // stencil pixel. Accept all original indexed/list/strip/fan IA ordinals,
    // but never apply the proof to wireframe, point-filled, W=0, boundary,
    // malformed indices or a merely thin (nonzero-area) game triangle.
    Vertex collapsed[]{
        {{-.4f,-.6f,.2f,1.f},{1,1,1,1,1,1}},
        {{-.4f,-.6f,.8f,1.f},{1,1,1,1,1,1}},
        {{ .6f, .4f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.4f,-.6f,.2f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan collapsedSource{
        collapsed,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    NativeRawFvfRaster solidNoCull{
        NativeRawFvfCull::None,false,true,false};
    NativeRawFvfRaster wireNoCull{
        NativeRawFvfCull::None,false,true,true};
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull)); // no implicit admission
    assert(native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true));
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&wireNoCull,true));
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,false)); // point-filled
    // 01237: an original D3D9 WVP projects equal XY/W even when the
    // duplicated screen corner has DIFFERENT homogeneous W, source Z and
    // shader UVs. Recognize exact projective equality, not merely copied
    // XYZ/W payloads. A different Y/W or an almost-equal X/W is real GPU
    // geometry and must retain its original native Draw.
    collapsed[1].clip[0]=-.8f;
    collapsed[1].clip[1]=-1.2f;
    collapsed[1].clip[3]=2.f;
    assert(native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true));
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&wireNoCull,true));
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,false));
    collapsed[1].clip[1]=-.6f;
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true));
    collapsed[1].clip[1]=-1.2f;
    collapsed[1].clip[0]=-.7999999f;
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true));
    collapsed[1].clip[3]=1.f;
    collapsed[1].clip[1]=-.6f;
    collapsed[1].clip[0]=-.399f;
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true)); // thin real pixels
    collapsed[1].clip[0]=-.4f;
    collapsed[1].clip[3]=0.f;
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true)); // camera crossing
    collapsed[1].clip[3]=1.f;
    collapsed[2].clip[0]=1.f; // clip-plane contact: normal Draw
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true));
    collapsed[2].clip[0]=.6f;
    collapsedSource.count=4u;
    collapsedSource.assembly=NativeRawFvfAssembly::TriangleStrip;
    assert(native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true));
    collapsedSource.assembly=NativeRawFvfAssembly::TriangleFan;
    assert(native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true));
    collapsedSource.assembly=NativeRawFvfAssembly::TriangleList;
    const std::uint32_t collapsedIndices[]{0u,1u,2u,0u,2u,3u};
    collapsedSource.indices=collapsedIndices;
    collapsedSource.indexCount=6u;
    assert(native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true));
    const std::uint32_t corruptCollapsed[]{0u,1u,2u,0u,2u,99u};
    collapsedSource.indices=corruptCollapsed;
    assert(!native_game_fvf_fully_clipped_draw(
        collapsedSource,true,nullptr,&solidNoCull,true));
    collapsedSource.indices=nullptr;
    collapsedSource.indexCount=0u;

    // 01238: three DIFFERENT source vertices may collapse to an exact
    // vertical or horizontal line after homogeneous W division. Keep these
    // successful, strictly interior solid Draw ordinals contiguous without
    // inventing a native GPU color/Z/stencil write; a real wireframe Draw
    // must still be sampled from its GPU line edges.
    Vertex axisCollapsed[]{
        {{.25f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{.5f,.5f,1.f,2.f},{1,1,1,1,1,1}},
        {{1.f,2.f,2.f,4.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan axisSource{
        axisCollapsed,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    assert(native_game_fvf_fully_clipped_draw(
        axisSource,true,nullptr,&solidNoCull,true));
    assert(!native_game_fvf_fully_clipped_draw(
        axisSource,true,nullptr,&wireNoCull,true));
    assert(!native_game_fvf_fully_clipped_draw(
        axisSource,true,nullptr,&solidNoCull,false));
    NativeRawDrawExtent axisRaster{};
    NativeRawFvfInteriorSample axisStroke{};
    assert(!native_raw_fvf_projected_raster(
        axisSource,0,0,3440,1440,axisRaster,nullptr,&solidNoCull));
    assert(native_raw_fvf_projected_raster(
        axisSource,0,0,3440,1440,axisRaster,nullptr,&wireNoCull,
        &axisStroke));
    assert(axisStroke.sparseDiagonal &&
           axisStroke.pixelX >= axisRaster.left &&
           axisStroke.pixelX < axisRaster.right &&
           axisStroke.pixelY >= axisRaster.top &&
           axisStroke.pixelY < axisRaster.bottom);
    // One actual float ULP of horizontal separation means a nonzero-area
    // source triangle. Neither the solid no-op proof nor a tolerance-based
    // projected-axis comparison may discard this menu/road geometry.
    axisCollapsed[2].clip[0]=1.00000011920928955078125f;
    assert(!native_game_fvf_fully_clipped_draw(
        axisSource,true,nullptr,&solidNoCull,true));
    axisCollapsed[2].clip[0]=1.f;
    // Horizontal collapsed source, including an original indexed Draw.
    for (unsigned c=0;c<3u;++c) {
        const float w=axisCollapsed[c].clip[3];
        const float x=axisCollapsed[c].clip[1];
        axisCollapsed[c].clip[0]=x;
        axisCollapsed[c].clip[1]=.25f*w;
    }
    const std::uint32_t axisIndices[]{0u,1u,2u};
    axisSource.indices=axisIndices;
    axisSource.indexCount=3u;
    assert(native_game_fvf_fully_clipped_draw(
        axisSource,true,nullptr,&solidNoCull,true));
    assert(!native_game_fvf_fully_clipped_draw(
        axisSource,true,nullptr,&wireNoCull,true));
    // Clip-boundary or invalid eye-plane source must never acquire an
    // empty certificate from homogeneous axis alignment alone.
    axisCollapsed[2].clip[0]=4.f;
    assert(!native_game_fvf_fully_clipped_draw(
        axisSource,true,nullptr,&solidNoCull,true));
    axisCollapsed[2].clip[0]=2.f;
    axisCollapsed[2].clip[3]=0.f;
    assert(!native_game_fvf_fully_clipped_draw(
        axisSource,true,nullptr,&solidNoCull,true));
    live_game_frame::GameNativeFrameBatch collapsedBatch{};
    assert(collapsedBatch.absorb_empty_source_draw(0u,true));
    assert(collapsedBatch.absorb_empty_source_draw(1u,true));
    assert(collapsedBatch.accepts_full(2u));
    assert(collapsedBatch.accepts_source_draw(2u,true));
    collapsedBatch.succeeded(false,false);
    collapsedBatch.record_source_draw(2u);
    assert(collapsedBatch.submitted==1u &&
           collapsedBatch.leadingEmptySourceDraws==2u);

    // 01239: genuine one-float-ULP FVF triangles have finite nonzero
    // projected area far below 1e-12. They still belong to native PRE/POST
    // GPU RGB sampling; the old absolute-area threshold discarded their
    // entire original Draw from source-authentic island capture.
    Vertex fine[]{
        {{.5f,.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{.500000059604644775390625f,.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{.5f,.500000059604644775390625f,.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan fineSource{
        fine,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    NativeRawDrawExtent fineExtent{};
    NativeRawFvfInteriorSample fineInterior{};
    assert(!native_game_fvf_fully_clipped_draw(
        fineSource,true,nullptr,&solidNoCull,true));
    assert(native_raw_fvf_projected_raster(
        fineSource,0,0,3440,1440,fineExtent,nullptr,&solidNoCull,
        &fineInterior));
    assert(fineExtent.left < fineExtent.right &&
           fineExtent.top < fineExtent.bottom &&
           fineInterior.pixelX >= fineExtent.left &&
           fineInterior.pixelX < fineExtent.right);
    // Authenticated indexed Draw: unused vertices never substitute for the
    // real one-ULP triangle. Every source index must be in-range and the
    // live GPU source geometry remains available to the island selector.
    Vertex fineIndexed[]{
        {{-.8f,-.8f,.5f,1.f},{1,1,1,1,1,1}},
        fine[0],fine[1],fine[2],
        {{-.7f,-.3f,.5f,1.f},{1,1,1,1,1,1}}
    };
    const std::uint32_t fineIndices[]{1u,2u,3u};
    NativeRawFvfClipSpan fineIndexedSource{
        fineIndexed,sizeof(Vertex),5u,fineIndices,3u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    assert(native_raw_fvf_projected_raster(
        fineIndexedSource,0,0,3440,1440,fineExtent,nullptr,
        &solidNoCull));
    NativeRawDualTile fineTiles{};
    assert(native_raw_fvf_island_dual_draw_tile(
        fineIndexedSource,0,0,3440,1440,3440,1440,512,288,
        {0,0,3440,1440},0u,fineTiles,&solidNoCull));
    const std::uint32_t fineBadIndices[]{1u,2u,99u};
    fineIndexedSource.indices=fineBadIndices;
    assert(!native_raw_fvf_projected_raster(
        fineIndexedSource,0,0,3440,1440,fineExtent,nullptr,
        &solidNoCull));
    assert(!native_raw_fvf_island_dual_draw_tile(
        fineIndexedSource,0,0,3440,1440,3440,1440,512,288,
        {0,0,3440,1440},0u,fineTiles,&solidNoCull));
    // Exact axis-collapse remains an empty SOLID source, but its authentic
    // WIREFRAME edges must still have a real GPU sampling footprint.
    fineIndexedSource.indices=fineIndices;
    fineIndexed[2].clip[0]=.5f;
    assert(!native_raw_fvf_projected_raster(
        fineIndexedSource,0,0,3440,1440,fineExtent,nullptr,
        &solidNoCull));
    assert(native_raw_fvf_projected_raster(
        fineIndexedSource,0,0,3440,1440,fineExtent,nullptr,
        &wireNoCull));

    // 01240: a genuine indexed/linear native WIREFRAME triangle may be
    // EXACTLY diagonal-collinear (signed area zero) while its clipped
    // line edges still cover native GPU pixels. The original area-only
    // selector left the edge anchor at (0,0), sampling unrelated RGB.
    // All three source edge midpoints must be visited; the two synthetic
    // midpoints between edge anchors are polygon INTERIOR, not wire edges.
    Vertex diagonalWire[]{
        {{-.8f,-.6f,.5f,1.f},{1,1,1,1,1,1}},
        {{ 0.f, 0.f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .8f, .6f,.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan diagonalSource{
        diagonalWire,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    NativeRawDrawExtent diagonalExtent{};
    NativeRawFvfInteriorSample diagonalEdge{};
    assert(native_raw_fvf_projected_raster(
        diagonalSource,0,0,3440,1440,diagonalExtent,nullptr,
        &wireNoCull,&diagonalEdge));
    assert(diagonalEdge.sparseDiagonal &&
           diagonalEdge.pixelX>=diagonalExtent.left &&
           diagonalEdge.pixelX<diagonalExtent.right &&
           diagonalEdge.pixelY>=diagonalExtent.top &&
           diagonalEdge.pixelY<diagonalExtent.bottom);
    NativeRawDualTile diagonalPhases[6]{};
    for (std::uint32_t phase=0u; phase<6u; ++phase) {
        assert(native_raw_fvf_island_dual_draw_tile(
            diagonalSource,0,0,3440,1440,3440,1440,512,288,
            {0,0,3440,1440},phase,diagonalPhases[phase],&wireNoCull));
        assert(!diagonalPhases[phase].hasSecond ||
               native_raw_source_tiles_disjoint(
                   diagonalPhases[phase].first,
                   diagonalPhases[phase].second,512,288));
        if (phase >= 3u) {
            assert(diagonalPhases[phase].first.x ==
                   diagonalPhases[phase-3u].first.x &&
                   diagonalPhases[phase].first.y ==
                   diagonalPhases[phase-3u].first.y);
        }
    }
    // All original edge anchors are physically distinct for this large
    // source line; no fabricated CPU pixels can replace PRE/POST GPU delta.
    assert(diagonalPhases[0].first.x!=diagonalPhases[1].first.x &&
           diagonalPhases[1].first.x!=diagonalPhases[2].first.x);
    const std::uint32_t diagonalIndices[]{2u,1u,0u};
    diagonalSource.indices=diagonalIndices;
    diagonalSource.indexCount=3u;
    assert(native_raw_fvf_island_dual_draw_tile(
        diagonalSource,0,0,3440,1440,3440,1440,512,288,
        {0,0,3440,1440},0u,diagonalPhases[0],&wireNoCull));
    const std::uint32_t diagonalBadIndices[]{2u,1u,99u};
    diagonalSource.indices=diagonalBadIndices;
    assert(!native_raw_fvf_island_dual_draw_tile(
        diagonalSource,0,0,3440,1440,3440,1440,512,288,
        {0,0,3440,1440},0u,diagonalPhases[0],&wireNoCull));
    diagonalSource.indices=nullptr;
    diagonalSource.indexCount=0u;
    for (auto& v : diagonalWire) v.clip[0]=2.f; // truly offscreen
    assert(!native_raw_fvf_island_dual_draw_tile(
        diagonalSource,0,0,3440,1440,3440,1440,512,288,
        {0,0,3440,1440},0u,diagonalPhases[0],&wireNoCull));

    // 01235: authenticated one-pixel POINTLIST / point-filled TRIANGLELIST
    // use the same source-authentic clipping and face-cull certificate.
    // Point scissor proof is conservatively expanded by one pixel.
    Vertex points[]{
        {{-.5f,-.5f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.4f, .5f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.6f,-.1f,.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan unitPoint{
        points,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::PointList,offset,0u};
    const NativeRawFvfScissorClip rightPointScissor{
        0.0,0.0,100.0,100.0,60,0,100,100};
    assert(native_game_fvf_fully_clipped_draw(
        unitPoint,true,&rightPointScissor));
    points[0].clip[0]=.19f; // x=59.5: aliasing can reach sample x=60
    assert(!native_game_fvf_fully_clipped_draw(
        unitPoint,true,&rightPointScissor));
    points[0].clip[0]=-.5f;
    const std::uint32_t pointOrder[]{1u,0u,2u};
    unitPoint.indices=pointOrder;unitPoint.indexCount=3u;
    assert(native_game_fvf_fully_clipped_draw(
        unitPoint,true,&rightPointScissor)); // valid indexed hidden points
    points[1].clip[0]=.6f;
    assert(!native_game_fvf_fully_clipped_draw(
        unitPoint,true,&rightPointScissor)); // visible indexed point
    points[1].clip[0]=-.4f;
    const std::uint32_t badPointOrder[]{1u,0u,99u};
    unitPoint.indices=badPointOrder;
    assert(!native_game_fvf_fully_clipped_draw(
        unitPoint,true,&rightPointScissor)); // corrupt tail is not empty
    unitPoint.indices=nullptr;unitPoint.indexCount=0u;
    unitPoint.assembly=NativeRawFvfAssembly::TriangleList;
    const NativeRawFvfRaster pointBack{
        NativeRawFvfCull::Back,false,true,false};
    const NativeRawFvfRaster pointNoCull{
        NativeRawFvfCull::None,false,true,false};
    points[0].clip[0]=-.7f;points[0].clip[1]=-.6f;
    points[1].clip[0]= .7f;points[1].clip[1]=-.6f;
    points[2].clip[0]=  0.f;points[2].clip[1]= .7f;
    assert(native_game_fvf_fully_clipped_draw(
        unitPoint,true,nullptr,&pointBack)); // source-cull no GPU points
    assert(!native_game_fvf_fully_clipped_draw(
        unitPoint,true,nullptr,&pointNoCull)); // actual native point draw
    points[2].clip[3]=0.f;
    assert(!native_game_fvf_fully_clipped_draw(
        unitPoint,true,nullptr,&pointBack)); // eye-plane source stays live
    points[2].clip[3]=1.f;
    unitPoint.clipDistanceMask=1u;
    points[0].user[0]=-1.f;
    assert(!native_game_fvf_fully_clipped_draw(
        unitPoint,true,nullptr,&pointBack)); // user-plane partial clip
    points[0].user[0]=1.f;unitPoint.clipDistanceMask=0u;
    live_game_frame::GameNativeFrameBatch pointBatch{};
    assert(pointBatch.absorb_empty_source_draw(0u,true));
    assert(pointBatch.absorb_empty_source_draw(1u,true));
    assert(pointBatch.accepts_full(2u));
    pointBatch.succeeded(false,false);
    pointBatch.record_source_draw(2u);
    assert(pointBatch.submitted==1u &&
           pointBatch.leadingEmptySourceDraws==2u);

    // 01234: front/back face, indexed, strip/fan, eye-plane and lines
    // preserve a source-authentic zero-pixel ordinal only when safe.
    Vertex face[]{
        {{-.7f,-.6f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .7f,-.6f,.5f,1.f},{1,1,1,1,1,1}},
        {{ 0.f, .7f,.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan faceSrc{
        face,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    const NativeRawFvfRaster backCcw{
        NativeRawFvfCull::Back,false,true,false};
    const NativeRawFvfRaster backCw{
        NativeRawFvfCull::Back,true,true,false};
    const NativeRawFvfRaster noCull{
        NativeRawFvfCull::None,false,true,false};
    assert(!native_game_fvf_fully_clipped_draw(faceSrc));
    assert(native_game_fvf_fully_clipped_draw(
        faceSrc,true,nullptr,&backCcw));
    assert(!native_game_fvf_fully_clipped_draw(
        faceSrc,true,nullptr,&backCw));
    assert(!native_game_fvf_fully_clipped_draw(
        faceSrc,true,nullptr,&noCull));
    // 01234-E002: D3D11 RS DepthClipEnable=FALSE retains real out-of-depth
    // positive-W pixels. Caller flag cannot override bound native RS.
    Vertex depthOutside[]{
        {{-.5f,-.5f,2.f,1.f},{1,1,1,1,1,1}},
        {{ .5f,-.5f,2.f,1.f},{1,1,1,1,1,1}},
        {{ 0.f, .5f,2.f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan depthSource{
        depthOutside,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    const NativeRawFvfRaster depthClipDisabled{
        NativeRawFvfCull::None,false,false,false};
    assert(native_game_fvf_fully_clipped_draw(depthSource));
    assert(native_game_fvf_fully_clipped_draw(
        depthSource,true,nullptr,&noCull));
    assert(!native_game_fvf_fully_clipped_draw(
        depthSource,true,nullptr,&depthClipDisabled));
    assert(!native_game_fvf_fully_clipped_draw(
        depthSource,false,nullptr,&noCull));
    for (auto& v:depthOutside) v.clip[2]=-0.25f;
    assert(native_game_fvf_fully_clipped_draw(
        depthSource,true,nullptr,&noCull));
    assert(!native_game_fvf_fully_clipped_draw(
        depthSource,true,nullptr,&depthClipDisabled));
    for (auto& v:depthOutside) v.clip[2]=0.5f;
    assert(!native_game_fvf_fully_clipped_draw(
        depthSource,true,nullptr,&noCull));

    const NativeRawFvfScissorClip allScissor{
        0,0,100,100,0,0,100,100};
    assert(native_game_fvf_fully_clipped_draw(
        faceSrc,true,&allScissor,&backCcw));
    const std::uint32_t reverseFace[]{0u,2u,1u};
    faceSrc.indices=reverseFace;faceSrc.indexCount=3u;
    assert(!native_game_fvf_fully_clipped_draw(
        faceSrc,true,nullptr,&backCcw));
    const std::uint32_t badFace[]{0u,2u,99u};
    faceSrc.indices=badFace;
    assert(!native_game_fvf_fully_clipped_draw(
        faceSrc,true,nullptr,&backCcw));
    faceSrc.indices=nullptr;faceSrc.indexCount=0u;
    faceSrc.clipDistanceMask=1u;
    face[0].user[0]=-1.f;
    assert(!native_game_fvf_fully_clipped_draw(
        faceSrc,true,nullptr,&backCcw));
    faceSrc.clipDistanceMask=0u;face[0].user[0]=1.f;
    face[0].clip[3]=0.f;
    assert(!native_game_fvf_fully_clipped_draw(
        faceSrc,true,nullptr,&backCcw));
    face[0].clip[3]=1.f;
    Vertex quad[]{
        {{-.7f,-.7f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .7f,-.7f,.5f,1.f},{1,1,1,1,1,1}},
        {{-.7f, .7f,.5f,1.f},{1,1,1,1,1,1}},
        {{ .7f, .7f,.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan quadSrc{
        quad,sizeof(Vertex),4u,nullptr,0u,
        NativeRawFvfAssembly::TriangleStrip,offset,0u};
    assert(native_game_fvf_fully_clipped_draw(
        quadSrc,true,nullptr,&backCcw));
    assert(!native_game_fvf_fully_clipped_draw(
        quadSrc,true,nullptr,&backCw));
    quadSrc.assembly=NativeRawFvfAssembly::TriangleFan;
    assert(!native_game_fvf_fully_clipped_draw(
        quadSrc,true,nullptr,&backCcw));
    quadSrc.assembly=NativeRawFvfAssembly::LineStrip;
    assert(!native_game_fvf_fully_clipped_draw(
        quadSrc,true,nullptr,&backCcw));
    live_game_frame::GameNativeFrameBatch faceBatch{};
    assert(faceBatch.absorb_empty_source_draw(0u,true));
    assert(faceBatch.accepts_full(1u));
    faceBatch.succeeded(false,false);
    faceBatch.record_source_draw(1u);
    assert(faceBatch.submitted==1u &&
           faceBatch.leadingEmptySourceDraws==1u);

    // 01232: a corner-scissored original FVF triangle can cross EACH
    // clipping plane, yet lie entirely outside their INTERSECTION.
    // A single-plane vertex test cannot prove this empty GPU Draw.
    Vertex cornerOutside[]{
        {{ 0.6f,-0.6f,0.5f,1.f},{1,1,1,1,1,1}},
        {{-0.6f, 0.6f,0.5f,1.f},{1,1,1,1,1,1}},
        {{-0.3f,-0.3f,0.5f,1.f},{1,1,1,1,1,1}}
    };
    NativeRawFvfClipSpan cornerSource{
        cornerOutside,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,0u};
    const NativeRawFvfScissorClip upperRight{
        0.0,0.0,100.0,100.0,70,0,100,30};
    assert(!native_game_fvf_fully_clipped_draw(cornerSource));
    assert(native_game_fvf_fully_clipped_draw(
        cornerSource,true,&upperRight));
    // The identical original IA is still potentially GPU-visible when
    // one corner reaches the overlap (including via a clipped edge).
    cornerOutside[2].clip[0]=0.9f;
    cornerOutside[2].clip[1]=0.9f;
    assert(!native_game_fvf_fully_clipped_draw(
        cornerSource,true,&upperRight));
    cornerOutside[2].clip[0]=-0.3f;
    cornerOutside[2].clip[1]=-0.3f;
    const std::uint32_t cornerIndices[]{0u,1u,2u};
    cornerSource.indices=cornerIndices;
    cornerSource.indexCount=3u;
    assert(native_game_fvf_fully_clipped_draw(
        cornerSource,true,&upperRight));
    cornerSource.assembly=NativeRawFvfAssembly::LineStrip;
    assert(native_game_fvf_fully_clipped_draw(
        cornerSource,true,&upperRight));
    cornerSource.assembly=NativeRawFvfAssembly::TriangleList;
    // Independent enabled user ClipDistance planes can also form a
    // disjoint source polygon even though none excludes all corners.
    Vertex splitUser[]{
        {{-0.4f,-0.4f,0.5f,1.f},{ 1,-2,1,1,1,1}},
        {{ 0.4f,-0.4f,0.5f,1.f},{-2, 1,1,1,1,1}},
        {{ 0.0f, 0.4f,0.5f,1.f},{-2,-2,1,1,1,1}}
    };
    NativeRawFvfClipSpan dualUser{
        splitUser,sizeof(Vertex),3u,nullptr,0u,
        NativeRawFvfAssembly::TriangleList,offset,3u};
    assert(native_game_fvf_fully_clipped_draw(dualUser));
    dualUser.clipDistanceMask=1u;
    assert(!native_game_fvf_fully_clipped_draw(dualUser));
    dualUser.clipDistanceMask=3u;
    splitUser[0].user[1]=2.f;
    assert(!native_game_fvf_fully_clipped_draw(dualUser));
    splitUser[0].user[1]=-2.f;
    splitUser[1].user[1]=std::numeric_limits<float>::quiet_NaN();
    assert(!native_game_fvf_fully_clipped_draw(dualUser));
    // This is a pixel-neutral SOURCE ordinal, not a synthetic GPU success.
    live_game_frame::GameNativeFrameBatch cornerBatch{};
    assert(cornerBatch.absorb_empty_source_draw(0u,true));
    assert(cornerBatch.accepts_full(1u));
    cornerBatch.succeeded(true,false);
    cornerBatch.record_source_draw(1u);

    // Even an independent foreign-Z/reversed-Z source command cannot
    // poison a prior real native Draw when its entire IA is pixel-neutral.
    live_game_frame::GameNativeFrameBatch scissorBatch{};
    assert(scissorBatch.absorb_empty_source_draw(0u,true));
    assert(scissorBatch.accepts_full(1u));
    scissorBatch.succeeded(true,false);
    scissorBatch.record_source_draw(1u);
    assert(!scissorBatch.accepts_depth(true,true));
    assert(scissorBatch.absorb_empty_source_draw(2u,true));
    assert(scissorBatch.accepts_full(3u));
    assert(scissorBatch.submitted == 1u &&
           scissorBatch.postDrawEmptySourceDraws == 1u);

}