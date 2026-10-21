#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr/game/render_semantics.hpp"
#include "vr/game/stage_edge_cull_projection.hpp"
#include "vr/ui/vr_mirror_aspect_fit.hpp"
#include "vr/game/pmt_node_culling_contract.hpp"
#include "vr_shared.hpp"
#include "vr/game/driver_seat_camera_math.hpp"
#include "vr/game/driver_seat_car_space.hpp"
#include "vr/game/driver_seat_render_pass.hpp"
#include "vr/game/driver_seat_vehicle_scale.hpp"
#include "vr/game/driver_seat_occupant.hpp"
#include "vr/game/cockpit_glass_material_probe.hpp"
#include "vr/game/reflection_frame_budget.hpp"
#include "vr/game/car_base_shadow_stereo.hpp"
#include "vr/runtime_eligibility.hpp"
#include <algorithm>
#include <iostream>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>

namespace Settings
{
	Setting<int> SkyGlowFactor{ "Graphics", "SkyGlowFactor", 4,
		"If set above 0, restores the glowing sky/track effect from the console versions. Resolution of the glow effect is "
		"divided by the factor value: use 1 for full resolution, or 4 for quarter-res (same factor as console).", Range<int>{ 0, 16 } };
	Setting<bool> SkyGlowTwoStep{ "Graphics", "SkyGlowTwoStep", true,
		"Reduces aliasing in the sky glow effect by handling the SkyGlowFactor in two steps. "
		"Likely not console-accurate, but can help reduce the aliasing with Factor = 4 or higher." };
	// Defined by src/vr/settings.cpp. Sky glow samples the mono game backbuffer,
	// so it must be suppressed while true stereo is active or the left-eye bloom
	// gets composited into the right eye as a translucent ghost.
	extern Setting<bool> VREnabled;
	extern Setting<bool> VRStereo;
	extern Setting<bool> VRTelemetry;
	extern Setting<bool> VRMirrorFitDesktop;
    extern Setting<bool> VRMirrorPreserveAspect;
    extern Setting<bool> VRAutoRenderResolution;
    extern Setting<int> VRAntiAliasing;
    extern Setting<int> VRStageCullingMode;
    extern Setting<bool> VRLensFlareCentreEnabled;
    extern Setting<float> VRCullingUnionMarginDegrees;
    extern Setting<bool> VRTransparencySupersampling;
	extern Setting<int> VRRenderWidth;
	extern Setting<int> VRRenderHeight;
	extern Setting<bool> VRDisableDesktopVsync;
	extern Setting<bool> VRDriverSeatView;
    extern Setting<bool> VRDriverSeatGlassMaterialTrace;
    extern Setting<float> VRDriverSeatVehicleScale;
    extern Setting<float> VRDriverSeatGlassOpacity;
	extern Setting<bool> VRDriverSeatCarSpaceBasis;
	extern Setting<int> VRDriverSeatNativeMode;
	extern Setting<float> VRDriverSeatForward;
	extern Setting<float> VRDriverSeatRight;
	extern Setting<float> VRDriverSeatUp;
	extern Setting<bool> VRDriverSeatFullCar;
	extern Setting<bool> VRDriverSeatHideDriver;
	extern Setting<int> VRDriverSeatDriverWorkId;
	extern Setting<int> VRDriverSeatDriverChrset;
	Setting<bool> RestoreXboxBrightness{ "Graphics", "RestoreXboxBrightness", false,
		"Restores the HDR effect from the Xbox releases, brightening up most areas of the game." };

	Setting<bool> UseHiDefCharacters{ "Graphics", "UseHiDefCharacters", true,
		"Forces hi-def versions of Alberto/Jennifer/Clarissa during gameplay." };

	Setting<int> AnisotropicFiltering{ "Graphics", "AnisotropicFiltering", 16,
		"1 - 16, 0 to leave it at games default.", Range<int>{ 0, 16 } };
	Setting<int> ReflectionResolution{ "Graphics", "ReflectionResolution", 1024,
		"Resolution used for car reflections, games default is 128x128, 1024x1024 seems a reasonable improvement.",
		Range<int>{ 0, 8192 } };
	Setting<float> ReflectionUpdateRate{ "Graphics", "ReflectionUpdateRate", 0.5f,
		"How much of the car reflection to redraw each frame: 1.0 redraws all faces every frame, 0.5 spreads it over two frames (games default).", Range<float>{ 0.0f, 1.0f } };
	Setting<bool> TransparencySupersampling{ "Graphics", "TransparencySupersampling", true,
		"Allows game to enable 4x transparency supersampling, heavily reducing aliasing on things like barriers or cloth "
		"around the track edge. For best results use this with \"DX/ANTIALIASING = 2\" inside outrun2006.ini." };
	Setting<bool> ScreenEdgeCullFix{ "Graphics", "ScreenEdgeCullFix", true,
		"Fixes certain stage objects disappearing before they reach edge of screen, when playing at non-4:3 aspect ratio." };
	Setting<bool> DisableVehicleLODs{ "Graphics", "DisableVehicleLODs", true,
		"Disables LODs on vehicles, reducing the ugly pop-in they have." };
	Setting<bool> DisableStageCulling{ "Graphics", "DisableStageCulling", true,
		"Disables culling of certain stage objects, so most distant objects won't obviously pop in to view." };
	Setting<bool> FixZBufferPrecision{ "Graphics", "FixZBufferPrecision", true,
		"Fixes Z-Buffer precision issues, greatly reducing z-fighting and distant object drawing issues "
		"(eg. signs/buildings will have much less pop-in)." };
	Setting<float> CarBaseShadowOpacity{ "Graphics", "CarBaseShadowOpacity", 1.0f,
		"Restores the player car base shadow that was included in other C2C ports. Opacity = 1.0 can help mask some issues "
		"with the stencil shadowing; Xbox C2C uses 0.5, but that makes it very transparent on PC.", Range<float>{ 0.0f, 1.0f } };

	Setting<int> VSync{ "Performance", "VSync", 1,
		"Syncs rendering to your displays refresh rate to reduce screen tearing.",
		{ "Disabled", "Enabled", "Half-refresh-rate" } };

	Setting<bool> WindowedBorderless{ "Window", "WindowedBorderless", true,
		"Forces windowed mode to become borderless. (requires \"DX/WINDOWED = 1\" inside outrun2006.ini)" };
	Setting<int> WindowPositionX{ "Window", "WindowPositionX", 0,
		"Only applied if WindowedBorderless is set to true." };
	Setting<int> WindowPositionY{ "Window", "WindowPositionY", 0,
		"Only applied if WindowedBorderless is set to true." };
	Setting<bool> DisableDPIScaling{ "Window", "DisableDPIScaling", true,
		"Disables DPI scaling on game window, can help fix issues when screen DPI is set above 100%." };
}

class UseHiDefCharacters : public Hook
{
	inline static const char ChrDrGh00_path[] = "Media\\CHR_DR_GH00.bin";
	inline static const char ChrDrGh00_gamepath[] = "\\Media\\CHR_DR_GH00.bin";
	inline static const char ChrDrGh00Usa_path[] = "Media\\CHR_DR_GH00_USA.bin";
	inline static const char ChrDrGh00Usa_gamepath[] = "\\Media\\CHR_DR_GH00_USA.bin";

public:
	std::string_view description() override
	{
		return "UseHiDefCharacters";
	}

	bool validate() override
	{
		return Settings::UseHiDefCharacters;
	}

	void declare_settings() override
	{
		Settings::UseHiDefCharacters.needs_restart();
	}

	bool apply() override
	{
		// Switch Chr\CHR_DR_GH00*.bin usages to read from Media\CHR_DR_GH00*.bin instead, if they exist
		// (Chr\ versions are missing hair anims which Media\ versions fortunately include - Media\ versions are otherwise unused)
		{
			if (std::filesystem::exists(ChrDrGh00_path))
				Game::chrset_info[ChrSet::CHR_DR_GH00].bin_ptr = ChrDrGh00_gamepath;
			if (std::filesystem::exists(ChrDrGh00Usa_path))
				Game::chrset_info[ChrSet::CHR_DR_GH00_USA].bin_ptr = ChrDrGh00Usa_gamepath;
		}

		int* driver_chrsets = Module::exe_ptr<int>(0x2549B0);
		int* heroine_chrsets = Module::exe_ptr<int>(0x2549C8);

		// Switch Alberto CHR_DR_M00 -> CHR_DR_MH00
		driver_chrsets[0] = ChrSet::CHR_DR_MH00;
		Memory::VP::Patch(Module::exe_ptr(0x87F41 + 1), { uint8_t(ChrSet::CHR_DR_MH00) }); // O2SP

		// Switch Jennifer CHR_DR_L00 -> CHR_DR_LH00
		heroine_chrsets[3] = ChrSet::CHR_DR_LH00;
		Memory::VP::Patch(Module::exe_ptr(0x8803A + 1), { uint8_t(ChrSet::CHR_DR_LH00) }); // O2SP

		// Switch Clarissa CHR_DR_G00_* -> CHR_DR_GH00_*
		heroine_chrsets[4] = ChrSet::CHR_DR_GH00; // (game code handles switching heroine_chrsets to USA variant, so we don't need to check RestoreJPClarissa here)

		// Clarissa O2SP code (this is also patched by RestoreJPClarissa, so make sure both set it to same value...)
		Memory::VP::Patch(Module::exe_ptr(0x88044 + 1), { Settings::RestoreJPClarissa ? uint8_t(ChrSet::CHR_DR_GH00) : uint8_t(ChrSet::CHR_DR_GH00_USA) });

		return true;
	}

	static UseHiDefCharacters instance;
};
UseHiDefCharacters UseHiDefCharacters::instance;

// Keep camera placement and the native car/occupant render pass eligible
// under the same validated basis, following the standalone Quest's separation
// of cockpit-active, vehicle and occupant rendering responsibilities.
static bool VRDriverSeatGameplayActive() noexcept;

static bool VRDriverSeatCameraPose(const EvWorkCamera* camera,
    D3DVECTOR& translatedPosition, D3DVECTOR& translatedLook) noexcept
{
    if (!camera)
        return false;
    OutRunVR::DriverSeatCamera::Vec3 newPos{}, newLook{};
    const auto& pos = camera->cam_pos_F8;
    const auto& look = camera->look_pos_104;
    const auto* player = Game::pl_car();
    if (!player)
        return false;
    const auto& m = player->matrix_B0;
    // A car-space matrix can intermittently be stale during interpolation,
    // looping, camera switches, respawn or a new stage. Previously each
    // rejected frame fell back to the bumper camera, then the very next
    // valid frame returned to car space, yielding an apparent cockpit
    // zoom-in/zoom-out oscillation. Latch that fallback for the remainder
    // of the selected native camera-mode session; do not alternate bases.
    // Reset only after actually leaving the game or changing native mode,
    // not after an incidental invalid render-time matrix.
    static thread_local bool carSpaceFallbackLatched = false;
    static thread_local int lastCameraMode = -1;
    static thread_local const EvWorkCamera* lastCamera = nullptr;
    const int mode = static_cast<int>(camera->cam_mode_34A);
    if (mode != lastCameraMode || camera != lastCamera ||
        !VRDriverSeatGameplayActive())
        carSpaceFallbackLatched = false;
    lastCameraMode = mode;
    lastCamera = camera;
    const bool carSpaceRequested =
        Settings::VRDriverSeatCarSpaceBasis && !carSpaceFallbackLatched;
    bool usedCarSpace = false;
    if (!OutRunVR::DriverSeatCamera::ComputeStableSeatPose(
            {pos.x, pos.y, pos.z}, {look.x, look.y, look.z},
            carSpaceRequested,
            {{m._31, m._32, m._33}, {m._21, m._22, m._23}},
            Settings::VRDriverSeatForward.get(),
            Settings::VRDriverSeatRight.get(),
            Settings::VRDriverSeatUp.get(), newPos, newLook,
            &usedCarSpace))
        return false;
    if (carSpaceRequested && !usedCarSpace)
    {
        carSpaceFallbackLatched = true;
        spdlog::warn(
            "VR DRIVER SEAT BASIS STABILIZED: car-space source invalid; "
            "keep native-camera offset until camera mode/session resets");
    }
    if (!Settings::VRDriverSeatCarSpaceBasis)
        carSpaceFallbackLatched = false;
    translatedPosition = {newPos.x, newPos.y, newPos.z};
    translatedLook = {newLook.x, newLook.y, newLook.z};
    return true;
}

// START includes cinematics; only progress 65 is the playable countdown.
static bool VRDriverSeatGameplayActive() noexcept
{
    if (!Game::current_mode)
        return false;
    if (*Game::current_mode == STATE_GAME ||
        *Game::current_mode == STATE_GOAL)
        return true;
    return *Game::current_mode == STATE_START &&
        Game::game_start_progress_code &&
        *Game::game_start_progress_code == 65;
}


static bool VRDriverSeatCameraEligible(const EvWorkCamera* camera) noexcept
{
    if (!OutRunVR::DriverSeatRenderPass::IsWorldOrCockpitPass())
        return false;
    // A missing player vehicle has no seat geometry to render. Do not
    // displace the camera, force a near plane, or hide any occupant.
    if (!camera || !Game::pl_car())
        return false;
    // Native camera switch at EXE RVA 0x84A40 uses +0x340/+0x344.
    // A transient mode 1 is not enough to move the synthetic seat camera:
    // reject pending native transitions for camera, car, driver and near clip.
    if (!OutRunVR::DriverSeatCamera::NativeViewTransitionSettled(
            camera->word340, camera->word344))
        return false;
    // Native scene/mode eligibility is independent of camera-space math.
    // In a loop the native forward vector can be vertical while the car
    // matrix still offers a stable seat basis. Check the selected pose once,
    // and use this SAME result for camera, body, driver and near clip.
    if (!OutRunVR::DriverSeatCamera::NativeCameraModeEligible(
            Settings::VREnabled && Settings::VRDriverSeatView,
            VRDriverSeatGameplayActive(), camera->cam_mode_timer_364,
            static_cast<int>(camera->cam_mode_34A),
            Settings::VRDriverSeatNativeMode.get()))
        return false;

    D3DVECTOR correctedPosition{}, correctedLook{};
    return VRDriverSeatCameraPose(camera, correctedPosition, correctedLook);
}

class VRDriverSeatRenderTest : public Hook
{
	constexpr static int PlayerCarRenderState_HookAddr = 0x69764;
	constexpr static int RobotDisplay_Addr = 0x114C10;

	inline static SafetyHookMid PlayerCarRenderStateHook{};
	inline static SafetyHookInline RobotDisplayHook{};
	inline static bool FullCarLogged = false;
	inline static bool DriverHiddenLogged = false;
	inline static std::array<std::uint64_t, 24> RobotTraceKeys{};
	inline static std::size_t RobotTraceCount = 0;

	static bool Active()
	{
		// Driver-seat geometry/camera testing must not depend on the current
		// stereo recovery gate. Keeping it native-game active makes the test
		// visible on the PC mirror too and prevents temporary host eligibility
		// changes from turning the car/driver path on and off.
		return VRDriverSeatCameraEligible(Game::camera());
	}

	static void PlayerCarRenderState_dest(SafetyHookContext& ctx)
	{
		if (!Active() || !Settings::VRDriverSeatFullCar)
			return;
		EVWORK_CAR* player = Game::pl_car();
		if (!player || reinterpret_cast<EVWORK_CAR*>(ctx.ebx) != player)
			return;

		const std::uint32_t originalState = (ctx.eax >> 14) & 3u;
		// Canonical DispCarModel_Common disassembly shows state 1 takes the
		// full exterior/body path; state 0 skips those blocks and was the reason
		// the first prototype made the car disappear.
		ctx.eax = (ctx.eax & ~0x0000C000u) | 0x00004000u;
		if (!FullCarLogged)
		{
			FullCarLogged = true;
			spdlog::info(
				"VR DRIVER SEAT TEST: player car render state {} -> 1 (full model); persistent flags unchanged",
				originalState);
		}
	}

	static void TraceRobotCandidate(EvWorkRobot* robot)
	{
		if (!robot || RobotTraceCount >= RobotTraceKeys.size())
			return;
		const std::uint64_t key =
			(static_cast<std::uint64_t>(robot->workId_0) << 32) |
			static_cast<std::uint32_t>(robot->chrset_8);
		for (std::size_t i = 0; i < RobotTraceCount; ++i)
			if (RobotTraceKeys[i] == key)
				return;
		RobotTraceKeys[RobotTraceCount++] = key;
		spdlog::info("VR DRIVER SEAT ROBOT: candidate workId={} chrset={}",
			robot->workId_0, static_cast<int>(robot->chrset_8));
	}

	static void __cdecl RobotDisplay_dest(EvWorkRobot* robot)
	{
		if (Active() && robot)
		{
			TraceRobotCandidate(robot);
            // Native game tables track selected driver vs heroine chrsets.
            // Unlike a naked workId, this protects the seated passenger.
            const int* driverChrsets = Module::exe_ptr<int>(0x2549B0);
            const int* heroineChrsets = Module::exe_ptr<int>(0x2549C8);
			if (OutRunVR::DriverSeatOccupant::HideIdentifiedDriver(
				Settings::VRDriverSeatHideDriver,
				static_cast<int>(robot->workId_0),
				static_cast<int>(robot->chrset_8),
				Settings::VRDriverSeatDriverWorkId.get(),
				Settings::VRDriverSeatDriverChrset.get(),
                driverChrsets, heroineChrsets, 6))
			{
				if (!DriverHiddenLogged)
				{
					DriverHiddenLogged = true;
					spdlog::info(
						"VR DRIVER SEAT TEST: hiding configured driver robot workId={} chrset={}; other robots/passenger remain enabled",
						robot->workId_0, static_cast<int>(robot->chrset_8));
				}
				return;
			}
		}
		RobotDisplayHook.ccall<void>(robot);
	}

public:
	std::string_view description() override
	{
		return "VRDriverSeatRenderTest";
	}

	bool apply() override
	{
        // A rejected second detour used to leave the car-state midhook live
        // even though HookManager was told installation failed. Either both
        // gameplay callbacks are active, or neither changes native rendering.
        return OutRunVR::DriverSeatRenderPass::InstallAtomicCockpitPair(
            PlayerCarRenderStateHook, RobotDisplayHook,
            [] { return safetyhook::create_mid(
                Module::exe_ptr(PlayerCarRenderState_HookAddr),
                PlayerCarRenderState_dest); },
            [] { return safetyhook::create_inline(
                Module::exe_ptr(RobotDisplay_Addr), RobotDisplay_dest); });
	}

	static VRDriverSeatRenderTest instance;
};
VRDriverSeatRenderTest VRDriverSeatRenderTest::instance;

// Canonical PC OR2006C2C.EXE player-car renderer:
// 0x4697B8 LEA EDX,[ESP+70h]; 0x4697BC PUSH EDX;
// 0x4697BD CALL 0x409FD0 (load temporary display matrix).
// Restrict this midhook to the EXACT player-car EBX and live cockpit pose;
// no physics EVWORK_CAR, camera matrix, resource, texture, PMT or disk writes.
class VRDriverSeatVehicleScaleRenderHook final : public Hook
{
    static constexpr int PlayerCarMatrixCallRva = 0x697BD;
    inline static SafetyHookMid MatrixCallHook{};
    inline static bool FirstAppliedLogged = false;

    static void ScalePlayerCarMatrix(SafetyHookContext& ctx)
    {
        if (!Settings::VREnabled || !Settings::VRDriverSeatView ||
            !VRDriverSeatCameraEligible(Game::camera()) ||
            reinterpret_cast<EVWORK_CAR*>(ctx.ebx) != Game::pl_car() ||
            !ctx.esp)
            return;

        const float scale = Settings::VRDriverSeatVehicleScale.get();
        if (!std::isfinite(scale) || scale == 1.0f)
            return;
        // Before the original call, [ESP] is the pointer PUSHed from EDX
        // to the caller's own 64-byte stack-local display transform.
        const auto* args = reinterpret_cast<D3DMATRIX* const*>(ctx.esp);
        D3DMATRIX* temporaryRenderMatrix = args[0];
        if (!temporaryRenderMatrix ||
            !OutRunVR::DriverSeatVehicle::TryScaleModelBasis(
                *temporaryRenderMatrix, scale))
            return;

        if (!FirstAppliedLogged)
        {
            FirstAppliedLogged = true;
            spdlog::info(
                "VR DRIVER SEAT: player-only temporary render matrix scaled {:.2f}; world translation, physics and original PMT unchanged",
                scale);
        }
    }

public:
    std::string_view description() override
    {
        return "VRDriverSeatVehicleScaleRenderHook";
    }

    bool apply() override
    {
        // Fail closed for unknown EXE variants instead of detouring nearby
        // instructions or risk scaling non-player traffic/world geometry.
        constexpr std::array<std::uint8_t, 5> signature{
            0xE8, 0x0E, 0x08, 0xFA, 0xFF
        };
        const auto* instruction =
            Module::exe_ptr<std::uint8_t>(PlayerCarMatrixCallRva);
        if (!std::equal(signature.begin(), signature.end(), instruction))
        {
            spdlog::warn(
                "VR DRIVER SEAT: original player matrix call signature differs, car scale hook not installed");
            return false;
        }
        MatrixCallHook = safetyhook::create_mid(
            Module::exe_ptr(PlayerCarMatrixCallRva), ScalePlayerCarMatrix);
        return !!MatrixCallHook;
    }
    static VRDriverSeatVehicleScaleRenderHook instance;
};
VRDriverSeatVehicleScaleRenderHook
    VRDriverSeatVehicleScaleRenderHook::instance;

// Canonical EXE+0x4901: PUSH EDX; CALL 0x408C80 (material application).
// EXE+0x48F2 loads the PMT material table; EXE+0x48F5 multiplies
// the selected material index by 0x58. This global loop is NOT glass-only.
class VRDriverSeatGlassMaterialProbe : public Hook
{
    static constexpr int ApplyMaterialRva = 0x4901;
    inline static SafetyHookMid ApplyMaterialHook{};
    inline static std::array<std::uintptr_t, 32> Seen{};
    inline static std::size_t Count = 0;

    static void MaterialEntry(SafetyHookContext& ctx)
    {
        if (!Settings::VREnabled || !Settings::VRDriverSeatView ||
            !VRDriverSeatGameplayActive() || !Game::pl_car() ||
            !ctx.edx || Count >= Seen.size())
            return;
        const auto* material = reinterpret_cast<const std::uint32_t*>(ctx.edx);
        const std::uint32_t attr = material[1];
        if (!OutRunVR::CockpitGlassProbe::CandidateBlend(attr))
            return;
        const auto identity = reinterpret_cast<std::uintptr_t>(material);
        for (std::size_t i=0; i<Count; ++i)
            if (Seen[i] == identity)
                return;
        Seen[Count++] = identity;
        spdlog::info(
            "VR COCKPIT GLASS PROBE (candidate only, ownership unknown): "
            "material=0x{:X} colorIndex={} attr=0x{:08X} src={} dst={} count={}",
            identity, material[0], attr, (attr>>8)&15u, (attr>>12)&15u, Count);
    }

public:
    std::string_view description() override { return "VRDriverSeatGlassMaterialProbe"; }
    bool validate() override { return Settings::VRDriverSeatGlassMaterialTrace; }
    void declare_settings() override { Settings::VRDriverSeatGlassMaterialTrace.needs_restart(); }
    bool apply() override
    {
        // Reject variant or relocated code, never install on an unknown EXE.
        const auto* p = Module::exe_ptr<std::uint8_t>(ApplyMaterialRva);
        constexpr std::array<std::uint8_t, 6> signature =
            { 0x52, 0xE8, 0x79, 0x43, 0x00, 0x00 };
        if (!std::equal(signature.begin(), signature.end(), p))
        {
            spdlog::warn("VR GLASS PROBE: original PMT call signature differs; hook not installed");
            return false;
        }
        ApplyMaterialHook = safetyhook::create_mid(
            Module::exe_ptr(ApplyMaterialRva), MaterialEntry);
        return !!ApplyMaterialHook;
    }
    static VRDriverSeatGlassMaterialProbe instance;
};
VRDriverSeatGlassMaterialProbe VRDriverSeatGlassMaterialProbe::instance;


class RestoreCarBaseShadow : public Hook
{
	static void __cdecl CalcPeraShadow(int a1, int a2, int a3, float a4)
	{
		// These call sites were nullsub_1 calls on PC, so skipping the draw
		// restores exactly what the game did without the shadow.
		if (Settings::CarBaseShadowOpacity <= 0.f ||
			!std::isfinite(a4))
			return;
        float shadowAlpha = 0.f;
        if (!OutRunVR::CarShadowStereo::ValidScaledAlpha(
                a4, Settings::CarBaseShadowOpacity.get(), shadowAlpha))
            return;

		// The selector also invokes this PC nullsub replacement, but
		// pl_car() there is not the selected model (or may be null).
		// Do not borrow a stale gameplay matrix or pass a null matrix.
		// Until the selector's transform owner is proven, omit its shadow.
		if (!VRDriverSeatGameplayActive())
			return;
		EVWORK_CAR* car = Game::pl_car();
		if (!car)
			return;
		Game::mxPushLoadMatrix(&car->matrix_B0);
		Game::mxTranslate(0.0f, 0.05f, 0.0f);

		// Each original-mod shadow CALL is world geometry, not a HUD sprite.
		// EffectiveScope prefers an old selected SpriteNode's exact ScreenHud
		// to CurrentScope. A nonqueued direct Draw therefore needs a bounded
		// exact owner; it must never overwrite the owner of a live queue draw.
		{
			const auto directWorldScope =
				Settings::VREnabled &&
				!OutRunVR::GameSemantic::QueueRenderActive()
				? OutRunVR::GameSemantic::RenderScope::WorldParticle
				: OutRunVR::GameSemantic::RenderScope::None;
			// The direct producer must not consume an unrelated pending
			// HUD one-shot token or inherit a stale queue-owned scope.
			// Keep the legacy RAII world scope immediately around the draw.
			// This also preserves the original live-queue/desktop fallback.
			OutRunVR::GameSemantic::ScopedExactProducerSemantic directWorld(
				directWorldScope, nullptr, true,
				OutRunVR::GameSemantic::ProducerToken::CarBaseShadow);
			OutRunVR::GameSemantic::ScopedRenderSemantic semantic(
				OutRunVR::GameSemantic::RenderScope::WorldParticle);
			Game::DrawObjectAlpha_Internal(
				a1, shadowAlpha, 0, -1);
		}
		Game::mxPopMatrix();
	}

public:
	std::string_view description() override
	{
		return "RestoreCarBaseShadow";
	}

	bool apply() override
	{
		constexpr int DispCarModel_Common_HookAddr = 0x69EB4;
		constexpr int DispSelCarModel_HookAddr = 0x6AC76; // O2SP car selection
		constexpr int Sumo_DispSelCarModel_HookAddr = 0x6B766; // C2C car selection

		// These three funcs contain nullsub_1 calls which were CalcPeraShadow calls in O2SP / C2CXbox
		// We can't just hook nullsub_1 since a bunch of other nulled out code also calls it, instead we'll rewrite them to call our CalcPeraShadow func
		Memory::VP::InjectHook(Module::exe_ptr(DispCarModel_Common_HookAddr), CalcPeraShadow, Memory::HookType::Call);
		Memory::VP::InjectHook(Module::exe_ptr(DispSelCarModel_HookAddr), CalcPeraShadow, Memory::HookType::Call);
		Memory::VP::InjectHook(Module::exe_ptr(Sumo_DispSelCarModel_HookAddr), CalcPeraShadow, Memory::HookType::Call);

		return true;
	}

	static RestoreCarBaseShadow instance;
};
RestoreCarBaseShadow RestoreCarBaseShadow::instance;

// Canonical SceneEffect/lens producer proof:
//   sub_40CAE0 owns the effect loop,
//   EXE+0xCABE is the single DrawObjectAlpha_Internal producer call,
//   EXE+0xCF4E calls Calc3D2D for its projected anchor.
// Do not infer lens ownership from generic alpha state or tune disparity scalars.
class VRLensFlareProjected2D : public Hook
{
    // Original OR2006C2C.EXE SHA 68ceb386... disassembly:
    // sub_40CAE0 at 0xCF4E projects the light centre (Calc3D2D),
    // then 0xD3A0 loads object 0x570002 and 0xD3A5 calls sub_40C980,
    // which directly forwards to DrawObjectAlpha_Internal. The later
    // outer halo discs use distinct sub_40C9A0 calls at 0xD5F5..0xD796.
    // Prior 0xCABE hook only covered the OUTER sub_40C9A0 path.
    // Correct the central SUN object alone: preserve its world matrix
    // through true per-eye stereo, rather than classifying it as an
    // already-projected flat ScreenHud. Leave every other flare child and
    // original display opacity untouched.
    inline static SafetyHookMid LensCentreEnterHook{};
    inline static SafetyHookMid LensCentreLeaveHook{};
    inline static thread_local unsigned LensCentreDepth = 0;
    // This is the depth at which a non-queue, VR-enabled centre became the
    // owner. Count every D3A5 entry, even when skipped, so each D3AA exit
    // balances its own call without restoring an outer centre prematurely.
    inline static thread_local unsigned LensCentreOwnerDepth = 0;
    inline static thread_local OutRunVR::GameSemantic::RenderScope
        LensCentreSavedScope = OutRunVR::GameSemantic::RenderScope::None;
    inline static thread_local OutRunVR::GameSemantic::ProducerToken
        LensCentreSavedProducer = OutRunVR::GameSemantic::ProducerToken::None;
    inline static thread_local std::uint64_t LensCentreSavedEpoch = 0;

    static void LensCentreEnter(safetyhook::Context&)
    {
        // A non-queued original producer must never overwrite a selected
        // SpriteNode's semantic during nested queue processing.
        ++LensCentreDepth;
        // Original 0xD3A5/0xD3AA are paired call edges, including nested
        // and disabled-VR paths. An ignored nested queue call must still
        // consume exactly one depth on its matching leave, not pop the
        // active outer sun's saved render scope.
        if (!Settings::VREnabled ||
            OutRunVR::GameSemantic::QueueRenderActive() ||
            LensCentreDepth != 1)
            return;
        LensCentreOwnerDepth = LensCentreDepth;
        LensCentreSavedScope = OutRunVR::GameSemantic::CurrentScope;
        LensCentreSavedProducer = OutRunVR::GameSemantic::CurrentDirectExactProducer;
        LensCentreSavedEpoch = OutRunVR::GameSemantic::CurrentLensCentreCallEpoch;
        auto& next = OutRunVR::GameSemantic::NextLensCentreCallEpoch;
        if (++next == 0)
            ++next;
        OutRunVR::GameSemantic::CurrentLensCentreCallEpoch = next;
        OutRunVR::GameSemantic::CurrentDirectExactProducer =
            OutRunVR::GameSemantic::ProducerToken::LensFlareCentre;
        OutRunVR::GameSemantic::CurrentScope =
            OutRunVR::GameSemantic::RenderScope::WorldBillboard;
    }

    static void LensCentreLeave(safetyhook::Context&)
    {
        // A captured render scope must be restored even if VR is disabled
        // during the original draw; gating exit on the current VR setting
        // would leak the central WorldBillboard semantic into later effects.
        if (!LensCentreDepth)
            return;
        // Only the precise enter which acquired ownership may restore it.
        // Preserve that restore even if VREnabled toggles during the call.
        if (LensCentreOwnerDepth == LensCentreDepth)
        {
            OutRunVR::GameSemantic::CurrentScope = LensCentreSavedScope;
            OutRunVR::GameSemantic::CurrentDirectExactProducer = LensCentreSavedProducer;
            OutRunVR::GameSemantic::CurrentLensCentreCallEpoch = LensCentreSavedEpoch;
            LensCentreSavedProducer = OutRunVR::GameSemantic::ProducerToken::None;
            LensCentreSavedEpoch = 0;
            LensCentreSavedScope =
                OutRunVR::GameSemantic::RenderScope::None;
            LensCentreOwnerDepth = 0;
        }
        --LensCentreDepth;
    }

	static void __cdecl DrawObjectAlphaProjected(
		int objectId, float alpha, void* work, int flags)
	{
        // One original 0xCABE call occurs for each source effect object,
        // rather than each of the 4-5 visible flare discs being one surface.
        // Capture bounded per-object evidence to identify the centre-only
        // ghost WITHOUT reclassifying the normal surrounding lens circles.
        // Object/flag logging must not affect alpha, original call count,
        // return value, game matrices or shader state.
        if (Settings::VRTelemetry)
        {
            static std::atomic<std::uint64_t> flareCalls{ 0 };
            const auto hit =
                flareCalls.fetch_add(1, std::memory_order_relaxed) + 1;
            if (hit <= 24 || (hit & (hit - 1)) == 0)
                spdlog::info(
                    "VR P0 FLARE OBJECT: id={} alpha={} flags=0x{:X} calls={} gameState={}",
                    objectId, alpha, static_cast<unsigned>(flags), hit,
                    Game::current_mode ? static_cast<int>(*Game::current_mode) : -1);
        }
		OutRunVR::GameSemantic::ScopedRenderSemantic semantic(
			OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D);
		Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);
	}

    // Unlike the outer halo discs at 0xCABE, the central 0x570002 sun
    // travels through sub_40C980 and its independent 0xC993 E8 call to
    // DrawObjectAlpha_Internal. The old D3A5 scope only marked the parent
    // lifetime; nested SceneEffect and the actual draw can overwrite it.
    // Own THIS one actual draw, not the shared object renderer or the
    // four already-correct surrounding discs. Matching the EXE's existing
    // 0xCABE call signature preserves the original arguments and alpha.
    static void __cdecl DrawObjectAlphaCentre(
        int objectId, float alpha, void* work, int flags)
    {
        // D3A5 owns the 0x570002 central world sun. Previously its actual
        // C993 DrawObjectAlpha call replaced this world owner with the flat
        // projected screen-effect layer, defeating finite per-eye stereo.
        // Match BOTH the active original parent and its exact sun object.
        // Desktop, partial parent-hook install and all outer CABE rings retain
        // their original raster classification and one game Draw call.
        const auto centreScope =
            Settings::VREnabled && LensCentreDepth != 0 &&
            LensCentreOwnerDepth == LensCentreDepth &&
            !OutRunVR::GameSemantic::QueueRenderActive() &&
            objectId == 0x570002
            ? OutRunVR::GameSemantic::RenderScope::WorldBillboard
            : OutRunVR::GameSemantic::RenderScope::None;
        // HMD-confirmed 2026-10-20: this exact C993 centre appears twice
        // and head-follows even while the outer CABE rings remain distinct.
        // Until a same-call/pose/raw-WVP proof permits per-eye rendering,
        // remove this ONE source draw, not a whole SceneEffect or sun/sky
        // producer. A user setting can restore it for comparison. Desktop
        // and unknown C993 objects always execute their original draw.
        // Quest3 2026-10-20: C993's central point remained doubled even
        // with LensFlareCentreEnabled=false. A transient D3A5 scope or
        // queue state must NOT bypass the suppression of this precisely
        // identified C993 object. This skips only original object 0x570002
        // in VR, not other C993 objects, CABE halos, sky, or desktop.
        // It is a temporary optical workaround, not a corrected stereo WVP.
        if (Settings::VREnabled && objectId == 0x570002 &&
            !Settings::VRLensFlareCentreEnabled.get())
        {
            if (Settings::VRTelemetry)
            {
                static std::atomic<std::uint64_t> hits{ 0 };
                const auto n = hits.fetch_add(
                    1, std::memory_order_relaxed) + 1;
                if (n <= 8 || (n & (n - 1)) == 0)
                    spdlog::info(
                        "VR LENS C993 CENTER HIDDEN: count={} "
                        "parent={} owner={} queue={} (CABE intact)",
                        n, LensCentreDepth, LensCentreOwnerDepth,
                        OutRunVR::GameSemantic::QueueRenderActive() ? 1 : 0);
            }
            return;
        }
        // The previously-hidden C993 sun now executes in the main profile.
        // Observe this original CALL and parent state so a later per-eye
        // WVP trace can distinguish a second original sun from CABE halos.
        if (Settings::VREnabled && Settings::VRTelemetry &&
            objectId == 0x570002)
        {
            static std::atomic<std::uint64_t> draws{ 0 };
            const auto n = draws.fetch_add(1, std::memory_order_relaxed) + 1;
            if (n <= 8 || (n & (n - 1)) == 0)
                spdlog::info(
                    "VR SUN C993 ORIGINAL DRAW: hits={} worldOwner={} "
                    "parent={} nestedOwner={} queue={} requestedVisible={}",
                    n,
                    centreScope ==
                        OutRunVR::GameSemantic::RenderScope::WorldBillboard,
                    LensCentreDepth, LensCentreOwnerDepth,
                    OutRunVR::GameSemantic::QueueRenderActive() ? 1 : 0,
                    Settings::VRLensFlareCentreEnabled.get() ? 1 : 0);
        }
        // An unrelated one-shot producer (for example an earlier queued
        // HUD/world draw) must not replace this exact C993 centre draw.
        // Keep its token intact for the original later owner, and leave all
        // C993 desktop/non-centre calls unchanged when centreScope is None.
        OutRunVR::GameSemantic::ScopedExactProducerSemantic semantic(
            centreScope, nullptr, true,
            centreScope != OutRunVR::GameSemantic::RenderScope::None
                ? OutRunVR::GameSemantic::ProducerToken::LensFlareCentre
                : OutRunVR::GameSemantic::ProducerToken::None);
        // The exact token is one-shot. Retain the centre's world scope for
        // ALL nested GPU draws, then restore the previous SceneEffect owner.
        // When this is not our centre, preserve the original caller scope.
        OutRunVR::GameSemantic::ScopedRenderSemantic centreDrawScope(
            centreScope != OutRunVR::GameSemantic::RenderScope::None
                ? centreScope : OutRunVR::GameSemantic::CurrentScope);
        // The original alpha renderer may enter nested SceneEffect helpers
        // between c64 upload and GPU Draw. Keep this precise C993 source
        // authoritative until its synchronous original draw returns.
        // No CABE ring, queued SpriteNode, desktop or external UI is affected.
        OutRunVR::GameSemantic::ScopedExactLensCentreGpuDraw centreGpuOwner(
            centreScope != OutRunVR::GameSemantic::RenderScope::None);
        Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);
    }

public:
	std::string_view description() override
	{
		return "VRLensFlareProjected2D";
	}

	bool apply() override
	{
		Memory::VP::InjectHook(
			Module::exe_ptr(0xCABE), DrawObjectAlphaProjected,
			Memory::HookType::Call);
        // Separate verified E8 into the same DrawObjectAlpha_Internal ABI,
        // invoked only by the primary sun's sub_40C980 producer.
        Memory::VP::InjectHook(
            Module::exe_ptr(0xC993), DrawObjectAlphaCentre,
            Memory::HookType::Call);
        // Exact E8 source for central 0x570002 object, not the shared
        // sub_40C980 target. If either enter/leave cannot relocate, retain
        // the unchanged original lens behavior rather than leaking a world
        // semantic beyond this sole object.
        LensCentreEnterHook = safetyhook::create_mid(
            Module::exe_ptr(0xD3A5), LensCentreEnter);
        LensCentreLeaveHook = safetyhook::create_mid(
            Module::exe_ptr(0xD3AA), LensCentreLeave);
        if (!LensCentreEnterHook || !LensCentreLeaveHook)
        {
            LensCentreEnterHook = {};
            LensCentreLeaveHook = {};
            spdlog::warn(
                "VR P0 LENS CENTRE: 0xD3A5/0xD3AA partial hook rolled back; keeping original scene effect");
        }
        else
            spdlog::info(
                "VR P0 LENS CENTRE: 0xD3A5 owner plus exact 0xC993 projected draw scope (outer 0xCABE discs untouched)");
		spdlog::info(
			"VR P0 FLARE: exact EXE+0xCABE producer -> PROJECTED_SCREEN_EFFECT_2D; placement remains WVP-proven");
		return true;
	}

	static VRLensFlareProjected2D instance;
};
VRLensFlareProjected2D VRLensFlareProjected2D::instance;

// Restores the console's lighting dynamic range, which the PC port didn't make
// use of, costing roughly a third of the sun on surfaces facing it.
//
// In the stage data the light diffuse is often authored between 1.00 - 1.64 on
// the original OR2 stages.
// The vertex shader ends on "mad oD0, r0, r2, r1", and oD0 is a colour output,
// which hardware clamps to 0.0 - 1.0. So saturate(N dot L) * material * 1.64 clips 
// at 1.0 and the pixel stage then modulates the texture by 1.0 instead of 1.64.
//
// The console keeps the same value under the clamp by working in a dynamic range
// of 2: the light diffuse is halved into the constant, the ambient half of the
// equation is scaled by CV_R_DRANGE (c16) to match, and the first texture stage
// then doubles the result back with D3DTOP_MODULATE2X. The arcade shader source
// names the constant "reciprocal of dynamic range" and comments the clamp.
//
class RestoreXboxBrightness : public Hook
{
	// (1) Doubling is chosen per shader by a flag holding the bound shader's id.
	// Only id 1, a shader combined from the VsUnit tables, has its lighting halved
	// and so wants doubling back. vsSelectVertexShader binds the shader and returns
	// without ever writing the flag; the one path that does write it is for an entry
	// carrying no shader, which writes zero, so the flag never holds 1.
	//
	// The hook adds the missing write where the shader is bound. esi holds the
	// shader entry there, and its third word is the id.
	static constexpr int SelectVertexShader_IdBranch_Addr = 0x106E9;
	static constexpr int Modulate2xFlag_Addr = 0x49EDD0;
	static constexpr int ShaderEntry_Id = 2;

	inline static SafetyHookMid SelectVertexShader_hook = {};
	static void SelectVertexShader_dest(safetyhook::Context& ctx)
	{
		const uint32_t* entry = reinterpret_cast<const uint32_t*>(ctx.esi);
		if (entry)
			*Module::exe_ptr<uint32_t>(Modulate2xFlag_Addr) = entry[ShaderEntry_Id];
	}

	// (2) The promotion has to be redone for every material. psSetTextureColorOp
	// has its own copy of it but only reaches that when the requested colour op
	// differs from the previous one, and it records the op unpromoted. Two materials
	// that both ask for MODULATE are then identical to that test even when their
	// shader ids differ, so the second inherits the first's MODULATE2X combiner and
	// its intensity_state.
	//
	// Promoting from a hook at the entry, with the in-function copy blanked, makes
	// the op reaching that test the promoted one. A differing shader id then reopens
	// it by itself, while an op that really is unchanged still short circuits and
	// avoids rebuilding the shader every draw.
	static constexpr int PsSetTextureColorOp_Addr = 0xB800;
	static constexpr int PsSetTextureColorOp_Inline_Addr = 0xB832;
	static constexpr int PsSetTextureColorOp_Inline_Size = 29;
	static constexpr int IntensityState_Addr = 0x49EDC8;
	static constexpr uint32_t Op_Modulate = 4;
	static constexpr uint32_t Op_Modulate2x = 5;

	inline static SafetyHookMid PsSetTextureColorOp_hook = {};
	static void PsSetTextureColorOp_dest(safetyhook::Context& ctx)
	{
		// __usercall: eax is the texture stage, edx the requested colour op.
		if (ctx.eax != 0 || !Settings::RestoreXboxBrightness)
			return;

		uint32_t* intensityState = Module::exe_ptr<uint32_t>(IntensityState_Addr);
		*intensityState = 0;

		if (ctx.edx != Op_Modulate)
			return;
		if (*Module::exe_ptr<uint32_t>(Modulate2xFlag_Addr) != 1)
			return;

		ctx.edx = Op_Modulate2x;
		*intensityState = 1;
	}

	// (3) Texture stage 0's MODULATE2X snippet is a copy of the plain MODULATE one
	// in both shader model tables, missing the shift that does the doubling. Stage 1
	// carries it in both. Bits 24 to 27 of a destination token hold the shift, where
	// 1 means _x2. Both tables need patching: a material landing on the untouched
	// one gets the halved light with nothing to double it back.
	static constexpr int Modulate2xShift_ps11_Addr = 0x21EB43;
	static constexpr int Modulate2xShift_ps14_Addr = 0x21EF97;

	// (4) vsSetLightIntensity uploads the halved diffuse and c16 only on the frame
	// the mode turns on, and vsSetDirctinalLight overwrites that same register with
	// the unhalved diffuse every frame after. Dropping the test re-uploads it per
	// material, which runs after the light setup rather than before it.
	static constexpr int IntensityLatch_Addr = 0x10D16;

public:
	std::string_view description() override
	{
		return "RestoreXboxBrightness";
	}

	// Never install the irreversible NOPs or per-material hooks when off.
	// This option changes executable shader code and requires a restart.
	bool validate() override
	{
		return Settings::RestoreXboxBrightness;
	}

	void declare_settings() override
	{
		Settings::RestoreXboxBrightness.needs_restart();
	}

	bool apply() override
	{
		Memory::VP::Patch(Module::exe_ptr<uint8_t>(Modulate2xShift_ps11_Addr), uint8_t(0x81));
		Memory::VP::Patch(Module::exe_ptr<uint8_t>(Modulate2xShift_ps14_Addr), uint8_t(0x81));

		Memory::VP::Nop(Module::exe_ptr(IntensityLatch_Addr), 6);
		Memory::VP::Nop(Module::exe_ptr(PsSetTextureColorOp_Inline_Addr),
			PsSetTextureColorOp_Inline_Size);

		SelectVertexShader_hook = safetyhook::create_mid(
			Module::exe_ptr(SelectVertexShader_IdBranch_Addr), SelectVertexShader_dest);
		PsSetTextureColorOp_hook = safetyhook::create_mid(
			Module::exe_ptr(PsSetTextureColorOp_Addr), PsSetTextureColorOp_dest);

		return SelectVertexShader_hook && PsSetTextureColorOp_hook;
	}

	static RestoreXboxBrightness instance;
};
RestoreXboxBrightness RestoreXboxBrightness::instance;

// Restores the console sky glow, which PC port mostly included but was disabled
// in the code due to various issues.
//
// The effect blooms pixels whose framebuffer alpha beats a per stage baseline,
// alpha being an HDR exposure of 0 to 4.0 rather than opacity. vsSetMaterial
// turns a material's intensity into that exposure, clamp(((intensity + 1) * 0.25)
// * glow_param[1] * 255), so an ordinary material at intensity 0 gives 63, and
// g_GlowParamTable sets the baseline to match.
//
// Five separate things had to be fixed for this to work properly, plus two
// more for quality:
class RestoreSkyGlow : public Hook
{
	static bool SkyGlowAllowed() noexcept
	{
		return Settings::SkyGlowFactor > 0 &&
			!(Settings::VREnabled && Settings::VRStereo);
	}

	// (1) The exposure reaches pixel shader constant c7 alpha, but nothing reads
	// it. Games pixel shaders are assembled by concatenating ps_1_1 snippets looked
	// up by combiner encoding, and entry for the HDR alpha op holds an empty snippet 
	// on PC, so alpha keeps whatever the texture stages left: opaque scenery writes 255 
	// where it should write 63 and the whole stage blooms.
	//
	// A key names an NV2A sum, (b3 * b2) + (b1 * b0), where 0x10 is zero, 0x30 one,
	// 0x14 v0, 0x18 to 0x1B t0 to t3, 0x1C r0, and 0x11 and 0x12 the stage's two
	// constants. SetHDRPostProcessCombiner picks by the draw's alpha reference:
	// 0x1C301010 below 0x80, which is r0 alone and so leaves alpha untouched, and
	// 0x10101230 at 0x80 and above, the second constant on its own. Only the second
	// is the exposure write, so only its entry is redirected and draws that keep
	// their own alpha are unaffected.
	//
	// Its key2 of 0x4C00 carries the one flag nibble set anywhere in either table,
	// AB_CD_MUX, making the result (r0.a >= 0.5) ? exposure : 0 rather than the
	// exposure everywhere. Multiplying by the alpha already in the register gives
	// the same two outcomes for a cutout mask in one instruction.
	static constexpr int AlphaOpTable_ps11_Entry0Snippet = 0x21F248;
	static constexpr int AlphaOpTable_ps14_Entry0Snippet = 0x21F2B8;

	// Alpha shader snippet for ps_1_1
	static inline const uint32_t Snippet_ps11[] = {
		0xFFFF0101, // not copied
		0x00000005, // mul
		0x80080000, // r0.a
		0x80FF0000, // r0.a
		0xA0FF0007, // c7.a
		0x0000FFFF, // end
	};
	// Alpha shader snippet for ps_1_4
	static inline const uint32_t Snippet_ps14[] = {
		0xFFFF0104,
		0x00000005,
		0x80080004, // r4.a
		0x80FF0004, // r4.a
		0xA0FF0007,
		0x0000FFFF,
	};

	// (2) InitRender leaves the alpha test on with D3DCMP_GREATEREQUAL and the
	// opaque class carries a reference of 128. That works while alpha holds texture
	// alpha, opaque texels being 255, but no exposure can reach it, so every opaque
	// draw would fail and vanish.
	//
	// Only the copy psSetPixelShader reasserts is lowered. The 128 in
	// SetDefaultAlphaState is also what SetHDRPostProcessCombiner tests to choose
	// the alpha op, and below 0x80 it installs the no-op, reverting the effect.
	// ApplyAlphaRenderState sets the device reference and picks the op from that
	// same value, then psSetPixelShader runs per material and leaves 1 for the draw.
	static constexpr int AlphaRefCompare_Imm = 0xB027;
	static constexpr int AlphaRefReassert_Imm = 0xB039;

	// (2b) The console uses one reference for every HDR draw, s_HdrState[4], left
	// at 1 by SetHDRPostProcessCombiner, which is what the immediates above now
	// hold. One value serves because its alpha op is a MUX: alpha comes out as the
	// material's exposure or as 0, so 1 always cuts at half texture alpha.
	//
	// The mul standing in for that MUX writes tex_alpha * exposure, a ramp, so 1
	// would cut at almost nothing and every soft alpha edge would draw the fringe
	// it used to clip. Half the exposure puts the cut back where the MUX had it,
	// so a draw carrying the op has its reference set per draw instead.
	static constexpr int PsSetPixelShader_Addr = 0xAF80;
	static constexpr int HdrState_Addr = 0x49BC04;
	static constexpr int ReqPresetPs_Addr = 0x49BC20;
	static constexpr int VsSetMaterial_Exposure_Addr = 0x10F4F;

	// (2c) byte_95AEF4 is bit 8 of a material's first texture attribute, set per
	// material by SetMaterialStructure to mark one that needs its real alpha.
	// psSetPixelShader passes it to ConstructPixelShaderProgram, which then skips
	// stage 4 and emits no exposure op, and picks s_HdrState[1] over [2] for
	// D3DRS_COLORWRITEENABLE, the same mask with the alpha bit cleared. Neither is
	// in the Xbox build, which calls its shader builder with no argument at all
	// and always uses the mask with alpha.
	//
	// The guard covers a case that cannot arise. It stops a blended draw having
	// its alpha replaced by an exposure the blender would then use as srcA, but a
	// blended draw is alpha class 1, and SetHDRPostProcessCombiner gives an HDR
	// enable of 0 the no-op alpha op regardless. Only class 0 carries the exposure
	// op, and class 0 has blending off.
	//
	// What it costs is every material with alpha in its texture, cutouts as well
	// as blends. A hatched road verge is a cutout, so it writes no exposure and
	// shows whatever is behind it, which against sky is the sky's own exposure.
	static constexpr int MaterialKeepsAlpha_Addr = 0x8F56;


	// ConstructPixelShaderProgram's output: the per entry alpha op keys, their
	// second words, and the entry count in the low nibble of the last.
	static constexpr int PsdAlphaOp_Addr = 0x49BC28;
	static constexpr int PsdAlphaOp2_Addr = 0x49BC9C;
	static constexpr int PsdCount_Addr = 0x49BD14;
	static constexpr uint32_t MaxCombinerEntries = 9;

	// The combiner encoding whose table entry is redirected above, so finding it
	// among the emitted entries is what says this shader writes the exposure.
	static constexpr uint32_t ExposureAlphaOp = 0x10101230;
	static constexpr uint32_t ExposureAlphaOp2 = 0x4C00;

	// The exposure op only reaches a shader if ConstructPixelShaderProgram emitted
	// stage 4 carrying it, and three separate things stop that. byte_95AEF4, bit 8
	// of the material's first texture attribute, makes it skip stage 4 outright,
	// which is how a material keeps real alpha for blending. A reference below
	// 0x80 makes SetHDRPostProcessCombiner put the no-op op there instead. And a
	// material whose earlier stages fill all nine entries never reaches stage 4 at
	// all. The emitted list is the one place all three show up, and is what
	// BuildPixelShaderFromCombiners_mb keys its own snippet lookup on.
	static bool ShaderWritesExposure()
	{
		const uint32_t count = *Module::exe_ptr<uint32_t>(PsdCount_Addr) & 0xF;
		const uint32_t* alphaOp = Module::exe_ptr<uint32_t>(PsdAlphaOp_Addr);
		const uint32_t* alphaOp2 = Module::exe_ptr<uint32_t>(PsdAlphaOp2_Addr);

		for (uint32_t i = 0; i < count && i < MaxCombinerEntries; i++)
		{
			if (alphaOp[i] == ExposureAlphaOp && alphaOp2[i] == ExposureAlphaOp2)
				return true;
		}

		return false;
	}

	// The exposure varies per material, so the reference has to follow it rather
	// than sit at a constant. The console alpha op was a MUX, (r0.a >= 0.5) ?
	// exposure : 0, which cut at half alpha whatever the reference was, since
	// everything below the threshold came out at zero. The mul that stands in for
	// it writes tex_alpha * exposure, a ramp rather than a step, so the cut lands
	// wherever reference over exposure falls instead.
	inline static uint32_t MaterialExposure = 1;

	inline static SafetyHookMid Exposure_hook = {};
	static void Exposure_dest(safetyhook::Context& ctx)
	{
		// __ftol2 has just returned it; the game clamps over the next few
		// instructions, with unsigned compares, so a negative conversion lands
		// at 255 rather than 1.
		uint32_t exposure = ctx.eax;
		if (exposure < 1)
			exposure = 1;
		if (exposure > 255)
			exposure = 255;

		MaterialExposure = exposure;
	}

	inline static SafetyHookInline PsSetPixelShader_hook = {};
	static int __stdcall PsSetPixelShader_dest()
	{
		const int result = PsSetPixelShader_hook.stdcall<int>();

		// A preset shader is not built from the combiner tables, so st_psd does not
		// describe it and the patched immediate never applied to it either. The
		// game gives it s_HdrState[3], 8 for the blended class, and overriding
		// that would drop everything below half alpha.
		if (*Module::exe_ptr<uint32_t>(ReqPresetPs_Addr) != 0)
			return result;

		// Zero means the game left the reference alone, so nothing here should
		// touch it either.
		if (*Module::exe_ptr<uint32_t>(HdrState_Addr) == 0)
			return result;

		// A shader without the op keeps the reference the game left it, which the
		// immediates above have already put where the console holds it.
		if (!ShaderWritesExposure())
			return result;

		// Half the exposure, putting the cut where the console's MUX had it.
		DWORD alphaRef = MaterialExposure / 2;
		if (alphaRef < 1)
			alphaRef = 1;

		if (IDirect3DDevice9* device = Game::D3DDevice())
			device->SetRenderState(D3DRS_ALPHAREF, alphaRef);

		return result;
	}

	// (3) D3D9 blends alpha with the colour factors, so the sky's exposure lands as
	// srcA*srcA + dstA*(1 - srcA) instead of srcA.
	//
	// Seeding the frame clear colour with that exposure, E = 0.25 * glow_param[0], 
	// makes that E*E + E*(1 - E), which is E, the blend's fixed point, so it comes 
	// out with right value without needing to override blend modes.
	//
	// Consoles seem to reach E by never clearing alpha and letting it settle across
	// frames, which the DISCARD swap chain used on PC can't do. E also suits pixels 
	// no sky covers: Sky_Disp draws with depth off and transparent scenery writes RGB 
	// only, so on Alaska, which has no skyId0 and shows black, a 0 clear would previously
	// leave a hard edge on surfaces that intersect empty sky parts.
	static constexpr int ClearBuffer_Addr = 0xEC70;
	static constexpr int BackColor_Addr = 0x49BD5C;
	static constexpr int GlowParam0_Addr = 0x4A8C18;

	// (4b) InitFilter tests g_GlowEnabled once at game_init around the whole of the
	// one time setup: the pixel shaders, and scaling vtx_glow2glow_base by
	// g_ScreenMultiplyX and Y. Nothing repeats either, so booting with the effect
	// off left the composite quad at its authored 640x480 and switching it on later
	// drew the glow into that corner with no shaders bound.
	//
	// Dropping the test runs the setup either way, leaving the flag to SceneControl
	// as the per frame switch. D3D_GlowInit_mb tests it itself, so the render
	// targets are still only allocated once the effect is on.
	static constexpr int InitFilter_EnabledCheck_Addr = 0x14CE7;

	// (4) Flag for enabling the glow effect - always set to 0 on PC.
	// (the launcher exe did include a setting for the glow that was hidden, devs
	// likely intended to add an option for it, but guess they ran out of time
	// to implement it fully - to be fair it took us over 2 years to fix too :P)
	static constexpr int GlowEnabled_Addr = 0x55AF09;

	// Addresses for glow texture sizes
	static constexpr int GlowInit_Addr = 0x14C00;
	static constexpr int GlowInit_WidthImm[] = { 0x14C22, 0x14C45, 0x14C69 };
	static constexpr int GlowInit_HeightImm[] = { 0x14C1D, 0x14C40, 0x14C64 };

	// Extract and blur passes both draw a quad spanning 0,0 to the target size,
	// so also have to be updated with the proper texture size.
	static constexpr int ExtractQuad_XY[] = { 0x2236CC, 0x2236EC, 0x223704, 0x223708 };
	static constexpr int BlurQuad_XY[] = { 0x223754, 0x22378C, 0x2237BC, 0x2237C0 };

	// (5) MakeReduceBuff copies the back buffer into the glow buffer with a single
	// StretchRect. Bilinear samples 2x2, so reducing by 4x reads only four of every
	// sixteen pixels, and building edges alias and crawl. Two 2x steps sample all of
	// them, bilinear being an exact box filter at exactly half, and the extra
	// averaging adds the softness the small buffer is meant to provide. Only worth
	// doing when the reduction is more than 2x.
	static constexpr int MakeReduceBuff_Addr = 0x14E50;
	static constexpr int GlowRelease_Addr = 0x14C80;
	static constexpr int RenderCfgGlow_Addr = 0x39FCD5; // tested as (x & 3) == 2
	static constexpr int Step1Tex_Addr = 0x4A8C14;
	static constexpr int LatestTex_Addr = 0x4A8C08;
	static constexpr int GlowAmount_Addr = 0x4A8C40; // glow_param.amount_28

	inline static IDirect3DTexture9* ReduceHalf = nullptr;

	inline static SafetyHookInline MakeReduceBuff_hook = {};
	static void __stdcall MakeReduceBuff_dest()
	{
		// True stereo owns two independent eye images. The stock glow reducer
		// samples D3DBACKBUFFER_TYPE_MONO, which is the left/game backbuffer in
		// the VR renderer; letting this run would bake left-eye scenery into a
		// texture that is later composited into both eyes.
		if (!SkyGlowAllowed())
			return;

		// Checked here rather than in apply so the setting can be changed while the
		// game runs.
		if (!Settings::SkyGlowTwoStep || !ReduceHalf)
		{
			MakeReduceBuff_hook.stdcall();
			return;
		}

		// The conditions the original reduces under.
		if ((*Module::exe_ptr<uint8_t>(RenderCfgGlow_Addr) & 3) != 2)
			return;
		if (*Module::exe_ptr<int>(GlowAmount_Addr) == 0)
			return;

		IDirect3DDevice9* device = Game::D3DDevice();
		IDirect3DTexture9* step1 = *Module::exe_ptr<IDirect3DTexture9*>(Step1Tex_Addr);
		if (!device || !step1)
			return;

		IDirect3DSurface9* back = nullptr;
		IDirect3DSurface9* half = nullptr;
		IDirect3DSurface9* target = nullptr;

		if (SUCCEEDED(device->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &back))
			&& SUCCEEDED(ReduceHalf->GetSurfaceLevel(0, &half))
			&& SUCCEEDED(step1->GetSurfaceLevel(0, &target)))
		{
			device->StretchRect(back, nullptr, half, nullptr, D3DTEXF_LINEAR);
			device->StretchRect(half, nullptr, target, nullptr, D3DTEXF_LINEAR);

			*Module::exe_ptr<IDirect3DTexture9*>(LatestTex_Addr) = step1;
		}

		if (target)
			target->Release();
		if (half)
			half->Release();
		if (back)
			back->Release();
	}

	// The intermediate is D3DPOOL_DEFAULT, so it has to be gone before a device
	// reset. D3D_GlowRelease_mb is where the game drops its own glow targets.
	inline static SafetyHookInline GlowRelease_hook = {};
	static void __stdcall GlowRelease_dest()
	{
		if (ReduceHalf)
		{
			ReduceHalf->Release();
			ReduceHalf = nullptr;
		}

		GlowRelease_hook.stdcall();
	}

	// (6) BlurGlowImage offsets its taps by `glow_param[11] / screen width` in texture
	// coordinates, growing by glow_param[12] each pass. Dividing by the live width
	// pins the blur to a fixed count of screen pixels, which covered most of the
	// picture at 640 across and is almost nothing at 3840: the offset stays 0.1
	// buffer texels either way, but the buffer is six times wider so the blur spans
	// six times less of the image, and four taps inside one texel leave bilinear
	// nothing to average.
	// Scaling both by width / 640 holds the texture coordinate offset constant, the 
	// proportion the console blurred at.
	static constexpr int BlurGlowImage_Addr = 0x15630;
	static constexpr int BlurOffset_Addr = 0x4A8C44;     // glow_param[11]
	static constexpr int BlurOffsetStep_Addr = 0x4A8C48; // glow_param[12]

	inline static SafetyHookInline BlurGlowImage_hook = {};
	static void __stdcall BlurGlowImage_dest()
	{
		// Keep the whole post-process chain inert while true stereo is active.
		// This is a second fail-safe behind g_GlowEnabled for paths that can be
		// entered from cached game state during a mode transition.
		if (!SkyGlowAllowed())
			return;

		float* offset = Module::exe_ptr<float>(BlurOffset_Addr);
		float* step = Module::exe_ptr<float>(BlurOffsetStep_Addr);

		const float scale = Game::screen_resolution->x / Game::original_resolution.x;
		const float prevOffset = *offset;
		const float prevStep = *step;

		*offset = prevOffset * scale;
		*step = prevStep * scale;

		{
			OutRunVR::GameSemantic::ScopedRenderSemantic semantic(
				OutRunVR::GameSemantic::RenderScope::SkyGlow);
			BlurGlowImage_hook.stdcall();
		}

		*offset = prevOffset;
		*step = prevStep;
	}

	inline static SafetyHookInline GlowInit_hook = {};
	static void __stdcall GlowInit_dest()
	{
		// The setup runs even with SkyGlowFactor switched off, so the divisor 
		// is floored at 1 rather than taken from a setting that can be 0.
		const int factor = max(1, Settings::SkyGlowFactor.get());

		// Sized here rather than in apply because the render resolution is only
		// known once the game has read its config.
		int w = int(Game::screen_resolution->x) / factor;
		int h = int(Game::screen_resolution->y) / factor;

		// Floor at the size the console ran, so a small window still leaves the blur
		// room to work in.
		if (w < 160)
			w = 160;
		if (h < 120)
			h = 120;

		for (int addr : GlowInit_WidthImm)
			Memory::VP::Patch(Module::exe_ptr<uint32_t>(addr), uint32_t(w));
		for (int addr : GlowInit_HeightImm)
			Memory::VP::Patch(Module::exe_ptr<uint32_t>(addr), uint32_t(h));

		for (const int* quad : { ExtractQuad_XY, BlurQuad_XY })
		{
			Memory::VP::Patch(Module::exe_ptr<float>(quad[0]), float(w));
			Memory::VP::Patch(Module::exe_ptr<float>(quad[1]), float(h));
			Memory::VP::Patch(Module::exe_ptr<float>(quad[2]), float(w));
			Memory::VP::Patch(Module::exe_ptr<float>(quad[3]), float(h));
		}

		spdlog::info("RestoreSkyGlow: glow buffers sized {}x{}", w, h);

		// True-stereo VR owns its own per-eye R30 glow chain. Do not allocate
		// the game's mono glow render targets here: besides wasting a large
		// buffer at 4K, that chain can only sample D3DBACKBUFFER_TYPE_MONO and
		// would later leak left-eye content into the right eye.
		if (Settings::VREnabled && Settings::VRStereo)
		{
			if (ReduceHalf)
			{
				ReduceHalf->Release();
				ReduceHalf = nullptr;
			}
			spdlog::info(
				"RestoreSkyGlow: stock mono buffers skipped in true-stereo VR; R30 owns independent eye buffers factor={}",
				Settings::SkyGlowFactor.get());
			return;
		}

		GlowInit_hook.stdcall();

		// Halfway stage for the reduce, so neither StretchRect does more than a 2x.
		// This runs again after a device reset, so drop any previous one first.
		if (ReduceHalf)
		{
			ReduceHalf->Release();
			ReduceHalf = nullptr;
		}

		if (SkyGlowAllowed() && Settings::SkyGlowFactor > 2)
		{
			if (IDirect3DDevice9* device = Game::D3DDevice())
			{
				uint32_t halfW = uint32_t(Game::screen_resolution->x) / 2;
				uint32_t halfH = uint32_t(Game::screen_resolution->y) / 2;

				if (FAILED(device->CreateTexture(halfW, halfH, 1, D3DUSAGE_RENDERTARGET,
					D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &ReduceHalf, nullptr)))
				{
					ReduceHalf = nullptr;
					spdlog::warn("RestoreSkyGlow: reduce intermediate failed, glow will alias at edges");
				}
			}
		}
	}

	inline static SafetyHookInline ClearBuffer_hook = {};
	static int __cdecl ClearBuffer_dest(int a1)
	{
		// When glow is disabled (including true-stereo VR), preserve the game's
		// original clear alpha exactly. The exposure seed only exists to feed the
		// mono sky-glow extraction pass.
		if (!SkyGlowAllowed())
			return ClearBuffer_hook.ccall<int>(a1);

		uint32_t* backColor = Module::exe_ptr<uint32_t>(BackColor_Addr);
		const uint32_t prevColor = *backColor;

		if (Game::is_in_game() || *Game::current_mode == GameState::STATE_GAMEOVER)
		{
			float exposure = 0.25f * *Module::exe_ptr<float>(GlowParam0_Addr);

			int alpha = int(exposure * 255.0f);
			if (alpha < 0)
				alpha = 0;
			if (alpha > 255)
				alpha = 255;

			*backColor = (prevColor & 0x00FFFFFF) | (uint32_t(alpha) << 24);
		}

		int result = ClearBuffer_hook.ccall<int>(a1);

		// Only the clear needs the exposure in there; leaving it set changes what
		// every later clear starts from, including the menus after a race.
		*backColor = prevColor;

		return result;
	}

public:
	std::string_view description() override
	{
		return "RestoreSkyGlow";
	}

	void declare_settings() override
	{
		// The buffers are sized from the factor, so a change has to resize them.
		// SkyGlowTwoStep is read inside MakeReduceBuff on every call, so nothing
		// needs declaring for it at all.
		Settings::SkyGlowFactor.watch([] { RebuildGlowBuffers(); });
		Settings::VREnabled.watch([] { RebuildGlowBuffers(); });
		Settings::VRStereo.watch([] { RebuildGlowBuffers(); });
	}

	bool apply() override
	{
		// Note: hooks/patches are always applied regardless of INI settings, so they can be changed at runtime
		Memory::VP::Patch(Module::exe_ptr<uint8_t>(GlowEnabled_Addr), uint8_t(SkyGlowAllowed() ? 1 : 0));
		if (Settings::SkyGlowFactor > 0 && !SkyGlowAllowed())
			spdlog::info("VR SKY GLOW: stock mono-backbuffer chain disabled; stereo renderer owns independent left/right glow extraction and blur");

		Memory::VP::Patch(Module::exe_ptr(AlphaOpTable_ps11_Entry0Snippet), uintptr_t(Snippet_ps11));
		Memory::VP::Patch(Module::exe_ptr(AlphaOpTable_ps14_Entry0Snippet), uintptr_t(Snippet_ps14));

		for (int addr : { AlphaRefCompare_Imm, AlphaRefReassert_Imm })
			Memory::VP::Patch(Module::exe_ptr<uint32_t>(addr), uint32_t(1));

		Memory::VP::Patch(Module::exe_ptr(MaterialKeepsAlpha_Addr), { 0x30, 0xC0 }); // and al, 1 -> xor al, al

		// jz over the one time setup, six bytes.
		Memory::VP::Nop(Module::exe_ptr(InitFilter_EnabledCheck_Addr), 6);

		GlowInit_hook = safetyhook::create_inline(Module::exe_ptr(GlowInit_Addr), GlowInit_dest);
		ClearBuffer_hook = safetyhook::create_inline(Module::exe_ptr(ClearBuffer_Addr), ClearBuffer_dest);
		MakeReduceBuff_hook = safetyhook::create_inline(Module::exe_ptr(MakeReduceBuff_Addr), MakeReduceBuff_dest);
		GlowRelease_hook = safetyhook::create_inline(Module::exe_ptr(GlowRelease_Addr), GlowRelease_dest);
		BlurGlowImage_hook = safetyhook::create_inline(Module::exe_ptr(BlurGlowImage_Addr), BlurGlowImage_dest);
		PsSetPixelShader_hook = safetyhook::create_inline(Module::exe_ptr(PsSetPixelShader_Addr), PsSetPixelShader_dest);

		if (!GlowInit_hook || !ClearBuffer_hook || !MakeReduceBuff_hook
			|| !GlowRelease_hook || !BlurGlowImage_hook || !PsSetPixelShader_hook)
			return false;

		// Mid hook rather than inline: vsSetMaterial is __usercall, and the
		// exposure only exists in a register partway through it.
		Exposure_hook = safetyhook::create_mid(Module::exe_ptr(VsSetMaterial_Exposure_Addr), Exposure_dest);

		// Read inside MakeReduceBuff on every call, so nothing to re-do.

		// The buffers are sized from the factor, so a change has to resize them.
		return true;
	}

	// Resizing the glow buffers means tearing down what the old size allocated.
	static void RebuildGlowBuffers()
	{
		// declare_settings runs whether or not the hooks installed, so a change
		// can reach here after apply gave up. The release path calls through
		// these, which would be a jump into nothing.
		if (!GlowInit_hook || !GlowRelease_hook)
			return;

		// Release before patching the enabled byte, so it frees resources if needed
		GlowRelease_dest();
		Memory::VP::Patch(Module::exe_ptr<uint8_t>(GlowEnabled_Addr), uint8_t(SkyGlowAllowed() ? 1 : 0));
		GlowInit_dest();
	}

	static RestoreSkyGlow instance;
};
RestoreSkyGlow RestoreSkyGlow::instance;

class ReflectionResolution : public Hook
{
	inline static std::array<int, 6> ReflectionResolution_Addrs = 
	{
		// Envmap_Init
		0x13B50 + 1,
		0x13BA1 + 1,
		0x13BA6 + 1,
		// D3D_CreateTemporaries
		0x17A69 + 1,
		0x17A88 + 1,
		0x17A8D + 1,
	};

public:
	std::string_view description() override
	{
		return "ReflectionResolution";
	}

	bool validate() override
	{
		return Settings::ReflectionResolution >= 2;
	}

	void declare_settings() override
	{
		Settings::ReflectionResolution.needs_restart();
	}

	bool apply() override
	{
		for (const int& addr : ReflectionResolution_Addrs)
		{
			Memory::VP::Patch(Module::exe_ptr<int>(addr), Settings::ReflectionResolution.get());
		}
		return true;
	}

	static ReflectionResolution instance;
};
ReflectionResolution ReflectionResolution::instance;

// Envmap_RenderToCubeMap redraws part of the car reflection cubemap each frame, picking
// up from the face the previous frame stopped on, so the count it works out is faces for
// this frame rather than an update rate. Vanilla asks for 3 of the 6 faces, completing a
// cubemap every second frame, which was 30 of them a second at the games 60FPS lock.
class ReflectionUpdateRate : public Hook
{
	const static int Envmap_FaceCount_Addr = 0x1447E;

	static constexpr int FacesPerCubemap = 6;

	inline static SafetyHookMid FaceCount_midhook = {};

	static void FaceCount_dest(SafetyHookContext& ctx)
	{
		// Carried between frames so a share that doesn't come to a whole number of
		// faces still averages out. In VR, render cadence can be 72/80/90/120 Hz;
		// normalize the work to elapsed time so 0.5 keeps the original 60 Hz
		// budget (3 faces/frame * 60) instead of scaling GPU cost with HMD Hz.
		static float pendingFaces = 0.0f;
		static LARGE_INTEGER lastCounter{};
		static LARGE_INTEGER frequency{};
		static OutRunVR::ReflectionFrameBudget::AdaptiveFrameCadence frameCadence{};

		float frameScale60 = 1.0f;
		bool frameSpike = false;
		if (Settings::VREnabled && Settings::VRNormalizeReflectionRate)
		{
			if (frequency.QuadPart <= 0)
				QueryPerformanceFrequency(&frequency);
			LARGE_INTEGER now{};
			QueryPerformanceCounter(&now);
			if (lastCounter.QuadPart > 0 && frequency.QuadPart > 0 &&
				now.QuadPart >= lastCounter.QuadPart)
			{
				const double dt = static_cast<double>(now.QuadPart - lastCounter.QuadPart) /
					static_cast<double>(frequency.QuadPart);
				// Avoid a long pause/load screen producing a one-frame cubemap spike.
				// At 120 Hz an over-budget frame can still be well below 18 ms.
				// Use the observed healthy headset cadence as an additional
				// late-frame criterion; preserve the old >18-ms protection.
				frameSpike = frameCadence.Observe(dt);
				frameScale60 = frameSpike ? 0.5f :
					static_cast<float>(std::clamp(dt * 60.0, 0.0, 1.0));
			}
			lastCounter = now;
		}
		else
		{
			lastCounter = {};
			frameCadence.Reset();
		}

		// Quest-inspired bounded render work: one deterministic budget
		// preserves original 60 Hz reflection quality while preventing XR
		// frame misses from triggering a large deferred cubemap redraw.
		const auto budget = OutRunVR::ReflectionFrameBudget::Advance(
			pendingFaces, Settings::ReflectionUpdateRate.get(), frameScale60,
			Settings::VREnabled && Settings::VRNormalizeReflectionRate,
			frameSpike);
		pendingFaces = budget.pendingFaces;
		ctx.eax = budget.faces;
	}

public:
	std::string_view description() override
	{
		return "ReflectionUpdateRate";
	}

	bool apply() override
	{
		Memory::VP::Nop(Module::exe_ptr<uint8_t>(Envmap_FaceCount_Addr), 7);
		FaceCount_midhook = safetyhook::create_mid(Module::exe_ptr(Envmap_FaceCount_Addr), FaceCount_dest);

		return true;
	}

	static ReflectionUpdateRate instance;
};
ReflectionUpdateRate ReflectionUpdateRate::instance;

class DisableDPIScaling : public Hook
{
public:
	std::string_view description() override
	{
		return "DisableDPIScaling";
	}

	bool validate() override
	{
		return Settings::DisableDPIScaling;
	}

	void declare_settings() override
	{
		Settings::DisableDPIScaling.needs_restart();
	}

	bool apply() override
	{
		SetProcessDPIAware();
		return true;
	}

	static DisableDPIScaling instance;
};
DisableDPIScaling DisableDPIScaling::instance;

class ScreenEdgeCullFix : public Hook
{
	const static int CalcBall3D2D_Addr = 0x49E70;

	// Hook CalcBall3D2D to rescale screen-ratio positions back to 4:3 positions that game code expects
	// (fixes objects like cones being culled out before they reach edge of the screen)
	inline static SafetyHookInline dest_orig = {};
	static float __cdecl destination(float a1, Sphere* a2, Sphere* a3)
	{
		float ret = dest_orig.ccall<float>(a1, a2, a3);

		if (!Settings::ScreenEdgeCullFix || !a3 || !Game::screen_resolution)
			return ret;

		// CalcBall3D2D already wrote the game's culling sphere. During
		// VR eye-extent changes, device Reset and minimize the original
		// source viewport can transiently be zero/invalid. Correct both
		// coordinates only after a complete finite 4:3 projection succeeds;
		// otherwise keep the original game's sphere and return value intact.
		const auto mapped = OutRunVrStageCull::CorrectBallProjection(
			a3->f0, a3->f1,
			Game::screen_resolution->x, Game::screen_resolution->y);
		if (mapped.valid)
		{
			a3->f0 = mapped.x;
			a3->f1 = mapped.y;
		}
		return ret;
	}

public:
	std::string_view description() override
	{
		return "ScreenEdgeCullFix";
	}

	bool apply() override
	{
		dest_orig = safetyhook::create_inline(Module::exe_ptr(CalcBall3D2D_Addr), destination);
		return !!dest_orig;
	}

	static ScreenEdgeCullFix instance;
};
ScreenEdgeCullFix ScreenEdgeCullFix::instance;

// VR PMT culling is intentionally attached to the *original visibility
// function's call boundary*, not to the render projection/WVP upload.
// Changing the live projection for an entire BeginScene caused previous visual
// regressions: world rendering and effects inherited a culling-only matrix.
//
// PMT walk:
//   EXE+0x5015 CALL render_node_visible_404b00
//   EXE+0x501D TEST EAX,EAX / JE ...
// Keep the original EAX answer for the VR-wide case, and override it only for
// explicit disable/fail-open. Both hooks are on the same rendering thread.
class DisableStageCulling : public Hook
{
    inline static SafetyHookMid before_visible_hook{};
    inline static SafetyHookMid result_gate_hook{};
    inline static bool signature_mismatch_logged = false;
    inline static bool projection_writable = false;
    inline static std::uint64_t scoped_calls = 0;
    inline static std::uint64_t fail_open_calls = 0;
    inline static std::uint64_t first_deferred_report = 0;

    // Canonical OutRun.exe + 0x55D8A0 = game's 0x0095D8A0 projection matrix.
    // Only a scoped CPU PMT visibility invocation ever sees the widened copy.
    static constexpr std::uintptr_t ProjectionRva = 0x0055D8A0u;

    struct SavedProjection
    {
        D3DMATRIX* target = nullptr;
        D3DMATRIX original{};
        bool active = false;
    };
    inline static thread_local SavedProjection saved{};

    static bool VrGameplay() noexcept
    {
        return Settings::VREnabled.get() && Game::current_mode &&
            (*Game::current_mode == GameState::STATE_GAME ||
             *Game::current_mode == GameState::STATE_SMPAUSEMENU) &&
            OutRunVR::RuntimeEligibility::MayInjectStereo();
    }

    static bool ValidateProjectionAddress() noexcept
    {
        D3DMATRIX* p = Module::exe_ptr<D3DMATRIX>(ProjectionRva);
        MEMORY_BASIC_INFORMATION mbi{};
        if (!p || !VirtualQuery(p, &mbi, sizeof(mbi)) ||
            mbi.State != MEM_COMMIT)
            return false;
        const DWORD access = mbi.Protect & 0xFFu;
        if (access != PAGE_READWRITE && access != PAGE_WRITECOPY &&
            access != PAGE_EXECUTE_READWRITE &&
            access != PAGE_EXECUTE_WRITECOPY)
            return false;
        const auto begin = reinterpret_cast<std::uintptr_t>(p);
        const auto regionEnd =
            reinterpret_cast<std::uintptr_t>(mbi.BaseAddress) + mbi.RegionSize;
        return begin <= regionEnd && regionEnd - begin >= sizeof(D3DMATRIX);
    }

    static bool GetWideFov(float& tanHorizontal, float& tanVertical) noexcept
    {
        const auto* frame = OutRunVRRenderer::GetLatchedStereoFrameView();
        if (!frame || !frame->valid || frame->poseSequence == 0)
            return false;
        const float margin = std::clamp(
            Settings::VRCullingUnionMarginDegrees.get(), 0.0f, 15.0f) *
            0.01745329251994329577f;
        float h = 0.0f, v = 0.0f;
        for (int eye = 0; eye < 2; ++eye)
        {
            const auto& fov = frame->eyeFov[eye];
            const float angles[4] = {
                fov.angleLeft, fov.angleRight, fov.angleDown, fov.angleUp
            };
            for (float angle : angles)
                if (!std::isfinite(angle) || std::abs(angle) >= 1.56f)
                    return false;
            if (!(fov.angleLeft < fov.angleRight) ||
                !(fov.angleDown < fov.angleUp))
                return false;
            h = (std::max)(h, (std::max)(std::abs(fov.angleLeft),
                std::abs(fov.angleRight)));
            v = (std::max)(v, (std::max)(std::abs(fov.angleDown),
                std::abs(fov.angleUp)));
        }
        // Symmetric enclosure of both OpenXR asymmetric eye frusta.
        // Conservative when either eye differs; never shrink original FOV.
        h = (std::min)(1.48f, h + margin);
        v = (std::min)(1.48f, v + margin);
        tanHorizontal = std::tan(h);
        tanVertical = std::tan(v);
        return std::isfinite(tanHorizontal) && tanHorizontal > 0.0f &&
            std::isfinite(tanVertical) && tanVertical > 0.0f;
    }

    static void RestoreScopedProjection() noexcept
    {
        if (!saved.active)
            return;
        if (saved.target)
            std::memcpy(saved.target, &saved.original, sizeof(D3DMATRIX));
        saved = {};
    }

    static void BeforeVisible(safetyhook::Context&) noexcept
    {
        // The companion after-call hook always restores the CPU matrix, even
        // when the original game decides this PMT node is invisible.
        RestoreScopedProjection();
        if (!projection_writable || !VrGameplay() ||
            Settings::VRStageCullingMode.get() != 1)
            return;

        float tanH = 0.0f, tanV = 0.0f;
        if (!GetWideFov(tanH, tanV))
            return;
        auto* projection = Module::exe_ptr<D3DMATRIX>(ProjectionRva);
        if (!projection)
            return;
        D3DMATRIX original{};
        std::memcpy(&original, projection, sizeof(original));
        if (!std::isfinite(original._11) || !std::isfinite(original._22) ||
            !std::isfinite(original._34) || !std::isfinite(original._44) ||
            original._11 <= 0.0f || original._22 <= 0.0f ||
            std::abs(original._34) < 0.5f || std::abs(original._44) > 0.5f)
            return; // Not a perspective-world source: never alter it.

        // D3D9 right-handed projection. A culling-only symmetric enclosure
        // lets the game keep its own visibility algorithm and node transforms.
        const float newX = (std::min)(original._11, 1.0f / tanH);
        const float newY = (std::min)(original._22, 1.0f / tanV);
        if (!std::isfinite(newX) || !std::isfinite(newY) ||
            newX <= 0.0f || newY <= 0.0f)
            return;
        saved.target = projection;
        saved.original = original;
        saved.active = true;
        projection->_11 = newX;
        projection->_22 = newY;
        projection->_31 = 0.0f;
        projection->_32 = 0.0f;
        ++scoped_calls;
    }

    static void AfterVisible(safetyhook::Context& ctx) noexcept
    {
        const bool scoped = saved.active;
        RestoreScopedProjection();

        const bool vr = VrGameplay();
        const int mode = Settings::VRStageCullingMode.get();
        if (vr && mode == 2)
        {
            ctx.eax = 1u; // TEST EAX,EAX now falls through
            return;
        }
        if (vr && mode == 1)
        {
            // A missing/invalid pose or unsafe projection must never delete
            // scenery in a VR frame. This costs perf only until VR is ready.
            if (!scoped)
            {
                ++fail_open_calls;
                ctx.eax = 1u;
            }
        }
        else if (Settings::DisableStageCulling.get())
        {
            // Original Graphics toggle remains authoritative for legacy and
            // desktop modes without patching code bytes under a live detour.
            ctx.eax = 1u;
        }

        if ((scoped_calls + fail_open_calls) != 0 &&
            ((scoped_calls + fail_open_calls) & 0xFFFFFu) == 0 &&
            first_deferred_report != scoped_calls + fail_open_calls)
        {
            first_deferred_report = scoped_calls + fail_open_calls;
            spdlog::info(
                "VR PMT CULL: scopedWide={} failOpen={} mode={} marginDeg={:.1f}; HMD coverage untested",
                scoped_calls, fail_open_calls, mode,
                Settings::VRCullingUnionMarginDegrees.get());
        }
    }

public:
    std::string_view description() override
    {
        return "DisableStageCulling";
    }

    bool apply() override
    {
        // Relocated TEST/JE must be stock before the mid-hook is installed.
        auto* gate = Module::exe_ptr<std::uint8_t>(
            OutRunVR::PmtNodeCull::ResultTestRva);
        if (!OutRunVR::PmtNodeCull::ResultGateBytesCompatible(
                gate, OutRunVR::PmtNodeCull::OriginalResultGate.size()))
        {
            if (!signature_mismatch_logged)
            {
                signature_mismatch_logged = true;
                spdlog::error(
                    "VR PMT CULL: signature mismatch at 0x{:X}, refusing hooks",
                    static_cast<unsigned>(OutRunVR::PmtNodeCull::ResultTestRva));
            }
            return false;
        }
        const auto* call = Module::exe_ptr<std::uint8_t>(
            OutRunVR::PmtNodeCull::WalkNodeVisibleCallRva);
        if (!call || *call != 0xE8u)
        {
            spdlog::error("VR PMT CULL: expected direct CALL absent at 0x5015");
            return false;
        }

        projection_writable = ValidateProjectionAddress();
        // Install the after-call restore FIRST. If the pre-call hook fails,
        // no source matrix is ever changed.
        result_gate_hook = safetyhook::create_mid(
            Module::exe_ptr(OutRunVR::PmtNodeCull::ResultTestRva),
            AfterVisible);
        if (!result_gate_hook)
            return false;
        before_visible_hook = safetyhook::create_mid(
            Module::exe_ptr(OutRunVR::PmtNodeCull::WalkNodeVisibleCallRva),
            BeforeVisible);
        if (!before_visible_hook)
        {
            result_gate_hook = {};
            return false;
        }
        spdlog::info(
            "VR PMT CULL: native result-gate modes installed; projectionWritable={} (wide FOV scoped to call only)",
            projection_writable);
        return true;
    }

    static DisableStageCulling instance;
};
DisableStageCulling DisableStageCulling::instance;

class DisableVehicleLODs : public Hook
{
	const static int DispOthcar_PatchAddr = 0xAE4E9;
public:
	std::string_view description() override
	{
		return "DisableVehicleLODs";
	}

	void declare_settings() override
	{
		Settings::DisableVehicleLODs.watch([this] { apply(); });
	}

	bool apply() override
	{
		// Patch "eax = car.LodNumber" -> "eax = 0"
		static TogglePatch patch(Module::exe_ptr(DispOthcar_PatchAddr), { 0x90, 0x31, 0xC0 });
		patch.set(Settings::DisableVehicleLODs);

		return true;
	}

	static DisableVehicleLODs instance;
};
DisableVehicleLODs DisableVehicleLODs::instance;

class FixZBufferPrecision : public Hook
{
	const static int CalcCameraMatrix_Addr = 0x84BD0;
	const static int Clr_SceneEffect_Addr = 0xBE70;

	inline static SafetyHookInline CalcCameraMatrix = {};

	static inline bool allow_znear_override = true;

	static bool DriverSeatCameraActive(EvWorkCamera* camera)
	{
		return VRDriverSeatCameraEligible(camera);
	}

	static bool ApplyDriverSeatCameraOffset(EvWorkCamera* camera,
		D3DVECTOR& savedPos, D3DVECTOR& savedLook,
		bool driverSeatFrame)
	{
		if (!driverSeatFrame)
			return false;

		savedPos = camera->cam_pos_F8;
		savedLook = camera->look_pos_104;

		D3DVECTOR newPos{}, newLook{};
		if (!VRDriverSeatCameraPose(camera, newPos, newLook))
			return false;

		const float forward = Settings::VRDriverSeatForward.get();
		const float right = Settings::VRDriverSeatRight.get();
		const float up = Settings::VRDriverSeatUp.get();

		// One atomic valid camera pose for view-matrix generation. The
		// original game camera is restored by CalcCameraMatrix_dest.
		camera->cam_pos_F8 = newPos;
		camera->look_pos_104 = newLook;

		static float lastForward = 9999.0f, lastRight = 9999.0f, lastUp = 9999.0f;
		static int lastMode = -1;
		const int mode = static_cast<int>(camera->cam_mode_34A);
		if (mode != lastMode || std::fabs(forward - lastForward) > 0.0001f ||
			std::fabs(right - lastRight) > 0.0001f || std::fabs(up - lastUp) > 0.0001f)
		{
			lastMode = mode;
			lastForward = forward;
			lastRight = right;
			lastUp = up;
			spdlog::info(
				"VR DRIVER SEAT CAMERA: native mode={} forward={:.3f} right={:.3f} up={:.3f} applied before CalcCameraMatrix",
				mode, forward, right, up);
		}
		return true;
	}

	static void CalcCameraMatrix_dest(EvWorkCamera* camera)
	{
		// improve z-buffer precision by increasing znear
		// game default is 0.1 which reduces precision of far objects massively, causing z-fighting and objects not drawing properly

		// Snapshot camera eligibility once for near-plane and the native
		// view-matrix transaction. Repeated checks cost redundant camera
		// basis construction and can disagree during mode transitions.
		const bool driverSeatFrame = DriverSeatCameraActive(camera);
		if (allow_znear_override &&
			(Settings::FixZBufferPrecision || driverSeatFrame))
		{
			// In 6DoF VR the player can move their head through the normal third-
			// person near plane. Keep the 2D precision fix intact outside VR, but
			// use the dedicated VR near plane during gameplay/goal rendering.
			if (driverSeatFrame)
			{
				// Keep cockpit geometry within 15 cm even during stereo warmup.
				camera->perspective_znear_BC = std::clamp(
					OutRunVR::DriverSeatCamera::SafeNearPlane(
						Settings::VRNearPlane.get(), 0.05f, 0.15f),
					0.05f, 0.15f);
			}
			else if (Settings::VRPositionalTracking &&
				Settings::VRStereo &&
				OutRunVR::RuntimeEligibility::MayInjectStereo() &&
				VRDriverSeatGameplayActive())
			{
				camera->perspective_znear_BC =
						OutRunVR::DriverSeatCamera::SafeNearPlane(
							Settings::VRNearPlane.get(), 0.03f, 0.50f);
			}
			// only set znear to 1 if...
			else
			if ((camera->cam_mode_34A == 2 || camera->cam_mode_34A == 0) // ... in third-person or FPV
				&& camera->cam_mode_timer_364 == 0 // ... not switching cameras
				&& (*Game::current_mode == STATE_GAME || *Game::current_mode == STATE_GOAL)) // ... we're in main game state (not in STATE_START cutscene etc)
			{
				camera->perspective_znear_BC = 1.0f;
			}
			else
			{
				if (camera->cam_mode_timer_364 != 0 || *Game::current_mode != STATE_GAME)
					camera->perspective_znear_BC = 0.1f; // set znear to 0.1 during camera switch / cutscene
				else
				{
					float in_car_view_znear = 0.25f; // 0.25 seems fine for in-car view, doesn't improve as much as 1.0f but still better than 0.1f
					auto* pl_car = Game::pl_car();
					if (pl_car)
					{
						if (pl_car->car_kind_11 == 7) // 360SP still shows gap with 0.25
							in_car_view_znear = 0.2f;
					}

					camera->perspective_znear_BC = in_car_view_znear;
				} 
			}
		}
		D3DVECTOR savedPos{}, savedLook{};
		const bool driverSeatOffset = ApplyDriverSeatCameraOffset(
			camera, savedPos, savedLook, driverSeatFrame);
		CalcCameraMatrix.call(camera);
		if (driverSeatOffset)
		{
			// Only the generated native View matrix keeps the offset. Restore the
			// camera work immediately so the game's smoothing/controller never
			// feeds the synthetic cockpit position back into the next simulation tick.
			camera->cam_pos_F8 = savedPos;
			camera->look_pos_104 = savedLook;
		}
	}

	// hook Clr_SceneEffect so we can reset camera z-near before screen effects are draw
	inline static SafetyHookInline Clr_SceneEffect = {};
	static void Clr_SceneEffect_dest(int a1)
	{
		// Preserve the caller's suppression state: nested SceneEffect passes
		// must not re-enable the gameplay near-plane override mid-pass.
		const bool previousAllowZnearOverride = FixZBufferPrecision::allow_znear_override;
		FixZBufferPrecision::allow_znear_override = false;
		// Includes BOTH CalcCameraMatrix calls as well as Clr_SceneEffect:
		// render effects use the native short near-plane, while only real
		// world/vehicle passes may move the VR camera into the driver seat.
		// SceneEffect owns its short near-plane camera only until the original
		// effect GPU submission returns. Rebuild the *world* view after the
		// scope closes so a real driver-seat view cannot be replaced by the
		// temporary unshifted effect camera between world/car draws.
		EvWorkCamera* camera = Module::exe_ptr<EvWorkCamera>(0x39FE10);
		const float prev = camera->perspective_znear_BC;
		OutRunVR::DriverSeatRenderPass::RunSceneEffectThenRestoreView(
			[&]() {
				camera->perspective_znear_BC = 0.05f;
				CalcCameraMatrix_dest(camera);
				{
					OutRunVR::GameSemantic::ScopedRenderSemantic semantic(
						OutRunVR::GameSemantic::RenderScope::SceneEffect);
					Clr_SceneEffect.call(a1);
				}
			},
			[&]() {
				// The original effect has finished; the normal view-matrix owner
				// may now apply the validated native cockpit displacement once.
				camera->perspective_znear_BC = prev;
				CalcCameraMatrix_dest(camera);
			});
		FixZBufferPrecision::allow_znear_override = previousAllowZnearOverride;
	}

public:
	std::string_view description() override
	{
		return "FixZBufferPrecision";
	}

	bool validate() override
	{
        // DriverSeatView must still install the game camera hook if the
        // independent desktop Z-precision tweak was disabled in the INI.
		return Settings::FixZBufferPrecision ||
            (Settings::VREnabled && Settings::VRDriverSeatView);
	}

	void declare_settings() override
	{
		Settings::FixZBufferPrecision.needs_restart();
	}

	bool apply() override
	{
		CalcCameraMatrix = safetyhook::create_inline(Module::exe_ptr(CalcCameraMatrix_Addr), CalcCameraMatrix_dest);
		if (!CalcCameraMatrix)
			return false;

		Clr_SceneEffect = safetyhook::create_inline(Module::exe_ptr(Clr_SceneEffect_Addr), Clr_SceneEffect_dest);
		return !!Clr_SceneEffect;
	}

	static FixZBufferPrecision instance;
};
FixZBufferPrecision FixZBufferPrecision::instance;

class TransparencySupersampling : public Hook
{
	const static int DeviceInitHookAddr = 0xEC2F;
	const static int DeviceResetHookAddr = 0x17A20;

	inline static SafetyHookMid dest_hook = {};
	inline static SafetyHookMid deviceReset_hook = {};
	static void destination(safetyhook::Context& ctx)
	{
		static D3DADAPTER_IDENTIFIER9 adapterId = { 0 };

		if (adapterId.VendorId == 0)
		{
			auto* d3d = Game::D3D();
			if (!d3d || !SUCCEEDED(d3d->GetAdapterIdentifier(*Game::D3DAdapterNum, 0, &adapterId)))
				adapterId.VendorId = 0xFFFF;
		}

		if (adapterId.VendorId == 0x10DE) // NVIDIA
		{
			auto* device = Game::D3DDevice();
			spdlog::debug("TransparencySupersampling: enabling NVIDIA SSAA");
			device->SetRenderState(D3DRS_MULTISAMPLEANTIALIAS, TRUE);
			// SSAA support must not silently overwrite the game's cached
			// alpha, blend or line state at device init/Reset.
			device->SetRenderState(D3DRS_MULTISAMPLEMASK, 0xFFFFFFFF);

			// TODO: Allow switching between ATOC/SSAA modes, may give better performance for some?
			// Enabling ATOC here causes graphical issues though.
			// (Intel apparently supports the same ATOC switch, but users have reported issues before, unsure if they were on intel)
			//device->SetRenderState(D3DRS_ADAPTIVETESS_Y, D3DFORMAT(MAKEFOURCC('A', 'T', 'O', 'C')));

			// NVIDIA transparency supersampling. Report driver API result rather
            // than claiming that the actual hardware pixel cost was measured.
			const HRESULT ssaaHr = device->SetRenderState(
                D3DRS_ADAPTIVETESS_Y, D3DFORMAT(MAKEFOURCC('S', 'S', 'A', 'A')));
            char gpuLab[4]{};
            if (GetEnvironmentVariableA("OUTRUN_VR_GPU_PROFILE", gpuLab,
                    static_cast<DWORD>(std::size(gpuLab))) == 1 && gpuLab[0] == '1')
                spdlog::info(
                    "VR GPU LAB SSAA DEVICE: vendor=NVIDIA hr=0x{:08X} driverAccepted={} hardwareCost=UNTESTED",
                    static_cast<unsigned int>(ssaaHr), SUCCEEDED(ssaaHr));
		}

		// TODO: AMD ATOC mode.
		// This causes same graphical issues that the NVIDIA ATOC above gave.
		// Maybe it can be worked into the actual rendering code instead.
#if 0
		else if (adapterId.VendorId == 0x1002) // AMD
		{
			auto* device = Game::D3DDevice();
			spdlog::debug("TransparencySupersampling: enabling AMD ATOC");
			device->SetRenderState(D3DRS_MULTISAMPLEANTIALIAS, TRUE);
			device->SetRenderState(D3DRS_ANTIALIASEDLINEENABLE, TRUE);
			device->SetRenderState(D3DRS_ALPHABLENDENABLE, TRUE);
			device->SetRenderState(D3DRS_SRCBLEND, D3DBLEND_SRCALPHA);
			device->SetRenderState(D3DRS_DESTBLEND, D3DBLEND_INVSRCALPHA);
			device->SetRenderState(D3DRS_MULTISAMPLEMASK, 0xFFFFFFFF);

			// AMD ATOC
			device->SetRenderState(D3DRS_POINTSIZE, MAKEFOURCC('A', '2', 'M', '1'));
		}
#endif
	}

public:
	std::string_view description() override
	{
		return "TransparencySupersampling";
	}

	bool validate() override
	{
        // VR.Enabled defaults to true even for plain 2D launches. Do not
        // suppress the original 2D graphics setting unless the selected
        // backend is actually the native DX9Ex VR reference.
        char backend[32]{};
        const DWORD length = GetEnvironmentVariableA(
            "OUTRUN_VR_BACKEND", backend, static_cast<DWORD>(std::size(backend)));
        const bool activeNativeVr = Settings::VREnabled &&
            length > 0 && length < std::size(backend) &&
            lstrcmpiA(backend, "d3d9") == 0;
        const bool eligible = Settings::TransparencySupersampling &&
            (!activeNativeVr || Settings::VRTransparencySupersampling);
        char gpuLab[4]{};
        if (GetEnvironmentVariableA("OUTRUN_VR_GPU_PROFILE", gpuLab,
                static_cast<DWORD>(std::size(gpuLab))) == 1 && gpuLab[0] == '1')
            spdlog::info(
                "VR GPU LAB SSAA GATE: graphics={} vr={} nativeDX9Ex={} eligible={} (device API acceptance tracked separately)",
                Settings::TransparencySupersampling.get(),
                Settings::VRTransparencySupersampling.get(), activeNativeVr, eligible);
        return eligible;
	}

	void declare_settings() override
	{
		Settings::TransparencySupersampling.needs_restart();
        Settings::VRTransparencySupersampling.needs_restart();
	}

	bool apply() override
	{
		dest_hook = safetyhook::create_mid(Module::exe_ptr(DeviceInitHookAddr), destination);
		deviceReset_hook = safetyhook::create_mid(Module::exe_ptr(DeviceResetHookAddr), destination);
		return !!dest_hook;
	}

	static TransparencySupersampling instance;
};
TransparencySupersampling TransparencySupersampling::instance;

class WindowedBorderless : public Hook
{
	const static int WinMain_BorderlessWindow_WndStyleExAddr = 0x18175;
	const static int WinMain_BorderlessWindow_WndStyleAddr = 0x1817A;
	const static int Win32_Init_DisableWindowResize_Addr1 = 0xE9E3;
	const static int Win32_Init_DisableWindowResize_Addr2 = 0xEA30;
	const static int Win32_Init_SetWindowPos_Addr = 0xEAA7;

	inline static SafetyHookMid dest_hook = {};
	static void destination(safetyhook::Context& ctx)
	{
		HWND window = HWND(ctx.ebp);
		int x = Settings::WindowPositionX;
		int y = Settings::WindowPositionY;
		int width = Game::screen_resolution->x;
		int height = Game::screen_resolution->y;

		// VR may intentionally render a larger internal backbuffer than the PC
		// desktop. Keep that render resolution for the HMD/SBS source, but fit the
		// borderless mirror window to the current monitor so a 3840x2160 render on
		// a 3440x1440 display is scaled instead of extending off-screen.
        // Preserve the VR internal eye backbuffer. Only resize the PC mirror
        // when a valid VR render resolution is explicitly configured.
        const bool vrInternalOverride = Settings::VRRenderWidth >= 640 &&
            Settings::VRRenderHeight >= 480 &&
            static_cast<std::int64_t>(static_cast<int>(Settings::VRRenderWidth)) *
                static_cast<int>(Settings::VRRenderHeight) <= 16777216LL;
        if (Settings::VREnabled &&
            (Settings::VRMirrorFitDesktop || vrInternalOverride || Settings::VRAutoRenderResolution))
		{
			MONITORINFO monitorInfo{};
			monitorInfo.cbSize = sizeof(monitorInfo);
			const HMONITOR monitor = MonitorFromWindow(
				window, MONITOR_DEFAULTTOPRIMARY);
			if (monitor && GetMonitorInfoW(monitor, &monitorInfo))
			{
                const int monitorWidth =
                    monitorInfo.rcMonitor.right - monitorInfo.rcMonitor.left;
                const int monitorHeight =
                    monitorInfo.rcMonitor.bottom - monitorInfo.rcMonitor.top;
                x = monitorInfo.rcMonitor.left;
                y = monitorInfo.rcMonitor.top;
                width = monitorWidth;
                height = monitorHeight;
                // The unified physical source may be portrait 2496x2688
                // while a 3440x1440 desktop mirror is ultrawide. Stretching
                // the HWND to that whole monitor rescales the D3D9Ex Present
                // anisotropically and flattens car/menu sprites vertically.
                // Fit the WINDOW, never the actual game/eye render buffers.
                // Users can opt out for old full-width mirror A/B captures.
                if (Settings::VRMirrorPreserveAspect) {
                    const auto fit = OutRunVRMirrorAspect::Fit(
                        monitorWidth, monitorHeight,
                        Game::screen_resolution->x,
                        Game::screen_resolution->y);
                    if (fit.valid) {
                        x += fit.left;
                        y += fit.top;
                        width = fit.width;
                        height = fit.height;
                    }
                }
                spdlog::info(
                    "VR PC MIRROR: monitor={}x{} source={}x{} fittedWindow={}x{} origin={},{} preserveAspect={} (OpenXR eyes unchanged)",
                    monitorWidth, monitorHeight,
                    Game::screen_resolution->x, Game::screen_resolution->y,
                    width, height, x, y,
                    Settings::VRMirrorPreserveAspect.get());
			}
		}

		SetWindowPos(window, 0, x, y, width, height, 0x40);
	}

public:
	std::string_view description() override
	{
		return "WindowedBorderless";
	}

	bool validate() override
	{
		return Settings::WindowedBorderless;
	}

	void declare_settings() override
	{
		Settings::WindowedBorderless.needs_restart();
		Settings::WindowPositionX.needs_restart();
		Settings::WindowPositionY.needs_restart();
	}

	bool apply() override
	{
		auto* patch_addr = Module::exe_ptr(WinMain_BorderlessWindow_WndStyleExAddr);
		Memory::VP::Patch(patch_addr, uint32_t(0));

		patch_addr = Module::exe_ptr(WinMain_BorderlessWindow_WndStyleAddr);
		Memory::VP::Patch(patch_addr, uint32_t(WS_POPUP));

		patch_addr = Module::exe_ptr(Win32_Init_DisableWindowResize_Addr1);
		Memory::VP::Nop(patch_addr, 6);

		patch_addr = Module::exe_ptr(Win32_Init_DisableWindowResize_Addr2);
		Memory::VP::Nop(patch_addr, 6);

		// replace original SetWindowPos call
		Memory::VP::Nop(Module::exe_ptr(Win32_Init_SetWindowPos_Addr), 0x23);
		dest_hook = safetyhook::create_mid(Module::exe_ptr(Win32_Init_SetWindowPos_Addr), destination);

		return true;
	}

	static WindowedBorderless instance;
};
WindowedBorderless WindowedBorderless::instance;

class AnisotropicFiltering : public Hook
{
	const static int ChangeTexAttribute_HookAddr1 = 0x9AD8;
	const static int ChangeTexAttribute_HookAddr2 = 0x8960;

	inline static SafetyHookMid dest_hook = {};
	static bool PreserveScreenTextureFiltering() noexcept
	{
		if (!Settings::VREnabled.get())
			return false;
		const auto scope = OutRunVR::GameSemantic::EffectiveScope();
		return scope == OutRunVR::GameSemantic::RenderScope::ScreenHud ||
			scope == OutRunVR::GameSemantic::RenderScope::ScreenOverlay2D ||
			scope == OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D ||
			scope == OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D;
	}
	static void destination(safetyhook::Context& ctx)
	{
		if (Settings::AnisotropicFiltering <= 0)
			return;
		const int sampler = ctx.ebp;
		// A prior 3D texture can leave 16x anisotropy on a HUD sampler.
		// Keep 2D MIN/MAG/MIP unmodified while resetting its max level.
		const int anisotropy = PreserveScreenTextureFiltering()
			? 1 : Settings::AnisotropicFiltering.get();
		Game::D3DDevice()->SetSamplerState(sampler,
			D3DSAMP_MAXANISOTROPY, anisotropy);
	}

	// ChangeTexAttribute reads the mip filter from bits 19-20 of the material and
	// passes it straight to D3DSAMP_MIPFILTER, but first rewrites a 3 into a 1:
	// D3DTEXF_ANISOTROPIC is not a legal D3D9 mip filter, and it picks POINT rather
	// than LINEAR to replace it.
	// A material asking for the best filtering therefore gets hard mip transitions, 
	// which shimmer wherever the mip level changes quickly across a surface, thin 
	// geometry seen at an angle most of all.
	const static int MipFilter_HookAddr = 0x9B73;

	inline static SafetyHookMid mip_hook = {};
	static void mip_destination(safetyhook::Context& ctx)
	{
		if (Settings::AnisotropicFiltering <= 0 ||
			PreserveScreenTextureFiltering())
			return;

		// Only upgrade POINT. A material that asked for no mipmapping at all is
		// left alone, since that is a deliberate choice for 2D and UI textures.
		if (ctx.esi == D3DTEXF_POINT)
			ctx.esi = D3DTEXF_LINEAR;
	}

	inline static SafetyHookMid dest_hook2 = {};
	static void destination2(safetyhook::Context& ctx)
	{
		// Checked before the filter is forced below, so 0 really does leave the
		// games filtering untouched rather than only skipping the level.
		if (Settings::AnisotropicFiltering <= 0 ||
			PreserveScreenTextureFiltering())
			return;
		// Only minification needs forced anisotropy for 3D materials.
		// MAGFILTER retains the game's requested value. All ScreenHud and
		// 2D overlays still bypass this hook via PreserveScreenTextureFiltering.
		if (ctx.edi == D3DSAMP_MINFILTER)
			ctx.esi = D3DTEXF_ANISOTROPIC;
	}

public:
	std::string_view description() override
	{
		return "AnisotropicFiltering";
	}

	bool apply() override
	{
		dest_hook = safetyhook::create_mid(Module::exe_ptr(ChangeTexAttribute_HookAddr1), destination);
		dest_hook2 = safetyhook::create_mid(Module::exe_ptr(ChangeTexAttribute_HookAddr2), destination2);
		mip_hook = safetyhook::create_mid(Module::exe_ptr(MipFilter_HookAddr), mip_destination);

		return true;
	}

	static AnisotropicFiltering instance;
};
AnisotropicFiltering AnisotropicFiltering::instance;

class VSyncOverride : public Hook
{
	const static int D3DInit_HookAddr = 0xEB66;

	inline static SafetyHookMid dest_hook = {};

	static bool IsNativeD3D9ReferenceLaunch() noexcept
	{
		char backend[32]{};
		const DWORD length = GetEnvironmentVariableA(
			"OUTRUN_VR_BACKEND", backend, static_cast<DWORD>(std::size(backend)));
		return length > 0 && length < std::size(backend) &&
			lstrcmpiA(backend, "d3d9") == 0;
	}

	static void ConfigureReferenceVRMSAA() noexcept
	{
		if (!Settings::VREnabled || !IsNativeD3D9ReferenceLaunch() ||
			!Game::D3D() || !Game::D3DPresentParams || !Game::D3DAdapterNum)
			return;

        auto& params = *Game::D3DPresentParams;
        const int vrMode = Settings::VRAntiAliasing.get();
        if (vrMode == 3)
        {
            // Keep 2D's AA selection unchanged only in explicit Game AA mode.
            spdlog::info("VR DX9Ex AA: using original game/2D type={} quality={}",
                static_cast<int>(params.MultiSampleType), params.MultiSampleQuality);
            return;
        }
        // VR-only modes must not inherit an expensive game NONMASKABLE request.
        // This does not change Game::D3DAntialiasing or saved 2D configuration.
        params.MultiSampleType = D3DMULTISAMPLE_NONE;
        params.MultiSampleQuality = 0;
        if (vrMode == 0)
        {
            spdlog::info("VR DX9Ex AA: Off, independent of 2D game AA");
            return;
        }
        if (vrMode != 1 && vrMode != 2 && vrMode != 4)
        {
            spdlog::warn("VR DX9Ex AA: invalid level {}, using Off", vrMode);
            return;
        }
        if (params.SwapEffect != D3DSWAPEFFECT_DISCARD)
        {
            spdlog::warn("VR DX9Ex AA: swap effect {} disallows MSAA; using Off",
                static_cast<int>(params.SwapEffect));
            return;
        }

		const UINT adapter = static_cast<UINT>(*Game::D3DAdapterNum);
		D3DFORMAT colorFormat = params.BackBufferFormat;
		if (colorFormat == D3DFMT_UNKNOWN)
		{
			D3DDISPLAYMODE mode{};
			if (FAILED(Game::D3D()->GetAdapterDisplayMode(adapter, &mode)))
			{
				spdlog::warn("VR DX9Ex AA: display format unavailable; using Off");
				return;
			}
			colorFormat = mode.Format;
		}

        // 2x never escalates. 4x may fall back to 2x. 8x is
        // opt-in and tries 8x -> 4x -> 2x; unsupported modes fail closed.
        // Preserve mode 3 as "Use Game AA" for existing user INI files.
		const D3DMULTISAMPLE_TYPE candidates[] = {
            D3DMULTISAMPLE_8_SAMPLES,
			D3DMULTISAMPLE_4_SAMPLES,
			D3DMULTISAMPLE_2_SAMPLES
		};
		for (const auto sampleType : candidates)
		{
            if (vrMode == 1 && sampleType != D3DMULTISAMPLE_2_SAMPLES)
                continue;
            if (vrMode == 2 && sampleType == D3DMULTISAMPLE_8_SAMPLES)
                continue;
			DWORD colorQuality = 0;
			if (FAILED(Game::D3D()->CheckDeviceMultiSampleType(
					adapter, D3DDEVTYPE_HAL, colorFormat, params.Windowed,
					sampleType, &colorQuality)) ||
				colorQuality == 0)
				continue;

			DWORD depthQuality = colorQuality;
			if (params.EnableAutoDepthStencil)
			{
				if (FAILED(Game::D3D()->CheckDeviceMultiSampleType(
						adapter, D3DDEVTYPE_HAL, params.AutoDepthStencilFormat,
						params.Windowed, sampleType, &depthQuality)) ||
					depthQuality == 0)
					continue;
			}

			params.MultiSampleType = sampleType;
            // Index zero avoids forcing an adapter's maximum quality tier.
			params.MultiSampleQuality = 0;
			spdlog::info(
				"VR DX9Ex AA: explicit {}x MSAA selected quality={} (colorLevels={} depthLevels={}); replaces ambiguous NONMASKABLE game AA",
				static_cast<int>(sampleType), params.MultiSampleQuality,
				colorQuality, depthQuality);
			return;
		}

		spdlog::warn("VR DX9Ex AA: selected MSAA unsupported; using Off (not game 2D AA)");
	}

	static void destination(safetyhook::Context& ctx)
	{
		ConfigureReferenceVRMSAA();
		if (Settings::VREnabled && Settings::VRDisableDesktopVsync)
		{
			Game::D3DPresentParams->PresentationInterval =
				D3DPRESENT_INTERVAL_IMMEDIATE;
			spdlog::info("VR PRESENT: desktop D3D9 VSync bypass active; OpenXR cadence is owned by the host/runtime");
		}
		else
		{
			Game::D3DPresentParams->PresentationInterval = Settings::VSync;
			if (!Settings::VSync)
				Game::D3DPresentParams->PresentationInterval =
					D3DPRESENT_INTERVAL_IMMEDIATE;
		}

		// DX9Ex reference runs select an explicit multisample type above.
		// Other backends retain the game's original AA presentation parameters.
	}

public:
	std::string_view description() override
	{
		return "VSync";
	}

	bool validate() override
	{
		// The D3D9 reference path also owns the explicit MSAA selection above.
		// CORRECTNESS normally keeps desktop VSync at its default, so without
		// this clause the hook never installed and the runtime silently stayed
		// on the game's NONMASKABLE AA despite the requested 4x/2x policy.
		return Settings::VSync != 1 ||
			(Settings::VREnabled &&
				(Settings::VRDisableDesktopVsync ||
				 IsNativeD3D9ReferenceLaunch()));
	}

	void declare_settings() override
	{
		Settings::VSync.needs_restart();
        Settings::VRAntiAliasing.needs_restart();
	}

	bool apply() override
	{
		dest_hook = safetyhook::create_mid(Module::exe_ptr(D3DInit_HookAddr), destination);

		return true;
	}

	static VSyncOverride instance;
};
VSyncOverride VSyncOverride::instance;