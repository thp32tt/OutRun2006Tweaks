#pragma once
// Verified release-compatibility gates; pure C++17, no game/device reads.
namespace OutRunVR::DinoSidecar {
constexpr bool UseExternalSuspensionSmoothing(bool actualF50,
                                               bool requested) noexcept {
    return actualF50 && requested;
}
// Separate opt-in probes: the production v0.03 path still has neither.
// An explicit PBR stereo probe may use R7's physical dual-eye receipt instead
// of the fixed-function A/B probe; no generic replacement is implicit.
constexpr bool PermitGenericSidecar(bool selected,
                                    bool fixedFunctionStereoA_B,
                                    bool pbrStereoDiagnostic,
                                    bool explicitNativeCallbackReplacement) noexcept {
    return selected && (fixedFunctionStereoA_B || pbrStereoDiagnostic) &&
           explicitNativeCallbackReplacement;
}
static_assert(UseExternalSuspensionSmoothing(true,true));
static_assert(!UseExternalSuspensionSmoothing(false,true));
static_assert(!PermitGenericSidecar(true,false,false,true));
static_assert(!PermitGenericSidecar(true,false,true,false));
static_assert(!PermitGenericSidecar(false,false,true,true));
static_assert(PermitGenericSidecar(true,true,false,true));
static_assert(PermitGenericSidecar(true,false,true,true));
}
