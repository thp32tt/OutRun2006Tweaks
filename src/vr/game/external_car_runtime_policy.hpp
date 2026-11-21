#pragma once
// Verified release-compatibility gates; pure C++17, no game/device reads.
namespace OutRunVR::DinoSidecar {
constexpr bool UseExternalSuspensionSmoothing(bool actualF50,
                                               bool requested) noexcept {
    return actualF50 && requested;
}
constexpr bool PermitGenericSidecar(bool selected,
                                    bool fixedFunctionStereoA_B,
                                    bool explicitNativeCallbackReplacement) noexcept {
    return selected && fixedFunctionStereoA_B &&
           explicitNativeCallbackReplacement;
}
static_assert(UseExternalSuspensionSmoothing(true,true));
static_assert(!UseExternalSuspensionSmoothing(false,true));
static_assert(!PermitGenericSidecar(true,false,true));
static_assert(!PermitGenericSidecar(true,true,false));
static_assert(PermitGenericSidecar(true,true,true));
}
