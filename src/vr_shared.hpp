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
	};

	// reserved[] stays inside protocol v1 so diagnostics and renderer/host
	// coordination can evolve without changing the x86/x64 ABI. Indices 0..2
	// are written by the x86 client, index 3 by the x64 host, and 4..5 by the
	// x86 client. Keep ownership disjoint so host seqlock writes never need to
	// overwrite client telemetry.
	inline constexpr std::uint32_t ClientHeartbeatIndex = 0;
	inline constexpr std::uint32_t ClientFlagsIndex = 1;
	inline constexpr std::uint32_t ClientLastAngleBitsIndex = 2;
	inline constexpr std::uint32_t HostReferenceSpaceGenerationIndex = 3;
	inline constexpr std::uint32_t ClientPresentationModeIndex = 4;
	inline constexpr std::uint32_t ClientGameStateIndex = 5;

	enum ClientPresentationMode : std::uint32_t
	{
		PresentationUnknown = 0,
		PresentationGameplay = 1,
		PresentationTheater = 2,
	};

	enum ClientTelemetryFlags : std::uint32_t
	{
		ClientHookAlive = 1u << 0,
		ClientHostPoseValid = 1u << 1,
		// Set only after the final D3D9 constant upload succeeds and then
		// published only after a successful EndScene. It no longer means merely
		// that a corrected matrix was calculated.
		ClientPoseApplied = 1u << 2,
		ClientAutoEnabled = 1u << 3,
		ClientRendererWvpVerified = 1u << 4,
		// Kept for host compatibility; now means the original D3D9 upload
		// returned success for the patched c64 data.
		ClientRendererPoseInjected = 1u << 5,
		ClientRendererMatrixPrepared = 1u << 6,
		ClientRendererUploadFailed = 1u << 7,
		ClientCullingCameraSynced = 1u << 8,
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
		float reservedPose;

		// Kept in the protocol now so the stereo milestone can render true
		// stereo without changing the x86/x64 IPC ABI.
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

// Renderer-side aliases. These do not change protocol layout or ownership.
namespace OutRunVRRenderer
{
	using OutRunVR::SharedMemoryName;
	using OutRunVR::SharedMagic;
	using OutRunVR::SharedProtocolVersion;
	using OutRunVR::SharedPoseState;
	using OutRunVR::HostAlive;
	using OutRunVR::OrientationValid;
	using OutRunVR::PositionValid;
	using OutRunVR::ClientHeartbeatIndex;
	using OutRunVR::ClientFlagsIndex;
	using OutRunVR::ClientLastAngleBitsIndex;
	using OutRunVR::HostReferenceSpaceGenerationIndex;
	using OutRunVR::ClientPresentationModeIndex;
	using OutRunVR::ClientGameStateIndex;
	using OutRunVR::ClientPresentationMode;
	using OutRunVR::PresentationUnknown;
	using OutRunVR::PresentationGameplay;
	using OutRunVR::PresentationTheater;
	using OutRunVR::ClientHookAlive;
	using OutRunVR::ClientHostPoseValid;
	using OutRunVR::ClientPoseApplied;
	using OutRunVR::ClientAutoEnabled;
	using OutRunVR::ClientRendererWvpVerified;
	using OutRunVR::ClientRendererPoseInjected;
	using OutRunVR::ClientRendererMatrixPrepared;
	using OutRunVR::ClientRendererUploadFailed;
	using OutRunVR::ClientCullingCameraSynced;
}
