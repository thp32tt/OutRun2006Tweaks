#pragma once
// Physical live-backbuffer-bound affine for original D3DX full/partial/pivoted
// title/menu/car-selector matrices; game screen_scale can lag after Reset.
#include "multi_sprite_contain_scale.hpp"
#include <cmath>
namespace OutRunVrUiAspect {
struct FrontEndAffineContain {
 float ratioX=0.f,ratioY=0.f,offsetX=0.f,offsetY=0.f;
 bool valid=false;
 float ScaleX(float x) const noexcept {return x*ratioX;}
 float ScaleY(float y) const noexcept {return y*ratioY;}
 float MapX(float x) const noexcept {return x*ratioX+offsetX;}
 float MapY(float y) const noexcept {return y*ratioY+offsetY;}
};
inline FrontEndAffineContain BuildFrontEndAffineContain(
 float sx,float sy,float width,float height,
 float srcWidth,float srcHeight) noexcept {
 const float contain=BoundedMultiSpriteContainScale(
  sx,sy,width,height,srcWidth,srcHeight);
 if(!(contain>0.f))return {};
 const float rx=contain/sx,ry=contain/sy;
 const double ox=(double(width)-double(srcWidth)*contain)*0.5;
 const double oy=(double(height)-double(srcHeight)*contain)*0.5;
 if(!std::isfinite(rx)||!std::isfinite(ry)||
    !std::isfinite(ox)||!std::isfinite(oy))return {};
 const float x=static_cast<float>(ox),y=static_cast<float>(oy);
 if(!std::isfinite(x)||!std::isfinite(y))return {};
 return {rx,ry,x,y,true};
}
}
