#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <TlHelp32.h>

#include <filesystem>
#include <string>
#include <atomic>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"

// VR settings live here, but the final camera transform does not.
// Head tracking is applied only at the verified D3D9 c64 WorldViewProjection
// upload. Simulation, input, timers and native FFB are never replayed for the
// second eye. Pose.v3 is primary with v2 retained as automatic compatibility
// fallback while frame transport migration is still in progress.
//
// D3D9Ex can preserve full-size L/R eye textures instead of squeezing them into
// SBS halves before Desktop Duplication. It remains opt-in until R14's lifetime-
// bound MANAGED 2D shadow path and cube/volume compatibility complete hardware
// validation. The shared-eye path is GPU-direct transport, not literal zero-
// copy: the host takes a D3D11 safety copy before it ACKs a producer ring slot.
namespace Settings
{
	Setting<bool> VREnabled{ "VR", "Enabled", true,
		"Enables the OpenXR renderer-side VR bridge." };
	Setting<bool> VRAutoEnableWhenHostPresent{ "VR", "AutoEnableWhenHostPresent", true,
		"Automatically applies renderer-side tracking whenever outrun-vr-host.exe is supplying a valid pose." };
    // HMD-less debug runs game-side R84 left/right rendering to the desktop.
    // Never auto-start or impersonate an OpenXR host in this mode.
    Setting<int> VRHmdlessDebugMode{ "VR", "HmdlessDebugMode", 0,
        "No-headset diagnostic only. Desktop SBS gameplay eye preview using synthetic 64 mm IPD and asymmetric FOV; restart required. This does NOT validate Quest 3 optics or compositor.",
        { "Off (normal Quest 3)", "Center (desktop SBS)", "Auto pose sweep (14 s)",
          "Yaw +30", "Yaw -30", "Pitch +20", "Pitch -20",
          "Move +10 cm X", "Move -10 cm X" } };
	Setting<bool> VRAutoLaunchHost{ "VR", "AutoLaunchHost", true,
		"Starts outrun-vr-host.exe from the game directory when VR is enabled. A short retry window also covers fast game restarts where the previous host is still shutting down." };
    // VR quality is independent of the original game's [DX] ANTIALIASING.
    // D3D9Ex MSAA buffer allocations only change after a game restart.
    Setting<int> VRAntiAliasing{ "VR", "AntiAliasing", 2,
        "VR-only MSAA level: Off/2x/4x or optional 8x (fallback 4x/2x); 8x may worsen crowded-stage GPU frame drops. Use Game AA restores 2D request. Restart required.",
        { "Off (fastest)", "2x MSAA", "4x MSAA (fallback 2x)", "Use Game/2D AA", "8x MSAA (fallback 4x/2x; costly)" } };
    Setting<bool> VRTransparencySupersampling{ "VR", "TransparencySupersampling", false,
        "Enable extra NVIDIA transparency SSAA in VR (costly). Off by default; the original 2D Graphics setting is unchanged. Restart required." };
    // Use the game's requested D3D9 backbuffer as the 2D/menu/HUD coordinate
    // system. Virtual Desktop's streaming desktop resolution and OpenXR
    // per-eye render extent are independent. Never hard-code the primary
    // monitor's current pixels into Game::screen_resolution after game config.
    // A paired VR RenderWidth/RenderHeight is still an explicit game override.
    Setting<bool> VRUnifiedEyeMenuSource{ "VR", "UnifiedEyeMenuSource", false,
        "Opt-in only: Quest3 2026-10-20 showed a portrait XR eye extent 2496x2688 corrupting the original game/menu layout. Default false preserves the original configured landscape game source, and XR eyes remain separately allocated. When enabled, use one VR 3D/2D menu render source. If the VDXR/OpenXR eye size is available BEFORE the original game graphics initialization, select it for both the D3D9Ex source and the game's scaled 2D menu. 640x480 logical UI coordinates remain independent. Never change the source at CreateDevice after the UI scale was calculated. When unavailable, keep the configured game resolution. Manual RenderWidth/Height and -width/-height win. Restart required." };
    Setting<bool> VRFollowGameResolution{ "VR", "FollowGameResolution", true,
        "Follow the game's configured resolution for VR source and UI when UnifiedEyeMenuSource is disabled. In unified mode, a ready XR eye extent sets ONE shared game/menu source before UI scale initialization; -width/-height or paired VR manual source settings take precedence. Restart required." };
    Setting<bool> VRAutoRenderResolution{ "VR", "AutoRenderResolution", true,
        "At launch, match the actual VDXR/OpenXR allocated per-eye render extent (not desktop or 2x eye width). "
        "Manual RenderWidth/RenderHeight take precedence; when host startup fails, use existing game resolution." };
	// Optional explicit internal render resolution independent of the PC monitor.
    // Auto (0/0) retains the original desktop-sized behavior. The x64 host
    // starts later than GameDefaultConfigOverride, so do NOT mistake a desktop
    // resolution for OpenXR's per-eye recommended image size.
    Setting<int> VRRenderWidth{ "VR", "RenderWidth", 0,
        "Optional game/eye render width. 0 = use original desktop default; set with RenderHeight. Higher resolution increases GPU load.", Range<int>{ 0, 8192 } };
    Setting<int> VRRenderHeight{ "VR", "RenderHeight", 0,
        "Optional game/eye render height. 0 = use original desktop default; set with RenderWidth. Not an OpenXR runtime autodetection.", Range<int>{ 0, 8192 } };
    Setting<bool> VRMirrorFitDesktop{ "VR", "MirrorFitDesktop", true,
        "Fits the borderless PC mirror within the monitor even when the internal D3D9Ex source is larger. The game and OpenXR eye images are not resized." };
    Setting<bool> VRMirrorPreserveAspect{ "VR", "MirrorPreserveAspect", true,
        "Keep the original 2D menu/game pixel aspect when displaying a portrait VDXR 3D/2D source on an ultrawide desktop. The PC mirror is centered with unused desktop space instead of vertically squashing the image. VR eye buffers and all source UI pixels stay unchanged." };
	Setting<bool> VRDisableDesktopVsync{ "VR", "DisableDesktopVsync", true,
		"Uses immediate D3D9 presentation while VR is enabled so the game source is not hard-capped by the desktop VSync setting before the OpenXR host captures it." };
	Setting<float> VRHudScale{ "VR", "HudScale", 0.55f,
		"Projection-space HUD size after the headset-specific asymmetric-FOV correction. Lower values make speed/time/position and menus smaller in the HMD.", Range<float>{ 0.30f, 1.20f } };
	// HMD-proven DX11 R57 mode 6 projects car ordinal and rival markers
    // with head inverse, identity eye orientations and physical per-eye
    // IPD/FOV. The R26 ordinal-only cant experiment is reversible.
    Setting<bool> VRRankDx11ProducerReference{ "VR", "RankDx11ProducerReference", true,
        "DX11 R57 mode6 direct original Calc3D2D output rank source; false restores the guarded R26 input check for A/B." };
    Setting<bool> VRRivalDx11NativeRoute{ "VR", "RivalDx11NativeRoute", true,
        "DX11-equivalent stock rival: do not install additional R26 0xBB6F0 and 0xBB796 E8 detours. False restores old detours; requires restart." };
    Setting<bool> VRRankDesktopLift{ "VR", "RankDesktopLift", false,
        "Reversible optional +32 original UI pixel rank vertical lift, absent in tested DX11. Default off. Does not affect rival." };
    Setting<bool> VRRankDx11ReferenceEyePose{ "VR", "RankDx11ReferenceEyePose", true,
        "Use the DX11 HMD-proven R57 mode-6 eye pose for car-attached rank markers. True keeps identity eye orientation and relative IPD with head inverse. False restores the R26 ordinal-only canted-eye experiment for A/B. World and rival producers are unchanged." };
	Setting<bool> VRHud1080pReference{ "VR", "Hud1080pReference", true,
        "R26 VR gameplay HUD only: uniform 1920x1080 viewing reference for ultrawide game sources. Never rewrite native OutRun 640x480 sprite coordinates, rank/rival anchors, front-end, or F11." };
    Setting<float> VRHudPlaneDistance{ "VR", "HudPlaneDistance", 4.0f,
        "R26 VR gameplay HUD plane distance. Old reference 2.50, default 4.00 for less face-close HUD. External ImGui F11 and front-end are unchanged.", Range<float>{ 2.50f, 8.00f } };
	Setting<float> VRPauseMenuScale{ "VR", "PauseMenuScale", 1.0f,
		"Independent centred ESC/pause menu size in VR; does not resize gameplay HUD, F11, the title menus, or world markers.", Range<float>{ 0.55f, 1.50f } };
	Setting<float> VRPauseMenuVerticalOffset{ "VR", "PauseMenuVerticalOffset", 0.10f,
		"Signed fraction of viewport height to move ESC/pause menu vertically in VR (positive is down); independent of gameplay HUD and F11.", Range<float>{ -0.25f, 0.25f } };
	Setting<bool> VRHudEdgeAnchors{ "VR", "HudEdgeAnchors", false,
		"Legacy opt-in exact HUD text anchors; set false with HudResponsiveLayout=false for the baseline A/B comparison." };
	// Issue #119: previous HudEdgeAnchors=false persists in an existing .ini;
	// a completed HUD code path must not remain invisible on new builds.
	// New default-on profile remains reversible and exact-producer-only.
	Setting<bool> VRHudResponsiveLayout{ "VR", "HudResponsiveLayout", true,
		"Quest3 responsive driving HUD edge anchors and larger independent ESC menu; disable for original layout A/B. GOAL, world markers, front-end and desktop are unchanged." };
	Setting<bool> VRHeadTracking{ "VR", "HeadTracking", true,
		"Applies the OpenXR HMD orientation at OutRun's verified D3D9 WorldViewProjection upload." };
	Setting<bool> VRStereo{ "VR", "Stereo", true,
		"Renders true left/right geometry stereo into verified shared-eye transport. Menus use a LOCAL-space world-fixed mono quad so head rotation and translation remain 6DoF." };
	Setting<bool> VRPreferD3D9Ex{ "VR", "PreferD3D9Ex", true,
		"Prefers guarded D3D9Ex shared-eye transport so gameplay can bypass Desktop Duplication. Disable to return to classic D3D9/SBS capture." };
	Setting<bool> VRDirectGpuOnly{ "VR", "DirectGpuOnly", true,
		"During gameplay, rejects classic Desktop-Duplication stereo candidates and keeps DirectGPU/cached OpenXR projection paths only. Menus remain mono on a world-fixed LOCAL-space quad." };
	Setting<bool> VRDisableDesktopDuplication{ "VR", "DisableDesktopDuplication", false,
		"Diagnostic isolation switch. Disables Desktop Duplication for gameplay and menus. Leave false for normal DirectGPU-only gameplay with visible menus." };
	Setting<float> VRTargetRefreshRateHz{ "VR", "TargetRefreshRateHz", 0.0f,
		"Optional OpenXR refresh-rate override through XR_FB_display_refresh_rate. Leave at 0 to respect the refresh rate selected by Virtual Desktop/runtime (for example 72 or 90 Hz).", Range<float>{ 0.0f, 144.0f } };
	Setting<int> VRFrameCadenceMode{ "VR", "FrameCadenceMode", 1,
		"Synchronizes rendering to the OpenXR clock. PhaseLock gates each game Present on the next host xrWaitFrame token without making the host wait for the game; SerializedProbe additionally enables bounded host-side diagnostics. Off restores the pre-R35 cadence.",
		{ "Off", "PhaseLock", "SerializedProbe" } };
	Setting<float> VRFrameCadenceTargetHz{ "VR", "FrameCadenceTargetHz", 0.0f,
		"Render cadence override while XR pacing is enabled. 0 = Auto/native OpenXR refresh (72/80/90/120 Hz as reported by xrWaitFrame). Non-zero keeps a fixed diagnostic render cadence.", Range<float>{ 0.0f, 120.0f } };
	Setting<float> VRFrameCadenceMaxHz{ "VR", "FrameCadenceMaxHz", 120.0f,
		"Maximum VR render cadence in Auto mode. The 60 Hz simulation remains unchanged; Tweaks interpolation fills intermediate render frames.", Range<float>{ 60.0f, 120.0f } };
	Setting<float> VRFrameCadenceTimeoutMs{ "VR", "FrameCadenceTimeoutMs", 35.0f,
		"Base fail-open timeout for OpenXR cadence waits. PhaseLock may extend this to four runtime periods (max 100 ms) so a temporary compositor stall can recover without returning to an uncapped producer loop.", Range<float>{ 5.0f, 100.0f } };
	Setting<bool> VRPositionalTracking{ "VR", "PositionalTracking", true,
		"Applies 6DoF HMD X/Y/Z movement in addition to orientation. Disable this option if a title-specific camera/culling issue is observed; stereo eye separation is independent." };
    // The precise central 0x570002 / EXE+C993 flare sometimes duplicates
    // across binocular views when its original game WVP proof is missing.
    // Preserve the original central draw in VR by default; surrounding
    // EXE+CABE lens discs, actual sky/lighting and desktop remain unchanged.
    // User confirmed hiding C993 did not remove duplicate sun; A/B hiding is optional only.
    Setting<bool> VRLensFlareCentreEnabled{ "VR", "LensFlareCentreEnabled", true,
        "VR only: render the central 0x570002 flare at the exact original C993 call. Default true keeps the real sun visible for exact stereo repair; false hides only this draw for explicit optical A/B, not as a fix. Outer CABE discs and sky remain intact." };
    // F11 VR PMT visibility policy; the desktop/legacy gate stays unchanged.
    Setting<int> VRStageCullingMode{ "VR", "StageCullingMode", 1,
        "VR PMT culling: Legacy follows Graphics/DisableStageCulling; VR Wide keeps culling with a stereo FOV and safety margin; Off disables PMT culling. HMD validation required.",
        { "Legacy (Graphics setting)", "VR Wide (stereo FOV)", "Off (no PMT culling)" } };
	Setting<bool> VRCullingCameraSync{ "VR", "CullingCameraSync", true,
		"Temporarily mirrors the render-time VR camera into OutRun's live camera position/look so render-phase culling and camera-facing effects can follow head motion. Restored before game logic resumes." };
	Setting<bool> VRCullingUnionFov{ "VR", "CullingUnionFov", true,
		"Legacy compatibility toggle; superseded by StageCullingMode. The game render projection is never modified across an entire scene." };
	Setting<float> VRCullingUnionMarginDegrees{ "VR", "CullingUnionMarginDegrees", 8.0f,
		"Extra angular safety margin in VR Wide (StageCullingMode=1). Start at 8 degrees to reduce headset-edge scenery pop; larger margins render more stage nodes and may cost FPS. Can be tuned in F11. The original game render projection and HUD are not modified.", Range<float>{ 0.0f, 15.0f } };
	Setting<bool> VRNormalizeReflectionRate{ "VR", "NormalizeReflectionRate", true,
		"Keeps car cubemap reflection work at the original 60 Hz time budget when rendering the HMD at 72/80/90/120 Hz." };
	Setting<float> VRNearPlane{ "VR", "NearPlane", 0.10f,
		"VR gameplay camera near plane in game units. Overrides the 2D Z-precision fix while positional tracking is active so dashboard/driver geometry is not clipped by the normal 1.0 near plane.", Range<float>{ 0.03f, 0.50f } };
	Setting<bool> VRDriverSeatView{ "VR", "DriverSeatView", true,
		"Experimental test view: reuses the native bumper camera timing/smoothing, shows the full player car, hides the driver robot and offsets the VR camera into the cockpit." };
    Setting<float> VRDriverSeatVehicleScale{ "VR", "DriverSeatVehicleScale", 1.15f,
        "Experimental cockpit-only player-car visual model scale. 1.0 preserves stock geometry; affects neither game physics nor original asset bytes. F11 adjustable; applied to the original PC player's stack-local draw matrix only when the cockpit mode is eligible. Not an APK-proven scale.", Range<float>{ 0.85f, 1.35f } };
    Setting<float> VRDriverSeatGlassOpacity{ "VR", "DriverSeatGlassOpacity", 0.30f,
        "Requested cockpit glass material opacity (0.10 to 0.90). A live renderer change requires a verified player-windshield material identity; currently diagnostic only and DOES NOT recolor unrelated materials.", Range<float>{ 0.10f, 0.90f } };
    Setting<bool> VRDriverSeatGlassMaterialTrace{ "VR", "DriverSeatGlassMaterialTrace", true,
        "Restart-required read-only bounded canonical PMT material probe; logs candidate blend/material IDs, never changes any glass or world opacity." };
	Setting<bool> VRDriverSeatCarSpaceBasis{ "VR", "DriverSeatCarSpaceBasis", false,
        "Experimental OPT-IN: align cockpit offsets to player matrix_B0. Quest3 field report 2026-10-17 observed severe cockpit/third-person zoom oscillation; default to the uninterrupted native camera basis to avoid per-frame car-space-to-native fallback switches. Enable only for separate A/B diagnosis." };
	Setting<int> VRDriverSeatNativeMode{ "VR", "DriverSeatNativeMode", 1,
		"Native camera mode used as the synchronized base for DriverSeatView. Default 1 is the bumper/in-car camera discovered from the canonical EXE.", Range<int>{ 0, 2 } };
	Setting<float> VRDriverSeatForward{ "VR", "DriverSeatForward", -1.35f,
		"Driver-seat camera offset along the native camera forward axis. Positive moves toward the road; negative moves rearward into the cabin.", Range<float>{ -3.0f, 3.0f } };
	Setting<float> VRDriverSeatRight{ "VR", "DriverSeatRight", -0.32f,
		"Driver-seat camera offset along the native camera right axis. Negative moves left toward the driver seat.", Range<float>{ -2.0f, 2.0f } };
	Setting<float> VRDriverSeatUp{ "VR", "DriverSeatUp", 0.65f,
		"Driver-seat camera vertical offset from the native bumper camera.", Range<float>{ -2.0f, 2.0f } };
	Setting<bool> VRDriverSeatFullCar{ "VR", "DriverSeatFullCar", true,
		"While DriverSeatView is active, forces DispCarModel_Common render state 1, the full exterior/body path. The games persistent camera/car flags are not changed." };
	Setting<bool> VRDriverSeatHideDriver{ "VR", "DriverSeatHideDriver", true,
		"Hides only the selected driver robot while DriverSeatView is active. Passenger/girlfriend rendering remains untouched." };
	Setting<int> VRDriverSeatDriverWorkId{ "VR", "DriverSeatDriverWorkId", 0,
		"Robot workId suppressed as the player driver in DriverSeatView. Candidate workId/chrset pairs are logged so this can be corrected live from F11 without rebuilding.", Range<int>{ 0, 20 } };
	Setting<int> VRDriverSeatDriverChrset{ "VR", "DriverSeatDriverChrset", -1,
		"Optional exact driver character set. -1 auto-detects driver-only chrsets from native driver/heroine tables; ambiguous or passenger characters are never hidden. Not hand tracking.", Range<int>{ -1, 4095 } };
	Setting<float> VRWorldScale{ "VR", "WorldScale", 1.0f,
		"Game-world units per metre of OpenXR head movement.", Range<float>{ 0.1f, 10.0f } };
	Setting<float> VRStereoDepth{ "VR", "StereoDepth", 1.0f,
		"Scales only virtual eye separation/3D parallax without changing head positional movement. 1.0 uses the runtime IPD; raise it for stronger depth.", Range<float>{ 0.50f, 2.00f } };
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
	namespace
	{
		bool VRHostProcessRunning() noexcept
		{
			HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
			if (snapshot == INVALID_HANDLE_VALUE)
				return false;
			PROCESSENTRY32W entry{};
			entry.dwSize = sizeof(entry);
			bool found = false;
			if (Process32FirstW(snapshot, &entry))
			{
				do
				{
					if (_wcsicmp(entry.szExeFile, L"outrun-vr-host.exe") == 0)
					{
						found = true;
						break;
					}
				} while (Process32NextW(snapshot, &entry));
			}
			CloseHandle(snapshot);
			return found;
		}

		bool VRLaunchHostOnce() noexcept
		{
			try
			{
				const std::filesystem::path gameDir = Module::ExePath.parent_path();
				const std::filesystem::path hostPath = gameDir / "outrun-vr-host.exe";
				if (!std::filesystem::exists(hostPath))
				{
					spdlog::warn("VR AUTO HOST: {} not found; start the host manually", hostPath.string());
					return false;
				}
				// The host inherits these test-mode switches. Keeping transport
				// policy in the same [VR] config as D3D9Ex avoids mismatched
				// game/host modes during cadence testing.
				SetEnvironmentVariableA("OUTRUN_VR_DIRECT_TRANSPORT", "1");
				SetEnvironmentVariableA("OUTRUN_VR_DIRECT_ONLY",
					Settings::VRDirectGpuOnly ? "1" : "0");
				SetEnvironmentVariableA("OUTRUN_VR_DISABLE_DESKTOP_DUPLICATION",
					Settings::VRDisableDesktopDuplication ? "1" : "0");
				const std::string refreshHz =
					std::to_string(Settings::VRTargetRefreshRateHz.get());
				SetEnvironmentVariableA("OUTRUN_VR_TARGET_REFRESH_HZ",
					refreshHz.c_str());
				const std::string cadenceMode =
					std::to_string(Settings::VRFrameCadenceMode.get());
				const std::string cadenceTargetHz =
					std::to_string(Settings::VRFrameCadenceTargetHz.get());
				const std::string cadenceMaxHz =
					std::to_string(Settings::VRFrameCadenceMaxHz.get());
				const std::string cadenceTimeoutMs =
					std::to_string(Settings::VRFrameCadenceTimeoutMs.get());
				SetEnvironmentVariableA("OUTRUN_VR_CADENCE_MODE", cadenceMode.c_str());
				SetEnvironmentVariableA("OUTRUN_VR_CADENCE_TARGET_HZ", cadenceTargetHz.c_str());
				SetEnvironmentVariableA("OUTRUN_VR_CADENCE_MAX_HZ", cadenceMaxHz.c_str());
				SetEnvironmentVariableA("OUTRUN_VR_CADENCE_TIMEOUT_MS", cadenceTimeoutMs.c_str());

				std::wstring command = L"\"" + hostPath.wstring() + L"\"";
				std::wstring workingDir = gameDir.wstring();
				STARTUPINFOW si{};
				si.cb = sizeof(si);
				PROCESS_INFORMATION pi{};
				if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE,
					CREATE_NEW_CONSOLE, nullptr, workingDir.c_str(), &si, &pi))
				{
					spdlog::warn("VR AUTO HOST: CreateProcess failed error={}", GetLastError());
					return false;
				}
				CloseHandle(pi.hThread);
				CloseHandle(pi.hProcess);
				spdlog::info("VR AUTO HOST: launched {}", hostPath.string());
				return true;
			}
			catch (const std::exception& e)
			{
				spdlog::warn("VR AUTO HOST: launch exception: {}", e.what());
				return false;
			}
		}

		DWORD WINAPI VRAutoLaunchHostThread(void*)
		{
			if (!Settings::VREnabled || !Settings::VRAutoLaunchHost || Settings::VRHmdlessDebugMode != 0)
				return 0;
            for (int attempt = 0; attempt < 40; ++attempt)
            {
                // Prewarmed host is ready; never spin the retry thread for 20s.
                if (VRHostProcessRunning())
                    return 0;
                if (VRLaunchHostOnce())
                    return 0;
                Sleep(500);
            }
			if (!VRHostProcessRunning())
				spdlog::warn("VR AUTO HOST: no host process became available during the startup retry window");
			return 0;
		}
	}

    void RequestVRHostStartup() noexcept
    {
        if (!Settings::VREnabled || !Settings::VRAutoLaunchHost || Settings::VRHmdlessDebugMode != 0)
            return;
        static std::atomic<bool> queued{false};
        bool expected = false;
        if (!queued.compare_exchange_strong(expected, true))
            return;
        HANDLE thread = CreateThread(nullptr, 0, VRAutoLaunchHostThread, nullptr, 0, nullptr);
        if (thread)
            CloseHandle(thread);
        else
        {
            queued.store(false);
            spdlog::warn("VR AUTO HOST: failed to create startup helper thread error={}", GetLastError());
        }
    }

	class VRSettingsHook : public Hook
	{
	public:
		std::string_view description() override { return "OpenXRVRSettings"; }
		bool validate() override { return true; }
		void declare_settings() override
		{
			Settings::VRAutoLaunchHost.needs_restart();
            Settings::VRHmdlessDebugMode.needs_restart();
            // Superseded by the explicit F11 StageCullingMode; keep existing
            // INI parsing backwards compatible without duplicate controls.
            Settings::VRCullingUnionFov.hidden(true);
            Settings::VRAntiAliasing.needs_restart();
            Settings::VRTransparencySupersampling.needs_restart();
            Settings::VRUnifiedEyeMenuSource.needs_restart();
            // Exact x86 rival detours are installed at startup only.
            // Treat F11 edits as pending until the next game launch.
            Settings::VRRivalDx11NativeRoute.needs_restart();
            Settings::VRFollowGameResolution.needs_restart();
    Settings::VRAutoRenderResolution.needs_restart();
			Settings::VRMirrorFitDesktop.needs_restart();
			Settings::VRDisableDesktopVsync.needs_restart();
			Settings::VRPreferD3D9Ex.needs_restart();
			Settings::VRDirectGpuOnly.needs_restart();
			Settings::VRDisableDesktopDuplication.needs_restart();
			Settings::VRTargetRefreshRateHz.needs_restart();
			Settings::VRFrameCadenceMode.needs_restart();
			Settings::VRFrameCadenceTargetHz.needs_restart();
			Settings::VRFrameCadenceMaxHz.needs_restart();
			Settings::VRFrameCadenceTimeoutMs.needs_restart();
		}

		bool apply() override
		{
			spdlog::info(
				"VR: D3D9Ex DirectGPU preference={} directOnly={} refreshOverrideHz={:.1f} cadenceMode={} cadenceTargetHz={:.1f} cadenceMaxHz={:.1f}; target 0 means XR-native render cadence, simulation remains 60 Hz",
				Settings::VRPreferD3D9Ex.get(),
				Settings::VRDirectGpuOnly.get(),
				Settings::VRTargetRefreshRateHz.get(),
				Settings::VRFrameCadenceMode.get(),
				Settings::VRFrameCadenceTargetHz.get(),
				Settings::VRFrameCadenceMaxHz.get());
            RequestVRHostStartup();
			return true;
		}

		static VRSettingsHook instance;
	};

	VRSettingsHook VRSettingsHook::instance;
}