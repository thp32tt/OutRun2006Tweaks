#pragma once
// Row-vector D3D9 view-matrix inverse camera extraction, shared by the
// initial PBR Bind and R7's per-eye stereo uploads. No platform headers.
#include <cmath>

namespace OutRunVR::DinoSidecar {
inline bool ExternalPbrEyeConstants(const float* view,float ormPresent,
                                   float* output) noexcept {
    if(!view || !output || !std::isfinite(ormPresent))return false;
    for(unsigned i=0;i<16u;++i)
        if(!std::isfinite(view[i]))return false;
    // Native camera composition can contain scale or nonorthogonal
    // rotation. The transpose shortcut is correct only for a rigid view.
    // Solve eye * A + translation = 0 for the row-vector affine view.
    if(std::abs(view[3])>1.e-6f||std::abs(view[7])>1.e-6f||
       std::abs(view[11])>1.e-6f||std::abs(view[15]-1.f)>1.e-6f)return false;
    const double a=view[0],b=view[1],c=view[2];
    const double d=view[4],e=view[5],f=view[6];
    const double g=view[8],h=view[9],i=view[10];
    const double cof[9]{e*i-f*h,f*g-d*i,d*h-e*g,
                        c*h-b*i,a*i-c*g,b*g-a*h,
                        b*f-c*e,c*d-a*f,a*e-b*d};
    const double det=a*cof[0]+b*cof[1]+c*cof[2];
    const double norm=std::sqrt((a*a+b*b+c*c)*(d*d+e*e+f*f)*(g*g+h*h+i*i));
    if(!(norm>0.)||!std::isfinite(norm)||!std::isfinite(det)||
       std::abs(det)<=norm*1.e-8)return false;
    const double x=view[12],y=view[13],z=view[14];
    const double pos[3]{-(x*cof[0]+y*cof[1]+z*cof[2])/det,
                        -(x*cof[3]+y*cof[4]+z*cof[5])/det,
                        -(x*cof[6]+y*cof[7]+z*cof[8])/det};
    const float eye[3]{static_cast<float>(pos[0]),static_cast<float>(pos[1]),
                       static_cast<float>(pos[2])};
    if(!std::isfinite(eye[0]) || !std::isfinite(eye[1]) ||
       !std::isfinite(eye[2]))return false;
    output[0]=eye[0];
    output[1]=eye[1];
    output[2]=eye[2];
    output[3]=ormPresent;
    return true;
}
} // namespace OutRunVR::DinoSidecar
