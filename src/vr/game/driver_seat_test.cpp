#include "driver_seat_test.hpp"

#include "game_addrs.hpp"
#include "hook_mgr.hpp"
#include "plugin.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

#include <spdlog/spdlog.h>

namespace Settings
{
	extern Setting<bool> VREnabled;
	extern Setting<bool> VRDriverSeatView;
	extern Setting<int> VRDriverSeatNativeMode;
	extern Setting<float> VRDriverSeatForward;
	extern Setting<float> VRDriverSeatRight;
	extern Setting<float> VRDriverSeatUp;
	extern Setting<int> VRDriverSeatCarRenderState;
	extern Setting<bool> VRDriverSeatHideDriver;
}

namespace OutRunVR::DriverSeatTest
{
	namespace
	{
		constexpr int PlayerCarRenderStateHookRva = 0x69764;
		constexpr int RobotDisplayRva = 0x114C10;
		constexpr int DriverChrsetsRva = 0x2549B0;
		constexpr int HeroineChrsetsRva = 0x2549C8;
		constexpr int ChrsetCount = 6;
		constexpr int ReferenceFullCarCameraMode = 0;
		constexpr int AutoRenderState = -1;
		constexpr int AutoFallbackRenderState = 1;

		SafetyHookMid PlayerCarRenderStateHook{};
		SafetyHookInline RobotDisplayHook{};

		int LastReferenceRenderState = -1;
		int LastLoggedReferenceRenderState = -1;
		int LastLoggedForcedRenderState = -99;
		std::array<std::uint64_t, 24> LoggedRobotKeys{};
		std::size_t LoggedRobotKeyCount = 0;

		bool GameplayState() noexcept
		{
			return Game::current_mode &&
				(*Game::current_mode == STATE_GAME || *Game::current_mode == STATE_GOAL);
		}

		bool ChrsetInTable(ChrSet chrset, int tableRva) noexcept
		{
			const int* table = Module::exe_ptr<int>(tableRva);
			if (!table)
				return false;
			const int value = static_cast<int>(chrset);
			for (int i = 0; i < ChrsetCount; ++i)
				if (table[i] == value)
					return true;
			return false;
		}

		void LogRobotOnce(EvWorkRobot* robot, bool driver, bool heroine) noexcept
		{
			if (!robot || LoggedRobotKeyCount >= LoggedRobotKeys.size())
				return;
			const std::uint64_t key =
				(static_cast<std::uint64_t>(robot->workId_0) << 32) |
				static_cast<std::uint32_t>(robot->chrset_8);
			for (std::size_t i = 0; i < LoggedRobotKeyCount; ++i)
				if (LoggedRobotKeys[i] == key)
					return;
			LoggedRobotKeys[LoggedRobotKeyCount++] = key;
			spdlog::info(
				"VR DRIVER SEAT ROBOT: workId={} chrset={} driverTable={} heroineTable={}",
				robot->workId_0, static_cast<int>(robot->chrset_8),
				driver ? 1 : 0, heroine ? 1 : 0);
		}

		int RequestedCarRenderState() noexcept
		{
			const int configured = Settings::VRDriverSeatCarRenderState.get();
			if (configured >= 0)
				return std::clamp(configured, 0, 2);
			if (LastReferenceRenderState >= 0)
				return LastReferenceRenderState;
			return AutoFallbackRenderState;
		}

		void PlayerCarRenderStateDest(SafetyHookContext& ctx)
		{
			EVWORK_CAR* player = Game::pl_car();
			if (!player || reinterpret_cast<EVWORK_CAR*>(ctx.ebx) != player)
				return;

			EvWorkCamera* camera = Game::camera();
			const int currentState = static_cast<int>((ctx.eax >> 14) & 3u);

			// Learn the exact player-car render state used by the native
			// third-person camera. This avoids hard-coding an interpretation of
			// bits 14..15 that changes meaning across the game's camera paths.
			if (camera && camera->cam_mode_timer_364 == 0.0f &&
				static_cast<int>(camera->cam_mode_34A) == ReferenceFullCarCameraMode)
			{
				LastReferenceRenderState = currentState;
				if (LastLoggedReferenceRenderState != currentState)
				{
					LastLoggedReferenceRenderState = currentState;
					spdlog::info(
						"VR DRIVER SEAT CAR: learned native mode {} player render state={}",
						ReferenceFullCarCameraMode, currentState);
				}
			}

			if (!IsActive(camera))
				return;

			const int targetState = RequestedCarRenderState();
			ctx.eax = (ctx.eax & ~0x0000C000u) |
				(static_cast<std::uint32_t>(targetState & 3) << 14);
			if (LastLoggedForcedRenderState != targetState)
			{
				LastLoggedForcedRenderState = targetState;
				spdlog::info(
					"VR DRIVER SEAT CAR: nativeState={} -> requestedState={} setting={} learnedReference={}",
					currentState, targetState,
					Settings::VRDriverSeatCarRenderState.get(),
					LastReferenceRenderState);
			}
		}

		void __cdecl RobotDisplayDest(EvWorkRobot* robot)
		{
			if (robot && IsActive(Game::camera()))
			{
				const bool driver = ChrsetInTable(robot->chrset_8, DriverChrsetsRva);
				const bool heroine = ChrsetInTable(robot->chrset_8, HeroineChrsetsRva);
				LogRobotOnce(robot, driver, heroine);

				// Classify by the game's live driver/heroine tables rather than by
				// robot workId. UseHiDefCharacters mutates these same tables, so
				// the test remains correct with HD characters enabled.
				if (Settings::VRDriverSeatHideDriver && driver && !heroine)
					return;
			}
			RobotDisplayHook.ccall<void>(robot);
		}

		class DriverSeatRenderHook final : public Hook
		{
		public:
			std::string_view description() override
			{
				return "VRDriverSeatCleanTest";
			}

			bool apply() override
			{
				PlayerCarRenderStateHook = safetyhook::create_mid(
					Module::exe_ptr(PlayerCarRenderStateHookRva),
					PlayerCarRenderStateDest);
				RobotDisplayHook = safetyhook::create_inline(
					Module::exe_ptr(RobotDisplayRva), RobotDisplayDest);
				return !!PlayerCarRenderStateHook && !!RobotDisplayHook;
			}

			static DriverSeatRenderHook instance;
		};

		DriverSeatRenderHook DriverSeatRenderHook::instance;
	}

	bool IsActive(EvWorkCamera* camera) noexcept
	{
		return Settings::VREnabled && Settings::VRDriverSeatView &&
			GameplayState() && camera &&
			camera->cam_mode_timer_364 == 0.0f &&
			static_cast<int>(camera->cam_mode_34A) ==
				Settings::VRDriverSeatNativeMode.get();
	}

	CameraRestore ApplyCameraOffset(EvWorkCamera* camera) noexcept
	{
		CameraRestore restore{};
		if (!IsActive(camera))
			return restore;

		restore.position = camera->cam_pos_F8;
		restore.look = camera->look_pos_104;

		float fx = restore.look.x - restore.position.x;
		float fy = restore.look.y - restore.position.y;
		float fz = restore.look.z - restore.position.z;
		const float forwardLength = std::sqrt(fx * fx + fy * fy + fz * fz);
		if (!std::isfinite(forwardLength) || forwardLength < 1.0e-5f)
			return restore;
		fx /= forwardLength;
		fy /= forwardLength;
		fz /= forwardLength;

		// right = forward x world-up
		float rx = -fz;
		const float ry = 0.0f;
		float rz = fx;
		const float rightLength = std::sqrt(rx * rx + rz * rz);
		if (!std::isfinite(rightLength) || rightLength < 1.0e-5f)
			return restore;
		rx /= rightLength;
		rz /= rightLength;

		// camera-local up = right x forward
		const float ux = ry * fz - rz * fy;
		const float uy = rz * fx - rx * fz;
		const float uz = rx * fy - ry * fx;

		const float forward = Settings::VRDriverSeatForward.get();
		const float right = Settings::VRDriverSeatRight.get();
		const float up = Settings::VRDriverSeatUp.get();
		const D3DVECTOR delta{
			fx * forward + rx * right + ux * up,
			fy * forward + ry * right + uy * up,
			fz * forward + rz * right + uz * up
		};

		camera->cam_pos_F8 = {
			restore.position.x + delta.x,
			restore.position.y + delta.y,
			restore.position.z + delta.z
		};
		camera->look_pos_104 = {
			restore.look.x + delta.x,
			restore.look.y + delta.y,
			restore.look.z + delta.z
		};
		restore.active = true;

		static float lastForward = 9999.0f;
		static float lastRight = 9999.0f;
		static float lastUp = 9999.0f;
		static int lastMode = -1;
		const int mode = static_cast<int>(camera->cam_mode_34A);
		if (mode != lastMode ||
			std::fabs(forward - lastForward) > 0.0001f ||
			std::fabs(right - lastRight) > 0.0001f ||
			std::fabs(up - lastUp) > 0.0001f)
		{
			lastMode = mode;
			lastForward = forward;
			lastRight = right;
			lastUp = up;
			spdlog::info(
				"VR DRIVER SEAT CAMERA: mode={} forward={:.3f} right={:.3f} up={:.3f} applied before native CalcCameraMatrix",
				mode, forward, right, up);
		}

		return restore;
	}

	void RestoreCamera(EvWorkCamera* camera, const CameraRestore& restore) noexcept
	{
		if (!camera || !restore.active)
			return;
		camera->cam_pos_F8 = restore.position;
		camera->look_pos_104 = restore.look;
	}
}
