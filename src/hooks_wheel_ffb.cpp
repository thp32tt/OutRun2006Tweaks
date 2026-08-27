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
#include <string>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"

extern "C"
{
    void __cdecl CalcVibrationValues(EVWORK_CAR* car);
}

extern double __cdecl sub_1149C0(unsigned int surfaceMask, int loadColiType, DWORD* waterFlag);

namespace Settings
{
    // Experimental branch: enabled by default, but deliberately conservative for DD wheels.
    Setting<bool> WheelFFBEnable{
        "WheelFFB", "Enable", true,
        "Enable experimental DirectInput COM force feedback for steering wheels."
    };

    Setting<std::string> WheelFFBDeviceName{
        "WheelFFB", "DeviceName", "MOZA",
        "Case-insensitive substring used to select the FFB wheel. Empty selects the first non-virtual FFB device."
    };

    Setting<float> WheelFFBGlobalStrength{
        "WheelFFB", "GlobalStrength", 0.25f,
        "Master DirectInput effect gain. Start low on direct-drive wheels.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBSpringStrength{
        "WheelFFB", "SpringStrength", 0.45f,
        "Speed-dependent center restoring force.", Range<float>{ 0.0f, 1.5f }
    };

    Setting<float> WheelFFBDamperStrength{
        "WheelFFB", "DamperStrength", 0.10f,
        "Resistance to rapid steering movement.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBSteeringWeight{
        "WheelFFB", "SteeringWeight", 0.45f,
        "Cornering load from OutRun lateral physics.", Range<float>{ 0.0f, 1.5f }
    };

    Setting<float> WheelFFBGripLoss{
        "WheelFFB", "GripLoss", 0.60f,
        "How much cornering load unloads as the car enters a deep drift.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBLateralDeadzone{
        "WheelFFB", "LateralDeadzone", 1.5f,
        "Subtractive noise floor for the game's lateral force signal.", Range<float>{ 0.0f, 8.0f }
    };

    Setting<float> WheelFFBWeightTransfer{
        "WheelFFB", "WeightTransfer", 0.60f,
        "Longitudinal acceleration/braking modulation of steering load.", Range<float>{ 0.0f, 1.5f }
    };

    Setting<float> WheelFFBWallImpact{
        "WheelFFB", "WallImpact", 0.35f,
        "Collision impulse strength.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBGearShift{
        "WheelFFB", "GearShift", 0.18f,
        "Symmetric gear-change thunk strength.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBRoadTexture{
        "WheelFFB", "RoadTexture", 0.20f,
        "Hardware sine vibration driven by the game's own surface roughness table.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBTireSlip{
        "WheelFFB", "TireSlip", 0.18f,
        "Hardware sine chatter as drift depth increases.", Range<float>{ 0.0f, 1.0f }
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
        "WheelFFB", "InvertForce", false,
        "Reverse steering force direction."
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

    std::string lower_copy(const char* text)
    {
        std::string result = text ? text : "";
        std::transform(result.begin(), result.end(), result.begin(),
            [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        return result;
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
            if (!Settings::WheelFFBEnable || !car || panicStopped_)
                return;

            lastUpdateTick_ = GetTickCount();

            if (!initialized_)
            {
                if (GetTickCount() < retryAfter_)
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
                reset_signal_state();
                return;
            }

            float steer = read_game_steering();
            float steerRate = steer - prevSteer_;
            prevSteer_ = steer;

            // field_1C4 reaches roughly 2.0 at OutRun top speed. Normalize by 2
            // rather than treating 1.0 as terminal speed.
            const float speed = car->field_1C4;
            const float speedNorm = std::clamp(speed / 2.0f, 0.0f, 1.0f);

            const uint32_t stateFlags = car->field_8;
            const uint32_t curGear = car->cur_gear_208;
            const float lateralRaw = car->field_264 + car->field_268;

            // Fast attack / slightly slower release. This is intentionally close
            // to the Redux-era tuning, but the steering backbone comes from the
            // real game input instead of car->field_1D0.
            const float alpha =
                std::abs(lateralRaw) > std::abs(smoothedLateral_) ? 0.25f : 0.20f;
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

            const float latNorm = std::clamp(lateralDz / 24.0f, -1.0f, 1.0f);
            const float driftAmt =
                std::clamp((std::abs(smoothedLateral_) - 12.0f) / 12.0f, 0.0f, 1.0f);
            const float gripFactor =
                1.0f - static_cast<float>(Settings::WheelFFBGripLoss) * driftAmt;

            speedHistory_[speedHistoryIndex_ % SpeedHistoryCount] = speed;
            ++speedHistoryIndex_;

            update_crash_detection(speed, stateFlags);
            update_gear_event(curGear);

            float roughness = 0.0f;
            DWORD waterFlag = 0;
            for (int i = 0; i < 4; ++i)
            {
                roughness = std::max(
                    roughness,
                    static_cast<float>(sub_1149C0(
                        car->water_flag_24C[i],
                        static_cast<int>(car->OnRoadPlace_5C.loadColiType_0),
                        &waterFlag)));
            }

            // Road texture and tire-slip envelopes.
            float roadAmp =
                roughness * speedNorm * static_cast<float>(Settings::WheelFFBRoadTexture);
            const float roadFreq = 25.0f + 12.0f * speedNorm;

            if (waterFlag && roughness > 0.7f && speedNorm > 0.70f && splashTimer_ <= 0)
            {
                splashAmp_ = (roughness - 0.7f) * speedNorm * 0.75f;
                splashTimer_ = 9;
            }
            if (splashTimer_ > 0)
            {
                roadAmp = std::max(roadAmp, splashAmp_);
                --splashTimer_;
            }

            float slipAmp = 0.0f;
            float slipFreq = 40.0f;
            if (driftAmt > 0.15f && speedNorm > 0.05f)
            {
                slipAmp = driftAmt * static_cast<float>(Settings::WheelFFBTireSlip);
                slipFreq = 40.0f - 12.0f * driftAmt;
            }
            else if (speedNorm < 0.03f && car->pedal_amount_34 > 0)
            {
                const float throttleNorm =
                    std::clamp(static_cast<float>(car->pedal_amount_34) / 255.0f, 0.0f, 1.0f);
                slipAmp =
                    static_cast<float>(Settings::WheelFFBEngineIdle) * throttleNorm;
                slipFreq = 15.0f + 7.0f * throttleNorm;
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

            // Center-out arcade model.
            const float speedCurve =
                std::clamp(speedNorm / 0.25f, 0.0f, 1.0f) *
                (0.35f + 0.65f * speedNorm);

            const float spring =
                -steer * static_cast<float>(Settings::WheelFFBSpringStrength) * speedCurve;

            // Because steer comes from the real input path, derive rate from it
            // here instead of using the unverified field_1D4.
            constexpr float SteerRateScale = 10.0f;
            const float damper =
                -steerRate * SteerRateScale *
                static_cast<float>(Settings::WheelFFBDamperStrength) *
                (0.4f + 0.6f * speedNorm);

            const float lateral =
                latNorm * speedNorm *
                static_cast<float>(Settings::WheelFFBSteeringWeight) *
                gripFactor;

            float loadMod = 1.0f;
            if (speedHistoryIndex_ > 6)
            {
                const float oldSpeed =
                    speedHistory_[(speedHistoryIndex_ - 6) % SpeedHistoryCount];
                const float longAccel = (speed - oldSpeed) * 5.0f;
                loadMod = 1.0f + std::clamp(
                    -longAccel * static_cast<float>(Settings::WheelFFBWeightTransfer),
                    -0.20f, 0.30f);
            }

            float structural = 0.0f;
            if (crashImpulseTimer_ <= CrashCooldownFrames)
                structural = (spring + lateral) * loadMod + damper;

            float events = update_event_force();

            float total = structural + events;
            if (Settings::WheelFFBInvertForce)
                total = -total;

            total *= warmupScale * recreateScale;

            // Soft saturation preserves detail near the force cap.
            const float compressed = std::tanh(total);

            LONG structuralLevel =
                static_cast<LONG>(compressed * static_cast<float>(DI_FFNOMINALMAX));

            const LONG maxSlew = static_cast<LONG>(
                std::clamp(static_cast<float>(Settings::WheelFFBSlewRate), 0.01f, 1.0f) *
                static_cast<float>(DI_FFNOMINALMAX));

            const LONG structuralDelta = structuralLevel - prevStructuralLevel_;
            const bool bypassSlew =
                crashImpulseTimer_ > CrashCooldownFrames || gearShiftTimer_ > 0;

            if (std::abs(structuralDelta) > maxSlew && !bypassSlew)
            {
                structuralLevel = prevStructuralLevel_ +
                    (structuralDelta > 0 ? maxSlew : -maxSlew);
            }
            prevStructuralLevel_ = structuralLevel;

            // Hardware periodics are preferred. If unavailable, inject a capped
            // low-frequency sine after the tanh compressor.
            float fallbackVibration = 0.0f;
            if (!periodicsActive_)
            {
                fallbackVibration += synth_fallback(
                    roadPhase_, roadAmp, std::min(roadFreq, 15.0f));
                fallbackVibration += synth_fallback(
                    slipPhase_, slipAmp, std::min(slipFreq, 15.0f));
            }

            const LONG level = std::clamp(
                structuralLevel +
                    static_cast<LONG>(fallbackVibration * static_cast<float>(DI_FFNOMINALMAX)),
                -static_cast<LONG>(DI_FFNOMINALMAX),
                static_cast<LONG>(DI_FFNOMINALMAX));

            if (std::abs(level - prevConstantLevel_) > 15 || bypassSlew)
                set_constant_force(level);

            ++updateCounter_;
            if (periodicsActive_ && (updateCounter_ % 4) == 0)
            {
                update_periodic(roadTextureEffect_, roadState_, roadAmp, roadFreq);
                update_periodic(tireSlipEffect_, slipState_, slipAmp, slipFreq);
            }

            if (Settings::WheelFFBUsePeriodicEffects &&
                (!roadTextureEffect_ || !tireSlipEffect_) &&
                (updateCounter_ % 60) == 0 &&
                GetTickCount() >= recreateHoldoffUntil_)
            {
                create_periodic_effects();
            }

            prevGear_ = curGear;
            prevCollisionFlags_ = stateFlags;
            maybe_log(speedNorm, steer, steerRate, driftAmt, roughness, level);
        }

        void check_watchdog()
        {
            if (!initialized_ || panicStopped_ || lastUpdateTick_ == 0)
                return;

            const DWORD elapsed = GetTickCount() - lastUpdateTick_;
            if (elapsed > 250 && prevConstantLevel_ != 0)
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
                DICONSTANTFORCE cf{};
                DIEFFECT eff{};
                eff.dwSize = sizeof(eff);
                eff.cbTypeSpecificParams = sizeof(cf);
                eff.lpvTypeSpecificParams = &cf;

                HRESULT hr = constantEffect_->SetParameters(
                    &eff, DIEP_TYPESPECIFICPARAMS | DIEP_START);
                spdlog::info("WheelFFB: PanicStop constant zero => 0x{:08X}", (unsigned)hr);
                hr = constantEffect_->Stop();
                spdlog::info("WheelFFB: PanicStop constant Stop => 0x{:08X}", (unsigned)hr);
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
            spdlog::info("WheelFFB: PanicStop Unacquire => 0x{:08X}", (unsigned)hr);

            DIPROPDWORD autocenter{};
            autocenter.diph.dwSize = sizeof(autocenter);
            autocenter.diph.dwHeaderSize = sizeof(DIPROPHEADER);
            autocenter.diph.dwObj = 0;
            autocenter.diph.dwHow = DIPH_DEVICE;
            autocenter.dwData = DIPROPAUTOCENTER_ON;
            hr = device_->SetProperty(DIPROP_AUTOCENTER, &autocenter.diph);
            spdlog::info("WheelFFB: PanicStop autocenter restore => 0x{:08X}", (unsigned)hr);
        }

    private:
        struct PeriodicState
        {
            DWORD lastMagnitude = 0;
            DWORD lastPeriod = 0;
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
        };

        static BOOL CALLBACK enum_devices_callback(
            LPCDIDEVICEINSTANCEA instance, LPVOID context)
        {
            auto* ctx = static_cast<EnumContext*>(context);
            const std::string instanceName = lower_copy(instance->tszInstanceName);
            const std::string productName = lower_copy(instance->tszProductName);
            const std::string wanted =
                lower_copy(Settings::WheelFFBDeviceName.get().c_str());

            if (is_virtual_device_name(instanceName) ||
                is_virtual_device_name(productName))
            {
                spdlog::info(
                    "WheelFFB: skipping virtual FFB device '{}'",
                    instance->tszInstanceName);
                return DIENUM_CONTINUE;
            }

            if (!wanted.empty() &&
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

            hr = directInput_->EnumDevices(
                DI8DEVCLASS_GAMECTRL,
                enum_devices_callback,
                &ctx,
                DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);

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

            hr = directInput_->CreateDevice(selectedGuid_, &device_, nullptr);
            if (FAILED(hr) || !device_)
            {
                spdlog::error(
                    "WheelFFB: CreateDevice('{}') failed (0x{:08X})",
                    selectedName_, (unsigned)hr);
                release_directinput();
                return false;
            }

            DIDEVCAPS caps{};
            caps.dwSize = sizeof(caps);
            device_->GetCapabilities(&caps);

            if ((caps.dwFlags & DIDC_FORCEFEEDBACK) == 0)
            {
                spdlog::error("WheelFFB: '{}' does not report force-feedback capability", selectedName_);
                release_device();
                release_directinput();
                return false;
            }

            hr = device_->SetDataFormat(&c_dfDIJoystick2);
            if (FAILED(hr))
            {
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

            hr = device_->SetCooperativeLevel(
                gameHwnd_,
                DISCL_EXCLUSIVE | DISCL_BACKGROUND);

            if (FAILED(hr))
            {
                spdlog::error(
                    "WheelFFB: SetCooperativeLevel(EXCLUSIVE|BACKGROUND) failed (0x{:08X})",
                    (unsigned)hr);
                release_device();
                release_directinput();
                return false;
            }

            // Disable driver centering before acquiring. Restored by PanicStop.
            DIPROPDWORD autocenter{};
            autocenter.diph.dwSize = sizeof(autocenter);
            autocenter.diph.dwHeaderSize = sizeof(DIPROPHEADER);
            autocenter.diph.dwObj = 0;
            autocenter.diph.dwHow = DIPH_DEVICE;
            autocenter.dwData = DIPROPAUTOCENTER_OFF;
            hr = device_->SetProperty(DIPROP_AUTOCENTER, &autocenter.diph);
            if (FAILED(hr))
                spdlog::warn("WheelFFB: disabling driver autocenter failed (0x{:08X})", (unsigned)hr);

            hr = device_->Acquire();
            if (FAILED(hr))
            {
                spdlog::error("WheelFFB: Acquire('{}') failed (0x{:08X})", selectedName_, (unsigned)hr);
                release_device();
                release_directinput();
                return false;
            }

            device_->SendForceFeedbackCommand(DISFFC_SETACTUATORSON);

            if (!create_constant_effect())
            {
                release_device();
                release_directinput();
                return false;
            }

            create_periodic_effects();
            install_exit_guards();

            initialized_ = true;
            reset_signal_state();

            spdlog::info(
                "WheelFFB: ready on '{}' (DirectInput COM, axes={}, buttons={}, global={}%)",
                selectedName_,
                caps.dwAxes,
                caps.dwButtons,
                static_cast<int>(static_cast<float>(Settings::WheelFFBGlobalStrength) * 100.0f));

            return true;
        }

        float read_game_steering() const
        {
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

            DWORD axes[1] = { DIJOFS_X };
            LONG directions[1] = { 0 };
            DICONSTANTFORCE cf{};
            cf.lMagnitude = 0;

            DIEFFECT effect{};
            effect.dwSize = sizeof(effect);
            effect.dwFlags = DIEFF_CARTESIAN | DIEFF_OBJECTOFFSETS;
            effect.dwDuration = INFINITE;
            effect.dwSamplePeriod = 0;
            effect.dwGain = static_cast<DWORD>(
                std::clamp(static_cast<float>(Settings::WheelFFBGlobalStrength), 0.0f, 1.0f) *
                static_cast<float>(DI_FFNOMINALMAX));
            effect.dwTriggerButton = DIEB_NOTRIGGER;
            effect.dwTriggerRepeatInterval = 0;
            effect.cAxes = 1;
            effect.rgdwAxes = axes;
            effect.rglDirection = directions;
            effect.cbTypeSpecificParams = sizeof(cf);
            effect.lpvTypeSpecificParams = &cf;

            HRESULT hr = device_->CreateEffect(
                GUID_ConstantForce, &effect, &constantEffect_, nullptr);

            if (FAILED(hr) || !constantEffect_)
            {
                spdlog::error(
                    "WheelFFB: CreateEffect(ConstantForce) failed (0x{:08X})",
                    (unsigned)hr);
                return false;
            }

            spdlog::info("WheelFFB: ConstantForce created");
            return true;
        }

        IDirectInputEffect* create_periodic_effect(const char* label, float initialHz)
        {
            if (!device_)
                return nullptr;

            DWORD axes[1] = { DIJOFS_X };
            LONG directions[1] = { 0 };
            DIPERIODIC periodic{};
            periodic.dwMagnitude = 0;
            periodic.lOffset = 0;
            periodic.dwPhase = 0;
            periodic.dwPeriod = static_cast<DWORD>(1000000.0f / initialHz);

            DIEFFECT effect{};
            effect.dwSize = sizeof(effect);
            effect.dwFlags = DIEFF_CARTESIAN | DIEFF_OBJECTOFFSETS;
            effect.dwDuration = INFINITE;
            effect.dwGain = static_cast<DWORD>(
                std::clamp(static_cast<float>(Settings::WheelFFBGlobalStrength), 0.0f, 1.0f) *
                static_cast<float>(DI_FFNOMINALMAX));
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
                spdlog::warn("WheelFFB: hardware periodic effects unavailable; using constant-force fallback");
        }

        void update_periodic(
            IDirectInputEffect*& effect,
            PeriodicState& state,
            float magnitude,
            float frequency)
        {
            if (!effect || panicStopped_)
                return;

            const DWORD mag = static_cast<DWORD>(
                std::clamp(magnitude, 0.0f, 1.0f) *
                static_cast<float>(DI_FFNOMINALMAX));
            frequency = std::clamp(frequency, 1.0f, 100.0f);
            const DWORD period = static_cast<DWORD>(1000000.0f / frequency);

            const bool silence = mag == 0 && state.lastMagnitude != 0;
            const bool magChanged =
                std::abs(static_cast<long>(mag) - static_cast<long>(state.lastMagnitude)) > 300;
            const bool periodChanged =
                state.lastPeriod != 0 &&
                std::abs(static_cast<long>(period) - static_cast<long>(state.lastPeriod)) * 10 >
                    static_cast<long>(state.lastPeriod);

            if (!silence && !magChanged && !periodChanged)
                return;

            DIPERIODIC periodic{};
            periodic.dwMagnitude = mag;
            periodic.dwPeriod = period;

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

            if (FAILED(hr))
            {
                spdlog::warn(
                    "WheelFFB: periodic update failed (0x{:08X}); falling back to ConstantForce vibration",
                    (unsigned)hr);
                disable_periodics();
                recreateHoldoffUntil_ = GetTickCount() + 500;
                return;
            }

            state.lastMagnitude = mag;
            state.lastPeriod = period;
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

            DICONSTANTFORCE cf{};
            cf.lMagnitude = requestedLevel;

            DIEFFECT params{};
            params.dwSize = sizeof(params);
            params.cbTypeSpecificParams = sizeof(cf);
            params.lpvTypeSpecificParams = &cf;

            HRESULT hr = E_FAIL;
            if (constantEffect_)
            {
                hr = constantEffect_->SetParameters(
                    &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
            }

            if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
            {
                device_->Acquire();
                if (constantEffect_)
                {
                    hr = constantEffect_->SetParameters(
                        &params, DIEP_TYPESPECIFICPARAMS | DIEP_START);
                }
            }

            if (hr == E_HANDLE || hr == DIERR_NOTDOWNLOADED || !constantEffect_)
            {
                safe_release_effect(constantEffect_, "stale constant");

                const DWORD now = GetTickCount();
                if (now < recreateHoldoffUntil_)
                    return;

                if (!create_constant_effect())
                {
                    recreateHoldoffUntil_ = now + 500;
                    return;
                }

                DICONSTANTFORCE zero{};
                DIEFFECT zeroParams{};
                zeroParams.dwSize = sizeof(zeroParams);
                zeroParams.cbTypeSpecificParams = sizeof(zero);
                zeroParams.lpvTypeSpecificParams = &zero;

                constantEffect_->SetParameters(
                    &zeroParams, DIEP_TYPESPECIFICPARAMS | DIEP_START);

                recreateRampFrames_ = RecreateRampFrames;
                prevConstantLevel_ = 0;
                prevStructuralLevel_ = 0;

                spdlog::info(
                    "WheelFFB: recreated ConstantForce after handle loss; ramping in");
                return;
            }

            if (FAILED(hr))
            {
                spdlog::warn(
                    "WheelFFB: constant force update failed (0x{:08X})",
                    (unsigned)hr);
                return;
            }

            prevConstantLevel_ = requestedLevel;
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

                    crashImpulseForce_ =
                        direction * 1.5f *
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
                    direction * 1.2f *
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
                    float envelope = 1.0f;
                    if (crashImpulseTimer_ <= 85)
                    {
                        envelope =
                            static_cast<float>(crashImpulseTimer_ - CrashCooldownFrames) /
                            5.0f;
                    }
                    result += crashImpulseForce_ * envelope;
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
            if (amplitude <= 0.005f)
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

            prevStructuralLevel_ = 0;

            if (roadTextureEffect_)
                update_periodic(roadTextureEffect_, roadState_, 0.0f, 30.0f);
            if (tireSlipEffect_)
                update_periodic(tireSlipEffect_, slipState_, 0.0f, 35.0f);
        }

        void reset_signal_state()
        {
            smoothedLateral_ = 0.0f;
            prevSteer_ = 0.0f;
            prevStructuralLevel_ = 0;
            crashImpulseTimer_ = 0;
            crashImpulseForce_ = 0.0f;
            gearShiftTimer_ = 0;
            warmupFrames_ = 0;
            roadPhase_ = 0.0f;
            slipPhase_ = 0.0f;
            splashTimer_ = 0;
            splashAmp_ = 0.0f;
        }

        void install_exit_guards()
        {
            if (!gameHwnd_)
                return;

            if (SetWindowSubclass(
                    gameHwnd_,
                    window_subclass_proc,
                    FFB_SUBCLASS_ID,
                    reinterpret_cast<DWORD_PTR>(this)))
            {
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

            if (auto* exitProc =
                    GetProcAddress(GetModuleHandleA("kernel32.dll"), "ExitProcess"))
            {
                exitProcessHook_ =
                    safetyhook::create_inline(exitProc, exit_process_hook);
                if (exitProcessHook_)
                    spdlog::info("WheelFFB: ExitProcess safety hook installed");
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
                    if (wParam == FALSE)
                        self->zero_all_forces();
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

        void release_device()
        {
            if (!device_)
                return;
            __try
            {
                device_->Unacquire();
                device_->Release();
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                spdlog::warn(
                    "WheelFFB: exception releasing DirectInput device (0x{:X})",
                    GetExceptionCode());
            }
            device_ = nullptr;
        }

        void release_directinput()
        {
            if (!directInput_)
                return;
            directInput_->Release();
            directInput_ = nullptr;
        }

        void maybe_log(
            float speedNorm,
            float steer,
            float steerRate,
            float driftAmt,
            float roughness,
            LONG level)
        {
            if (!Settings::WheelFFBDebugLog)
                return;

            const DWORD now = GetTickCount();
            if (now - lastLogTick_ < 2000)
                return;

            lastLogTick_ = now;
            spdlog::info(
                "WheelFFB DIAG: spd={:.2f} steer={:.3f} rate={:.4f} lat={:.2f} drift={:.2f} rough={:.2f} out={} periodic={}",
                speedNorm,
                steer,
                steerRate,
                smoothedLateral_,
                driftAmt,
                roughness,
                static_cast<int>(level),
                periodicsActive_);
        }

        IDirectInput8A* directInput_ = nullptr;
        IDirectInputDevice8A* device_ = nullptr;
        IDirectInputEffect* constantEffect_ = nullptr;
        IDirectInputEffect* roadTextureEffect_ = nullptr;
        IDirectInputEffect* tireSlipEffect_ = nullptr;

        GUID selectedGuid_{};
        std::string selectedName_;
        HWND gameHwnd_ = nullptr;

        bool initialized_ = false;
        bool panicStopped_ = false;
        bool periodicsActive_ = false;
        int periodicStrategy_ = -1;

        DWORD retryAfter_ = 0;
        DWORD recreateHoldoffUntil_ = 0;
        DWORD lastUpdateTick_ = 0;
        DWORD lastLogTick_ = 0;

        PeriodicState roadState_{};
        PeriodicState slipState_{};

        float smoothedLateral_ = 0.0f;
        float prevSteer_ = 0.0f;
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

        int crashImpulseTimer_ = 0;
        int gearShiftTimer_ = 0;
        int warmupFrames_ = 0;
        int recreateRampFrames_ = 0;
        int splashTimer_ = 0;
        unsigned updateCounter_ = 0;

        SafetyHookInline exitProcessHook_{};

        inline static WheelFFBEngine* activeEngine_ = nullptr;
    };

    WheelFFBEngine gWheelFFB;

    class WheelFFBHook : public Hook
    {
        inline static SafetyHookInline CalcVibrationHook_ = {};

        static void __cdecl calc_vibration_hook(EVWORK_CAR* car)
        {
            CalcVibrationHook_.ccall<void>(car);
            gWheelFFB.update(car);
        }

    public:
        std::string_view description() override
        {
            return "WheelFFB (DirectInput COM)";
        }

        bool validate() override
        {
            return Settings::WheelFFBEnable;
        }

        bool apply() override
        {
            // Hook Tweaks' Xbox vibration calculation instead of installing a
            // second GamePlCar_Ctrl hook. This gives one deterministic 60 Hz
            // update after the game's car physics has been calculated.
            CalcVibrationHook_ = safetyhook::create_inline(
                reinterpret_cast<void*>(&CalcVibrationValues),
                calc_vibration_hook);

            if (!CalcVibrationHook_)
            {
                spdlog::error("WheelFFB: failed to hook CalcVibrationValues");
                return false;
            }

            spdlog::info(
                "WheelFFB: DirectInput COM hook installed; device init deferred to first gameplay tick");
            return true;
        }

        static WheelFFBHook instance;
    };

    WheelFFBHook WheelFFBHook::instance;
}
