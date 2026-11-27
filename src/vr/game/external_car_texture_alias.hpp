#pragma once
#include "dino_external_sidecar.hpp"
namespace OutRunVR::DinoSidecar {
// Share only exact immutable DDS within a texture role. Material factors
// remain separate. Empty maps never alias.
inline bool SameExternalTexture(const Texture& a,const Texture& b) noexcept {
    return !a.dds.empty()&&a.width==b.width&&a.height==b.height&&
        a.mips==b.mips&&a.format==b.format&&a.dds==b.dds;
}
template<class Get>
inline std::vector<unsigned> ExternalTextureAliases(unsigned count,Get get) {
    std::vector<unsigned> aliases(count);
    for(unsigned i=0;i<count;++i){
        aliases[i]=i;
        const auto& src=get(i);
        if(src.dds.empty())continue;
        for(unsigned j=0;j<i;++j)
            if(aliases[j]==j&&SameExternalTexture(src,get(j))){
                aliases[i]=j;break;
            }
    }
    return aliases;
}
struct ExternalTextureAliasPlan {
    std::vector<unsigned> albedo,normal,orm;
};
inline ExternalTextureAliasPlan BuildExternalTextureAliasPlan(const Model& m) {
    return {
        ExternalTextureAliases(static_cast<unsigned>(m.textures.size()),
            [&](unsigned i)->const Texture&{return m.textures[i];}),
        ExternalTextureAliases(static_cast<unsigned>(m.pbrMaterials.size()),
            [&](unsigned i)->const Texture&{return m.pbrMaterials[i].normal;}),
        ExternalTextureAliases(static_cast<unsigned>(m.pbrMaterials.size()),
            [&](unsigned i)->const Texture&{return m.pbrMaterials[i].orm;})
    };
}
// Canonical slots alone own COM references; aliases never AddRef or Release.
template<class Resource>
inline Resource* ResolveExternalTexture(const std::vector<Resource*>& resources,
    const std::vector<unsigned>& aliases,unsigned material) noexcept {
    if(material>=aliases.size())return nullptr;
    const auto i=aliases[material];
    if(i>material||i>=resources.size()||i>=aliases.size()||aliases[i]!=i)return nullptr;
    return resources[i];
}
// Cache only within the already-isolated raw raster owner. A nullptr
// binding is meaningful (disable inherited texture), so track validity
// separately. An unsuccessful setter never publishes a cached state.
template<class Resource>
struct ExternalTextureBindCache {
    std::array<Resource*,3> bound{};
    std::array<bool,3> known{};
    void Invalidate() noexcept {known.fill(false);bound.fill(nullptr);}
    template<class Current,class Setter>
    bool Bind(unsigned slot,Resource* resource,bool isolated,Current current,Setter set) noexcept {
        if(slot>=known.size()||!current())return false;
        if(isolated&&known[slot]&&bound[slot]==resource)return true;
        if(!set(slot,resource)||!current()){Invalidate();return false;}
        known[slot]=true;bound[slot]=resource;return true;
    }
};
} // namespace OutRunVR::DinoSidecar
