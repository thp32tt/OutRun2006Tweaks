#pragma once
// Device-independent proof for the physical external-car fixed-function path.
// A pair of successful eye DIPs still draws mono if camera centres coincide.\n// Distinct projection alone (asymmetric lenses) does NOT prove stereo depth.
#include <cmath>
#include <cstddef>

namespace OutRunVR::DinoSidecar {
inline bool DistinctFiniteExternalEyeTransforms(
    const float* leftView,const float* rightView,
    const float* leftProjection,const float* rightProjection) noexcept
{
    if(!leftView || !rightView || !leftProjection || !rightProjection)
        return false;
    for(std::size_t i=0;i<16u;++i) {
        if(!std::isfinite(leftView[i]) || !std::isfinite(rightView[i]) ||
           !std::isfinite(leftProjection[i]) ||
           !std::isfinite(rightProjection[i]))
            return false;
    }
    // A projection-only change or canted orientations about a shared centre
    // cannot establish binocular parallax. Extract centres from row-vector
    // rigid D3D9 view matrices (camera = -(translation * rotation^T)).
    const float* views[2]{leftView,rightView};
    for(const float* v:views) {
        constexpr float affineTolerance=1.0e-4f;
        if(std::fabs(v[3])>affineTolerance ||
           std::fabs(v[7])>affineTolerance ||
           std::fabs(v[11])>affineTolerance ||
           std::fabs(v[15]-1.f)>affineTolerance) return false;
    }
    constexpr double separationSqMin=1.0e-12; // 1e-6 world units
    double separationSq=0.0;
    for(std::size_t axis=0;axis<3u;++axis) {
        const auto cameraCentre=[axis](const float* v) noexcept {
            return -(static_cast<double>(v[12])*v[axis*4u] +
                     static_cast<double>(v[13])*v[axis*4u+1u] +
                     static_cast<double>(v[14])*v[axis*4u+2u]);
        };
        const double delta=cameraCentre(leftView)-cameraCentre(rightView);
        if(!std::isfinite(delta))return false;
        separationSq+=delta*delta;
    }
    return std::isfinite(separationSq) && separationSq>separationSqMin;
}
} // namespace OutRunVR::DinoSidecar
