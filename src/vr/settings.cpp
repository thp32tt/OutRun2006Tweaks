#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"

// VR settings live here, but the final camera transform does not.
// Head tracking is applied only at the verified D3D9 c64 WorldViewProjection
// upload. Simulation, input, timers and native FFB are never replayed for the
// second eye. Pose.v3 is primary with v2 retained as automatic compatibility
// fallback while frame transport migration is still in progress.
//
// D3D9Ex is preferred on the VR branch because it preserves the full-size L/R
// eye textures instead of squeezing them into SBS halves before Desktop
// Duplication. R14 services legacy MANAGED 2D LockRect through SYSTEMMEM CPU
// shadows, while device-promotion/setup failures still fall back to classic
// D3D9. Cube/volume legacy resources remain hardware-validation items. The
// shared-eye path is GPU-direct transport, not literal zero-copy: the host takes
// a D3D11 safety copy before it ACKs a producer ring slot.
namespace Settings
{
	Setting<bool> VREnabled{ "VR", "Enabled", true,
		"Enables the OpenXR renderer-side VR bridge." };
	Setting<bool> VRAutoEnableWhenHostPresent{ "VR", "AutoEnableWhenHostPresent", true,
		"Automatically applies renderer-side tracking whenever outrun-vr-host.exe is supplying a valid pose." };
	Setting<bool> VRHeadTracking{ "VR", "HeadTracking", true,
		"Applies the OpenXR HMD orientation at OutRun's verified D3D9 WorldViewProjection upload." };
	Setting<bool> VRStereo{ "VR", "Stereo", true,
		"Renders true left/right geometry stereo into an SBS game frame or verified shared-eye transport. Menus remain on the fixed theater quad." };
	Setting<bool> VRPreferD3D9Ex{ "VR", "PreferD3D9Ex", true,
		"Prefers the guarded D3D9Ex shared-eye transport so each eye keeps full backbuffer resolution and Desktop Duplication can be skipped. R14 CPU-shadows legacy MANAGED 2D texture locks and device setup still falls back to classic D3D9; set false if a driver/resource compatibility issue is observed." };
	Setting<bool> VRPositionalTracking{ "VR", "PositionalTracking", true,
		"Applies 6DoF HMD X/Y/Z movement in addition to orientation. Disable this option if a title-specific camera/culling issue is observed; stereo eye separation is independent." };
	Setting<bool> VRCullingCameraSync{ "VR", "CullingCameraSync", true,
		"Temporarily mirrors the render-time VR camera into OutRun's live camera position/look so render-phase culling and camera-facing effects can follow head motion. Restored before game logic resumes." };
	Setting<bool> VRCullingUnionFov{ "VR", "CullingUnionFov", false,
		"Reserved diagnostic option. Union-FOV culling is intentionally deferred until a culling-only frustum boundary is verified; the live game projection is not modified." };
	Setting<float> VRWorldScale{ "VR", "WorldScale", 1.0f,
		"Game-world units per metre of OpenXR head/eye movement.", Range<float>{ 0.1f, 10.0f } };
	Setting<float> VRRotationScale{ "VR", "RotationScale", 1.0f,
		"Scales HMD rotation around the recentered forward direction.", Range<float>{ 0.0f, 2.0f } };
	Setting<int> VRMatrixOrder{ "VR", "MatrixOrder", 0,
		"Renderer-side camera-matrix composition order. Leave at 0 unless runtime validation shows the alternate path is required.",
		{ "WorldView * HeadInverse * Projection", "World * HeadInverse * View * Projection" } };
	Setting<bool> VRTelemetry{ "VR", "Telemetry", true,
		"Logs renderer-boundary verification, stereo draw duplication, pose source/fallback and head-tracking diagnostics." };
}

namespace OutRunVR
{
	class VRSettingsHook : public Hook
	{
	public:
		std::string_view description() override { return "OpenXRVRSettings"; }
		bool validate() override { return true; }

		bool apply() override
		{
			spdlog::info("VR: guarded D3D9Ex full-eye transport preferred; classic D3D9 + fresh SBS/Desktop Duplication retained as automatic compatibility fallback; CalcCameraMatrix untouched");
			return true;
		}

		static VRSettingsHook instance;
	};

	VRSettingsHook VRSettingsHook::instance;
}