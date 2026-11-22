#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>
#include <stdexcept>
#include "../src/vr/game/external_car_selection.hpp"
#include "../src/vr/game/dino_external_sidecar.hpp"
#include "../src/vr/game/dino_external_original_car_gate.hpp"
#include "../src/vr/game/external_car_ground.hpp"
#include "../src/vr/game/external_car_dashboard.hpp"

using namespace OutRunVR::DinoSidecar;

static Gate GoodPrepare() {
    Gate g{};
    g.optIn=true;g.vr=true;g.seat=true;g.gameplay=true;
    g.stereo=true;g.playerDraw=true;g.deviceReady=true;
    g.stateRecording=false;g.allowOtherFerrari=true;
    g.carId=5u;g.expectedCarId=5u;return g;
}
static OriginalCarGate GoodDraw() {
    OriginalCarGate g{};
    g.optedIn=true;g.ownedPlayer=true;g.gameplay=true;
    g.cockpitModeOne=true;g.validStereo=true;
    g.nativeFrameActive=true;g.deviceReady=true;
    g.ticketEpoch=88;g.liveEpoch=88;g.ticketPose=99;g.livePose=99;
    return g;
}
static MeshDrawReceipt Receipt(std::uint32_t expected,std::uint32_t submitted,
                              bool ok=true,bool restored=true) {
    MeshDrawReceipt r{};r.expectedMeshes=expected;r.submittedMeshes=submitted;
    r.attemptedMeshes=submitted;
    r.verifiedStereoMeshes=ok?submitted:0u;
    r.possiblySubmitted=submitted!=0;
    r.drawSucceeded=ok;r.stateRestored=restored;return r;
}
static bool Near(float a,float b,float tol=.0001f) {return std::fabs(a-b)<=tol;}
static int total=0,passed=0;
static void Check(const char* id,const char* flow,bool ok) {
    ++total;
    if(ok){++passed;std::cout<<"PASS "<<id<<" "<<flow<<"\n";}
    else {std::cerr<<"FAIL "<<id<<" "<<flow<<"\n";throw std::runtime_error(id);}
}
int main(){
    // 01-10. Launcher selected id -> canonical candidate admission.
    Check("01","selected base 5",MatchesFerrariSelection(5u,5));
    Check("02","selected tuned 20",MatchesFerrariSelection(20u,5));
    Check("03","reverse tuned selector to base",MatchesFerrariSelection(5u,20));
    Check("04","f50 excluded from 575",!MatchesFerrariSelection(2u,5));
    Check("05","f430sp excluded",!MatchesFerrariSelection(28u,5));
    Check("06","f40 tuned excluded",!MatchesFerrariSelection(26u,5));
    Check("07","invalid requested -2 fails",!MatchesFerrariSelection(5u,-2));
    Check("08","requested 30 out of bounds",!MatchesFerrariSelection(5u,30));
    Check("09","player ID 30 out of bounds",!MatchesFerrariSelection(30u,-1));
    Check("10","legacy all-cars request -1",MatchesFerrariSelection(29u,-1));

    // 11-20. Real PrepareF50External -> DinoSidecar::Eligible gate variants.
    auto p=GoodPrepare();
    Check("11","575 owned player eligible",Eligible(p));
    p=GoodPrepare();p.optIn=false;
    Check("12","no opt-in rejected",!Eligible(p));
    p=GoodPrepare();p.vr=false;
    Check("13","2D path rejected",!Eligible(p));
    p=GoodPrepare();p.seat=false;
    Check("14","outside cockpit rejected",!Eligible(p));
    p=GoodPrepare();p.gameplay=false;
    Check("15","menu state rejected",!Eligible(p));
    p=GoodPrepare();p.stereo=false;
    Check("16","invalid XR stereo rejected",!Eligible(p));
    p=GoodPrepare();p.playerDraw=false;
    Check("17","not player draw rejected",!Eligible(p));
    p=GoodPrepare();p.deviceReady=false;
    Check("18","no D3D device rejected",!Eligible(p));
    p=GoodPrepare();p.stateRecording=true;
    Check("19","D3D recording rejected",!Eligible(p));
    p=GoodPrepare();p.expectedCarId=20u;
    Check("20","wrong ticket car identity rejected",!Eligible(p));

    // 21-30. DrawPreparedF50External -> CanReplaceOriginalCar gates.
    auto d=GoodDraw();
    Check("21","valid epoch and pose can replace",CanReplaceOriginalCar(d));
    d=GoodDraw();d.optedIn=false;
    Check("22","opt-out not replace",!CanReplaceOriginalCar(d));
    d=GoodDraw();d.ownedPlayer=false;
    Check("23","rival player not replace",!CanReplaceOriginalCar(d));
    d=GoodDraw();d.gameplay=false;
    Check("24","menu draw not replace",!CanReplaceOriginalCar(d));
    d=GoodDraw();d.cockpitModeOne=false;
    Check("25","external camera not replace",!CanReplaceOriginalCar(d));
    d=GoodDraw();d.validStereo=false;
    Check("26","eye pose invalid not replace",!CanReplaceOriginalCar(d));
    d=GoodDraw();d.nativeFrameActive=false;
    Check("27","inactive frame not replace",!CanReplaceOriginalCar(d));
    d=GoodDraw();d.deviceReady=false;
    Check("28","device null not replace",!CanReplaceOriginalCar(d));
    d=GoodDraw();d.liveEpoch=89;
    Check("29","stale native epoch not replace",!CanReplaceOriginalCar(d));
    d=GoodDraw();d.livePose=100;
    Check("30","different XR pose not replace",!CanReplaceOriginalCar(d));

    // 31-40. Actual external mesh receipt -> original fallback/quarantine.
    auto good=GoodDraw();
    Check("31","all mesh submitted complete",ChooseOriginalCarRoute(good,Receipt(78,78))==OriginalCarRoute::ExternalComplete);
    Check("32","zero expected fallback",ChooseOriginalCarRoute(good,Receipt(0,0))==OriginalCarRoute::OriginalFallback);
    Check("33","no triangle draw fallback",ChooseOriginalCarRoute(good,Receipt(78,0))==OriginalCarRoute::OriginalFallback);
    Check("34","partial GPU draw quarantined",ChooseOriginalCarRoute(good,Receipt(78,44,false,true))==OriginalCarRoute::ExternalPartial);
    Check("35","all submitted but D3D failure partial",ChooseOriginalCarRoute(good,Receipt(78,78,false,true))==OriginalCarRoute::ExternalPartial);
    Check("36","state restore failure partial",ChooseOriginalCarRoute(good,Receipt(78,78,true,false))==OriginalCarRoute::ExternalPartial);
    Check("37","over-submitted receipt avoids stock-car double draw",ChooseOriginalCarRoute(good,Receipt(78,79))==OriginalCarRoute::ExternalPartial);
    Check("38","one of many partial",ChooseOriginalCarRoute(good,Receipt(78,1))==OriginalCarRoute::ExternalPartial);
    d=GoodDraw();d.validStereo=false;
    Check("39","late draw gate failure avoids original body overdraw",ChooseOriginalCarRoute(d,Receipt(78,78))==OriginalCarRoute::ExternalPartial);
    Check("40","single drawable mesh complete",ChooseOriginalCarRoute(good,Receipt(1,1))==OriginalCarRoute::ExternalComplete);

    // 41-50. Geometry ground placement -> dashboard latch -> retry reset.
    float lift=0.f;
    bool ok=ComputeExternalFloorLift(0.f,0.f,lift);
    Check("41","native floor minimum 3.5cm",ok&&Near(lift,.035f));
    ok=ComputeExternalFloorLift(0.f,-.5f,lift);
    Check("42","native model floor lift",ok&&Near(lift,.535f));
    ok=ComputeExternalFloorLift(0.f,-1.20f,lift);
    Check("43","negative bound exact edge",ok&&Near(lift,1.235f));
    Check("44","out of envelope floor fail",!ComputeExternalFloorLift(0.f,-1.21f,lift));
    Check("45","sunk model with min>0.25 reject",!ComputeExternalFloorLift(0.f,.26f,lift));
    Check("46","nan floor reject",!ComputeExternalFloorLift(.1f,std::numeric_limits<float>::quiet_NaN(),lift));
    auto telemetry=SanitizeDashboardTelemetry(160.f,5000u,4u);
    Check("47","speed RPM and gear valid",telemetry.valid&&Near(telemetry.speedKph,160.f)&&Near(telemetry.rpm,5000.f)&&telemetry.gear==4);
    DashboardFrameLatch latch;
    auto first=latch.Capture(88u,0x1234u,100.f,4000u,3u);
    auto same=latch.Capture(88u,0x1234u,300.f,9000u,5u);
    Check("48","two eyes same frame dashboard latch",Near(first.speedKph,same.speedKph)&&Near(first.rpm,same.rpm)&&first.gear==same.gear);
    GpuRetryPolicy retry;
    int a=1,b=2;
    Check("49","GPU failed device is quarantined",retry.CanAttempt(&a)&&(retry.NoteFailure(&a),!retry.CanAttempt(&a)));
    retry.OnReset();
    Check("50","real device reset re-enables one retry",retry.CanAttempt(&a)&&retry.CanAttempt(&b));
    std::cout<<"FERRARI14_50_DISTINCT_PATHS "<<passed<<"/"<<total<<" PASS\n";
    return total==50&&passed==50?0:1;
}