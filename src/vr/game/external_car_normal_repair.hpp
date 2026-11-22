#pragma once
// Repair zero-length imported vertex normals only when source triangles
// provide a defined geometric normal. Never change positions, UV, index
// order, valid source normals, or the PBR normal map itself.
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>
#include "dino_external_sidecar.hpp"

namespace OutRunVR::DinoSidecar {
struct NormalRepairStats final {
    std::uint64_t repaired=0;
    std::uint64_t unresolved=0;
};

inline bool HasUsableExternalNormal(const Vertex& v) noexcept {
    const double x=v.nx,y=v.ny,z=v.nz;
    const double length2=x*x+y*y+z*z;
    return std::isfinite(length2) && length2>1.e-12;
}

inline NormalRepairStats RepairExternalMeshNormals(Mesh& mesh) {
    NormalRepairStats result{};
    bool needsRepair=false;
    for(const auto& v:mesh.vertices)
        if(!HasUsableExternalNormal(v)){needsRepair=true;break;}
    if(!needsRepair)return result;
    std::vector<std::array<double,3>> accum(mesh.vertices.size());
    for(std::size_t i=0;i+2<mesh.indices.size();i+=3) {
        const auto i0=mesh.indices[i],i1=mesh.indices[i+1],
                   i2=mesh.indices[i+2];
        if(i0>=mesh.vertices.size() || i1>=mesh.vertices.size() ||
           i2>=mesh.vertices.size())continue;
        const auto& a=mesh.vertices[i0];
        const auto& b=mesh.vertices[i1];
        const auto& c=mesh.vertices[i2];
        const double abx=double(b.x)-a.x,aby=double(b.y)-a.y,
                     abz=double(b.z)-a.z;
        const double acx=double(c.x)-a.x,acy=double(c.y)-a.y,
                     acz=double(c.z)-a.z;
        const double nx=aby*acz-abz*acy,
                     ny=abz*acx-abx*acz,
                     nz=abx*acy-aby*acx;
        const double n2=nx*nx+ny*ny+nz*nz;
        if(!std::isfinite(n2) || n2<=1.e-24)continue;
        for(const auto id:{i0,i1,i2}){
            accum[id][0]+=nx;accum[id][1]+=ny;accum[id][2]+=nz;
        }
    }
    for(std::size_t i=0;i<mesh.vertices.size();++i) {
        auto& v=mesh.vertices[i];
        if(HasUsableExternalNormal(v))continue;
        const auto& n=accum[i];
        const double length2=n[0]*n[0]+n[1]*n[1]+n[2]*n[2];
        if(!std::isfinite(length2) || length2<=1.e-24) {
            ++result.unresolved;
            continue;
        }
        const double inv=1.0/std::sqrt(length2);
        v.nx=static_cast<float>(n[0]*inv);
        v.ny=static_cast<float>(n[1]*inv);
        v.nz=static_cast<float>(n[2]*inv);
        if(HasUsableExternalNormal(v))++result.repaired;
        else ++result.unresolved;
    }
    return result;
}

inline NormalRepairStats RepairExternalModelNormals(Model& model) {
    NormalRepairStats result{};
    // Legacy fixed-function sidecars retain their unchanged source normals.
    if(!model.pbrEnabled)return result;
    for(auto& mesh:model.meshes) {
        const auto next=RepairExternalMeshNormals(mesh);
        result.repaired+=next.repaired;
        result.unresolved+=next.unresolved;
    }
    return result;
}
} // namespace OutRunVR::DinoSidecar
