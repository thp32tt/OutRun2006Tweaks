#pragma once
// Real D3D9 FVF D3DFILL_POINT clips source triangles before point rasterization.
// D3D11 POINTLIST cannot generate intersection vertices: build every point
// and interpolated native VS attribute before touching the GPU. Always keep
// the original D3D9 game Draw and input/FFB path as fail-closed fallback.
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
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
        (topology!=4u && topology!=5u) || (topology==4u && elements%3u) ||
        (cull!=1u && cull!=2u && cull!=3u) || (userMask & ~0x3fu) ||
        maxVertices<3u) return false;
    struct V {
        Vertex vertex{};
        std::array<double,12> plane{};
    };
    const auto load = [userMask](const Vertex& v,V& out) noexcept {
        const double x=v.clip[0],y=v.clip[1],z=v.clip[2],w=v.clip[3];
        if (!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z)||
            !std::isfinite(w)||!(w>0.00001)) return false;
        out.vertex=v;
        out.plane={w+x,w-x,w+y,w-y,z,w-z,0,0,0,0,0,0};
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
            const unsigned ai=topology==4u?3u*t:t+(t&1u);
            const unsigned bi=topology==4u?ai+1u:t+1u-(t&1u);
            const unsigned ci=topology==4u?ai+2u:t+2u;
            const auto idx=[indices](unsigned i) noexcept {
                return indices?indices[i]:i;
            };
            const auto a=idx(ai),b=idx(bi),c=idx(ci);
            if (a>=source.size()||b>=source.size()||c>=source.size())
                return false;
            V va{},vb{},vc{};
            if (!load(source[a],va)||!load(source[b],vb)||
                !load(source[c],vc)) return false;
            bool invisible=false,crossing=false;
            for (unsigned p=0u;p<12u;++p) {
                if (p>=6u && !(userMask & (1u<<(p-6u)))) continue;
                const bool na=va.plane[p]<0,nb=vb.plane[p]<0,
                           nc=vc.plane[p]<0;
                invisible|=na&&nb&&nc;
                crossing|=na||nb||nc;
            }
            if (invisible) continue;
            const auto nx=[](const V& v) noexcept {
                return double(v.vertex.clip[0])/v.vertex.clip[3];
            };
            const auto ny=[](const V& v) noexcept {
                return double(v.vertex.clip[1])/v.vertex.clip[3];
            };
            const double area=(nx(vb)-nx(va))*(ny(vc)-ny(va))-
                              (ny(vb)-ny(va))*(nx(vc)-nx(va));
            if (!std::isfinite(area)||std::abs(area)<=1.e-12) return false;
            const bool clockwise=area<0.0; // Y flipped by D3D viewport
            if ((cull==2u&&clockwise)||(cull==3u&&!clockwise)) continue;
            std::vector<V> polygon{va,vb,vc};
            if (crossing) for (unsigned p=0u;p<12u;++p) {
                if (p>=6u && !(userMask & (1u<<(p-6u)))) continue;
                if (polygon.empty()) break;
                std::vector<V> clipped;
                clipped.reserve(polygon.size()+1u);
                V last=polygon.back();
                for (const auto& current:polygon) {
                    const bool insideLast=last.plane[p]>=0;
                    const bool insideNow=current.plane[p]>=0;
                    if (insideLast!=insideNow) {
                        const double u=last.plane[p]/
                                       (last.plane[p]-current.plane[p]);
                        if (!std::isfinite(u)||u<0.0||u>1.0) return false;
                        // An endpoint on the plane is already emitted once.
                        if (u>0.0 && u<1.0) {
                            V cut{};
                            cut.vertex=interpolate(last.vertex,current.vertex,u);
                            if (!load(cut.vertex,cut)) return false;
                            for (unsigned d=0u;d<12u;++d)
                                cut.plane[d]=last.plane[d]+u*
                                    (current.plane[d]-last.plane[d]);
                            cut.plane[p]=0.0;
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
            if (polygon.size()>maxVertices-fresh.size()) return false;
            for (const auto& v:polygon) fresh.push_back(v.vertex);
        }
        if (fresh.empty()) return false;
        destination.swap(fresh);
        return true;
    } catch (...) { return false; }
}
} // namespace outrun::vr::dx11::live_game_frame
