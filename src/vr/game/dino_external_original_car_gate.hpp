#pragma once
// Pure admission logic for replacing ONLY the original playable Dino player
// display callback (PC retail 0x49F3E0). Never suppress a game callback just
// because an external OVC file exists: a successful physical draw is required.
#include <cstdint>
#include "external_car_stereo_receipt.hpp"
namespace OutRunVR::DinoSidecar {
struct OriginalCarGate final {
    bool optedIn=false,ownedPlayer=false,gameplay=false,cockpitModeOne=false;
    bool validStereo=false,nativeFrameActive=false,deviceReady=false;
    std::uint64_t ticketEpoch=0,liveEpoch=0;
    std::uint64_t ticketPose=0,livePose=0;
};
inline bool CanReplaceOriginalCar(const OriginalCarGate& gate) noexcept {
    return gate.optedIn && gate.ownedPlayer && gate.gameplay &&
        gate.cockpitModeOne && gate.validStereo && gate.nativeFrameActive &&
        gate.deviceReady && gate.ticketEpoch!=0 &&
        gate.ticketEpoch==gate.liveEpoch && gate.ticketPose!=0 &&
        gate.ticketPose==gate.livePose;
}
// A failed late mesh submit cannot be rolled back: the already rasterized
// sidecar triangles would overlap the full original native vehicle if the
// original 49F3E0 display callback were invoked. Never duplicate that car.
// A no-mesh/no-submit failure still restores the original complete vehicle.
struct MeshDrawReceipt final {
    std::uint32_t expectedMeshes=0;
    std::uint32_t submittedMeshes=0;
    std::uint32_t attemptedMeshes=0;
    std::uint32_t verifiedStereoMeshes=0;
    ExternalEyeFailure lastEyeFailure=ExternalEyeFailure::NotAttempted;
    unsigned lastEyeReports=0;
    // A failed API result may follow a successful LEFT-eye rasterization.
    bool possiblySubmitted=false;
    // StateBlock capture succeeded, but Apply later failed. The original
    // callback must not run with contaminated world/RT/texture states.
    bool stateMayBeDirty=false;
    bool drawSucceeded=false;
    bool stateRestored=false;
};
enum class OriginalCarRoute : unsigned char {
    OriginalFallback,ExternalComplete,ExternalPartial
};
inline OriginalCarRoute ChooseOriginalCarRoute(
    const OriginalCarGate& gate,const MeshDrawReceipt& receipt) noexcept
{
    // Never reintroduce the native body if the eligibility changed after
    // even a potentially rasterized LEFT eye. A late pose/epoch failure is
    // partial for this frame, regardless of the original pre-draw admission.
    if(!CanReplaceOriginalCar(gate))
        return (receipt.possiblySubmitted || receipt.submittedMeshes!=0 ||
                receipt.stateMayBeDirty)
            ? OriginalCarRoute::ExternalPartial
            : OriginalCarRoute::OriginalFallback;
    if(receipt.submittedMeshes==0 && !receipt.possiblySubmitted &&
       !receipt.stateMayBeDirty)
        return OriginalCarRoute::OriginalFallback;
    // No-overdraw safety: once any external triangle has been submitted,
    // its pixels cannot be removed from the current eye. An impossible
    // receipt count (zero expected or more submitted than expected) must
    // NEVER cause the stock player body to be drawn on top. Quarantine the
    // anomalous route for this frame instead of stacking two full vehicles.
    if(receipt.expectedMeshes==0 ||
       receipt.submittedMeshes>receipt.expectedMeshes)
        return OriginalCarRoute::ExternalPartial;
    if(receipt.drawSucceeded && receipt.stateRestored &&
       receipt.possiblySubmitted &&
       receipt.submittedMeshes==receipt.expectedMeshes &&
       receipt.attemptedMeshes==receipt.expectedMeshes &&
       receipt.verifiedStereoMeshes==receipt.expectedMeshes)
        return OriginalCarRoute::ExternalComplete;
    // At least one external mesh has already written to this frame. Suppress
    // the original *for this frame only*. Quarantine failed GPU resources so
    // subsequent frames can revert to original instead of repeatedly failing.
    return OriginalCarRoute::ExternalPartial;
}
inline bool SuppressOriginalCarAfterExternalDraw(
    const OriginalCarGate& gate, bool externalSubmittedAndStateRestored) noexcept
{
    return CanReplaceOriginalCar(gate) && externalSubmittedAndStateRestored;
}
} // namespace OutRunVR::DinoSidecar