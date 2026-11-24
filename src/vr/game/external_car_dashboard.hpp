#pragma once
// Portable dashboard animation contract for external OutRun cockpit sidecars.
// No D3D headers: parser/converter/runtime tests can share the exact math.
#include <algorithm>
#include <array>
#include <cstddef>
#include <cmath>
#include <cstdint>

namespace OutRunVR::DinoSidecar {

enum class DashboardKind : std::uint32_t {
    SpeedNeedle=1,
    RpmNeedle=2,
    GearVisible=3
};

struct DashboardTelemetry final {
    float speedKph=0.f;
    float rpm=0.f;
    std::uint32_t gear=0;
    bool valid=false;
};

inline DashboardTelemetry SanitizeDashboardTelemetry(
    float speedKph,std::uint32_t rpm,std::uint32_t gear) noexcept
{
    DashboardTelemetry t{};
    if(!std::isfinite(speedKph))return t;
    t.speedKph=std::clamp(speedKph,0.f,500.f);
    t.rpm=std::clamp(static_cast<float>(rpm),0.f,20000.f);
    t.gear=gear<=7u?gear:0u;
    t.valid=true;
    return t;
}

// Latches game telemetry once per native frame/player. Replayed stereo eyes
// therefore see exactly the same dashboard state even if render callbacks repeat.
class DashboardFrameLatch final {
    std::uint64_t epoch_=0;
    std::uintptr_t player_=0;
    DashboardTelemetry sample_{};
public:
    DashboardTelemetry Capture(std::uint64_t epoch,std::uintptr_t player,
                               float speedKph,std::uint32_t rpm,
                               std::uint32_t gear) noexcept
    {
        if(epoch!=0 && player!=0 && epoch==epoch_ && player==player_)
            return sample_;
        epoch_=epoch;player_=player;
        sample_=SanitizeDashboardTelemetry(speedKph,rpm,gear);
        return sample_;
    }
    void Reset() noexcept {epoch_=0;player_=0;sample_=DashboardTelemetry{};}
};

struct DashboardBinding final {
    std::uint32_t meshIndex=0;
    DashboardKind kind=DashboardKind::SpeedNeedle;
    std::uint32_t gear=0;
    std::array<float,3> pivot{{0.f,0.f,0.f}};
    std::array<float,3> axis{{0.f,0.f,1.f}};
    float inputMin=0.f,inputMax=1.f;
    float angleMinRad=0.f,angleMaxRad=0.f;
};

inline bool ValidDashboardBinding(
    const DashboardBinding& b,std::uint32_t meshCount) noexcept
{
    if(b.meshIndex>=meshCount)return false;
    const auto kind=static_cast<std::uint32_t>(b.kind);
    if(kind<static_cast<std::uint32_t>(DashboardKind::SpeedNeedle) ||
       kind>static_cast<std::uint32_t>(DashboardKind::GearVisible))
        return false;
    for(float v:b.pivot)
        if(!std::isfinite(v)||std::fabs(v)>10000.f)return false;
    if(b.kind==DashboardKind::GearVisible)
        return b.gear<=7u;
    float axisLen2=0.f;
    for(float v:b.axis) {
        if(!std::isfinite(v)||std::fabs(v)>1.001f)return false;
        axisLen2+=v*v;
    }
    if(axisLen2<0.9801f||axisLen2>1.0201f)return false;
    return std::isfinite(b.inputMin)&&std::isfinite(b.inputMax)&&
        b.inputMax>b.inputMin &&
        std::isfinite(b.angleMinRad)&&std::isfinite(b.angleMaxRad)&&
        std::fabs(b.angleMinRad)<=12.566371f&&
        std::fabs(b.angleMaxRad)<=12.566371f;
}

inline bool DashboardMeshVisible(
    const DashboardBinding* binding,const DashboardTelemetry& telemetry) noexcept
{
    return !binding || binding->kind!=DashboardKind::GearVisible ||
        (telemetry.valid && telemetry.gear==binding->gear);
}

// Two independently embedded needles, not one all-or-nothing indicator.
constexpr unsigned DashboardSpeedNeedleBit=1u;
constexpr unsigned DashboardRpmNeedleBit=2u;
constexpr unsigned DashboardBothNeedles=DashboardSpeedNeedleBit|DashboardRpmNeedleBit;
inline unsigned DashboardNeedleMask(
    const DashboardBinding* bindings,std::size_t count) noexcept
{
    unsigned mask=0u;
    if(!bindings)return mask;
    for(std::size_t i=0;i<count;++i) {
        if(bindings[i].kind==DashboardKind::SpeedNeedle)
            mask|=DashboardSpeedNeedleBit;
        else if(bindings[i].kind==DashboardKind::RpmNeedle)
            mask|=DashboardRpmNeedleBit;
    }
    return mask;
}
inline bool DashboardOverlayMeshVisible(
    const DashboardBinding* binding,const DashboardTelemetry& telemetry,
    unsigned embeddedMask) noexcept
{
    // Both needles embedded: gear-only, suppress redundant unbound housing.
    if(embeddedMask==DashboardBothNeedles &&
       (!binding || binding->kind!=DashboardKind::GearVisible))
        return false;
    if(binding) {
        if(binding->kind==DashboardKind::SpeedNeedle &&
           (embeddedMask&DashboardSpeedNeedleBit))return false;
        if(binding->kind==DashboardKind::RpmNeedle &&
           (embeddedMask&DashboardRpmNeedleBit))return false;
    }
    return DashboardMeshVisible(binding,telemetry);
}

inline float DashboardAngle(
    const DashboardBinding& binding,const DashboardTelemetry& telemetry) noexcept
{
    if(!telemetry.valid || binding.kind==DashboardKind::GearVisible)return 0.f;
    const float value=binding.kind==DashboardKind::SpeedNeedle ?
        telemetry.speedKph:telemetry.rpm;
    // Every finite float calibration accepted by the OVC parser must
    // interpolate without float overflow (e.g. -FLT_MAX to +FLT_MAX).
    const double lo=binding.inputMin,hi=binding.inputMax;
    if(!std::isfinite(value) || !std::isfinite(lo) ||
       !std::isfinite(hi) || !(hi>lo))return 0.f;
    const double u=std::clamp((static_cast<double>(value)-lo)/
        (hi-lo),0.0,1.0);
    return static_cast<float>(binding.angleMinRad+
        (static_cast<double>(binding.angleMaxRad)-binding.angleMinRad)*u);
}

using DashboardMatrix=std::array<float,16>;

inline DashboardMatrix DashboardIdentity() noexcept {
    return DashboardMatrix{{1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1}};
}

inline DashboardMatrix DashboardMultiply(
    const DashboardMatrix& a,const DashboardMatrix& b) noexcept
{
    DashboardMatrix r{};
    for(unsigned row=0;row<4;++row)
        for(unsigned col=0;col<4;++col)
            for(unsigned k=0;k<4;++k)
                r[row*4+col]+=a[row*4+k]*b[k*4+col];
    return r;
}

inline DashboardMatrix DashboardLocalRotation(
    const DashboardBinding& b,const DashboardTelemetry& t) noexcept
{
    const float angle=DashboardAngle(b,t);
    if(!std::isfinite(angle) || std::fabs(angle)<1e-8f)
        return DashboardIdentity();
    // ValidDashboardBinding deliberately accepts small axis length errors
    // from exported assets. Rodrigues requires a unit axis: otherwise the
    // needle scales/shears and changes length instead of rotating rigidly.
    const float len2=b.axis[0]*b.axis[0]+b.axis[1]*b.axis[1]+b.axis[2]*b.axis[2];
    if(!std::isfinite(len2) || len2<0.9801f || len2>1.0201f)
        return DashboardIdentity();
    const float invLen=1.f/std::sqrt(len2);
    const float x=b.axis[0]*invLen,y=b.axis[1]*invLen,z=b.axis[2]*invLen;
    const float c=std::cos(angle),s=std::sin(angle),q=1.f-c;
    // Row-vector Rodrigues matrix (D3D9/D3DX convention).
    DashboardMatrix r{{q*x*x+c,   q*x*y+s*z, q*x*z-s*y, 0.f,
                       q*x*y-s*z, q*y*y+c,   q*y*z+s*x, 0.f,
                       q*x*z+s*y, q*y*z-s*x, q*z*z+c,   0.f,
                       0.f,0.f,0.f,1.f}};
    DashboardMatrix toOrigin=DashboardIdentity();
    toOrigin[12]=-b.pivot[0];toOrigin[13]=-b.pivot[1];toOrigin[14]=-b.pivot[2];
    DashboardMatrix fromOrigin=DashboardIdentity();
    fromOrigin[12]=b.pivot[0];fromOrigin[13]=b.pivot[1];fromOrigin[14]=b.pivot[2];
    return DashboardMultiply(DashboardMultiply(toOrigin,r),fromOrigin);
}

inline DashboardMatrix DashboardWorldMatrix(
    const DashboardMatrix& baseWorld,const DashboardBinding* binding,
    const DashboardTelemetry& telemetry) noexcept
{
    if(!binding || binding->kind==DashboardKind::GearVisible)
        return baseWorld;
    return DashboardMultiply(DashboardLocalRotation(*binding,telemetry),baseWorld);
}

} // namespace OutRunVR::DinoSidecar