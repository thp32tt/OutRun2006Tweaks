#pragma once

#include "../../hook_mgr.hpp"
#include "../../plugin.hpp"
#include "../../game_addrs.hpp"
#include "render_semantics.hpp"

#include <cmath>
#include <cstdint>

namespace Settings
{
	extern Setting<bool> VREnabled;
	extern Setting<bool> VRDriverSeatView;
	extern Setting<float> VRDriverSeatForward;
	extern Setting<float> VRDriverSeatRight;
	extern Setting<float> VRDriverSeatUp;
	extern Setting<bool> VRDriverSeatFullCar;
	extern Setting<float> VRDriverSeatCarScale;
	extern Setting<bool> VRDriverSeatPassenger;
}

namespace OutRunVR::DriverSeatView2
{
	// Canonical executable mapping:
	// raw 2 = native view 1, raw 1 = native view 2, raw 0 = native view 3.
	// Virtual view 4 aliases raw mode 1, so it uses the exact native view-2
	// camera controller. A separate flag distinguishes native view 2 from V4.
	constexpr int NativeMode = 1;
	constexpr int CarRenderStateHookRva = 0x69764;
	constexpr int CarRenderMatrixHookRva = 0x69891;
	// Player-car display calls DispCarModel_Common at 0x6BF8C, then restores
	// the game matrix stack with mxPopMatrix at 0x6BF91. Inject the passenger
	// only after that pop, never from inside DispCarModel_Common.
	constexpr int PassengerAfterCarHookRva = 0x6BF96;
	constexpr int RobotDisplayRva = 0x114C10;
	constexpr int ChangeViewCycleRva = 0x84B93;
	constexpr int ChangeViewCycleDoneRva = 0x84BAE;

	struct CameraBackup
	{
		D3DVECTOR pos{};
		D3DVECTOR look{};
		bool applied = false;
	};

	namespace Detail
	{
		inline SafetyHookMid CarRenderStateHook{};
		inline SafetyHookMid CarRenderMatrixHook{};
		inline SafetyHookMid PassengerAfterCarHook{};
		inline SafetyHookMid ChangeViewCycleHook{};
		inline SafetyHookMid ChangeViewCycleDoneHook{};
		inline bool VirtualActive = false;
		inline bool PendingEnterVirtual = false;
		inline bool PendingExitVirtual = false;
		inline bool StateLogged = false;
		inline bool ScaleLogged = false;
		inline bool PassengerLogged = false;
		inline bool PassengerMissingLogged = false;
		inline thread_local bool PassengerDrawInProgress = false;

		inline void ResetVirtualState()
		{
			VirtualActive = false;
			PendingEnterVirtual = false;
			PendingExitVirtual = false;
		}

		inline void ChangeViewCycleDest(safetyhook::Context& ctx)
		{
			auto* camera = reinterpret_cast<EvWorkCamera*>(ctx.esi);
			if (!camera || !Settings::VRDriverSeatView || !Game::current_mode ||
				(*Game::current_mode != STATE_GAME && *Game::current_mode != STATE_GOAL))
			{
				ResetVirtualState();
				return;
			}

			if (camera->cam_mode_timer_364 != 0.0f)
				return;

			if (VirtualActive)
			{
				// V4 is raw mode 1. Before the stock 2->1->0->2 cycle reads
				// cam_mode, temporarily present raw mode 0 so the stock cycle
				// wraps to raw mode 2 (native view 1). The post hook finalizes.
				camera->cam_mode_34A = 0;
				PendingExitVirtual = true;
				PendingEnterVirtual = false;
				return;
			}

			if (camera->cam_mode_34A == 0)
			{
				// Native view 3 normally wraps to raw mode 2. Let the stock code
				// perform that transition, then post-adjust to raw mode 1 and
				// mark it as virtual view 4. Native view 2 remains untouched
				// because its raw mode 1 is never tagged VirtualActive.
				PendingEnterVirtual = true;
				PendingExitVirtual = false;
			}
		}

		inline void ChangeViewCycleDoneDest(safetyhook::Context& ctx)
		{
			auto* camera = reinterpret_cast<EvWorkCamera*>(ctx.esi);
			if (!camera)
			{
				ResetVirtualState();
				return;
			}

			if (PendingEnterVirtual)
			{
				PendingEnterVirtual = false;
				camera->cam_mode_34A = NativeMode;
				VirtualActive = true;
				spdlog::info(
					"VR DRIVER V4: entered virtual view 4 using native view-2 camera controller (raw mode 1)");
				return;
			}

			if (PendingExitVirtual)
			{
				PendingExitVirtual = false;
				VirtualActive = false;
				camera->cam_mode_34A = 2;
				spdlog::info(
					"VR DRIVER V4: exited virtual view 4 -> native view 1 (raw mode 2)");
			}
		}

		inline bool Gameplay()
		{
			return Game::current_mode &&
				(*Game::current_mode == STATE_GAME || *Game::current_mode == STATE_GOAL);
		}

		inline D3DVECTOR Add(const D3DVECTOR& a, const D3DVECTOR& b)
		{
			return { a.x+b.x, a.y+b.y, a.z+b.z };
		}
		inline D3DVECTOR Sub(const D3DVECTOR& a, const D3DVECTOR& b)
		{
			return { a.x-b.x, a.y-b.y, a.z-b.z };
		}
		inline D3DVECTOR Mul(const D3DVECTOR& v, float s)
		{
			return { v.x*s, v.y*s, v.z*s };
		}
		inline float Dot(const D3DVECTOR& a, const D3DVECTOR& b)
		{
			return a.x*b.x + a.y*b.y + a.z*b.z;
		}
		inline bool Normalize(D3DVECTOR& v)
		{
			const float len = std::sqrt(Dot(v,v));
			if (!std::isfinite(len) || len < 1.0e-5f)
				return false;
			v = Mul(v, 1.0f/len);
			return true;
		}

		inline void CarRenderStateDest(safetyhook::Context& ctx)
		{
			EvWorkCamera* camera = Game::camera();
			if (!Settings::VRDriverSeatView || !Settings::VRDriverSeatFullCar ||
				!VirtualActive || !Gameplay() || !camera ||
				camera->cam_mode_timer_364 != 0.0f || camera->cam_mode_34A != NativeMode)
				return;

			auto* car = Game::pl_car();
			if (!car || reinterpret_cast<EVWORK_CAR*>(ctx.ebx) != car)
				return;

			const std::uint32_t originalState = (ctx.eax >> 14) & 3u;
			ctx.eax = (ctx.eax & ~0x0000C000u) | 0x00004000u;
			if (!StateLogged)
			{
				StateLogged = true;
				spdlog::info(
					"VR DRIVER V4: player car render state {} -> 1; native view 2 remains untouched outside V4",
					originalState);
			}
		}

		inline void DrawPassengerOnly(EVWORK_CAR* car)
		{
			if (!Settings::VRDriverSeatPassenger || PassengerDrawInProgress || !car)
				return;
			// Only inject into the main world pass. Reflections/effects may reuse
			// DispCarModel_Common and would otherwise redraw the passenger several
			// extra times per frame.
			if (OutRunVR::GameSemantic::CurrentScope !=
				OutRunVR::GameSemantic::RenderScope::None)
				return;

			auto* event = Game::event(EVENT_ROB02);
			auto* passenger = event ? event->data<EvWorkRobot>() : nullptr;
			if (!passenger)
			{
				if (!PassengerMissingLogged)
				{
					PassengerMissingLogged = true;
					spdlog::warn("VR DRIVER V4: EVENT_ROB02 passenger data unavailable; skipping passenger draw");
				}
				return;
			}

			// Canonical game helper: rebuild the passenger base matrix from the
			// current player-car transform using the original passenger slot (1).
			// This keeps the game's authored seat placement and current animation.
			Game::CalcCharMatrix(car, passenger, 1);

			using RobotDisplayFn = void(__cdecl*)(EvWorkRobot*);
			auto robotDisplay = reinterpret_cast<RobotDisplayFn>(
				Module::exe_ptr(RobotDisplayRva));

			PassengerDrawInProgress = true;
			robotDisplay(passenger);
			PassengerDrawInProgress = false;

			if (!PassengerLogged)
			{
				PassengerLogged = true;
				spdlog::info(
					"VR DRIVER V4: ROB02 passenger-only draw active workId={} chrset={}; ROB01 driver remains untouched/not forced",
					passenger->workId_0, static_cast<int>(passenger->chrset_8));
			}
		}

		inline void PassengerAfterCarDest(safetyhook::Context&)
		{
			EvWorkCamera* camera = Game::camera();
			if (!Settings::VRDriverSeatView || !VirtualActive || !Gameplay() || !camera ||
				camera->cam_mode_timer_364 != 0.0f || camera->cam_mode_34A != NativeMode)
				return;

			// This point is after DispCarModel_Common and its mxPopMatrix, so the
			// passenger renderer receives the same clean matrix-stack ownership it
			// expects when invoked by the normal event display path.
			DrawPassengerOnly(Game::pl_car());
		}

		inline void CarRenderMatrixDest(safetyhook::Context& ctx)
		{
			EvWorkCamera* camera = Game::camera();
			if (!Settings::VRDriverSeatView || !Settings::VRDriverSeatFullCar ||
				!VirtualActive || !Gameplay() || !camera ||
				camera->cam_mode_timer_364 != 0.0f || camera->cam_mode_34A != NativeMode)
				return;

			auto* car = Game::pl_car();
			if (!car || reinterpret_cast<EVWORK_CAR*>(ctx.ebx) != car)
				return;

			const float s = Settings::VRDriverSeatCarScale.get();
			if (std::isfinite(s) && std::fabs(s - 1.0f) >= 0.0001f)
			{
				// At canonical VA 0x469891, DispCarModel_Common has just copied the
				// state-1 body matrix to ESP+0x70. Uniformly scale only its 3x3 basis;
				// translation and the persistent EVWORK_CAR matrices remain untouched.
				auto* m = reinterpret_cast<D3DMATRIX*>(ctx.esp + 0x70);
				m->_11 *= s; m->_12 *= s; m->_13 *= s;
				m->_21 *= s; m->_22 *= s; m->_23 *= s;
				m->_31 *= s; m->_32 *= s; m->_33 *= s;

				if (!ScaleLogged)
				{
					ScaleLogged = true;
					spdlog::info(
						"VR DRIVER V4: player-car visual scale {:.3f} applied only to DispCarModel_Common body matrix",
						s);
				}
			}

		}
	}

	inline bool Active(EvWorkCamera* camera = nullptr)
	{
		if (!Settings::VREnabled || !Settings::VRDriverSeatView ||
			!Detail::VirtualActive || !Detail::Gameplay())
			return false;
		if (!camera)
			camera = Game::camera();
		if (!camera || camera->cam_mode_34A != NativeMode)
		{
			Detail::ResetVirtualState();
			return false;
		}
		return camera->cam_mode_timer_364 == 0.0f;
	}

	inline CameraBackup BeforeCalcCameraMatrix(EvWorkCamera* camera)
	{
		CameraBackup backup{};
		if (!Active(camera))
			return backup;

		backup.pos = camera->cam_pos_F8;
		backup.look = camera->look_pos_104;

		D3DVECTOR forward = Detail::Sub(backup.look, backup.pos);
		if (!Detail::Normalize(forward))
			return backup;
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
		delta = Detail::Add(delta, Detail::Mul(forward, Settings::VRDriverSeatForward.get()));
		delta = Detail::Add(delta, Detail::Mul(right, Settings::VRDriverSeatRight.get()));
		delta = Detail::Add(delta, Detail::Mul(up, Settings::VRDriverSeatUp.get()));

		camera->cam_pos_F8 = Detail::Add(backup.pos, delta);
		camera->look_pos_104 = Detail::Add(backup.look, delta);
		backup.applied = true;

		static float lf=9999.0f, lr=9999.0f, lu=9999.0f;
		const float f=Settings::VRDriverSeatForward.get();
		const float r=Settings::VRDriverSeatRight.get();
		const float u=Settings::VRDriverSeatUp.get();
		if (std::fabs(f-lf)>0.0001f || std::fabs(r-lr)>0.0001f || std::fabs(u-lu)>0.0001f)
		{
			lf=f; lr=r; lu=u;
			spdlog::info("VR DRIVER V4 CAMERA: forward={:.3f} right={:.3f} up={:.3f}", f,r,u);
		}
		return backup;
	}

	inline void AfterCalcCameraMatrix(EvWorkCamera* camera, const CameraBackup& backup)
	{
		if (!camera || !backup.applied)
			return;
		camera->cam_pos_F8 = backup.pos;
		camera->look_pos_104 = backup.look;
	}

	class HookImpl final : public Hook
	{
	public:
		std::string_view description() override { return "VRDriverSeatNativeView2"; }
		bool apply() override
		{
			Detail::CarRenderStateHook = safetyhook::create_mid(
				Module::exe_ptr(CarRenderStateHookRva), Detail::CarRenderStateDest);
			Detail::CarRenderMatrixHook = safetyhook::create_mid(
				Module::exe_ptr(CarRenderMatrixHookRva), Detail::CarRenderMatrixDest);
			Detail::PassengerAfterCarHook = safetyhook::create_mid(
				Module::exe_ptr(PassengerAfterCarHookRva), Detail::PassengerAfterCarDest);
			Detail::ChangeViewCycleHook = safetyhook::create_mid(
				Module::exe_ptr(ChangeViewCycleRva), Detail::ChangeViewCycleDest);
			Detail::ChangeViewCycleDoneHook = safetyhook::create_mid(
				Module::exe_ptr(ChangeViewCycleDoneRva), Detail::ChangeViewCycleDoneDest);
			return !!Detail::CarRenderStateHook && !!Detail::CarRenderMatrixHook &&
				!!Detail::PassengerAfterCarHook && !!Detail::ChangeViewCycleHook &&
				!!Detail::ChangeViewCycleDoneHook;
		}
		static HookImpl instance;
	};
	inline HookImpl HookImpl::instance;
}
