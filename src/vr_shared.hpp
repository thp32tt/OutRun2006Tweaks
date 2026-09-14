#pragma once

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
