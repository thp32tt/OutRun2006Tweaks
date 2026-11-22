// Ferrari 16-car canonical/tuned alias, replacement and recovery contracts.
// Portable pure logic only: real OVC bytes, Direct3D and Quest3 are NOT tested.
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cwchar>
#include <iostream>
#include "../src/vr/game/external_car_selection.hpp"
#include "../src/vr/game/external_car_ground.hpp"
#include "../src/vr/game/dino_external_sidecar.hpp"
#include "../src/vr/game/dino_external_original_car_gate.hpp"
using namespace OutRunVR::DinoSidecar;

int main() {
    std::array<bool,30> canonical{};
    unsigned unique=0;
    // All thirty retail IDs resolve to precisely sixteen model identities.
    for(unsigned id=0;id<30;id++) {
        const auto slot=CanonicalFerrariExternalCarId(
            static_cast<unsigned char>(id));
        assert(slot<30 && IsFerrari16CanonicalCarId(slot));
        if(!canonical[slot]) {canonical[slot]=true;++unique;}
        assert(MatchesFerrariSelection(static_cast<unsigned char>(id),-1));
        assert(MatchesFerrariSelection(static_cast<unsigned char>(id),slot));
        assert(MatchesFerrariSelection(static_cast<unsigned char>(slot),
                                       static_cast<int>(id)));
        // A tuned/base pair must not upload another large OVC GPU resource.
        assert(CanonicalFerrariExternalCarId(
            static_cast<unsigned char>(id))==slot);
        const auto* fallback=LegacyFerrariCarSuffix(
            static_cast<unsigned char>(id));
        if(slot==7)
            assert(fallback && std::wcscmp(fallback,
                                           L"ExternalCars\\288gto.ovc")==0);
        else if(slot==11)
            assert(fallback && std::wcscmp(fallback,
                                           L"ExternalCars\\f40.ovc")==0);
        else
            assert(fallback==nullptr);
    }
    assert(unique==16);
    for(unsigned id=0;id<30;id++)
        assert(canonical[id]==(id<=14 || id==28));
    assert(CanonicalFerrariExternalCarId(15)==0);
    assert(CanonicalFerrariExternalCarId(27)==12);
    assert(CanonicalFerrariExternalCarId(28)==28);
    assert(CanonicalFerrariExternalCarId(29)==14);
    for(unsigned id=30;id<=255;id++)
        assert(!MatchesFerrariSelection(static_cast<unsigned char>(id),-1));

    Gate admission{};
    admission.optIn=true;admission.vr=true;admission.seat=true;
    admission.gameplay=true;admission.stereo=true;admission.playerDraw=true;
    admission.deviceReady=true;admission.allowOtherFerrari=true;
    for(unsigned id=0;id<30;id++) {
        admission.carId=static_cast<unsigned char>(id);
        admission.expectedCarId=static_cast<unsigned char>(id);
        assert(Eligible(admission));
        admission.expectedCarId=static_cast<unsigned char>((id+1)%30);
        assert(!Eligible(admission));
        admission.expectedCarId=static_cast<unsigned char>(id);
        float applied=0;
        // Every car uses its own local floor envelope, not F50's old lift.
        assert(ComputeExternalFloorLift(0.f,0.f,applied));
        assert(std::fabs(applied-0.035f)<1e-6f);
        assert(ComputeExternalFloorLift(0.f,-0.5f,applied));
        assert(std::fabs(applied-0.535f)<1e-6f);
        assert(!ComputeExternalFloorLift(0.f,-1.30f,applied));
        OriginalCarGate draw{};
        draw.optedIn=true;draw.ownedPlayer=true;draw.gameplay=true;
        draw.cockpitModeOne=true;draw.validStereo=true;
        draw.nativeFrameActive=true;draw.deviceReady=true;
        draw.ticketEpoch=id+1;draw.liveEpoch=id+1;
        draw.ticketPose=100+id;draw.livePose=100+id;
        assert(CanReplaceOriginalCar(draw));
        MeshDrawReceipt receipt{};
        receipt.expectedMeshes=32+id;
        assert(ChooseOriginalCarRoute(draw,receipt)==
               OriginalCarRoute::OriginalFallback);
        receipt.submittedMeshes=receipt.expectedMeshes;
        receipt.drawSucceeded=true;receipt.stateRestored=true;
        assert(ChooseOriginalCarRoute(draw,receipt)==
               OriginalCarRoute::ExternalComplete);
        receipt.submittedMeshes=1;
        assert(ChooseOriginalCarRoute(draw,receipt)==
               OriginalCarRoute::ExternalPartial);
        draw.livePose++;
        assert(!CanReplaceOriginalCar(draw));
        DashboardFrameLatch latch;
        const auto a=latch.Capture(id+1,id+100,80.f+id,4000+id,3);
        const auto b=latch.Capture(id+1,id+100,170.f,8000,5);
        assert(a.valid && b.valid && a.speedKph==b.speedKph &&
               a.rpm==b.rpm && a.gear==b.gear);
    }
    admission.carId=30;admission.expectedCarId=30;
    assert(!Eligible(admission));
    admission.carId=255;admission.expectedCarId=255;
    assert(!Eligible(admission));
    // An isolated asset upload failure must quarantine only until a device
    // reset or a genuinely different device, never reallocate every eye.
    GpuRetryPolicy retry{};
    int devices[2]={1,2};
    assert(retry.CanAttempt(&devices[0]));
    retry.NoteFailure(&devices[0]);
    assert(!retry.CanAttempt(&devices[0]));
    assert(retry.CanAttempt(&devices[1]));
    retry.OnReset();
    assert(retry.CanAttempt(&devices[0]));
    std::cout<<"FERRARI16_MULTICAR_16_CANONICAL_30_RETAIL_PASS\\n";
    return 0;
}
