from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")

def replace_once(path, old, new):
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:120]!r}")
    write(path, text.replace(old, new, 1))

def require(path, needle):
    if needle not in read(path):
        raise RuntimeError(f"{path}: missing required marker {needle!r}")

# Shared ABI: preserve Pose.v1 size, add full eye orientation inside the same
# 248-byte host packet, and add a separate Game->Host Frame.v1 bridge.
shared = r'''#pragma once

#include <cstdint>

namespace OutRunVR
{
\tinline constexpr wchar_t SharedMemoryName[] = L"Local\\OutRun2006Tweaks.VR.Pose.v1";
\tinline constexpr std::uint32_t SharedMagic = 0x5256524Fu; // 'ORVR' in little endian
\tinline constexpr std::uint32_t SharedProtocolVersion = 1;

\tinline constexpr wchar_t RenderFrameMemoryName[] = L"Local\\OutRun2006Tweaks.VR.Frame.v1";
\tinline constexpr std::uint32_t RenderFrameMagic = 0x4656524Fu; // 'ORVF'
\tinline constexpr std::uint32_t RenderFrameProtocolVersion = 1;

\tenum SharedFlags : std::uint32_t
\t{
\t\tHostAlive = 1u << 0,
\t\tOrientationValid = 1u << 1,
\t\tPositionValid = 1u << 2,
\t\tSessionVisible = 1u << 3,
\t\tSessionFocused = 1u << 4,
\t\tStereoViewsValid = 1u << 5,
\t\tStereoEyeOrientationValid = 1u << 6,
\t};

\tinline constexpr std::uint32_t ClientHeartbeatIndex = 0;
\tinline constexpr std::uint32_t ClientFlagsIndex = 1;
\tinline constexpr std::uint32_t ClientLastAngleBitsIndex = 2;
\tinline constexpr std::uint32_t HostReferenceSpaceGenerationIndex = 3;
\tinline constexpr std::uint32_t ClientPresentationModeIndex = 4;
\tinline constexpr std::uint32_t ClientGameStateIndex = 5;
\tinline constexpr std::uint32_t HostEyeOffsetLeftXIndex = 6;
\tinline constexpr std::uint32_t HostEyeOffsetLeftYIndex = 7;
\tinline constexpr std::uint32_t HostEyeOffsetLeftZIndex = 8;
\tinline constexpr std::uint32_t HostEyeOffsetRightXIndex = 9;
\tinline constexpr std::uint32_t HostEyeOffsetRightYIndex = 10;
\tinline constexpr std::uint32_t HostEyeOffsetRightZIndex = 11;
\tinline constexpr std::uint32_t ClientStereoStateIndex = 12;
\tinline constexpr std::uint32_t ClientStereoFrameIndex = 13;
\tinline constexpr std::uint32_t ClientStereoPresentQpcLowIndex = 14;
\tinline constexpr std::uint32_t ClientStereoBackbufferHeightIndex = 15;
\tinline constexpr std::uint32_t ClientStereoBackbufferWidthIndex = ClientStereoPresentQpcLowIndex;

\tenum ClientPresentationMode : std::uint32_t
\t{
\t\tPresentationUnknown = 0,
\t\tPresentationGameplay = 1,
\t\tPresentationTheater = 2,
\t};

\tenum ClientStereoState : std::uint32_t
\t{
\t\tStereoDisabled = 0,
\t\tStereoSbsActive = 1,
\t\tStereoSbsFallbackMono = 2,
\t};

\tenum ClientTelemetryFlags : std::uint32_t
\t{
\t\tClientHookAlive = 1u << 0,
\t\tClientHostPoseValid = 1u << 1,
\t\tClientPoseApplied = 1u << 2,
\t\tClientAutoEnabled = 1u << 3,
\t\tClientRendererWvpVerified = 1u << 4,
\t\tClientRendererPoseInjected = 1u << 5,
\t\tClientRendererMatrixPrepared = 1u << 6,
\t\tClientRendererUploadFailed = 1u << 7,
\t\tClientCullingCameraSynced = 1u << 8,
\t\tClientFrameCompleted = 1u << 9,
\t\tClientStereoActive = 1u << 10,
\t\tClientStereoWorldDraw = 1u << 11,
\t\tClientStereoDrawDuplicated = 1u << 12,
\t};

\tenum RenderFrameFlags : std::uint32_t
\t{
\t\tRenderFrameStereoComplete = 1u << 0,
\t\tRenderFrameWorldStereo = 1u << 1,
\t\tRenderFrameDrawDuplicated = 1u << 2,
\t\tRenderFrameEffectivePoseValid = 1u << 3,
\t};

\tenum StereoFailureReason : std::uint32_t
\t{
\t\tStereoFailureNone = 0,
\t\tStereoFailureMissingLatchedPose = 1,
\t\tStereoFailureResourceUnavailable = 2,
\t\tStereoFailureMrtActive = 3,
\t\tStereoFailureViewportUnavailable = 4,
\t\tStereoFailureLeftWvpUploadFailed = 5,
\t\tStereoFailureLeftDrawFailed = 6,
\t\tStereoFailureRightStateFailed = 7,
\t\tStereoFailureRightWvpUploadFailed = 8,
\t\tStereoFailureRightDrawFailed = 9,
\t\tStereoFailureRestoreFailed = 10,
\t\tStereoFailureComposeFailed = 11,
\t\tStereoFailurePresentFailed = 12,
\t\tStereoFailureDepthStateChanged = 13,
\t\tStereoFailurePoseSequenceMismatch = 14,
\t\tStereoFailureDepthUnsynchronized = 15,
\t\tStereoFailureClearFailed = 16,
\t};

#pragma pack(push, 4)
\tstruct SharedFov
\t{
\t\tfloat angleLeft;
\t\tfloat angleRight;
\t\tfloat angleUp;
\t\tfloat angleDown;
\t};

\tstruct SharedPoseState
\t{
\t\tstd::uint32_t magic;
\t\tstd::uint32_t protocolVersion;
\t\tstd::uint32_t structSize;
\t\tvolatile std::uint32_t sequence;
\t\tvolatile std::uint32_t hostPid;
\t\tvolatile std::uint32_t clientPid;
\t\tvolatile std::uint32_t flags;
\t\tvolatile std::uint32_t heartbeat;
\t\tstd::int64_t sampleQpc;
\t\tfloat orientation[4];
\t\tfloat position[3];
\t\tvolatile std::uint32_t clientStereoPoseSequence;
\t\tSharedFov eyeFov[2];
\t\tfloat eyeOrientation[2][4];
\t\tchar runtimeName[48];
\t\tstd::uint32_t reserved[16];
\t};

\tstruct SharedRenderEye
\t{
\t\tfloat orientation[4];
\t\tfloat position[3];
\t\tfloat reserved0;
\t\tSharedFov fov;
\t};

\tstruct SharedRenderFrameState
\t{
\t\tstd::uint32_t magic;
\t\tstd::uint32_t protocolVersion;
\t\tstd::uint32_t structSize;
\t\tvolatile std::uint32_t sequence;
\t\tvolatile std::uint32_t clientPid;
\t\tstd::uint32_t state;
\t\tstd::uint32_t frameId;
\t\tstd::uint32_t sourcePoseSequence;
\t\tstd::uint32_t presentationMode;
\t\tstd::uint32_t flags;
\t\tstd::uint32_t failureReason;
\t\tstd::uint32_t backbufferWidth;
\t\tstd::uint32_t backbufferHeight;
\t\tstd::int64_t presentQpc;
\t\tSharedRenderEye eye[2];
\t\tstd::uint32_t reserved[25];
\t};
#pragma pack(pop)

\tstatic_assert(sizeof(SharedFov) == 16);
\tstatic_assert(sizeof(SharedPoseState) == 248);
\tstatic_assert(sizeof(SharedRenderEye) == 48);
\tstatic_assert(sizeof(SharedRenderFrameState) == 256);
}

namespace OutRunVRRenderer
{
\tusing OutRunVR::SharedMemoryName;
\tusing OutRunVR::SharedMagic;
\tusing OutRunVR::SharedProtocolVersion;
\tusing OutRunVR::SharedPoseState;
\tusing OutRunVR::SharedFov;
\tusing OutRunVR::HostAlive;
\tusing OutRunVR::OrientationValid;
\tusing OutRunVR::PositionValid;
\tusing OutRunVR::StereoViewsValid;
\tusing OutRunVR::StereoEyeOrientationValid;
\tusing OutRunVR::ClientHeartbeatIndex;
\tusing OutRunVR::ClientFlagsIndex;
\tusing OutRunVR::ClientLastAngleBitsIndex;
\tusing OutRunVR::HostReferenceSpaceGenerationIndex;
\tusing OutRunVR::ClientPresentationModeIndex;
\tusing OutRunVR::ClientGameStateIndex;
\tusing OutRunVR::HostEyeOffsetLeftXIndex;
\tusing OutRunVR::HostEyeOffsetLeftYIndex;
\tusing OutRunVR::HostEyeOffsetLeftZIndex;
\tusing OutRunVR::HostEyeOffsetRightXIndex;
\tusing OutRunVR::HostEyeOffsetRightYIndex;
\tusing OutRunVR::HostEyeOffsetRightZIndex;
\tusing OutRunVR::ClientStereoStateIndex;
\tusing OutRunVR::ClientStereoFrameIndex;
\tusing OutRunVR::ClientStereoPresentQpcLowIndex;
\tusing OutRunVR::ClientStereoBackbufferWidthIndex;
\tusing OutRunVR::ClientStereoBackbufferHeightIndex;
\tusing OutRunVR::ClientPresentationMode;
\tusing OutRunVR::PresentationUnknown;
\tusing OutRunVR::PresentationGameplay;
\tusing OutRunVR::PresentationTheater;
\tusing OutRunVR::StereoDisabled;
\tusing OutRunVR::StereoSbsActive;
\tusing OutRunVR::StereoSbsFallbackMono;
\tusing OutRunVR::ClientHookAlive;
\tusing OutRunVR::ClientHostPoseValid;
\tusing OutRunVR::ClientPoseApplied;
\tusing OutRunVR::ClientAutoEnabled;
\tusing OutRunVR::ClientRendererWvpVerified;
\tusing OutRunVR::ClientRendererPoseInjected;
\tusing OutRunVR::ClientRendererMatrixPrepared;
\tusing OutRunVR::ClientRendererUploadFailed;
\tusing OutRunVR::ClientCullingCameraSynced;
\tusing OutRunVR::ClientFrameCompleted;
\tusing OutRunVR::ClientStereoActive;
\tusing OutRunVR::ClientStereoWorldDraw;
\tusing OutRunVR::ClientStereoDrawDuplicated;

\tstruct LatchedStereoFrame
\t{
\t\tbool valid = false;
\t\tstd::uint32_t poseSequence = 0;
\t\tSharedFov eyeFov[2]{};
\t\tfloat eyeOffset[2][3]{};
\t\tfloat eyeOrientation[2][4]{};
\t\tfloat effectiveEyeOrientation[2][4]{};
\t\tfloat effectiveEyePosition[2][3]{};
\t};

\tbool GetLatchedStereoFrame(LatchedStereoFrame& out);
\tbool GetLastVerifiedWvp(float outConstants[16], std::uint32_t& generation,
\t\tstd::uint32_t& poseSequence, std::uintptr_t& shaderIdentity,
\t\tstd::uint64_t& shaderSerial);
}

namespace OutRunVRStereo
{
\tbool IsInternalStereoPassActive();
\tbool GetCurrentShaderEpoch(std::uintptr_t& shaderIdentity, std::uint64_t& serial);
}
'''
write("src/vr_shared.hpp", shared)

replace_once("src/hooks_vr.cpp",
'''\tSetting<bool> VRCullingCameraSync{ "VR", "CullingCameraSync", true,
\t\t"Temporarily mirrors the render-time VR camera into OutRun's live camera position/look so render-phase culling and camera-facing effects can follow head motion. Restored before game logic resumes." };
\tSetting<float> VRWorldScale''',
'''\tSetting<bool> VRCullingCameraSync{ "VR", "CullingCameraSync", true,
\t\t"Temporarily mirrors the render-time VR camera into OutRun's live camera position/look so render-phase culling and camera-facing effects can follow head motion. Restored before game logic resumes." };
\tSetting<bool> VRCullingUnionFov{ "VR", "CullingUnionFov", false,
\t\t"Experimental: temporarily widens the verified render-time projection to the union of both OpenXR eye FOVs for render-phase culling. It cannot fix visibility lists built before BeginScene." };
\tSetting<float> VRWorldScale''')
replace_once("src/hooks_vr.cpp",
'''// vr_renderer_probe.cpp. vr_stereo.cpp builds on that already-verified mono transform:
// it duplicates D3D9 draws into left/right SBS viewports and replaces only world-draw
// c64 constants with true per-eye OpenXR view/projection matrices. Simulation, input,
// timers and native FFB are never replayed for the second eye.''',
'''// vr_renderer_probe.cpp. vr_stereo.cpp builds on that already-verified mono transform:
// it duplicates final D3D9 draws into full-size left/right eye surfaces and replaces
// only verified world-draw c64 constants with true per-eye OpenXR transforms.
// Simulation, input, timers and native FFB are never replayed for the second eye.''')

replace_once("src/vr_renderer_probe.cpp",
'''\textern Setting<bool> VRCullingCameraSync;
\textern Setting<float> VRWorldScale;''',
'''\textern Setting<bool> VRCullingCameraSync;
\textern Setting<bool> VRCullingUnionFov;
\textern Setting<float> VRWorldScale;''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\t\tbool stereoValid = false;
\t\t\tSharedFov eyeFov[2]{};
\t\t\tfloat eyeOffset[2][3]{};
\t\t};''',
'''\t\t\tbool stereoValid = false;
\t\t\tSharedFov eyeFov[2]{};
\t\t\tfloat eyeOffset[2][3]{};
\t\t\tQuat eyeOrientation[2]{
\t\t\t\t{ 0.0f, 0.0f, 0.0f, 1.0f },
\t\t\t\t{ 0.0f, 0.0f, 0.0f, 1.0f }
\t\t\t};
\t\t};''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\tD3DVECTOR CullingCameraSavedPos{};
\t\tD3DVECTOR CullingCameraSavedLook{};
\t\tEvWorkCamera* CullingCameraObject = nullptr;
\t\tbool CullingCameraOverridden = false;''',
'''\t\tD3DVECTOR CullingCameraSavedPos{};
\t\tD3DVECTOR CullingCameraSavedLook{};
\t\tEvWorkCamera* CullingCameraObject = nullptr;
\t\tbool CullingCameraOverridden = false;
\t\tD3DMATRIX CullingProjectionSaved{};
\t\tbool CullingProjectionOverridden = false;''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\tbool MatrixNear(const float* candidate, const D3DMATRIX& matrix, bool transposed, float epsilon)
\t\t{''',
'''\t\tD3DMATRIX ProjectionFromFov(const D3DMATRIX& base, const SharedFov& fov)
\t\t{
\t\t\tconst float tanLeft = std::tan(fov.angleLeft), tanRight = std::tan(fov.angleRight);
\t\t\tconst float tanUp = std::tan(fov.angleUp), tanDown = std::tan(fov.angleDown);
\t\t\tconst float width = tanRight - tanLeft, height = tanUp - tanDown;
\t\t\tD3DMATRIX out{};
\t\t\tout._11 = 2.0f / width; out._22 = 2.0f / height;
\t\t\tout._31 = (tanRight + tanLeft) / width; out._32 = (tanUp + tanDown) / height;
\t\t\tout._33 = base._33; out._34 = base._34; out._43 = base._43; out._44 = base._44;
\t\t\treturn out;
\t\t}

\t\tbool MatrixNear(const float* candidate, const D3DMATRIX& matrix, bool transposed, float epsilon)
\t\t{''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\tbool ImageContainsRange(std::uintptr_t rva, std::size_t size)
\t\t{''',
'''\t\tbool IsWritableRange(void* address, std::size_t size)
\t\t{
\t\t\tif (!address || size == 0) return false;
\t\t\tMEMORY_BASIC_INFORMATION info{};
\t\t\tif (VirtualQuery(address, &info, sizeof(info)) != sizeof(info) || info.State != MEM_COMMIT ||
\t\t\t\t(info.Protect & PAGE_GUARD) || (info.Protect & PAGE_NOACCESS)) return false;
\t\t\tconst DWORD protect = info.Protect & 0xFFu;
\t\t\tconst bool writable = protect == PAGE_READWRITE || protect == PAGE_WRITECOPY ||
\t\t\t\tprotect == PAGE_EXECUTE_READWRITE || protect == PAGE_EXECUTE_WRITECOPY;
\t\t\tif (!writable) return false;
\t\t\tconst auto begin = reinterpret_cast<std::uintptr_t>(address);
\t\t\tconst auto regionBegin = reinterpret_cast<std::uintptr_t>(info.BaseAddress);
\t\t\tconst auto regionEnd = regionBegin + info.RegionSize;
\t\t\treturn begin >= regionBegin && begin + size >= begin && begin + size <= regionEnd;
\t\t}

\t\tbool ImageContainsRange(std::uintptr_t rva, std::size_t size)
\t\t{''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\t\tstd::memcpy(&view, RendererView, sizeof(view));
\t\t\tstd::memcpy(&projection, RendererProjection, sizeof(projection));
\t\t\tstd::memcpy(&worldView, RendererWorldView, sizeof(worldView));''',
'''\t\t\tstd::memcpy(&view, RendererView, sizeof(view));
\t\t\tif (CullingProjectionOverridden) projection = CullingProjectionSaved;
\t\t\telse std::memcpy(&projection, RendererProjection, sizeof(projection));
\t\t\tstd::memcpy(&worldView, RendererWorldView, sizeof(worldView));''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\t\tpose.stereoValid = (snapshot.flags & StereoViewsValid) != 0 &&
\t\t\t\tFovValid(snapshot.eyeFov[0]) && FovValid(snapshot.eyeFov[1]);''',
'''\t\t\tpose.stereoValid = (snapshot.flags & StereoViewsValid) != 0 &&
\t\t\t\t(snapshot.flags & StereoEyeOrientationValid) != 0 &&
\t\t\t\tFovValid(snapshot.eyeFov[0]) && FovValid(snapshot.eyeFov[1]);''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\t\t\t\t\tpose.eyeOffset[eye][axis] = value;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}''',
'''\t\t\t\t\t\tpose.eyeOffset[eye][axis] = value;
\t\t\t\t\t}
\t\t\t\t\tconst Quat eyeQ{ snapshot.eyeOrientation[eye][0], snapshot.eyeOrientation[eye][1],
\t\t\t\t\t\tsnapshot.eyeOrientation[eye][2], snapshot.eyeOrientation[eye][3] };
\t\t\t\t\tif (!QuaternionIsSane(eyeQ)) pose.stereoValid = false;
\t\t\t\t\telse pose.eyeOrientation[eye] = Normalize(eyeQ);
\t\t\t\t}
\t\t\t}''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\tvoid RestoreCullingCamera()
\t\t{
\t\t\tif (!CullingCameraOverridden || !CullingCameraObject)
\t\t\t\treturn;
\t\t\tCullingCameraObject->cam_pos_F8 = CullingCameraSavedPos;
\t\t\tCullingCameraObject->look_pos_104 = CullingCameraSavedLook;
\t\t\tCullingCameraObject = nullptr;
\t\t\tCullingCameraOverridden = false;
\t\t}''',
'''\t\tvoid RestoreCullingCamera()
\t\t{
\t\t\tif (CullingCameraOverridden && CullingCameraObject)
\t\t\t{
\t\t\t\tCullingCameraObject->cam_pos_F8 = CullingCameraSavedPos;
\t\t\t\tCullingCameraObject->look_pos_104 = CullingCameraSavedLook;
\t\t\t}
\t\t\tCullingCameraObject = nullptr;
\t\t\tCullingCameraOverridden = false;
\t\t\tif (CullingProjectionOverridden && RendererProjection)
\t\t\t{
\t\t\t\tauto* projection = const_cast<D3DMATRIX*>(RendererProjection);
\t\t\t\tif (IsWritableRange(projection, sizeof(D3DMATRIX))) std::memcpy(projection, &CullingProjectionSaved, sizeof(D3DMATRIX));
\t\t\t}
\t\t\tCullingProjectionOverridden = false;
\t\t}''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\t\tCullingCameraOverridden = true;
\t\t\tFrameTelemetryFlags |= ClientCullingCameraSynced;''',
'''\t\t\tCullingCameraOverridden = true;
\t\t\tif (Settings::VRCullingUnionFov && LatchedStereo.valid && RendererProjection)
\t\t\t{
\t\t\t\tauto* projection = const_cast<D3DMATRIX*>(RendererProjection);
\t\t\t\tD3DMATRIX baseProjection{}; std::memcpy(&baseProjection, RendererProjection, sizeof(baseProjection));
\t\t\t\tSharedFov unionFov{};
\t\t\t\tunionFov.angleLeft = std::min(LatchedStereo.eyeFov[0].angleLeft, LatchedStereo.eyeFov[1].angleLeft);
\t\t\t\tunionFov.angleRight = std::max(LatchedStereo.eyeFov[0].angleRight, LatchedStereo.eyeFov[1].angleRight);
\t\t\t\tunionFov.angleUp = std::max(LatchedStereo.eyeFov[0].angleUp, LatchedStereo.eyeFov[1].angleUp);
\t\t\t\tunionFov.angleDown = std::min(LatchedStereo.eyeFov[0].angleDown, LatchedStereo.eyeFov[1].angleDown);
\t\t\t\tconst D3DMATRIX widened = ProjectionFromFov(baseProjection, unionFov);
\t\t\t\tif (MatrixFinite(widened) && IsWritableRange(projection, sizeof(D3DMATRIX)))
\t\t\t\t{
\t\t\t\t\tCullingProjectionSaved = baseProjection;
\t\t\t\t\tstd::memcpy(projection, &widened, sizeof(widened));
\t\t\t\t\tCullingProjectionOverridden = true;
\t\t\t\t}
\t\t\t}
\t\t\tFrameTelemetryFlags |= ClientCullingCameraSynced;''')
replace_once("src/vr_renderer_probe.cpp",
'''\t\t\trelativeOrientation = ScaleRotation(relativeOrientation, Settings::VRRotationScale);
\t\t\tLatchedHeadInverse = InverseRigid(MatrixFromPose(relativeOrientation, relativePosition));
\t\t\tLatchedHeadInverseValid = MatrixFinite(LatchedHeadInverse);
\t\t\tLatchedPoseSequence = sample.sequence;

\t\t\tif (LatchedHeadInverseValid && sample.stereoValid)
\t\t\t{
\t\t\t\tLatchedStereo.valid = true;
\t\t\t\tLatchedStereo.poseSequence = sample.sequence;
\t\t\t\tLatchedStereo.eyeFov[0] = sample.eyeFov[0];
\t\t\t\tLatchedStereo.eyeFov[1] = sample.eyeFov[1];
\t\t\t\tstd::memcpy(LatchedStereo.eyeOffset, sample.eyeOffset, sizeof(LatchedStereo.eyeOffset));
\t\t\t}''',
'''\t\t\trelativeOrientation = ScaleRotation(relativeOrientation, Settings::VRRotationScale);
\t\t\tLatchedHeadInverse = InverseRigid(MatrixFromPose(relativeOrientation, relativePosition));
\t\t\tLatchedHeadInverseValid = MatrixFinite(LatchedHeadInverse);
\t\t\tLatchedPoseSequence = sample.sequence;

\t\t\tif (LatchedHeadInverseValid && sample.stereoValid)
\t\t\t{
\t\t\t\tLatchedStereo.valid = true;
\t\t\t\tLatchedStereo.poseSequence = sample.sequence;
\t\t\t\tLatchedStereo.eyeFov[0] = sample.eyeFov[0]; LatchedStereo.eyeFov[1] = sample.eyeFov[1];
\t\t\t\tstd::memcpy(LatchedStereo.eyeOffset, sample.eyeOffset, sizeof(LatchedStereo.eyeOffset));
\t\t\t\tconst Quat effectiveHeadOrientation = Multiply(Normalize(CenterOrientation), relativeOrientation);
\t\t\t\tVec3 effectiveHeadPosition = sample.position;
\t\t\t\tif (!Settings::VRPositionalTracking || !sample.positionValid) effectiveHeadPosition = CenterPositionValid ? CenterPosition : sample.position;
\t\t\t\tfor (int eye = 0; eye < 2; ++eye)
\t\t\t\t{
\t\t\t\t\tconst Quat eyeOrientation = sample.eyeOrientation[eye];
\t\t\t\t\tLatchedStereo.eyeOrientation[eye][0]=eyeOrientation.x; LatchedStereo.eyeOrientation[eye][1]=eyeOrientation.y;
\t\t\t\t\tLatchedStereo.eyeOrientation[eye][2]=eyeOrientation.z; LatchedStereo.eyeOrientation[eye][3]=eyeOrientation.w;
\t\t\t\t\tconst Quat effectiveEyeOrientation = Multiply(effectiveHeadOrientation, eyeOrientation);
\t\t\t\t\tLatchedStereo.effectiveEyeOrientation[eye][0]=effectiveEyeOrientation.x; LatchedStereo.effectiveEyeOrientation[eye][1]=effectiveEyeOrientation.y;
\t\t\t\t\tLatchedStereo.effectiveEyeOrientation[eye][2]=effectiveEyeOrientation.z; LatchedStereo.effectiveEyeOrientation[eye][3]=effectiveEyeOrientation.w;
\t\t\t\t\tconst Vec3 localEye{sample.eyeOffset[eye][0], sample.eyeOffset[eye][1], sample.eyeOffset[eye][2]};
\t\t\t\t\tconst Vec3 worldEye = RotateVector(effectiveHeadOrientation, localEye);
\t\t\t\t\tLatchedStereo.effectiveEyePosition[eye][0]=effectiveHeadPosition.x+worldEye.x;
\t\t\t\t\tLatchedStereo.effectiveEyePosition[eye][1]=effectiveHeadPosition.y+worldEye.y;
\t\t\t\t\tLatchedStereo.effectiveEyePosition[eye][2]=effectiveHeadPosition.z+worldEye.z;
\t\t\t\t}
\t\t\t}''')

# Stereo file core changes
replace_once("src/vr_stereo.cpp",'''\t\tHANDLE SharedMapping = nullptr;
\t\tOutRunVR::SharedPoseState* SharedState = nullptr;''','''\t\tHANDLE SharedMapping = nullptr;
\t\tOutRunVR::SharedPoseState* SharedState = nullptr;
\t\tHANDLE RenderFrameMapping = nullptr;
\t\tOutRunVR::SharedRenderFrameState* RenderFrameState = nullptr;''')
replace_once("src/vr_stereo.cpp",'''\t\tbool FrameHadDuplicatedDraw = false;
\t\tbool FrameHadWorldStereo = false;
\t\tbool FrameRightDrawFailed = false;
\t\tstd::uint32_t FrameStereoPoseSequence = 0;
\t\tstd::uint32_t StereoFrameCounter = 0;''','''\t\tbool FrameHadDuplicatedDraw = false;
\t\tbool FrameHadWorldStereo = false;
\t\tbool FrameRightDrawFailed = false;
\t\tbool FrameStereoIncomplete = false;
\t\tOutRunVR::StereoFailureReason FrameFailureReason = OutRunVR::StereoFailureNone;
\t\tstd::uint32_t FrameStereoPoseSequence = 0;
\t\tOutRunVRRenderer::LatchedStereoFrame FrameStereoMetadata{};
\t\tstd::uint32_t StereoFrameCounter = 0;
\t\tbool RightDepthSynchronized = true;''')
replace_once("src/vr_stereo.cpp",'''\t\tD3DMATRIX MultiplyMatrix(const D3DMATRIX& a, const D3DMATRIX& b)
\t\t{''','''\t\tD3DMATRIX MatrixFromQuaternionTranslation(const float qIn[4], const float position[3], float positionScale)
\t\t{
\t\t\tfloat x=qIn[0],y=qIn[1],z=qIn[2],w=qIn[3]; const float lenSq=x*x+y*y+z*z+w*w;
\t\t\tif (!std::isfinite(lenSq)||lenSq<=1.0e-12f) return IdentityMatrix(); const float inv=1.0f/std::sqrt(lenSq); x*=inv;y*=inv;z*=inv;w*=inv;
\t\t\tD3DMATRIX out=IdentityMatrix(); const float xx=x*x,yy=y*y,zz=z*z,xy=x*y,xz=x*z,yz=y*z,xw=x*w,yw=y*w,zw=z*w;
\t\t\tout._11=1-2*(yy+zz);out._12=2*(xy+zw);out._13=2*(xz-yw);out._21=2*(xy-zw);out._22=1-2*(xx+zz);out._23=2*(yz+xw);
\t\t\tout._31=2*(xz+yw);out._32=2*(yz-xw);out._33=1-2*(xx+yy);out._41=position[0]*positionScale;out._42=position[1]*positionScale;out._43=position[2]*positionScale; return out;
\t\t}
\t\tD3DMATRIX InverseRigid(const D3DMATRIX& m)
\t\t{
\t\t\tD3DMATRIX out=IdentityMatrix(); out._11=m._11;out._12=m._21;out._13=m._31;out._21=m._12;out._22=m._22;out._23=m._32;out._31=m._13;out._32=m._23;out._33=m._33;
\t\t\tout._41=-(m._41*out._11+m._42*out._21+m._43*out._31);out._42=-(m._41*out._12+m._42*out._22+m._43*out._32);out._43=-(m._41*out._13+m._42*out._23+m._43*out._33); return out;
\t\t}

\t\tD3DMATRIX MultiplyMatrix(const D3DMATRIX& a, const D3DMATRIX& b)
\t\t{''')
replace_once("src/vr_stereo.cpp",'''\t\t\tfor (int eye = 0; eye < 2; ++eye)
\t\t\t{
\t\t\t\tD3DMATRIX eyeInverse = IdentityMatrix();
\t\t\t\teyeInverse._41 = -stereo.eyeOffset[eye][0] * Settings::VRWorldScale;
\t\t\t\teyeInverse._42 = -stereo.eyeOffset[eye][1] * Settings::VRWorldScale;
\t\t\t\teyeInverse._43 = -stereo.eyeOffset[eye][2] * Settings::VRWorldScale;''','''\t\t\tfor (int eye = 0; eye < 2; ++eye)
\t\t\t{
\t\t\t\tconst D3DMATRIX eyePose = MatrixFromQuaternionTranslation(stereo.eyeOrientation[eye], stereo.eyeOffset[eye], Settings::VRWorldScale);
\t\t\t\tconst D3DMATRIX eyeInverse = InverseRigid(eyePose);''')
replace_once("src/vr_stereo.cpp",'''\t\tstruct DrawStereoState
\t\t{''','''\t\tbool EnsureRenderFrameState()
\t\t{
\t\t\tif (RenderFrameState) return RenderFrameState->magic==OutRunVR::RenderFrameMagic && RenderFrameState->protocolVersion==OutRunVR::RenderFrameProtocolVersion && RenderFrameState->structSize==sizeof(OutRunVR::SharedRenderFrameState);
\t\t\tRenderFrameMapping=CreateFileMappingW(INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,static_cast<DWORD>(sizeof(OutRunVR::SharedRenderFrameState)),OutRunVR::RenderFrameMemoryName); if(!RenderFrameMapping)return false;
\t\t\tconst bool existed=GetLastError()==ERROR_ALREADY_EXISTS; RenderFrameState=static_cast<OutRunVR::SharedRenderFrameState*>(MapViewOfFile(RenderFrameMapping,FILE_MAP_ALL_ACCESS,0,0,sizeof(OutRunVR::SharedRenderFrameState))); if(!RenderFrameState)return false;
\t\t\tif(!existed){std::memset(RenderFrameState,0,sizeof(*RenderFrameState));RenderFrameState->protocolVersion=OutRunVR::RenderFrameProtocolVersion;RenderFrameState->structSize=sizeof(*RenderFrameState);MemoryBarrier();RenderFrameState->magic=OutRunVR::RenderFrameMagic;}
\t\t\treturn RenderFrameState->magic==OutRunVR::RenderFrameMagic && RenderFrameState->protocolVersion==OutRunVR::RenderFrameProtocolVersion && RenderFrameState->structSize==sizeof(*RenderFrameState);
\t\t}
\t\tvoid PoisonFrame(OutRunVR::StereoFailureReason reason){FrameStereoIncomplete=true;if(FrameFailureReason==OutRunVR::StereoFailureNone)FrameFailureReason=reason;}

\t\tstruct DrawStereoState
\t\t{''')
replace_once("src/vr_stereo.cpp",'''\t\t\tbool worldStereo = false;
\t\t\tstd::uint32_t poseSequence = 0;
\t\t};''','''\t\t\tbool worldStereo = false;
\t\t\tstd::uint32_t poseSequence = 0;
\t\t\tOutRunVRRenderer::LatchedStereoFrame stereoFrame{};
\t\t};''')
replace_once("src/vr_stereo.cpp",'''\t\t\tReleaseCom(RightEyeDepth);
\t\t\tif (!TrackedDepthStencil)
\t\t\t\treturn true;''','''\t\t\tReleaseCom(RightEyeDepth);
\t\t\tRightDepthSynchronized = TrackedDepthStencil == nullptr;
\t\t\tif (!TrackedDepthStencil)
\t\t\t\treturn true;''')
replace_once("src/vr_stereo.cpp",'''\t\t\tFrameRightDrawFailed = true;
\t\t\t++RestoreFailures;''','''\t\t\tFrameRightDrawFailed = true;
\t\t\tPoisonFrame(OutRunVR::StereoFailureRestoreFailed);
\t\t\t++RestoreFailures;''')
replace_once("src/vr_stereo.cpp",'''\t\tstruct ScreenVertex
\t\t{''','''\t\tvoid PublishRenderFrame(std::uint32_t state,std::uint32_t frameId,std::uint32_t sourcePoseSequence,std::int64_t presentQpc,OutRunVR::StereoFailureReason failureReason,const OutRunVRRenderer::LatchedStereoFrame* stereo)
\t\t{
\t\t\tif(!EnsureRenderFrameState())return; LONG seq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameState->sequence));if((seq&1)==0)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameState->sequence));MemoryBarrier();
\t\t\tRenderFrameState->clientPid=GetCurrentProcessId();RenderFrameState->state=state;RenderFrameState->frameId=frameId;RenderFrameState->sourcePoseSequence=sourcePoseSequence;RenderFrameState->presentationMode=GameplayActive()?OutRunVR::PresentationGameplay:OutRunVR::PresentationTheater;RenderFrameState->flags=0;RenderFrameState->failureReason=static_cast<std::uint32_t>(failureReason);RenderFrameState->backbufferWidth=BackBufferDesc.Width;RenderFrameState->backbufferHeight=BackBufferDesc.Height;RenderFrameState->presentQpc=presentQpc;std::memset(RenderFrameState->eye,0,sizeof(RenderFrameState->eye));
\t\t\tif(state==OutRunVR::StereoSbsActive&&stereo&&stereo->valid&&frameId){RenderFrameState->flags=OutRunVR::RenderFrameStereoComplete|OutRunVR::RenderFrameWorldStereo|OutRunVR::RenderFrameDrawDuplicated|OutRunVR::RenderFrameEffectivePoseValid;for(int eye=0;eye<2;++eye){std::memcpy(RenderFrameState->eye[eye].orientation,stereo->effectiveEyeOrientation[eye],sizeof(RenderFrameState->eye[eye].orientation));std::memcpy(RenderFrameState->eye[eye].position,stereo->effectiveEyePosition[eye],sizeof(RenderFrameState->eye[eye].position));RenderFrameState->eye[eye].fov=stereo->eyeFov[eye];}}
\t\t\tMemoryBarrier();seq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameState->sequence));if(seq&1)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameState->sequence));
\t\t}

\t\tstruct ScreenVertex
\t\t{''')
replace_once("src/vr_stereo.cpp",'''\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoFrameIndex]), 0);

\t\t\tif (state != OutRunVR::StereoSbsActive''','''\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoFrameIndex]), 0);
\t\t\tconst LONG stereoBits=static_cast<LONG>(OutRunVR::ClientStereoActive|OutRunVR::ClientStereoWorldDraw|OutRunVR::ClientStereoDrawDuplicated);
\t\t\tInterlockedAnd(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientFlagsIndex]), ~stereoBits);

\t\t\tif (state != OutRunVR::StereoSbsActive''')
replace_once("src/vr_stereo.cpp",'''\t\tbool PrepareDuplicatedDraw(IDirect3DDevice9* device, DrawStereoState& draw)
\t\t{
\t\t\tif (InternalStereoPass || !StereoWanted() || !TargetIsBackBuffer())
\t\t\t\treturn false;
\t\t\tif (AnyAuxRenderTargetActive())
\t\t\t{
\t\t\t\t++MrtRejectedDraws;
\t\t\t\tif (!FirstMrtRejectLogged)
\t\t\t\t{
\t\t\t\t\tFirstMrtRejectLogged = true;
\t\t\t\t\tspdlog::info("VR stereo: auxiliary MRT active; draw left untouched to avoid double-writing RT1+");
\t\t\t\t}
\t\t\t\treturn false;
\t\t\t}
\t\t\tif (!EnsureStereoResources(device))
\t\t\t\treturn false;

\t\t\tOutRunVRRenderer::LatchedStereoFrame stereo{};
\t\t\tif (!OutRunVRRenderer::GetLatchedStereoFrame(stereo))
\t\t\t\treturn false;
\t\t\tBuildEyeConstants(device, stereo, draw);
\t\t\treturn true;
\t\t}''','''\t\tbool PrepareDuplicatedDraw(IDirect3DDevice9* device, DrawStereoState& draw)
\t\t{
\t\t\tif (InternalStereoPass || !StereoWanted() || !TargetIsBackBuffer()) return false;
\t\t\tif (AnyAuxRenderTargetActive()){PoisonFrame(OutRunVR::StereoFailureMrtActive);++MrtRejectedDraws;if(!FirstMrtRejectLogged){FirstMrtRejectLogged=true;spdlog::info("VR stereo: auxiliary MRT active; current Present is marked incomplete");}return false;}
\t\t\tif(!EnsureStereoResources(device)){PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);return false;}
\t\t\tif(TrackedDepthStencil&&!RightDepthSynchronized){PoisonFrame(OutRunVR::StereoFailureDepthUnsynchronized);return false;}
\t\t\tOutRunVRRenderer::LatchedStereoFrame stereo{};if(!OutRunVRRenderer::GetLatchedStereoFrame(stereo)){PoisonFrame(OutRunVR::StereoFailureMissingLatchedPose);return false;}
\t\t\tdraw.stereoFrame=stereo;BuildEyeConstants(device,stereo,draw);return true;
\t\t}''')
replace_once("src/vr_stereo.cpp",'''\t\t\tD3DVIEWPORT9 savedViewport{};
\t\t\tif (FAILED(device->GetViewport(&savedViewport)))
\t\t\t\treturn drawCall();

\t\t\tif (draw.worldStereo && !SetWvpOneRegisterAtATime(device, draw.eyeConstants[0]))
\t\t\t\treturn drawCall();''','''\t\t\tD3DVIEWPORT9 savedViewport{};
\t\t\tif(FAILED(device->GetViewport(&savedViewport))){PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return drawCall();}
\t\t\tif(draw.worldStereo&&!SetWvpOneRegisterAtATime(device,draw.eyeConstants[0])){const bool rolledBack=SetWvpOneRegisterAtATime(device,draw.originalConstants);PoisonFrame(OutRunVR::StereoFailureLeftWvpUploadFailed);if(!rolledBack)NoteRestoreFailure("left-eye c64 rollback");return drawCall();}''')
replace_once("src/vr_stereo.cpp",'''\t\t\tif (FAILED(leftHr))
\t\t\t{
\t\t\t\tif (draw.worldStereo && !SetWvpOneRegisterAtATime(device, draw.originalConstants))
\t\t\t\t\tNoteRestoreFailure("left draw c64");
\t\t\t\treturn leftHr;
\t\t\t}''','''\t\t\tif(FAILED(leftHr)){PoisonFrame(OutRunVR::StereoFailureLeftDrawFailed);if(draw.worldStereo&&!SetWvpOneRegisterAtATime(device,draw.originalConstants))NoteRestoreFailure("left draw c64");return leftHr;}''')
replace_once("src/vr_stereo.cpp",'''\t\t\t\tif (FrameStereoPoseSequence == 0)
\t\t\t\t\tFrameStereoPoseSequence = draw.poseSequence;
\t\t\t\telse if (FrameStereoPoseSequence != draw.poseSequence)
\t\t\t\t{
\t\t\t\t\tFrameRightDrawFailed = true;
\t\t\t\t\tspdlog::warn("VR stereo: multiple host pose sequences reached one Present; frame forced to mono fallback");
\t\t\t\t}''','''\t\t\t\tif(FrameStereoPoseSequence==0){FrameStereoPoseSequence=draw.poseSequence;FrameStereoMetadata=draw.stereoFrame;}
\t\t\t\telse if(FrameStereoPoseSequence!=draw.poseSequence){FrameRightDrawFailed=true;PoisonFrame(OutRunVR::StereoFailurePoseSequenceMismatch);spdlog::warn("VR stereo: multiple host pose sequences reached one Present; frame forced to mono fallback");}''')
replace_once("src/vr_stereo.cpp",'''\t\t\tif (FAILED(rightHr))
\t\t\t\tFrameRightDrawFailed = true;''','''\t\t\tif(FAILED(rightHr)){FrameRightDrawFailed=true;PoisonFrame(draw.worldStereo?OutRunVR::StereoFailureRightWvpUploadFailed:OutRunVR::StereoFailureRightDrawFailed);}''')

# ClearDest by regex
p=re.compile(r'\t\tHRESULT __stdcall ClearDest\(IDirect3DDevice9\* device, DWORD count, const D3DRECT\* rects,\n.*?\t\t}\n\n\t\tHRESULT __stdcall SetRenderTargetDest',re.S);t=read("src/vr_stereo.cpp");m=p.search(t)
if not m: raise RuntimeError("ClearDest block not found")
new=r'''\t\tHRESULT __stdcall ClearDest(IDirect3DDevice9* device, DWORD count, const D3DRECT* rects,
\t\t\tDWORD flags, D3DCOLOR color, float z, DWORD stencil)
\t\t{
\t\t\tconst bool candidate=!InternalStereoPass&&StereoWanted()&&TargetIsBackBuffer();bool duplicate=candidate;
\t\t\tif(duplicate&&AnyAuxRenderTargetActive()){PoisonFrame(OutRunVR::StereoFailureMrtActive);duplicate=false;}
\t\t\tif(duplicate&&!EnsureStereoResources(device)){PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);duplicate=false;}
\t\t\tconst HRESULT leftHr=ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);if(!duplicate||FAILED(leftHr)){if(candidate&&FAILED(leftHr))PoisonFrame(OutRunVR::StereoFailureClearFailed);return leftHr;}
\t\t\tD3DVIEWPORT9 savedViewport{};if(FAILED(device->GetViewport(&savedViewport))){PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return leftHr;}
\t\t\tIDirect3DSurface9* savedRt=TrackedRenderTarget;IDirect3DSurface9* savedDepth=TrackedDepthStencil;HRESULT rightHr=D3D_OK;bool restoreOk=true;{
\t\t\t\tInternalPassScope guard;rightHr=SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface);if(SUCCEEDED(rightHr))rightHr=SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth);if(SUCCEEDED(rightHr))rightHr=device->SetViewport(&savedViewport);if(SUCCEEDED(rightHr))rightHr=ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);restoreOk=RestoreRightPassState(device,savedRt,savedDepth,savedViewport,nullptr,false);}
\t\t\tif(FAILED(rightHr)){FrameRightDrawFailed=true;PoisonFrame(OutRunVR::StereoFailureClearFailed);}else if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=true;if(!restoreOk)NoteRestoreFailure("right-eye clear");return leftHr;
\t\t}

\t\tHRESULT __stdcall SetRenderTargetDest'''
write("src/vr_stereo.cpp",t[:m.start()]+new+t[m.end():])
replace_once("src/vr_stereo.cpp",'''\t\t\t\tconst bool changed = TrackedDepthStencil != surface;
\t\t\t\tReplaceSurfaceRef(TrackedDepthStencil, surface);
\t\t\t\tif (changed && StereoResourcesReady && !CreateRightDepthForTracked(device))
\t\t\t\t\tStereoResourcesReady = false;''','''\t\t\t\tconst bool changed=TrackedDepthStencil!=surface;ReplaceSurfaceRef(TrackedDepthStencil,surface);if(changed){if(StereoWanted()&&TargetIsBackBuffer())PoisonFrame(OutRunVR::StereoFailureDepthStateChanged);if(StereoResourcesReady&&!CreateRightDepthForTracked(device))StereoResourcesReady=false;}''')
replace_once("src/vr_stereo.cpp",'''\t\t\t\tCurrentVertexShaderIdentity.store(reinterpret_cast<std::uintptr_t>(shader), std::memory_order_release);
\t\t\t\tstd::uint64_t serial = VertexShaderSerial.fetch_add(1, std::memory_order_acq_rel) + 1;
\t\t\t\tif (serial == 0)
\t\t\t\t\tVertexShaderSerial.fetch_add(1, std::memory_order_acq_rel);''','''\t\t\t\tconst std::uintptr_t next=reinterpret_cast<std::uintptr_t>(shader);const std::uintptr_t previous=CurrentVertexShaderIdentity.load(std::memory_order_acquire);if(next!=previous){CurrentVertexShaderIdentity.store(next,std::memory_order_release);std::uint64_t serial=VertexShaderSerial.fetch_add(1,std::memory_order_acq_rel)+1;if(serial==0)VertexShaderSerial.fetch_add(1,std::memory_order_acq_rel);}''')

# Present by regex
p=re.compile(r'\t\tHRESULT __stdcall PresentDest\(IDirect3DDevice9\* device, const RECT\* sourceRect,\n.*?\t\t}\n\n\t\tHRESULT __stdcall ResetDest',re.S);t=read("src/vr_stereo.cpp");m=p.search(t)
if not m: raise RuntimeError("PresentDest block not found")
new=r'''\t\tHRESULT __stdcall PresentDest(IDirect3DDevice9* device,const RECT* sourceRect,const RECT* destRect,HWND destWindowOverride,const RGNDATA* dirtyRegion)
\t\t{
\t\t\tif(!IsGameDevice(device))return PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);const bool stereoRequested=StereoWanted();bool composedStereo=false;std::uint32_t pendingPoseSequence=0;
\t\t\tif(stereoRequested&&FrameHadWorldStereo&&FrameHadDuplicatedDraw&&!FrameRightDrawFailed&&!FrameStereoIncomplete&&FrameStereoPoseSequence&&FrameStereoMetadata.valid&&EnsureStereoResources(device)){if(ComposeSbs(device)){++StereoComposeSuccess;composedStereo=true;pendingPoseSequence=FrameStereoPoseSequence;}else{++StereoComposeFailure;PoisonFrame(OutRunVR::StereoFailureComposeFailed);}}
\t\t\tMaybeLogSummary();LARGE_INTEGER presentStart{};QueryPerformanceCounter(&presentStart);const HRESULT hr=PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);
\t\t\tif(composedStereo&&SUCCEEDED(hr)&&!FrameStereoIncomplete){const std::uint32_t frameId=NextStereoFrameId();std::uint32_t low=static_cast<std::uint32_t>(presentStart.QuadPart);if(!low)low=1;PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,frameId,low);PublishRenderFrame(OutRunVR::StereoSbsActive,frameId,pendingPoseSequence,presentStart.QuadPart,OutRunVR::StereoFailureNone,&FrameStereoMetadata);if(!FirstStereoActiveLogged){FirstStereoActiveLogged=true;spdlog::info("VR stereo: SBS transport active; exact effective eye pose published in Frame.v1");}}
\t\t\telse{if(FAILED(hr)&&FrameFailureReason==OutRunVR::StereoFailureNone)FrameFailureReason=OutRunVR::StereoFailurePresentFailed;const std::uint32_t fallback=stereoRequested?OutRunVR::StereoSbsFallbackMono:OutRunVR::StereoDisabled;PublishStereoState(fallback,false,0,0,0);PublishRenderFrame(fallback,0,0,presentStart.QuadPart,FrameFailureReason,nullptr);}
\t\t\tFrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata={};return hr;
\t\t}

\t\tHRESULT __stdcall ResetDest'''
write("src/vr_stereo.cpp",t[:m.start()]+new+t[m.end():])
replace_once("src/vr_stereo.cpp",'''\t\t\tPublishStereoState(OutRunVR::StereoDisabled, false, 0, 0, 0);
\t\t\tconst HRESULT hr = ResetHook.stdcall<HRESULT>(device, params);''','''\t\t\tFrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoMetadata={};PublishStereoState(OutRunVR::StereoDisabled,false,0,0,0);PublishRenderFrame(OutRunVR::StereoDisabled,0,0,0,OutRunVR::StereoFailureNone,nullptr);const HRESULT hr=ResetHook.stdcall<HRESULT>(device,params);''')
replace_once("src/vr_stereo.cpp",'''\t\t\tEnsureSharedState();
\t\t\tEnsureStereoResources(device);''','''\t\t\tEnsureSharedState();
\t\t\tEnsureRenderFrameState();
\t\t\tEnsureStereoResources(device);''')

# Host changes
replace_once("vrhost/main_stereo.cpp",'''    XrVector3f ToHeadLocal(const XrPosef& head, const XrVector3f& world)
    {''','''    XrQuaternionf NormalizeQuaternion(XrQuaternionf q){const float l=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;if(!std::isfinite(l)||l<=1e-12f)return{0,0,0,1};const float i=1.0f/std::sqrt(l);q.x*=i;q.y*=i;q.z*=i;q.w*=i;return q;}
    XrQuaternionf ConjugateQuaternion(XrQuaternionf q){q=NormalizeQuaternion(q);return{-q.x,-q.y,-q.z,q.w};}
    XrQuaternionf MultiplyQuaternion(const XrQuaternionf&aIn,const XrQuaternionf&bIn){const auto a=NormalizeQuaternion(aIn),b=NormalizeQuaternion(bIn);return NormalizeQuaternion({a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z});}

    XrVector3f ToHeadLocal(const XrPosef& head, const XrVector3f& world)
    {''')
replace_once("vrhost/main_stereo.cpp",'''        XrQuaternionf inv{
            -head.orientation.x, -head.orientation.y,
            -head.orientation.z, head.orientation.w
        };
        return RotateVector(inv, delta);
    }''','''        return RotateVector(ConjugateQuaternion(head.orientation),delta);
    }
    XrQuaternionf ToHeadLocalOrientation(const XrPosef& head,const XrPosef& eye){return MultiplyQuaternion(ConjugateQuaternion(head.orientation),eye.orientation);}''')
replace_once("vrhost/main_stereo.cpp",'''            if (stereoValid) flags |= OutRunVR::StereoViewsValid;''','''            if(stereoValid)flags|=OutRunVR::StereoViewsValid|OutRunVR::StereoEyeOrientationValid;''')
replace_once("vrhost/main_stereo.cpp",'''                state_->recommendedWidth[eye] = configs[eye].recommendedImageRectWidth;
                state_->recommendedHeight[eye] = configs[eye].recommendedImageRectHeight;
            }
            if (stereoValid)
            {
                const XrVector3f left = ToHeadLocal(head.pose, views[0].pose.position);
                const XrVector3f right = ToHeadLocal(head.pose, views[1].pose.position);''','''            }
            (void)configs;
            if(stereoValid)
            {
                const XrVector3f left=ToHeadLocal(head.pose,views[0].pose.position),right=ToHeadLocal(head.pose,views[1].pose.position);
                const XrQuaternionf eq[2]={ToHeadLocalOrientation(head.pose,views[0].pose),ToHeadLocalOrientation(head.pose,views[1].pose)};
                for(int eye=0;eye<2;++eye){state_->eyeOrientation[eye][0]=eq[eye].x;state_->eyeOrientation[eye][1]=eq[eye].y;state_->eyeOrientation[eye][2]=eq[eye].z;state_->eyeOrientation[eye][3]=eq[eye].w;}''')
replace_once("vrhost/main_stereo.cpp",'''    struct ViewHistoryEntry
    {''','''    class RenderFrameReader
    {
    public:
        RenderFrameReader(){mapping_=CreateFileMappingW(INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,static_cast<DWORD>(sizeof(OutRunVR::SharedRenderFrameState)),OutRunVR::RenderFrameMemoryName);if(!mapping_)throw std::runtime_error("CreateFileMappingW Frame.v1 failed");const bool existed=GetLastError()==ERROR_ALREADY_EXISTS;state_=static_cast<OutRunVR::SharedRenderFrameState*>(MapViewOfFile(mapping_,FILE_MAP_ALL_ACCESS,0,0,sizeof(OutRunVR::SharedRenderFrameState)));if(!state_)throw std::runtime_error("MapViewOfFile Frame.v1 failed");if(!existed){std::memset(state_,0,sizeof(*state_));state_->protocolVersion=OutRunVR::RenderFrameProtocolVersion;state_->structSize=sizeof(*state_);MemoryBarrier();state_->magic=OutRunVR::RenderFrameMagic;}}
        ~RenderFrameReader(){if(state_)UnmapViewOfFile(state_);if(mapping_)CloseHandle(mapping_);}
        bool Read(OutRunVR::SharedRenderFrameState&out)const{if(!state_||state_->magic!=OutRunVR::RenderFrameMagic||state_->protocolVersion!=OutRunVR::RenderFrameProtocolVersion||state_->structSize!=sizeof(*state_))return false;for(int a=0;a<4;++a){const auto b=state_->sequence;if(b&1u)continue;MemoryBarrier();std::memcpy(&out,state_,sizeof(out));MemoryBarrier();const auto e=state_->sequence;if(b==e&&!(e&1u)&&out.magic==OutRunVR::RenderFrameMagic&&out.protocolVersion==OutRunVR::RenderFrameProtocolVersion&&out.structSize==sizeof(out))return true;}return false;}
    private: HANDLE mapping_=nullptr;OutRunVR::SharedRenderFrameState*state_=nullptr;
    };

    struct ViewHistoryEntry
    {''')
replace_once("vrhost/main_stereo.cpp",'''    struct CaptureStatus
    {
        bool available = false;
        bool fresh = false;
        std::uint32_t lastPresentQpcLow = 0;
    };''','''    struct CaptureStatus{bool available=false;bool fresh=false;std::int64_t lastPresentQpc=0;std::uint32_t lastPresentQpcLow=0;};''')
replace_once("vrhost/main_stereo.cpp",'''        bool Initialize()
        {
            targetMonitor_ = MonitorFromWindow(hwnd_, MONITOR_DEFAULTTONEAREST);
            sdrWhiteScale_ = QuerySdrWhiteScale(targetMonitor_);''','''        bool Initialize()
        {
            if(!BindCaptureOutput(true))throw std::runtime_error("failed to bind game capture output");
            CreateShaders();
            ChooseSwapchainFormat();
            CreateProjectionSwapchain();
            CreateTheaterSwapchain();
            std::cout << "OpenXR true stereo ready: projection " << projection_.width << "x" << projection_.height << "x2; theater " << theater_.width << "x" << theater_.height << ".\\n";
            return true;
        }

        bool InitializeLegacyCaptureRemoved()
        {
            targetMonitor_ = MonitorFromWindow(hwnd_, MONITOR_DEFAULTTONEAREST);
            sdrWhiteScale_ = QuerySdrWhiteScale(targetMonitor_);''')
# Remove unreachable legacy tail by renaming is deliberate; compiler accepts it, but avoid duplicate setup execution.
replace_once("vrhost/main_stereo.cpp",'''        CaptureStatus Capture()
        {
            CaptureStatus status{ haveFrame_, false, lastCapturePresentQpcLow_ };''','''        CaptureStatus Capture(DWORD timeoutMs=0)
        {
            if(!IsWindow(hwnd_)){if(HWND replacement=FindGameWindow(gamePid_))hwnd_=replacement;}
            const HMONITOR monitorNow=IsWindow(hwnd_)?MonitorFromWindow(hwnd_,MONITOR_DEFAULTTONEAREST):nullptr;if(!duplication_||(monitorNow&&monitorNow!=targetMonitor_))BindCaptureOutput(false);
            CaptureStatus status{haveFrame_,false,lastCapturePresentQpc_,lastCapturePresentQpcLow_};''')
replace_once("vrhost/main_stereo.cpp",'''            const HRESULT hr = duplication_->AcquireNextFrame(haveFrame_ ? 0 : 1000, &fi, &res);''','''            if(!duplication_)return status;const DWORD waitMs=haveFrame_?timeoutMs:std::max<DWORD>(timeoutMs,1000);const HRESULT hr=duplication_->AcquireNextFrame(waitMs,&fi,&res);''')
replace_once("vrhost/main_stereo.cpp",'''                    ReleaseCom(duplication_);
                    haveFrame_ = false;
                    stereoSourceValid_ = false;
                    RecreateDuplication(false);''','''                    haveFrame_=false;stereoSourceValid_=false;BindCaptureOutput(false);''')
replace_once("vrhost/main_stereo.cpp",'''                return { haveFrame_, false, lastCapturePresentQpcLow_ };''','''                return {haveFrame_,false,lastCapturePresentQpc_,lastCapturePresentQpcLow_};''')
replace_once("vrhost/main_stereo.cpp",'''                if (fi.LastPresentTime.QuadPart != 0)
                    lastCapturePresentQpcLow_ = static_cast<std::uint32_t>(fi.LastPresentTime.QuadPart);''','''                if(fi.LastPresentTime.QuadPart!=0){lastCapturePresentQpc_=fi.LastPresentTime.QuadPart;lastCapturePresentQpcLow_=static_cast<std::uint32_t>(fi.LastPresentTime.QuadPart);}''')
replace_once("vrhost/main_stereo.cpp",'''                status.available = true;
                status.fresh = fi.AccumulatedFrames > 0;
                status.lastPresentQpcLow = lastCapturePresentQpcLow_;''','''                status.available=true;status.fresh=fi.AccumulatedFrames>0;status.lastPresentQpc=lastCapturePresentQpc_;status.lastPresentQpcLow=lastCapturePresentQpcLow_;''')
replace_once("vrhost/main_stereo.cpp",'''        bool RecreateDuplication(bool initial)
        {''','''        bool BindCaptureOutput(bool initial)
        {
            if(HWND replacement=FindGameWindow(gamePid_))hwnd_=replacement;if(!IsWindow(hwnd_))return false;targetMonitor_=MonitorFromWindow(hwnd_,MONITOR_DEFAULTTONEAREST);if(!targetMonitor_)return false;ReleaseCom(duplication_);ReleaseCom(output5_);ReleaseCom(output1_);
            IDXGIDevice*dxgi=nullptr;if(FAILED(device_->QueryInterface(__uuidof(IDXGIDevice),reinterpret_cast<void**>(&dxgi)))||!dxgi)return false;IDXGIAdapter*adapter=nullptr;const HRESULT ah=dxgi->GetAdapter(&adapter);dxgi->Release();if(FAILED(ah)||!adapter)return false;IDXGIOutput*selected=nullptr;DXGI_OUTPUT_DESC desc{};for(UINT i=0;;++i){IDXGIOutput*out=nullptr;if(adapter->EnumOutputs(i,&out)==DXGI_ERROR_NOT_FOUND)break;DXGI_OUTPUT_DESC d{};out->GetDesc(&d);if(d.Monitor==targetMonitor_){selected=out;desc=d;break;}out->Release();}adapter->Release();if(!selected)return false;selected->QueryInterface(__uuidof(IDXGIOutput1),reinterpret_cast<void**>(&output1_));selected->QueryInterface(__uuidof(IDXGIOutput5),reinterpret_cast<void**>(&output5_));selected->Release();if(!output1_)return false;outputDesktop_=desc.DesktopCoordinates;sdrWhiteScale_=QuerySdrWhiteScale(targetMonitor_);haveFrame_=false;stereoSourceValid_=false;lastCapturePresentQpc_=0;lastCapturePresentQpcLow_=0;return RecreateDuplication(initial);
        }

        bool RecreateDuplication(bool initial)
        {''')
replace_once("vrhost/main_stereo.cpp",'''        bool haveFrame_ = false;
        std::uint32_t lastCapturePresentQpcLow_ = 0;''','''        bool haveFrame_=false;std::int64_t lastCapturePresentQpc_=0;std::uint32_t lastCapturePresentQpcLow_=0;''')
replace_once("vrhost/main_stereo.cpp",'''    bool QpcLowAtOrAfter(std::uint32_t capture, std::uint32_t present)
    {''','''    bool QpcAtOrAfter(std::int64_t capture,std::int64_t present){return capture>0&&present>0&&capture>=present;}
    struct TimingSeries{std::array<double,256>samples{};std::size_t count=0,cursor=0;void Add(double ms){samples[cursor++%samples.size()]=ms;if(count<samples.size())++count;}double Percentile(double p)const{if(!count)return 0;auto c=samples;std::sort(c.begin(),c.begin()+count);const std::size_t i=std::min<std::size_t>(count-1,static_cast<std::size_t>(std::ceil(p*count))-1);return c[i];}};
    struct HostTimings{TimingSeries wait,capture,render,end;LARGE_INTEGER f{};ULONGLONG last=0;HostTimings(){QueryPerformanceFrequency(&f);}double Ms(const LARGE_INTEGER&a,const LARGE_INTEGER&b)const{return f.QuadPart?double(b.QuadPart-a.QuadPart)*1000.0/double(f.QuadPart):0;}void MaybeLog(){const auto n=GetTickCount64();if(n-last<5000)return;last=n;std::cout<<"VR host timing ms p95/p99: wait "<<wait.Percentile(.95)<<"/"<<wait.Percentile(.99)<<" capture "<<capture.Percentile(.95)<<"/"<<capture.Percentile(.99)<<" render "<<render.Percentile(.95)<<"/"<<render.Percentile(.99)<<" end "<<end.Percentile(.95)<<"/"<<end.Percentile(.99)<<"\\n";}};

    bool QpcLowAtOrAfter(std::uint32_t capture, std::uint32_t present)
    {''')
replace_once("vrhost/main_stereo.cpp",'''        SharedWriter shared;
        StereoCompositor compositor(session, d3d.device, d3d.context, gameWindow, configs);
        compositor.Initialize();
        ViewHistory viewHistory;''','''        SharedWriter shared;RenderFrameReader renderFrames;StereoCompositor compositor(session,d3d.device,d3d.context,gameWindow,configs);compositor.Initialize();ViewHistory viewHistory;HostTimings timings;''')
replace_once("vrhost/main_stereo.cpp",'''        ULONGLONG lastStereoMatchMs = 0;

        while (!quit)''','''        ULONGLONG lastStereoMatchMs=0;bool pendingReferenceSpaceChange=false;XrTime pendingReferenceSpaceChangeTime=0;

        while (!quit)''')
replace_once("vrhost/main_stereo.cpp",'''                else if (event.type == XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING)
                {
                    shared.ReferenceSpaceChanged();
                    compositor.ReferenceSpaceChanged();
                    viewHistory.Clear();
                    matchedStereoValid = false;
                    lastProcessedStereoFrame = shared.ReadStereoMeta().frame;
                }''','''                else if(event.type==XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING){const auto*e=reinterpret_cast<XrEventDataReferenceSpaceChangePending*>(&event);if(e->referenceSpaceType==XR_REFERENCE_SPACE_TYPE_LOCAL){pendingReferenceSpaceChange=true;pendingReferenceSpaceChangeTime=e->changeTime;}}''')
replace_once("vrhost/main_stereo.cpp",'''            CheckXr(xrWaitFrame(session, &wi, &fs), "xrWaitFrame");
            XrFrameBeginInfo bi{ XR_TYPE_FRAME_BEGIN_INFO };''','''            LARGE_INTEGER ws{},we{};QueryPerformanceCounter(&ws);CheckXr(xrWaitFrame(session,&wi,&fs),"xrWaitFrame");QueryPerformanceCounter(&we);timings.wait.Add(timings.Ms(ws,we));
            if(pendingReferenceSpaceChange&&(pendingReferenceSpaceChangeTime==0||fs.predictedDisplayTime>=pendingReferenceSpaceChangeTime)){shared.ReferenceSpaceChanged();compositor.ReferenceSpaceChanged();viewHistory.Clear();matchedStereoValid=false;OutRunVR::SharedRenderFrameState rf{};lastProcessedStereoFrame=renderFrames.Read(rf)?rf.frameId:shared.ReadStereoMeta().frame;pendingReferenceSpaceChange=false;pendingReferenceSpaceChangeTime=0;}
            XrFrameBeginInfo bi{ XR_TYPE_FRAME_BEGIN_INFO };''')
replace_once("vrhost/main_stereo.cpp",'''                matchedStereoValid = false;
                lastProcessedStereoFrame = shared.ReadStereoMeta().frame;
                lastPresentation = presentation;''','''                matchedStereoValid=false;OutRunVR::SharedRenderFrameState rf{};lastProcessedStereoFrame=renderFrames.Read(rf)?rf.frameId:shared.ReadStereoMeta().frame;lastPresentation=presentation;''')

# Replace gameplay/capture block
old='''            bool layerReady = false;
            CaptureStatus capture{};
            if (fs.shouldRender==XR_TRUE)
                capture = compositor.Capture();

            if (fs.shouldRender==XR_TRUE && vc >= 2)
            {
                if (presentation == OutRunVR::PresentationGameplay)
                {
                    const ClientStereoMeta meta = shared.ReadStereoMeta();'''
if old not in read("vrhost/main_stereo.cpp"): raise RuntimeError("host gameplay prefix not found")
start=read("vrhost/main_stereo.cpp").index(old);text=read("vrhost/main_stereo.cpp");endmark='''            end.layerCount = layerReady ? 1 : 0;
            end.layers = layerReady ? layers : nullptr;
            CheckXr(xrEndFrame(session, &end), "xrEndFrame");''';end=text.index(endmark,start)+len(endmark)
new='''            bool layerReady=false;
            if(fs.shouldRender==XR_TRUE&&vc>=2){
                if(presentation==OutRunVR::PresentationGameplay){OutRunVR::SharedRenderFrameState before{};const bool have=renderFrames.Read(before);const std::uint32_t need=OutRunVR::RenderFrameStereoComplete|OutRunVR::RenderFrameWorldStereo|OutRunVR::RenderFrameDrawDuplicated|OutRunVR::RenderFrameEffectivePoseValid;
                    if(have&&before.state==OutRunVR::StereoSbsActive&&before.frameId&&before.frameId!=lastProcessedStereoFrame&&before.sourcePoseSequence&&(before.flags&need)==need){std::array<XrView,2> history{};if(viewHistory.Find(before.sourcePoseSequence,history)){LARGE_INTEGER cs{},ce{};QueryPerformanceCounter(&cs);const CaptureStatus capture=compositor.Capture(2);QueryPerformanceCounter(&ce);timings.capture.Add(timings.Ms(cs,ce));OutRunVR::SharedRenderFrameState after{};const bool same=renderFrames.Read(after)&&after.state==before.state&&after.frameId==before.frameId&&after.sourcePoseSequence==before.sourcePoseSequence&&after.presentQpc==before.presentQpc;if(capture.available&&QpcAtOrAfter(capture.lastPresentQpc,before.presentQpc)&&same&&compositor.CommitStereoSource()){for(int eye=0;eye<2;++eye){matchedViews[eye]={XR_TYPE_VIEW};matchedViews[eye].pose.orientation={before.eye[eye].orientation[0],before.eye[eye].orientation[1],before.eye[eye].orientation[2],before.eye[eye].orientation[3]};matchedViews[eye].pose.position={before.eye[eye].position[0],before.eye[eye].position[1],before.eye[eye].position[2]};matchedViews[eye].fov={before.eye[eye].fov.angleLeft,before.eye[eye].fov.angleRight,before.eye[eye].fov.angleUp,before.eye[eye].fov.angleDown};}matchedStereoValid=true;lastProcessedStereoFrame=before.frameId;lastStereoMatchMs=GetTickCount64();}}}
                    const bool grace=matchedStereoValid&&compositor.HasStereoSource()&&GetTickCount64()-lastStereoMatchMs<=StereoGraceMs;LARGE_INTEGER rs{},re{};QueryPerformanceCounter(&rs);if(grace&&compositor.RenderProjection(matchedViews,pv)){projection.space=localSpace;projection.viewCount=2;projection.views=pv.data();layers[0]=reinterpret_cast<const XrCompositionLayerBaseHeader*>(&projection);layerReady=true;}QueryPerformanceCounter(&re);timings.render.Add(timings.Ms(rs,re));
                }else{LARGE_INTEGER cs{},ce{};QueryPerformanceCounter(&cs);const CaptureStatus capture=compositor.Capture();QueryPerformanceCounter(&ce);timings.capture.Add(timings.Ms(cs,ce));LARGE_INTEGER rs{},re{};QueryPerformanceCounter(&rs);if(capture.available&&compositor.RenderTheater(viewSpace,localSpace,fs.predictedDisplayTime,quad)){layers[0]=reinterpret_cast<const XrCompositionLayerBaseHeader*>(&quad);layerReady=true;}QueryPerformanceCounter(&re);timings.render.Add(timings.Ms(rs,re));}}
            end.layerCount=layerReady?1:0;end.layers=layerReady?layers:nullptr;LARGE_INTEGER es{},ee{};QueryPerformanceCounter(&es);CheckXr(xrEndFrame(session,&end),"xrEndFrame");QueryPerformanceCounter(&ee);timings.end.Add(timings.Ms(es,ee));timings.MaybeLog();'''
write("vrhost/main_stereo.cpp",text[:start]+new+text[end:])

# Documentation + CI markers
text=read("VR_OPENXR.md");text=text.replace("## Current status: true stereo implemented, runtime validation pending","## Current status: true stereo + frame-integrity hardening implemented, runtime validation pending")
text+='''\n\n## Review-hardening contract\n\n`Pose.v1` remains the 248-byte Host->Game packet. `Local\\OutRun2006Tweaks.VR.Frame.v1` is the authoritative 256-byte Game->Host presented-frame contract with full Present QPC, failure reason and effective LOCAL eye poses/FOV. A required backbuffer draw/clear/depth operation that cannot be reproduced for both eyes poisons that Present, so partial stereo is never published active. The host reads metadata before capture, validates full Desktop Duplication `LastPresentTime`, rereads unchanged metadata, then freezes the SBS source. Full head-local eye orientation is applied in addition to IPD translation. `CullingUnionFov` is opt-in and affects only render-phase culling; pre-BeginScene visibility remains runtime-test territory.\n''';write("VR_OPENXR.md",text)

workflow=read(".github/workflows/vr-openxr.yml")
workflow=workflow.replace("'GetLatchedStereoFrame','GetCurrentShaderEpoch','IsInternalStereoPassActive','InvalidateVerifiedWvp'","'GetLatchedStereoFrame','GetCurrentShaderEpoch','IsInternalStereoPassActive','InvalidateVerifiedWvp','StereoEyeOrientationValid','effectiveEyeOrientation','VRCullingUnionFov'")
workflow=workflow.replace("'ClientStereoPresentQpcLowIndex','QueryPerformanceCounter(&presentStart)','FrameStereoPoseSequence'","'ClientStereoPresentQpcLowIndex','QueryPerformanceCounter(&presentStart)','FrameStereoPoseSequence','FrameStereoIncomplete','PoisonFrame','PublishRenderFrame','StereoFailureLeftWvpUploadFailed','RightDepthSynchronized'")
workflow=workflow.replace("'clientStereoPoseSequence','ClientStereoPresentQpcLowIndex','LatchedStereoFrame'","'clientStereoPoseSequence','ClientStereoPresentQpcLowIndex','LatchedStereoFrame','RenderFrameMemoryName','SharedRenderFrameState','static_assert(sizeof(SharedRenderFrameState) == 256)'")
workflow=workflow.replace("'ClientStereoPresentQpcLowIndex','QpcLowAtOrAfter'","'ClientStereoPresentQpcLowIndex','QpcLowAtOrAfter','RenderFrameReader','QpcAtOrAfter','HostTimings','BindCaptureOutput','pendingReferenceSpaceChangeTime'")
write(".github/workflows/vr-openxr.yml",workflow)

for path,markers in {"src/vr_shared.hpp":["SharedRenderFrameState","StereoEyeOrientationValid"],"src/vr_renderer_probe.cpp":["effectiveEyeOrientation","VRCullingUnionFov"],"src/vr_stereo.cpp":["FrameStereoIncomplete","PublishRenderFrame"],"vrhost/main_stereo.cpp":["RenderFrameReader","QpcAtOrAfter","HostTimings"]}.items():
    for marker in markers: require(path,marker)
print("VR review hardening patch applied successfully")
