#pragma once
#include <cstdint>
// A failed per-eye draw does not imply damaged DDS, VB/IB or shader resources.
// Skip a bounded number of native callbacks (original PMT remains visible)
// before retrying the same installed sidecar. Actual GPU allocation or
// state-restore failures still use the existing hard device quarantine.
namespace OutRunVR::DinoSidecar {
struct ExternalStereoRetryPolicy final {
    static constexpr unsigned CooldownDraws=120u;
    unsigned remaining=0;
    void OnSoftStereoFailure() noexcept { remaining=CooldownDraws; }
    bool AllowNativeAttempt() noexcept {
        if(remaining!=0u) {
            --remaining;
            return false;
        }
        return true;
    }
    void OnSelectionOrDeviceReset() noexcept { remaining=0; }
};
// Private scene replay is expensive even if the final vehicle stage fails
// cleanly. Charge cooldown once per *distinct Present epoch*, not per eye,
// Clear, mesh, or native callback. The whole stock stereo pair remains live.
// Separate from legacy live-DIP retry: no private-eye failure quarantines
// validated assets. Selection/device reset immediately rearms the owner.
struct ExternalIsolatedRetryPolicy final {
    static constexpr unsigned CooldownFrames=120u;
    unsigned remaining=0;
    std::uint64_t epoch=0;
    bool admitted=false;
    bool AllowSeed(std::uint64_t next) noexcept {
        if(!next)return false;
        if(epoch==next)return admitted;
        epoch=next;
        admitted=remaining==0;
        if(remaining)--remaining;
        return admitted;
    }
    bool Admitted(std::uint64_t frame) const noexcept {return frame&&epoch==frame&&admitted;}
    void OnCleanStageFailure() noexcept {
        if(!epoch||!admitted)return;
        admitted=false;
        remaining=CooldownFrames;
    }
    void Reset() noexcept {*this={};}
};
// Creation/capture failure occurs before render state changes or raster.
// Retain the uploaded model, but avoid allocating another full state block
// on every native callback. A defensive release handles a nonnull output
// even on a failed create. Successful capture transfers ownership to caller.
template<class State,class Create,class Capture,class Release>
inline bool CaptureExternalDrawState(State*& state,
    ExternalStereoRetryPolicy& retry,Create create,Capture capture,
    Release release) noexcept {
    if(create(&state) && state && capture())return true;
    if(state) {release();state=nullptr;}
    retry.OnSoftStereoFailure();
    return false;
}
} // namespace OutRunVR::DinoSidecar
