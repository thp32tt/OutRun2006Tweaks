#pragma once
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
