#include "../src/vr/game/external_car_stereo_retry.hpp"
#include <cassert>
using OutRunVR::DinoSidecar::ExternalStereoRetryPolicy;
int main() {
    ExternalStereoRetryPolicy p{};
    assert(p.AllowNativeAttempt());
    p.OnSoftStereoFailure();
    for(unsigned i=0;i<ExternalStereoRetryPolicy::CooldownDraws;++i)
        assert(!p.AllowNativeAttempt());
    assert(p.AllowNativeAttempt());
    p.OnSoftStereoFailure();
    p.OnSelectionOrDeviceReset();
    assert(p.AllowNativeAttempt());
    // Repeated independent stereo failures must not silently clear the gate.
    p.OnSoftStereoFailure();
    for(unsigned i=0;i<22;++i)
        assert(!p.AllowNativeAttempt());
    p.OnSoftStereoFailure();
    for(unsigned i=0;i<ExternalStereoRetryPolicy::CooldownDraws;++i)
        assert(!p.AllowNativeAttempt());
    assert(p.AllowNativeAttempt());
}
