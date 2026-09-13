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

	// reserved[] stays inside protocol v1 so we can add diagnostics without
	// changing the x86/x64 ABI. The x86 game writes these values and the x64
	// host only reads them.
	inline constexpr std::uint32_t ClientHeartbeatIndex = 0;
	inline constexpr std::uint32_t ClientFlagsIndex = 1;
	inline constexpr std::uint32_t ClientLastAngleBitsIndex = 2;

	enum ClientTelemetryFlags : std::uint32_t
	{
		ClientHookAlive = 1u << 0,
		ClientHostPoseValid = 1u << 1,
		ClientPoseApplied = 1u << 2,
		ClientAutoEnabled = 1u << 3,
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

		// Kept in the protocol now so the next milestone can render true stereo
		// without changing the x86/x64 IPC ABI.
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

// The final D3D9 renderer injector is intentionally a separate implementation
// from the original game-camera experiment. Re-export only the protocol symbols
// it consumes so the renderer file can stay in its own namespace without
// changing the shared-memory ABI or the host/game producer code.
namespace OutRunVRRenderer
{
	using OutRunVR::SharedMemoryName;
	using OutRunVR::SharedMagic;
	using OutRunVR::SharedProtocolVersion;
	using OutRunVR::SharedPoseState;
	using OutRunVR::HostAlive;
	using OutRunVR::OrientationValid;
	using OutRunVR::PositionValid;
}
