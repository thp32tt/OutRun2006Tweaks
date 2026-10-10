#include "vr/runtime_eligibility.hpp"

// Release CI must retain checks: NDEBUG strips standard assert statements.
#define REQUIRE(condition) do { if (!(condition)) return __LINE__; } while (false)

int main()
{
    using namespace OutRunVR::RuntimeEligibility;

    MarkSafetyOverlayUnavailable();
    // Soft compositor suspension cannot invent a new fresh host after loss.
    ObserveSoftHostSuspend();
    REQUIRE(!SafetyOverlayReady.load());
    REQUIRE(!HostFresh.load());
    REQUIRE(!HostRenderable.load());
    REQUIRE(!StereoAllowed.load());
    REQUIRE(RecoveryPending.load());
    REQUIRE(!MayInjectStereo());

    // Host freshness alone must never reopen stereo after a stall.
    ObserveFreshHost();
    REQUIRE(HostFresh.load());
    REQUIRE(!MayInjectStereo());

    // A baseline observed before the final safety overlay is installed is not
    // authoritative and therefore may not reopen stereo.
    BaselineVerified();
    REQUIRE(!MayInjectStereo());

    MarkSafetyOverlayInstalled();
    ObserveSoftHostSuspend();
    REQUIRE(SafetyOverlayReady.load());
    REQUIRE(!HostFresh.load());
    REQUIRE(!HostRenderable.load());
    REQUIRE(RecoveryPending.load());
    REQUIRE(!MayInjectStereo());

    ObserveFreshHost();
    REQUIRE(!MayInjectStereo());
    BaselineVerified();
    REQUIRE(MayInjectStereo());

    // A verified soft shouldRender=false pause preserves the stereo source.
    // Only the host decides whether to submit a layer this OpenXR frame.
    ObserveSoftHostSuspend();
    REQUIRE(HostFresh.load());
    REQUIRE(HostRenderable.load());
    REQUIRE(StereoAllowed.load());
    REQUIRE(!RecoveryPending.load());
    REQUIRE(MayInjectStereo());
    ObserveFreshHost();
    REQUIRE(HostRenderable.load());
    REQUIRE(MayInjectStereo());

    // Host death immediately closes the gate. A later soft suspend must
    // not turn a disconnected host into a new baseline-ready host.
    FailClosed();
    ObserveSoftHostSuspend();
    REQUIRE(!HostFresh.load());
    REQUIRE(!HostRenderable.load());
    REQUIRE(!MayInjectStereo());
    BaselineVerified();
    REQUIRE(!MayInjectStereo());
    ObserveFreshHost();
    REQUIRE(!MayInjectStereo());
    BaselineVerified();
    REQUIRE(MayInjectStereo());

    // ResetEx/classic-state health is an independent persistent safety gate.
    // A later baseline must not reopen stereo until the compatibility owner
    // explicitly clears the block.
    SetExternalSafetyBlock(true);
    REQUIRE(ExternalSafetyBlock.load());
    REQUIRE(!StereoAllowed.load());
    REQUIRE(RecoveryPending.load());
    REQUIRE(!MayInjectStereo());
    ObserveSoftHostSuspend();
    REQUIRE(!MayInjectStereo());
    BaselineVerified();
    REQUIRE(!MayInjectStereo());

    SetExternalSafetyBlock(false);
    REQUIRE(!ExternalSafetyBlock.load());
    REQUIRE(!MayInjectStereo());
    BaselineVerified();
    REQUIRE(MayInjectStereo());

    std::atomic<InstallState> state{ InstallState::Pending };
    REQUIRE(!IsReady(state));
    REQUIRE(!IsFailed(state));
    state.store(InstallState::Ready);
    REQUIRE(IsReady(state));
    state.store(InstallState::Failed);
    REQUIRE(IsFailed(state));
    return 0;
}
