#define WIN32_LEAN_AND_MEAN
#define DIRECTINPUT_VERSION 0x0800
#include <Windows.h>
#include <commctrl.h>
#include <dinput.h>

#pragma comment(lib, "dinput8.lib")
#pragma comment(lib, "dxguid.lib")
#pragma comment(lib, "Comctl32.lib")

#include <algorithm>
#include <cmath>
#include <cctype>
#include <cstring>
#include <cstdio>
#include <string>
#include <vector>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "hooks_wheel_vehicle_dynamics.hpp"
#include "wheel_ffb_math.hpp"
#include "overlay/overlay.hpp"

extern "C"
{
    void __cdecl CalcVibrationValues(EVWORK_CAR* car);
}

extern double __cdecl sub_1149C0(unsigned int surfaceMask, int loadColiType, DWORD* waterFlag);
extern float InputManager_SteeringValue();

namespace Settings
{
    extern Setting<bool> UseNewInput;
    // Experimental branch: enabled by default, but deliberately conservative for DD wheels.
    Setting<bool> WheelFFBEnable{
        "WheelFFB", "Enable", true,
        "Enable experimental DirectInput COM force feedback for steering wheels."
    };

    Setting<std::string> WheelFFBDeviceName{
        "WheelFFB", "DeviceName", "MOZA",
        "Case-insensitive substring used to select the FFB wheel. Empty selects the first non-virtual FFB device."
    };

    Setting<std::string> WheelFFBDeviceGuid{
        "WheelFFB", "DeviceGuid", "",
        "Exact DirectInput instance GUID selected by F11 Wheel Setup; a saved GUID never falls back to a different device automatically."
    };

    Setting<float> WheelFFBGlobalStrength{
        "WheelFFB", "GlobalStrength", 0.70f,
        "Master force-model gain. Applied before soft saturation/slew; 1.0=100%, 1.5=150% headroom.", Range<float>{ 0.0f, 1.5f }
    };

    Setting<float> WheelFFBSpringStrength{
        "WheelFFB", "SpringStrength", 0.65f,
        "Speed-dependent center restoring force. Drives GUID_Spring when hardware spring is enabled.", Range<float>{ 0.0f, 1.5f }
    };

    Setting<bool> WheelFFBUseHardwareSpring{
        "WheelFFB", "UseHardwareSpring", true,
        "Use a DirectInput GUID_Spring condition effect for centering instead of synthesizing spring torque at 60 Hz."
    };

    Setting<float> WheelFFBSpringSaturation{
        "WheelFFB", "SpringSaturation", 0.775f,
        "Maximum hardware spring output before GlobalStrength, based on the FXT spring saturation model.", Range<float>{ 0.1f, 1.0f }
    };

    Setting<float> WheelFFBDamperStrength{
        "WheelFFB", "DamperStrength", 0.30f,
        "Dynamic steering damping. For DD wheels try 0.25-0.45.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<bool> WheelFFBUseHardwareDamper{
        "WheelFFB", "UseHardwareDamper", true,
        "Use DirectInput GUID_Damper when the wheel supports it; otherwise use the software fallback."
    };

    Setting<float> WheelFFBSteeringWeight{
        "WheelFFB", "SteeringWeight", 1.45f,
        "Self-aligning torque strength. Physics SAT direction/trail comes from front slip; field_264/268 only scale lateral load.", Range<float>{ 0.0f, 2.0f }
    };

    Setting<bool> WheelFFBPhysicsSat{
        "WheelFFB", "PhysicsSAT", true,
        "Experimental body-slip/yaw SAT instead of steering-centre direction alone."
    };

    Setting<float> WheelFFBGripLoss{
        "WheelFFB", "GripLoss", 0.65f,
        "How strongly real chassis/front-slip signals release damping and unload SAT. Lateral G is load only, never a drift detector.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBLateralDeadzone{
        "WheelFFB", "LateralDeadzone", 1.5f,
        "Subtractive noise floor for the game's lateral-G/load signal.", Range<float>{ 0.0f, 8.0f }
    };

    Setting<float> WheelFFBWeightTransfer{
        "WheelFFB", "WeightTransfer", 0.60f,
        "Longitudinal acceleration/braking modulation of steering load.", Range<float>{ 0.0f, 1.5f }
    };

    Setting<float> WheelFFBWallImpact{
        "WheelFFB", "WallImpact", 0.38f,
        "Collision impulse strength.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBGearShift{
        "WheelFFB", "GearShift", 0.18f,
        "Symmetric gear-change thunk strength.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBRoadTexture{
        "WheelFFB", "RoadTexture", 0.30f,
        "Hardware sine vibration driven by the game's own surface roughness table.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBTireSlip{
        "WheelFFB", "TireSlip", 0.20f,
        "Hardware sine chatter driven mainly by estimated front-tire scrub, with a small chassis-slide contribution.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBEngineIdle{
        "WheelFFB", "EngineIdle", 0.04f,
        "Low-speed launch/idle vibration.", Range<float>{ 0.0f, 0.5f }
    };

    Setting<float> WheelFFBSlewRate{
        "WheelFFB", "SlewRate", 0.06f,
        "Maximum structural-force change per 60 Hz tick, normalized 0..1.", Range<float>{ 0.01f, 1.0f }
    };

    Setting<bool> WheelFFBUsePeriodicEffects{
        "WheelFFB", "UsePeriodicEffects", true,
        "Use DirectInput hardware GUID_Sine effects for road texture and tire slip."
    };

    Setting<bool> WheelFFBInvertForce{
        "WheelFFB", "InvertForce", true,
        "Reverse ConstantForce steering/event direction without changing the centering spring."
    };

    Setting<bool> WheelFFBInvertSpring{
        "WheelFFB", "InvertSpring", false,
        "Reverse only the DirectInput GUID_Spring condition direction. Leave off when the wheel returns toward centre normally."
    };

    Setting<bool> WheelFFBTelemetry{
        "WheelFFB", "Telemetry", false,
        "Opt-in 10 Hz dynamics and force-pipeline telemetry. Event logs remain separate."
    };

    Setting<bool> WheelFFBDebugLog{
        "WheelFFB", "DebugLog", true,
        "Write a compact FFB diagnostic line about once every two seconds."
    };
}

namespace
{
    constexpr UINT_PTR FFB_SUBCLASS_ID = 0x0FFB;
    constexpr UINT_PTR FFB_WATCHDOG_TIMER_ID = 0x0FFA;
    constexpr UINT FFB_WATCHDOG_INTERVAL_MS = 100;
    constexpr DWORD FFB_EFFECT_LEASE_US = 250000;
    constexpr DWORD FFB_EFFECT_REFRESH_MS = 100;
    constexpr DWORD FFB_DEVICE_FAILURE_GRACE_MS = 750;
    constexpr DWORD FFB_DEVICE_RETRY_MS = 750;

    // GetTickCount wraps roughly every 49.7 days. Compare deadlines by signed
    // subtraction so retry/holdoff gates remain correct across the wrap.
    bool tick_before(DWORD now, DWORD deadline)
    {
        return deadline != 0 && static_cast<LONG>(now - deadline) < 0;
    }

    bool tick_reached(DWORD now, DWORD deadline)
    {
        return deadline == 0 || static_cast<LONG>(now - deadline) >= 0;
    }

    std::string lower_copy(const char* text)
    {
        std::string result = text ? text : "";
        std::transform(result.begin(), result.end(), result.begin(),
            [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        return result;
    }

    std::string directinput_guid_key(const GUID& guid)
    {
        char b[64]{};
        std::snprintf(b, sizeof(b),
            "%08X-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X",
            (unsigned)guid.Data1, (unsigned)guid.Data2, (unsigned)guid.Data3,
            (unsigned)guid.Data4[0], (unsigned)guid.Data4[1],
            (unsigned)guid.Data4[2], (unsigned)guid.Data4[3],
            (unsigned)guid.Data4[4], (unsigned)guid.Data4[5],
            (unsigned)guid.Data4[6], (unsigned)guid.Data4[7]);
        return lower_copy(b);
    }

    bool is_virtual_device_name(const std::string& lowered)
    {
        static constexpr const char* VirtualNames[] = {
            "vjoy", "vigem", "xoutput", "virtual", "vxbox", "v xbox",
            "hidguardian", "hidhide"
        };

        for (const char* token : VirtualNames)
        {
            if (lowered.find(token) != std::string::npos)
                return true;
        }
        return false;
    }

    class WheelFFBEngine
    {
    public:
        void update(EVWORK_CAR* car)
        {
            if (panicStopped_)
                return;

            if (disable_live_if_needed())
                return;
            enabledLastTick_ = true;

            if (!car)
            {
                if (initialized_)
                {
                    zero_all_forces();
                    reset_signal_state();
                }
                lastCar_ = nullptr;
                return;
            }

            // Safety first for a DD base: WM_ACTIVATEAPP releases exclusive
            // ownership when the game loses focus. The foreground window is also
            // authoritative on recovery so a missed activation message cannot
            // leave FFB permanently dormant after Alt-Tab.
            if (!appActive_)
            {
                if (gameHwnd_ && GetForegroundWindow() == gameHwnd_)
                {
                    appActive_ = true;
                    warmupFrames_ = 0;
                }
                else
                {
                    if (initialized_)
                    {
                        zero_all_forces();
                        reset_signal_state();
                    }
                    return;
                }
            }

            // WM_ACTIVATEAPP is normally authoritative, but keep a direct
            // foreground guard as a second DD-wheel safety net. A delayed or
            // missed activation message must never leave background torque
            // running merely because the device uses DISCL_BACKGROUND.
            if (initialized_ && gameHwnd_ && GetForegroundWindow() != gameHwnd_)
            {
                appActive_ = false;
                zero_all_forces();
                reset_signal_state();
                if (device_ && deviceAcquired_)
                {
                    device_->Unacquire();
                    deviceAcquired_ = false;
                }
                return;
            }

            const DWORD updateNow = GetTickCount();

            if (initialized_)
            {
                const std::string guidNow = lower_copy(Settings::WheelFFBDeviceGuid.get().c_str());
                const std::string nameNow = lower_copy(Settings::WheelFFBDeviceName.get().c_str());
                if (guidNow != selectedConfiguredGuid_ || nameNow != selectedConfiguredName_)
                {
                    selectedConfiguredGuid_ = guidNow;
                    selectedConfiguredName_ = nameNow;
                    request_device_reinitialize("configured wheel identity changed", S_OK);
                    return;
                }
            }

            if (deviceReinitPending_)
            {
                if (tick_before(updateNow, deviceReinitAfter_))
                    return;
                teardown_for_reinitialize();
                deviceReinitPending_ = false;
                deviceFailureSince_ = 0;
                initialized_ = false;
                retryAfter_ = updateNow + FFB_DEVICE_RETRY_MS;
                spdlog::info(
                    "WheelFFB: DirectInput device released; waiting to re-enumerate after device loss");
                return;
            }

            lastUpdateTick_ = updateNow;

            if (!initialized_)
            {
                if (tick_before(GetTickCount(), retryAfter_))
                    return;
                if (!initialize())
                {
                    retryAfter_ = GetTickCount() + 2000;
                    return;
                }
            }

            const bool inGameplay =
                Game::current_mode && (*Game::current_mode == STATE_GAME);

            if (!inGameplay)
            {
                zero_all_forces();
                // Let the legacy/menu DirectInput reader reacquire the same
                // physical wheel while menus or F11 setup are active. Effects
                // remain created and are reused when gameplay resumes.
                if (device_ && deviceAcquired_)
                {
                    device_->Unacquire();
                    deviceAcquired_ = false;
                }
                reset_signal_state();
                return;
            }

            if (device_ && !deviceAcquired_)
            {
                if (!gameHwnd_ || GetForegroundWindow() != gameHwnd_)
                    return;

                const HRESULT acquireHr = device_->Acquire();
                if (FAILED(acquireHr) && acquireHr != S_FALSE)
                {
                    note_device_failure("gameplay Acquire", acquireHr);
                    return;
                }

                if (GetForegroundWindow() != gameHwnd_)
                {
                    device_->Unacquire();
                    deviceAcquired_ = false;
                    return;
                }

                deviceAcquired_ = true;
                clear_device_failure();
                const HRESULT actuatorHr =
                    device_->SendForceFeedbackCommand(DISFFC_SETACTUATORSON);
                if (FAILED(actuatorHr))
                {
                    note_device_failure("SETACTUATORSON", actuatorHr);
                    device_->Unacquire();
                    deviceAcquired_ = false;
                    return;
                }
                clear_device_failure();
            }

            if (manualTestFrames_ > 0)
            {
                if (springEffect_)
                    update_spring(0.0f);
                if (damperEffect_)
                    update_damper(0.0f);
                if (roadTextureEffect_)
                    update_periodic(roadTextureEffect_, roadState_, 0.0f, 30.0f);
                if (tireSlipEffect_)
                    update_periodic(tireSlipEffect_, slipState_, 0.0f, 35.0f);

                crashImpulseTimer_ = 0;
                crashImpulseForce_ = 0.0f;
                gearShiftTimer_ = 0;
                splashTimer_ = 0;
                splashAmp_ = 0.0f;

                LONG testLevel = manualTestDirection_ * 2000L;
                if (Settings::WheelFFBInvertForce)
                    testLevel = -testLevel;
                set_constant_force(testLevel);
                --manualTestFrames_;
                if (manualTestFrames_ == 0)
                {
                    zero_all_forces();
                    reset_signal_state();
                }
                return;
            }

            if (Overlay::IsActive || Overlay::IsBindingDialogActive)
            {
                zero_all_forces();
                reset_signal_state();
                return;
            }

            if (lastCar_ != car)
            {
                zero_all_forces();
                reset_signal_state();
                lastCar_ = car;
            }

            const float steer = read_game_steering();
            float rawSteerRate = 0.0f;
            if (steerSampleValid_)
            {
                rawSteerRate = steer - prevSteer_;
                smoothedSteerRate_ += (rawSteerRate - smoothedSteerRate_) * 0.45f;
            }
            else
            {
                // First sample after menu/race/device transitions is a baseline,
                // not a one-tick steering velocity.
                steerSampleValid_ = true;
                smoothedSteerRate_ = 0.0f;
            }
            prevSteer_ = steer;
            const float steerRate = smoothedSteerRate_;

            // field_1C4 reaches roughly 2.0 at OutRun top speed. Normalize by 2
            // rather than treating 1.0 as terminal speed.
            const float speedRaw = car->field_1C4;
            const float speed = std::isfinite(speedRaw) ? speedRaw : 0.0f;
            const float speedNorm = std::clamp(speed / 2.0f, 0.0f, 1.0f);
            const float configuredStrength =
                static_cast<float>(Settings::WheelFFBGlobalStrength);
            const float outputStrength = std::isfinite(configuredStrength)
                ? std::clamp(configuredStrength, 0.0f, 1.5f)
                : 0.0f;

            const uint32_t stateFlags = car->field_8;
            const uint32_t curGear = car->cur_gear_208;
            const float lateralSum = car->field_264 + car->field_268;
            const float lateralRaw = std::isfinite(lateralSum) ? lateralSum : 0.0f;

            // Fast attack / slightly slower release. This is intentionally close
            // to the Redux-era tuning, but the steering backbone comes from the
            // real game input instead of car->field_1D0.
            const float alpha =
                std::abs(lateralRaw) > std::abs(smoothedLateral_) ? 0.18f : 0.12f;
            smoothedLateral_ += (lateralRaw - smoothedLateral_) * alpha;

            lateralHistory_[lateralHistoryIndex_ % LateralHistoryCount] = smoothedLateral_;
            ++lateralHistoryIndex_;

            float lateralDz = 0.0f;
            {
                const float mag =
                    std::abs(smoothedLateral_) - static_cast<float>(Settings::WheelFFBLateralDeadzone);
                if (mag > 0.0f)
                    lateralDz = smoothedLateral_ >= 0.0f ? mag : -mag;
            }

            // field_264 + field_268 is treated strictly as lateral acceleration/load.
            // It must never decide whether the tyres are sliding; that comes from
            // bodySlip/frontSlip estimated from actual vehicle motion.
            const float latNorm = std::clamp(lateralDz / 24.0f, -1.0f, 1.0f);
            const float lateralLoad = std::clamp(std::abs(latNorm), 0.0f, 1.0f);
            const float lateralLoadSmooth =
                lateralLoad * lateralLoad * (3.0f - 2.0f * lateralLoad);

            const int previousDiscontinuities = vehicleDynamics_.discontinuityCount();
            vehicleDynamics_.update(car, steer, speedNorm, lateralLoadSmooth);
            if (vehicleDynamics_.discontinuityCount() != previousDiscontinuities)
            {
                spdlog::info("WheelFFB EVENT: motion discontinuity; clearing force and event histories");
                zero_all_forces();
                reset_signal_state();
                return;
            }

            const float bodySlideT = std::clamp(
                (std::abs(vehicleDynamics_.bodySlip()) - 0.10f) / 0.22f,
                0.0f, 1.0f);
            const float bodySlide =
                bodySlideT * bodySlideT * (3.0f - 2.0f * bodySlideT);
            const float frontScrubT = std::clamp(
                (std::abs(vehicleDynamics_.frontSlip()) - 0.04f) / 0.14f,
                0.0f, 1.0f);
            const float frontScrub =
                frontScrubT * frontScrubT * (3.0f - 2.0f * frontScrubT);
            const float configuredGripLoss =
                static_cast<float>(Settings::WheelFFBGripLoss);
            const float gripLoss = std::isfinite(configuredGripLoss)
                ? std::clamp(configuredGripLoss, 0.0f, 1.0f)
                : 0.0f;

            speedHistory_[speedHistoryIndex_ % SpeedHistoryCount] = speed;
            ++speedHistoryIndex_;

            update_crash_detection(speed, stateFlags);
            update_gear_event(curGear);

            float roughness = 0.0f;
            DWORD waterFlag = 0;
            for (int i = 0; i < 4; ++i)
            {
                const float surfaceRoughness = static_cast<float>(sub_1149C0(
                    car->water_flag_24C[i],
                    static_cast<int>(car->OnRoadPlace_5C.loadColiType_0),
                    &waterFlag));
                if (std::isfinite(surfaceRoughness))
                    roughness = std::max(roughness, surfaceRoughness);
            }

            // Road texture and tire-slip envelopes.  sub_1149C0 returns
            // ~0.25 for ordinary asphalt; that is a material baseline, not a
            // request to vibrate the wheel.  The Xbox routine only enters its
            // stronger surface branch above roughly 0.30, so remove that
            // baseline here and ramp rough surfaces from 0.30 -> 0.85.
            const float textureRoughness =
                std::clamp((roughness - 0.30f) / 0.55f, 0.0f, 1.0f);
            const float roadSpeedGate =
                std::clamp((speedNorm - 0.05f) / 0.20f, 0.0f, 1.0f);

            // Xbox gamepad rumble treats snow/ice as a continuously rough
            // material. On a DD wheel that becomes an unpleasant constant
            // high-frequency sine. Stage IDs follow Game::StageNames: 4/19
            // are Snowy Mountain/Ice Scape and +30 are their reverse variants.
            const int stageNumber = Game::GetNowStageNum(8);
            const int uniqueStage = Game::GetStageUniqueNum(stageNumber);
            const bool snowOrIceStage =
                uniqueStage == 4 || uniqueStage == 19 ||
                uniqueStage == 34 || uniqueStage == 49;
            constexpr float SnowIceRoadTextureScale = 0.04f;
            const float stageRoadTextureScale =
                snowOrIceStage ? SnowIceRoadTextureScale : 1.0f;

            float roadAmp =
                textureRoughness * roadSpeedGate *
                static_cast<float>(Settings::WheelFFBRoadTexture) * outputStrength *
                stageRoadTextureScale;
            const float roadFreq = 25.0f + 12.0f * speedNorm;

            if (waterFlag && roughness > 0.7f && speedNorm > 0.70f && splashTimer_ <= 0)
            {
                const float roadTextureScale = std::clamp(
                    static_cast<float>(Settings::WheelFFBRoadTexture) / 0.20f,
                    0.0f, 5.0f);
                splashAmp_ =
                    (roughness - 0.7f) * speedNorm * 0.75f * roadTextureScale *
                    outputStrength * stageRoadTextureScale;
                splashTimer_ = 9;
            }
            if (splashTimer_ > 0)
            {
                roadAmp = std::max(roadAmp, splashAmp_);
                --splashTimer_;
            }

            float slipAmp = 0.0f;
            float slipFreq = 40.0f;
            const float slipSeverity = std::clamp(
                frontScrub * (0.50f + 0.50f * lateralLoadSmooth) +
                    bodySlide * 0.20f,
                0.0f, 1.0f);
            if (slipSeverity > 0.08f && speedNorm > 0.05f)
            {
                slipAmp =
                    slipSeverity * static_cast<float>(Settings::WheelFFBTireSlip) *
                    outputStrength;
                slipFreq = 40.0f - 12.0f * slipSeverity;
            }
            else if (speedNorm < 0.03f && car->pedal_amount_34 > 0)
            {
                const float throttleNorm =
                    std::clamp(static_cast<float>(car->pedal_amount_34) / 255.0f, 0.0f, 1.0f);
                slipAmp =
                    static_cast<float>(Settings::WheelFFBEngineIdle) * throttleNorm * outputStrength;
                slipFreq = 15.0f + 7.0f * throttleNorm;
            }

            if (!Settings::WheelFFBUsePeriodicEffects &&
                (roadTextureEffect_ || tireSlipEffect_))
            {
                disable_periodics();
                spdlog::info(
                    "WheelFFB: hardware periodic effects disabled live; using ConstantForce fallback");
            }

            // Warm-up ramp prevents the first few garbage/settling frames from
            // producing a DD-wheel spike.
            float warmupScale = 1.0f;
            if (warmupFrames_ < WarmupFrames)
            {
                ++warmupFrames_;
                warmupScale = static_cast<float>(warmupFrames_) /
                              static_cast<float>(WarmupFrames);
            }

            float recreateScale = 1.0f;
            if (recreateRampFrames_ > 0)
            {
                recreateScale =
                    static_cast<float>(RecreateRampFrames - recreateRampFrames_) /
                    static_cast<float>(RecreateRampFrames);
                --recreateRampFrames_;
            }

            // FXT-inspired split: the centering backbone is a DirectInput
            // condition effect handled continuously by the wheel/driver. Keep
            // the game's real lateral/event signals on ConstantForce.
            // Simulation-style aligning backbone: light at parking speed,
            // progressively stronger with vehicle speed, then additionally
            // loaded by cornering force. Deep slip unloads the wheel again.
            // Keep GUID_Spring as a low-speed/near-centre stabilizer instead of
            // stacking a second high-speed SAT on top of ConstantForce. The
            // fade is a smoothstep, so crossing the blend region cannot create
            // a coefficient step or a sudden return-to-centre kick.
            const float springFadeT = std::clamp(
                (speedNorm - 0.05f) / 0.35f, 0.0f, 1.0f);
            const float springFade =
                springFadeT * springFadeT * (3.0f - 2.0f * springFadeT);
            const float springSpeed = 1.0f - 0.88f * springFade;
            // Centering Spring is an artificial low-speed stabilizer, not a tyre
            // grip estimator. Do not modulate it with lateral-G or slide state.
            const float springStrength = std::clamp(
                static_cast<float>(Settings::WheelFFBSpringStrength) * springSpeed,
                0.0f, 1.0f);

            const bool suppressSpringForImpact =
                crashImpulseTimer_ > CrashCooldownFrames;

            // Make UseHardwareSpring a real live F11 switch.  Previously
            // changing it to false after startup left the already-created
            // GUID_Spring running, which made direction testing misleading.
            if (!Settings::WheelFFBUseHardwareSpring && springEffect_)
            {
                update_spring(0.0f);
                if (springEffect_)
                    springEffect_->Stop();
                safe_release_effect(springEffect_, "hardware spring disabled");
                prevSpringCoefficient_ = 0;
                prevSpringSaturation_ = 0;
                springStrategy_ = -1;
                spdlog::info("WheelFFB: hardware spring disabled live; using software centering");
            }

            if (springEffect_)
            {
                update_spring(
                    suppressSpringForImpact
                        ? 0.0f
                        : springStrength * warmupScale * recreateScale * outputStrength);
            }

            const float softwareSpringSign = Settings::WheelFFBInvertSpring
                ? 1.0f : -1.0f;
            const float softwareSpring =
                springEffect_
                    ? 0.0f
                    : steer * softwareSpringSign * springStrength;

            // ACC/AMS2-inspired dynamic damping. It resists steering velocity
            // rather than pulling toward centre, grows with vehicle speed, and
            // relaxes when the tyres are deeply sliding so counter-steer is not
            // smothered. Prefer a native DirectInput GUID_Damper on wheels that
            // implement it and keep the old software term as a fallback.
            const float dampingSpeed =
                0.10f + 0.90f * std::pow(speedNorm, 1.30f);
            // Release steering damping from real tyre/chassis slip, never
            // from lateral-G alone. Front scrub gets a slightly smaller weight
            // than body slide so understeer is readable without making the rack
            // go completely loose in an ordinary loaded corner.
            const float damperSlipRelief = std::max(bodySlide, frontScrub * 0.75f);
            const float damperRelease = 1.0f - 0.55f * gripLoss * damperSlipRelief;
            const float dynamicDamperStrength = std::clamp(
                static_cast<float>(Settings::WheelFFBDamperStrength) *
                    dampingSpeed * damperRelease,
                0.0f, 1.0f);

            if (!Settings::WheelFFBUseHardwareDamper && damperEffect_)
            {
                update_damper(0.0f);
                if (damperEffect_)
                    damperEffect_->Stop();
                safe_release_effect(damperEffect_, "hardware damper disabled");
                prevDamperCoefficient_ = 0;
                damperStrategy_ = -1;
                spdlog::info("WheelFFB: hardware damper disabled live; using software damping");
            }

            if (damperEffect_)
                update_damper(dynamicDamperStrength * warmupScale * recreateScale * outputStrength);

            constexpr float SteerRateScale = 10.0f;
            const float damper = damperEffect_
                ? 0.0f
                : -steerRate * SteerRateScale * dynamicDamperStrength;

            // Strong sim-style pseudo self-aligning torque (SAT). OutRun does
            // not expose tyre pneumatic trail directly, so use the real steering
            // angle as torque direction and the game's smoothed lateral signal as
            // a load magnitude. This is intentionally NOT the old signed lateral
            // ConstantForce, which could partially cancel the centering spring.
            //
            // - steering angle determines restoring direction (always toward centre)
            // - vehicle speed builds SAT progressively
            // - lateral load makes a loaded corner heavier
            // - deeper drift unloads SAT so loss of grip is felt in the wheel
            const float steerAbs = std::clamp(std::abs(steer), 0.0f, 1.0f);

            // Natural pseudo-SAT: a soft 2.5% centre deadband followed by a
            // sine-shaped pneumatic-trail curve. Unlike the previous power
            // curve, tiny steering angles stay tiny instead of immediately
            // generating a large ConstantForce. The curve remains progressive
            // through normal cornering angles and naturally flattens near lock.
            const float satAngleInput = std::clamp(
                (steerAbs - 0.025f) / 0.975f, 0.0f, 1.0f);
            constexpr float HalfPi = 1.57079632679f;
            const float steerForSat = std::sin(satAngleInput * HalfPi);

            // Motion gate removes SAT at rest, then builds it continuously once
            // the car is rolling. This retains strong loaded-corner steering
            // without the old square-root-like jump at small steering angles.
            const float satMotionT = std::clamp(
                (speedNorm - 0.015f) / 0.085f, 0.0f, 1.0f);
            const float satMotionGate =
                satMotionT * satMotionT * (3.0f - 2.0f * satMotionT);
            const float satSpeed = satMotionGate *
                (0.20f + 0.80f * std::sqrt(speedNorm));

            // OutRun exposes an arcade lateral signal rather than tyre
            // pneumatic trail. Use only its magnitude as a gentle load modifier
            // and never let its sign decide the FFB direction.
            const float satLoadBoost = 0.72f + 0.38f * lateralLoadSmooth;

            // Natural SAT remains an A/B fallback, but even it now unloads from
            // actual chassis slide instead of mistaking high lateral-G for drift.
            const float naturalSlideRelief =
                1.0f - 0.25f * gripLoss * bodySlide;

            // A real steering rack loses net aligning acceleration as the wheel
            // is already rotating quickly back toward centre. Apply a bounded
            // return-rate relief to stop a DD base from whipping through zero;
            // holding a corner (rate ~= 0) still gets the full SAT magnitude.
            const bool returningToCentre = steer * steerRate < 0.0f;
            const float returnRateT = returningToCentre
                ? std::clamp(std::abs(steerRate) / 0.08f, 0.0f, 1.0f)
                : 0.0f;
            const float returnRateSmooth =
                returnRateT * returnRateT * (3.0f - 2.0f * returnRateT);
            const float satReturnRelief = 1.0f - 0.45f * returnRateSmooth;

            const float satStrength = std::clamp(
                static_cast<float>(Settings::WheelFFBSteeringWeight), 0.0f, 2.0f);
            const float naturalSatTorque =
                (steer >= 0.0f ? -1.0f : 1.0f) *
                steerForSat * satSpeed * satLoadBoost * naturalSlideRelief *
                satReturnRelief * satStrength;

            // Physics SAT force shaping lives here, separate from the vehicle
            // estimator. Front slip determines both direction and the pneumatic-
            // trail-like rise/fall. Body slide only applies a mild rear-slide
            // relief so counter-steer SAT is not double-unloaded.
            const float frontSlip = vehicleDynamics_.frontSlip();
            float physicsSatTorque = 0.0f;
            const float trailShape = WheelFFBMath::trail_shape(frontSlip);
            const float physicsLoad = 0.62f + 0.48f * lateralLoadSmooth;
            const float rearSlideRelief = 1.0f - 0.15f * gripLoss * bodySlide;
            if (vehicleDynamics_.calibrated() && vehicleDynamics_.sampleValid())
            {
                const float physicsReturnRelief =
                    WheelFFBMath::physics_return_relief(frontSlip, steerRate);

                physicsSatTorque =
                    (frontSlip > 0.0f ? -1.0f : 1.0f) *
                    trailShape * satSpeed * physicsLoad * rearSlideRelief *
                    physicsReturnRelief * satStrength;
                if (!std::isfinite(physicsSatTorque))
                    physicsSatTorque = 0.0f;
            }

            // Keep full Natural SAT while calibration/current motion is unavailable,
            // then crossfade over valid dynamics ticks. Invalid telemetry falls
            // back immediately instead of leaking stale Physics SAT values.
            const float physicsMix = vehicleDynamics_.sampleValid()
                ? vehicleDynamics_.activationBlend()
                : 0.0f;
            // Natural SAT remains the fallback throughout the activation ramp.
            // Dropping it on the calibration tick created a short SAT hole while
            // physicsMix was still near zero.
            const float physicsFallback = naturalSatTorque;
            const float selfAligningTorque = Settings::WheelFFBPhysicsSat
                ? physicsFallback + (physicsSatTorque - physicsFallback) * physicsMix
                : naturalSatTorque;

            float loadMod = 1.0f;
            if (speedHistoryIndex_ > 6)
            {
                const float oldSpeed =
                    speedHistory_[(speedHistoryIndex_ - 6) % SpeedHistoryCount];
                const float longAccelSample = (speed - oldSpeed) * 5.0f;
                if (std::isfinite(longAccelSample))
                    smoothedLongAccel_ +=
                        (longAccelSample - smoothedLongAccel_) * 0.25f;
                const float configuredWeightTransfer =
                    static_cast<float>(Settings::WheelFFBWeightTransfer);
                const float weightTransfer = std::isfinite(configuredWeightTransfer)
                    ? std::clamp(configuredWeightTransfer, 0.0f, 1.5f)
                    : 0.0f;
                loadMod = 1.0f + std::clamp(
                    -smoothedLongAccel_ * weightTransfer, -0.06f, 0.08f);
            }

            float structural = 0.0f;
            if (crashImpulseTimer_ <= CrashCooldownFrames)
                structural = (softwareSpring + selfAligningTorque) * loadMod + damper;

            float events = update_event_force();

            // Sustained steering and short events have different timing needs.
            // Keep SAT/spring/damper on the DD-safe slew path while allowing a
            // crash or gear thunk to arrive promptly without releasing that
            // slew limiter for the whole steering signal.
            const float forceDirection = Settings::WheelFFBInvertForce ? -1.0f : 1.0f;
            const float outputRamp = warmupScale * recreateScale;
            float total = structural * outputStrength * forceDirection * outputRamp;
            float eventOutput = events * outputStrength * forceDirection * outputRamp;
            if (!std::isfinite(total))
                total = 0.0f;
            if (!std::isfinite(eventOutput))
                eventOutput = 0.0f;

            // Preserve ordinary SAT linearly; bend only near the force cap.
            const float compressed = WheelFFBMath::soft_saturate(total);
            const float eventCompressed = WheelFFBMath::soft_saturate(eventOutput);

            LONG structuralLevel =
                static_cast<LONG>(compressed * static_cast<float>(DI_FFNOMINALMAX));
            const LONG eventLevel = static_cast<LONG>(
                eventCompressed * static_cast<float>(DI_FFNOMINALMAX));

            const float configuredSlew = static_cast<float>(Settings::WheelFFBSlewRate);
            const float safeSlew = std::isfinite(configuredSlew)
                ? std::clamp(configuredSlew, 0.01f, 1.0f)
                : 0.06f;
            const LONG maxSlew = static_cast<LONG>(
                safeSlew * static_cast<float>(DI_FFNOMINALMAX));

            const LONG releaseMaxSlew = std::min(
                static_cast<LONG>(DI_FFNOMINALMAX), maxSlew * 2);
            const bool oppositeTorqueDirection =
                structuralLevel != 0 && prevStructuralLevel_ != 0 &&
                (structuralLevel > 0) != (prevStructuralLevel_ > 0);

            if (oppositeTorqueDirection)
            {
                // A sign change first unloads stale torque to zero at the
                // already-approved faster release rate. Do not build the new
                // direction in the same tick.
                if (std::abs(prevStructuralLevel_) <= releaseMaxSlew)
                    structuralLevel = 0;
                else
                    structuralLevel = prevStructuralLevel_ +
                        (prevStructuralLevel_ > 0 ? -releaseMaxSlew : releaseMaxSlew);
            }
            else
            {
                const bool unloadingStructural =
                    std::abs(structuralLevel) < std::abs(prevStructuralLevel_);
                const LONG appliedMaxSlew =
                    unloadingStructural ? releaseMaxSlew : maxSlew;
                const LONG structuralDelta =
                    structuralLevel - prevStructuralLevel_;
                if (std::abs(structuralDelta) > appliedMaxSlew)
                {
                    structuralLevel = prevStructuralLevel_ +
                        (structuralDelta > 0 ? appliedMaxSlew : -appliedMaxSlew);
                }
            }
            prevStructuralLevel_ = structuralLevel;

            // Hardware periodics are preferred. If unavailable, inject a capped
            // low-frequency sine after the structural soft-knee limiter. Road/slip signals
            // share the same startup/recreate ramp as structural force.
            const float effectRampScale = warmupScale * recreateScale;
            float fallbackVibration = 0.0f;
            if (!periodicsActive_)
            {
                fallbackVibration += synth_fallback(
                    roadPhase_, roadAmp * effectRampScale, std::min(roadFreq, 15.0f));
                fallbackVibration += synth_fallback(
                    slipPhase_, slipAmp * effectRampScale, std::min(slipFreq, 15.0f));
            }

            const LONG baseSteeringLevel = std::clamp(
                structuralLevel + eventLevel,
                -static_cast<LONG>(DI_FFNOMINALMAX),
                static_cast<LONG>(DI_FFNOMINALMAX));
            const LONG vibrationRequested = static_cast<LONG>(
                fallbackVibration * static_cast<float>(DI_FFNOMINALMAX));
            const LONG vibrationHeadroom =
                static_cast<LONG>(DI_FFNOMINALMAX) - std::abs(baseSteeringLevel);
            const LONG vibrationLevel = std::clamp(
                vibrationRequested, -vibrationHeadroom, vibrationHeadroom);
            const LONG level = baseSteeringLevel + vibrationLevel;

            if (std::abs(level - prevConstantLevel_) > 15 || eventLevel != 0 ||
                (level != 0 && GetTickCount() - lastConstantWriteTick_ >= FFB_EFFECT_REFRESH_MS))
                set_constant_force(level);

            ++updateCounter_;
            if (periodicsActive_ && (updateCounter_ % 2) == 0)
            {
                update_periodic(roadTextureEffect_, roadState_, roadAmp * effectRampScale, roadFreq);
                update_periodic(tireSlipEffect_, slipState_, slipAmp * effectRampScale, slipFreq);
            }

            if (Settings::WheelFFBUsePeriodicEffects &&
                (!roadTextureEffect_ || !tireSlipEffect_) &&
                (updateCounter_ % 60) == 0 &&
                tick_reached(GetTickCount(), periodicRecreateHoldoffUntil_))
            {
                create_periodic_effects();
            }

            if (Settings::WheelFFBUseHardwareSpring &&
                !springEffect_ &&
                (updateCounter_ % 60) == 0 &&
                tick_reached(GetTickCount(), springRecreateHoldoffUntil_))
            {
                create_spring_effect();
            }

            if (Settings::WheelFFBUseHardwareDamper &&
                !damperEffect_ &&
                (updateCounter_ % 60) == 0 &&
                tick_reached(GetTickCount(), damperRecreateHoldoffUntil_))
            {
                create_damper_effect();
            }

            prevGear_ = curGear;
            prevCollisionFlags_ = stateFlags;
            maybe_log(speedNorm, steer, steerRate, lateralLoadSmooth, bodySlide, frontScrub, roughness, selfAligningTorque, level);
            const DWORD telemetryNow = GetTickCount();
            if (Settings::WheelFFBTelemetry && telemetryNow - lastTelemetryTick_ >= 100)
            {
                lastTelemetryTick_ = telemetryNow;
                spdlog::info(
                    "WheelFFB SAMPLE t={} car={} speedRaw={} speedNorm={} steer={} steerRateRaw={} steerRateFiltered={} field264={} field268={} lateralRaw={} lateralSmooth={} lateralLoad={} bodySlip={} bodySlide={} yawRate={} frontSlip={} frontScrub={} vLongTick={} vLatTick={} positionStep={} spdX={} spdY={} spdZ={} spdLenXZ={} spdCorrelation={} basis={} basisConfidence={} sampleValid={} mix={} satRaw={} satMixed={} trailShape={} satLoad={} rearSlideRelief={} springRequested={} springCoefficient={} damperRequested={} damperRelease={} damperCoefficient={} roadAmp={} slipAmp={} structural={} event={} structuralPreClip={} structuralPostClip={} eventPostClip={} postSlew={} diRequested={} diLastAccepted={} polar={} hwSpring={} hwDamper={} hwPeriodic={} gain={} invert={} invertSpring={}",
                    telemetryNow, static_cast<const void*>(car), speedRaw, speedNorm, steer, rawSteerRate, steerRate,
                    car->field_264, car->field_268, lateralRaw, smoothedLateral_, lateralLoadSmooth,
                    vehicleDynamics_.bodySlip(), bodySlide, vehicleDynamics_.yawRate(), frontSlip, frontScrub,
                    vehicleDynamics_.vLong(), vehicleDynamics_.vLat(), vehicleDynamics_.positionStep(),
                    car->spd_mb_20.x, car->spd_mb_20.y, car->spd_mb_20.z,
                    vehicleDynamics_.spdLen(), vehicleDynamics_.spdCorrelation(),
                    vehicleDynamics_.forwardAxis(), vehicleDynamics_.calibrationConfidence(),
                    vehicleDynamics_.sampleValid(), physicsMix, physicsSatTorque, selfAligningTorque,
                    trailShape, physicsLoad, rearSlideRelief, springStrength, prevSpringCoefficient_,
                    dynamicDamperStrength, damperRelease, prevDamperCoefficient_, roadAmp, slipAmp,
                    structural, events, total, compressed, eventCompressed, structuralLevel, level, prevConstantLevel_,
                    constantEffectPolar_, springEffect_ != nullptr, damperEffect_ != nullptr,
                    periodicsActive_, outputStrength, bool(Settings::WheelFFBInvertForce),
                    bool(Settings::WheelFFBInvertSpring));
                // Raw horizontal bases allow row/column x X/Z candidates to be
                // compared offline without changing the active steering model.
                spdlog::info(
                    "WheelFFB BASIS t={} tick={} state={} gear={} stage={} basisSign={} posX={} posY={} posZ={} m70_11={} m70_13={} m70_31={} m70_33={} mB0_11={} mB0_13={} mB0_31={} mB0_33={} mF0_11={} mF0_13={} mF0_31={} mF0_33={}",
                    telemetryNow, updateCounter_, stateFlags, curGear, uniqueStage, vehicleDynamics_.forwardSign(),
                    car->position_14.x, car->position_14.y, car->position_14.z,
                    car->matrix_70._11, car->matrix_70._13, car->matrix_70._31, car->matrix_70._33,
                    car->matrix_B0._11, car->matrix_B0._13, car->matrix_B0._31, car->matrix_B0._33,
                    car->matrix_F0._11, car->matrix_F0._13, car->matrix_F0._31, car->matrix_F0._33);
            }
        }

        bool output_owner_active() const
        {
            return Settings::WheelFFBEnable && initialized_ && device_ &&
                deviceAcquired_ && !deviceReinitPending_ && !panicStopped_;
        }

        void request_direction_test(int direction)
        {
            if (direction == 0)
            {
                const bool hadPendingTest = manualTestFrames_ > 0;
                manualTestFrames_ = 0;
                manualTestDirection_ = 1;
                const bool inGameplay =
                    Game::current_mode && (*Game::current_mode == STATE_GAME);
                if (hadPendingTest && initialized_ && !panicStopped_ &&
                    deviceAcquired_ && inGameplay && appActive_ && gameHwnd_ &&
                    GetForegroundWindow() == gameHwnd_)
                {
                    zero_all_forces();
                }
                if (hadPendingTest)
                    reset_signal_state();
                return;
            }

            const bool inGameplay =
                Game::current_mode && (*Game::current_mode == STATE_GAME);
            if (!inGameplay)
            {
                manualTestFrames_ = 0;
                manualTestDirection_ = 1;
                spdlog::warn(
                    "WheelFFB: ignored direction test outside gameplay; no torque was queued");
                return;
            }

            if (!Settings::WheelFFBEnable || !initialized_ || panicStopped_ ||
                !device_ || !deviceAcquired_ || !appActive_ || !gameHwnd_ ||
                GetForegroundWindow() != gameHwnd_)
            {
                manualTestFrames_ = 0;
                manualTestDirection_ = 1;
                spdlog::warn(
                    "WheelFFB: ignored direction test while FFB device was not active and foreground; no torque was queued");
                return;
            }

            manualTestDirection_ = direction < 0 ? -1 : 1;
            manualTestFrames_ = 18;
            spdlog::info(
                "WheelFFB: queued safe {} direction test at fixed 20% output",
                manualTestDirection_ < 0 ? "left" : "right");
        }

        void settings_transition()
        {
            manualTestFrames_ = 0;
            if (initialized_ && device_ && deviceAcquired_ && !panicStopped_)
                zero_all_forces();
            reset_signal_state();
            // Re-enable any hardware effect selected by the new profile on the
            // first active gameplay tick instead of waiting up to one second.
            // The normal warm-up ramp is already reset by reset_signal_state().
            updateCounter_ = 59;
            spdlog::info("WheelFFB: settings/profile transition; forces zeroed and warm-up restarted");
        }

        void service_safety()
        {
            if (panicStopped_) return;
            if (disable_live_if_needed()) return;
            if (!initialized_) return;

            const bool gameplay = Game::current_mode && *Game::current_mode == STATE_GAME;
            const bool foreground = gameHwnd_ && GetForegroundWindow() == gameHwnd_;
            if (!gameplay || !foreground ||
                ((Overlay::IsActive || Overlay::IsBindingDialogActive) && manualTestFrames_ == 0))
            {
                zero_all_forces();
                reset_signal_state();
                if ((!gameplay || !foreground) && device_ && deviceAcquired_)
                {
                    device_->Unacquire();
                    deviceAcquired_ = false;
                }
            }
        }

        void check_watchdog()
        {
            if (!initialized_ || panicStopped_ || lastUpdateTick_ == 0)
                return;

            const DWORD elapsed = GetTickCount() - lastUpdateTick_;
            if (elapsed > 250 &&
                (prevConstantLevel_ != 0 || prevSpringCoefficient_ != 0 ||
                 prevDamperCoefficient_ != 0 || roadState_.lastMagnitude != 0 ||
                 slipState_.lastMagnitude != 0))
            {
                zero_all_forces();
                reset_signal_state();
                spdlog::info("WheelFFB: watchdog zeroed forces after {}ms without game update", elapsed);
            }
        }

        void panic_stop()
        {
            if (panicStopped_)
                return;

            panicStopped_ = true;

            if (gameHwnd_)
                KillTimer(gameHwnd_, FFB_WATCHDOG_TIMER_ID);

            if (!device_)
                return;

            spdlog::info("WheelFFB: PanicStop - zeroing and releasing wheel torque");

            if (constantEffect_)
            {
                constantParams_ = {};
                DIEFFECT eff{};
                eff.dwSize = sizeof(eff);
                eff.cbTypeSpecificParams = sizeof(constantParams_);
                eff.lpvTypeSpecificParams = &constantParams_;

                HRESULT hr = constantEffect_->SetParameters(
                    &eff, DIEP_TYPESPECIFICPARAMS | DIEP_START);
                spdlog::info("WheelFFB: PanicStop constant zero => 0x{:08X}", (unsigned)hr);
                hr = constantEffect_->Stop();
                spdlog::info("WheelFFB: PanicStop constant Stop => 0x{:08X}", (unsigned)hr);
            }

            if (springEffect_)
            {
                const HRESULT springHr = springEffect_->Stop();
                spdlog::info("WheelFFB: PanicStop spring Stop => 0x{:08X}", (unsigned)springHr);
            }

            if (damperEffect_)
            {
                const HRESULT damperHr = damperEffect_->Stop();
                spdlog::info("WheelFFB: PanicStop damper Stop => 0x{:08X}", (unsigned)damperHr);
            }

            if (roadTextureEffect_)
                roadTextureEffect_->Stop();
            if (tireSlipEffect_)
                tireSlipEffect_->Stop();

            HRESULT hr = device_->SendForceFeedbackCommand(DISFFC_STOPALL);
            spdlog::info("WheelFFB: PanicStop STOPALL => 0x{:08X}", (unsigned)hr);
            hr = device_->SendForceFeedbackCommand(DISFFC_SETACTUATORSOFF);
            spdlog::info("WheelFFB: PanicStop SETACTUATORSOFF => 0x{:08X}", (unsigned)hr);
            hr = device_->SendForceFeedbackCommand(DISFFC_RESET);
            spdlog::info("WheelFFB: PanicStop RESET => 0x{:08X}", (unsigned)hr);

            // DIPROP_AUTOCENTER must be written while unacquired.
            hr = device_->Unacquire();
            deviceAcquired_ = false;
            spdlog::info("WheelFFB: PanicStop Unacquire => 0x{:08X}", (unsigned)hr);

            restore_driver_autocenter("PanicStop");
        }

    private:
        struct PeriodicState
        {
            DWORD lastMagnitude = 0;
            DWORD lastPeriod = 0;
            DWORD lastWriteTick = 0;
            double phaseCycles = 0.0;
        };

        static constexpr int SpeedHistoryCount = 8;
        static constexpr int LateralHistoryCount = 16;
        static constexpr int WarmupFrames = 30;
        static constexpr int RecreateRampFrames = 15;
        static constexpr int CrashTimerFrames = 90;
        static constexpr int CrashCooldownFrames = 80;

        struct EnumContext
        {
            WheelFFBEngine* self = nullptr;
            GUID selectedGuid{};
            std::string selectedName;
            bool found = false;
                        bool matchGuidOnly = false;
        };

        static BOOL CALLBACK enum_devices_callback(
            LPCDIDEVICEINSTANCEA instance, LPVOID context)
        {
            auto* ctx = static_cast<EnumContext*>(context);
            const std::string instanceName = lower_copy(instance->tszInstanceName);
            const std::string productName = lower_copy(instance->tszProductName);
            const std::string wanted =
                lower_copy(Settings::WheelFFBDeviceName.get().c_str());
            const std::string wantedGuid =
                lower_copy(Settings::WheelFFBDeviceGuid.get().c_str());

            if (ctx->self && tick_before(GetTickCount(), ctx->self->failedInterfaceUntil_) &&
                directinput_guid_key(instance->guidInstance) == ctx->self->failedInterfaceGuid_)
            {
                spdlog::warn(
                    "WheelFFB: temporarily skipping rejected FFB interface '{}' [{}] until retry",
                    instance->tszProductName, directinput_guid_key(instance->guidInstance));
                return DIENUM_CONTINUE;
            }

            if (is_virtual_device_name(instanceName) ||
                is_virtual_device_name(productName))
            {
                spdlog::info(
                    "WheelFFB: skipping virtual FFB device '{}'",
                    instance->tszInstanceName);
                return DIENUM_CONTINUE;
            }

            if (ctx->matchGuidOnly &&
                (wantedGuid.empty() || directinput_guid_key(instance->guidInstance) != wantedGuid))
                return DIENUM_CONTINUE;

            if (!ctx->matchGuidOnly && !wanted.empty() &&
                instanceName.find(wanted) == std::string::npos &&
                productName.find(wanted) == std::string::npos)
            {
                return DIENUM_CONTINUE;
            }

            ctx->selectedGuid = instance->guidInstance;
            ctx->selectedName = instance->tszProductName;
            ctx->found = true;
            return DIENUM_STOP;
        }

        bool disable_live_if_needed()
        {
            if (Settings::WheelFFBEnable)
                return false;

            const bool hadInitializedOutput = initialized_;
            if (initialized_)
            {
                if (device_ && deviceAcquired_)
                    zero_all_forces();
                teardown_for_reinitialize("live disable");
                initialized_ = false;
                deviceReinitPending_ = false;
                deviceFailureSince_ = 0;
                deviceReinitAfter_ = 0;
                retryAfter_ = 0;
                failedInterfaceGuid_.clear();
                failedInterfaceUntil_ = 0;
            }

            enabledLastTick_ = false;
            if (hadInitializedOutput)
                spdlog::info("WheelFFB: disabled live; output released and driver autocenter restored");
            return true;
        }

        void clear_device_failure()
        {
            deviceFailureSince_ = 0;
        }

        void request_device_reinitialize(const char* reason, HRESULT hr)
        {
            if (panicStopped_ || deviceReinitPending_)
                return;

            deviceReinitPending_ = true;
            deviceReinitAfter_ = GetTickCount();
            spdlog::warn(
                "WheelFFB: scheduling DirectInput device reinitialization after {} (0x{:08X})",
                reason, (unsigned)hr);
        }

        void note_device_failure(const char* where, HRESULT hr)
        {
            if (panicStopped_ || !initialized_)
                return;

            const DWORD now = GetTickCount();
            if (deviceFailureSince_ == 0)
            {
                deviceFailureSince_ = now;
                spdlog::warn(
                    "WheelFFB: DirectInput device access failed at {} (0x{:08X}); allowing {}ms for transient recovery",
                    where, (unsigned)hr, (unsigned)FFB_DEVICE_FAILURE_GRACE_MS);
                return;
            }

            if (now - deviceFailureSince_ >= FFB_DEVICE_FAILURE_GRACE_MS)
                request_device_reinitialize(where, hr);
        }

        bool reacquire_after_input_loss(const char* where, HRESULT originalHr)
        {
            if (!device_)
            {
                note_device_failure(where, originalHr);
                return false;
            }

            const bool inGameplay =
                Game::current_mode && (*Game::current_mode == STATE_GAME);
            if (!inGameplay)
            {
                deviceAcquired_ = false;
                return false;
            }
            if (!appActive_ || !gameHwnd_ || GetForegroundWindow() != gameHwnd_)
            {
                deviceAcquired_ = false;
                return false;
            }

            deviceAcquired_ = false;
            const HRESULT acquireHr = device_->Acquire();
            if (SUCCEEDED(acquireHr) || acquireHr == S_FALSE)
            {
                if (!appActive_ || GetForegroundWindow() != gameHwnd_)
                {
                    device_->Unacquire();
                    deviceAcquired_ = false;
                    return false;
                }

                deviceAcquired_ = true;
                const HRESULT actuatorHr =
                    device_->SendForceFeedbackCommand(DISFFC_SETACTUATORSON);
                if (FAILED(actuatorHr))
                {
                    device_->Unacquire();
                    deviceAcquired_ = false;
                    note_device_failure("reacquire SETACTUATORSON", actuatorHr);
                    return false;
                }
                clear_device_failure();
                return true;
            }

            note_device_failure(where, acquireHr);
            return false;
        }

        void release_effects_for_reinitialize()
        {
            safe_release_effect(constantEffect_, "constant during device reinit");
            safe_release_effect(springEffect_, "spring during device reinit");
            safe_release_effect(damperEffect_, "damper during device reinit");
            safe_release_effect(roadTextureEffect_, "road during device reinit");
            safe_release_effect(tireSlipEffect_, "tire during device reinit");

            roadState_ = {};
            slipState_ = {};
            periodicsActive_ = false;
            springStrategy_ = 1;
            damperStrategy_ = 1;
            periodicStrategy_ = 1;
        }

        void teardown_for_reinitialize(const char* autocenterReason = "device reinitialize")
        {
            if (device_)
            {
                __try
                {
                    device_->SendForceFeedbackCommand(DISFFC_STOPALL);
                    device_->SendForceFeedbackCommand(DISFFC_SETACTUATORSOFF);
                }
                __except (EXCEPTION_EXECUTE_HANDLER)
                {
                    spdlog::warn(
                        "WheelFFB: exception stopping stale DirectInput device during reinit (0x{:X})",
                        GetExceptionCode());
                }
            }

            release_effects_for_reinitialize();
            deviceAcquired_ = false;

            restore_driver_autocenter(autocenterReason);
            release_device();
            release_directinput();
            selectedName_.clear();
            selectedGuid_ = {};
            constantRecreateHoldoffUntil_ = 0;
            periodicRecreateHoldoffUntil_ = 0;
            springRecreateHoldoffUntil_ = 0;
            damperRecreateHoldoffUntil_ = 0;
            reset_signal_state();
        }

        static BOOL CALLBACK enum_actuator_axis_callback(
            LPCDIDEVICEOBJECTINSTANCEA object, LPVOID context)
        {
            auto* self = static_cast<WheelFFBEngine*>(context);
            if (!self || !object)
                return DIENUM_CONTINUE;
            if ((object->dwType & DIDFT_FFACTUATOR) != 0 && self->actuatorAxes_.size() < 2)
                self->actuatorAxes_.push_back(object->dwOfs);
            return DIENUM_CONTINUE;
        }

        DWORD primary_actuator_axis() const
        {
            return actuatorAxes_.empty() ? DIJOFS_X : actuatorAxes_.front();
        }

        void mark_selected_interface_failed(const char* reason, HRESULT hr)
        {
            failedInterfaceGuid_ = directinput_guid_key(selectedGuid_);
            failedInterfaceUntil_ = GetTickCount() + 5000;
            spdlog::warn(
                "WheelFFB: interface '{}' [{}] rejected {}; will retry this interface (0x{:08X})",
                selectedName_, failedInterfaceGuid_, reason, (unsigned)hr);
        }

        bool initialize()
        {
            retryAfter_ = 0;

            HRESULT hr = DirectInput8Create(
                GetModuleHandleW(nullptr),
                DIRECTINPUT_VERSION,
                IID_IDirectInput8A,
                reinterpret_cast<void**>(&directInput_),
                nullptr);

            if (FAILED(hr) || !directInput_)
            {
                spdlog::error(
                    "WheelFFB: DirectInput8Create failed (0x{:08X})",
                    (unsigned)hr);
                return false;
            }

            EnumContext ctx{};
            ctx.self = this;
            const std::string configuredGuid =
                lower_copy(Settings::WheelFFBDeviceGuid.get().c_str());

            if (!configuredGuid.empty())
            {
                ctx.matchGuidOnly = true;
                hr = directInput_->EnumDevices(
                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,
                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);
                if (FAILED(hr))
                {
                    release_directinput();
                    return false;
                }
                if (!ctx.found)
                {
                    spdlog::warn(
                        "WheelFFB: saved GUID unavailable or rejected; select its FFB interface explicitly in Force Feedback");
                    release_directinput();
                    return false;
                }
            }

            if (!ctx.found)
            {
                hr = directInput_->EnumDevices(
                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,
                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);
            }

            if (FAILED(hr) || !ctx.found)
            {
                spdlog::error(
                    "WheelFFB: no FFB wheel matched DeviceName='{}'",
                    Settings::WheelFFBDeviceName.get());
                release_directinput();
                return false;
            }

            selectedGuid_ = ctx.selectedGuid;
            selectedName_ = ctx.selectedName;
            selectedConfiguredGuid_ = lower_copy(Settings::WheelFFBDeviceGuid.get().c_str());
            selectedConfiguredName_ = lower_copy(Settings::WheelFFBDeviceName.get().c_str());
            spdlog::info("WheelFFB: selected DirectInput identity '{}' / '{}'",
                selectedName_, directinput_guid_key(selectedGuid_));

            hr = directInput_->CreateDevice(selectedGuid_, &device_, nullptr);
            if (FAILED(hr) || !device_)
            {
                const HRESULT failHr = FAILED(hr) ? hr : E_FAIL;
                mark_selected_interface_failed("CreateDevice", failHr);
                spdlog::error(
                    "WheelFFB: CreateDevice('{}') failed (0x{:08X})",
                    selectedName_, (unsigned)failHr);
                release_directinput();
                return false;
            }

            DIDEVCAPS caps{};
            caps.dwSize = sizeof(caps);
            hr = device_->GetCapabilities(&caps);
            if (FAILED(hr))
            {
                mark_selected_interface_failed("GetCapabilities", hr);
                spdlog::error(
                    "WheelFFB: GetCapabilities('{}') failed (0x{:08X})",
                    selectedName_, (unsigned)hr);
                release_device();
                release_directinput();
                return false;
            }

            if ((caps.dwFlags & DIDC_FORCEFEEDBACK) == 0)
            {
                mark_selected_interface_failed("force-feedback capability", E_NOINTERFACE);
                spdlog::error("WheelFFB: '{}' does not report force-feedback capability", selectedName_);
                release_device();
                release_directinput();
                return false;
            }

            hr = device_->SetDataFormat(&c_dfDIJoystick2);
            if (FAILED(hr))
            {
                mark_selected_interface_failed("SetDataFormat", hr);
                spdlog::error("WheelFFB: SetDataFormat failed (0x{:08X})", (unsigned)hr);
                release_device();
                release_directinput();
                return false;
            }

            gameHwnd_ = Game::GameHwnd();
            if (!gameHwnd_)
            {
                spdlog::error("WheelFFB: game window not available yet");
                release_device();
                release_directinput();
                return false;
            }

            // initialize() can run while the game is already in the background,
            // before our WM_ACTIVATEAPP subclass has seen a focus transition.
            // Seed appActive_ from the real foreground window so an exclusive
            // DD device is never acquired merely because the default was true.
            appActive_ = (GetForegroundWindow() == gameHwnd_);
            if (!appActive_)
            {
                release_device();
                release_directinput();
                retryAfter_ = GetTickCount() + FFB_DEVICE_RETRY_MS;
                return false;
            }

            hr = device_->SetCooperativeLevel(
                gameHwnd_,
                DISCL_EXCLUSIVE | DISCL_BACKGROUND);

            if (FAILED(hr))
            {
                mark_selected_interface_failed("SetCooperativeLevel", hr);
                spdlog::error(
                    "WheelFFB: SetCooperativeLevel(EXCLUSIVE|BACKGROUND) failed (0x{:08X})",
                    (unsigned)hr);
                release_device();
                release_directinput();
                return false;
            }

            DIPROPDWORD deviceGain{};
            deviceGain.diph.dwSize = sizeof(deviceGain);
            deviceGain.diph.dwHeaderSize = sizeof(DIPROPHEADER);
            deviceGain.diph.dwHow = DIPH_DEVICE;
            deviceGain.dwData = DI_FFNOMINALMAX;
            const HRESULT gainHr = device_->SetProperty(DIPROP_FFGAIN, &deviceGain.diph);
            if (FAILED(gainHr))
                spdlog::warn("WheelFFB: nominal device gain rejected (0x{:08X})", (unsigned)gainHr);

            // Disable driver centering before acquiring. Restored by PanicStop.
            DIPROPDWORD autocenter{};
            autocenter.diph.dwSize = sizeof(autocenter);
            autocenter.diph.dwHeaderSize = sizeof(DIPROPHEADER);
            autocenter.diph.dwObj = 0;
            autocenter.diph.dwHow = DIPH_DEVICE;
            autocenterRestoreKnown_ = SUCCEEDED(
                device_->GetProperty(DIPROP_AUTOCENTER, &autocenter.diph));
            if (autocenterRestoreKnown_)
            {
                originalAutocenter_ = autocenter.dwData;
                autocenter.dwData = DIPROPAUTOCENTER_OFF;
                hr = device_->SetProperty(DIPROP_AUTOCENTER, &autocenter.diph);
                if (FAILED(hr))
                    spdlog::warn("WheelFFB: disabling driver autocenter failed (0x{:08X})", (unsigned)hr);
                else
                    driverAutocenterDisabled_ = true;
            }
            else
            {
                spdlog::warn(
                    "WheelFFB: driver autocenter state could not be read; leaving it unchanged for safe restoration semantics");
            }

            hr = device_->Acquire();
            if (FAILED(hr))
            {
                mark_selected_interface_failed("Acquire", hr);
                spdlog::error("WheelFFB: Acquire('{}') failed (0x{:08X})", selectedName_, (unsigned)hr);
                release_device();
                release_directinput();
                return false;
            }
            deviceAcquired_ = true;

            const HRESULT actuatorOnHr =
                device_->SendForceFeedbackCommand(DISFFC_SETACTUATORSON);
            if (FAILED(actuatorOnHr))
            {
                mark_selected_interface_failed("initial SETACTUATORSON", actuatorOnHr);
                spdlog::error(
                    "WheelFFB: SETACTUATORSON during initialization failed (0x{:08X})",
                    (unsigned)actuatorOnHr);
                release_device();
                release_directinput();
                return false;
            }

            actuatorAxes_.clear();
            const HRESULT axisEnumHr = device_->EnumObjects(
                enum_actuator_axis_callback, this, DIDFT_AXIS);
            if (FAILED(axisEnumHr) || actuatorAxes_.empty())
            {
                actuatorAxes_.clear();
                actuatorAxes_.push_back(DIJOFS_X);
                spdlog::warn(
                    "WheelFFB: no explicit DIDFT_FFACTUATOR axis reported; using DIJOFS_X fallback");
            }
            else
            {
                spdlog::info(
                    "WheelFFB: detected {} force actuator axis/axes; primary offset={}",
                    actuatorAxes_.size(), (unsigned)actuatorAxes_.front());
            }

            if (!create_constant_effect())
            {
                release_device();
                release_directinput();
                return false;
            }

            {
                const std::string actualGuid = directinput_guid_key(selectedGuid_);
                if (lower_copy(Settings::WheelFFBDeviceGuid.get().c_str()) != actualGuid)
                {
                    Settings::WheelFFBDeviceGuid = actualGuid;
                    selectedConfiguredGuid_ = actualGuid;
                    spdlog::info(
                        "WheelFFB: pinned working force interface GUID '{}' after capability validation",
                        actualGuid);
                }
            }

            if (Settings::WheelFFBUseHardwareSpring && !create_spring_effect())
            {
                spdlog::warn(
                    "WheelFFB: hardware GUID_Spring unavailable; retaining software spring fallback");
            }

            if (Settings::WheelFFBUseHardwareDamper && !create_damper_effect())
            {
                spdlog::warn(
                    "WheelFFB: hardware GUID_Damper unavailable; retaining software damper fallback");
            }

            create_periodic_effects();
            install_exit_guards();

            initialized_ = true;
            deviceReinitPending_ = false;
            deviceFailureSince_ = 0;
            deviceReinitAfter_ = 0;
            retryAfter_ = 0;
            reset_signal_state();

            failedInterfaceGuid_.clear();
            failedInterfaceUntil_ = 0;

            spdlog::info(
                "WheelFFB: ready on '{}' (DirectInput COM, axes={}, buttons={}, global={}%, spring={}, damper={})",
                selectedName_,
                caps.dwAxes,
                caps.dwButtons,
                static_cast<int>(static_cast<float>(Settings::WheelFFBGlobalStrength) * 100.0f),
                springEffect_ ? "GUID_Spring" : "software",
                damperEffect_ ? "GUID_Damper" : "software");

            return true;
        }

        float read_game_steering() const
        {
            if (Settings::UseNewInput)
            {
                const float steering = InputManager_SteeringValue();
                return std::isfinite(steering)
                    ? std::clamp(steering, -1.0f, 1.0f)
                    : 0.0f;
            }

            using GetVolumeFn = int(__cdecl*)(ADChannel);
            auto getVolume = Module::fn_ptr<GetVolumeFn>(0x53720);
            if (!getVolume)
                return 0.0f;

            const int raw = getVolume(ADChannel::Steering);
            return std::clamp(raw / 127.0f, -1.0f, 1.0f);
        }

        bool create_constant_effect()
        {
            if (!device_)
                return false;

            safe_release_effect(constantEffect_, "constant before create");
            constantEffectPolar_ = false;

            DWORD axes[2] = {
                primary_actuator_axis(),
                actuatorAxes_.size() > 1 ? actuatorAxes_[1] : primary_actuator_axis()
            };
            LONG directions[2] = { 9000L, 0L };
            constantParams_ = {};
            constantParams_.lMagnitude = 0;

            DIEFFECT effect{};
            effect.dwSize = sizeof(effect);
            effect.dwDuration = FFB_EFFECT_LEASE_US;
            effect.dwSamplePeriod = 0;
            effect.dwGain = DI_FFNOMINALMAX;
            effect.dwTriggerButton = DIEB_NOTRIGGER;
            effect.dwTriggerRepeatInterval = 0;
            effect.rgdwAxes = axes;
            effect.rglDirection = directions;
            effect.cbTypeSpecificParams = sizeof(constantParams_);
            effect.lpvTypeSpecificParams = &constantParams_;

            HRESULT hr = E_FAIL;
            if (actuatorAxes_.size() > 1)
            {
                effect.dwFlags = DIEFF_POLAR | DIEFF_OBJECTOFFSETS;
                effect.cAxes = 2;
                hr = device_->CreateEffect(GUID_ConstantForce, &effect, &constantEffect_, nullptr);
                if (SUCCEEDED(hr) && constantEffect_)
                {
                    constantEffectPolar_ = true;
                    prevConstantLevel_ = 0;
                    lastConstantWriteTick_ = 0;
                    spdlog::info("WheelFFB: ConstantForce created with 2-axis POLAR actuator encoding");
                    return true;
                }

                safe_release_effect(constantEffect_, "failed POLAR constant");
                spdlog::warn(
                    "WheelFFB: 2-axis POLAR ConstantForce rejected (0x{:08X}); trying one-axis CARTESIAN",
                    (unsigned)hr);
            }

            effect.dwFlags = DIEFF_CARTESIAN | DIEFF_OBJECTOFFSETS;
            effect.cAxes = 1;
            directions[0] = 1;
            hr = device_->CreateEffect(GUID_ConstantForce, &effect, &constantEffect_, nullptr);
            if (FAILED(hr) || !constantEffect_)
            {
                mark_selected_interface_failed("ConstantForce creation", hr);
                spdlog::error("WheelFFB: CreateEffect(ConstantForce) failed (0x{:08X})", (unsigned)hr);
                return false;
            }

            constantEffectPolar_ = false;
            prevConstantLevel_ = 0;
            lastConstantWriteTick_ = 0;
            spdlog::info("WheelFFB: ConstantForce created with 1-axis CARTESIAN fallback");
            return true;
        }

        bool create_spring_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareSpring)
                return false;

            DWORD axes[1] = { primary_actuator_axis() };
            LONG directions[1] = { 1 };

            const float configuredSaturation =
                static_cast<float>(Settings::WheelFFBSpringSaturation);
            const float safeSaturation = std::isfinite(configuredSaturation)
                ? std::clamp(configuredSaturation, 0.1f, 1.0f)
                : 0.775f;
            const DWORD saturation = static_cast<DWORD>(
                safeSaturation * static_cast<float>(DI_FFNOMINALMAX));

            springParams_ = {};
            springParams_.lOffset = 0;
            springParams_.lPositiveCoefficient = 0;
            springParams_.lNegativeCoefficient = 0;
            springParams_.dwPositiveSaturation = saturation;
            springParams_.dwNegativeSaturation = saturation;
            springParams_.lDeadBand = 0;

            DIEFFECT effect{};
            effect.dwSize = sizeof(effect);
            effect.dwFlags = DIEFF_CARTESIAN | DIEFF_OBJECTOFFSETS;
            effect.dwDuration = FFB_EFFECT_LEASE_US;
            effect.dwSamplePeriod = 0;
            effect.dwGain = DI_FFNOMINALMAX;
            effect.dwTriggerButton = DIEB_NOTRIGGER;
            effect.dwTriggerRepeatInterval = 0;
            effect.cAxes = 1;
            effect.rgdwAxes = axes;
            effect.rglDirection = directions;
            effect.cbTypeSpecificParams = sizeof(springParams_);
            effect.lpvTypeSpecificParams = &springParams_;

            HRESULT hr = device_->CreateEffect(
                GUID_Spring, &effect, &springEffect_, nullptr);

            if (FAILED(hr) || !springEffect_)
            {
                spdlog::warn(
                    "WheelFFB: CreateEffect(GUID_Spring) failed (0x{:08X})",
                    (unsigned)hr);
                springRecreateHoldoffUntil_ = GetTickCount() + 1000;
                return false;
            }

            hr = springEffect_->Start(1, 0);
            if (FAILED(hr))
            {
                spdlog::warn(
                    "WheelFFB: GUID_Spring initial Start failed (0x{:08X}); SetParameters will retry with DIEP_START",
                    (unsigned)hr);
            }

            prevSpringCoefficient_ = 0;
            prevSpringSaturation_ = saturation;
            springStrategy_ = 1; // Always include DIEP_START on dynamic updates.

            spdlog::info(
                "WheelFFB: GUID_Spring created (saturation={} / {}, R3 normal sign=positive, independent direction toggle)",
                static_cast<unsigned>(saturation),
                DI_FFNOMINALMAX);
            return true;
        }

        void update_spring(float strength)
        {
            if (!springEffect_ || !device_ || panicStopped_)
                return;

            const float safeStrength = std::isfinite(strength)
                ? std::clamp(strength, 0.0f, 1.0f)
                : 0.0f;
            const LONG coefficientMagnitude = static_cast<LONG>(
                safeStrength * static_cast<float>(DI_FFNOMINALMAX));

            // R3 hardware testing established positive condition coefficients
            // as the normal centering sign for this backend.  Keep this independent
            // from ConstantForce inversion so fixing corner-force direction can
            // never accidentally turn the centering spring into a runaway force.
            const LONG coefficient = Settings::WheelFFBInvertSpring
                ? -coefficientMagnitude
                : coefficientMagnitude;
            const float configuredSaturation =
                static_cast<float>(Settings::WheelFFBSpringSaturation);
            const float safeSaturation = std::isfinite(configuredSaturation)
                ? std::clamp(configuredSaturation, 0.1f, 1.0f)
                : 0.775f;
            const DWORD saturation = static_cast<DWORD>(
                safeSaturation * static_cast<float>(DI_FFNOMINALMAX));

            const bool silence =
                coefficient == 0 && prevSpringCoefficient_ != 0;
            const bool coefficientChanged =
                std::abs(coefficient - prevSpringCoefficient_) > 40;
            const bool saturationChanged =
                saturation != prevSpringSaturation_;

            const bool refresh = coefficient != 0 &&
                GetTickCount() - lastSpringWriteTick_ >= FFB_EFFECT_REFRESH_MS;
            if (!silence && !coefficientChanged && !saturationChanged && !refresh)
                return;

            springParams_ = {};
            springParams_.lOffset = 0;
            springParams_.lPositiveCoefficient = coefficient;
            springParams_.lNegativeCoefficient = coefficient;
            springParams_.dwPositiveSaturation = saturation;
            springParams_.dwNegativeSaturation = saturation;
            springParams_.lDeadBand = 0;

            DIEFFECT params{};
            params.dwSize = sizeof(params);
            params.cbTypeSpecificParams = sizeof(springParams_);
            params.lpvTypeSpecificParams = &springParams_;

            DWORD flags = DIEP_TYPESPECIFICPARAMS |
                (springStrategy_ == 1 ? DIEP_START : 0);

            HRESULT hr = springEffect_->SetParameters(&params, flags);

            if (springStrategy_ == -1)
            {
                if (SUCCEEDED(hr))
                {
                    springStrategy_ = 0;
                    spdlog::info("WheelFFB: GUID_Spring updates work without DIEP_START");
                }
                else
                {
                    hr = springEffect_->SetParameters(
                        &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
                    if (SUCCEEDED(hr))
                    {
                        springStrategy_ = 1;
                        spdlog::info("WheelFFB: GUID_Spring driver requires DIEP_START");
                    }
                }
            }

            if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
            {
                if (reacquire_after_input_loss("GUID_Spring", hr))
                    hr = springEffect_->SetParameters(
                        &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
            }

            if (FAILED(hr))
            {
                spdlog::warn(
                    "WheelFFB: GUID_Spring update failed (0x{:08X}); returning to software spring fallback",
                    (unsigned)hr);
                springEffect_->Stop();
                safe_release_effect(springEffect_, "stale spring");
                prevSpringCoefficient_ = 0;
                prevSpringSaturation_ = 0;
                springStrategy_ = -1;
                springRecreateHoldoffUntil_ = GetTickCount() + 1000;
                return;
            }

            clear_device_failure();
            prevSpringCoefficient_ = coefficient;
            prevSpringSaturation_ = saturation;
            lastSpringWriteTick_ = GetTickCount();
        }

        bool create_damper_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareDamper)
                return false;

            DWORD axes[1] = { primary_actuator_axis() };
            LONG directions[1] = { 1 };
            damperParams_ = {};
            damperParams_.lOffset = 0;
            damperParams_.lPositiveCoefficient = 0;
            damperParams_.lNegativeCoefficient = 0;
            damperParams_.dwPositiveSaturation = DI_FFNOMINALMAX;
            damperParams_.dwNegativeSaturation = DI_FFNOMINALMAX;
            damperParams_.lDeadBand = 0;

            DIEFFECT effect{};
            effect.dwSize = sizeof(effect);
            effect.dwFlags = DIEFF_CARTESIAN | DIEFF_OBJECTOFFSETS;
            effect.dwDuration = FFB_EFFECT_LEASE_US;
            effect.dwSamplePeriod = 0;
            effect.dwGain = DI_FFNOMINALMAX;
            effect.dwTriggerButton = DIEB_NOTRIGGER;
            effect.dwTriggerRepeatInterval = 0;
            effect.cAxes = 1;
            effect.rgdwAxes = axes;
            effect.rglDirection = directions;
            effect.cbTypeSpecificParams = sizeof(damperParams_);
            effect.lpvTypeSpecificParams = &damperParams_;

            HRESULT hr = device_->CreateEffect(
                GUID_Damper, &effect, &damperEffect_, nullptr);
            if (FAILED(hr) || !damperEffect_)
            {
                spdlog::warn(
                    "WheelFFB: CreateEffect(GUID_Damper) failed (0x{:08X})",
                    (unsigned)hr);
                damperRecreateHoldoffUntil_ = GetTickCount() + 1000;
                return false;
            }

            hr = damperEffect_->Start(1, 0);
            if (FAILED(hr))
                spdlog::warn("WheelFFB: GUID_Damper initial Start failed (0x{:08X})", (unsigned)hr);

            prevDamperCoefficient_ = 0;
            damperStrategy_ = 1; // Always include DIEP_START after menu reacquire.
            spdlog::info("WheelFFB: GUID_Damper created (dynamic speed/grip damping)");
            return true;
        }

        void update_damper(float strength)
        {
            if (!damperEffect_ || !device_ || panicStopped_)
                return;

            // Positive coefficients are the conventional DirectInput condition
            // representation for GUID_Damper; the effect type itself applies
            // force opposite steering velocity.
            const float safeStrength = std::isfinite(strength)
                ? std::clamp(strength, 0.0f, 1.0f)
                : 0.0f;
            const LONG coefficient = static_cast<LONG>(
                safeStrength * static_cast<float>(DI_FFNOMINALMAX));

            const bool silence = coefficient == 0 && prevDamperCoefficient_ != 0;
            const bool changed = std::abs(coefficient - prevDamperCoefficient_) > 40;
            const bool refresh = coefficient != 0 &&
                GetTickCount() - lastDamperWriteTick_ >= FFB_EFFECT_REFRESH_MS;
            if (!silence && !changed && !refresh)
                return;

            damperParams_ = {};
            damperParams_.lOffset = 0;
            damperParams_.lPositiveCoefficient = coefficient;
            damperParams_.lNegativeCoefficient = coefficient;
            damperParams_.dwPositiveSaturation = DI_FFNOMINALMAX;
            damperParams_.dwNegativeSaturation = DI_FFNOMINALMAX;
            damperParams_.lDeadBand = 0;

            DIEFFECT params{};
            params.dwSize = sizeof(params);
            params.cbTypeSpecificParams = sizeof(damperParams_);
            params.lpvTypeSpecificParams = &damperParams_;

            DWORD flags = DIEP_TYPESPECIFICPARAMS |
                (damperStrategy_ == 1 ? DIEP_START : 0);
            HRESULT hr = damperEffect_->SetParameters(&params, flags);

            if (damperStrategy_ == -1)
            {
                if (SUCCEEDED(hr))
                {
                    damperStrategy_ = 0;
                    spdlog::info("WheelFFB: GUID_Damper updates work without DIEP_START");
                }
                else
                {
                    hr = damperEffect_->SetParameters(
                        &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
                    if (SUCCEEDED(hr))
                    {
                        damperStrategy_ = 1;
                        spdlog::info("WheelFFB: GUID_Damper driver requires DIEP_START");
                    }
                }
            }

            if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
            {
                if (reacquire_after_input_loss("GUID_Damper", hr))
                    hr = damperEffect_->SetParameters(
                        &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
            }

            if (FAILED(hr))
            {
                spdlog::warn(
                    "WheelFFB: GUID_Damper update failed (0x{:08X}); using software fallback",
                    (unsigned)hr);
                damperEffect_->Stop();
                safe_release_effect(damperEffect_, "stale damper");
                prevDamperCoefficient_ = 0;
                damperStrategy_ = -1;
                damperRecreateHoldoffUntil_ = GetTickCount() + 1000;
                return;
            }

            clear_device_failure();
            prevDamperCoefficient_ = coefficient;
            lastDamperWriteTick_ = GetTickCount();
        }

        IDirectInputEffect* create_periodic_effect(const char* label, float initialHz)
        {
            if (!device_)
                return nullptr;

            DWORD axes[1] = { primary_actuator_axis() };
            LONG directions[1] = { 1 };
            DIPERIODIC& periodic = (std::strcmp(label, "RoadTexture") == 0)
                ? roadPeriodicParams_
                : tireSlipPeriodicParams_;
            periodic = {};
            periodic.dwMagnitude = 0;
            periodic.lOffset = 0;
            periodic.dwPhase = 0;
            periodic.dwPeriod = static_cast<DWORD>(1000000.0f / initialHz);

            DIEFFECT effect{};
            effect.dwSize = sizeof(effect);
            effect.dwFlags = DIEFF_CARTESIAN | DIEFF_OBJECTOFFSETS;
            effect.dwDuration = FFB_EFFECT_LEASE_US;
            effect.dwGain = DI_FFNOMINALMAX;
            effect.dwTriggerButton = DIEB_NOTRIGGER;
            effect.cAxes = 1;
            effect.rgdwAxes = axes;
            effect.rglDirection = directions;
            effect.cbTypeSpecificParams = sizeof(periodic);
            effect.lpvTypeSpecificParams = &periodic;

            IDirectInputEffect* result = nullptr;
            HRESULT hr = device_->CreateEffect(
                GUID_Sine, &effect, &result, nullptr);

            if (FAILED(hr) || !result)
            {
                spdlog::warn(
                    "WheelFFB: CreateEffect({}/GUID_Sine) failed (0x{:08X})",
                    label, (unsigned)hr);
                return nullptr;
            }

            hr = result->Start(1, 0);
            if (FAILED(hr))
                spdlog::warn("WheelFFB: {} initial Start failed (0x{:08X})", label, (unsigned)hr);

            spdlog::info("WheelFFB: {} hardware sine created", label);
            return result;
        }

        void create_periodic_effects()
        {
            if (!Settings::WheelFFBUsePeriodicEffects || !device_)
            {
                periodicsActive_ = false;
                return;
            }

            if (!roadTextureEffect_)
                roadTextureEffect_ = create_periodic_effect("RoadTexture", 30.0f);
            if (!tireSlipEffect_)
                tireSlipEffect_ = create_periodic_effect("TireSlip", 35.0f);

            roadState_ = {};
            slipState_ = {};
            periodicsActive_ =
                roadTextureEffect_ != nullptr && tireSlipEffect_ != nullptr;

            if (!periodicsActive_)
            {
                // Treat the two sines atomically. A half-created pair plus the
                // software fallback would double one signal and distort tuning.
                disable_periodics();
                periodicRecreateHoldoffUntil_ = GetTickCount() + 500;
                spdlog::warn(
                    "WheelFFB: complete hardware periodic pair unavailable; using ConstantForce fallback for both signals");
            }
        }

        void update_periodic(
            IDirectInputEffect*& effect,
            PeriodicState& state,
            float magnitude,
            float frequency)
        {
            if (!effect || panicStopped_)
                return;

            // Very small hardware-sine magnitudes can remain audible on DD
            // bases.  Snap them to zero, and update much more aggressively on
            // falling magnitude so an off-road effect cannot remain latched
            // after the car returns to asphalt.
            const float magnitudeClamped = std::isfinite(magnitude)
                ? std::clamp(magnitude, 0.0f, 1.0f)
                : 0.0f;
            const DWORD mag = magnitudeClamped < 0.01f
                ? 0u
                : static_cast<DWORD>(
                    magnitudeClamped * static_cast<float>(DI_FFNOMINALMAX));
            frequency = std::isfinite(frequency)
                ? std::clamp(frequency, 1.0f, 100.0f)
                : 30.0f;
            const DWORD period = static_cast<DWORD>(1000000.0f / frequency);

            const long magDelta = std::abs(
                static_cast<long>(mag) - static_cast<long>(state.lastMagnitude));
            const bool silence = mag == 0 && state.lastMagnitude != 0;
            const bool magChanged =
                magDelta > 60 ||
                (state.lastMagnitude > 0 &&
                 magDelta * 5 > static_cast<long>(state.lastMagnitude));
            const bool periodChanged =
                state.lastPeriod != 0 &&
                std::abs(static_cast<long>(period) - static_cast<long>(state.lastPeriod)) * 10 >
                    static_cast<long>(state.lastPeriod);

            const DWORD periodicNow = GetTickCount();
            const bool refresh = mag != 0 &&
                periodicNow - state.lastWriteTick >= FFB_EFFECT_REFRESH_MS;
            if (!silence && !magChanged && !periodChanged && !refresh)
                return;

            DIPERIODIC& periodic = (effect == roadTextureEffect_)
                ? roadPeriodicParams_
                : tireSlipPeriodicParams_;
            periodic = {};
            periodic.dwMagnitude = mag;
            periodic.dwPeriod = period;
            // DIEP_START restarts the lease. Advance phase so refreshing an
            // unchanged envelope does not deliberately restart at phase zero.
            if (state.lastPeriod != 0)
                state.phaseCycles = std::fmod(state.phaseCycles +
                    double(periodicNow - state.lastWriteTick) * 1000.0 / state.lastPeriod, 1.0);
            periodic.dwPhase = static_cast<DWORD>(state.phaseCycles * 36000.0);

            DIEFFECT params{};
            params.dwSize = sizeof(params);
            params.cbTypeSpecificParams = sizeof(periodic);
            params.lpvTypeSpecificParams = &periodic;

            DWORD flags = DIEP_TYPESPECIFICPARAMS |
                (periodicStrategy_ == 1 ? DIEP_START : 0);

            HRESULT hr = effect->SetParameters(&params, flags);

            if (periodicStrategy_ == -1)
            {
                if (SUCCEEDED(hr))
                {
                    periodicStrategy_ = 0;
                    spdlog::info("WheelFFB: periodic updates work without DIEP_START");
                }
                else
                {
                    hr = effect->SetParameters(
                        &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
                    if (SUCCEEDED(hr))
                    {
                        periodicStrategy_ = 1;
                        spdlog::info("WheelFFB: periodic driver requires DIEP_START");
                    }
                }
            }

            if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
            {
                if (reacquire_after_input_loss("GUID_Sine periodic", hr))
                    hr = effect->SetParameters(
                        &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
            }

            if (FAILED(hr))
            {
                spdlog::warn(
                    "WheelFFB: periodic update failed (0x{:08X}); falling back to ConstantForce vibration",
                    (unsigned)hr);
                disable_periodics();
                periodicRecreateHoldoffUntil_ = GetTickCount() + 500;
                return;
            }

            clear_device_failure();
            state.lastMagnitude = mag;
            state.lastPeriod = period;
            state.lastWriteTick = periodicNow;
        }

        void disable_periodics()
        {
            if (roadTextureEffect_)
                roadTextureEffect_->Stop();
            if (tireSlipEffect_)
                tireSlipEffect_->Stop();

            safe_release_effect(roadTextureEffect_, "road texture");
            safe_release_effect(tireSlipEffect_, "tire slip");

            roadState_ = {};
            slipState_ = {};
            periodicsActive_ = false;
        }

        void set_constant_force(LONG requestedLevel)
        {
            if (!device_ || panicStopped_)
                return;

            requestedLevel = std::clamp(
                requestedLevel,
                -static_cast<LONG>(DI_FFNOMINALMAX),
                static_cast<LONG>(DI_FFNOMINALMAX));

            constantParams_ = {};
            LONG directions[2] = { 1L, 0L };
            DWORD flags = DIEP_TYPESPECIFICPARAMS | DIEP_START;

            DIEFFECT params{};
            params.dwSize = sizeof(params);
            params.cbTypeSpecificParams = sizeof(constantParams_);
            params.lpvTypeSpecificParams = &constantParams_;

            if (constantEffectPolar_)
            {
                constantParams_.lMagnitude = std::abs(requestedLevel);
                directions[0] = requestedLevel < 0 ? 27000L : 9000L;
                params.dwFlags = DIEFF_POLAR | DIEFF_OBJECTOFFSETS;
                params.cAxes = 2;
                params.rglDirection = directions;
                flags |= DIEP_DIRECTION;
            }
            else
            {
                constantParams_.lMagnitude = requestedLevel;
            }

            HRESULT hr = E_FAIL;
            if (constantEffect_)
                hr = constantEffect_->SetParameters(&params, flags);

            if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
            {
                if (reacquire_after_input_loss("ConstantForce", hr) && constantEffect_)
                    hr = constantEffect_->SetParameters(&params, flags);
            }

            if (hr == E_HANDLE || hr == DIERR_NOTDOWNLOADED || !constantEffect_)
            {
                safe_release_effect(constantEffect_, "stale constant");
                const DWORD now = GetTickCount();
                if (tick_before(now, constantRecreateHoldoffUntil_))
                    return;

                if (!create_constant_effect())
                {
                    constantRecreateHoldoffUntil_ = now + 500;
                    request_device_reinitialize("ConstantForce recreation rejected interface", hr);
                    return;
                }

                recreateRampFrames_ = RecreateRampFrames;
                prevConstantLevel_ = 0;
                prevStructuralLevel_ = 0;
                spdlog::info("WheelFFB: recreated ConstantForce after handle loss; ramping in");
                return;
            }

            if (FAILED(hr))
            {
                request_device_reinitialize("ConstantForce output failed", hr);
                spdlog::warn("WheelFFB: constant force update failed (0x{:08X})", (unsigned)hr);
                return;
            }

            clear_device_failure();
            prevConstantLevel_ = requestedLevel;
            lastConstantWriteTick_ = GetTickCount();
        }

        void update_crash_detection(float speed, uint32_t stateFlags)
        {
            if (crashImpulseTimer_ <= 0 && speedHistoryIndex_ > 6)
            {
                const float oldSpeed =
                    speedHistory_[(speedHistoryIndex_ - 6) % SpeedHistoryCount];
                const float speedDrop = oldSpeed - speed;

                if (speedDrop > 0.03f && speed > 0.10f)
                {
                    const float lateralBeforeImpact =
                        lateralHistoryIndex_ > 8
                            ? lateralHistory_[(lateralHistoryIndex_ - 8) % LateralHistoryCount]
                            : smoothedLateral_;

                    const float direction =
                        lateralBeforeImpact >= 0.0f ? -1.0f : 1.0f;

                    const float severity =
                        std::clamp((speedDrop - 0.03f) / 0.12f, 0.0f, 1.0f);
                    crashImpulseForce_ =
                        direction * (1.7f + 0.8f * severity) *
                        static_cast<float>(Settings::WheelFFBWallImpact);

                    crashImpulseTimer_ = CrashTimerFrames;
                    smoothedLateral_ = 0.0f;

                    if (Settings::WheelFFBDebugLog)
                    {
                        spdlog::info(
                            "WheelFFB: crash speedDrop={:.3f}, dir={:.0f}",
                            speedDrop, direction);
                    }
                }
            }

            const bool collision = (stateFlags & 0x1000) != 0;
            const bool wasCollision = (prevCollisionFlags_ & 0x1000) != 0;

            if (collision && !wasCollision && crashImpulseTimer_ <= 0)
            {
                const float lateralBeforeImpact =
                    lateralHistoryIndex_ > 8
                        ? lateralHistory_[(lateralHistoryIndex_ - 8) % LateralHistoryCount]
                        : smoothedLateral_;

                const float direction =
                    lateralBeforeImpact >= 0.0f ? -1.0f : 1.0f;

                crashImpulseForce_ =
                    direction * 1.9f *
                    static_cast<float>(Settings::WheelFFBWallImpact);
                crashImpulseTimer_ = CrashTimerFrames;
                smoothedLateral_ = 0.0f;
            }
        }

        void update_gear_event(uint32_t curGear)
        {
            if (curGear != prevGear_ && prevGear_ != 0 && gearShiftTimer_ <= 0)
                gearShiftTimer_ = 6;
        }

        float update_event_force()
        {
            float result = 0.0f;

            if (crashImpulseTimer_ > 0)
            {
                if (crashImpulseTimer_ > CrashCooldownFrames)
                {
                    // A short kick/rebound is much easier to feel on a DD wheel
                    // than the old soft one-direction 10-frame push.
                    const int impactFrame = CrashTimerFrames - crashImpulseTimer_;
                    if (impactFrame < 3)
                        result += crashImpulseForce_;
                    else if (impactFrame < 6)
                        result -= crashImpulseForce_ * 0.55f;
                    else
                        result += crashImpulseForce_ * 0.20f;
                }
                --crashImpulseTimer_;
            }

            if (gearShiftTimer_ > 0)
            {
                const float thunk =
                    0.20f *
                    static_cast<float>(Settings::WheelFFBGearShift) *
                    (gearShiftTimer_ > 3 ? 1.0f : -1.0f);
                result += thunk;
                --gearShiftTimer_;
            }

            return result;
        }

        float synth_fallback(float& phase, float amplitude, float frequency)
        {
            if (!std::isfinite(amplitude) || !std::isfinite(frequency) ||
                amplitude <= 0.005f)
            {
                phase = 0.0f;
                return 0.0f;
            }

            constexpr float TwoPi = 6.28318530718f;
            phase = std::fmod(phase + frequency / 60.0f * TwoPi, TwoPi);
            return std::sin(phase) * amplitude;
        }

        void zero_all_forces()
        {
            if (!initialized_ || panicStopped_)
                return;

            if (constantEffect_ && prevConstantLevel_ != 0)
                set_constant_force(0);

            if (springEffect_ && prevSpringCoefficient_ != 0)
                update_spring(0.0f);

            if (damperEffect_ && prevDamperCoefficient_ != 0)
                update_damper(0.0f);

            prevStructuralLevel_ = 0;

            if (roadTextureEffect_)
                update_periodic(roadTextureEffect_, roadState_, 0.0f, 30.0f);
            if (tireSlipEffect_)
                update_periodic(tireSlipEffect_, slipState_, 0.0f, 35.0f);
        }

        void reset_signal_state()
        {
            smoothedLateral_ = 0.0f;
            smoothedLongAccel_ = 0.0f;
            prevSteer_ = 0.0f;
            smoothedSteerRate_ = 0.0f;
            steerSampleValid_ = false;
            vehicleDynamics_.reset_dynamic();
            prevStructuralLevel_ = 0;
            prevSpringCoefficient_ = 0;
            prevDamperCoefficient_ = 0;
            crashImpulseTimer_ = 0;
            crashImpulseForce_ = 0.0f;
            gearShiftTimer_ = 0;
            warmupFrames_ = 0;
            roadPhase_ = 0.0f;
            slipPhase_ = 0.0f;
            splashTimer_ = 0;
            splashAmp_ = 0.0f;
            manualTestFrames_ = 0;
            manualTestDirection_ = 1;

            // Menu/race transitions must not reuse samples from the previous
            // gameplay segment. Old speed/lateral history can otherwise look
            // like a huge first-frame deceleration and synthesize a false crash
            // or weight-transfer kick when returning from F11/the main menu.
            std::fill_n(speedHistory_, SpeedHistoryCount, 0.0f);
            speedHistoryIndex_ = 0;
            std::fill_n(lateralHistory_, LateralHistoryCount, 0.0f);
            lateralHistoryIndex_ = 0;
            prevGear_ = 0;
            prevCollisionFlags_ = 0;
        }

        void install_exit_guards()
        {
            if (!gameHwnd_)
                return;

            // USB/device-loss recovery may call initialize() more than once.
            // Window subclassing and inline-hooking ExitProcess must be
            // idempotent or a second initialization can create a bad hook chain.
            if (subclassHwnd_ != gameHwnd_)
            {
                if (subclassHwnd_ && IsWindow(subclassHwnd_))
                {
                    KillTimer(subclassHwnd_, FFB_WATCHDOG_TIMER_ID);
                    RemoveWindowSubclass(
                        subclassHwnd_, window_subclass_proc, FFB_SUBCLASS_ID);
                }

                if (SetWindowSubclass(
                        gameHwnd_,
                        window_subclass_proc,
                        FFB_SUBCLASS_ID,
                        reinterpret_cast<DWORD_PTR>(this)))
                {
                    subclassHwnd_ = gameHwnd_;
                    SetTimer(
                        gameHwnd_,
                        FFB_WATCHDOG_TIMER_ID,
                        FFB_WATCHDOG_INTERVAL_MS,
                        nullptr);
                    spdlog::info("WheelFFB: window exit/watchdog guard installed");
                }
                else
                {
                    spdlog::warn("WheelFFB: SetWindowSubclass failed");
                }
            }

            if (!exitProcessHook_)
            {
                if (auto* exitProc =
                        GetProcAddress(GetModuleHandleA("kernel32.dll"), "ExitProcess"))
                {
                    exitProcessHook_ =
                        safetyhook::create_inline(exitProc, exit_process_hook);
                    if (exitProcessHook_)
                        spdlog::info("WheelFFB: ExitProcess safety hook installed");
                }
            }

            activeEngine_ = this;
        }

        static LRESULT CALLBACK window_subclass_proc(
            HWND hwnd,
            UINT message,
            WPARAM wParam,
            LPARAM lParam,
            UINT_PTR,
            DWORD_PTR refData)
        {
            auto* self = reinterpret_cast<WheelFFBEngine*>(refData);

            if (self)
            {
                switch (message)
                {
                case WM_TIMER:
                    if (wParam == FFB_WATCHDOG_TIMER_ID)
                        self->check_watchdog();
                    break;

                case WM_ACTIVATEAPP:
                    self->appActive_ = (wParam != FALSE);
                    if (!self->appActive_)
                    {
                        self->zero_all_forces();
                        self->reset_signal_state();
                        if (self->device_ && self->deviceAcquired_)
                        {
                            self->device_->Unacquire();
                            self->deviceAcquired_ = false;
                        }
                    }
                    else
                    {
                        // Re-enter with the normal DD warm-up ramp instead of
                        // restoring the previous torque in one frame.
                        self->warmupFrames_ = 0;
                    }
                    break;

                case WM_CLOSE:
                case WM_DESTROY:
                case WM_QUERYENDSESSION:
                    self->panic_stop();
                    break;
                }
            }

            return DefSubclassProc(hwnd, message, wParam, lParam);
        }

        static void WINAPI exit_process_hook(UINT exitCode)
        {
            auto* engine = activeEngine_;
            if (!engine)
                return;

            engine->panic_stop();
            engine->exitProcessHook_.stdcall<void>(exitCode);
        }

        static void safe_release_effect(
            IDirectInputEffect*& effect,
            const char* name)
        {
            if (!effect)
                return;

            __try
            {
                effect->Release();
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                spdlog::warn(
                    "WheelFFB: exception releasing {} effect (0x{:X})",
                    name,
                    GetExceptionCode());
            }
            effect = nullptr;
        }

        void restore_driver_autocenter(const char* where)
        {
            if (!device_ || !driverAutocenterDisabled_ || !autocenterRestoreKnown_)
                return;

            deviceAcquired_ = false;
            __try
            {
                device_->Unacquire();

                DIPROPDWORD autocenter{};
                autocenter.diph.dwSize = sizeof(autocenter);
                autocenter.diph.dwHeaderSize = sizeof(DIPROPHEADER);
                autocenter.diph.dwObj = 0;
                autocenter.diph.dwHow = DIPH_DEVICE;
                autocenter.dwData = originalAutocenter_;
                const HRESULT restoreHr =
                    device_->SetProperty(DIPROP_AUTOCENTER, &autocenter.diph);
                if (FAILED(restoreHr))
                {
                    spdlog::warn(
                        "WheelFFB: autocenter restore during {} failed (0x{:08X})",
                        where, (unsigned)restoreHr);
                }
                else
                {
                    driverAutocenterDisabled_ = false;
                }
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                spdlog::warn(
                    "WheelFFB: exception restoring autocenter during {} (0x{:X})",
                    where, GetExceptionCode());
            }
        }

        void release_device()
        {
            if (!device_)
            {
                deviceAcquired_ = false;
                driverAutocenterDisabled_ = false;
                return;
            }

            // Clear logical acquisition state before touching a possibly stale
            // COM object. Even a driver exception must not leave a phantom
            // acquired device behind in the engine state.
            deviceAcquired_ = false;
            restore_driver_autocenter("device release");

            IDirectInputDevice8A* staleDevice = device_;
            device_ = nullptr;
            driverAutocenterDisabled_ = false;
            __try
            {
                staleDevice->Unacquire();
                staleDevice->Release();
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                spdlog::warn(
                    "WheelFFB: exception releasing DirectInput device (0x{:X})",
                    GetExceptionCode());
            }
        }

        void release_directinput()
        {
            if (!directInput_)
                return;

            IDirectInput8A* staleDirectInput = directInput_;
            directInput_ = nullptr;
            __try
            {
                staleDirectInput->Release();
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                spdlog::warn(
                    "WheelFFB: exception releasing DirectInput root object (0x{:X})",
                    GetExceptionCode());
            }
        }

        void maybe_log(
            float speedNorm,
            float steer,
            float steerRate,
            float lateralLoad,
            float bodySlide,
            float frontScrub,
            float roughness,
            float satTorque,
            LONG level)
        {
            if (!Settings::WheelFFBDebugLog)
                return;

            const DWORD now = GetTickCount();
            if (now - lastLogTick_ < 2000)
                return;

            lastLogTick_ = now;
            spdlog::info(
                "WheelFFB DIAG: spd={:.2f} steer={:.3f} rate={:.4f} lat={:.2f} load={:.2f} slide={:.2f} scrub={:.2f} rough={:.2f} sat={:.3f} phys={} basis=M70r{} cal={:.2f} mix={:.2f} beta={:.3f} yaw={:.3f} fslip={:.3f} vLat={:.5f} vLong={:.5f} step={:.5f} spdLen={:.5f} spdCorr={:.2f} steerSrc={} out={} invCF={} spring={} invSpring={} coeff={} damper={} dcoeff={} periodic={}",
                speedNorm,
                steer,
                steerRate,
                smoothedLateral_,
                lateralLoad,
                bodySlide,
                frontScrub,
                roughness,
                satTorque,
                Settings::WheelFFBPhysicsSat
                    ? (vehicleDynamics_.calibrated()
                        ? (vehicleDynamics_.sampleValid() ? "ACTIVE" : "FALLBACK")
                        : "CAL")
                    : "OFF",
                vehicleDynamics_.forwardAxis(),
                vehicleDynamics_.calibrationConfidence(),
                vehicleDynamics_.activationBlend(),
                vehicleDynamics_.bodySlip(),
                vehicleDynamics_.yawRate(),
                vehicleDynamics_.frontSlip(),
                vehicleDynamics_.vLat(),
                vehicleDynamics_.vLong(),
                vehicleDynamics_.positionStep(),
                vehicleDynamics_.spdLen(),
                vehicleDynamics_.spdCorrelation(),
                Settings::UseNewInput ? "SDL" : "legacy",
                static_cast<int>(level),
                bool(Settings::WheelFFBInvertForce),
                springEffect_ ? "HW" : "SW",
                bool(Settings::WheelFFBInvertSpring),
                static_cast<int>(prevSpringCoefficient_),
                damperEffect_ ? "HW" : "SW",
                static_cast<int>(prevDamperCoefficient_),
                periodicsActive_);
        }

        DWORD lastTelemetryTick_ = 0;
        DWORD lastConstantWriteTick_ = 0;
        DWORD lastSpringWriteTick_ = 0;
        DWORD lastDamperWriteTick_ = 0;
        EVWORK_CAR* lastCar_ = nullptr;
        IDirectInput8A* directInput_ = nullptr;
        IDirectInputDevice8A* device_ = nullptr;
        IDirectInputEffect* constantEffect_ = nullptr;
        IDirectInputEffect* springEffect_ = nullptr;
        IDirectInputEffect* damperEffect_ = nullptr;
        IDirectInputEffect* roadTextureEffect_ = nullptr;
        IDirectInputEffect* tireSlipEffect_ = nullptr;

        // DirectInput does not promise to copy lpvTypeSpecificParams. Keep the
        // backing structures alive for as long as their effects exist.
        DICONSTANTFORCE constantParams_{};
        DICONDITION springParams_{};
        DICONDITION damperParams_{};
        DIPERIODIC roadPeriodicParams_{};
        DIPERIODIC tireSlipPeriodicParams_{};

        std::vector<DWORD> actuatorAxes_;
        bool constantEffectPolar_ = false;

        GUID selectedGuid_{};
        std::string selectedName_;
        std::string selectedConfiguredGuid_;
        std::string selectedConfiguredName_;
        HWND gameHwnd_ = nullptr;
        HWND subclassHwnd_ = nullptr;

        bool initialized_ = false;
        bool panicStopped_ = false;
        bool deviceAcquired_ = false;
        bool driverAutocenterDisabled_ = false;
        bool autocenterRestoreKnown_ = false;
        DWORD originalAutocenter_ = DIPROPAUTOCENTER_ON;
        bool enabledLastTick_ = true;
        bool appActive_ = true;
        bool periodicsActive_ = false;
        int periodicStrategy_ = 1; // Explicitly restart sine effects on every update.
        int springStrategy_ = -1;
        int damperStrategy_ = -1;

        DWORD retryAfter_ = 0;
        std::string failedInterfaceGuid_;
        DWORD failedInterfaceUntil_ = 0;
        DWORD constantRecreateHoldoffUntil_ = 0;
        DWORD periodicRecreateHoldoffUntil_ = 0;
        DWORD springRecreateHoldoffUntil_ = 0;
        DWORD damperRecreateHoldoffUntil_ = 0;
        DWORD lastUpdateTick_ = 0;
        DWORD lastLogTick_ = 0;
        DWORD deviceFailureSince_ = 0;
        DWORD deviceReinitAfter_ = 0;
        bool deviceReinitPending_ = false;

        PeriodicState roadState_{};
        PeriodicState slipState_{};

        float smoothedLateral_ = 0.0f;
        float smoothedLongAccel_ = 0.0f;
        float prevSteer_ = 0.0f;
        float smoothedSteerRate_ = 0.0f;
        bool steerSampleValid_ = false;
        WheelVehicleDynamics vehicleDynamics_{};
        float crashImpulseForce_ = 0.0f;
        float roadPhase_ = 0.0f;
        float slipPhase_ = 0.0f;
        float splashAmp_ = 0.0f;

        float speedHistory_[SpeedHistoryCount]{};
        int speedHistoryIndex_ = 0;
        float lateralHistory_[LateralHistoryCount]{};
        int lateralHistoryIndex_ = 0;

        uint32_t prevGear_ = 0;
        uint32_t prevCollisionFlags_ = 0;

        LONG prevConstantLevel_ = 0;
        LONG prevStructuralLevel_ = 0;
        LONG prevSpringCoefficient_ = 0;
        LONG prevDamperCoefficient_ = 0;
        DWORD prevSpringSaturation_ = 0;

        int crashImpulseTimer_ = 0;
        int gearShiftTimer_ = 0;
        int warmupFrames_ = 0;
        int recreateRampFrames_ = 0;
        int manualTestFrames_ = 0;
        int manualTestDirection_ = 1;
        int splashTimer_ = 0;
        unsigned updateCounter_ = 0;

        SafetyHookInline exitProcessHook_{};

        inline static WheelFFBEngine* activeEngine_ = nullptr;
    };

    WheelFFBEngine gWheelFFB;

    class WheelFFBHook : public Hook
    {
        // FFB update ownership lives in the existing GamePlCar_Ctrl wrapper.
        // Do not install another inline hook on the physics/vibration path.

    public:
        std::string_view description() override
        {
            return "WheelFFB (DirectInput COM)";
        }

        void declare_settings() override
        {
            // Wheel FFB has one dedicated F11 page. Keep every [WheelFFB]
            // setting out of the generic Settings window so there is no second
            // UI that looks like a competing backend.
            for (auto* setting : Settings::SettingBase::registry())
            {
                if (setting && setting->section() == "WheelFFB")
                    setting->hidden(true);
            }
        }

        bool validate() override
        {
            // The engine itself gates on WheelFFBEnable; the existing Vibration
            // GamePlCar_Ctrl wrapper invokes us after each 60 Hz physics tick.
            return true;
        }

        bool apply() override
        {
            spdlog::info(
                "WheelFFB: DirectInput COM engine registered; update runs after GamePlCar_Ctrl physics");
            return true;
        }

        static WheelFFBHook instance;
    };

    WheelFFBHook WheelFFBHook::instance;
}

void __cdecl WheelFFB_UpdateAfterPhysics(EVWORK_CAR* car)
{
    gWheelFFB.update(car);
}

void WheelFFB_ServiceSafety()
{
    gWheelFFB.service_safety();
}

bool WheelFFB_IsOutputOwnerActive()
{
    return gWheelFFB.output_owner_active();
}

void WheelFFB_RequestDirectionTest(int direction)
{
    gWheelFFB.request_direction_test(direction);
}

void WheelFFB_RequestSettingsTransition()
{
    gWheelFFB.settings_transition();
}
