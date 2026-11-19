#pragma once
// F50 external visual-only alignment. Never mutates gameplay physics matrices.
// Native frame epoch is the stereo pair key: both eyes receive identical
// filtered vertical placement; large terrain steps and car changes snap.
#include <cmath>
#include <cstdint>
#include <d3d9.h>

namespace OutRunVR::DinoSidecar {
class F50VisualPoseFilter final {
    std::uintptr_t car_=0;
    std::uint64_t epoch_=0;
    float stableY_=0.f;
    bool initialized_=false;
public:
    void Reset() noexcept {
        car_=0;epoch_=0;stableY_=0.f;initialized_=false;
    }
    void Apply(D3DMATRIX& world,std::uint64_t epoch,std::uintptr_t car,
               float localUp,bool stabilize) noexcept {
        if (!std::isfinite(localUp) || localUp < -0.25f || localUp > 1.f)
            localUp=0.f;
        const float rawY=world._42;
        if(stabilize && epoch && car && std::isfinite(rawY)) {
            if(!initialized_ || car_!=car) {
                stableY_=rawY;initialized_=true;
            } else if(epoch_!=epoch) {
                const float difference=rawY-stableY_;
                // Never smooth a real road height transition larger than 20 cm.
                if(std::fabs(difference)>0.20f)
                    stableY_=rawY;
                else
                    stableY_+=difference*0.45f;
            }
            car_=car;epoch_=epoch;
            world._42=stableY_;
        }
        // Local Y (up) is transformed by the car's current rotation.
        // Simply changing world._42 would incorrectly lift world-vertical
        // during bank/roll; this is a local model origin calibration.
        world._41+=localUp*world._21;
        world._42+=localUp*world._22;
        world._43+=localUp*world._23;
    }
};
inline F50VisualPoseFilter& GlobalF50PoseFilter() noexcept {
    static F50VisualPoseFilter filter;
    return filter;
}
} // namespace OutRunVR::DinoSidecar
