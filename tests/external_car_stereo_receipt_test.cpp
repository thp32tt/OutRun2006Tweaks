#include "../src/vr/game/external_car_stereo_receipt.hpp"
#include "../src/vr/game/dino_external_original_car_gate.hpp"
#include <cassert>
using namespace OutRunVR::DinoSidecar;

static OriginalCarGate Admitted() {
    OriginalCarGate gate{};
    gate.optedIn=gate.ownedPlayer=gate.gameplay=gate.cockpitModeOne=true;
    gate.validStereo=gate.nativeFrameActive=gate.deviceReady=true;
    gate.ticketEpoch=gate.liveEpoch=23;
    gate.ticketPose=gate.livePose=44;
    return gate;
}
int main() {
    ExternalStereoMeshReceipt r{};
    r.expectedPose=44;
    assert(!r.Complete());
    {
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(true,true,true,44,true);
        assert(r.Complete());
    }
    assert(ActiveExternalStereoMesh==nullptr);
    // Ordinary v0.03 game draws retain their original HRESULT, while scoped
    // external meshes need a complete physical binocular pair.
    assert(CanCompleteExternalStereoDraw(true,nullptr));
    assert(!CanCompleteExternalStereoDraw(false,nullptr));
    assert(CanCompleteExternalStereoDraw(true,&r));
    assert(!CanCompleteExternalStereoDraw(false,&r));
    r.rightSucceeded=false;
    assert(!CanCompleteExternalStereoDraw(true,&r)); // RIGHT missing
    r.rightSucceeded=true;
    r.geometryStereo=false;
    assert(!CanCompleteExternalStereoDraw(true,&r)); // doubled mono
    r.geometryStereo=true;
    r.stateRestored=false;
    assert(!CanCompleteExternalStereoDraw(true,&r)); // dirty D3D state
    r.stateRestored=true;
    r.rightDrawFailed=true;
    assert(!CanCompleteExternalStereoDraw(true,&r)); // inconsistent GPU fault
    r.rightDrawFailed=false;
    r.deviceRestoreFailed=true;
    assert(!CanCompleteExternalStereoDraw(true,&r)); // hidden restore fault
    r.deviceRestoreFailed=false;
    r.reports=2;
    assert(!CanCompleteExternalStereoDraw(true,&r)); // duplicate report
    // Inject each independent restore failure: projection restoration must
    // still execute after a failed view restore. Both success is required.
    for(unsigned mask=0;mask<4;++mask) {
        unsigned viewCalls=0,projectionCalls=0;
        const bool restored=RestoreExternalStereoTransformPair(
            [&]() { ++viewCalls; return (mask&1u)!=0; },
            [&]() { ++projectionCalls; return (mask&2u)!=0; });
        assert(viewCalls==1 && projectionCalls==1);
        assert(restored==(mask==3u));
        r={};r.expectedPose=44;
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalPreRasterRollback(restored);
        assert(r.reports==0 && !r.Complete());
        assert(CanFallbackAfterNoExternalRaster(r,0,0)==restored);
        assert(ClassifyExternalEyeFailure(r)==(restored ?
            ExternalEyeFailure::ProvenNoPhysicalDraw :
            ExternalEyeFailure::DeviceRestoreFailed));
        ProveExternalNoPhysicalDraw(); // later clean guard cannot erase fault
        assert(r.provedNoPhysicalDraw==restored);
        assert(r.deviceRestoreFailed==!restored);
    }
    // All 16 combinations of c64-c67 restore outcomes, including a
    // failing first/middle register: every independent restore must run.
    for(unsigned mask=0;mask<16;++mask) {
        unsigned calls=0;
        const bool restored=RestoreStereoWvpRegisters(4,[&](unsigned reg) {
            assert(reg==calls++);
            return (mask&(1u<<reg))!=0;
        });
        assert(calls==4 && restored==(mask==15u));
        r={};r.expectedPose=44;
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalPreRasterRollback(restored);
        assert(CanFallbackAfterNoExternalRaster(r,0,0)==restored);
        // Simulate a failed RIGHT GPU draw after a live LEFT draw. Even
        // complete WVP restoration cannot prove zero physical submission.
        RecordExternalStereoMeshPair(true,false,restored,44,true,true,!restored);
        assert(!r.Complete() && !CanFallbackAfterNoExternalRaster(r,0,0));
        assert(r.rightDrawFailed && r.deviceRestoreFailed==!restored);
    }
    // First-mesh proven no-DIP is safe; missing or late reports are not.
    r={};r.expectedPose=44;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        ProveExternalNoPhysicalDraw();
        assert(CanFallbackAfterNoExternalRaster(r,0,0));
        assert(!CanFallbackAfterNoExternalRaster(r,1,0));
        assert(!CanFallbackAfterNoExternalRaster(r,0,1));
        assert(ClassifyExternalEyeFailure(r)==ExternalEyeFailure::ProvenNoPhysicalDraw);
    }
    r={};r.expectedPose=44;
    assert(!CanFallbackAfterNoExternalRaster(r,0,0));
    {
        ScopedExternalStereoMeshReceipt scope(r);
        ProveExternalNoPhysicalDraw();
        RecordExternalStereoMeshPair(true,false,true,44,true,true);
        assert(!CanFallbackAfterNoExternalRaster(r,0,0));
        assert(r.reports==1 && !r.provedNoPhysicalDraw);
        ProveExternalNoPhysicalDraw();
        assert(!CanFallbackAfterNoExternalRaster(r,0,0));
    }
    r={};r.expectedPose=0;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        ProveExternalNoPhysicalDraw();
        assert(!CanFallbackAfterNoExternalRaster(r,0,0));
    }
    // The result of the cleared possiblySubmitted flag is actually used by
    // the original-car gate; after a successful outer StateBlock restoration,
    // the native model is allowed. Dirty state and any earlier DIP forbid it.
    MeshDrawReceipt noPixels{};
    noPixels.expectedMeshes=3;
    noPixels.attemptedMeshes=1;
    noPixels.stateRestored=true;
    assert(ChooseOriginalCarRoute(Admitted(),noPixels)==
           OriginalCarRoute::OriginalFallback);
    noPixels.stateMayBeDirty=true;
    assert(ChooseOriginalCarRoute(Admitted(),noPixels)==
           OriginalCarRoute::ExternalPartial);
    noPixels.stateMayBeDirty=false;
    noPixels.possiblySubmitted=true;
    assert(ChooseOriginalCarRoute(Admitted(),noPixels)==
           OriginalCarRoute::ExternalPartial);
    // RIGHT GPU failure is different from merely unproven stereo. It
    // requires hard device quarantine instead of just a soft cooldown.
    r={}; r.expectedPose=44;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(true,false,true,44,true,true);
        assert(!r.Complete());
        assert(r.rightDrawFailed);
    }
    r={}; r.expectedPose=44;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(true,false,true,44,true,false);
        assert(!r.Complete());
        assert(!r.rightDrawFailed);
    }
    // RIGHT eye state restore failed despite success HRESULT from both
    // physical Draw calls. Outer StateBlock success cannot mask this fault.
    r={}; r.expectedPose=44;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(true,true,false,44,true,false,true);
        assert(!r.Complete());
        assert(r.deviceRestoreFailed);
        assert(ClassifyExternalEyeFailure(r)==
               ExternalEyeFailure::DeviceRestoreFailed);
    }
    // Duplicate/nested physical reports preserve ALL previous failures.
    r={}; r.expectedPose=44;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(true,true,false,44,true,false,true);
        RecordExternalStereoMeshPair(true,true,true,44,true,false,false);
        assert(r.reports==2 && r.deviceRestoreFailed);
        assert(!r.stateRestored && !r.Complete());
        assert(ClassifyExternalEyeFailure(r)==
               ExternalEyeFailure::DeviceRestoreFailed);
    }
    // Two successful DIP executions without separate eye transforms
    // are NOT proven VR geometry; never replace stock with doubled mono.
    r={}; r.expectedPose=44;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(true,true,true,44,false);
        assert(!r.Complete());
    }

    for(int scenario=0;scenario!=4;++scenario) {
        r={};
        r.expectedPose=44;
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(scenario!=0,scenario!=1,
                                     scenario!=2,scenario==3?45:44,true);
        assert(!r.Complete());
    }
    r={}; r.expectedPose=44;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(true,true,true,44);
        RecordExternalStereoMeshPair(true,true,true,44);
    }
    assert(!r.Complete()); // multiple physical routes must not certify one DIP
    // A later success report must never clear an earlier RIGHT GPU failure.
    r={}; r.expectedPose=44;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(true,false,true,44,true,true);
        RecordExternalStereoMeshPair(true,true,true,44,true,false);
        assert(!r.Complete());
        assert(r.reports==2 && r.rightDrawFailed);
    }
    // Even a later bad report may not claim an earlier verified pair valid.
    r={}; r.expectedPose=44;
    {
        ScopedExternalStereoMeshReceipt scope(r);
        RecordExternalStereoMeshPair(true,true,true,44,true,false);
        RecordExternalStereoMeshPair(true,false,true,44,true,true);
        assert(!r.Complete());
        assert(r.rightDrawFailed);
    }
    MeshDrawReceipt mesh{};
    mesh.expectedMeshes=3;
    mesh.submittedMeshes=1;
    mesh.possiblySubmitted=true;
    assert(ChooseOriginalCarRoute(Admitted(),mesh)==OriginalCarRoute::ExternalPartial);
    mesh={};
    mesh.expectedMeshes=3;
    mesh.possiblySubmitted=true; // a failed DIP may still have rasterized LEFT
    assert(ChooseOriginalCarRoute(Admitted(),mesh)==OriginalCarRoute::ExternalPartial);
    mesh={};
    assert(ChooseOriginalCarRoute(Admitted(),mesh)==OriginalCarRoute::OriginalFallback);
    // State was changed by external submission setup, then could not be
    // restored. Even zero DIPs cannot justify calling stock with dirty state.
    mesh={};
    mesh.stateMayBeDirty=true;
    assert(ChooseOriginalCarRoute(Admitted(),mesh)==OriginalCarRoute::ExternalPartial);
    auto expiredStateGate=Admitted();
    ++expiredStateGate.liveEpoch;
    assert(ChooseOriginalCarRoute(expiredStateGate,mesh)==OriginalCarRoute::ExternalPartial);
    mesh={};
    mesh.expectedMeshes=3;
    mesh.submittedMeshes=3;
    mesh.verifiedStereoMeshes=3;
    mesh.attemptedMeshes=3;
    mesh.possiblySubmitted=true;
    mesh.drawSucceeded=mesh.stateRestored=true;
    assert(ChooseOriginalCarRoute(Admitted(),mesh)==OriginalCarRoute::ExternalComplete);
    mesh.verifiedStereoMeshes=2;
    assert(ChooseOriginalCarRoute(Admitted(),mesh)==OriginalCarRoute::ExternalPartial);
    mesh.verifiedStereoMeshes=3;
    mesh.attemptedMeshes=2;
    assert(ChooseOriginalCarRoute(Admitted(),mesh)==OriginalCarRoute::ExternalPartial);
    mesh.attemptedMeshes=3;
    auto staleGate=Admitted();
    ++staleGate.livePose;
    assert(ChooseOriginalCarRoute(staleGate,mesh)==OriginalCarRoute::ExternalPartial);
}
