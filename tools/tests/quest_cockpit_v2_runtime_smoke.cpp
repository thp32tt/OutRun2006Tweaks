#include "../../src/vr/game/quest_cockpit_v2_runtime.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
using namespace OutRunVR::QuestCockpitV2;

static bool Approx(float x,float y) {return std::fabs(x-y)<1.0e-4f;}
static FrameInput Good() {
    FrameInput x{};
    x.nativeGameFrame=12;x.xrPoseSequence=32;x.xrSpaceGeneration=3;
    x.playerIdentity=0x1234;x.cameraMode=1;
    x.optionRequested=x.gameplay=x.worldPass=true;
    x.originalPlayerEventVerified=x.stereoAndPositionValid=true;
    x.matrixB0=Identity;x.matrixF0=Identity;
    return x;
}
int main() {
    Matrix corrected{};
    assert(ComputeBodyCorrection(Identity,Identity,corrected));
    for(int i=0;i<3;++i) assert(Approx(corrected[i*4+i],-1.f));
    assert(Approx(corrected[15],1.f));
    Matrix a=Identity,b=Identity;
    a[12]=4.f;a[13]=2.f;a[14]=-3.f;
    b[12]=-2.f;b[13]=3.f;b[14]=1.f;
    assert(ComputeBodyCorrection(a,b,corrected));
    assert(Approx(corrected[12],10.f));
    assert(Approx(corrected[13],-3.f));
    assert(Approx(corrected[14],-7.f));
    auto original=corrected;
    a[3]=0.5f;assert(!ComputeBodyCorrection(a,b,corrected));
    assert(corrected==original);
    a[3]=0.f;a[0]=std::numeric_limits<float>::quiet_NaN();
    assert(!ComputeBodyCorrection(a,b,corrected));
    assert(corrected==original);
    a=Identity;
    FrameOwner o;
    auto f=Good();
    assert(o.Observe(f));
    const auto* snap=o.Snapshot();
    assert(snap && snap->nativeGameFrame==12 &&
           snap->playerIdentity==f.playerIdentity);
    assert(o.Observe(f)); // second eye: same exact native frame + HMD pose
    auto wrong=f;wrong.sceneEffect=true;
    assert(!o.Observe(wrong));
    assert(!o.Observe(f)); // irrevocable within frame
    f.nativeGameFrame++;
    assert(o.Observe(f));
    f.xrPoseSequence++;
    assert(!o.Observe(f)); // different eye pose in same frame
    f.nativeGameFrame++;
    assert(o.Observe(f));
    f.matrixB0[12]=1.f;assert(!o.Observe(f)); // player matrix mutated
    f.nativeGameFrame++;assert(o.Observe(f));
    f.playerIdentity=0xdead;assert(!o.Observe(f));
    f.nativeGameFrame++;assert(o.Observe(f));
    f.xrSpaceGeneration++;assert(!o.Observe(f)); // recenter invalidation
    f.nativeGameFrame++;assert(o.Observe(f));
    f.cameraMode=2;assert(!o.Observe(f));
    f.nativeGameFrame++;f.cameraMode=1;
    assert(o.Observe(f));
    auto missing=f; missing.originalPlayerEventVerified=false;
    missing.nativeGameFrame++;
    assert(!o.Observe(missing));
    assert(!o.Observe(f)); // prior native generation cannot resume safely
    o.Reset();assert(o.Snapshot()==nullptr);
    f=Good();f.nativeGameFrame=0;
    assert(!o.Observe(f)); // no guessed Present->game epoch
    f.nativeGameFrame=1;f.stereoAndPositionValid=false;
    assert(!o.Observe(f)); // orientation-only host never enables cockpit
    f.nativeGameFrame=2;f.stereoAndPositionValid=true;
    assert(o.Observe(f));
    Matrix scratch=b;
    try {
        ScopedRenderMatrixF0 transaction(scratch,true);
        assert(scratch==Identity);
        throw std::runtime_error("unwind");
    } catch (const std::runtime_error&) {}
    assert(scratch==b); // not persistent game physics mutation
    {ScopedRenderMatrixF0 off(scratch,false);assert(scratch==b);}
    assert(scratch==b);
    assert(MatrixFingerprint(Identity,b)!=MatrixFingerprint(b,b));
}
