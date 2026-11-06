#pragma once
// Pure admission logic for replacing ONLY the original playable Dino player
// display callback (PC retail 0x49F3E0). Never suppress a game callback just
// because an external OVC file exists: a successful physical draw is required.
#include <cstdint>
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
    bool drawSucceeded=false;
    bool stateRestored=false;
};
enum class OriginalCarRoute : unsigned char {
    OriginalFallback,ExternalComplete,ExternalPartial
};
inline OriginalCarRoute ChooseOriginalCarRoute(
    const OriginalCarGate& gate,const MeshDrawReceipt& receipt) noexcept
{
    if(!CanReplaceOriginalCar(gate) ||
       receipt.expectedMeshes==0 ||
       receipt.submittedMeshes>receipt.expectedMeshes ||
       receipt.submittedMeshes==0)
        return OriginalCarRoute::OriginalFallback;
    if(receipt.drawSucceeded && receipt.stateRestored &&
       receipt.submittedMeshes==receipt.expectedMeshes)
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
