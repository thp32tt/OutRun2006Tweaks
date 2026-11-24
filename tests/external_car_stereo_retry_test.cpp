#include "../src/vr/game/external_car_stereo_retry.hpp"
#include <cassert>
#include <initializer_list>
using OutRunVR::DinoSidecar::ExternalStereoRetryPolicy;
static void TestCaptureRetry() {
    using OutRunVR::DinoSidecar::CaptureExternalDrawState;
    // Model all canonical slots and create failure with/without an output,
    // a null-success output, capture failure and successful ownership.
    for(unsigned slot=0;slot<16;++slot) {
        (void)slot;
        for(unsigned mode=0;mode<5;++mode) {
            ExternalStereoRetryPolicy retry{};
            int block=1;
            int* state=nullptr;
            unsigned creates=0,captures=0,releases=0,draws=0;
            auto attempt=[&]() {
                if(!retry.AllowNativeAttempt())return false;
                if(!CaptureExternalDrawState(state,retry,
                    [&](int** out) noexcept {
                        ++creates;
                        if(mode==1 || mode>=3)*out=&block;
                        return mode>=2;
                    },
                    [&]() noexcept {++captures;return mode==4;},
                    [&]() noexcept {assert(state==&block);++releases;}))
                    return false;
                ++draws; // simulated raster only on successful capture
                return true;
            };
            assert(attempt()==(mode==4));
            assert(creates==1 && captures==(mode>=3?1u:0u));
            assert(releases==((mode==1 || mode==3)?1u:0u));
            assert(draws==(mode==4?1u:0u));
            if(mode==4) {
                assert(state==&block && retry.remaining==0);
                ++releases;state=nullptr; // caller owns successful capture
                assert(releases==1);
            } else {
                assert(!state);
                for(unsigned i=0;i<ExternalStereoRetryPolicy::CooldownDraws;++i)
                    assert(!attempt());
                assert(creates==1 && draws==0);
                assert(!attempt());
                assert(creates==2 && !state && draws==0);
                retry.OnSelectionOrDeviceReset();
                assert(!attempt() && creates==3);
            }
        }
    }
}
int main() {
    TestCaptureRetry();
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
