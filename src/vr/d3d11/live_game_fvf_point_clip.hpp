#pragma once
// Real D3D9 FVF D3DFILL_POINT clips source triangles before point rasterization.
// D3D11 POINTLIST cannot generate intersection vertices: build every point
// and interpolated native VS attribute before touching the GPU. In particular,
// clip eye-plane-crossing world-space vertices before NDC winding/culling;
// the real D3D9 WVP path legitimately supplies W<=0 corners. Always keep
// the original D3D9 game Draw and input/FFB path as fail-closed fallback.
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>
namespace outrun::vr::dx11::live_game_frame {
template<class Vertex, class Interpolate>
[[nodiscard]] bool game_fvf_clipped_point_vertices(
    const std::vector<Vertex>& source, const std::uint32_t* indices,
    std::uint32_t elements, std::uint32_t topology, std::uint32_t cull,
    std::uint32_t userMask, std::uint32_t maxVertices,
    Interpolate interpolate, std::vector<Vertex>& destination) noexcept {
    if (source.empty() || source.size()>1048576u ||
        elements<3u || elements>1048576u ||
        (!indices && source.size()!=elements) ||
        (topology!=4u && topology!=5u && topology!=6u) ||
        (topology==4u && elements%3u) ||
        (cull!=1u && cull!=2u && cull!=3u) || (userMask & ~0x3fu) ||
        maxVertices<3u) return false;
    struct V {
        Vertex vertex{};
        std::array<double,13> plane{};
    };
    // The synthetic positive-W plane is required only for an eye crossing.
    // Its scale is derived from the actual original Draw vertices, not the
    // fixed 1e-5 threshold that can erase a near-camera menu/race polygon.
    // All native points still pass the real hardware X/Y/Z/user clip planes.
    double eyeGuard=0.00001;
    const auto load = [userMask,&eyeGuard](const Vertex& v,V& out) noexcept {
        const double x=v.clip[0],y=v.clip[1],z=v.clip[2],w=v.clip[3];
        if (!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z)||
            !std::isfinite(w)||(!x&&!y&&!z&&!w)) return false;
        out.vertex=v;
        // Keep GPU perspective division out of the CPU until all vertices
        // have been clipped to a strictly positive homogeneous eye plane.
        out.plane={w+x,w-x,w+y,w-y,z,w-z,0,0,0,0,0,0,w-eyeGuard};
        for (unsigned p=0u;p<6u;++p) if (userMask & (1u<<p)) {
            const double d=p<4u?v.clip0[p]:v.clip1[p-4u];
            if (!std::isfinite(d)) return false;
            out.plane[p+6u]=d;
        }
        return true;
    };
    try {
        std::vector<Vertex> fresh;
        const unsigned triangles=topology==4u?elements/3u:elements-2u;
        fresh.reserve((std::min)(maxVertices,triangles*3u));
        for (unsigned t=0u;t<triangles;++t) {
            // The original fan anchor is the first IA occurrence, even
            // for an indexed fan whose first index is not vertex zero.
            // Clipped polygons carry color, both UV stages and clip planes
            // through interpolation before any native GPU POINTLIST write.
            const unsigned ai=topology==4u?3u*t:
                topology==6u?0u:t+(t&1u);
            const unsigned bi=topology==4u?ai+1u:
                topology==6u?t+1u:t+1u-(t&1u);
            const unsigned ci=topology==4u?ai+2u:t+2u;
            const auto idx=[indices](unsigned i) noexcept {
                return indices?indices[i]:i;
            };
            const auto a=idx(ai),b=idx(bi),c=idx(ci);
            if (a>=source.size()||b>=source.size()||c>=source.size())
                return false;
            // Per-source-face guard; previous triangle/window must never
            // leak its camera-plane tolerance into a later original Draw.
            eyeGuard=0.00001;
            V va{},vb{},vc{};
            if (!load(source[a],va)||!load(source[b],vb)||
                !load(source[c],vc)) return false;
            // A wholly visible positive-W FVF polygon must preserve the
            // ORIGINAL GPU eye plane W>0, even when all three W values are
            // smaller than 1e-5. The synthetic epsilon plane is needed only
            // when the actual source polygon crosses W<=0, where clipping
            // protects finite perspective division and vertex interpolation.
            const bool crossesEyePlane =
                va.vertex.clip[3] <= 0.0f ||
                vb.vertex.clip[3] <= 0.0f ||
                vc.vertex.clip[3] <= 0.0f;
            if (crossesEyePlane) {
                // Linear homogeneous clipping cannot create positive W if
                // every authentic corner has W<=0. Otherwise retain a
                // strictly positive float-representable guard below the
                // smallest ORIGINAL positive W. This preserves tiny near-
                // camera geometry, unlike an absolute 1e-5 cutoff. Values
                // too small for a safe guard fail closed to the real D3D9.
                double closestPositiveW=std::numeric_limits<double>::infinity();
                for (double w : {double(va.vertex.clip[3]),
                                 double(vb.vertex.clip[3]),
                                 double(vc.vertex.clip[3])})
                    if (w>0.0) closestPositiveW=(std::min)(closestPositiveW,w);
                if (!std::isfinite(closestPositiveW)) continue;
                eyeGuard=(std::min)(1.0e-5, closestPositiveW*0.25);
                if (!(eyeGuard>0.0) ||
                    !(static_cast<float>(eyeGuard)>0.0f)) return false;
                va.plane[12u]=double(va.vertex.clip[3])-eyeGuard;
                vb.plane[12u]=double(vb.vertex.clip[3])-eyeGuard;
                vc.plane[12u]=double(vc.vertex.clip[3])-eyeGuard;
            }
            // All source indices and active user-plane values were validated
            // first, including negative/zero W world-space game vertices.
            bool invisible=false;
            for (unsigned p=0u;p<13u;++p) {
                if (p==12u && !crossesEyePlane) continue;
                if (p>=6u && p<12u && !(userMask & (1u<<(p-6u))))
                    continue;
                invisible |= va.plane[p]<0 && vb.plane[p]<0 && vc.plane[p]<0;
            }
            if (invisible) continue;
            std::vector<V> polygon{va,vb,vc};
            // The source WVP transform deliberately retains behind-eye and
            // eye-plane corners. NDC x/w and y/w are meaningless there:
            // for a real eye crossing first intersect W>=epsilon, then
            // the D3D9 homogeneous six planes and enabled user clip planes.
            // Fully positive-W source polygons never use this synthetic guard.
            for (unsigned order=0u;order<13u;++order) {
                const unsigned p=order==0u?12u:order-1u;
                if (p==12u && !crossesEyePlane) continue;
                if (p>=6u && p<12u && !(userMask & (1u<<(p-6u))))
                    continue;
                if (polygon.empty()) break;
                std::vector<V> clipped;
                clipped.reserve(polygon.size()+1u);
                V last=polygon.back();
                for (const auto& current:polygon) {
                    const bool insideLast=last.plane[p]>=0.0;
                    const bool insideNow=current.plane[p]>=0.0;
                    if (insideLast!=insideNow) {
                        const double denom=last.plane[p]-current.plane[p];
                        const double u=last.plane[p]/denom;
                        if (!std::isfinite(u)||u<0.0||u>1.0) return false;
                        // Plane endpoints are copied only by the inside branch;
                        // never duplicate or silently skip an intersection.
                        if (u>0.0 && u<1.0) {
                            V cut{};
                            cut.vertex=interpolate(last.vertex,current.vertex,u);
                            if (!load(cut.vertex,cut)) return false;
                            for (unsigned d=0u;d<13u;++d)
                                cut.plane[d]=last.plane[d]+u*
                                    (current.plane[d]-last.plane[d]);
                            cut.plane[p]=0.0;
                            // CPU clipping computes the intersection in double,
                            // but the native D3D11 POINTLIST consumes float
                            // coordinates and float SV_ClipDistance. Rounding
                            // the interpolated float back across the very
                            // plane we just intersected can silently drop an
                            // authentic original-game point pixel. Snap ONLY
                            // generated intersections to their exact source
                            // boundary; untouched game vertices and the
                            // interpolated UV/color/specular remain unchanged.
                            if (p==0u) cut.vertex.clip[0]=-cut.vertex.clip[3];
                            else if (p==1u) cut.vertex.clip[0]=cut.vertex.clip[3];
                            else if (p==2u) cut.vertex.clip[1]=-cut.vertex.clip[3];
                            else if (p==3u) cut.vertex.clip[1]=cut.vertex.clip[3];
                            else if (p==4u) cut.vertex.clip[2]=0.0f;
                            else if (p==5u) cut.vertex.clip[2]=cut.vertex.clip[3];
                            else if (p>=6u && p<10u)
                                cut.vertex.clip0[p-6u]=0.0f;
                            else if (p>=10u && p<12u)
                                cut.vertex.clip1[p-10u]=0.0f;
                            // The synthetic eye-plane W guard must never
                            // manufacture a GPU-visible point from zero W.
                            // It remains verified by the final positive-W
                            // and projected-winding checks below.
                            clipped.push_back(cut);
                        }
                    }
                    if (insideNow) clipped.push_back(current);
                    last=current;
                }
                if (clipped.size()>16u) return false;
                polygon.swap(clipped);
            }
            if (polygon.size()<3u) continue;
            // D3D9 polygon winding is evaluated on the clipped projected
            // polygon, never by dividing a negative-W source vertex. This
            // also preserves original CW/CCW exclusion for point-filled faces.
            // Anchor the clipped polygon at one projected source corner
            // and sum its triangle fans. Unlike an origin-based shoelace
            // with a fixed area cutoff, this preserves thin but genuinely
            // nondegenerate D3D9 point-filled faces and their interpolated
            // GPU vertices. Only an orientation indistinguishable from
            // floating-point cancellation is rejected to D3D9 fallback.
            std::vector<std::array<double,2u>> projected;
            projected.reserve(polygon.size());
            for (const auto& corner:polygon) {
                const auto& v=corner.vertex;
                if (!std::isfinite(v.clip[3]) || !(v.clip[3]>0.0f))
                    return false;
                const double x=double(v.clip[0])/v.clip[3];
                const double y=double(v.clip[1])/v.clip[3];
                if (!std::isfinite(x)||!std::isfinite(y)) return false;
                projected.push_back({x,y});
            }
            double signedArea=0.0, magnitude=0.0;
            for (std::size_t i=1u;i+1u<projected.size();++i) {
                const double abx=projected[i][0]-projected[0][0];
                const double aby=projected[i][1]-projected[0][1];
                const double acx=projected[i+1u][0]-projected[0][0];
                const double acy=projected[i+1u][1]-projected[0][1];
                const double p=abx*acy, q=aby*acx;
                signedArea+=p-q;
                magnitude+=std::abs(p)+std::abs(q);
            }
            const double uncertainty =
                16.0 * std::numeric_limits<double>::epsilon() * magnitude;
            if (!std::isfinite(signedArea)||!std::isfinite(uncertainty)||
                !(std::abs(signedArea)>uncertainty)) return false;
            const bool clockwise=signedArea<0.0; // D3D viewport Y flip
            if ((cull==2u&&clockwise)||(cull==3u&&!clockwise)) continue;
            // The D3D9 polygon clipper triangulates a newly clipped
            // polygon before D3DFILL_POINT rasterization. Native POINTLIST
            // therefore needs THREE corner occurrences for each clipped
            // fan triangle, not one point per unique polygon vertex. For a
            // four-corner clipped menu/race face this is six real GPU points
            // (0,1,2; 0,2,3), preserving the interpolated color, both UV
            // stages and enabled user-plane distances at every occurrence.
            // Capacity is checked for the complete original primitive
            // before its first vertex reaches the native GPU upload.
            const std::size_t pointCount = (polygon.size()-2u)*3u;
            if (fresh.size()>maxVertices ||
                pointCount>maxVertices-fresh.size()) return false;
            for (std::size_t corner=1u;corner+1u<polygon.size();++corner) {
                fresh.push_back(polygon[0u].vertex);
                fresh.push_back(polygon[corner].vertex);
                fresh.push_back(polygon[corner+1u].vertex);
            }
        }
        if (fresh.empty()) return false;
        destination.swap(fresh);
        return true;
    } catch (...) { return false; }
}
} // namespace outrun::vr::dx11::live_game_frame
