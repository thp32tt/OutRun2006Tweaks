// R26 + HUD FINAL OWNER ONLY. Included by stereo_renderer_r30_r26_safe.cpp.
// This source deliberately uses the existing R7/R9/R23/R26/R30 anonymous
// namespace owner, not any R29/R84 symbol or second physical D3D9 hook.
#include "../game/dino_external_d3d9.hpp"
#include "../game/dino_external_r26_bridge.hpp"
#include "../game/driver_seat_vehicle_scale.hpp"
#include <cmath>
#include <cstring>
#include <cstdint>

namespace OutRunVRStereo {
void R26DinoSidecarReleaseGpu() noexcept {
    OutRunVR::DinoSidecar::GlobalGpu().OnDeviceReset();
}

bool R26DinoSidecarTryDraw(IDirect3DDevice9* device,
    const D3DMATRIX& carWorld, const D3DMATRIX& gameView,
    const OutRunVR::DinoSidecar::Gate& gate,
    float worldScale, float depthScale, float vehicleScale) noexcept
{
    using OutRunVR::DinoSidecar::GlobalGpu;
    if (!OutRunVR::DinoSidecar::Eligible(gate) || !device ||
        !R30SafeStereoBase(device) || !StereoResourcesReady ||
        !BackBuffer || !RightEyeSurface || !RightEyeDepth ||
        !RightDepthSynchronized || !R9StereoSeeded ||
        !FrameHadWorldStereo || !FrameHadDuplicatedDraw ||
        FrameRightDrawFailed || FrameStereoIncomplete ||
        !TrackedDepthStencil || PresentEpoch == 0)
        return false;

    OutRunVRRenderer::LatchedStereoFrame stereo{};
    float projectionRaw[16]{}, headRaw[16]{};
    std::uint32_t headSequence=0;
    if (!OutRunVRRenderer::GetLatchedStereoFrame(stereo) ||
        !stereo.valid || stereo.poseSequence==0 ||
        !OutRunVRRenderer::GetRendererBaseProjection(projectionRaw) ||
        !OutRunVRRenderer::GetLatchedHeadInverse(headRaw,headSequence) ||
        headSequence!=stereo.poseSequence ||
        (FrameStereoPoseSequence && FrameStereoPoseSequence!=stereo.poseSequence) ||
        !std::isfinite(worldScale) || worldScale<=0.f ||
        !std::isfinite(depthScale) || depthScale<=0.f ||
        !std::isfinite(vehicleScale) ||
        vehicleScale<0.85f || vehicleScale>1.35f)
        return false;

    D3DMATRIX projection{},headInverse{},world=carWorld;
    std::memcpy(&projection,projectionRaw,sizeof(projection));
    std::memcpy(&headInverse,headRaw,sizeof(headInverse));
    if (!MatrixFinite(gameView) || !MatrixFinite(projection) ||
        !MatrixFinite(headInverse) || !MatrixFinite(world) ||
        !OutRunVR::DriverSeatVehicle::TryScaleModelBasis(world,vehicleScale))
        return false;

    D3DMATRIX eyeView[2]{},eyeProjection[2]{};
    for(int eye=0;eye<2;++eye) {
        // Same transform order and latched pose as R7 fixed-function world.
        const D3DMATRIX eyePose=MatrixFromQuaternionTranslation(
            stereo.eyeOrientation[eye],stereo.eyeOffset[eye],worldScale*depthScale);
        const D3DMATRIX eyeInverse=InverseRigid(eyePose);
        eyeView[eye]=MultiplyMatrix(MultiplyMatrix(gameView,headInverse),eyeInverse);
        eyeProjection[eye]=ProjectionFromFov(projection,stereo.eyeFov[eye]);
        if(!MatrixFinite(eyeView[eye])||!MatrixFinite(eyeProjection[eye]))
            return false;
    }

    // A game may call the player car's body state hook multiple times in one
    // Present. Draw cockpit once per device/Present, never once per mesh.
    static thread_local IDirect3DDevice9* lastDevice=nullptr;
    static thread_local std::uint64_t lastEpoch=~std::uint64_t{0};
    if (lastDevice==device && lastEpoch==PresentEpoch) return false;

    IDirect3DSurface9* savedRt=nullptr;
    IDirect3DSurface9* savedDepth=nullptr;
    D3DVIEWPORT9 savedViewport{};
    const bool acquired=SUCCEEDED(device->GetRenderTarget(0,&savedRt)) && savedRt &&
        SUCCEEDED(device->GetDepthStencilSurface(&savedDepth)) && savedDepth &&
        SUCCEEDED(device->GetViewport(&savedViewport)) && savedViewport.Width &&
        savedViewport.Height && savedRt==BackBuffer;
    if(!acquired){
        if(savedDepth)savedDepth->Release();
        if(savedRt)savedRt->Release();
        return false;
    }

    // Fail closed for missing/invalid .ovc with zero original-scene changes.
    {
        InternalPassScope internal;
        if(!GlobalGpu().EnsureResources(device)){
            savedDepth->Release();savedRt->Release();return false;
        }
    }

    lastDevice=device;
    lastEpoch=PresentEpoch;
    bool pair=false;
    HRESULT leftHr=E_FAIL,rightHr=E_FAIL;
    bool restored=false;
    {
        InternalPassScope internal;
        R9NoteStereoDrawWithoutMonoBackup();
        R9NoteMainDepthContentWrite();
        leftHr=GlobalGpu().DrawEye(device,world,eyeView[0],eyeProjection[0]);
        if(SUCCEEDED(leftHr)){
            rightHr=SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface);
            if(SUCCEEDED(rightHr))
                rightHr=SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth);
            if(SUCCEEDED(rightHr))
                rightHr=device->SetViewport(&savedViewport);
            if(SUCCEEDED(rightHr))
                rightHr=GlobalGpu().DrawEye(device,world,eyeView[1],eyeProjection[1]);
        }
        restored=RestoreRightPassState(device,savedRt,savedDepth,
                                       savedViewport,nullptr,false);
        // StateBlock::Apply bypasses render-state setter tracking, and can
        // be invoked while the right-eye target is active. Re-capture the
        // restored original raster and shader state before the game resumes.
        R22InvalidateAfterStateBlockApply(device);
        pair=SUCCEEDED(leftHr)&&SUCCEEDED(rightHr)&&restored;
    }
    savedDepth->Release();
    savedRt->Release();
    if(!pair){
        if(!restored)NoteRestoreFailure("Dino R26 sidecar restored state");
        R9Poison(FAILED(leftHr)?OutRunVR::StereoFailureLeftDrawFailed:
            OutRunVR::StereoFailureRightDrawFailed,
            "Dino R26 sidecar eye-pair",FAILED(leftHr)?leftHr:rightHr);
        FrameRightDrawFailed=true;
        R30ArmSafeFallback();
        return false;
    }
    FrameHadWorldStereo=true;
    FrameHadDuplicatedDraw=true;
    ++DuplicatedDraws;
    ++WorldStereoDraws;
    ++R30SafeTwoEyeDraws;
    if(FrameStereoPoseSequence==0) {
        FrameStereoPoseSequence=stereo.poseSequence;
        FrameStereoMetadata=stereo;
    }
    return true;
}
} // namespace OutRunVRStereo
