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
    assert(DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
    rp[8]=0.f;
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
    assert(!DistinctFiniteExternalEyeTransforms(nullptr,rv,lp,rp));
    rv[0]=std::numeric_limits<float>::quiet_NaN();
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
    rv[0]=lv[0];rp[11]=std::numeric_limits<float>::infinity();
    assert(!DistinctFiniteExternalEyeTransforms(lv,rv,lp,rp));
}
