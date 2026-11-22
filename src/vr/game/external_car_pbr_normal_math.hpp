#pragma once
// Normal transform for row-vector world matrices. Shader normal vectors
// require inverse-transpose when the source/world scale is nonuniform.
#include <cmath>

namespace OutRunVR::DinoSidecar {
inline bool ExternalCarPbrNormalMatrix(const float* world,float* rows) noexcept {
    if(!world || !rows)return false;
    for(unsigned i=0;i<16u;++i)
        if(!std::isfinite(world[i]))return false;
    const double a=world[0], b=world[1], c=world[2];
    const double d=world[4], e=world[5], f=world[6];
    const double g=world[8], h=world[9], i=world[10];
    const double cof[9]{
        e*i-f*h, f*g-d*i, d*h-e*g,
        c*h-b*i, a*i-c*g, b*g-a*h,
        b*f-c*e, c*d-a*f, a*e-b*d
    };
    const double det=a*cof[0]+b*cof[1]+c*cof[2];
    if(!std::isfinite(det) || std::abs(det)<1e-12)return false;
    float result[12]{};
    for(unsigned row=0;row<3u;++row) {
        for(unsigned col=0;col<3u;++col) {
            const double value=cof[row*3u+col]/det;
            if(!std::isfinite(value))return false;
            result[row*4u+col]=static_cast<float>(value);
            if(!std::isfinite(result[row*4u+col]))return false;
        }
    }
    for(unsigned k=0;k<12u;++k)rows[k]=result[k];
    return true;
}
} // namespace OutRunVR::DinoSidecar
