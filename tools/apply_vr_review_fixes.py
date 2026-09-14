from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:180]!r}")
    write(path, text.replace(old, new, 1))


# 1) IPC: explicitly expose runtime render eligibility and a Present-in-flight
# publication state without changing either shared-memory structure size.
replace_once(
    "src/vr_shared.hpp",
    "        StereoEyeOrientationValid = 1u << 6,\n",
    "        StereoEyeOrientationValid = 1u << 6,\n        HostShouldRender = 1u << 7,\n",
)
replace_once(
    "src/vr_shared.hpp",
    "        RenderFrameEffectivePoseValid = 1u << 3,\n",
    "        RenderFrameEffectivePoseValid = 1u << 3,\n        RenderFramePresentInFlight = 1u << 4,\n",
)
replace_once(
    "src/vr_shared.hpp",
    "    using OutRunVR::StereoEyeOrientationValid;\n",
    "    using OutRunVR::StereoEyeOrientationValid;\n    using OutRunVR::SessionVisible;\n    using OutRunVR::HostShouldRender;\n",
)

# 2) Renderer pose latch: do not consume poses while OpenXR says not to render.
replace_once(
    "src/vr_renderer_probe.cpp",
    "\t\t\tif ((snapshot.flags & HostAlive) == 0 ||\n\t\t\t\t(snapshot.flags & OrientationValid) == 0 || snapshot.hostPid == 0)\n\t\t\t\treturn false;\n",
    "\t\t\tif ((snapshot.flags & HostAlive) == 0 ||\n\t\t\t\t(snapshot.flags & OrientationValid) == 0 ||\n\t\t\t\t(snapshot.flags & SessionVisible) == 0 ||\n\t\t\t\t(snapshot.flags & HostShouldRender) == 0 || snapshot.hostPid == 0)\n\t\t\t\treturn false;\n",
)

# If position tracking was unavailable at recenter/startup, lock the first later
# valid LOCAL position even when positional tracking is disabled. This keeps the
# effective projection pose fixed instead of silently following live XYZ.
replace_once(
    "src/vr_renderer_probe.cpp",
    "\t\t\trelativeOrientation = ScaleRotation(relativeOrientation, Settings::VRRotationScale);\n",
    "\t\t\tif (!CenterPositionValid && sample.positionValid)\n\t\t\t{\n\t\t\t\tCenterPosition = sample.position;\n\t\t\t\tCenterPositionValid = true;\n\t\t\t}\n\n\t\t\trelativeOrientation = ScaleRotation(relativeOrientation, Settings::VRRotationScale);\n",
)

# CullingUnionFov must never mutate OutRun's live renderer projection. Until a
# culling-only frustum boundary is identified, keep the option deliberately
# fail-safe/no-op and warn once if a user enables it.
replace_once(
    "src/vr_renderer_probe.cpp",
    "\t\tbool FirstUploadFailedLogged = false;\n",
    "\t\tbool FirstUploadFailedLogged = false;\n\t\tbool CullingUnionFovDeferredLogged = false;\n",
)
old_union = '''\t\t\tif (Settings::VRCullingUnionFov && LatchedStereo.valid && RendererProjection)\n\t\t\t{\n\t\t\t\tauto* projection = const_cast<D3DMATRIX*>(RendererProjection);\n\t\t\t\tD3DMATRIX baseProjection{}; std::memcpy(&baseProjection, RendererProjection, sizeof(baseProjection));\n\t\t\t\tSharedFov unionFov{};\n\t\t\t\tunionFov.angleLeft = std::min(LatchedStereo.eyeFov[0].angleLeft, LatchedStereo.eyeFov[1].angleLeft);\n\t\t\t\tunionFov.angleRight = std::max(LatchedStereo.eyeFov[0].angleRight, LatchedStereo.eyeFov[1].angleRight);\n\t\t\t\tunionFov.angleUp = std::max(LatchedStereo.eyeFov[0].angleUp, LatchedStereo.eyeFov[1].angleUp);\n\t\t\t\tunionFov.angleDown = std::min(LatchedStereo.eyeFov[0].angleDown, LatchedStereo.eyeFov[1].angleDown);\n\t\t\t\tconst D3DMATRIX widened = ProjectionFromFov(baseProjection, unionFov);\n\t\t\t\tif (MatrixFinite(widened) && IsWritableRange(projection, sizeof(D3DMATRIX)))\n\t\t\t\t{\n\t\t\t\t\tCullingProjectionSaved = baseProjection;\n\t\t\t\t\tstd::memcpy(projection, &widened, sizeof(widened));\n\t\t\t\t\tCullingProjectionOverridden = true;\n\t\t\t\t}\n\t\t\t}\n'''
new_union = '''\t\t\tif (Settings::VRCullingUnionFov && !CullingUnionFovDeferredLogged)\n\t\t\t{\n\t\t\t\tCullingUnionFovDeferredLogged = true;\n\t\t\t\tspdlog::warn("VR renderer: CullingUnionFov is deferred until a culling-only frustum boundary is verified; live projection remains untouched");\n\t\t\t}\n'''
replace_once("src/vr_renderer_probe.cpp", old_union, new_union)

# 3) Stereo device isolation and right-depth validity.
replace_once(
    "src/vr_stereo.cpp",
    '''\t\tbool StereoWanted()\n\t\t{\n\t\t\tif (!Settings::VRStereo || !GameplayActive())\n\t\t\t\treturn false;\n\t\t\treturn Settings::VREnabled || Settings::VRAutoEnableWhenHostPresent;\n\t\t}\n''',
    '''\t\tbool HostRenderEligible()\n\t\t{\n\t\t\tif (!SharedState || SharedState->magic != OutRunVR::SharedMagic ||\n\t\t\t\tSharedState->protocolVersion != OutRunVR::SharedProtocolVersion ||\n\t\t\t\tSharedState->structSize != sizeof(OutRunVR::SharedPoseState))\n\t\t\t\treturn false;\n\t\t\tconst std::uint32_t flags = SharedState->flags;\n\t\t\treturn (flags & OutRunVR::HostAlive) != 0 &&\n\t\t\t\t(flags & OutRunVR::SessionVisible) != 0 &&\n\t\t\t\t(flags & OutRunVR::HostShouldRender) != 0;\n\t\t}\n\n\t\tbool StereoWanted()\n\t\t{\n\t\t\tif (!Settings::VRStereo || !GameplayActive() || !HostRenderEligible())\n\t\t\t\treturn false;\n\t\t\treturn Settings::VREnabled || Settings::VRAutoEnableWhenHostPresent;\n\t\t}\n''',
)
replace_once(
    "src/vr_stereo.cpp",
    '''\t\tbool ViewportCoversStereoBackbuffer(IDirect3DDevice9* device)\n''',
    '''\t\tbool LeftDrawMayWriteDepth(IDirect3DDevice9* device)\n\t\t{\n\t\t\tif (!device || !TrackedDepthStencil)\n\t\t\t\treturn false;\n\t\t\tDWORD zEnable = D3DZB_TRUE;\n\t\t\tDWORD zWrite = TRUE;\n\t\t\tif (FAILED(device->GetRenderState(D3DRS_ZENABLE, &zEnable)) ||\n\t\t\t\tFAILED(device->GetRenderState(D3DRS_ZWRITEENABLE, &zWrite)))\n\t\t\t\treturn true; // fail closed if state cannot be inspected\n\t\t\treturn zEnable != D3DZB_FALSE && zWrite != FALSE;\n\t\t}\n\n\t\tvoid InvalidateRightDepthIfLeftMayWrite(IDirect3DDevice9* device)\n\t\t{\n\t\t\tif (RightDepthSynchronized && LeftDrawMayWriteDepth(device))\n\t\t\t\tRightDepthSynchronized = false;\n\t\t}\n\n\t\tbool ViewportCoversStereoBackbuffer(IDirect3DDevice9* device)\n''',
)

replace_once(
    "src/vr_stereo.cpp",
    '''\t\ttemplate <typename DrawCall>\n\t\tHRESULT ExecuteStereoDraw(IDirect3DDevice9* device, DrawCall&& drawCall)\n\t\t{\n\t\t\tDrawStereoState draw{};\n\t\t\tif (!PrepareDuplicatedDraw(device, draw))\n\t\t\t\treturn drawCall();\n''',
    '''\t\ttemplate <typename DrawCall>\n\t\tHRESULT ExecuteStereoDraw(IDirect3DDevice9* device, DrawCall&& drawCall)\n\t\t{\n\t\t\tif (!IsGameDevice(device))\n\t\t\t\treturn drawCall();\n\t\t\tif (StereoWanted() && !TargetIsBackBuffer())\n\t\t\t{\n\t\t\t\tInvalidateRightDepthIfLeftMayWrite(device);\n\t\t\t\treturn drawCall();\n\t\t\t}\n\n\t\t\tDrawStereoState draw{};\n\t\t\tif (!PrepareDuplicatedDraw(device, draw))\n\t\t\t{\n\t\t\t\tif (StereoWanted() && TargetIsBackBuffer())\n\t\t\t\t\tInvalidateRightDepthIfLeftMayWrite(device);\n\t\t\t\treturn drawCall();\n\t\t\t}\n''',
)
replace_once(
    "src/vr_stereo.cpp",
    '''\t\t\tconst HRESULT leftHr = drawCall();\n\t\t\tif(FAILED(leftHr)){PoisonFrame(OutRunVR::StereoFailureLeftDrawFailed);if(draw.worldStereo&&!SetWvpOneRegisterAtATime(device,draw.originalConstants))NoteRestoreFailure("left draw c64");return leftHr;}\n''',
    '''\t\t\tconst HRESULT leftHr = drawCall();\n\t\t\tif(FAILED(leftHr)){InvalidateRightDepthIfLeftMayWrite(device);PoisonFrame(OutRunVR::StereoFailureLeftDrawFailed);if(draw.worldStereo&&!SetWvpOneRegisterAtATime(device,draw.originalConstants))NoteRestoreFailure("left draw c64");return leftHr;}\n''',
)
replace_once(
    "src/vr_stereo.cpp",
    '''\t\t\tif (FAILED(rightHr))\n\t\t\t{\n\t\t\t\tFrameRightDrawFailed = true;\n\t\t\t\tPoisonFrame(rightFailure);\n\t\t\t}\n\t\t\tif (!restoreOk)\n\t\t\t\tNoteRestoreFailure("right-eye draw");\n''',
    '''\t\t\tif (FAILED(rightHr))\n\t\t\t{\n\t\t\t\tFrameRightDrawFailed = true;\n\t\t\t\tInvalidateRightDepthIfLeftMayWrite(device);\n\t\t\t\tPoisonFrame(rightFailure);\n\t\t\t}\n\t\t\tif (!restoreOk)\n\t\t\t{\n\t\t\t\tInvalidateRightDepthIfLeftMayWrite(device);\n\t\t\t\tNoteRestoreFailure("right-eye draw");\n\t\t\t}\n''',
)

old_clear = '''\t\tHRESULT __stdcall ClearDest(IDirect3DDevice9* device, DWORD count, const D3DRECT* rects,\n\t\t\tDWORD flags, D3DCOLOR color, float z, DWORD stencil)\n\t\t{\n\t\t\tconst bool candidate=!InternalStereoPass&&StereoWanted()&&TargetIsBackBuffer();bool duplicate=candidate;\n\t\t\tif(duplicate&&AnyAuxRenderTargetActive()){PoisonFrame(OutRunVR::StereoFailureMrtActive);duplicate=false;}\n\t\t\tif(duplicate&&!EnsureStereoResources(device)){PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);duplicate=false;}\n\t\t\tconst HRESULT leftHr=ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);if(!duplicate||FAILED(leftHr)){if(candidate&&FAILED(leftHr))PoisonFrame(OutRunVR::StereoFailureClearFailed);return leftHr;}\n\t\t\tD3DVIEWPORT9 savedViewport{};if(FAILED(device->GetViewport(&savedViewport))){PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return leftHr;}\n\t\t\tIDirect3DSurface9* savedRt=TrackedRenderTarget;IDirect3DSurface9* savedDepth=TrackedDepthStencil;HRESULT rightHr=D3D_OK;bool restoreOk=true;{\n\t\t\t\tInternalPassScope guard;rightHr=SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface);if(SUCCEEDED(rightHr))rightHr=SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth);if(SUCCEEDED(rightHr))rightHr=device->SetViewport(&savedViewport);if(SUCCEEDED(rightHr))rightHr=ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);restoreOk=RestoreRightPassState(device,savedRt,savedDepth,savedViewport,nullptr,false);}\n\t\t\tif(FAILED(rightHr)){FrameRightDrawFailed=true;PoisonFrame(OutRunVR::StereoFailureClearFailed);}else if ((flags & D3DCLEAR_ZBUFFER) != 0 && count == 0 &&\n\t\t\t\tViewportCoversStereoBackbuffer(device)) RightDepthSynchronized = true;if(!restoreOk)NoteRestoreFailure("right-eye clear");return leftHr;\n\t\t}\n'''
new_clear = '''\t\tHRESULT __stdcall ClearDest(IDirect3DDevice9* device, DWORD count, const D3DRECT* rects,\n\t\t\tDWORD flags, D3DCOLOR color, float z, DWORD stencil)\n\t\t{\n\t\t\tif (!IsGameDevice(device) || InternalStereoPass)\n\t\t\t\treturn ClearHook.stdcall<HRESULT>(device, count, rects, flags, color, z, stencil);\n\t\t\tif (StereoWanted() && !TargetIsBackBuffer())\n\t\t\t{\n\t\t\t\tconst HRESULT hr = ClearHook.stdcall<HRESULT>(device, count, rects, flags, color, z, stencil);\n\t\t\t\tif (SUCCEEDED(hr) && (flags & D3DCLEAR_ZBUFFER) != 0 && TrackedDepthStencil)\n\t\t\t\t\tRightDepthSynchronized = false;\n\t\t\t\treturn hr;\n\t\t\t}\n\n\t\t\tconst bool candidate=StereoWanted()&&TargetIsBackBuffer();bool duplicate=candidate;\n\t\t\tif(duplicate&&AnyAuxRenderTargetActive()){PoisonFrame(OutRunVR::StereoFailureMrtActive);duplicate=false;}\n\t\t\tif(duplicate&&!EnsureStereoResources(device)){PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);duplicate=false;}\n\t\t\tconst HRESULT leftHr=ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);\n\t\t\tif(!duplicate||FAILED(leftHr)){if(candidate&&FAILED(leftHr))PoisonFrame(OutRunVR::StereoFailureClearFailed);if(SUCCEEDED(leftHr)&&candidate&&(flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;return leftHr;}\n\t\t\tD3DVIEWPORT9 savedViewport{};if(FAILED(device->GetViewport(&savedViewport))){if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return leftHr;}\n\t\t\tIDirect3DSurface9* savedRt=TrackedRenderTarget;IDirect3DSurface9* savedDepth=TrackedDepthStencil;HRESULT rightHr=D3D_OK;bool restoreOk=true;{\n\t\t\t\tInternalPassScope guard;rightHr=SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface);if(SUCCEEDED(rightHr))rightHr=SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth);if(SUCCEEDED(rightHr))rightHr=device->SetViewport(&savedViewport);if(SUCCEEDED(rightHr))rightHr=ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);restoreOk=RestoreRightPassState(device,savedRt,savedDepth,savedViewport,nullptr,false);}\n\t\t\tif(FAILED(rightHr)){FrameRightDrawFailed=true;if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;PoisonFrame(OutRunVR::StereoFailureClearFailed);}else if ((flags & D3DCLEAR_ZBUFFER) != 0 && count == 0 &&\n\t\t\t\tViewportCoversStereoBackbuffer(device)) RightDepthSynchronized = true;if(!restoreOk){if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;NoteRestoreFailure("right-eye clear");}return leftHr;\n\t\t}\n'''
replace_once("src/vr_stereo.cpp", old_clear, new_clear)

# 4) Frame.v1 two-phase Present publication.
replace_once(
    "src/vr_stereo.cpp",
    "\t\tvoid PublishRenderFrame(std::uint32_t state,std::uint32_t frameId,std::uint32_t sourcePoseSequence,std::int64_t presentQpc,OutRunVR::StereoFailureReason failureReason,const OutRunVRRenderer::LatchedStereoFrame* stereo)\n",
    "\t\tvoid PublishRenderFrame(std::uint32_t state,std::uint32_t frameId,std::uint32_t sourcePoseSequence,std::int64_t presentQpc,OutRunVR::StereoFailureReason failureReason,const OutRunVRRenderer::LatchedStereoFrame* stereo,bool presentInFlight=false)\n",
)
replace_once(
    "src/vr_stereo.cpp",
    "RenderFrameState->presentationMode=GameplayActive()?OutRunVR::PresentationGameplay:OutRunVR::PresentationTheater;RenderFrameState->flags=0;RenderFrameState->failureReason=static_cast<std::uint32_t>(failureReason);",
    "RenderFrameState->presentationMode=GameplayActive()?OutRunVR::PresentationGameplay:OutRunVR::PresentationTheater;RenderFrameState->flags=presentInFlight?OutRunVR::RenderFramePresentInFlight:0;RenderFrameState->failureReason=static_cast<std::uint32_t>(failureReason);",
)
replace_once(
    "src/vr_stereo.cpp",
    "\t\t\tif(state==OutRunVR::StereoSbsActive&&stereo&&stereo->valid&&frameId){RenderFrameState->flags=OutRunVR::RenderFrameStereoComplete|OutRunVR::RenderFrameWorldStereo|OutRunVR::RenderFrameDrawDuplicated|OutRunVR::RenderFrameEffectivePoseValid;",
    "\t\t\tif(!presentInFlight&&state==OutRunVR::StereoSbsActive&&stereo&&stereo->valid&&frameId){RenderFrameState->flags=OutRunVR::RenderFrameStereoComplete|OutRunVR::RenderFrameWorldStereo|OutRunVR::RenderFrameDrawDuplicated|OutRunVR::RenderFrameEffectivePoseValid;",
)
old_present = '''\t\tHRESULT __stdcall PresentDest(IDirect3DDevice9* device,const RECT* sourceRect,const RECT* destRect,HWND destWindowOverride,const RGNDATA* dirtyRegion)\n\t\t{\n\t\t\tif(!IsGameDevice(device))return PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);const bool stereoRequested=StereoWanted();bool composedStereo=false;std::uint32_t pendingPoseSequence=0;\n\t\t\tif(stereoRequested&&FrameHadWorldStereo&&FrameHadDuplicatedDraw&&!FrameRightDrawFailed&&!FrameStereoIncomplete&&FrameStereoPoseSequence&&FrameStereoMetadata.valid&&EnsureStereoResources(device)){if(ComposeSbs(device)){++StereoComposeSuccess;composedStereo=true;pendingPoseSequence=FrameStereoPoseSequence;}else{++StereoComposeFailure;PoisonFrame(OutRunVR::StereoFailureComposeFailed);}}\n\t\t\tMaybeLogSummary();LARGE_INTEGER presentStart{};QueryPerformanceCounter(&presentStart);const HRESULT hr=PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);\n\t\t\tif(composedStereo&&SUCCEEDED(hr)&&!FrameStereoIncomplete){const std::uint32_t frameId=NextStereoFrameId();PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,frameId);PublishRenderFrame(OutRunVR::StereoSbsActive,frameId,pendingPoseSequence,presentStart.QuadPart,OutRunVR::StereoFailureNone,&FrameStereoMetadata);if(!FirstStereoActiveLogged){FirstStereoActiveLogged=true;spdlog::info("VR stereo: SBS transport active; exact effective eye pose published in Frame.v1");}}\n\t\t\telse{if(FAILED(hr)&&FrameFailureReason==OutRunVR::StereoFailureNone)FrameFailureReason=OutRunVR::StereoFailurePresentFailed;const std::uint32_t fallback=stereoRequested?OutRunVR::StereoSbsFallbackMono:OutRunVR::StereoDisabled;PublishStereoState(fallback,false,0,0);PublishRenderFrame(fallback,0,0,presentStart.QuadPart,FrameFailureReason,nullptr);}\n\t\t\tFrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata={};return hr;\n\t\t}\n'''
new_present = '''\t\tHRESULT __stdcall PresentDest(IDirect3DDevice9* device,const RECT* sourceRect,const RECT* destRect,HWND destWindowOverride,const RGNDATA* dirtyRegion)\n\t\t{\n\t\t\tif(!IsGameDevice(device))return PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);const bool stereoRequested=StereoWanted();bool composedStereo=false;std::uint32_t pendingPoseSequence=0;\n\t\t\tif(stereoRequested&&FrameHadWorldStereo&&FrameHadDuplicatedDraw&&!FrameRightDrawFailed&&!FrameStereoIncomplete&&FrameStereoPoseSequence&&FrameStereoMetadata.valid&&EnsureStereoResources(device)){if(ComposeSbs(device)){++StereoComposeSuccess;composedStereo=true;pendingPoseSequence=FrameStereoPoseSequence;}else{++StereoComposeFailure;PoisonFrame(OutRunVR::StereoFailureComposeFailed);}}\n\t\t\tMaybeLogSummary();LARGE_INTEGER presentStart{};QueryPerformanceCounter(&presentStart);const std::uint32_t pendingFrameId=stereoRequested?NextStereoFrameId():0;if(stereoRequested)PublishRenderFrame(OutRunVR::StereoSbsFallbackMono,pendingFrameId,pendingPoseSequence,presentStart.QuadPart,OutRunVR::StereoFailureNone,nullptr,true);const HRESULT hr=PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);\n\t\t\tif(composedStereo&&SUCCEEDED(hr)&&!FrameStereoIncomplete){PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,pendingFrameId);PublishRenderFrame(OutRunVR::StereoSbsActive,pendingFrameId,pendingPoseSequence,presentStart.QuadPart,OutRunVR::StereoFailureNone,&FrameStereoMetadata);if(!FirstStereoActiveLogged){FirstStereoActiveLogged=true;spdlog::info("VR stereo: SBS transport active; two-phase Present commit + effective eye pose published in Frame.v1");}}\n\t\t\telse{if(FAILED(hr)&&FrameFailureReason==OutRunVR::StereoFailureNone)FrameFailureReason=OutRunVR::StereoFailurePresentFailed;const std::uint32_t fallback=stereoRequested?OutRunVR::StereoSbsFallbackMono:OutRunVR::StereoDisabled;PublishStereoState(fallback,false,0,0);PublishRenderFrame(fallback,0,0,presentStart.QuadPart,FrameFailureReason,nullptr);}\n\t\t\tFrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata={};return hr;\n\t\t}\n'''
replace_once("src/vr_stereo.cpp", old_present, new_present)

# 5) Host sets render eligibility from OpenXR shouldRender and rejects in-flight
# Frame.v1 records both before and after desktop capture.
replace_once(
    "vrhost/main_stereo.cpp",
    "            XrSessionState sessionState, XrViewStateFlags viewFlags,\n            const char* runtime)\n",
    "            XrSessionState sessionState, XrViewStateFlags viewFlags, bool shouldRender,\n            const char* runtime)\n",
)
replace_once(
    "vrhost/main_stereo.cpp",
    "            if (sessionState == XR_SESSION_STATE_FOCUSED) flags |= OutRunVR::SessionFocused;\n",
    "            if (sessionState == XR_SESSION_STATE_FOCUSED) flags |= OutRunVR::SessionFocused;\n            if (shouldRender) flags |= OutRunVR::HostShouldRender;\n",
)
replace_once(
    "vrhost/main_stereo.cpp",
    "            const std::uint32_t hostSequence = shared.Write(head, views, vc, configs,\n                state, vs.viewStateFlags, ip.runtimeName);\n",
    "            const std::uint32_t hostSequence = shared.Write(head, views, vc, configs,\n                state, vs.viewStateFlags, fs.shouldRender == XR_TRUE, ip.runtimeName);\n",
)
replace_once(
    "vrhost/main_stereo.cpp",
    "                    if(have&&before.state==OutRunVR::StereoSbsActive&&before.frameId&&before.frameId!=lastProcessedStereoFrame&&before.sourcePoseSequence&&(before.flags&need)==need){",
    "                    if(have&&(before.flags&OutRunVR::RenderFramePresentInFlight)==0&&before.state==OutRunVR::StereoSbsActive&&before.frameId&&before.frameId!=lastProcessedStereoFrame&&before.sourcePoseSequence&&(before.flags&need)==need){",
)
replace_once(
    "vrhost/main_stereo.cpp",
    "const bool same=renderFrames.Read(after)&&after.state==before.state&&after.frameId==before.frameId&&after.sourcePoseSequence==before.sourcePoseSequence&&after.presentQpc==before.presentQpc;",
    "const bool same=renderFrames.Read(after)&&(after.flags&OutRunVR::RenderFramePresentInFlight)==0&&after.state==before.state&&after.frameId==before.frameId&&after.sourcePoseSequence==before.sourcePoseSequence&&after.presentQpc==before.presentQpc&&after.flags==before.flags&&after.failureReason==before.failureReason;",
)

# Documentation: culling union is intentionally deferred, and Frame.v1 uses a
# two-phase Present transaction to close both image/metadata race directions.
doc = read("VR_OPENXR.md")
doc = doc.replace(
    "`CullingUnionFov` is opt-in and affects only render-phase culling; pre-BeginScene visibility remains runtime-test territory.",
    "`CullingUnionFov` remains opt-in but is currently fail-safe deferred: the live renderer projection is never widened until a culling-only frustum boundary is verified. Pre-BeginScene visibility remains runtime-test territory. Frame.v1 also publishes a Present-in-flight transaction before the real D3D9 Present and commits the completed frame afterward, so Desktop Duplication cannot accept either old-image/new-metadata or new-image/old-metadata pairings.",
)
write("VR_OPENXR.md", doc)

# Contract checks for the source-only patch.
shared = read("src/vr_shared.hpp")
renderer = read("src/vr_renderer_probe.cpp")
stereo = read("src/vr_stereo.cpp")
host = read("vrhost/main_stereo.cpp")
for marker in ("HostShouldRender", "RenderFramePresentInFlight"):
    if marker not in shared:
        raise RuntimeError(f"missing IPC marker: {marker}")
for marker in ("CullingUnionFov is deferred", "HostShouldRender"):
    if marker not in renderer:
        raise RuntimeError(f"missing renderer marker: {marker}")
for marker in ("HostRenderEligible", "InvalidateRightDepthIfLeftMayWrite", "two-phase Present commit", "presentInFlight"):
    if marker not in stereo:
        raise RuntimeError(f"missing stereo marker: {marker}")
for marker in ("fs.shouldRender == XR_TRUE", "RenderFramePresentInFlight", "after.flags==before.flags"):
    if marker not in host:
        raise RuntimeError(f"missing host marker: {marker}")

print("applied device isolation, two-phase Present handshake, depth invalidation, render gating and safe culling deferral")
