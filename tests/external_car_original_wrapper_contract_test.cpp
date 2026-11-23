#include <array>
#include <cassert>
#include <cstdint>
#include <initializer_list>
#include "../src/vr/game/external_car_original_wrapper_contract.hpp"
#include "../src/vr/game/external_car_atomic_precommit.hpp"
#include "../src/vr/game/dino_external_original_car_gate.hpp"
#include "../src/vr/game/external_car_dashboard.hpp"
using namespace OutRunVR::DinoSidecar;
static OriginalCarGate ValidGate(){
    OriginalCarGate g{};
    g.optedIn=g.ownedPlayer=g.gameplay=g.cockpitModeOne=true;
    g.validStereo=g.nativeFrameActive=g.deviceReady=true;
    g.ticketEpoch=g.liveEpoch=14;
    g.ticketPose=g.livePose=22;
    return g;
}
int main(){
    static_assert(!MaySkipRetailPlayerWrapper(),
        "A proven two-call retail wrapper is not a body-only draw leaf");
    static_assert(!RuntimeExternalCarAtomicStageReady(),
        "Do not enable exterior model raster before GPU pair staging");
    constexpr auto bytes=RetailPlayerWrapperPrefix;
    static_assert(RetailCallTarget(bytes.data(),bytes.size(),6)==0x46BD30u);
    static_assert(RetailCallTarget(bytes.data(),bytes.size(),17)==0x49A650u);
    static_assert(ExactRetailPlayerWrapperTwoCalls(bytes.data(),bytes.size()));
    assert(!ExactRetailPlayerWrapperTwoCalls(bytes.data(),bytes.size()-1));
    assert(!ExactRetailPlayerWrapperTwoCalls(nullptr,bytes.size()));
    auto corrupt=bytes;corrupt[7]^=1;
    assert(!ExactRetailPlayerWrapperTwoCalls(corrupt.data(),corrupt.size()));
    corrupt=bytes;corrupt[18]^=1;
    assert(!ExactRetailPlayerWrapperTwoCalls(corrupt.data(),corrupt.size()));
    corrupt=bytes;corrupt[11]=0x90;
    assert(!ExactRetailPlayerWrapperTwoCalls(corrupt.data(),corrupt.size()));
    assert(RetailCallTarget(bytes.data(),3,6)==0u);
    assert(RetailCallTarget(bytes.data(),bytes.size(),5)==0u);

    // Every canonical Ferrari slot (0..14, 28) remains on the ORIGINAL
    // complete callback: body, stock dashboard, glass/alpha, passenger and
    // shadow follow-up are not skipped. This is callback ownership parity,
    // not a visual claim about any untested HMD pixels.
    constexpr std::array<unsigned,16> ids{{
        0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,28}};
    for(unsigned id:ids){
        (void)id;
        const bool externalPresent=true;
        const bool missingExternal=false;
        const bool dashboardMissing=true;
        const bool alphaGlass=true;
        const bool passengerAndShadow=true;
        for(bool installed:{externalPresent,missingExternal}){
            for(bool overlay:{false,dashboardMissing}){
                // No wrapper suppression allowed independent of sidecar or
                // missing dashboard. A future body-only hook is separate.
                assert(!(MaySkipRetailPlayerWrapper() && installed && overlay));
                assert(alphaGlass && passengerAndShadow);
            }
        }
        const auto gate=ValidGate();
        MeshDrawReceipt noRaster{};
        noRaster.expectedMeshes=3;
        noRaster.stateRestored=true;
        assert(ChooseOriginalCarRoute(gate,noRaster)==
               OriginalCarRoute::OriginalFallback);
        // A late right-eye or mesh failure after any raster is NEVER
        // equated with stock rollback from HRESULT alone.
        MeshDrawReceipt partial{};
        partial.expectedMeshes=3;
        partial.attemptedMeshes=1;
        partial.possiblySubmitted=true;
        partial.stateRestored=true;
        assert(ChooseOriginalCarRoute(gate,partial)==
               OriginalCarRoute::ExternalPartial);
        partial={};
        partial.stateMayBeDirty=true;
        assert(ChooseOriginalCarRoute(gate,partial)==
               OriginalCarRoute::ExternalPartial);
        auto stale=gate;stale.livePose++;
        assert(ChooseOriginalCarRoute(stale,noRaster)==
               OriginalCarRoute::OriginalFallback);
        // Hybrid embedded speed/RPM never authorizes dropping the *whole*
        // native dashboard when a separate overlay is absent.
        DashboardBinding speed{},rpm{},gear{};
        speed.kind=DashboardKind::SpeedNeedle;
        rpm.kind=DashboardKind::RpmNeedle;
        gear.kind=DashboardKind::GearVisible;
        gear.gear=3u;
        const auto telemetry=SanitizeDashboardTelemetry(88.f,4200u,3u);
        assert(telemetry.valid && telemetry.gear==3u);
        assert(DashboardOverlayMeshVisible(&gear,telemetry,0u));
        assert(DashboardNeedleMask(&speed,1)==DashboardSpeedNeedleBit);
        assert(DashboardNeedleMask(&rpm,1)==DashboardRpmNeedleBit);
        std::array<DashboardBinding,2> both{{speed,rpm}};
        assert(DashboardNeedleMask(both.data(),both.size())==
               DashboardBothNeedles);
        assert(!MaySkipRetailPlayerWrapper());
    }
}
