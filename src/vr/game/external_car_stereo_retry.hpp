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
} // namespace OutRunVR::DinoSidecar
