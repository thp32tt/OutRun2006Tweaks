#pragma once
#include "../../src/vr/game/dino_external_sidecar.hpp"
namespace OutRunVR::DinoSidecar {
// Exact flat-color proof for the preserved albedo. All BC mip blocks
// must use equal color endpoints, and BC3 alpha must decode to one value.
inline bool uniform_albedo(const Texture& texture){
 const auto& d=texture.dds;
 if(d.size()<132)return false;
 if(texture.format==TextureFormat::ARGB32){
  if((d.size()-128)%4)return false;
  for(size_t i=132;i<d.size();i+=4)
   if(std::memcmp(d.data()+i,d.data()+128,4)!=0)return false;
  return true;
 }
 const unsigned block=texture.format==TextureFormat::DXT1?8u:16u;
 if((d.size()-128)%block)return false;
 unsigned color=0,alpha=0;bool first=true;size_t off=128;
 for(unsigned level=0;level<texture.mips;++level){
  const unsigned w=std::max(1u,texture.width>>level),h=std::max(1u,texture.height>>level);
  for(unsigned by=0;by<h;by+=4)for(unsigned bx=0;bx<w;bx+=4){
   if(off+block>d.size())return false;
   const auto* p=d.data()+off+(block==16u?8u:0u);
   const unsigned c0=U16(p),c1=U16(p+2),indices=U32(p+4);
   if(c0!=c1||(!first&&c0!=color))return false;
   color=c0;
   const unsigned a0=d[off],a1=d[off+1];
   std::uint64_t bits=0;
   if(block==16u){
    if(a0!=a1||(!first&&a0!=alpha))return false;
    alpha=a0;
    for(unsigned i=0;i<6;++i)bits|=std::uint64_t(d[off+2+i])<<(8*i);
   }
   // BC blocks at 2x2 / 1x1 mips include unused padding selectors.
   // Check only actual in-bounds texels, not transparent block padding.
   for(unsigned y=0;y<std::min(4u,h-by);++y)for(unsigned x=0;x<std::min(4u,w-bx);++x){
    const unsigned i=y*4+x;
    if(block==8u){if(((indices>>(2*i))&3u)==3u)return false;}
    else{
     const auto index=(bits>>(3*i))&7u;
     if((index==6u&&a0!=0u)||(index==7u&&a0!=255u))return false;
    }
   }
   first=false;off+=block;
  }
 }
 if(off!=d.size())return false;
 return !first;
}
} // namespace OutRunVR::DinoSidecar
