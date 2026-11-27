#pragma once
#include "dino_external_sidecar.hpp"
#include <cstring>
#include <numeric>

namespace OutRunVR::DinoSidecar {
inline bool IsExternalGlassMesh(const Mesh& mesh) noexcept {
    return mesh.name.compare(0,10,"F50_GLASS_")==0 ||
           mesh.name.compare(0,10,"EXT_GLASS_")==0;
}
// CPU-only, lossless reduction of draw calls. Merge only adjacent static
// opaque meshes with identical material and index width. Preserve source
// triangle order, vertex bytes, UV seams, and every animated/glass boundary.
// No index widening (GPU payload budget unchanged), no LOD, no welding.
inline unsigned BatchExternalOpaqueMeshes(Model& model) {
    if(!model.highQuality||model.meshes.size()<2)return 0;
    constexpr std::size_t maxBatchVertices=65535u;
    constexpr std::size_t maxBatchIndices=65535u*3u;
    std::vector<bool> animated(model.meshes.size(),false);
    for(const auto& binding:model.dashboardBindings) {
        if(binding.meshIndex>=model.meshes.size())return 0;
        animated[binding.meshIndex]=true;
    }
    std::vector<unsigned> remap(model.meshes.size());
    std::vector<Mesh> batched;
    batched.reserve(model.meshes.size());
    bool previousStatic=false;
    unsigned merged=0;
    for(unsigned i=0;i<model.meshes.size();++i) {
        auto& mesh=model.meshes[i];
        const bool staticOpaque=!animated[i]&&!IsExternalGlassMesh(mesh);
        if(staticOpaque&&previousStatic&&!batched.empty()) {
            auto& dst=batched.back();
            if(dst.material==mesh.material&&dst.index32==mesh.index32&&
               dst.vertices.size()<=maxBatchVertices&&
               mesh.vertices.size()<=maxBatchVertices-dst.vertices.size()&&
               dst.indices.size()<=maxBatchIndices&&
               mesh.indices.size()<=maxBatchIndices-dst.indices.size()) {
                const auto offset=static_cast<std::uint32_t>(dst.vertices.size());
                dst.vertices.insert(dst.vertices.end(),mesh.vertices.begin(),mesh.vertices.end());
                for(const auto index:mesh.indices)dst.indices.push_back(offset+index);
                remap[i]=static_cast<unsigned>(batched.size()-1);
                ++merged;
                continue;
            }
        }
        remap[i]=static_cast<unsigned>(batched.size());
        batched.push_back(std::move(mesh));
        previousStatic=staticOpaque;
    }
    for(auto& binding:model.dashboardBindings)binding.meshIndex=remap[binding.meshIndex];
    model.meshes=std::move(batched);
    return merged;
}
// Reduce uploaded VB bytes without changing a single indexed triangle
// corner. Exact full vertex bytes include position, repaired normal and UV;
// neither seams nor hard edges are welded. Keep index width, mesh identity,
// triangle order, material and dashboard bindings. CPU worker only.
inline unsigned DeduplicateExternalVertices(Model& model) {
    if(!model.highQuality)return 0;
    static_assert(sizeof(Vertex)==8*sizeof(float));
    unsigned removed=0;
    for(auto& mesh:model.meshes){
        if(mesh.vertices.size()<2)continue;
        // Parser has already bounded vertex count and validated every index.
        // Validate callers too before any remap or destructive compaction.
        if(std::any_of(mesh.indices.begin(),mesh.indices.end(),
            [&](auto i){return i>=mesh.vertices.size();}))continue;
        const auto count=static_cast<std::uint32_t>(mesh.vertices.size());
        std::vector<std::uint32_t> order(count),remap(count);
        std::iota(order.begin(),order.end(),0u);
        auto compare=[&](auto a,auto b){
            const int bytes=std::memcmp(&mesh.vertices[a],&mesh.vertices[b],sizeof(Vertex));
            return bytes<0||(bytes==0&&a<b);
        };
        std::sort(order.begin(),order.end(),compare);
        auto first=order[0];remap[first]=first;
        unsigned duplicateCount=0;
        for(std::uint32_t k=1;k<count;++k){
            const auto i=order[k];
            if(std::memcmp(&mesh.vertices[first],&mesh.vertices[i],sizeof(Vertex))==0){
                remap[i]=first;++duplicateCount;
            }else{first=i;remap[i]=i;}
        }
        if(!duplicateCount)continue;
        // Canonical is always the lowest original index. Its compact
        // destination is known before any later alias is processed.
        std::uint32_t write=0;
        for(std::uint32_t i=0;i<count;++i){
            const auto canonical=remap[i];
            if(canonical==i){
                if(write!=i)mesh.vertices[write]=mesh.vertices[i];
                remap[i]=write++;
            }else remap[i]=remap[canonical];
        }
        for(auto& index:mesh.indices)index=remap[index];
        mesh.vertices.resize(write);
        removed+=duplicateCount;
    }
    model.vertices-=removed;
    return removed;
}
} // namespace OutRunVR::DinoSidecar
