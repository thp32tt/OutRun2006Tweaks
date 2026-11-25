#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
// Pure pass selection for the optional Ferrari sidecar only.
// Opaque meshes must establish depth before transparent glass is blended.
// Avoid sorting/copying GPU objects and allocating memory on each eye draw.
namespace OutRunVR::DinoSidecar {
constexpr bool MeshInDrawPass(bool isGlass, unsigned pass) noexcept {
    return pass < 2u && isGlass == (pass == 1u);
}
// Source order is NOT visibility order for overlapping back/front glass.
// Sort only the tagged glass mesh centroids, once per external scene draw;
// tie-break by source index for deterministic stereo submission.
struct GlassDepthItem {
    unsigned index=0;
    float viewZ=0.f;
};
inline float ExternalGlassViewDepth(const float center[3],
                                    const float* world,
                                    const float* view,
                                    float projectionWZ) noexcept {
    if(!center || !world || !view || !std::isfinite(projectionWZ) ||
       projectionWZ==0.f)return 0.f;
    // D3D9 row-vector convention: local * world * view, camera-space z.
    const float x=center[0]*world[0]+center[1]*world[4]+
                  center[2]*world[8]+world[12];
    const float y=center[0]*world[1]+center[1]*world[5]+
                  center[2]*world[9]+world[13];
    const float z=center[0]*world[2]+center[1]*world[6]+
                  center[2]*world[10]+world[14];
    const float depth=x*view[2]+y*view[6]+z*view[10]+view[14];
    // Perspective clip W = viewZ * projection._34 (plus _44).
    // Retail OutRun uses _34=-1: visible points have NEGATIVE view Z.
    // Sort by signed forward distance, not raw Z or abs(Z) (behind-eye
    // geometry must not be mistaken for distant visible glass).
    const float forward=projectionWZ<0.f ? -depth : depth;
    return std::isfinite(forward)?forward:0.f;
}
inline void SortGlassBackToFront(GlassDepthItem* items,
                                 std::size_t count) noexcept {
    if(!items || count<2)return;
    std::sort(items,items+count,[](const GlassDepthItem& a,
                                   const GlassDepthItem& b) noexcept {
        return a.viewZ==b.viewZ ? a.index<b.index : a.viewZ>b.viewZ;
    });
}
// The source owns UV interpolation; sampler ADDRESS_WRAP is independent.
// Stage 0 is the final fixed-function stage, so its output must be CURRENT.
// Shader TEXCOORD0/1/2 carry world position, normal and UV respectively.
// A failed state setter must stop before any external raster submission.
template<class SetCurrent,class SetWrap>
inline bool ConfigureExternalTextureRouting(SetCurrent setCurrent,
                                             SetWrap setWrap) noexcept {
    if(!setCurrent())return false;
    for(unsigned coordinate=0;coordinate<3u;++coordinate)
        if(!setWrap(coordinate))return false;
    return true;
}
static_assert(MeshInDrawPass(false,0u));
static_assert(!MeshInDrawPass(true,0u));
static_assert(MeshInDrawPass(true,1u));
static_assert(!MeshInDrawPass(false,1u));
static_assert(!MeshInDrawPass(false,2u));
} // namespace OutRunVR::DinoSidecar
