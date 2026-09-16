#include "vr/runtime_eligibility.hpp"

#include <cassert>

int main()
{
    using namespace OutRunVR::RuntimeEligibility;

    MarkSafetyOverlayUnavailable();
    assert(!SafetyOverlayReady.load());
    assert(!HostFresh.load());
    assert(!StereoAllowed.load());
    assert(RecoveryPending.load());
    assert(!MayInjectStereo());

    // Host freshness alone must never reopen stereo after a stall.
    ObserveFreshHost();
    assert(HostFresh.load());
    assert(!MayInjectStereo());

    // A baseline observed before the final safety overlay is installed is not
    // authoritative and therefore may not reopen stereo.
    BaselineVerified();
    assert(!MayInjectStereo());

    MarkSafetyOverlayInstalled();
    assert(SafetyOverlayReady.load());
    assert(!HostFresh.load());
    assert(RecoveryPending.load());
    assert(!MayInjectStereo());

    ObserveFreshHost();
    assert(!MayInjectStereo());
    BaselineVerified();
    assert(MayInjectStereo());

    // Host death immediately closes the gate and recovery again requires both
    // a fresh host observation and a new baseline.
    FailClosed();
    assert(!MayInjectStereo());
    ObserveFreshHost();
    assert(!MayInjectStereo());
    BaselineVerified();
    assert(MayInjectStereo());

    std::atomic<InstallState> state{ InstallState::Pending };
    assert(!IsReady(state));
    assert(!IsFailed(state));
    state.store(InstallState::Ready);
    assert(IsReady(state));
    state.store(InstallState::Failed);
    assert(IsFailed(state));
    return 0;
}
