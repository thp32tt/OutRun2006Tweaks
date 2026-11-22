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
    // A rigid row-vector view has translation in row four. Multiplication
    // by the transpose of its orthonormal rotation recovers eye position.
    const float eye[3]{
        -(view[12]*view[0]+view[13]*view[1]+view[14]*view[2]),
        -(view[12]*view[4]+view[13]*view[5]+view[14]*view[6]),
        -(view[12]*view[8]+view[13]*view[9]+view[14]*view[10])
    };
    if(!std::isfinite(eye[0]) || !std::isfinite(eye[1]) ||
       !std::isfinite(eye[2]))return false;
    output[0]=eye[0];
    output[1]=eye[1];
    output[2]=eye[2];
    output[3]=ormPresent;
    return true;
}
} // namespace OutRunVR::DinoSidecar
