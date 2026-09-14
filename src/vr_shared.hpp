#pragma once

#include <cstdint>

namespace OutRunVR
{
	inline constexpr wchar_t SharedMemoryName[] = L"Local\\OutRun2006Tweaks.VR.Pose.v1";
	inline constexpr std::uint32_t SharedMagic = 0x5256524Fu; // 'ORVR' in little endian
	inline constexpr std::uint32_t SharedProtocolVersion = 1;

	enum SharedFlags : std::uint32_t
	{
		HostAlive = 1u << 0,
		OrientationValid = 1u << 1,
		PositionValid = 1u << 2,
		SessionVisible = 1u << 3,
		SessionFocused = 1u << 4,
		StereoViewsValid = 1u << 5,
	};

	// reserved[] stays inside protocol v1 so diagnostics and renderer/host
	// coordination can evolve without changing the x86/x64 ABI. Ownership is
	// deliberately disjoint so host seqlock writes never overwrite client state.
	inline constexpr std::uint32_t ClientHeartbeatIndex = 0;
	inline constexpr std::uint32_t ClientFlagsIndex = 1;
	inline constexpr std::uint32_t ClientLastAngleBitsIndex = 2;
	inline constexpr std::uint32_t HostReferenceSpaceGenerationIndex = 3;
	inline constexpr std::uint32_t ClientPresentationModeIndex = 4;
	inline constexpr std::uint32_t ClientGameStateIndex = 5;

	// Host-owned stereo eye offsets, stored as float bits in head-local metres.
	// [6..8] = left XYZ, [9..11] = right XYZ.
	inline constexpr std::uint32_t HostEyeOffsetLeftXIndex = 6;
	inline constexpr std::uint32_t HostEyeOffsetLeftYIndex = 7;
	inline constexpr std::uint32_t HostEyeOffsetLeftZIndex = 8;
	inline constexpr std::uint32_t HostEyeOffsetRightXIndex = 9;
	inline constexpr std::uint32_t HostEyeOffsetRightYIndex = 10;
	inline constexpr std::uint32_t HostEyeOffsetRightZIndex = 11;

	// Client-owned true-stereo transport state. The x64 host uses these to
	// decide whether gameplay contains a left/right SBS frame ready for an
	// XrCompositionLayerProjection submission.
	inline constexpr std::uint32_t ClientStereoStateIndex = 12;
	inline constexpr std::uint32_t ClientStereoFrameIndex = 13;
	inline constexpr std::uint32_t ClientStereoBackbufferWidthIndex = 14;
	inline constexpr std::uint32_t ClientStereoBackbufferHeightIndex = 15;

	enum ClientPresentationMode : std::uint32_t
	{
		PresentationUnknown = 0,
		PresentationGameplay = 1,
		PresentationTheater = 2,
	};

	enum ClientStereoState : std::uint32_t
	{
		StereoDisabled = 0,
		StereoSbsActive = 1,
		StereoSbsFallbackMono = 2,
	};

	enum ClientTelemetryFlags : std::uint32_t
	{
		ClientHookAlive = 1u << 0,
		ClientHostPoseValid = 1u << 1,
		ClientPoseApplied = 1u << 2,
		ClientAutoEnabled = 1u << 3,
		ClientRendererWvpVerified = 1u << 4,
		ClientRendererPoseInjected = 1u << 5,
		ClientRendererMatrixPrepared = 1u << 6,
		ClientRendererUploadFailed = 1u << 7,
		ClientCullingCameraSynced = 1u << 8,
		ClientFrameCompleted = 1u << 9,
		ClientStereoActive = 1u << 10,
		ClientStereoWorldDraw = 1u << 11,
		ClientStereoDrawDuplicated = 1u << 12,
	};

#pragma pack(push, 4)
	struct SharedFov
	{
		float angleLeft;
		float angleRight;
		float angleUp;
		float angleDown;
	};

	struct SharedPoseState
	{
		std::uint32_t magic;
		std::uint32_t protocolVersion;
		std::uint32_t structSize;

		// Seqlock. The x64 host increments this before and after a write.
		// Odd = write in progress, even = stable snapshot.
		volatile std::uint32_t sequence;

		volatile std::uint32_t hostPid;
		volatile std::uint32_t clientPid;
		volatile std::uint32_t flags;
		volatile std::uint32_t heartbeat;

		std::int64_t sampleQpc;

		// Raw OpenXR LOCAL-space head pose. Quaternion order is x,y,z,w.
		float orientation[4];
		float position[3];

		// Client-owned. When an SBS frame is published this is the exact stable
		// host seqlock sequence that was latched at the game's BeginScene and used
		// for both head tracking and stereo-eye construction. This reuses the old
		// reservedPose slot, preserving protocol-v1 layout and sizeof()==248.
		volatile std::uint32_t clientStereoPoseSequence;

		// Per-eye OpenXR FOV and recommended sizes are part of protocol v1 so
		// true stereo never needs an ABI-breaking pose bridge revision.
		SharedFov eyeFov[2];
		std::uint32_t recommendedWidth[2];
		std::uint32_t recommendedHeight[2];

		char runtimeName[64];
		std::uint32_t reserved[16];
	};
#pragma pack(pop)

	static_assert(sizeof(SharedFov) == 16);
	static_assert(sizeof(SharedPoseState) == 248);
}

namespace OutRunVRRenderer
{
	using OutRunVR::SharedMemoryName;
	using OutRunVR::SharedMagic;
	using OutRunVR::SharedProtocolVersion;
	using OutRunVR::SharedPoseState;
	using OutRunVR::SharedFov;
	using OutRunVR::HostAlive;
	using OutRunVR::OrientationValid;
	using OutRunVR::PositionValid;
	using OutRunVR::StereoViewsValid;
	using OutRunVR::ClientHeartbeatIndex;
	using OutRunVR::ClientFlagsIndex;
	using OutRunVR::ClientLastAngleBitsIndex;
	using OutRunVR::HostReferenceSpaceGenerationIndex;
	using OutRunVR::ClientPresentationModeIndex;
	using OutRunVR::ClientGameStateIndex;
	using OutRunVR::HostEyeOffsetLeftXIndex;
	using OutRunVR::HostEyeOffsetLeftYIndex;
	using OutRunVR::HostEyeOffsetLeftZIndex;
	using OutRunVR::HostEyeOffsetRightXIndex;
	using OutRunVR::HostEyeOffsetRightYIndex;
	using OutRunVR::HostEyeOffsetRightZIndex;
	using OutRunVR::ClientStereoStateIndex;
	using OutRunVR::ClientStereoFrameIndex;
	using OutRunVR::ClientStereoBackbufferWidthIndex;
	using OutRunVR::ClientStereoBackbufferHeightIndex;
	using OutRunVR::ClientPresentationMode;
	using OutRunVR::PresentationUnknown;
	using OutRunVR::PresentationGameplay;
	using OutRunVR::PresentationTheater;
	using OutRunVR::StereoDisabled;
	using OutRunVR::StereoSbsActive;
	using OutRunVR::StereoSbsFallbackMono;
	using OutRunVR::ClientHookAlive;
	using OutRunVR::ClientHostPoseValid;
	using OutRunVR::ClientPoseApplied;
	using OutRunVR::ClientAutoEnabled;
	using OutRunVR::ClientRendererWvpVerified;
	using OutRunVR::ClientRendererPoseInjected;
	using OutRunVR::ClientRendererMatrixPrepared;
	using OutRunVR::ClientRendererUploadFailed;
	using OutRunVR::ClientCullingCameraSynced;
	using OutRunVR::ClientFrameCompleted;
	using OutRunVR::ClientStereoActive;
	using OutRunVR::ClientStereoWorldDraw;
	using OutRunVR::ClientStereoDrawDuplicated;

	// One immutable OpenXR eye packet, latched by vr_renderer_probe.cpp on the
	// successful game BeginScene. vr_stereo.cpp consumes this instead of reading
	// shared memory independently for every draw, so head pose/FOV/IPD all belong
	// to the exact same host sequence.
	struct LatchedStereoFrame
	{
		bool valid = false;
		std::uint32_t poseSequence = 0;
		SharedFov eyeFov[2]{};
		float eyeOffset[2][3]{};
	};

	bool GetLatchedStereoFrame(LatchedStereoFrame& out);

	// The mono renderer records only c64 uploads that were independently verified
	// as OutRun's Transpose(WorldView*Projection) and successfully uploaded after
	// head correction. Stereo uses this generation marker to avoid treating stale
	// c64 values from HUD/effect shaders as geometry.
	bool GetLastVerifiedWvp(float outConstants[16], std::uint32_t& generation,
		std::uint32_t& poseSequence);
}

namespace OutRunVRStereo
{
	// ComposeSbs performs one compositor-only BeginScene/EndScene. The mono
	// renderer uses this guard so that pass cannot relatch pose or publish fake
	// game-frame telemetry.
	bool IsInternalStereoPassActive();
}
