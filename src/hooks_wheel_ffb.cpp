#define WIN32_LEAN_AND_MEAN
#define DIRECTINPUT_VERSION 0x0800
#include <Windows.h>
#include <commctrl.h>
#include <dinput.h>

#pragma comment(lib, "dinput8.lib")
#pragma comment(lib, "dxguid.lib")
#pragma comment(lib, "Comctl32.lib")

#include <algorithm>
#include <array>
#include <cmath>
#include <cctype>
#include <cstddef>
#include <cstring>
#include <cstdio>
#include <string>
#include <vector>

#include "hook_mgr.hpp"
#include "Proxy.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "hooks_wheel_vehicle_dynamics.hpp"
#include "hooks_wheel_native_physics_research.hpp"
#include "wheel_ffb_math.hpp"
#include "wheel_ffb_runtime.hpp"
#include "overlay/overlay.hpp"

extern "C"
{
    void __cdecl CalcVibrationValues(EVWORK_CAR* car);
}

extern double __cdecl sub_1149C0(unsigned int surfaceMask, int loadColiType, DWORD* waterFlag);
extern float InputManager_SteeringValue();

static_assert(offsetof(EVWORK_CAR, actionforce_DBC) == 0xDBC,
    "EVWORK_CAR::actionforce_DBC offset drifted; legacy DBC diagnostic would read the wrong memory");

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
        "Preferred DirectInput FFB interface selected by F11 Wheel Setup; if validation fails, a compatible sibling interface can be probed and pinned automatically."
    };

    Setting<bool> WheelFFBResponseCorrection{
        "WheelFFB", "ResponseCorrection", false,
        "Optional wheel-specific ConstantForce response correction. Store this with the wheel profile, not a force-feel profile."
    };

    Setting<std::string> WheelFFBResponseLUT{
        "WheelFFB", "ResponseLUT", "0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0",
        "Eleven monotonic command samples for desired torque 0..100% in 10% steps. Linear by default."
    };

    Setting<float> WheelFFBMaxTorqueNm{
        "WheelFFB", "MaxTorqueNm", 0.0f,
        "Optional physical wheel peak torque for diagnostics only. 0 means unknown.",
        Range<float>{ 0.0f, 30.0f }
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

    Setting<float> WheelFFBMechanicalTrail{
        "WheelFFB", "MechanicalTrail", 0.25f,
        "Normalized mechanical/caster-trail ratio in Physics SAT. Acts with front lateral force across the corner; not a centre spring.",
        Range<float>{ 0.0f, 0.60f }
    };

    Setting<float> WheelFFBTrailResponseLead{
        "WheelFFB", "TrailResponseLead", 0.25f,
        "Pneumatic-trail transient phase lead toward raw front slip. Lateral force and torque direction remain filtered.",
        Range<float>{ 0.0f, 0.60f }
    };

    Setting<bool> WheelFFBPhysicsSat{
        "WheelFFB", "PhysicsSAT", true,
        "Experimental body-slip/yaw SAT instead of steering-centre direction alone."
    };

    // v0.3 compatibility settings are retained so existing user.ini/profile
    // files continue to parse, but the whole-EXE map invalidated actionforce_DBC
    // as a steering-force source: its writer belongs to the race handicap /
    // catch-up path. Production output is therefore forced to Modern DD.
    Setting<int> WheelFFBFeedbackCharacter{
        "WheelFFB", "FeedbackCharacter", 0,
        "Deprecated compatibility value. EXE XREF analysis proved actionforce_DBC belongs to handicap/catch-up logic; runtime always uses Modern DD.",
        Range<int>{ 0, 2 }
    };

    Setting<float> WheelFFBXForceMix{
        "WheelFFB", "XForceMix", 0.50f,
        "Deprecated compatibility value. DBC native-force mixing is disabled by executable-map evidence.",
        Range<float>{ 0.0f, 1.0f }
    };

    Setting<bool> WheelFFBXForceInvert{
        "WheelFFB", "XForceInvert", false,
        "Deprecated compatibility value. DBC is diagnostic-only and is never routed to wheel torque."
    };

    Setting<float> WheelFFBXForceGain{
        "WheelFFB", "XForceGain", 1.00f,
        "Deprecated compatibility value. DBC is diagnostic-only and is never routed to wheel torque.",
        Range<float>{ 0.0f, 2.0f }
    };

    Setting<bool> WheelFFBXForceCapture60Hz{
        "WheelFFB", "XForceCapture60Hz", false,
        "Legacy 60 Hz DBC/DC0/DC4 diagnostic capture. DBC is now known to be handicap/catch-up data and never alters FFB output."
    };

    Setting<bool> WheelFFBNativePhysicsCapture60Hz{
        "WheelFFB", "NativePhysicsCapture60Hz", false,
        "Very verbose research capture of the canonical 4-wheel physics workspace after each 60 Hz player-car physics tick. Diagnostic only; never alters wheel output."
    };

    Setting<bool> WheelFFBNativeTireSat{
        "WheelFFB", "NativeTireSAT", false,
        "Experimental SAT from the game's native front-tyre slip/lateral-force channels (AC/C0). Default off until driving captures validate sign/scale."
    };

    Setting<float> WheelFFBNativeTireSatGain{
        "WheelFFB", "NativeTireSATGain", 1.00f,
        "Gain applied to the normalized native front lateral-force candidate before trail shaping.",
        Range<float>{ 0.0f, 2.0f }
    };

    Setting<bool> WheelFFBNativeTireSatInvert{
        "WheelFFB", "NativeTireSATInvert", false,
        "Reverse only the experimental native tyre-force SAT direction. Use only during low-strength validation."
    };

    Setting<bool> WheelFFBNativeOversteerCue{
        "WheelFFB", "NativeOversteerCue", false,
        "Experimental rear-tyre peak-slip counter-steer cue inspired by AMS2 rFuktor and AC post-process FFB. Default off until rear slip direction is hardware-validated."
    };

    Setting<float> WheelFFBNativeOversteerStrength{
        "WheelFFB", "NativeOversteerStrength", 0.10f,
        "Maximum additive rear-slip counter-steer cue before base-SAT headroom taper and the existing global output cap/slew path.",
        Range<float>{ 0.0f, 0.25f }
    };

    Setting<float> WheelFFBNativeOversteerSlipThreshold{
        "WheelFFB", "NativeOversteerSlipThreshold", 0.12f,
        "Rear native slip angle in radians treated as the approximate peak-slip reference for the bounded oversteer cue.",
        Range<float>{ 0.04f, 0.30f }
    };

    Setting<bool> WheelFFBNativeOversteerInvert{
        "WheelFFB", "NativeOversteerInvert", false,
        "Reverse only the native rear-slip counter-steer cue during low-strength direction validation."
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

    Setting<bool> WheelFFBEngineVibration{
        "WheelFFB", "EngineVibration", false,
        "Optional low-amplitude engine-speed haptic through the universal ConstantForce output path."
    };

    // Keep the legacy EngineIdle key for INI/profile compatibility. It now owns
    // the complete engine-vibration strength rather than only launch/idle rumble.
    Setting<float> WheelFFBEngineIdle{
        "WheelFFB", "EngineIdle", 0.20f,
        "Engine vibration strength (legacy EngineIdle key retained for compatibility).",
        Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBSlewRate{
        "WheelFFB", "SlewRate", 0.06f,
        "Maximum normal structural-force build change per 60 Hz tick, normalized 0..1.", Range<float>{ 0.01f, 1.0f }
    };

    Setting<float> WheelFFBReversalReleaseRate{
        "WheelFFB", "ReversalReleaseRate", 0.12f,
        "Dedicated stale-torque release rate when SAT changes direction. Higher values reduce counter-steer latency without accelerating normal force build.",
        Range<float>{ 0.02f, 1.0f }
    };

    Setting<bool> WheelFFBUsePeriodicEffects{
        "WheelFFB", "UsePeriodicEffects", true,
        "Use DirectInput hardware GUID_Sine effects for road texture and tire slip."
    };

    Setting<bool> WheelFFBInvertForce{
        "WheelFFB", "InvertForce", false,
        "Reverse ConstantForce steering/event direction without changing the centering spring. Leave off for the validated MOZA R3 path."
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
    constexpr DWORD FFB_DEVICE_FAILED_BACKOFF_MS = 10000;
    constexpr unsigned FFB_CONSTANT_LIVE_FAILURE_LIMIT = 3;

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

    bool directinput_guid_equal(const GUID& a, const GUID& b)
    {
        return std::memcmp(&a, &b, sizeof(GUID)) == 0;
    }

    bool directinput_guid_is_zero(const GUID& guid)
    {
        const GUID zero{};
        return directinput_guid_equal(guid, zero);
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
                    preferredVidPid_ = 0;
                    preferredProductGuid_ = {};
                    preferredFFDriverGuid_ = {};
                    preferredVendorId_ = 0;
                    failedInterfaces_.clear();
                    directionTested_ = false;
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

                const size_t failedBefore = active_failed_interface_count();
                const bool ready = initialize();
                if (!ready)
                {
                    const size_t failedAfter = active_failed_interface_count();
                    if (failedAfter > failedBefore)
                    {
                        // Compatibility rejection is progress, not a reason to
                        // block the game thread while every sibling is reopened.
                        // Probe the next candidate on the next update tick.
                        retryAfter_ = 0;
                        spdlog::info(
                            "WheelFFB: FFB interface failed validation; next compatible interface will be probed on the next update tick ({} rejected this cycle)",
                            failedAfter);
                        return;
                    }

                    // initialize() can request the short retry interval for
                    // transient startup/focus conditions. Do not overwrite that
                    // with the rejected-interface backoff.
                    const DWORD retryNow = GetTickCount();
                    if (!tick_before(retryNow, retryAfter_))
                        retryAfter_ = retryNow + FFB_DEVICE_FAILED_BACKOFF_MS;
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
            const float throttleNorm = std::clamp(
                static_cast<float>(car->pedal_amount_34) / 255.0f, 0.0f, 1.0f);

            float engineAmp = 0.0f;
            float engineFreq = 0.0f;
            if (Settings::WheelFFBEngineVibration)
            {
                const auto engineTarget = WheelFFBMath::estimate_engine_haptics(
                    speedNorm, curGear, throttleNorm);
                const float rpmBlend = engineTarget.rpmNorm > smoothedEngineRpm_
                    ? 0.24f : 0.12f;
                smoothedEngineRpm_ +=
                    (engineTarget.rpmNorm - smoothedEngineRpm_) * rpmBlend;

                const float configuredEngineStrength =
                    static_cast<float>(Settings::WheelFFBEngineIdle);
                const float engineStrength = std::isfinite(configuredEngineStrength)
                    ? std::clamp(configuredEngineStrength, 0.0f, 1.0f)
                    : 0.0f;
                const float amplitudeScale = std::clamp(
                    0.38f + 0.32f * smoothedEngineRpm_ + 0.10f * throttleNorm,
                    0.0f, 1.0f);
                // Strength is a user-friendly 0..1 control, not direct wheel torque.
                // 0.20 therefore remains subtle instead of becoming a 20% torque pulse.
                const float targetEngineAmp =
                    engineStrength * 0.22f * amplitudeScale * outputStrength;
                const float ampBlend = targetEngineAmp > smoothedEngineAmp_ ? 0.16f : 0.08f;
                smoothedEngineAmp_ +=
                    (targetEngineAmp - smoothedEngineAmp_) * ampBlend;
                engineAmp = smoothedEngineAmp_;

                const float targetEngineFreq = 13.0f + 11.0f * smoothedEngineRpm_;
                if (smoothedEngineFreq_ <= 0.0f)
                    smoothedEngineFreq_ = targetEngineFreq;
                else
                    smoothedEngineFreq_ +=
                        (targetEngineFreq - smoothedEngineFreq_) * 0.14f;
                engineFreq = smoothedEngineFreq_;
            }
            else
            {
                smoothedEngineRpm_ = 0.0f;
                smoothedEngineAmp_ = 0.0f;
                smoothedEngineFreq_ = 0.0f;
                enginePhase_ = 0.0f;
            }

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

            float regripRecovery = 0.0f;
            if (vehicleDynamics_.sampleValid() &&
                speedNorm > 0.08f &&
                crashImpulseTimer_ <= 0)
            {
                regripRecovery = driftRegripGuard_.update(
                    bodySlide, 1.0f / 60.0f);
            }
            else
            {
                driftRegripGuard_.reset();
            }
            const float regripSatScale =
                WheelFFBMath::drift_regrip_sat_scale(regripRecovery);
            const float regripDamperBoost =
                WheelFFBMath::drift_regrip_damper_boost(regripRecovery);
            const float regripBuildScale =
                WheelFFBMath::drift_regrip_build_scale(regripRecovery);

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
                    dampingSpeed * damperRelease +
                    regripDamperBoost,
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

            // Physics SAT separates tyre pneumatic trail from a bounded
            // mechanical/caster-trail contribution. Both are driven by the
            // front lateral-force proxy, so the mechanical term cannot become
            // an artificial speed-dependent centre spring. Pneumatic SAT drops
            // first near understeer while mechanical trail keeps useful rack
            // torque alive instead of making the wheel suddenly go dead.
            const float frontSlip = vehicleDynamics_.frontSlip();
            const float rawFrontSlip = vehicleDynamics_.rawFrontSlip();
            float physicsSatTorque = 0.0f;
            const float configuredTrailResponseLead =
                static_cast<float>(Settings::WheelFFBTrailResponseLead);
            const float trailResponseLead = std::isfinite(configuredTrailResponseLead)
                ? std::clamp(configuredTrailResponseLead, 0.0f, 0.60f)
                : 0.25f;
            const float trailResponseSlip = std::clamp(
                frontSlip + (rawFrontSlip - frontSlip) * trailResponseLead,
                -0.70f, 0.70f);
            const float lateralForceShape = WheelFFBMath::lateral_force_shape(frontSlip);
            const float pneumaticTrail = WheelFFBMath::pneumatic_trail_factor(trailResponseSlip);
            const float pneumaticSatShape =
                WheelFFBMath::pneumatic_sat_shape(frontSlip, trailResponseSlip);
            const float configuredMechanicalTrail =
                static_cast<float>(Settings::WheelFFBMechanicalTrail);
            const float mechanicalTrailMix = std::isfinite(configuredMechanicalTrail)
                ? std::clamp(configuredMechanicalTrail, 0.0f, 0.60f)
                : 0.25f;
            const float mechanicalContribution =
                WheelFFBMath::mechanical_sat_shape(frontSlip, mechanicalTrailMix);
            const float physicsShape = WheelFFBMath::combined_sat_shape(
                frontSlip, trailResponseSlip, mechanicalTrailMix);
            const float trailShape = pneumaticSatShape; // legacy telemetry field name
            const float physicsLoad = 0.62f + 0.48f * lateralLoadSmooth;
            const float rearSlideRelief = 1.0f - 0.15f * gripLoss * bodySlide;
            if (vehicleDynamics_.calibrated() && vehicleDynamics_.sampleValid())
            {
                const float physicsReturnRelief =
                    WheelFFBMath::physics_return_relief(frontSlip, steerRate);

                physicsSatTorque =
                    (frontSlip > 0.0f ? -1.0f : 1.0f) *
                    physicsShape * satSpeed * physicsLoad * rearSlideRelief *
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
            const float syntheticModernSat = Settings::WheelFFBPhysicsSat
                ? physicsFallback + (physicsSatTorque - physicsFallback) * physicsMix
                : naturalSatTorque;

            // Canonical EXE tyre path (research-gated):
            // wheel0/1 are the front axle and wheel2/3 are the rear axle.
            // +EE is native signed slip-angle state, +AC is the lateral tyre
            // force component and +C0 is the load-sensitive combined-slip
            // capacity. All new native ownership is opt-in and fail-closed.
            const WheelNativePhysicsResearch::FrontTireState nativeFront =
                WheelNativePhysicsResearch::front_tire_state();
            const WheelNativePhysicsResearch::RearTireState nativeRear =
                WheelNativePhysicsResearch::rear_tire_state();
            const bool nativeTireRequested =
                Settings::WheelFFBPhysicsSat &&
                Settings::WheelFFBNativeTireSat &&
                speedNorm > 0.04f;
            const bool nativeTireValid =
                nativeTireRequested && nativeFront.valid;

            constexpr float NativeTireBlendInPerTick = 1.0f / 12.0f;  // ~200 ms @60 Hz
            constexpr float NativeTireBlendOutPerTick = 1.0f / 6.0f; // ~100 ms @60 Hz
            if (nativeTireValid)
                nativeTireSatBlend_ = std::min(
                    1.0f, nativeTireSatBlend_ + NativeTireBlendInPerTick);
            else
                nativeTireSatBlend_ = std::max(
                    0.0f, nativeTireSatBlend_ - NativeTireBlendOutPerTick);

            float nativeTireSatTorque = syntheticModernSat;
            if (nativeFront.valid)
            {
                const float configuredNativeGain =
                    static_cast<float>(Settings::WheelFFBNativeTireSatGain);
                const float nativeGain = std::isfinite(configuredNativeGain)
                    ? std::clamp(configuredNativeGain, 0.0f, 2.0f)
                    : 1.0f;
                const float nativeForceMagnitude = std::clamp(
                    std::abs(nativeFront.normalizedLateral) * nativeGain,
                    0.0f, 1.0f);

                // AC already contains the game's own load/grip/combined-slip
                // behavior. Only the aligning lever arm is shaped here; do not
                // multiply the synthetic lateral-G load proxy on top of it.
                const float nativePneumaticTrail =
                    WheelFFBMath::pneumatic_trail_factor(nativeFront.slipRad);
                const float nativeTrailDenom = 1.0f + mechanicalTrailMix;
                const float nativeAlignShape = nativeTrailDenom > 0.0f
                    ? std::clamp(
                        nativeForceMagnitude *
                        (nativePneumaticTrail + mechanicalTrailMix) /
                        nativeTrailDenom,
                        0.0f, 1.0f)
                    : 0.0f;

                float nativeDirection =
                    nativeFront.normalizedLateral > 0.0f ? -1.0f :
                    (nativeFront.normalizedLateral < 0.0f ? 1.0f : 0.0f);
                if (Settings::WheelFFBNativeTireSatInvert)
                    nativeDirection = -nativeDirection;

                const float nativeReturnRelief =
                    WheelFFBMath::physics_return_relief(
                        nativeFront.slipRad, steerRate);
                nativeTireSatTorque =
                    nativeDirection * nativeAlignShape * satSpeed *
                    nativeReturnRelief * satStrength;
                if (!std::isfinite(nativeTireSatTorque))
                    nativeTireSatTorque = syntheticModernSat;
            }

            const float baseModernSelfAligningTorque =
                syntheticModernSat +
                (nativeTireSatTorque - syntheticModernSat) * nativeTireSatBlend_;

            // AMS2 rFuktor + AC Toolbox-inspired oversteer cue. It is deliberately
            // a bounded rear peak-slip cue, not a generic "drift force": it rises
            // near the configured rear peak-slip reference and fades again in a
            // very large slide. Both axles need trustworthy native tyre capacity,
            // and collision/reset/airborne-like states release ownership quickly.
            const float configuredRearSlipThreshold =
                static_cast<float>(Settings::WheelFFBNativeOversteerSlipThreshold);
            const float rearSlipThreshold =
                std::isfinite(configuredRearSlipThreshold)
                    ? std::clamp(configuredRearSlipThreshold, 0.04f, 0.30f)
                    : 0.12f;
            const float rearSlipNormalized = nativeRear.valid
                ? std::abs(nativeRear.slipRad) / rearSlipThreshold
                : 0.0f;
            const float rearOversteerBand =
                WheelFFBMath::native_oversteer_band(rearSlipNormalized);

            const bool nativeOversteerRequested =
                Settings::WheelFFBPhysicsSat &&
                Settings::WheelFFBNativeOversteerCue &&
                speedNorm > 0.08f;
            const bool oversteerProtectionClear =
                crashImpulseTimer_ <= 0 &&
                nativeFront.valid &&
                nativeRear.valid &&
                vehicleDynamics_.sampleValid();
            const bool nativeOversteerValid =
                nativeOversteerRequested && oversteerProtectionClear;

            constexpr float OversteerProtectBlendInPerTick = 1.0f / 12.0f; // ~200 ms
            constexpr float OversteerProtectBlendOutPerTick = 1.0f / 3.0f; // ~50 ms
            if (nativeOversteerValid)
                nativeOversteerProtectionBlend_ = std::min(
                    1.0f,
                    nativeOversteerProtectionBlend_ + OversteerProtectBlendInPerTick);
            else
                nativeOversteerProtectionBlend_ = std::max(
                    0.0f,
                    nativeOversteerProtectionBlend_ - OversteerProtectBlendOutPerTick);

            float nativeOversteerCueTorque = 0.0f;
            if (nativeRear.valid && rearOversteerBand > 0.0f)
            {
                const float configuredCueStrength =
                    static_cast<float>(Settings::WheelFFBNativeOversteerStrength);
                const float cueStrength = std::isfinite(configuredCueStrength)
                    ? std::clamp(configuredCueStrength, 0.0f, 0.25f)
                    : 0.10f;

                // Hardware testing on the R3 established the canonical EE sign:
                // preserving rear slip sign produces the correct counter-steer
                // direction. The optional invert remains for device/user fallback.
                const float rearCueDirection =
                    WheelFFBMath::native_oversteer_direction(
                        nativeRear.slipRad,
                        bool(Settings::WheelFFBNativeOversteerInvert));
                const float cueHeadroom =
                    WheelFFBMath::native_oversteer_headroom(
                        baseModernSelfAligningTorque);

                nativeOversteerCueTorque =
                    rearCueDirection *
                    rearOversteerBand *
                    cueStrength *
                    cueHeadroom *
                    satSpeed *
                    satStrength *
                    nativeOversteerProtectionBlend_;
                if (!std::isfinite(nativeOversteerCueTorque))
                    nativeOversteerCueTorque = 0.0f;
            }

            const float modernSelfAligningTorque =
                baseModernSelfAligningTorque + nativeOversteerCueTorque;

            // Legacy v0.3 DBC instrumentation is retained for comparison with
            // old captures, but whole-EXE XREF analysis proved actionforce_DBC is
            // written by the race handicap/catch-up path. It must never own
            // production steering torque. The guarded analyzer below is therefore
            // diagnostic-only until it is eventually removed/replaced by the
            // newly discovered four-wheel native-physics channels.
            const DWORD xForceNow = GetTickCount();
            float xForceDeltaSeconds = 1.0f / 60.0f;
            if (lastXForceFrameTick_ != 0)
            {
                xForceDeltaSeconds = std::clamp(
                    static_cast<float>(xForceNow - lastXForceFrameTick_) / 1000.0f,
                    1.0f / 240.0f, 0.10f);
            }
            lastXForceFrameTick_ = xForceNow;

            const float xForceRaw = car->actionforce_DBC;
            xForceAnalyzer_.update(
                xForceRaw, speedNorm, steer, modernSelfAligningTorque,
                frontSlip, vehicleDynamics_.yawRate(), xForceDeltaSeconds);
            const WheelFFBMath::XForceAnalysisSnapshot xForceAnalysis =
                xForceAnalyzer_.snapshot();
            const WheelFFBMath::XForceGuardSample xForceSample = xForceGuard_.update(
                xForceRaw, speedNorm, steerAbs, bool(Settings::WheelFFBXForceInvert),
                xForceDeltaSeconds, xForceAnalysis.frozenSuspicious);

            const float configuredXForceMix = std::isfinite(
                    static_cast<float>(Settings::WheelFFBXForceMix))
                ? std::clamp(static_cast<float>(Settings::WheelFFBXForceMix), 0.0f, 1.0f)
                : 0.50f;
            const float configuredXForceGain = std::isfinite(
                    static_cast<float>(Settings::WheelFFBXForceGain))
                ? std::clamp(static_cast<float>(Settings::WheelFFBXForceGain), 0.0f, 2.0f)
                : 1.00f;
            const float tuneAlpha = 1.0f - std::exp(
                -xForceDeltaSeconds / 0.12f);
            if (smoothedXForceMix_ < 0.0f)
                smoothedXForceMix_ = configuredXForceMix;
            else
                smoothedXForceMix_ +=
                    (configuredXForceMix - smoothedXForceMix_) * tuneAlpha;
            if (smoothedXForceGain_ < 0.0f)
                smoothedXForceGain_ = configuredXForceGain;
            else
                smoothedXForceGain_ +=
                    (configuredXForceGain - smoothedXForceGain_) * tuneAlpha;

            const float nativeXForceTorque =
                xForceSample.normalized * xForceSample.motionGate * satStrength *
                smoothedXForceGain_;

            const int requestedFeedbackCharacter = std::clamp(
                static_cast<int>(Settings::WheelFFBFeedbackCharacter), 0, 2);
            // Fail closed: DBC/DC0 are handicap/catch-up state, not steering-rack
            // force. Keep the legacy setting readable for old profiles, but force
            // production ownership to Modern DD irrespective of its value.
            constexpr int feedbackCharacter = 0;
            if (requestedFeedbackCharacter != 0)
            {
                static int lastRejectedFeedbackCharacter = -1;
                if (lastRejectedFeedbackCharacter != requestedFeedbackCharacter)
                {
                    lastRejectedFeedbackCharacter = requestedFeedbackCharacter;
                    spdlog::warn(
                        "WheelFFB: FeedbackCharacter={} ignored; executable-map XREFs prove actionforce_DBC is handicap/catch-up data, so Modern DD remains authoritative",
                        requestedFeedbackCharacter);
                }
            }
            const float xForceMix = std::clamp(smoothedXForceMix_, 0.0f, 1.0f);
            const WheelFFBMath::XForceMixResult xForceMixResult =
                WheelFFBMath::mix_xforce_character(
                    modernSelfAligningTorque, nativeXForceTorque,
                    feedbackCharacter, xForceMix, xForceSample.nativeBlend);
            const float rawSelfAligningTorque = xForceMixResult.torque;
            const float selfAligningTorque =
                rawSelfAligningTorque * regripSatScale;

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

            // Preserve v0.2 exactly in Modern mode. As the guarded native
            // share rises, stop layering the synthetic longitudinal weight-
            // transfer modulation onto X-Force itself; Spring keeps its existing
            // load modulation and fallback Modern SAT regains it automatically.
            const float satLoadMod = 1.0f +
                (loadMod - 1.0f) * (1.0f - xForceMixResult.nativeShare);
            float structural = 0.0f;
            if (crashImpulseTimer_ <= CrashCooldownFrames)
            {
                if (xForceMixResult.nativeShare <= 0.0f)
                {
                    // Keep the established v0.2 arithmetic path bit-for-bit in
                    // Modern mode and whenever the native guard has fallen back.
                    structural = (softwareSpring + selfAligningTorque) * loadMod + damper;
                }
                else
                {
                    structural = softwareSpring * loadMod +
                        selfAligningTorque * satLoadMod + damper;
                }
            }

            // Headroom analysis uses sustained structural steering only. Do not
            // let a wall hit, gear thunk, startup ramp or nearly-stopped frame
            // teach the gain recommendation the wrong lesson.
            const bool headroomEligible =
                crashImpulseTimer_ <= 0 && gearShiftTimer_ <= 0 &&
                warmupScale >= 0.999f && recreateScale >= 0.999f &&
                speedNorm > 0.08f;

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
            record_headroom(std::abs(total), headroomEligible);

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
            const LONG baseMaxSlew = static_cast<LONG>(
                safeSlew * static_cast<float>(DI_FFNOMINALMAX));
            const LONG maxSlew = std::max<LONG>(
                1,
                static_cast<LONG>(
                    static_cast<float>(baseMaxSlew) * regripBuildScale));

            const LONG releaseMaxSlew = std::min(
                static_cast<LONG>(DI_FFNOMINALMAX), baseMaxSlew * 2);
            const float configuredReversalRelease =
                static_cast<float>(Settings::WheelFFBReversalReleaseRate);
            const float safeReversalRelease = std::isfinite(configuredReversalRelease)
                ? std::clamp(configuredReversalRelease, 0.02f, 1.0f)
                : 0.12f;
            const LONG reversalReleaseMaxSlew = std::max(
                releaseMaxSlew,
                static_cast<LONG>(safeReversalRelease * static_cast<float>(DI_FFNOMINALMAX)));
            const bool oppositeTorqueDirection =
                structuralLevel != 0 && prevStructuralLevel_ != 0 &&
                (structuralLevel > 0) != (prevStructuralLevel_ > 0);

            if (oppositeTorqueDirection)
            {
                // A sign change first unloads stale torque to zero at the
                // already-approved faster release rate. Do not build the new
                // direction in the same tick.
                if (std::abs(prevStructuralLevel_) <= reversalReleaseMaxSlew)
                    structuralLevel = 0;
                else
                    structuralLevel = prevStructuralLevel_ +
                        (prevStructuralLevel_ > 0 ? -reversalReleaseMaxSlew : reversalReleaseMaxSlew);
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

            // Engine haptics always use the normalized ConstantForce tactile
            // transport so wheel brand / GUID_Sine support cannot change the feel.
            // The existing vibration-headroom clamp below guarantees SAT/events
            // always have priority over this cosmetic engine texture.
            if (Settings::WheelFFBEngineVibration)
            {
                fallbackVibration += synth_fallback(
                    enginePhase_, engineAmp * effectRampScale, engineFreq);
            }

            LONG baseSteeringLevel = std::clamp(
                structuralLevel + eventLevel,
                -static_cast<LONG>(DI_FFNOMINALMAX),
                static_cast<LONG>(DI_FFNOMINALMAX));
            if (Settings::WheelFFBEngineVibration && engineAmp > 0.0001f && eventLevel == 0)
            {
                // Reserve at most 2.5% during ordinary driving so the optional
                // engine texture does not abruptly vanish at brief SAT peaks.
                // Collision/gear events keep full priority.
                const LONG requestedReserve = static_cast<LONG>(
                    engineAmp * static_cast<float>(DI_FFNOMINALMAX));
                const LONG engineReserve = std::clamp(
                    std::abs(requestedReserve), 0L, 250L);
                const LONG baseCap = static_cast<LONG>(DI_FFNOMINALMAX) - engineReserve;
                baseSteeringLevel = std::clamp(
                    structuralLevel + eventLevel, -baseCap, baseCap);
            }
            const LONG vibrationRequested = static_cast<LONG>(
                fallbackVibration * static_cast<float>(DI_FFNOMINALMAX));
            const LONG vibrationHeadroom =
                static_cast<LONG>(DI_FFNOMINALMAX) - std::abs(baseSteeringLevel);
            const LONG vibrationLevel = std::clamp(
                vibrationRequested, -vibrationHeadroom, vibrationHeadroom);
            const LONG levelBeforeResponse = baseSteeringLevel + vibrationLevel;
            const LONG level = apply_response_correction(levelBeforeResponse);
            record_graph_sample(
                total,
                compressed,
                static_cast<float>(structuralLevel) / static_cast<float>(DI_FFNOMINALMAX),
                static_cast<float>(level) / static_cast<float>(DI_FFNOMINALMAX),
                xForceSample.normalized, modernSelfAligningTorque,
                nativeXForceTorque, xForceMixResult.nativeShare,
                nativeFront.valid ? nativeFront.normalizedLateral : 0.0f,
                nativeTireSatTorque, nativeTireSatBlend_,
                rearSlipNormalized, nativeOversteerCueTorque,
                nativeOversteerProtectionBlend_);

            if (Settings::WheelFFBXForceCapture60Hz)
            {
                spdlog::info(
                    "WheelFFB XFORCE60 tick={} t={} dt={} raw={} speed={} steer={} frontSlip={} yaw={} modern={} native={} finalSat={} normalized={} valid={} blend={} share={} gain={} mix={} confidence={} corrSteer={} corrModern={} corrFront={} corrYaw={} frozen={} frozenSec={} p50={} p90={} p95={} p99={} max={}",
                    updateCounter_, xForceNow, xForceDeltaSeconds, xForceRaw,
                    speedNorm, steer, frontSlip, vehicleDynamics_.yawRate(),
                    modernSelfAligningTorque, nativeXForceTorque, selfAligningTorque,
                    xForceSample.normalized, xForceSample.valid,
                    xForceSample.nativeBlend, xForceMixResult.nativeShare,
                    smoothedXForceGain_, xForceMix, xForceAnalysis.confidence,
                    xForceAnalysis.corrSteer, xForceAnalysis.corrModernSat,
                    xForceAnalysis.corrFrontSlip, xForceAnalysis.corrYawRate,
                    xForceAnalysis.frozenSuspicious, xForceAnalysis.frozenSeconds,
                    xForceAnalysis.p50Abs, xForceAnalysis.p90Abs,
                    xForceAnalysis.p95Abs, xForceAnalysis.p99Abs,
                    xForceAnalysis.maxAbs);
            }

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
                    "WheelFFB SAMPLE t={} car={} speedRaw={} speedNorm={} steer={} steerRateRaw={} steerRateFiltered={} field264={} field268={} lateralRaw={} lateralSmooth={} lateralLoad={} bodySlip={} bodySlide={} yawRate={} frontSlip={} frontScrub={} vLongTick={} vLatTick={} positionStep={} spdX={} spdY={} spdZ={} spdLenXZ={} spdCorrelation={} basis={} basisConfidence={} sampleValid={} mix={} satRaw={} satMixed={} trailShape={} satLoad={} rearSlideRelief={} regripRecovery={} regripSatScale={} regripDamperBoost={} regripBuildScale={} springRequested={} springCoefficient={} damperRequested={} damperRelease={} damperCoefficient={} roadAmp={} slipAmp={} structural={} event={} structuralPreClip={} structuralPostClip={} eventPostClip={} postSlew={} diRequested={} diLastAccepted={} polar={} hwSpring={} hwDamper={} hwPeriodic={} gain={} invert={} invertSpring={}",
                    telemetryNow, static_cast<const void*>(car), speedRaw, speedNorm, steer, rawSteerRate, steerRate,
                    car->field_264, car->field_268, lateralRaw, smoothedLateral_, lateralLoadSmooth,
                    vehicleDynamics_.bodySlip(), bodySlide, vehicleDynamics_.yawRate(), frontSlip, frontScrub,
                    vehicleDynamics_.vLong(), vehicleDynamics_.vLat(), vehicleDynamics_.positionStep(),
                    car->spd_mb_20.x, car->spd_mb_20.y, car->spd_mb_20.z,
                    vehicleDynamics_.spdLen(), vehicleDynamics_.spdCorrelation(),
                    vehicleDynamics_.forwardAxis(), vehicleDynamics_.calibrationConfidence(),
                    vehicleDynamics_.sampleValid(), physicsMix, physicsSatTorque, selfAligningTorque,
                    trailShape, physicsLoad, rearSlideRelief,
                    regripRecovery, regripSatScale, regripDamperBoost, regripBuildScale,
                    springStrength, prevSpringCoefficient_,
                    dynamicDamperStrength, damperRelease, prevDamperCoefficient_, roadAmp, slipAmp,
                    structural, events, total, compressed, eventCompressed, structuralLevel, level, prevConstantLevel_,
                    constantEffectPolar_, springEffect_ != nullptr, damperEffect_ != nullptr,
                    periodicsActive_, outputStrength, bool(Settings::WheelFFBInvertForce),
                    bool(Settings::WheelFFBInvertSpring));
                spdlog::info(
                    "WheelFFB XFORCE t={} character={} raw={} finite={} range={} observed={} responsive={} fresh={} stopped={} valid={} normalized={} motionGate={} guardBlend={} nativeShare={} nativeTorque={} modernTorque={} finalSat={} mix={} candidateInvert={}",
                    telemetryNow, feedbackCharacter, xForceRaw, xForceSample.finite,
                    xForceSample.rangeValid, xForceSample.responseObserved, xForceSample.responsive,
                    xForceSample.freshAfterStop, xForceSample.stopped, xForceSample.valid,
                    xForceSample.normalized, xForceSample.motionGate, xForceSample.nativeBlend,
                    xForceMixResult.nativeShare, nativeXForceTorque, modernSelfAligningTorque,
                    selfAligningTorque, xForceMix, bool(Settings::WheelFFBXForceInvert));
                spdlog::info(
                    "WheelFFB XFORCE ANALYSIS t={} samples={} confidence={} corrSteer={} corrModern={} corrFront={} corrYaw={} frozen={} frozenSec={} p50={} p90={} p95={} p99={} max={} gain={}",
                    telemetryNow, xForceAnalysis.samples, xForceAnalysis.confidence,
                    xForceAnalysis.corrSteer, xForceAnalysis.corrModernSat,
                    xForceAnalysis.corrFrontSlip, xForceAnalysis.corrYawRate,
                    xForceAnalysis.frozenSuspicious, xForceAnalysis.frozenSeconds,
                    xForceAnalysis.p50Abs, xForceAnalysis.p90Abs,
                    xForceAnalysis.p95Abs, xForceAnalysis.p99Abs,
                    xForceAnalysis.maxAbs, smoothedXForceGain_);
                spdlog::info(
                    "WheelFFB NATIVE_OVERSTEER t={} requested={} frontValid={} rearValid={} rearSlipRad={} rearSlipNorm={} rearBand={} rearAC={} rearCapacity={} protectionClear={} protectionBlend={} baseSat={} cueHeadroom={} cueTorque={} strength={} peakRef={} invert={}",
                    telemetryNow, nativeOversteerRequested, nativeFront.valid, nativeRear.valid,
                    nativeRear.slipRad, rearSlipNormalized, rearOversteerBand,
                    nativeRear.lateralSum, nativeRear.capacitySum,
                    oversteerProtectionClear, nativeOversteerProtectionBlend_,
                    baseModernSelfAligningTorque,
                    WheelFFBMath::native_oversteer_headroom(baseModernSelfAligningTorque),
                    nativeOversteerCueTorque,
                    static_cast<float>(Settings::WheelFFBNativeOversteerStrength),
                    rearSlipThreshold, bool(Settings::WheelFFBNativeOversteerInvert));
                spdlog::info(
                    "WheelFFB SATMODEL t={} rawBodySlip={} bodySlip={} bodyBlend={} rawYawRate={} yawRate={} yawBlend={} rawFrontSlip={} frontSlip={} frontBlend={} trailResponseSlip={} trailResponseLead={} fyShape={} pneumaticTrail={} pneumaticShape={} mechanicalMix={} mechanicalContribution={} combinedShape={} diPreResponse={} diCorrected={} responseCorrection={}",
                    telemetryNow,
                    vehicleDynamics_.rawBodySlip(), vehicleDynamics_.bodySlip(), vehicleDynamics_.bodySlipBlend(),
                    vehicleDynamics_.rawYawRate(), vehicleDynamics_.yawRate(), vehicleDynamics_.yawRateBlend(),
                    vehicleDynamics_.rawFrontSlip(), vehicleDynamics_.frontSlip(), vehicleDynamics_.frontSlipBlend(),
                    trailResponseSlip, trailResponseLead, lateralForceShape, pneumaticTrail,
                    pneumaticSatShape, mechanicalTrailMix, mechanicalContribution, physicsShape,
                    levelBeforeResponse, level, bool(Settings::WheelFFBResponseCorrection));
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

        WheelFFBHeadroomSnapshot headroom_snapshot() const
        {
            WheelFFBHeadroomSnapshot result{};
            result.samples = headroomSamples_;
            result.currentDemand = headroomCurrentDemand_;
            result.peakDemand = headroomPeakDemand_;

            const auto percentile = [&](double q)
            {
                if (headroomSamples_ == 0)
                    return 0.0f;
                const std::uint64_t target = std::max<std::uint64_t>(
                    1, static_cast<std::uint64_t>(std::ceil(headroomSamples_ * q)));
                std::uint64_t cumulative = 0;
                for (size_t i = 0; i < headroomHistogram_.size(); ++i)
                {
                    cumulative += headroomHistogram_[i];
                    if (cumulative >= target)
                    {
                        return static_cast<float>(i) *
                            (HeadroomHistogramMax / static_cast<float>(HeadroomHistogramBins - 1));
                    }
                }
                return HeadroomHistogramMax;
            };

            result.p95Demand = percentile(0.95);
            result.p99Demand = percentile(0.99);
            if (headroomSamples_ > 0)
            {
                const float inv = 100.0f / static_cast<float>(headroomSamples_);
                result.softKneePercent = static_cast<float>(headroomSoftKneeSamples_) * inv;
                result.hardClipPercent = static_cast<float>(headroomHardClipSamples_) * inv;
            }

            const float currentOverall = std::clamp(
                static_cast<float>(Settings::WheelFFBGlobalStrength), 0.0f, 1.5f);
            result.suggestedOverall = currentOverall;
            if (headroomSamples_ >= 600 && result.p99Demand > 0.05f)
            {
                result.suggestedOverall = std::clamp(
                    currentOverall * (0.90f / result.p99Demand),
                    0.05f, 1.5f);
            }
            return result;
        }

        WheelFFBStatusSnapshot status_snapshot() const
        {
            WheelFFBStatusSnapshot result{};
            result.initialized = initialized_;
            result.acquired = deviceAcquired_;
            result.outputOwner = output_owner_active();
            result.constantEffect = constantEffect_ != nullptr;
            result.springEffect = springEffect_ != nullptr;
            result.damperEffect = damperEffect_ != nullptr;
            result.periodicEffects = periodicsActive_;
            result.constantCapsKnown = constantCapsKnown_;
            result.constantDynamic = !constantCapsKnown_ ||
                (constantDynamicParams_ & DIEP_TYPESPECIFICPARAMS) != 0;
            result.polarDirectionDynamic = !constantCapsKnown_ ||
                (constantDynamicParams_ & DIEP_DIRECTION) != 0;
            result.springCapsKnown = springCapsKnown_;
            result.springDynamic = !springCapsKnown_ ||
                (springDynamicParams_ & DIEP_TYPESPECIFICPARAMS) != 0;
            result.damperCapsKnown = damperCapsKnown_;
            result.damperDynamic = !damperCapsKnown_ ||
                (damperDynamicParams_ & DIEP_TYPESPECIFICPARAMS) != 0;
            result.periodicCapsKnown = periodicCapsKnown_;
            result.periodicDynamic = !periodicCapsKnown_ ||
                (periodicDynamicParams_ & DIEP_TYPESPECIFICPARAMS) != 0;
            result.directionTested = directionTested_;

            if (device_)
            {
                DWORD state = 0;
                if (SUCCEEDED(device_->GetForceFeedbackState(&state)))
                {
                    result.ffbStateValid = true;
                    result.actuatorsOn = (state & DIGFFS_ACTUATORSON) != 0;
                    result.powerOn = (state & DIGFFS_POWERON) != 0;
                    result.powerOff = (state & DIGFFS_POWEROFF) != 0;
                    result.safetySwitchOn = (state & DIGFFS_SAFETYSWITCHON) != 0;
                    result.safetySwitchOff = (state & DIGFFS_SAFETYSWITCHOFF) != 0;
                    result.userSwitchOn = (state & DIGFFS_USERFFSWITCHON) != 0;
                    result.userSwitchOff = (state & DIGFFS_USERFFSWITCHOFF) != 0;
                    result.paused = (state & DIGFFS_PAUSED) != 0;
                    result.deviceLost = (state & DIGFFS_DEVICELOST) != 0;
                }
            }
            return result;
        }

        WheelFFBGraphSnapshot graph_snapshot() const
        {
            WheelFFBGraphSnapshot result{};
            result.count = graphCount_;
            const size_t start = graphCount_ < WheelFFBGraphCapacity
                ? 0
                : graphWriteIndex_ % WheelFFBGraphCapacity;
            for (size_t i = 0; i < graphCount_; ++i)
            {
                const size_t src = (start + i) % WheelFFBGraphCapacity;
                result.rawStructural[i] = graphRawStructural_[src];
                result.softLimited[i] = graphSoftLimited_[src];
                result.postSlew[i] = graphPostSlew_[src];
                result.finalOutput[i] = graphFinalOutput_[src];
                result.xForceNormalized[i] = graphXForceNormalized_[src];
                result.modernSat[i] = graphModernSat_[src];
                result.nativeSat[i] = graphNativeSat_[src];
                result.nativeShare[i] = graphNativeShare_[src];
                result.nativeTireNormalized[i] = graphNativeTireNormalized_[src];
                result.nativeTireSat[i] = graphNativeTireSat_[src];
                result.nativeTireShare[i] = graphNativeTireShare_[src];
                result.rearSlipNormalized[i] = graphRearSlipNormalized_[src];
                result.nativeOversteerCue[i] = graphNativeOversteerCue_[src];
                result.nativeOversteerProtection[i] = graphNativeOversteerProtection_[src];
            }
            return result;
        }

        WheelFFBXForceAnalysisSnapshot xforce_analysis_snapshot() const
        {
            const WheelFFBMath::XForceAnalysisSnapshot source = xForceAnalyzer_.snapshot();
            WheelFFBXForceAnalysisSnapshot out{};
            out.samples = source.samples;
            out.corrSteer = source.corrSteer;
            out.corrModernSat = source.corrModernSat;
            out.corrFrontSlip = source.corrFrontSlip;
            out.corrYawRate = source.corrYawRate;
            out.confidence = source.confidence;
            out.frozenSuspicious = source.frozenSuspicious;
            out.frozenSeconds = source.frozenSeconds;
            out.p50Abs = source.p50Abs;
            out.p90Abs = source.p90Abs;
            out.p95Abs = source.p95Abs;
            out.p99Abs = source.p99Abs;
            out.maxAbs = source.maxAbs;
            return out;
        }

        void reset_headroom_stats()
        {
            headroomHistogram_.fill(0);
            headroomSamples_ = 0;
            headroomSoftKneeSamples_ = 0;
            headroomHardClipSamples_ = 0;
            headroomCurrentDemand_ = 0.0f;
            headroomPeakDemand_ = 0.0f;
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

            directionTested_ = true;
            manualTestDirection_ = direction < 0 ? -1 : 1;
            manualTestFrames_ = 18;
            spdlog::info(
                "WheelFFB: queued safe {} direction test at fixed 20% output",
                manualTestDirection_ < 0 ? "left" : "right");
        }

        void reset_direction_test()
        {
            directionTested_ = false;
        }

        void settings_transition()
        {
            manualTestFrames_ = 0;
            if (initialized_ && device_ && deviceAcquired_ && !panicStopped_)
                zero_all_forces();
            reset_signal_state();
            reset_headroom_stats();
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
        static constexpr size_t HeadroomHistogramBins = 201;
        static constexpr float HeadroomHistogramMax = 2.0f;

        struct FailedInterfaceState
        {
            std::string guid;
            DWORD until = 0;
        };

        struct EnumContext
        {
            WheelFFBEngine* self = nullptr;
            GUID selectedGuid{};
            GUID selectedProductGuid{};
            GUID selectedFFDriverGuid{};
            std::string selectedName;
            DWORD selectedVidPid = 0;
            GUID preferredProductGuid{};
            GUID preferredFFDriverGuid{};
            DWORD preferredVidPid = 0;
            WORD preferredVendorId = 0;
            bool found = false;
            bool matchGuidOnly = false;
            bool requirePreferredProductGuid = false;
            bool requirePreferredVidPid = false;
            bool requirePreferredDriverVendor = false;
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

            if (ctx->self && ctx->self->interface_temporarily_failed(instance->guidInstance))
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

            if (ctx->requirePreferredProductGuid &&
                !directinput_guid_equal(instance->guidProduct, ctx->preferredProductGuid))
            {
                return DIENUM_CONTINUE;
            }

            DWORD candidateVidPid = 0;
            if (ctx->self &&
                (ctx->requirePreferredVidPid || ctx->requirePreferredDriverVendor))
            {
                candidateVidPid = ctx->self->query_device_vidpid(instance->guidInstance);
            }

            if (ctx->requirePreferredVidPid &&
                (candidateVidPid == 0 || candidateVidPid != ctx->preferredVidPid))
            {
                return DIENUM_CONTINUE;
            }

            if (ctx->requirePreferredDriverVendor)
            {
                if (candidateVidPid == 0 || LOWORD(candidateVidPid) != ctx->preferredVendorId ||
                    directinput_guid_is_zero(ctx->preferredFFDriverGuid) ||
                    !directinput_guid_equal(instance->guidFFDriver, ctx->preferredFFDriverGuid))
                {
                    return DIENUM_CONTINUE;
                }
            }

            if (!ctx->matchGuidOnly &&
                !ctx->requirePreferredProductGuid &&
                !ctx->requirePreferredVidPid &&
                !ctx->requirePreferredDriverVendor &&
                !wanted.empty() &&
                instanceName.find(wanted) == std::string::npos &&
                productName.find(wanted) == std::string::npos)
            {
                return DIENUM_CONTINUE;
            }

            if (candidateVidPid == 0 && ctx->self)
                candidateVidPid = ctx->self->query_device_vidpid(instance->guidInstance);

            ctx->selectedGuid = instance->guidInstance;
            ctx->selectedProductGuid = instance->guidProduct;
            ctx->selectedFFDriverGuid = instance->guidFFDriver;
            ctx->selectedName = instance->tszProductName;
            ctx->selectedVidPid = candidateVidPid;
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
            }

            // Disabling FFB is a hard recovery boundary even if initialization
            // never completed. A previous rejected-interface quarantine must not
            // survive a deliberate off/on cycle or a fresh device selection.
            deviceReinitPending_ = false;
            deviceFailureSince_ = 0;
            deviceReinitAfter_ = 0;
            retryAfter_ = 0;
            failedInterfaces_.clear();
            preferredVidPid_ = 0;
            preferredProductGuid_ = {};
            preferredFFDriverGuid_ = {};
            preferredVendorId_ = 0;

            enabledLastTick_ = false;
            if (hadInitializedOutput)
                spdlog::info("WheelFFB: disabled live; output released and driver autocenter restored");
            return true;
        }

        void clear_constant_live_failure()
        {
            constantLiveFailureCount_ = 0;
        }

        bool record_constant_live_failure()
        {
            if (constantLiveFailureCount_ < FFB_CONSTANT_LIVE_FAILURE_LIMIT)
                ++constantLiveFailureCount_;
            return constantLiveFailureCount_ >= FFB_CONSTANT_LIVE_FAILURE_LIMIT;
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
            clear_constant_live_failure();
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
            if ((object->dwType & DIDFT_FFACTUATOR) != 0)
            {
                const DWORD offset = object->dwOfs;
                if (std::find(self->actuatorAxes_.begin(), self->actuatorAxes_.end(), offset) ==
                    self->actuatorAxes_.end())
                {
                    self->actuatorAxes_.push_back(offset);
                }
            }
            return DIENUM_CONTINUE;
        }

        DWORD primary_actuator_axis() const
        {
            return actuatorAxes_.empty() ? DIJOFS_X : actuatorAxes_.front();
        }

        void prune_failed_interfaces()
        {
            const DWORD now = GetTickCount();
            failedInterfaces_.erase(
                std::remove_if(
                    failedInterfaces_.begin(), failedInterfaces_.end(),
                    [&](const FailedInterfaceState& state)
                    {
                        return tick_reached(now, state.until);
                    }),
                failedInterfaces_.end());
        }

        bool interface_temporarily_failed(const GUID& guid)
        {
            prune_failed_interfaces();
            const std::string key = directinput_guid_key(guid);
            return std::any_of(
                failedInterfaces_.begin(), failedInterfaces_.end(),
                [&](const FailedInterfaceState& state) { return state.guid == key; });
        }

        size_t active_failed_interface_count()
        {
            prune_failed_interfaces();
            return failedInterfaces_.size();
        }

        DWORD query_device_vidpid(const GUID& guid)
        {
            if (!directInput_)
                return 0;

            IDirectInputDevice8A* probe = nullptr;
            if (FAILED(directInput_->CreateDevice(guid, &probe, nullptr)) || !probe)
                return 0;

            DIPROPDWORD vidpid{};
            vidpid.diph.dwSize = sizeof(vidpid);
            vidpid.diph.dwHeaderSize = sizeof(vidpid.diph);
            vidpid.diph.dwObj = 0;
            vidpid.diph.dwHow = DIPH_DEVICE;
            const HRESULT hr = probe->GetProperty(DIPROP_VIDPID, &vidpid.diph);
            probe->Release();
            return SUCCEEDED(hr) ? vidpid.dwData : 0;
        }

        void mark_selected_interface_failed(const char* reason, HRESULT hr)
        {
            prune_failed_interfaces();
            const std::string failedGuid = directinput_guid_key(selectedGuid_);
            const DWORD until = GetTickCount() + FFB_DEVICE_FAILED_BACKOFF_MS;
            auto existing = std::find_if(
                failedInterfaces_.begin(), failedInterfaces_.end(),
                [&](const FailedInterfaceState& state) { return state.guid == failedGuid; });
            if (existing != failedInterfaces_.end())
                existing->until = until;
            else
                failedInterfaces_.push_back({ failedGuid, until });

            spdlog::warn(
                "WheelFFB: interface '{}' [{}] rejected {}; temporarily excluding it from automatic selection (0x{:08X})",
                selectedName_, failedGuid, reason, (unsigned)hr);
        }

        bool initialize()
        {
            retryAfter_ = 0;

            using DirectInput8CreateFn = HRESULT(WINAPI*)(
                HINSTANCE, DWORD, REFIID, LPVOID*, LPUNKNOWN);
            auto createDirectInput = proxy::origModule
                ? reinterpret_cast<DirectInput8CreateFn>(
                    GetProcAddress(proxy::origModule, "DirectInput8Create"))
                : nullptr;

            // The plugin is itself named dinput8.dll. Falling back to the linked
            // DirectInput8Create symbol can route back through our own proxy export,
            // so fail closed unless the already-loaded System32 module has the export.
            if (!createDirectInput)
            {
                spdlog::error(
                    "WheelFFB: original System32 dinput8 module has no DirectInput8Create export");
                return false;
            }

            HRESULT hr = createDirectInput(
                GetModuleHandleW(nullptr),
                DIRECTINPUT_VERSION,
                IID_IDirectInput8A,
                reinterpret_cast<void**>(&directInput_),
                nullptr);

            if (FAILED(hr) || !directInput_)
            {
                spdlog::error(
                    "WheelFFB: original DirectInput8Create failed (0x{:08X})",
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
                        "WheelFFB: saved FFB GUID unavailable or rejected; probing compatible sibling interfaces");
                    ctx.matchGuidOnly = false;
                }
            }

            if (!ctx.found && !directinput_guid_is_zero(preferredProductGuid_))
            {
                ctx.matchGuidOnly = false;
                ctx.requirePreferredProductGuid = true;
                ctx.preferredProductGuid = preferredProductGuid_;
                hr = directInput_->EnumDevices(
                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,
                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);
                ctx.requirePreferredProductGuid = false;
                if (FAILED(hr))
                {
                    release_directinput();
                    return false;
                }
                if (!ctx.found)
                {
                    spdlog::warn(
                        "WheelFFB: no remaining FFB interface shared the preferred DirectInput product GUID");
                }
            }

            if (!ctx.found && preferredVidPid_ != 0)
            {
                ctx.matchGuidOnly = false;
                ctx.requirePreferredVidPid = true;
                ctx.preferredVidPid = preferredVidPid_;
                hr = directInput_->EnumDevices(
                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,
                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);
                ctx.requirePreferredVidPid = false;
                if (FAILED(hr))
                {
                    release_directinput();
                    return false;
                }
                if (!ctx.found)
                {
                    spdlog::warn(
                        "WheelFFB: no remaining FFB interface shared preferred VID/PID 0x{:08X}",
                        (unsigned)preferredVidPid_);
                }
            }

            if (!ctx.found && !directinput_guid_is_zero(preferredFFDriverGuid_) &&
                preferredVendorId_ != 0)
            {
                ctx.matchGuidOnly = false;
                ctx.requirePreferredDriverVendor = true;
                ctx.preferredFFDriverGuid = preferredFFDriverGuid_;
                ctx.preferredVendorId = preferredVendorId_;
                hr = directInput_->EnumDevices(
                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,
                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);
                ctx.requirePreferredDriverVendor = false;
                if (FAILED(hr))
                {
                    release_directinput();
                    return false;
                }
                if (!ctx.found)
                {
                    spdlog::warn(
                        "WheelFFB: no remaining FFB interface shared preferred FFB driver/vendor; falling back to the configured device name");
                }
            }

            if (!ctx.found)
            {
                ctx.matchGuidOnly = false;
                ctx.requirePreferredProductGuid = false;
                ctx.requirePreferredVidPid = false;
                ctx.requirePreferredDriverVendor = false;
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
            const bool selectedConfiguredInterface =
                !configuredGuid.empty() && directinput_guid_key(selectedGuid_) == configuredGuid;
            if (!directinput_guid_is_zero(ctx.selectedProductGuid) &&
                (directinput_guid_is_zero(preferredProductGuid_) || selectedConfiguredInterface))
            {
                preferredProductGuid_ = ctx.selectedProductGuid;
            }
            if (!directinput_guid_is_zero(ctx.selectedFFDriverGuid) &&
                (directinput_guid_is_zero(preferredFFDriverGuid_) || selectedConfiguredInterface))
            {
                preferredFFDriverGuid_ = ctx.selectedFFDriverGuid;
            }
            if (ctx.selectedVidPid != 0)
            {
                if (preferredVidPid_ == 0 || selectedConfiguredInterface)
                    preferredVidPid_ = ctx.selectedVidPid;
                if (preferredVendorId_ == 0 || selectedConfiguredInterface)
                    preferredVendorId_ = LOWORD(ctx.selectedVidPid);
            }
            selectedConfiguredGuid_ = lower_copy(Settings::WheelFFBDeviceGuid.get().c_str());
            selectedConfiguredName_ = lower_copy(Settings::WheelFFBDeviceName.get().c_str());
            spdlog::info(
                "WheelFFB: selected DirectInput identity '{}' / '{}' product={} ffDriver={} vidpid=0x{:08X}",
                selectedName_, directinput_guid_key(selectedGuid_),
                directinput_guid_key(ctx.selectedProductGuid),
                directinput_guid_key(ctx.selectedFFDriverGuid),
                (unsigned)ctx.selectedVidPid);

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
                spdlog::warn("WheelFFB: game window not available yet; retrying shortly");
                release_device();
                release_directinput();
                retryAfter_ = GetTickCount() + FFB_DEVICE_RETRY_MS;
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
            if (FAILED(hr) && hr != S_FALSE)
            {
                mark_selected_interface_failed("Acquire", hr);
                spdlog::error("WheelFFB: Acquire('{}') failed (0x{:08X})", selectedName_, (unsigned)hr);
                release_device();
                release_directinput();
                return false;
            }
            deviceAcquired_ = true;

            // Some multi-interface wheel drivers need the legacy reset sequence
            // before the FFB interface will accept actuator/effect commands.
            const HRESULT resetHr = device_->SendForceFeedbackCommand(DISFFC_RESET);
            if (FAILED(resetHr))
            {
                spdlog::warn(
                    "WheelFFB: initial DISFFC_RESET rejected (0x{:08X}); continuing with actuator enable",
                    (unsigned)resetHr);
            }

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
                if (ctx.selectedVidPid != 0)
                    preferredVidPid_ = ctx.selectedVidPid;
                const bool identityChanged =
                    lower_copy(Settings::WheelFFBDeviceGuid.get().c_str()) != actualGuid ||
                    Settings::WheelFFBDeviceName.get() != selectedName_;
                if (identityChanged)
                {
                    Settings::WheelFFBDeviceGuid = actualGuid;
                    Settings::WheelFFBDeviceName = selectedName_;
                    selectedConfiguredGuid_ = actualGuid;
                    selectedConfiguredName_ = lower_copy(selectedName_.c_str());
                    const bool saved = Settings::write(Module::UserIniPath);
                    spdlog::info(
                        "WheelFFB: pinned working force interface '{}' [{}] after capability validation{}",
                        selectedName_, actualGuid, saved ? " and saved it to user.ini" : " for this session only");
                    if (!saved)
                    {
                        spdlog::warn(
                            "WheelFFB: automatic FFB interface selection could not persist user.ini; the interface may be probed again next launch");
                    }
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
            reset_headroom_stats();

            prune_failed_interfaces();

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

        bool query_dynamic_effect_capability(
            REFGUID effectGuid, const char* label, DWORD required,
            bool& known, DWORD& dynamicParams)
        {
            known = false;
            dynamicParams = 0;
            if (!device_)
                return false;

            DIEFFECTINFOA info{};
            info.dwSize = sizeof(info);
            const HRESULT hr = device_->GetEffectInfo(&info, effectGuid);
            if (FAILED(hr))
            {
                // Some older drivers do not expose useful effect metadata even
                // though SetParameters works. Preserve the proven legacy path
                // when capability discovery itself is unavailable.
                spdlog::warn(
                    "WheelFFB: GetEffectInfo({}) failed (0x{:08X}); keeping compatibility behavior",
                    label, (unsigned)hr);
                return true;
            }

            known = true;
            dynamicParams = info.dwDynamicParams;
            const bool supported = (dynamicParams & required) == required;
            spdlog::info(
                "WheelFFB: {} dynamic params=0x{:08X}, required=0x{:08X}, live={}",
                label, (unsigned)dynamicParams, (unsigned)required, supported);
            return supported;
        }

        bool create_constant_effect()
        {
            if (!device_)
                return false;

            const bool liveMagnitude = query_dynamic_effect_capability(
                GUID_ConstantForce, "ConstantForce", DIEP_TYPESPECIFICPARAMS,
                constantCapsKnown_, constantDynamicParams_);
            if (constantCapsKnown_ && !liveMagnitude)
            {
                spdlog::warn(
                    "WheelFFB: ConstantForce metadata reports no live magnitude update support; probing the real zero-force update path anyway");
            }

            safe_release_effect(constantEffect_, "constant before create");
            constantEffectPolar_ = false;

            DWORD axes[2] = { DIJOFS_X, DIJOFS_Y };
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

            auto probe_live_update = [&](const char* descriptor, bool polar) -> HRESULT
            {
                if (!constantEffect_)
                    return E_POINTER;

                HRESULT hr = constantEffect_->Start(1, 0);
                if (FAILED(hr))
                {
                    spdlog::warn(
                        "WheelFFB: ConstantForce {} start probe failed (0x{:08X})",
                        descriptor, (unsigned)hr);
                    return hr;
                }

                DICONSTANTFORCE zeroForce{};
                LONG probeDirections[2] = { 9000L, 0L };
                DIEFFECT params{};
                params.dwSize = sizeof(params);
                params.cbTypeSpecificParams = sizeof(zeroForce);
                params.lpvTypeSpecificParams = &zeroForce;
                DWORD flags = DIEP_TYPESPECIFICPARAMS | DIEP_START;

                if (polar)
                {
                    params.dwFlags = DIEFF_POLAR | DIEFF_OBJECTOFFSETS;
                    params.cAxes = 2;
                    params.rglDirection = probeDirections;
                    flags |= DIEP_DIRECTION;

                    probeDirections[0] = 27000L;
                    hr = constantEffect_->SetParameters(&params, flags);
                    if (SUCCEEDED(hr))
                    {
                        probeDirections[0] = 9000L;
                        hr = constantEffect_->SetParameters(&params, flags);
                    }
                }
                else
                {
                    hr = constantEffect_->SetParameters(&params, flags);
                }

                if (FAILED(hr))
                {
                    spdlog::warn(
                        "WheelFFB: ConstantForce {} zero-force live SetParameters probe failed (0x{:08X})",
                        descriptor, (unsigned)hr);
                    constantEffect_->Stop();
                    return hr;
                }

                const HRESULT stopHr = constantEffect_->Stop();
                if (FAILED(stopHr))
                {
                    spdlog::warn(
                        "WheelFFB: ConstantForce {} zero-force probe Stop failed (0x{:08X})",
                        descriptor, (unsigned)stopHr);
                }
                return S_OK;
            };

            auto accept_candidate = [&](const char* descriptor, bool polar) -> HRESULT
            {
                const HRESULT probeHr = probe_live_update(descriptor, polar);
                if (FAILED(probeHr))
                    return probeHr;

                constantEffectPolar_ = polar;
                prevConstantLevel_ = 0;
                lastConstantWriteTick_ = 0;
                clear_constant_live_failure();
                spdlog::info(
                    "WheelFFB: ConstantForce validated with {} including zero-force live SetParameters",
                    descriptor);
                return S_OK;
            };

            HRESULT hr = E_FAIL;

            // Fanatec-style multi-interface drivers can report one physical
            // actuator while still requiring the legacy X/Y POLAR descriptor.
            effect.dwFlags = DIEFF_POLAR | DIEFF_OBJECTOFFSETS;
            effect.cAxes = 2;
            hr = device_->CreateEffect(
                GUID_ConstantForce, &effect, &constantEffect_, nullptr);
            if (SUCCEEDED(hr) && constantEffect_)
            {
                const HRESULT probeHr = accept_candidate("canonical X/Y 2-axis POLAR descriptor", true);
                if (SUCCEEDED(probeHr))
                    return true;
                hr = probeHr;
            }

            safe_release_effect(constantEffect_, "failed POLAR constant probe");
            spdlog::warn(
                "WheelFFB: X/Y POLAR ConstantForce unavailable; trying canonical one-axis X CARTESIAN");

            effect.dwFlags = DIEFF_CARTESIAN | DIEFF_OBJECTOFFSETS;
            effect.cAxes = 1;
            axes[0] = DIJOFS_X;
            directions[0] = 1;
            hr = device_->CreateEffect(
                GUID_ConstantForce, &effect, &constantEffect_, nullptr);
            if (SUCCEEDED(hr) && constantEffect_)
            {
                const HRESULT probeHr = accept_candidate("canonical one-axis X CARTESIAN descriptor", false);
                if (SUCCEEDED(probeHr))
                    return true;
                hr = probeHr;
            }

            safe_release_effect(constantEffect_, "failed X CARTESIAN constant probe");

            // A device may expose more than one FFB actuator object. X was
            // already tried above; probe every other reported actuator offset
            // once so enumeration order cannot hide the steering actuator.
            std::vector<DWORD> triedActuatorAxes{ DIJOFS_X };
            for (const DWORD detectedAxis : actuatorAxes_)
            {
                if (std::find(triedActuatorAxes.begin(), triedActuatorAxes.end(), detectedAxis) !=
                    triedActuatorAxes.end())
                    continue;
                triedActuatorAxes.push_back(detectedAxis);

                axes[0] = detectedAxis;
                hr = device_->CreateEffect(
                    GUID_ConstantForce, &effect, &constantEffect_, nullptr);
                if (SUCCEEDED(hr) && constantEffect_)
                {
                    const HRESULT probeHr = accept_candidate("detected actuator one-axis CARTESIAN descriptor", false);
                    if (SUCCEEDED(probeHr))
                    {
                        spdlog::info(
                            "WheelFFB: ConstantForce is using detected actuator offset {} instead of DIJOFS_X",
                            (unsigned)detectedAxis);
                        return true;
                    }
                    hr = probeHr;
                }
                safe_release_effect(constantEffect_, "failed detected-axis CARTESIAN constant probe");
            }

            const HRESULT failHr = FAILED(hr) ? hr : E_FAIL;
            mark_selected_interface_failed("ConstantForce create/start/live-update probe", failHr);
            spdlog::error(
                "WheelFFB: no usable ConstantForce descriptor on selected interface (0x{:08X})",
                (unsigned)failHr);
            return false;
        }

        bool create_spring_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareSpring)
                return false;
            if (!query_dynamic_effect_capability(
                    GUID_Spring, "GUID_Spring", DIEP_TYPESPECIFICPARAMS,
                    springCapsKnown_, springDynamicParams_))
            {
                spdlog::warn("WheelFFB: GUID_Spring is not safely live-updatable; using software centering");
                return false;
            }

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
                if (!reacquire_after_input_loss("GUID_Spring", hr))
                    return;
                hr = springEffect_->SetParameters(
                    &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
                if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
                {
                    note_device_failure("GUID_Spring retry", hr);
                    return;
                }
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
            if (!query_dynamic_effect_capability(
                    GUID_Damper, "GUID_Damper", DIEP_TYPESPECIFICPARAMS,
                    damperCapsKnown_, damperDynamicParams_))
            {
                spdlog::warn("WheelFFB: GUID_Damper is not safely live-updatable; using software damping");
                return false;
            }

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
                if (!reacquire_after_input_loss("GUID_Damper", hr))
                    return;
                hr = damperEffect_->SetParameters(
                    &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
                if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
                {
                    note_device_failure("GUID_Damper retry", hr);
                    return;
                }
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
            if (!query_dynamic_effect_capability(
                    GUID_Sine, "GUID_Sine", DIEP_TYPESPECIFICPARAMS,
                    periodicCapsKnown_, periodicDynamicParams_))
            {
                spdlog::warn("WheelFFB: GUID_Sine is not safely live-updatable; using ConstantForce vibration fallback");
                return nullptr;
            }

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
                if (!reacquire_after_input_loss("GUID_Sine periodic", hr))
                    return;
                hr = effect->SetParameters(
                    &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
                if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
                {
                    note_device_failure("GUID_Sine periodic retry", hr);
                    return;
                }
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

        void record_graph_sample(
            float rawStructural, float softLimited, float postSlew, float finalOutput,
            float xForceNormalized, float modernSat, float nativeSat, float nativeShare,
            float nativeTireNormalized, float nativeTireSat, float nativeTireShare,
            float rearSlipNormalized, float nativeOversteerCue,
            float nativeOversteerProtection)
        {
            const size_t slot = graphWriteIndex_ % WheelFFBGraphCapacity;
            graphRawStructural_[slot] = std::isfinite(rawStructural) ? rawStructural : 0.0f;
            graphSoftLimited_[slot] = std::isfinite(softLimited) ? softLimited : 0.0f;
            graphPostSlew_[slot] = std::isfinite(postSlew) ? postSlew : 0.0f;
            graphFinalOutput_[slot] = std::isfinite(finalOutput) ? finalOutput : 0.0f;
            graphXForceNormalized_[slot] = std::isfinite(xForceNormalized) ? xForceNormalized : 0.0f;
            graphModernSat_[slot] = std::isfinite(modernSat) ? modernSat : 0.0f;
            graphNativeSat_[slot] = std::isfinite(nativeSat) ? nativeSat : 0.0f;
            graphNativeShare_[slot] = std::isfinite(nativeShare)
                ? std::clamp(nativeShare, 0.0f, 1.0f) : 0.0f;
            graphNativeTireNormalized_[slot] = std::isfinite(nativeTireNormalized)
                ? std::clamp(nativeTireNormalized, -1.0f, 1.0f) : 0.0f;
            graphNativeTireSat_[slot] = std::isfinite(nativeTireSat) ? nativeTireSat : 0.0f;
            graphNativeTireShare_[slot] = std::isfinite(nativeTireShare)
                ? std::clamp(nativeTireShare, 0.0f, 1.0f) : 0.0f;
            graphRearSlipNormalized_[slot] = std::isfinite(rearSlipNormalized)
                ? std::clamp(rearSlipNormalized, 0.0f, 3.0f) : 0.0f;
            graphNativeOversteerCue_[slot] = std::isfinite(nativeOversteerCue)
                ? nativeOversteerCue : 0.0f;
            graphNativeOversteerProtection_[slot] = std::isfinite(nativeOversteerProtection)
                ? std::clamp(nativeOversteerProtection, 0.0f, 1.0f) : 0.0f;
            ++graphWriteIndex_;
            graphCount_ = std::min<std::size_t>(graphCount_ + 1, WheelFFBGraphCapacity);
        }

        void record_headroom(float demand, bool eligible)
        {
            if (!std::isfinite(demand))
                return;
            demand = std::max(0.0f, demand);
            headroomCurrentDemand_ = demand;
            if (!eligible)
                return;

            headroomPeakDemand_ = std::max(headroomPeakDemand_, demand);
            ++headroomSamples_;
            if (demand > 0.75f)
                ++headroomSoftKneeSamples_;
            if (demand >= 1.35f)
                ++headroomHardClipSamples_;

            const float normalized = std::clamp(demand / HeadroomHistogramMax, 0.0f, 1.0f);
            const size_t bin = std::min<size_t>(
                HeadroomHistogramBins - 1,
                static_cast<size_t>(std::lround(
                    normalized * static_cast<float>(HeadroomHistogramBins - 1))));
            ++headroomHistogram_[bin];
        }

        LONG apply_response_correction(LONG requestedLevel)
        {
            if (!Settings::WheelFFBResponseCorrection || requestedLevel == 0)
                return requestedLevel;

            const std::string spec = Settings::WheelFFBResponseLUT.get();
            if (spec != responseLutSpec_)
            {
                responseLutSpec_ = spec;
                WheelFFBMath::ResponseLUT parsed{};
                responseLutValid_ = WheelFFBMath::parse_response_lut(spec, parsed);
                if (responseLutValid_)
                {
                    responseLut_ = parsed;
                    spdlog::info("WheelFFB: loaded valid wheel response LUT");
                }
                else
                {
                    responseLut_ = WheelFFBMath::linear_response_lut();
                    spdlog::warn(
                        "WheelFFB: invalid ResponseLUT; leaving ConstantForce linear until corrected");
                }
            }

            if (!responseLutValid_)
                return requestedLevel;

            const float normalized =
                static_cast<float>(requestedLevel) / static_cast<float>(DI_FFNOMINALMAX);
            const float corrected = WheelFFBMath::apply_response_lut(normalized, responseLut_);
            return std::clamp(
                static_cast<LONG>(std::lround(corrected * static_cast<float>(DI_FFNOMINALMAX))),
                -static_cast<LONG>(DI_FFNOMINALMAX),
                static_cast<LONG>(DI_FFNOMINALMAX));
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
                // Input loss is a transient ownership/focus condition, not proof
                // that this physical DirectInput interface is the wrong FFB port.
                // Preserve the grace window before any device reinitialization.
                if (!reacquire_after_input_loss("ConstantForce", hr) || !constantEffect_)
                    return;
                hr = constantEffect_->SetParameters(&params, flags);
                if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
                {
                    note_device_failure("ConstantForce retry", hr);
                    return;
                }
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
                clear_constant_live_failure();
                spdlog::info("WheelFFB: recreated ConstantForce after handle loss; ramping in");
                return;
            }

            if (FAILED(hr))
            {
                if (!record_constant_live_failure())
                {
                    note_device_failure("ConstantForce live SetParameters", hr);
                    spdlog::warn(
                        "WheelFFB: transient ConstantForce update failure {}/{} (0x{:08X}); retaining the current interface",
                        constantLiveFailureCount_, FFB_CONSTANT_LIVE_FAILURE_LIMIT, (unsigned)hr);
                    return;
                }

                mark_selected_interface_failed("ConstantForce live SetParameters", hr);
                request_device_reinitialize("ConstantForce output failed repeatedly", hr);
                spdlog::warn(
                    "WheelFFB: ConstantForce update failed {} consecutive times (0x{:08X}); current interface will be skipped on reinitialization",
                    constantLiveFailureCount_, (unsigned)hr);
                return;
            }

            clear_constant_live_failure();
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
            xForceGuard_.reset();
            xForceAnalyzer_.reset();
            lastXForceFrameTick_ = 0;
            smoothedXForceMix_ = -1.0f;
            smoothedXForceGain_ = -1.0f;
            nativeTireSatBlend_ = 0.0f;
            nativeOversteerProtectionBlend_ = 0.0f;
            driftRegripGuard_.reset();
            prevStructuralLevel_ = 0;
            prevSpringCoefficient_ = 0;
            prevDamperCoefficient_ = 0;
            crashImpulseTimer_ = 0;
            crashImpulseForce_ = 0.0f;
            gearShiftTimer_ = 0;
            warmupFrames_ = 0;
            roadPhase_ = 0.0f;
            slipPhase_ = 0.0f;
            enginePhase_ = 0.0f;
            smoothedEngineRpm_ = 0.0f;
            smoothedEngineAmp_ = 0.0f;
            smoothedEngineFreq_ = 0.0f;
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
        DWORD lastXForceFrameTick_ = 0;
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
        bool directionTested_ = false;
        bool constantCapsKnown_ = false;
        bool springCapsKnown_ = false;
        bool damperCapsKnown_ = false;
        bool periodicCapsKnown_ = false;
        DWORD constantDynamicParams_ = 0;
        DWORD springDynamicParams_ = 0;
        DWORD damperDynamicParams_ = 0;
        DWORD periodicDynamicParams_ = 0;
        int periodicStrategy_ = 1; // Explicitly restart sine effects on every update.
        int springStrategy_ = -1;
        int damperStrategy_ = -1;

        DWORD retryAfter_ = 0;
        std::vector<FailedInterfaceState> failedInterfaces_;
        DWORD preferredVidPid_ = 0;
        GUID preferredProductGuid_{};
        GUID preferredFFDriverGuid_{};
        WORD preferredVendorId_ = 0;
        DWORD constantRecreateHoldoffUntil_ = 0;
        DWORD periodicRecreateHoldoffUntil_ = 0;
        DWORD springRecreateHoldoffUntil_ = 0;
        DWORD damperRecreateHoldoffUntil_ = 0;
        DWORD lastUpdateTick_ = 0;
        DWORD lastLogTick_ = 0;
        DWORD deviceFailureSince_ = 0;
        unsigned constantLiveFailureCount_ = 0;
        DWORD deviceReinitAfter_ = 0;
        bool deviceReinitPending_ = false;

        PeriodicState roadState_{};
        PeriodicState slipState_{};

        float smoothedLateral_ = 0.0f;
        float smoothedLongAccel_ = 0.0f;
        float smoothedXForceMix_ = -1.0f;
        float smoothedXForceGain_ = -1.0f;
        float nativeTireSatBlend_ = 0.0f;
        float nativeOversteerProtectionBlend_ = 0.0f;
        WheelFFBMath::DriftRegripGuard driftRegripGuard_{};
        float prevSteer_ = 0.0f;
        float smoothedSteerRate_ = 0.0f;
        bool steerSampleValid_ = false;
        WheelVehicleDynamics vehicleDynamics_{};
        WheelFFBMath::XForceGuard xForceGuard_{};
        WheelFFBMath::XForceSignalAnalyzer xForceAnalyzer_{};

        std::array<std::uint64_t, HeadroomHistogramBins> headroomHistogram_{};
        std::uint64_t headroomSamples_ = 0;
        std::uint64_t headroomSoftKneeSamples_ = 0;
        std::uint64_t headroomHardClipSamples_ = 0;
        float headroomCurrentDemand_ = 0.0f;
        float headroomPeakDemand_ = 0.0f;

        std::array<float, WheelFFBGraphCapacity> graphRawStructural_{};
        std::array<float, WheelFFBGraphCapacity> graphSoftLimited_{};
        std::array<float, WheelFFBGraphCapacity> graphPostSlew_{};
        std::array<float, WheelFFBGraphCapacity> graphFinalOutput_{};
        std::array<float, WheelFFBGraphCapacity> graphXForceNormalized_{};
        std::array<float, WheelFFBGraphCapacity> graphModernSat_{};
        std::array<float, WheelFFBGraphCapacity> graphNativeSat_{};
        std::array<float, WheelFFBGraphCapacity> graphNativeShare_{};
        std::array<float, WheelFFBGraphCapacity> graphNativeTireNormalized_{};
        std::array<float, WheelFFBGraphCapacity> graphNativeTireSat_{};
        std::array<float, WheelFFBGraphCapacity> graphNativeTireShare_{};
        std::array<float, WheelFFBGraphCapacity> graphRearSlipNormalized_{};
        std::array<float, WheelFFBGraphCapacity> graphNativeOversteerCue_{};
        std::array<float, WheelFFBGraphCapacity> graphNativeOversteerProtection_{};
        std::size_t graphWriteIndex_ = 0;
        std::size_t graphCount_ = 0;

        WheelFFBMath::ResponseLUT responseLut_ = WheelFFBMath::linear_response_lut();
        std::string responseLutSpec_;
        bool responseLutValid_ = true;

        float crashImpulseForce_ = 0.0f;
        float roadPhase_ = 0.0f;
        float slipPhase_ = 0.0f;
        float enginePhase_ = 0.0f;
        float smoothedEngineRpm_ = 0.0f;
        float smoothedEngineAmp_ = 0.0f;
        float smoothedEngineFreq_ = 0.0f;
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

void WheelFFB_ResetDirectionTest()
{
    gWheelFFB.reset_direction_test();
}

WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot()
{
    return gWheelFFB.headroom_snapshot();
}

WheelFFBStatusSnapshot WheelFFB_GetStatusSnapshot()
{
    return gWheelFFB.status_snapshot();
}

WheelFFBGraphSnapshot WheelFFB_GetGraphSnapshot()
{
    return gWheelFFB.graph_snapshot();
}

WheelFFBXForceAnalysisSnapshot WheelFFB_GetXForceAnalysisSnapshot()
{
    return gWheelFFB.xforce_analysis_snapshot();
}

void WheelFFB_ResetHeadroomStats()
{
    gWheelFFB.reset_headroom_stats();
}
