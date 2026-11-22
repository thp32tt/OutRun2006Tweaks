#pragma once
// Device-independent proof for the physical external-car fixed-function path.
// A pair of successful eye DIPs still draws mono if VIEW and PROJECTION
// are identical. Reject absent, nonfinite or identical eye transforms.
#include <cmath>
#include <cstddef>

namespace OutRunVR::DinoSidecar {
inline bool DistinctFiniteExternalEyeTransforms(
    const float* leftView,const float* rightView,
    const float* leftProjection,const float* rightProjection) noexcept
{
    if(!leftView || !rightView || !leftProjection || !rightProjection)
        return false;
    bool distinct=false;
    for(std::size_t i=0;i<16u;++i) {
        if(!std::isfinite(leftView[i]) || !std::isfinite(rightView[i]) ||
           !std::isfinite(leftProjection[i]) ||
           !std::isfinite(rightProjection[i]))
            return false;
        if(leftView[i]!=rightView[i] ||
           leftProjection[i]!=rightProjection[i])
            distinct=true;
    }
    return distinct;
}
} // namespace OutRunVR::DinoSidecar
