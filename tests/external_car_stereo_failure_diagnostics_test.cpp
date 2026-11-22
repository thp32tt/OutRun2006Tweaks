#include "../src/vr/game/external_car_stereo_receipt.hpp"
#include "../src/vr/game/dino_external_original_car_gate.hpp"
#include <cassert>
#include <cstring>
using namespace OutRunVR::DinoSidecar;

static ExternalStereoMeshReceipt Receipt(bool left,bool right,bool restored,
    bool distinct,bool rightGpu=false,unsigned reports=1u)
{
    ExternalStereoMeshReceipt r{};
    r.expectedPose=33;
    r.observedPose=33;
    r.leftSucceeded=left;
    r.rightSucceeded=right;
    r.stateRestored=restored;
    r.geometryStereo=distinct;
    r.rightDrawFailed=rightGpu;
    r.reports=reports;
    return r;
}
int main() {
    MeshDrawReceipt notAttempted{};
    assert(notAttempted.lastEyeFailure==ExternalEyeFailure::NotAttempted);
    assert(std::strcmp(ExternalEyeFailureName(notAttempted.lastEyeFailure),
                       "NOT_ATTEMPTED")==0);
    auto r=Receipt(true,true,true,true);
    assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::None);
    assert(std::strcmp(ExternalEyeFailureName(ClassifyExternalEyeFailure(r)),
                       "STEREO_OK")==0);
    r.reports=0;
    assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::MissingReport);
    r.reports=2;
    assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::MultipleReports);
    r.rightDrawFailed=true;
    assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::RightGpuFailed);
    r=Receipt(true,true,true,true);
    r.observedPose=34;
    assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::PoseMismatch);
    r=Receipt(false,true,true,true);
    assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::LeftFailed);
    r=Receipt(true,false,true,true);
    assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::RightNotVerified);
    r=Receipt(true,true,false,true);
    assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::RestoreFailed);
    r=Receipt(true,true,true,false);
    assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::IdenticalEyeGeometry);
    assert(std::strcmp(ExternalEyeFailureName(ClassifyExternalEyeFailure(r)),
                       "MONO_EYE_MATRICES")==0);
}
