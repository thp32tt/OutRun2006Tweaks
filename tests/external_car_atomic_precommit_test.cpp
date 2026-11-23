#include <cassert>
#include <cstdint>
#include <initializer_list>
#include "../src/vr/game/external_car_atomic_precommit.hpp"
#include "../src/vr/game/dino_external_original_car_gate.hpp"
using namespace OutRunVR::DinoSidecar;
static OriginalCarGate Admit() {
    OriginalCarGate g{};
    g.optedIn=g.ownedPlayer=g.gameplay=g.cockpitModeOne=true;
    g.validStereo=g.nativeFrameActive=g.deviceReady=true;
    g.ticketEpoch=g.liveEpoch=g.ticketPose=g.livePose=77;
    return g;
}
// Simulates the native R7 pre-first-DIP guard; the fail-close policy must
// prevent BOTH draws even if a later RIGHT GPU injection would fail.
struct FakeR7LiveEye {
    unsigned left=0,right=0;
    bool injectRightFailure=false;
    bool TryDrawExternal() noexcept {
        if (!MaySubmitExternalCarLiveEye()) return false;
        ++left;
        if(injectRightFailure) return false;
        ++right;
        return true;
    }
};
int main() {
    static_assert(!MaySubmitExternalCarLiveEye(),
        "Live-eye R7 external raster cannot be enabled without atomic staging");
    const auto admitted=Admit();
    for(unsigned slot=0;slot<16;++slot) {
        for(bool injectAfterLeft: {false,true}) {
            FakeR7LiveEye gpu{};
            gpu.injectRightFailure=injectAfterLeft;
            assert(!gpu.TryDrawExternal());
            assert(gpu.left==0 && gpu.right==0); // pre-raster fallback
            MeshDrawReceipt noRaster{};
            noRaster.expectedMeshes=2;
            noRaster.attemptedMeshes=1; // scoped DIP rejected before GPU
            noRaster.stateRestored=true; // game D3DSBT_ALL Apply succeeded
            assert(ChooseOriginalCarRoute(admitted,noRaster)==
                   OriginalCarRoute::OriginalFallback);
        }
    }
    // The pure staging contract is deliberately independent from the
    // disabled runtime backend. A valid hypothetical pair is READY only
    // when the *entire* car and both isolated color/depth eyes are ready.
    ExternalCarAtomicStageProof stage{};
    stage.wholeVehiclePrepared=stage.leftColorIsolated=
        stage.rightColorIsolated=stage.leftDepthIsolated=
        stage.rightDepthIsolated=stage.sameFrameAndPose=
        stage.gpuStateRestorable=stage.oneAtomicPairPublish=
        stage.leftStageSucceeded=stage.rightStageSucceeded=true;
    assert(stage.ReadyToCommit());
    auto broken=stage;
    broken.rightStageSucceeded=false; // RIGHT GPU fail AFTER LEFT staged
    assert(!broken.ReadyToCommit());
    broken=stage;broken.partialMeshFailure=true;
    assert(!broken.ReadyToCommit()); // mid-model mesh failure
    broken=stage;broken.resetOrDeviceLost=true;
    assert(!broken.ReadyToCommit()); // device Reset/ResetEx during stage
    broken=stage;broken.gpuStateRestorable=false;
    assert(!broken.ReadyToCommit()); // failed state block restore
    broken=stage;broken.oneAtomicPairPublish=false;
    assert(!broken.ReadyToCommit()); // two sequential StretchRect not atomic
    broken=stage;broken.leftDepthIsolated=false;
    assert(!broken.ReadyToCommit()); // live scene ZWrite not isolated
    broken=stage;broken.sameFrameAndPose=false;
    assert(!broken.ReadyToCommit()); // stale frame/eye
    broken=stage;broken.wholeVehiclePrepared=false;
    assert(!broken.ReadyToCommit()); // partial vehicle is not a transaction
    broken=stage;broken.leftStageSucceeded=false;
    assert(!broken.ReadyToCommit()); // LEFT staged failure
    // If a future developer removes the pre-raster guard, partial failure
    // cannot become OriginalFallback merely from a failed HRESULT.
    MeshDrawReceipt partial{};
    partial.possiblySubmitted=true;
    partial.expectedMeshes=2;
    partial.attemptedMeshes=1;
    partial.submittedMeshes=0;
    partial.stateRestored=true;
    assert(ChooseOriginalCarRoute(admitted,partial)==
           OriginalCarRoute::ExternalPartial);
    partial.possiblySubmitted=false;
    partial.stateMayBeDirty=true;
    assert(ChooseOriginalCarRoute(admitted,partial)==
           OriginalCarRoute::ExternalPartial);
}
