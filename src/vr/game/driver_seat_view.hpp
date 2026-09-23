#pragma once

#include "../../hook_mgr.hpp"
#include "../../plugin.hpp"
#include "../../game_addrs.hpp"

#include <cmath>
#include <cstdint>

namespace Settings
{
	extern Setting<bool> VREnabled;
	extern Setting<bool> VRDriverSeatView;
	extern Setting<float> VRDriverSeatForward;
	extern Setting<float> VRDriverSeatRight;
	extern Setting<float> VRDriverSeatUp;
	extern Setting<bool> VRDriverSeatHideDriver;
}

namespace OutRunVR::DriverSeatView
{
	// User-visible numbering follows the native cycle observed in the canonical
	// OR2006C2C.EXE: raw 2 = view 1, raw 1 = view 2, raw 0 = view 3.
	// We keep raw 2 for virtual view 4 so the game owns exactly the same
	// vehicle/passenger rendering as view 1.
	constexpr int NativeRenderMode = 2;
	constexpr int NativeReferenceMode = 1;

	struct CameraBackup
	{
		D3DVECTOR pos{};
		D3DVECTOR look{};
		bool applied = false;
	};

	namespace Detail
	{
		inline bool VirtualActive = false;
		inline bool ReferenceValid = false;
		inline D3DVECTOR ReferencePosLocal{};
		inline D3DVECTOR ReferenceLookLocal{};
		inline SafetyHookMid ChangeViewHook{};
		inline SafetyHookInline RobotDisplayHook{};
		inline bool ReferenceLogged = false;
		inline bool DriverHiddenLogged = false;

		constexpr int ChangeViewCycleRva = 0x84B93;
		constexpr int ChangeViewCycleDoneRva = 0x84BAE;
		constexpr int RobotDisplayRva = 0x114C10;

		inline bool GameplayState()
		{
			return Game::current_mode &&
				(*Game::current_mode == STATE_GAME ||
				 *Game::current_mode == STATE_GOAL);
		}

		inline D3DVECTOR Sub(const D3DVECTOR& a, const D3DVECTOR& b)
		{
			return { a.x - b.x, a.y - b.y, a.z - b.z };
		}

		inline D3DVECTOR Add(const D3DVECTOR& a, const D3DVECTOR& b)
		{
			return { a.x + b.x, a.y + b.y, a.z + b.z };
		}

		inline D3DVECTOR Mul(const D3DVECTOR& v, float s)
		{
			return { v.x * s, v.y * s, v.z * s };
		}

		inline float Dot(const D3DVECTOR& a, const D3DVECTOR& b)
		{
			return a.x * b.x + a.y * b.y + a.z * b.z;
		}

		inline float Length(const D3DVECTOR& v)
		{
			return std::sqrt(Dot(v, v));
		}

		inline bool Normalize(D3DVECTOR& v)
		{
			const float len = Length(v);
			if (!std::isfinite(len) || len < 1.0e-5f)
				return false;
			v = Mul(v, 1.0f / len);
			return true;
		}

		inline D3DVECTOR RightAxis(const D3DMATRIX& m)
		{
			return { m._11, m._12, m._13 };
		}

		inline D3DVECTOR UpAxis(const D3DMATRIX& m)
		{
			return { m._21, m._22, m._23 };
		}

		inline D3DVECTOR ForwardAxis(const D3DMATRIX& m)
		{
			return { m._31, m._32, m._33 };
		}

		inline D3DVECTOR Translation(const D3DMATRIX& m)
		{
			return { m._41, m._42, m._43 };
		}

		inline D3DVECTOR WorldToLocal(const D3DMATRIX& m, const D3DVECTOR& world)
		{
			const D3DVECTOR d = Sub(world, Translation(m));
			return {
				Dot(d, RightAxis(m)),
				Dot(d, UpAxis(m)),
				Dot(d, ForwardAxis(m))
			};
		}

		inline D3DVECTOR LocalToWorld(const D3DMATRIX& m, const D3DVECTOR& local)
		{
			D3DVECTOR out = Translation(m);
			out = Add(out, Mul(RightAxis(m), local.x));
			out = Add(out, Mul(UpAxis(m), local.y));
			out = Add(out, Mul(ForwardAxis(m), local.z));
			return out;
		}

		inline void ResetVirtual()
		{
			VirtualActive = false;
			DriverHiddenLogged = false;
		}

		inline void ChangeViewDest(safetyhook::Context& ctx)
		{
			auto* camera = reinterpret_cast<EvWorkCamera*>(ctx.esi);
			if (!camera || !Settings::VRDriverSeatView || !GameplayState())
			{
				ResetVirtual();
				return;
			}

			if (VirtualActive)
			{
				// virtual 4 -> native 1: keep raw mode 2 and skip the native 2->1
				// decrement. The camera controller already handled the button edge.
				ResetVirtual();
				ctx.eip = reinterpret_cast<std::uintptr_t>(
					Module::exe_ptr(ChangeViewCycleDoneRva));
				spdlog::info(
					"VR DRIVER V4: leave virtual view -> native view 1 (raw mode 2)");
				return;
			}

			// Native 3 is raw mode 0. The game's own instruction below wraps it
			// to raw mode 2; mark that wrapped frame as virtual view 4.
			if (camera->cam_mode_34A == 0 && ReferenceValid)
			{
				VirtualActive = true;
				spdlog::info(
					"VR DRIVER V4: enter virtual view 4; raw render mode remains 2, learned view-2 camera reference is active");
			}
		}

		inline bool IsDriverRobot(EvWorkRobot* robot)
		{
			if (!robot)
				return false;
			auto* driverEvent = Game::event(EVENT_ROB01);
			auto* passengerEvent = Game::event(EVENT_ROB02);
			auto* driver = driverEvent ? driverEvent->data<EvWorkRobot>() : nullptr;
			auto* passenger = passengerEvent ? passengerEvent->data<EvWorkRobot>() : nullptr;
			if (robot == passenger)
				return false;
			return driver && robot == driver;
		}

		inline void __cdecl RobotDisplayDest(EvWorkRobot* robot)
		{
			if (VirtualActive && Settings::VRDriverSeatHideDriver &&
				GameplayState() && IsDriverRobot(robot))
			{
				if (!DriverHiddenLogged)
				{
					DriverHiddenLogged = true;
					auto* passenger = Game::event(EVENT_ROB02)->data<EvWorkRobot>();
					spdlog::info(
						"VR DRIVER V4: hiding ROB01 driver ptr={} chrset={}; ROB02 passenger ptr={} remains enabled",
						static_cast<const void*>(robot),
						static_cast<int>(robot->chrset_8),
						static_cast<const void*>(passenger));
				}
				return;
			}
			RobotDisplayHook.ccall<void>(robot);
		}
	}

	inline bool IsVirtualActive(EvWorkCamera* camera = nullptr)
	{
		if (!Detail::VirtualActive || !Settings::VRDriverSeatView ||
			!Detail::GameplayState())
			return false;
		if (!camera)
			camera = Game::camera();
		if (!camera || camera->cam_mode_34A != NativeRenderMode)
		{
			Detail::ResetVirtual();
			return false;
		}
		return true;
	}

	inline CameraBackup BeforeCalcCameraMatrix(EvWorkCamera* camera)
	{
		CameraBackup backup{};
		if (!camera || !Settings::VRDriverSeatView || !Detail::GameplayState())
			return backup;

		auto* car = Game::pl_car();
		if (!car)
			return backup;

		// Learn native view 2 continuously. This is the camera path the user
		// already verified stays synchronized with the car. Storing it in car
		// local space lets virtual view 4 reapply it while raw mode 2 owns
		// vehicle/passenger rendering.
		if (!Detail::VirtualActive &&
			camera->cam_mode_34A == NativeReferenceMode &&
			camera->cam_mode_timer_364 == 0.0f)
		{
			Detail::ReferencePosLocal =
				Detail::WorldToLocal(car->matrix_B0, camera->cam_pos_F8);
			Detail::ReferenceLookLocal =
				Detail::WorldToLocal(car->matrix_B0, camera->look_pos_104);
			Detail::ReferenceValid = true;
			if (!Detail::ReferenceLogged)
			{
				Detail::ReferenceLogged = true;
				spdlog::info(
					"VR DRIVER V4: learned native view-2 camera in player-car local space");
			}
			return backup;
		}

		if (!IsVirtualActive(camera) || !Detail::ReferenceValid ||
			camera->cam_mode_timer_364 != 0.0f)
			return backup;

		backup.pos = camera->cam_pos_F8;
		backup.look = camera->look_pos_104;
		backup.applied = true;

		D3DVECTOR pos = Detail::LocalToWorld(
			car->matrix_B0, Detail::ReferencePosLocal);
		D3DVECTOR look = Detail::LocalToWorld(
			car->matrix_B0, Detail::ReferenceLookLocal);

		D3DVECTOR forward = Detail::Sub(look, pos);
		if (!Detail::Normalize(forward))
			return backup;

		// Match the axis/sign convention used by the successful 2026-09-23
		// native-view-2 tuning build so the saved screenshot values transfer.
		D3DVECTOR right{ -forward.z, 0.0f, forward.x };
		if (!Detail::Normalize(right))
			return backup;
		D3DVECTOR up{
			right.y * forward.z - right.z * forward.y,
			right.z * forward.x - right.x * forward.z,
			right.x * forward.y - right.y * forward.x
		};
		if (!Detail::Normalize(up))
			return backup;

		D3DVECTOR delta{};
		delta = Detail::Add(delta,
			Detail::Mul(forward, Settings::VRDriverSeatForward.get()));
		delta = Detail::Add(delta,
			Detail::Mul(right, Settings::VRDriverSeatRight.get()));
		delta = Detail::Add(delta,
			Detail::Mul(up, Settings::VRDriverSeatUp.get()));

		camera->cam_pos_F8 = Detail::Add(pos, delta);
		camera->look_pos_104 = Detail::Add(look, delta);

		static float lastForward = 9999.0f;
		static float lastRight = 9999.0f;
		static float lastUp = 9999.0f;
		const float f = Settings::VRDriverSeatForward.get();
		const float r = Settings::VRDriverSeatRight.get();
		const float u = Settings::VRDriverSeatUp.get();
		if (std::fabs(f - lastForward) > 0.0001f ||
			std::fabs(r - lastRight) > 0.0001f ||
			std::fabs(u - lastUp) > 0.0001f)
		{
			lastForward = f;
			lastRight = r;
			lastUp = u;
			spdlog::info(
				"VR DRIVER V4 CAMERA: forward={:.3f} right={:.3f} up={:.3f}",
				f, r, u);
		}

		return backup;
	}

	inline void AfterCalcCameraMatrix(EvWorkCamera* camera,
		const CameraBackup& backup)
	{
		if (!camera || !backup.applied)
			return;
		camera->cam_pos_F8 = backup.pos;
		camera->look_pos_104 = backup.look;
	}

	class DriverSeatViewHook final : public Hook
	{
	public:
		std::string_view description() override
		{
			return "VRDriverSeatVirtualFourthView";
		}

		bool apply() override
		{
			Detail::ChangeViewHook = safetyhook::create_mid(
				Module::exe_ptr(Detail::ChangeViewCycleRva),
				Detail::ChangeViewDest);
			Detail::RobotDisplayHook = safetyhook::create_inline(
				Module::exe_ptr(Detail::RobotDisplayRva),
				Detail::RobotDisplayDest);
			return !!Detail::ChangeViewHook && !!Detail::RobotDisplayHook;
		}

		static DriverSeatViewHook instance;
	};

	inline DriverSeatViewHook DriverSeatViewHook::instance;
}
