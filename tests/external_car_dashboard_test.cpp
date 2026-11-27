#include "../src/vr/game/external_car_dashboard.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>

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

    // Body and overlay may both contain gear digits. Coverage is per gear:
    // prevent duplicate draws only for the same digit, never lose a digit
    // that exists exclusively in the optional overlay. Receipt counting
    // and actual mesh submission use the same visibility predicate.
    assert(DashboardGearMask(nullptr,0)==0u);
    assert(DashboardGearMask(&speed,1)==0u);
    DashboardBinding badGear=gear;
    badGear.gear=32u;
    assert(DashboardGearMask(&badGear,1)==0u);
    assert(DashboardGearMask(&gear,1)==(1u<<5));
    for(unsigned slot=0;slot<16;++slot) {
        (void)slot;
        for(unsigned bodyGear=0;bodyGear<8;++bodyGear) {
            DashboardBinding bodyDigit=gear;
            bodyDigit.gear=bodyGear;
            const unsigned mask=DashboardGearMask(&bodyDigit,1);
            for(unsigned liveGear=0;liveGear<8;++liveGear) {
                const auto sample=SanitizeDashboardTelemetry(60.f,4000u,liveGear);
                for(unsigned needleMask=0;needleMask<4;++needleMask) {
                    unsigned bodyDraws=DashboardMeshVisible(&bodyDigit,sample)?1u:0u;
                    unsigned overlayDraws=0u;
                    for(unsigned digit=0;digit<8;++digit) {
                        DashboardBinding overlayDigit=gear;
                        overlayDigit.gear=digit;
                        const bool visible=DashboardOverlayMeshVisible(
                            &overlayDigit,sample,needleMask,mask);
                        assert(visible==(digit==liveGear && digit!=bodyGear));
                        overlayDraws+=visible?1u:0u;
                    }
                    assert(bodyDraws+overlayDraws==1u);
                    assert(!DashboardOverlayMeshVisible(&bodyDigit,
                        invalidTelemetry,needleMask,mask));
                    assert(DashboardOverlayMeshVisible(&speed,sample,needleMask,mask)==
                        DashboardOverlayMeshVisible(&speed,sample,needleMask));
                    assert(DashboardOverlayMeshVisible(&rpm,sample,needleMask,mask)==
                        DashboardOverlayMeshVisible(&rpm,sample,needleMask));
                }
            }
        }
    }

    // Cover every needle and gear combination, including invalid telemetry.
    for(unsigned needles=0;needles<4;++needles)
        for(unsigned gears=0;gears<256;++gears)
            for(unsigned digit=0;digit<8;++digit){
                const auto sample=SanitizeDashboardTelemetry(50.f,3000u,digit);
                assert(DashboardCoverageComplete(needles,gears,sample)==
                    (needles==DashboardBothNeedles&&(gears&(1u<<digit))!=0u));
            }
    assert(!DashboardCoverageComplete(3u,255u,DashboardTelemetry{}));
    auto badSample=validGear;badSample.gear=32;
    assert(!DashboardCoverageComplete(3u,255u,badSample));
    // A tolerated exporter length error must not scale/shear a needle.
    // Compare every element to the same pivot rotation about a unit axis.
    for(const auto kind : {DashboardKind::SpeedNeedle,DashboardKind::RpmNeedle}) {
        DashboardBinding unit=pivot;
        unit.kind=kind;
        unit.axis={{0.6f,0.8f,0.f}};
        unit.pivot={{1.f,-2.f,3.f}};
        unit.angleMinRad=-halfPi;unit.angleMaxRad=halfPi;
        const auto sample=SanitizeDashboardTelemetry(1.f,1u,1u);
        const auto expected=DashboardLocalRotation(unit,sample);
        assert(ValidDashboardBinding(unit,3));
        for(float scale : {0.995f,1.f,1.005f}) {
            auto perturbed=unit;
            for(float& a:perturbed.axis)a*=scale;
            assert(ValidDashboardBinding(perturbed,3));
            const auto actual=DashboardLocalRotation(perturbed,sample);
            for(unsigned j=0;j<16;++j)assert(Near(actual[j],expected[j]));
            // Unit rows, perpendicular rows, and unchanged pivot.
            for(unsigned row=0;row<3;++row) {
                for(unsigned col=0;col<3;++col) {
                    float dot=0.f;
                    for(unsigned k=0;k<3;++k)
                        dot+=actual[4*row+k]*actual[4*col+k];
                    assert(Near(dot,row==col?1.f:0.f));
                }
                float point=actual[12+row];
                for(unsigned k=0;k<3;++k)point+=unit.pivot[k]*actual[4*k+row];
                assert(Near(point,unit.pivot[row]));
            }
        }
        // Negative: zero/out-of-tolerance axes never produce a bad matrix.
        for(float scale : {0.f,0.5f,1.1f}) {
            auto badAxis=unit;
            for(float& a:badAxis.axis)a*=scale;
            assert(!ValidDashboardBinding(badAxis,3));
            assert(DashboardLocalRotation(badAxis,sample)==DashboardIdentity());
        }
        // Valid, extreme finite float32 calibration previously overflowed
        // its denominator to infinity and returned the minimum angle.
        auto wide=unit;
        wide.inputMin=-(std::numeric_limits<float>::max)();
        wide.inputMax=(std::numeric_limits<float>::max)();
        assert(ValidDashboardBinding(wide,3));
        assert(Near(DashboardAngle(wide,sample),0.f));
        wide.inputMin=wide.inputMax;
        assert(!ValidDashboardBinding(wide,3));
        assert(DashboardAngle(wide,sample)==0.f);
    }

    speed.axis={{0.f,0.f,0.5f}};
    assert(!ValidDashboardBinding(speed,3));
    std::cout<<"EXTERNAL_DASHBOARD_V4_PASS\n";
}