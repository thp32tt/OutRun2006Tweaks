#include "../src/vr/game/external_car_dashboard.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>

using namespace OutRunVR::DinoSidecar;

static bool Near(float a,float b,float e=0.0001f) {
    return std::fabs(a-b)<=e;
}

int main() {
    auto t=SanitizeDashboardTelemetry(123.5f,8123u,4u);
    assert(t.valid && Near(t.speedKph,123.5f) && Near(t.rpm,8123.f) && t.gear==4u);
    auto clamped=SanitizeDashboardTelemetry(999.f,99999u,99u);
    assert(clamped.valid && Near(clamped.speedKph,500.f) &&
           Near(clamped.rpm,20000.f) && clamped.gear==0u);

    DashboardBinding speed{};
    speed.meshIndex=2;
    speed.kind=DashboardKind::SpeedNeedle;
    speed.axis={{0.f,0.f,1.f}};
    speed.inputMin=0.f;speed.inputMax=320.f;
    speed.angleMinRad=-1.f;speed.angleMaxRad=1.f;
    assert(ValidDashboardBinding(speed,3));
    assert(Near(DashboardAngle(speed,SanitizeDashboardTelemetry(160.f,0,1)),0.f));
    assert(Near(DashboardAngle(speed,SanitizeDashboardTelemetry(320.f,0,1)),1.f));

    DashboardBinding rpm=speed;
    rpm.kind=DashboardKind::RpmNeedle;
    rpm.inputMax=10000.f;
    rpm.angleMinRad=-2.f;rpm.angleMaxRad=2.f;
    assert(Near(DashboardAngle(rpm,SanitizeDashboardTelemetry(0.f,7500u,1u)),1.f));

    DashboardBinding gear{};
    gear.meshIndex=1;gear.kind=DashboardKind::GearVisible;gear.gear=5;
    assert(ValidDashboardBinding(gear,3));
    assert(DashboardMeshVisible(&gear,SanitizeDashboardTelemetry(0.f,0,5)));
    assert(!DashboardMeshVisible(&gear,SanitizeDashboardTelemetry(0.f,0,4)));

    // 90-degree Z rotation about pivot (1,0,0) keeps the pivot fixed.
    constexpr float halfPi=1.57079632679f;
    DashboardBinding pivot=speed;
    pivot.pivot={{1.f,0.f,0.f}};
    pivot.inputMax=1.f;pivot.angleMinRad=0.f;pivot.angleMaxRad=halfPi;
    const auto local=DashboardLocalRotation(
        pivot,SanitizeDashboardTelemetry(1.f,0,1));
    const float px=1.f*local[0]+0.f*local[4]+0.f*local[8]+local[12];
    const float py=1.f*local[1]+0.f*local[5]+0.f*local[9]+local[13];
    assert(Near(px,1.f) && Near(py,0.f));

    DashboardFrameLatch latch;
    auto first=latch.Capture(77u,0x1234u,100.f,6000u,3u);
    auto replay=latch.Capture(77u,0x1234u,200.f,9000u,6u);
    assert(Near(first.speedKph,replay.speedKph) &&
           Near(first.rpm,replay.rpm) && first.gear==replay.gear);
    auto next=latch.Capture(78u,0x1234u,200.f,9000u,6u);
    assert(Near(next.speedKph,200.f) && Near(next.rpm,9000.f) && next.gear==6u);

    // Positive and negative coverage: body speed only, RPM only, both, none.
    const std::array<DashboardBinding,2> embedded{{speed,rpm}};
    assert(DashboardNeedleMask(embedded.data(),embedded.size())==DashboardBothNeedles);
    assert(DashboardNeedleMask(&speed,1)==DashboardSpeedNeedleBit);
    assert(DashboardNeedleMask(&rpm,1)==DashboardRpmNeedleBit);
    assert(DashboardNeedleMask(nullptr,0)==0u);
    const auto validGear=SanitizeDashboardTelemetry(60.f,4000u,5u);
    assert(DashboardOverlayMeshVisible(&speed,validGear,0u));
    assert(DashboardOverlayMeshVisible(&rpm,validGear,0u));
    assert(DashboardOverlayMeshVisible(nullptr,validGear,0u));
    assert(!DashboardOverlayMeshVisible(&speed,validGear,DashboardSpeedNeedleBit));
    assert(DashboardOverlayMeshVisible(&rpm,validGear,DashboardSpeedNeedleBit));
    assert(DashboardOverlayMeshVisible(nullptr,validGear,DashboardSpeedNeedleBit));
    assert(DashboardOverlayMeshVisible(&speed,validGear,DashboardRpmNeedleBit));
    assert(!DashboardOverlayMeshVisible(&rpm,validGear,DashboardRpmNeedleBit));
    assert(!DashboardOverlayMeshVisible(&speed,validGear,DashboardBothNeedles));
    assert(!DashboardOverlayMeshVisible(&rpm,validGear,DashboardBothNeedles));
    assert(!DashboardOverlayMeshVisible(nullptr,validGear,DashboardBothNeedles));
    assert(DashboardOverlayMeshVisible(&gear,validGear,DashboardBothNeedles));
    const auto wrongGear=SanitizeDashboardTelemetry(60.f,4000u,4u);
    assert(!DashboardOverlayMeshVisible(&gear,wrongGear,DashboardBothNeedles));
    DashboardTelemetry invalidTelemetry{};
    assert(!DashboardOverlayMeshVisible(&gear,invalidTelemetry,0u));

    speed.axis={{0.f,0.f,0.5f}};
    assert(!ValidDashboardBinding(speed,3));
    std::cout<<"EXTERNAL_DASHBOARD_V4_PASS\n";
}