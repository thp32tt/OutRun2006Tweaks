#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <SDL3/SDL.h>

#include <algorithm>
#include <cmath>
#include <cctype>
#include <string>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"

extern "C"
{
    void __cdecl CalcVibrationValues(EVWORK_CAR* car);
}

extern float VibrationLeftMotor;
extern float VibrationRightMotor;

namespace Settings
{
    Setting<bool> WheelFFBEnable{
        "WheelFFB", "Enable", false,
        "Enable experimental SDL3 haptic force feedback for steering wheels."
    };

    Setting<std::string> WheelFFBDeviceName{
        "WheelFFB", "DeviceName", "MOZA",
        "Case-insensitive substring used to select the haptic device. Empty selects the first compatible device."
    };

    Setting<float> WheelFFBGlobalStrength{
        "WheelFFB", "GlobalStrength", 0.35f,
        "Master force-feedback strength.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBSteeringStrength{
        "WheelFFB", "SteeringStrength", 0.50f,
        "Basic steering restoring-force strength.", Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBTextureStrength{
        "WheelFFB", "TextureStrength", 0.08f,
        "Strength of the sine-wave texture generated from the restored Xbox vibration signal.",
        Range<float>{ 0.0f, 1.0f }
    };

    Setting<float> WheelFFBSlewRate{
        "WheelFFB", "SlewRate", 0.08f,
        "Maximum normalized constant-force change per game tick. Lower values are gentler on DD wheels.",
        Range<float>{ 0.01f, 1.0f }
    };

    Setting<bool> WheelFFBInvertForce{
        "WheelFFB", "InvertForce", false,
        "Invert the constant-force direction."
    };

    Setting<bool> WheelFFBDebugLog{
        "WheelFFB", "DebugLog", false,
        "Log steering, rumble and output values about once per second."
    };
}

namespace
{
    std::string lower_copy(const char* text)
    {
        std::string result = text ? text : "";
        std::transform(result.begin(), result.end(), result.begin(),
            [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        return result;
    }

    class WheelFFBEngine
    {
    public:
        void update(EVWORK_CAR* car, float vibrationLeft, float vibrationRight)
        {
            (void)car;

            if (!Settings::WheelFFBEnable)
            {
                if (haptic_)
                    shutdown();
                reset_filters();
                return;
            }

            if (!haptic_)
            {
                if (retryTicks_ > 0)
                {
                    --retryTicks_;
                    return;
                }

                if (!initialize())
                {
                    retryTicks_ = 120; // about two seconds at 60 Hz
                    return;
                }
            }

            const bool inGame =
                Game::current_mode && (*Game::current_mode == STATE_GAME);

            float steer = 0.0f;
            if (inGame)
            {
                // Ask the game's own GetVolume function for steering.
                // When UseNewInput is enabled, Tweaks already hooks this address
                // and returns the current SDL input value; with legacy input the
                // original game function returns the DirectInput steering value.
                using GetVolumeFn = int(__cdecl*)(ADChannel);
                auto getVolume = Module::fn_ptr<GetVolumeFn>(0x53720);
                if (getVolume)
                {
                    const int rawSteer = getVolume(ADChannel::Steering);
                    steer = std::clamp(rawSteer / 127.0f, -1.0f, 1.0f);
                }
            }

            float target = 0.0f;
            float texture = 0.0f;

            if (inGame)
            {
                // v0.1: intentionally simple restoring force.
                // True SAT / slip-based unloading comes after the output path
                // and axis direction are verified on a real wheel.
                target = -steer * static_cast<float>(Settings::WheelFFBSteeringStrength);

                texture = std::clamp(
                    std::max(vibrationLeft, vibrationRight),
                    0.0f, 1.0f) *
                    static_cast<float>(Settings::WheelFFBTextureStrength);
            }

            target *= static_cast<float>(Settings::WheelFFBGlobalStrength);
            texture *= static_cast<float>(Settings::WheelFFBGlobalStrength);

            if (Settings::WheelFFBInvertForce)
                target = -target;

            // Redux-inspired output conditioning:
            // fast attack, slower decay, soft saturation, then a slew limiter.
            const float ema =
                std::abs(target) > std::abs(filteredForce_) ? 0.25f : 0.10f;
            filteredForce_ += (target - filteredForce_) * ema;

            constexpr float SoftClipGain = 1.25f;
            const float soft = std::tanh(filteredForce_ * SoftClipGain) /
                               std::tanh(SoftClipGain);

            const float slew = static_cast<float>(Settings::WheelFFBSlewRate);
            const float delta = std::clamp(soft - outputForce_, -slew, slew);
            outputForce_ = std::clamp(outputForce_ + delta, -1.0f, 1.0f);

            if (!write_constant(outputForce_))
            {
                spdlog::error("WheelFFB: constant-force update failed: {}", SDL_GetError());
                shutdown();
                retryTicks_ = 120;
                return;
            }

            if (sineEffectId_ >= 0 && !write_sine(texture))
            {
                spdlog::warn("WheelFFB: sine update failed, disabling texture effect: {}", SDL_GetError());
                SDL_DestroyHapticEffect(haptic_, sineEffectId_);
                sineEffectId_ = -1;
            }

            if (Settings::WheelFFBDebugLog && (++logCounter_ % 60) == 0)
            {
                spdlog::info(
                    "WheelFFB: steer={:.3f}, vibL={:.3f}, vibR={:.3f}, out={:.3f}, texture={:.3f}",
                    steer, vibrationLeft, vibrationRight, outputForce_, texture);
            }
        }

    private:
        bool initialize()
        {
            // CalcVibrationValues is called from the game's car control path,
            // so this lazy init happens after the window/input startup path
            // rather than from DllMain.
            if ((SDL_WasInit(SDL_INIT_HAPTIC) & SDL_INIT_HAPTIC) == 0)
            {
                if (!SDL_InitSubSystem(SDL_INIT_HAPTIC))
                {
                    spdlog::error("WheelFFB: SDL_InitSubSystem(SDL_INIT_HAPTIC) failed: {}", SDL_GetError());
                    return false;
                }
            }

            const std::string wanted = lower_copy(Settings::WheelFFBDeviceName.get().c_str());

            int count = 0;
            SDL_HapticID* ids = SDL_GetHaptics(&count);
            if (!ids || count <= 0)
            {
                spdlog::error("WheelFFB: SDL reported no haptic devices: {}", SDL_GetError());
                if (ids)
                    SDL_free(ids);
                return false;
            }

            SDL_HapticID selected = 0;
            std::string selectedName;

            for (int i = 0; i < count; ++i)
            {
                const char* name = SDL_GetHapticNameForID(ids[i]);
                const std::string lowered = lower_copy(name);

                spdlog::debug("WheelFFB: haptic [{}] '{}'", i, name ? name : "(unnamed)");

                if (selected == 0 &&
                    (wanted.empty() || lowered.find(wanted) != std::string::npos))
                {
                    selected = ids[i];
                    selectedName = name ? name : "(unnamed)";
                }
            }

            SDL_free(ids);

            if (selected == 0)
            {
                spdlog::error(
                    "WheelFFB: no haptic device matched DeviceName='{}'",
                    Settings::WheelFFBDeviceName.get());
                return false;
            }

            haptic_ = SDL_OpenHaptic(selected);
            if (!haptic_)
            {
                spdlog::error("WheelFFB: SDL_OpenHaptic('{}') failed: {}",
                    selectedName, SDL_GetError());
                return false;
            }

            features_ = SDL_GetHapticFeatures(haptic_);
            if ((features_ & SDL_HAPTIC_CONSTANT) == 0)
            {
                spdlog::error("WheelFFB: '{}' does not support SDL_HAPTIC_CONSTANT", selectedName);
                shutdown();
                return false;
            }

            if (features_ & SDL_HAPTIC_AUTOCENTER)
            {
                if (!SDL_SetHapticAutocenter(haptic_, 0))
                    spdlog::warn("WheelFFB: could not disable device autocenter: {}", SDL_GetError());
            }

            if (!create_constant())
            {
                spdlog::error("WheelFFB: failed to create constant-force effect: {}", SDL_GetError());
                shutdown();
                return false;
            }

            if (features_ & SDL_HAPTIC_SINE)
            {
                if (!create_sine())
                    spdlog::warn("WheelFFB: sine texture unavailable: {}", SDL_GetError());
            }
            else
            {
                spdlog::info("WheelFFB: device has no SDL_HAPTIC_SINE support; texture disabled");
            }

            selectedName_ = selectedName;
            reset_filters();
            spdlog::info(
                "WheelFFB: ready on '{}' (features=0x{:X}, axes={}, max-playing={})",
                selectedName_,
                features_,
                SDL_GetNumHapticAxes(haptic_),
                SDL_GetMaxHapticEffectsPlaying(haptic_));

            return true;
        }

        bool create_constant()
        {
            constantEffect_ = {};
            constantEffect_.type = SDL_HAPTIC_CONSTANT;
            constantEffect_.constant.type = SDL_HAPTIC_CONSTANT;
            constantEffect_.constant.direction.type = SDL_HAPTIC_STEERING_AXIS;

            // Finite duration is a DD-wheel failsafe: if game updates stop,
            // the motor force expires instead of remaining latched forever.
            constantEffect_.constant.length = 100;
            constantEffect_.constant.level = 0;

            constantEffectId_ = SDL_CreateHapticEffect(haptic_, &constantEffect_);
            return constantEffectId_ >= 0;
        }

        bool create_sine()
        {
            sineEffect_ = {};
            sineEffect_.type = SDL_HAPTIC_SINE;
            sineEffect_.periodic.type = SDL_HAPTIC_SINE;
            sineEffect_.periodic.direction.type = SDL_HAPTIC_STEERING_AXIS;
            sineEffect_.periodic.length = 100;
            sineEffect_.periodic.period = 33; // ~30 Hz
            sineEffect_.periodic.magnitude = 0;

            sineEffectId_ = SDL_CreateHapticEffect(haptic_, &sineEffect_);
            return sineEffectId_ >= 0;
        }

        bool write_constant(float force)
        {
            if (!haptic_ || constantEffectId_ < 0)
                return false;

            constantEffect_.constant.level = static_cast<Sint16>(
                std::clamp(force, -1.0f, 1.0f) * 32767.0f);

            if (!SDL_UpdateHapticEffect(haptic_, constantEffectId_, &constantEffect_))
                return false;

            // Restart the 100 ms failsafe window every 60 Hz tick.
            return SDL_RunHapticEffect(haptic_, constantEffectId_, 1);
        }

        bool write_sine(float magnitude)
        {
            if (!haptic_ || sineEffectId_ < 0)
                return true;

            sineEffect_.periodic.magnitude = static_cast<Sint16>(
                std::clamp(magnitude, 0.0f, 1.0f) * 32767.0f);

            if (!SDL_UpdateHapticEffect(haptic_, sineEffectId_, &sineEffect_))
                return false;

            return SDL_RunHapticEffect(haptic_, sineEffectId_, 1);
        }

        void shutdown()
        {
            if (!haptic_)
                return;

            if (constantEffectId_ >= 0)
            {
                constantEffect_.constant.level = 0;
                SDL_UpdateHapticEffect(haptic_, constantEffectId_, &constantEffect_);
                SDL_StopHapticEffect(haptic_, constantEffectId_);
                SDL_DestroyHapticEffect(haptic_, constantEffectId_);
            }

            if (sineEffectId_ >= 0)
            {
                sineEffect_.periodic.magnitude = 0;
                SDL_UpdateHapticEffect(haptic_, sineEffectId_, &sineEffect_);
                SDL_StopHapticEffect(haptic_, sineEffectId_);
                SDL_DestroyHapticEffect(haptic_, sineEffectId_);
            }

            SDL_CloseHaptic(haptic_);
            haptic_ = nullptr;
            constantEffectId_ = -1;
            sineEffectId_ = -1;
            selectedName_.clear();
        }

        void reset_filters()
        {
            filteredForce_ = 0.0f;
            outputForce_ = 0.0f;
            logCounter_ = 0;
        }

        SDL_Haptic* haptic_ = nullptr;
        Uint32 features_ = 0;

        SDL_HapticEffect constantEffect_{};
        SDL_HapticEffect sineEffect_{};
        SDL_HapticEffectID constantEffectId_ = -1;
        SDL_HapticEffectID sineEffectId_ = -1;

        std::string selectedName_;
        float filteredForce_ = 0.0f;
        float outputForce_ = 0.0f;
        unsigned retryTicks_ = 0;
        unsigned logCounter_ = 0;
    };

    WheelFFBEngine gWheelFFB;

    class WheelFFBHook : public Hook
    {
        inline static SafetyHookInline CalcVibration_hook = {};

        static void __cdecl CalcVibration_dest(EVWORK_CAR* car)
        {
            CalcVibration_hook.ccall<void>(car);
            gWheelFFB.update(car, VibrationLeftMotor, VibrationRightMotor);
        }

    public:
        std::string_view description() override
        {
            return "WheelFFB (SDL3)";
        }

        bool apply() override
        {
            // Hook the Tweaks-side Xbox vibration reconstruction rather than
            // the game function a second time. This keeps the existing
            // GamePlCar_Ctrl hook untouched and gives us one update per call.
            CalcVibration_hook = safetyhook::create_inline(
                reinterpret_cast<void*>(&CalcVibrationValues),
                CalcVibration_dest);

            return static_cast<bool>(CalcVibration_hook);
        }

        static WheelFFBHook instance;
    };

    WheelFFBHook WheelFFBHook::instance;
}
