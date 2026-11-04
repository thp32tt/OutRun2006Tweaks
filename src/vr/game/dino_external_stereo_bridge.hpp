#pragma once
// Exact native player-car Draw owner calls this after the game has begun a scene.
// Sidecar never touches native model .sz, PMT, gameplay camera, physics or file IO.
#include "dino_external_d3d9.hpp"
#include "../core/r29_owner_api.hpp"
#include "../ipc/protocol.hpp"
#include "../game/driver_seat_vehicle_scale.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>

namespace OutRunVR::DinoSidecar {
inline GpuOwner& Gpu() noexcept {return GlobalGpu();}
struct ScopedInternal final {
    bool old;
    ScopedInternal() noexcept : old(OutRunVRStereo::R29OwnerExchangeInternalStereoPass(true)) {}
    ~ScopedInternal(){OutRunVRStereo::R29OwnerExchangeInternalStereoPass(old);}
};
inline bool TryDrawTwoEyes(IDirect3DDevice9* device,const D3DMATRIX& carWorld,
                          const D3DMATRIX& gameBaseView,
                          const Gate& gate,float worldScale,float depthScale,
                          float vehicleScale) noexcept {
    if(!Eligible(gate)||!device||
       !OutRunVRStereo::R29OwnerStableStereoBase(device)||
       !OutRunVRStereo::R29OwnerStereoWanted()||
       !OutRunVRStereo::R29OwnerTargetIsBackBuffer())
        return false;
    const auto* stereo=OutRunVRRenderer::GetLatchedStereoFrameView();
    if(!stereo || !stereo->valid || stereo->poseSequence==0)return false;
    const auto snapshot=OutRunVRStereo::R29OwnerCaptureFrameSnapshot();
    if(!snapshot.rightEyeSurface || !snapshot.rightEyeDepth ||
       !snapshot.rightDepthSynchronized ||
       snapshot.poseSequence!=stereo->poseSequence ||
       snapshot.rightDrawFailed || snapshot.stereoIncomplete)
        return false;
    float baseProjectionRaw[16]{},headInverseRaw[16]{};
    std::uint32_t headSequence=0;
    if(!OutRunVRRenderer::GetRendererBaseProjection(baseProjectionRaw) ||
       !OutRunVRRenderer::GetLatchedHeadInverse(headInverseRaw,headSequence) ||
       headSequence!=stereo->poseSequence || !std::isfinite(worldScale) ||
       !std::isfinite(depthScale) || worldScale<=0 || depthScale<=0 ||
       !std::isfinite(vehicleScale) || vehicleScale<0.5f || vehicleScale>2.0f)
        return false;
    D3DMATRIX originalProjection{},headInverse{};
    std::memcpy(&originalProjection,baseProjectionRaw,sizeof(originalProjection));
    std::memcpy(&headInverse,headInverseRaw,sizeof(headInverse));
    D3DMATRIX world=carWorld;
    if(vehicleScale!=1.0f &&
       !OutRunVR::DriverSeatVehicle::TryScaleModelBasis(world,vehicleScale))
        return false;
    D3DMATRIX views[2]{},projections[2]{};
    for(int eye=0;eye<2;++eye) {
        const D3DMATRIX eyePose=OutRunVRStereo::R29OwnerMatrixFromQuaternionTranslation(
            stereo->eyeOrientation[eye],stereo->eyeOffset[eye],worldScale*depthScale);
        const D3DMATRIX eyeInverse=OutRunVRStereo::R29OwnerInverseRigid(eyePose);
        views[eye]=OutRunVRStereo::R29OwnerMultiplyMatrix(
            OutRunVRStereo::R29OwnerMultiplyMatrix(gameBaseView,headInverse),eyeInverse);
        projections[eye]=OutRunVRStereo::R29OwnerProjectionFromFov(
            originalProjection,stereo->eyeFov[eye]);
        if(!OutRunVRStereo::R29OwnerMatrixFinite(world) ||
           !OutRunVRStereo::R29OwnerMatrixFinite(views[eye]) ||
           !OutRunVRStereo::R29OwnerMatrixFinite(projections[eye]))
            return false;
    }
    IDirect3DSurface9* originalRt=nullptr,*originalDepth=nullptr;
    D3DVIEWPORT9 originalViewport{};
    if(FAILED(device->GetRenderTarget(0,&originalRt)) || !originalRt)
        return false;
    if(FAILED(device->GetDepthStencilSurface(&originalDepth)) ||
       !originalDepth || FAILED(device->GetViewport(&originalViewport)) ||
       (snapshot.backBuffer && originalRt!=snapshot.backBuffer)) {
        if(originalDepth)originalDepth->Release();
        originalRt->Release();
        return false;
    }
    // One real cockpit pair per Present, even if the native player body runs
    // multiple opaque passes. Count only a fully admitted original RT owner.
    static thread_local std::uint64_t lastSubmittedEpoch=~std::uint64_t{0};
    static thread_local IDirect3DDevice9* lastSubmittedDevice=nullptr;
    if(lastSubmittedDevice==device && lastSubmittedEpoch==snapshot.presentEpoch) {
        originalDepth->Release();originalRt->Release();return false;
    }
    // A missing or invalid .ovc file must never poison the existing VR frame.
    // Asset validation and GPU allocation precede the first sidecar depth write.
    if(!Gpu().EnsureResources(device)) {
        originalDepth->Release();originalRt->Release();return false;
    }
    lastSubmittedDevice=device;
    lastSubmittedEpoch=snapshot.presentEpoch;
    bool good=false;
    {
        // Bypass R33 physical Draw hooks for each explicit sidecar eye:
        // the sidecar itself changes target and eye view/projection.
        ScopedInternal internal;
        // Match the native R33 stereo accounting. The sidecar changes the
        // current game depth and cannot be advertised as a pristine mono copy.
        OutRunVRStereo::R29OwnerNoteStereoDrawWithoutMonoBackup();
        OutRunVRStereo::R29OwnerNoteMainDepthContentWrite();
        const HRESULT left=Gpu().DrawEye(device,world,views[0],projections[0]);
        HRESULT right=E_FAIL;
        if(SUCCEEDED(left)) {
            D3DSURFACE_DESC desc{};
            const bool sized=SUCCEEDED(snapshot.rightEyeSurface->GetDesc(&desc)) &&
                             desc.Width && desc.Height;
            if(sized && SUCCEEDED(device->SetRenderTarget(0,snapshot.rightEyeSurface)) &&
               SUCCEEDED(device->SetDepthStencilSurface(snapshot.rightEyeDepth))) {
                D3DVIEWPORT9 viewport=originalViewport;
                viewport.X=0;viewport.Y=0;viewport.Width=desc.Width;
                viewport.Height=desc.Height;
                if(SUCCEEDED(device->SetViewport(&viewport)))
                    right=Gpu().DrawEye(device,world,views[1],projections[1]);
            }
        }
        // Restore RT, depth and viewport regardless of any failed right eye.
        const HRESULT rt=device->SetRenderTarget(0,originalRt);
        const HRESULT depth=device->SetDepthStencilSurface(originalDepth);
        const HRESULT viewport=device->SetViewport(&originalViewport);
        // StateBlock::Apply bypasses regular Set* interception; the last
        // Apply happened with the right-eye RT bound. Re-prime the lower
        // raster shadow against the restored original RT before native code
        // resumes. Unknown live state must fail closed, never reuse stale RT.
        OutRunVRStereo::R29OwnerInvalidateTrackedRasterShadow();
        OutRunVRStereo::R29OwnerInvalidateEffectStateCache();
        const bool rasterReady=OutRunVRStereo::R29OwnerPrimeTrackedRasterShadow(device);
        good=SUCCEEDED(left)&&SUCCEEDED(right)&&SUCCEEDED(rt)&&
             SUCCEEDED(depth)&&SUCCEEDED(viewport)&&rasterReady;
        if(!good) {
            OutRunVRStereo::R29OwnerMarkRightDrawFailed();
            OutRunVRStereo::R29OwnerArmMonoSafety();
        }
    }
    originalDepth->Release();originalRt->Release();
    return good;
}
} // OutRunVR::DinoSidecar
