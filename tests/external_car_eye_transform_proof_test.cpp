#include "../src/vr/game/external_car_eye_transform_proof.hpp"
#include <algorithm>
#include <cassert>
#include <limits>

using OutRunVR::DinoSidecar::DistinctFiniteExternalEyeTransforms;
int main() {
    float lv[16]{},rv[16]{},lp[16]{},rp[16]{};
    lv[0]=lv[5]=lv[10]=lv[15]=1.f;
    lp[0]=lp[5]=lp[10]=lp[15]=1.f;
    std::copy(lv,lv+16,rv);
    std::copy(lp,lp+16,rp);
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
    rv[12]=0.032f; // distinct left/right eye translations
    assert(DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
    rv[12]=0.f;
    rp[8]=0.012f; // canted/asymmetric eye projection
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp)); // zero IPD, projection-only
    rp[8]=0.f;
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
    assert(!DistinctFiniteExternalEyeTransforms(nullptr,rv,lp,rp));
    rv[0]=std::numeric_limits<float>::quiet_NaN();
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
    rv[0]=lv[0];
    rv[12]=1.e-8f; // numerical jitter cannot be eye baseline
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
    rv[12]=0.f;
    rv[0]=0.f;rv[1]=1.f;rv[4]=-1.f;rv[5]=0.f;
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp)); // orientation-only
    rv[12]=0.032f;
    assert(DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp)); // rotated + real baseline
    rv[3]=0.1f;
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp)); // invalid affine eye
    rv[3]=0.f;
    rp[11]=std::numeric_limits<float>::infinity();
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
}
