#pragma once
// EXT16-007: external meshes must never touch either LIVE eye until a
// whole-vehicle, isolated two-eye staging backend can publish atomically.
// The existing R7 duplicate-DIP path draws LEFT live before RIGHT live.
// A successful HRESULT/receipt cannot undo those already-rasterized pixels.
namespace OutRunVR::DinoSidecar {
struct ExternalCarAtomicStageProof final {
    bool wholeVehiclePrepared=false;
    bool leftColorIsolated=false;
    bool rightColorIsolated=false;
    bool leftDepthIsolated=false;
    bool rightDepthIsolated=false;
    bool sameFrameAndPose=false;
    bool gpuStateRestorable=false;
    bool oneAtomicPairPublish=false;
    bool resetOrDeviceLost=false;
    bool leftStageSucceeded=false;
    bool rightStageSucceeded=false;
    bool partialMeshFailure=false;
    // This is a model of the future backend's precommit criteria, not
    // evidence that any D3D9/OpenXR backend currently implements them.
    constexpr bool ReadyToCommit() const noexcept {
        return wholeVehiclePrepared && leftColorIsolated &&
            rightColorIsolated && leftDepthIsolated && rightDepthIsolated &&
            sameFrameAndPose && gpuStateRestorable && oneAtomicPairPublish &&
            !resetOrDeviceLost && leftStageSucceeded &&
            rightStageSucceeded && !partialMeshFailure;
    }
};
// No OVC parse/upload should begin until the authorized callback has a
// whole-vehicle isolated stereo owner. DrawNativeScene's later guard is too
// late: SafeFloorLift can already launch a costly async private asset parse.
// Pure admission policy: this does NOT enable the unimplemented backend.
inline constexpr bool MayPrepareExternalCarAssets(
    bool ownerAuthorized, bool atomicStageReady) noexcept {
    return ownerAuthorized && atomicStageReady;
}
static_assert(!MayPrepareExternalCarAssets(true,false));
static_assert(!MayPrepareExternalCarAssets(false,true));
static_assert(MayPrepareExternalCarAssets(true,true));
// Only the two-eye staged renderer is permitted to turn this on after
// implementation and device/reset + GPU failure testing. This revision has
// NO SUCH BACKEND. Never accept live LEFT then live RIGHT as a substitute.
inline constexpr bool RuntimeExternalCarAtomicStageReady() noexcept {
    return false;
}
// Called BEFORE the first actual external DIP; false is a guaranteed
// no-raster decision. Ordinary world/player, menus and v0.03 stay untouched.
inline constexpr bool MaySubmitExternalCarLiveEye() noexcept {
    return RuntimeExternalCarAtomicStageReady();
}
} // namespace OutRunVR::DinoSidecar
