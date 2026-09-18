#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <TlHelp32.h>

#include <filesystem>
#include <string>

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
	Setting<bool> VRAutoLaunchHost{ "VR", "AutoLaunchHost", true,
		"Starts outrun-vr-host.exe from the game directory when VR is enabled. A short retry window also covers fast game restarts where the previous host is still shutting down." };
	Setting<bool> VRMirrorFitDesktop{ "VR", "MirrorFitDesktop", false,
		"Fits the borderless PC mirror window to the current monitor even when the internal game backbuffer is larger. The VR render resolution is unchanged." };
	Setting<bool> VRDisableDesktopVsync{ "VR", "DisableDesktopVsync", true,
		"Uses immediate D3D9 presentation while VR is enabled so the game source is not hard-capped by the desktop VSync setting before the OpenXR host captures it." };
	Setting<float> VRHudScale{ "VR", "HudScale", 0.55f,
		"Projection-space HUD size after the headset-specific asymmetric-FOV correction. Lower values make speed/time/position and menus smaller in the HMD.", Range<float>{ 0.30f, 1.20f } };
	Setting<bool> VRHeadTracking{ "VR", "HeadTracking", true,
		"Applies the OpenXR HMD orientation at OutRun's verified D3D9 WorldViewProjection upload." };
	Setting<bool> VRStereo{ "VR", "Stereo", true,
		"Renders true left/right geometry stereo into an SBS game frame or verified shared-eye transport. Menus remain on the fixed theater quad." };
	Setting<bool> VRPreferD3D9Ex{ "VR", "PreferD3D9Ex", false,
		"Opt-in guarded D3D9Ex shared-eye transport. Legacy lost-device/Reset semantics are translated, R14 tracks actual external 2D writes, and unsupported cube/volume lock fallbacks fail closed; hardware validation is still required before making this the default." };
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
			if (!Settings::VREnabled || !Settings::VRAutoLaunchHost)
				return 0;
			bool launched = false;
			for (int attempt = 0; attempt < 40; ++attempt)
			{
				if (!VRHostProcessRunning() && !launched)
				{
					launched = VRLaunchHostOnce();
					if (launched)
						return 0;
				}
				Sleep(500);
			}
			if (!VRHostProcessRunning())
				spdlog::warn("VR AUTO HOST: no host process became available during the startup retry window");
			return 0;
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
			Settings::VRMirrorFitDesktop.needs_restart();
			Settings::VRDisableDesktopVsync.needs_restart();
		}

		bool apply() override
		{
			spdlog::info("VR: classic D3D9 + fresh SBS/Desktop Duplication is the validated default; guarded D3D9Ex full-eye transport remains opt-in pending hardware validation; CalcCameraMatrix untouched");
			if (Settings::VREnabled && Settings::VRAutoLaunchHost)
			{
				HANDLE thread = CreateThread(nullptr, 0, VRAutoLaunchHostThread, nullptr, 0, nullptr);
				if (thread)
					CloseHandle(thread);
				else
					spdlog::warn("VR AUTO HOST: failed to create startup helper thread error={}", GetLastError());
			}
			return true;
		}

		static VRSettingsHook instance;
	};

	VRSettingsHook VRSettingsHook::instance;
}
