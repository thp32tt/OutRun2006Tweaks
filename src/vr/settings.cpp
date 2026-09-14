#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"

// VR settings live here, but the final camera transform does not.
//
// The first prototype hooked CalcCameraMatrix and modified EvWorkCamera::d3dmatrix140.
// That turned out not to be the authoritative render boundary and also collided with
// FixZBufferPrecision, which legitimately hooks the same game function. Head tracking
// is now applied only at the verified D3D9 c64 WorldViewProjection upload in
// vr_renderer_probe.cpp. vr_stereo.cpp builds on that already-verified mono transform:
// it duplicates final D3D9 draws into full-size left/right eye surfaces and replaces
// only verified world-draw c64 constants with true per-eye OpenXR transforms.
// Simulation, input, timers and native FFB are never replayed for the second eye.
// Pose.v2 carries the OpenXR adapter/interop contract; exact rendered-frame timing/effective eye poses
// are published through the 4-slot Frame.v2 ring after a successful real D3D9 Present.
//
// The PC monitor is the transport surface, not a third 3D view: gameplay Present
// contains the two already-rendered eyes side-by-side. The x64 host Desktop-Duplicates
// that SBS image and crops each half for OpenXR. This costs resolve/copy bandwidth but
// does not execute OutRun's scene a third time for the monitor.
namespace Settings
{
	Setting<bool> VREnabled{ "VR", "Enabled", true,
		"Enables the experimental OpenXR renderer-side head-tracking bridge." };
	Setting<bool> VRAutoEnableWhenHostPresent{ "VR", "AutoEnableWhenHostPresent", true,
		"Automatically applies renderer-side head tracking whenever outrun-vr-host.exe is supplying a valid pose." };
	Setting<bool> VRHeadTracking{ "VR", "HeadTracking", true,
		"Applies the OpenXR HMD orientation at OutRun's verified D3D9 WorldViewProjection upload." };
	Setting<bool> VRStereo{ "VR", "Stereo", true,
		"Renders true left/right geometry stereo into an SBS game frame. The PC monitor shows that SBS transport; the x64 host splits the two eyes and submits an OpenXR projection layer. Menus remain on the fixed theater quad." };
	Setting<bool> VRPositionalTracking{ "VR", "PositionalTracking", false,
		"Also applies HMD X/Y/Z movement. Experimental; eye separation for stereo is applied independently of this setting." };
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
		"Logs renderer-boundary verification, stereo draw duplication and head-tracking diagnostics." };
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
			spdlog::info("VR: renderer-boundary head tracking + true stereo configured; CalcCameraMatrix remains untouched");
			return true;
		}

		static VRSettingsHook instance;
	};

	VRSettingsHook VRSettingsHook::instance;
}
