#pragma once
#include "dino_external_sidecar.hpp"

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
} // namespace OutRunVR::DinoSidecar
