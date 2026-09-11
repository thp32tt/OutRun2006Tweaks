#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#define DIRECTINPUT_VERSION 0x0800
#include <Windows.h>
#include <dinput.h>

#pragma comment(lib, "dinput8.lib")
#pragma comment(lib, "dxguid.lib")

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <utility>
#include <vector>

#include <imgui.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "overlay.hpp"

void WheelFFB_RequestDirectionTest(int direction);

namespace Settings
{
    extern Setting<float> SteeringDeadZone;
    extern Setting<bool> UseNewInput;
    extern Setting<bool> WheelFFBEnable;
    extern Setting<bool> WheelAccelerationInvert;
    extern Setting<bool> WheelBrakeInvert;
    extern Setting<std::string> WheelFFBDeviceName;
    extern Setting<std::string> WheelFFBDeviceGuid;
    extern Setting<bool> WheelMenuR3DirectDPad;
    extern Setting<bool> WheelMenuR3DirectAB;
    extern Setting<float> WheelFFBGlobalStrength;
    extern Setting<float> WheelFFBSpringStrength;
    extern Setting<float> WheelFFBSpringSaturation;
    extern Setting<float> WheelFFBDamperStrength;
    extern Setting<float> WheelFFBSteeringWeight;
    extern Setting<bool> WheelFFBPhysicsSat;
    extern Setting<float> WheelFFBGripLoss;
    extern Setting<float> WheelFFBWeightTransfer;
    extern Setting<float> WheelFFBSlewRate;
    extern Setting<int> VibrationMode;
    extern Setting<float> WheelFFBRoadTexture;
    extern Setting<float> WheelFFBTireSlip;
    extern Setting<float> WheelFFBWallImpact;
    extern Setting<bool> WheelFFBUseHardwareSpring;
    extern Setting<bool> WheelFFBUseHardwareDamper;
    extern Setting<bool> WheelFFBInvertForce;
    extern Setting<bool> WheelFFBInvertSpring;
    extern Setting<bool> WheelFFBUsePeriodicEffects;
    extern Setting<bool> WheelFFBDebugLog;
    extern Setting<bool> WheelFFBTelemetry;

    Setting<bool> WheelUniversalSetupEnable{
        "Controls", "WheelUniversalSetupEnable", false,
        "Use the F11 Wheel Setup profile to configure the original legacy DirectInput wheel mappings."
    };

    Setting<std::string> WheelUniversalDeviceName{
        "Controls", "WheelUniversalDeviceName", "",
        "DirectInput product name selected by F11 Wheel Setup."
    };

    Setting<std::string> WheelUniversalDeviceGuid{
        "Controls", "WheelUniversalDeviceGuid", "",
        "Exact DirectInput instance GUID selected by F11 Wheel Setup."
    };

    Setting<int> WheelUniversalLegacyDeviceIndex{
        "Controls", "WheelUniversalLegacyDeviceIndex", 0,
        "Original-game DirectInput device slot used by the universal wheel profile.",
        Range<int>{ 0, 2 }
    };

    Setting<int> WheelUniversalSteeringAxis{
        "Controls", "WheelUniversalSteeringAxis", -1,
        "DirectInput axis used for steering (-1 is Unassigned).",
        Range<int>{ -1, 7 }
    };
    Setting<bool> WheelUniversalSteeringInvert{
        "Controls", "WheelUniversalSteeringInvert", false,
        "Invert steering direction for the universal wheel profile."
    };
    Setting<int> WheelUniversalThrottleAxis{
        "Controls", "WheelUniversalThrottleAxis", -1,
        "DirectInput axis used for acceleration (-1 is Unassigned).",
        Range<int>{ -1, 7 }
    };
    Setting<int> WheelUniversalBrakeAxis{
        "Controls", "WheelUniversalBrakeAxis", -1,
        "DirectInput axis used for brake (-1 is Unassigned).",
        Range<int>{ -1, 7 }
    };

    Setting<int> WheelUniversalGearUpButton{
        "Controls", "WheelUniversalGearUpButton", -1,
        "Zero-based DirectInput button for Gear Up.", Range<int>{ -1, 127 }
    };
    Setting<int> WheelUniversalGearDownButton{
        "Controls", "WheelUniversalGearDownButton", -1,
        "Zero-based DirectInput button for Gear Down.", Range<int>{ -1, 127 }
    };
    Setting<int> WheelUniversalStartButton{
        "Controls", "WheelUniversalStartButton", -1,
        "Zero-based DirectInput button for Start.", Range<int>{ -1, 127 }
    };
    Setting<int> WheelUniversalViewButton{
        "Controls", "WheelUniversalViewButton", -1,
        "Zero-based DirectInput button for Change View.", Range<int>{ -1, 127 }
    };

    // Digital menu bindings: 0..127 = button, 1000+ = POV direction
    // (POV0 Up/Right/Down/Left = 1000..1003, POV1 = 1004..1007, etc.).
    Setting<int> WheelUniversalMenuAccept{
        "Controls", "WheelUniversalMenuAccept", -1,
        "DirectInput button/POV binding for menu Accept.", Range<int>{ -1, 1015 }
    };
    Setting<int> WheelUniversalMenuBack{
        "Controls", "WheelUniversalMenuBack", -1,
        "DirectInput button/POV binding for menu Back.", Range<int>{ -1, 1015 }
    };
    Setting<int> WheelUniversalMenuUp{
        "Controls", "WheelUniversalMenuUp", -1,
        "DirectInput button/POV binding for menu Up.", Range<int>{ -1, 1015 }
    };
    Setting<int> WheelUniversalMenuRight{
        "Controls", "WheelUniversalMenuRight", -1,
        "DirectInput button/POV binding for menu Right.", Range<int>{ -1, 1015 }
    };
    Setting<int> WheelUniversalMenuDown{
        "Controls", "WheelUniversalMenuDown", -1,
        "DirectInput button/POV binding for menu Down.", Range<int>{ -1, 1015 }
    };
    Setting<int> WheelUniversalMenuLeft{
        "Controls", "WheelUniversalMenuLeft", -1,
        "DirectInput button/POV binding for menu Left.", Range<int>{ -1, 1015 }
    };
}

namespace
{
    constexpr uintptr_t DeviceSlotsOffset = 0x4606D4;
    constexpr uintptr_t DeviceCountOffset = 0x55AEC4;
    constexpr size_t AxisMapOffset = 0x54;
    constexpr size_t ButtonMapOffset = 0x70;
    constexpr int AxisUnassigned = 8;
    constexpr int ButtonUnassigned = -1;

    constexpr std::array<const char*, 8> AxisNames = {
        "X", "Y", "Z", "Rx", "Ry", "Rz", "Slider 1", "Slider 2"
    };

    std::string lower_identity(std::string value)
    {
        std::transform(value.begin(), value.end(), value.begin(),
            [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        return value;
    }

    std::string wheel_guid_key(const GUID& guid)
    {
        char b[64]{};
        std::snprintf(b, sizeof(b),
            "%08X-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X",
            (unsigned)guid.Data1, (unsigned)guid.Data2, (unsigned)guid.Data3,
            (unsigned)guid.Data4[0], (unsigned)guid.Data4[1],
            (unsigned)guid.Data4[2], (unsigned)guid.Data4[3],
            (unsigned)guid.Data4[4], (unsigned)guid.Data4[5],
            (unsigned)guid.Data4[6], (unsigned)guid.Data4[7]);
        return lower_identity(b);
    }

    bool is_virtual_name(const std::string& name)
    {
        std::string lower = name;
        std::transform(lower.begin(), lower.end(), lower.begin(),
            [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        static constexpr const char* tokens[] = {
            "vjoy", "vigem", "xoutput", "virtual", "vxbox", "v xbox",
            "hidguardian", "hidhide"
        };
        for (const char* token : tokens)
            if (lower.find(token) != std::string::npos)
                return true;
        return false;
    }

    LONG axis_raw(const DIJOYSTATE2& state, int axis)
    {
        switch (axis)
        {
        case 0: return state.lX;
        case 1: return state.lY;
        case 2: return state.lZ;
        case 3: return state.lRx;
        case 4: return state.lRy;
        case 5: return state.lRz;
        case 6: return state.rglSlider[0];
        case 7: return state.rglSlider[1];
        default: return 0;
        }
    }

    const char* axis_name(int axis)
    {
        return axis >= 0 && axis < int(AxisNames.size()) ? AxisNames[axis] : "Unassigned";
    }

    int pov_direction(DWORD pov)
    {
        if ((pov & 0xFFFFu) == 0xFFFFu)
            return -1;
        const int angle = int(pov % 36000u);
        if (angle >= 31500 || angle < 4500) return 0; // up
        if (angle < 13500) return 1;                  // right
        if (angle < 22500) return 2;                  // down
        return 3;                                     // left
    }

    std::string digital_binding_name(int binding)
    {
        if (binding < 0)
            return "Unassigned";
        if (binding < 128)
            return "Button " + std::to_string(binding + 1);
        if (binding >= 1000 && binding < 1016)
        {
            const int code = binding - 1000;
            const int pov = code / 4;
            static constexpr const char* dirs[] = { "Up", "Right", "Down", "Left" };
            return "POV " + std::to_string(pov + 1) + " " + dirs[code % 4];
        }
        return "Unassigned";
    }

    struct DeviceInfo
    {
        GUID guid{};
        std::string guidKey;
        std::string name;
        DWORD axes = 0;
        DWORD buttons = 0;
        DWORD povs = 0;
        bool ffb = false;
    };

    class DirectWheelReader
    {
    public:
        ~DirectWheelReader() { release_all(); }

        const std::vector<DeviceInfo>& devices()
        {
            if (devices_.empty())
                enumerate();
            return devices_;
        }

        void refresh_devices()
        {
            release_device();
            devices_.clear();
            enumerate();
        }

        bool select_by_identity(const std::string& wantedGuid, const std::string& wantedName)
        {
            const std::string guid = lower_identity(wantedGuid);
            if (device_ && !guid.empty() && guid == selectedGuidKey_) return true;
            if (device_ && guid.empty() && wantedName == selectedName_) return true;

            release_device();
            if (devices_.empty()) enumerate();
            int index = -1;
            if (!guid.empty())
            {
                for (size_t i=0; i<devices_.size(); ++i)
                    if (devices_[i].guidKey == guid) { index=int(i); break; }
                if (index < 0)
                    return false;
            }
            else if (!wantedName.empty())
            {
                for (size_t i=0; i<devices_.size(); ++i)
                    if (devices_[i].name == wantedName) { index=int(i); break; }
            }
            if (index < 0 && guid.empty() && wantedName.empty() && !devices_.empty()) index=0;
            return index >= 0 ? open(index) : false;
        }

        bool poll()
        {
            if (!device_)
            {
                if (!select_by_identity(
                        Settings::WheelUniversalDeviceGuid.get(),
                        Settings::WheelUniversalDeviceName.get()))
                    return false;
            }

            HRESULT hr = device_->Poll();
            if (FAILED(hr))
            {
                hr = device_->Acquire();
                if (SUCCEEDED(hr))
                    hr = device_->Poll();
            }
            if (FAILED(hr))
            {
                release_device();
                devices_.clear();
                return false;
            }

            hr = device_->GetDeviceState(sizeof(state_), &state_);
            if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED)
            {
                if (SUCCEEDED(device_->Acquire()))
                {
                    device_->Poll();
                    hr = device_->GetDeviceState(sizeof(state_), &state_);
                }
            }
            if (FAILED(hr))
            {
                release_device();
                devices_.clear();
                return false;
            }
            return true;
        }

        const DIJOYSTATE2& state() const { return state_; }
        const std::string& selected_name() const { return selectedName_; }

        void release_device()
        {
            if (device_)
            {
                device_->Unacquire();
                device_->Release();
                device_ = nullptr;
            }
            selectedName_.clear();
            selectedGuidKey_.clear();
            state_ = {};
        }

    private:
        static BOOL CALLBACK enum_callback(LPCDIDEVICEINSTANCEA instance, LPVOID context)
        {
            auto* self = static_cast<DirectWheelReader*>(context);
            const std::string product = instance->tszProductName;
            const std::string instanceName = instance->tszInstanceName;
            if (is_virtual_name(product) || is_virtual_name(instanceName))
                return DIENUM_CONTINUE;

            DeviceInfo info{};
            info.guid = instance->guidInstance;
            info.guidKey = wheel_guid_key(info.guid);
            info.name = product;

            IDirectInputDevice8A* temp = nullptr;
            if (self->di_ && SUCCEEDED(self->di_->CreateDevice(info.guid, &temp, nullptr)) && temp)
            {
                DIDEVCAPS caps{};
                caps.dwSize = sizeof(caps);
                if (SUCCEEDED(temp->GetCapabilities(&caps)))
                {
                    info.axes = caps.dwAxes;
                    info.buttons = caps.dwButtons;
                    info.povs = caps.dwPOVs;
                    info.ffb = (caps.dwFlags & DIDC_FORCEFEEDBACK) != 0;
                }
                temp->Release();
            }

            self->devices_.push_back(std::move(info));
            return DIENUM_CONTINUE;
        }

        bool ensure_di()
        {
            if (di_)
                return true;
            const HRESULT hr = DirectInput8Create(
                GetModuleHandleW(nullptr), DIRECTINPUT_VERSION, IID_IDirectInput8A,
                reinterpret_cast<void**>(&di_), nullptr);
            return SUCCEEDED(hr) && di_;
        }

        void enumerate()
        {
            if (!ensure_di())
                return;
            di_->EnumDevices(
                DI8DEVCLASS_GAMECTRL, enum_callback, this, DIEDFL_ATTACHEDONLY);
        }

        bool open(int index)
        {
            if (index < 0 || index >= int(devices_.size()) || !ensure_di())
                return false;

            IDirectInputDevice8A* device = nullptr;
            HRESULT hr = di_->CreateDevice(devices_[index].guid, &device, nullptr);
            if (FAILED(hr) || !device)
                return false;

            hr = device->SetDataFormat(&c_dfDIJoystick2);
            if (FAILED(hr))
            {
                device->Release();
                return false;
            }

            HWND hwnd = Game::GameHwnd();
            if (!hwnd)
            {
                device->Release();
                return false;
            }

            hr = device->SetCooperativeLevel(hwnd, DISCL_NONEXCLUSIVE | DISCL_BACKGROUND);
            if (FAILED(hr))
            {
                device->Release();
                return false;
            }

            hr = device->Acquire();
            if (FAILED(hr) && hr != S_FALSE)
            {
                device->Release();
                return false;
            }
            device_ = device;
            selectedName_ = devices_[index].name;
            selectedGuidKey_ = devices_[index].guidKey;
            return true;
        }

        void release_all()
        {
            release_device();
            if (di_)
            {
                di_->Release();
                di_ = nullptr;
            }
        }

        IDirectInput8A* di_ = nullptr;
        IDirectInputDevice8A* device_ = nullptr;
        std::vector<DeviceInfo> devices_;
        std::string selectedName_;
        std::string selectedGuidKey_;
        DIJOYSTATE2 state_{};
    };

    DirectWheelReader gReader;

    class UniversalWheelProfile : public Hook
    {
        inline static SafetyHookInline ReadIOHook{};
        inline static SafetyHookInline SwitchNowHook{};
        inline static SafetyHookInline SwitchOnHook{};
        inline static SafetyHookInline GetVolumeHook{};
        inline static SafetyHookInline GetVolumeOldHook{};
        inline static uint32_t menuHeld_ = 0;
        inline static uint32_t menuPressed_ = 0;
        inline static uint32_t previousMenuHeld_ = 0;
        inline static DWORD lastApplyLog_ = 0;

        inline static constexpr uint32_t UniversalMenuSwitchMask =
            (1u << int(SwitchId::Start)) |
            (1u << int(SwitchId::Back)) |
            (1u << int(SwitchId::A)) |
            (1u << int(SwitchId::B)) |
            (1u << int(SwitchId::GearDown)) |
            (1u << int(SwitchId::GearUp)) |
            (1u << int(SwitchId::SelectionUp)) |
            (1u << int(SwitchId::SelectionDown)) |
            (1u << int(SwitchId::SelectionLeft)) |
            (1u << int(SwitchId::SelectionRight));

        static bool pure_universal_menu_query(uint32_t switches)
        {
            return switches != 0 &&
                (switches & UniversalMenuSwitchMask) != 0 &&
                (switches & ~UniversalMenuSwitchMask) == 0;
        }

        static bool active()
        {
            return Settings::WheelInputCompatibility && !Settings::UseNewInput &&
                Settings::WheelUniversalSetupEnable;
        }

        static int device_count()
        {
            auto* count = Module::exe_ptr<int>(DeviceCountOffset);
            return count ? std::clamp(*count, 0, 4) : 0;
        }

        static uint8_t* device_at(int index)
        {
            const int count = device_count();
            if (index < 0 || index >= count - 1)
                return nullptr;
            auto* slots = Module::exe_ptr<uintptr_t>(DeviceSlotsOffset);
            return slots ? reinterpret_cast<uint8_t*>(slots[index]) : nullptr;
        }

        static void apply_mapping()
        {
            if (!active())
                return;

            const int regularCount = std::max(device_count() - 1, 0);
            if (regularCount <= 0)
                return;
            const int maxSlot = std::min(regularCount - 1, 2);
            const int slot = std::clamp(
                int(Settings::WheelUniversalLegacyDeviceIndex), 0, maxSlot);
            if (slot != int(Settings::WheelUniversalLegacyDeviceIndex))
                Settings::WheelUniversalLegacyDeviceIndex = slot;

            auto* device = device_at(slot);
            if (!device)
                return;

            auto* axes = reinterpret_cast<int32_t*>(device + AxisMapOffset);
            auto* buttons = reinterpret_cast<int32_t*>(device + ButtonMapOffset);

            axes[0] = int(Settings::WheelUniversalThrottleAxis) >= 0
                ? int(Settings::WheelUniversalThrottleAxis) : AxisUnassigned;
            axes[1] = int(Settings::WheelUniversalBrakeAxis) >= 0
                ? int(Settings::WheelUniversalBrakeAxis) : AxisUnassigned;
            axes[2] = AxisUnassigned; // never use combined Accelerator/Brake
            axes[3] = int(Settings::WheelUniversalSteeringAxis) >= 0
                ? int(Settings::WheelUniversalSteeringAxis) : AxisUnassigned;
            axes[4] = AxisUnassigned; // Gear Up/Down axis
            axes[5] = AxisUnassigned; // Menu Up/Down axis

            buttons[0] = int(Settings::WheelUniversalGearUpButton);
            buttons[1] = int(Settings::WheelUniversalGearDownButton);
            buttons[2] = int(Settings::WheelUniversalStartButton);
            buttons[8] = int(Settings::WheelUniversalViewButton);

            const DWORD now = GetTickCount();
            if (now - lastApplyLog_ > 5000)
            {
                lastApplyLog_ = now;
                spdlog::info(
                    "WheelUniversalSetup: applied legacy slot {} axes steer={} accel={} brake={} buttons up={} down={} start={} view={}",
                    slot,
                    int(Settings::WheelUniversalSteeringAxis),
                    int(Settings::WheelUniversalThrottleAxis),
                    int(Settings::WheelUniversalBrakeAxis),
                    int(Settings::WheelUniversalGearUpButton) + 1,
                    int(Settings::WheelUniversalGearDownButton) + 1,
                    int(Settings::WheelUniversalStartButton) + 1,
                    int(Settings::WheelUniversalViewButton) + 1);
            }
        }

        static bool digital_active(const DIJOYSTATE2& state, int binding)
        {
            if (binding < 0)
                return false;
            if (binding < 128)
                return (state.rgbButtons[binding] & 0x80) != 0;
            if (binding >= 1000 && binding < 1016)
            {
                const int code = binding - 1000;
                const int povIndex = code / 4;
                const int wantedDir = code % 4;
                return pov_direction(state.rgdwPOV[povIndex]) == wantedDir;
            }
            return false;
        }

        static void poll_menu()
        {
            menuHeld_ = 0;
            menuPressed_ = 0;

            if (!active() || !Game::current_mode || *Game::current_mode == STATE_GAME)
            {
                previousMenuHeld_ = 0;
                gReader.release_device();
                return;
            }

            if (!gReader.poll())
                return;

            const auto& state = gReader.state();
            if (digital_active(state, Settings::WheelUniversalMenuAccept))
                menuHeld_ |= (1u << int(SwitchId::A)) | (1u << int(SwitchId::GearUp));
            if (digital_active(state, Settings::WheelUniversalMenuBack))
                menuHeld_ |= (1u << int(SwitchId::B)) | (1u << int(SwitchId::Back)) |
                    (1u << int(SwitchId::GearDown));
            if (digital_active(state, Settings::WheelUniversalMenuUp))
                menuHeld_ |= 1u << int(SwitchId::SelectionUp);
            if (digital_active(state, Settings::WheelUniversalMenuRight))
                menuHeld_ |= 1u << int(SwitchId::SelectionRight);
            if (digital_active(state, Settings::WheelUniversalMenuDown))
                menuHeld_ |= 1u << int(SwitchId::SelectionDown);
            if (digital_active(state, Settings::WheelUniversalMenuLeft))
                menuHeld_ |= 1u << int(SwitchId::SelectionLeft);
            if (digital_active(state, Settings::WheelUniversalStartButton))
                menuHeld_ |= 1u << int(SwitchId::Start);

            menuPressed_ = menuHeld_ & ~previousMenuHeld_;
            previousMenuHeld_ = menuHeld_;
        }

        static int ReadIO_dest()
        {
            const int result = ReadIOHook.ccall<int>();
            apply_mapping();
            poll_menu();
            return result;
        }

        static int SwitchNow_dest(uint32_t switches)
        {
            const int result = SwitchNowHook.ccall<int>(switches);
            if (result || !active() || !pure_universal_menu_query(switches))
                return result;
            return (menuHeld_ & switches) == switches ? 1 : 0;
        }

        static int SwitchOn_dest(uint32_t switches)
        {
            const int result = SwitchOnHook.ccall<int>(switches);
            if (result || !active() || !pure_universal_menu_query(switches))
                return result;
            return (menuPressed_ & switches) == switches ? 1 : 0;
        }

        static int maybe_invert_steering(int channel, int result)
        {
            if (active() && channel == int(ADChannel::Steering) &&
                Settings::WheelUniversalSteeringInvert)
                return -result;
            return result;
        }

        static int GetVolume_dest(int channel)
        {
            return maybe_invert_steering(channel, GetVolumeHook.call<int>(channel));
        }

        static int GetVolumeOld_dest(int channel)
        {
            return maybe_invert_steering(channel, GetVolumeOldHook.call<int>(channel));
        }

    public:
        static void apply_now() { apply_mapping(); }

        static int regular_device_count()
        {
            return std::max(device_count() - 1, 0);
        }

        static bool copy_current_mapping()
        {
            const int regularCount = std::max(device_count() - 1, 0);
            if (regularCount <= 0)
                return false;
            const int maxSlot = std::min(regularCount - 1, 2);
            const int slot = std::clamp(
                int(Settings::WheelUniversalLegacyDeviceIndex), 0, maxSlot);
            if (slot != int(Settings::WheelUniversalLegacyDeviceIndex))
                Settings::WheelUniversalLegacyDeviceIndex = slot;

            auto* device = device_at(slot);
            if (!device)
                return false;

            const auto* axes = reinterpret_cast<const int32_t*>(device + AxisMapOffset);
            const auto* buttons = reinterpret_cast<const int32_t*>(device + ButtonMapOffset);
            Settings::WheelUniversalThrottleAxis = axes[0] == AxisUnassigned ? -1 : axes[0];
            Settings::WheelUniversalBrakeAxis = axes[1] == AxisUnassigned ? -1 : axes[1];
            Settings::WheelUniversalSteeringAxis = axes[3] == AxisUnassigned ? -1 : axes[3];
            Settings::WheelUniversalGearUpButton = buttons[0];
            Settings::WheelUniversalGearDownButton = buttons[1];
            Settings::WheelUniversalStartButton = buttons[2];
            Settings::WheelUniversalViewButton = buttons[8];
            return true;
        }

        std::string_view description() override { return "Universal DirectInput Wheel Setup"; }
        bool validate() override { return Settings::WheelInputCompatibility; }
        bool apply() override
        {
            ReadIOHook = safetyhook::create_inline(Module::exe_ptr(0x53BB0), ReadIO_dest);
            SwitchNowHook = safetyhook::create_inline(Module::exe_ptr(0x536C0), SwitchNow_dest);
            SwitchOnHook = safetyhook::create_inline(Module::exe_ptr(0x536F0), SwitchOn_dest);
            GetVolumeHook = safetyhook::create_inline(Module::exe_ptr(0x53720), GetVolume_dest);
            GetVolumeOldHook = safetyhook::create_inline(Module::exe_ptr(0x53750), GetVolumeOld_dest);
            const bool ok = !!ReadIOHook && !!SwitchNowHook && !!SwitchOnHook &&
                !!GetVolumeHook && !!GetVolumeOldHook;
            if (ok)
                spdlog::info("WheelUniversalSetup: F11 universal DirectInput profile support installed");
            return ok;
        }
        static UniversalWheelProfile instance;
    };

    UniversalWheelProfile UniversalWheelProfile::instance;

    class WheelSetupWindow : public OverlayWindow
    {
        enum class BindTarget
        {
            None,
            Steering,
            Throttle,
            Brake,
            GearUp,
            GearDown,
            Start,
            View,
            MenuAccept,
            MenuBack,
            MenuUp,
            MenuRight,
            MenuDown,
            MenuLeft,
        };

        BindTarget target_ = BindTarget::None;
        DIJOYSTATE2 baseline_{};
        bool baselineValid_ = false;
        std::string status_;

        void save()
        {
            UniversalWheelProfile::apply_now();
            Settings::write(Module::UserIniPath);
            status_ = "Saved to OutRun2006Tweaks.user.ini";
        }

        void select_device(const DeviceInfo& info)
        {
            Settings::WheelUniversalDeviceName = info.name;
            Settings::WheelUniversalDeviceGuid = info.guidKey;
            Settings::WheelFFBDeviceName = info.name;
            Settings::WheelFFBDeviceGuid = info.guidKey;
            if (!Settings::UseNewInput)
                gReader.select_by_identity(info.guidKey, info.name);
            Settings::write(Module::UserIniPath);
            if (Settings::UseNewInput)
                status_ = "Selected FFB wheel and saved its exact DirectInput GUID. Restart the game after changing physical wheel.";
            else
                status_ = UniversalWheelProfile::regular_device_count() > 1
                    ? "Selected wheel/FFB device. Confirm the OutRun legacy input slot below when multiple controllers are present."
                    : "Selected wheel; FFB device follows this product name.";
        }

        void begin_bind(BindTarget target)
        {
            target_ = target;
            baselineValid_ = gReader.poll();
            if (baselineValid_)
                baseline_ = gReader.state();
            status_ = baselineValid_
                ? "Move the requested axis or press the requested button..."
                : "Could not read wheel. Configure from a game menu and try Refresh Devices.";
        }

        bool target_is_axis() const
        {
            return target_ == BindTarget::Steering || target_ == BindTarget::Throttle ||
                target_ == BindTarget::Brake;
        }

        void assign_axis(int axis)
        {
            if (target_ == BindTarget::Steering) Settings::WheelUniversalSteeringAxis = axis;
            if (target_ == BindTarget::Throttle) Settings::WheelUniversalThrottleAxis = axis;
            if (target_ == BindTarget::Brake) Settings::WheelUniversalBrakeAxis = axis;
            target_ = BindTarget::None;
            status_ = std::string("Bound Axis ") + axis_name(axis) + ". Check the live bar and Invert if needed.";
            UniversalWheelProfile::apply_now();
        }

        void assign_digital(int code)
        {
            const bool gameplayButton =
                target_ == BindTarget::GearUp || target_ == BindTarget::GearDown ||
                target_ == BindTarget::Start || target_ == BindTarget::View;
            if (gameplayButton && code >= 128)
            {
                target_ = BindTarget::None;
                status_ = "Gameplay actions currently require a physical button; POV is supported for menu directions.";
                return;
            }

            switch (target_)
            {
            case BindTarget::GearUp: Settings::WheelUniversalGearUpButton = code; break;
            case BindTarget::GearDown: Settings::WheelUniversalGearDownButton = code; break;
            case BindTarget::Start: Settings::WheelUniversalStartButton = code; break;
            case BindTarget::View: Settings::WheelUniversalViewButton = code; break;
            case BindTarget::MenuAccept: Settings::WheelUniversalMenuAccept = code; break;
            case BindTarget::MenuBack: Settings::WheelUniversalMenuBack = code; break;
            case BindTarget::MenuUp: Settings::WheelUniversalMenuUp = code; break;
            case BindTarget::MenuRight: Settings::WheelUniversalMenuRight = code; break;
            case BindTarget::MenuDown: Settings::WheelUniversalMenuDown = code; break;
            case BindTarget::MenuLeft: Settings::WheelUniversalMenuLeft = code; break;
            default: break;
            }
            target_ = BindTarget::None;
            status_ = "Binding captured: " + digital_binding_name(code);
            UniversalWheelProfile::apply_now();
        }

        void listen_for_binding()
        {
            if (target_ == BindTarget::None || !baselineValid_)
                return;
            if (ImGui::IsKeyPressed(ImGuiKey_Escape))
            {
                target_ = BindTarget::None;
                status_ = "Binding cancelled.";
                return;
            }
            if (!gReader.poll())
                return;

            const auto& state = gReader.state();
            if (target_is_axis())
            {
                int bestAxis = -1;
                LONG bestDelta = 0;
                for (int axis = 0; axis < 8; ++axis)
                {
                    const LONG delta = std::abs(axis_raw(state, axis) - axis_raw(baseline_, axis));
                    if (delta > bestDelta)
                    {
                        bestDelta = delta;
                        bestAxis = axis;
                    }
                }
                if (bestAxis >= 0 && bestDelta > 7000)
                    assign_axis(bestAxis);
                return;
            }

            for (int i = 0; i < 128; ++i)
            {
                const bool now = (state.rgbButtons[i] & 0x80) != 0;
                const bool before = (baseline_.rgbButtons[i] & 0x80) != 0;
                if (now && !before)
                {
                    assign_digital(i);
                    return;
                }
            }

            for (int p = 0; p < 4; ++p)
            {
                const int now = pov_direction(state.rgdwPOV[p]);
                const int before = pov_direction(baseline_.rgdwPOV[p]);
                if (now >= 0 && now != before)
                {
                    assign_digital(1000 + p * 4 + now);
                    return;
                }
            }
        }

        static float normalized_axis(int axis, bool steering, bool invert)
        {
            if (axis < 0 || !gReader.poll())
                return 0.0f;
            float v = std::clamp(axis_raw(gReader.state(), axis) / 65535.0f, 0.0f, 1.0f);
            if (steering)
            {
                v = v * 2.0f - 1.0f;
                if (invert) v = -v;
                return v;
            }
            if (invert) v = 1.0f - v;
            return v;
        }

        void axis_row(const char* label, BindTarget target, Settings::Setting<int>& axisSetting,
            bool* invertPtr, bool steering)
        {
            ImGui::PushID(label);
            ImGui::TextUnformatted(label);
            ImGui::SameLine(180.0f);
            ImGui::TextDisabled("Axis %s", axis_name(int(axisSetting)));
            ImGui::SameLine(290.0f);
            if (ImGui::Button("Bind", ImVec2(70, 0)))
                begin_bind(target);
            if (invertPtr)
            {
                ImGui::SameLine();
                ImGui::Checkbox("Invert", invertPtr);
            }

            bool invert = invertPtr ? *invertPtr : false;
            const float v = normalized_axis(int(axisSetting), steering, invert);
            const float bar = steering ? (v + 1.0f) * 0.5f : v;
            char text[32];
            std::snprintf(text, sizeof(text), steering ? "%+.2f" : "%.2f", v);
            ImGui::ProgressBar(std::clamp(bar, 0.0f, 1.0f), ImVec2(-FLT_MIN, 0), text);
            ImGui::PopID();
        }

        void button_row(const char* label, BindTarget target, Settings::Setting<int>& setting)
        {
            ImGui::PushID(label);
            ImGui::TextUnformatted(label);
            ImGui::SameLine(180.0f);
            const std::string name = digital_binding_name(int(setting));
            ImGui::TextDisabled("%s", name.c_str());
            ImGui::SameLine(330.0f);
            if (ImGui::Button("Bind", ImVec2(70, 0)))
                begin_bind(target);
            ImGui::SameLine();
            if (ImGui::SmallButton("Clear"))
                setting = -1;
            ImGui::PopID();
        }

        void apply_r3_menu_defaults()
        {
            Settings::WheelUniversalMenuAccept = 0;
            Settings::WheelUniversalMenuBack = 1;
            Settings::WheelUniversalMenuUp = 4;
            Settings::WheelUniversalMenuRight = 5;
            Settings::WheelUniversalMenuDown = 6;
            Settings::WheelUniversalMenuLeft = 7;
            status_ = "Loaded common MOZA R3/ES menu button defaults. Verify with Bind if your rim differs.";
        }

    public:
        Kind kind() const override { return Kind::Tab; }
        const char* name() const override
        {
            return Settings::UseNewInput ? "Force Feedback" : "Legacy Wheel Setup";
        }
        int order() const override { return 25; }
        void init() override {}

        void render(bool) override
        {
            listen_for_binding();

            if (Settings::UseNewInput)
            {
                ImGui::TextWrapped(
                    "Force feedback only. With UseNewInput enabled, steering, pedals, buttons, menu controls and calibration come only from Input Bindings. This page does not create input bindings; it only selects the DirectInput FFB wheel and tunes its forces.");
            }
            else
            {
                ImGui::TextWrapped(
                    "Legacy DirectInput wheel setup. Use this page for compatibility-mode input bindings and force feedback.");
            }

            const auto& devices = gReader.devices();
            if (ImGui::Button("Refresh Devices"))
                gReader.refresh_devices();

            ImGui::SameLine();
            std::string preview = Settings::UseNewInput
                ? Settings::WheelFFBDeviceName.get() : Settings::WheelUniversalDeviceName.get();
            if (preview.empty()) preview = devices.empty() ? "No DirectInput device" : devices.front().name;
            const std::string configuredGuid =
                lower_identity(Settings::UseNewInput
                    ? Settings::WheelFFBDeviceGuid.get() : Settings::WheelUniversalDeviceGuid.get());
            auto isSelectedDevice = [&](const DeviceInfo& dev)
            {
                return !configuredGuid.empty()
                    ? dev.guidKey == configuredGuid
                    : dev.name == Settings::WheelUniversalDeviceName.get();
            };
            if (ImGui::BeginCombo("Wheel", preview.c_str()))
            {
                for (size_t i = 0; i < devices.size(); ++i)
                {
                    const bool selected = isSelectedDevice(devices[i]);
                    const std::string label = devices[i].name + "##" + devices[i].guidKey;
                    if (ImGui::Selectable(label.c_str(), selected)) select_device(devices[i]);
                    if (selected) ImGui::SetItemDefaultFocus();
                }
                ImGui::EndCombo();
            }
            for (const auto& dev : devices)
                if (isSelectedDevice(dev))
                    ImGui::TextDisabled("%lu axes / %lu buttons / %lu POV / FFB %s / GUID %s",
                        dev.axes, dev.buttons, dev.povs, dev.ffb ? "yes" : "no", dev.guidKey.c_str());

            if (!Settings::UseNewInput)
            {
            const int regularSlots = UniversalWheelProfile::regular_device_count();
            if (regularSlots == 1)
                Settings::WheelUniversalLegacyDeviceIndex = 0;
            if (regularSlots > 0)
            {
                int currentSlot = std::clamp(
                    int(Settings::WheelUniversalLegacyDeviceIndex), 0,
                    std::min(regularSlots - 1, 2));
                if (currentSlot != int(Settings::WheelUniversalLegacyDeviceIndex))
                    Settings::WheelUniversalLegacyDeviceIndex = currentSlot;
                const std::string slotPreview =
                    "OutRun slot " + std::to_string(currentSlot + 1);
                if (ImGui::BeginCombo("Legacy input slot", slotPreview.c_str()))
                {
                    for (int slot = 0; slot < std::min(regularSlots, 3); ++slot)
                    {
                        const std::string label =
                            "OutRun slot " + std::to_string(slot + 1);
                        const bool selected = slot == currentSlot;
                        if (ImGui::Selectable(label.c_str(), selected))
                            Settings::WheelUniversalLegacyDeviceIndex = slot;
                        if (selected)
                            ImGui::SetItemDefaultFocus();
                    }
                    ImGui::EndCombo();
                }
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip(
                        "This is OutRun's original DirectInput slot, not the filtered Wheel combo index. Usually slot 1 when only one wheel is connected.");
            }

            if (ImGui::Checkbox("Enable F11 universal wheel profile", Settings::WheelUniversalSetupEnable.ptr()))
            {
                if (Settings::WheelUniversalSetupEnable)
                {
                    // The old R3-specific readers assume fixed button numbers.
                    // Once a universal profile is active, its own bindings must
                    // be the sole wheel-menu source so Logitech/Thrustmaster/
                    // Fanatec/Simagic/etc. do not inherit R3 button mappings.
                    Settings::WheelMenuR3DirectDPad = false;
                    Settings::WheelMenuR3DirectAB = false;
                    status_ = "Universal profile enabled; legacy R3 fixed-button menu helpers were disabled.";
                }
            }
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("When enabled, these bindings are written into OutRun's original legacy DirectInput device mapping.");

            ImGui::SameLine();
            if (ImGui::Button("Import current game mapping"))
            {
                if (UniversalWheelProfile::copy_current_mapping())
                {
                    Settings::WheelUniversalSetupEnable = true;
                    Settings::WheelMenuR3DirectDPad = false;
                    Settings::WheelMenuR3DirectAB = false;
                    status_ = "Imported current steering/pedal/shift bindings. Universal menu ownership enabled; add menu bindings below.";
                }
                else
                    status_ = "No regular legacy DirectInput game device is ready yet.";
            }

            ImGui::SeparatorText("Driving");
            axis_row("Steering", BindTarget::Steering, Settings::WheelUniversalSteeringAxis,
                Settings::WheelUniversalSteeringInvert.ptr(), true);
            axis_row("Accelerator", BindTarget::Throttle, Settings::WheelUniversalThrottleAxis,
                Settings::WheelAccelerationInvert.ptr(), false);
            axis_row("Brake", BindTarget::Brake, Settings::WheelUniversalBrakeAxis,
                Settings::WheelBrakeInvert.ptr(), false);

            button_row("Gear Up", BindTarget::GearUp, Settings::WheelUniversalGearUpButton);
            button_row("Gear Down", BindTarget::GearDown, Settings::WheelUniversalGearDownButton);
            button_row("Start", BindTarget::Start, Settings::WheelUniversalStartButton);
            button_row("Change View", BindTarget::View, Settings::WheelUniversalViewButton);

            ImGui::SeparatorText("Menus");
            button_row("Accept / OK", BindTarget::MenuAccept, Settings::WheelUniversalMenuAccept);
            button_row("Back / Cancel", BindTarget::MenuBack, Settings::WheelUniversalMenuBack);
            button_row("Menu Up", BindTarget::MenuUp, Settings::WheelUniversalMenuUp);
            button_row("Menu Right", BindTarget::MenuRight, Settings::WheelUniversalMenuRight);
            button_row("Menu Down", BindTarget::MenuDown, Settings::WheelUniversalMenuDown);
            button_row("Menu Left", BindTarget::MenuLeft, Settings::WheelUniversalMenuLeft);

            if (ImGui::Button("MOZA R3/ES menu defaults"))
                apply_r3_menu_defaults();
            }

            ImGui::SeparatorText("Simulation FFB");
            ImGui::Checkbox("Enable Force Feedback", Settings::WheelFFBEnable.ptr());
            ImGui::TextDisabled("gameplay FFB follows the exact selected DirectInput GUID.");
            ImGui::TextWrapped(
                "Single-owner wheel FFB: DirectInput COM only. field_264/268 are lateral load only; body slip releases damping, while front slip drives Physics SAT and tire scrub. Centering Spring remains a low-speed stabilizer.");
            ImGui::TextDisabled("Settings > WheelFFB is hidden; changes on this page apply live. SDL gamepad rumble is suppressed while wheel FFB is enabled.");

            ImGui::SliderFloat("Overall Strength", Settings::WheelFFBGlobalStrength.ptr(), 0.0f, 1.5f, "%.2f");
            if (Settings::WheelFFBGlobalStrength.get() > 1.0f)
                ImGui::TextColored(ImVec4(1.0f, 0.65f, 0.25f, 1.0f),
                    "Above 100% trades force-detail contrast for extra weight.");
            ImGui::SliderFloat("Centering Spring (low speed)", Settings::WheelFFBSpringStrength.ptr(), 0.0f, 1.0f, "%.2f");
            ImGui::SliderFloat("Dynamic Damping", Settings::WheelFFBDamperStrength.ptr(), 0.0f, 0.80f, "%.2f");
            ImGui::SliderFloat("Self-aligning Torque (SAT)", Settings::WheelFFBSteeringWeight.ptr(), 0.0f, 2.00f, "%.2f");
            ImGui::Checkbox("Physics SAT (body slip + yaw)", Settings::WheelFFBPhysicsSat.ptr());
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Uses post-physics OutRun car motion/body heading to estimate front slip. Disable for the Natural SAT comparison.");
            ImGui::SliderFloat("Grip-loss Response", Settings::WheelFFBGripLoss.ptr(), 0.0f, 1.0f, "%.2f");
            ImGui::SliderFloat("Road Detail", Settings::WheelFFBRoadTexture.ptr(), 0.0f, 0.50f, "%.2f");
            ImGui::SliderFloat("Tire Slip", Settings::WheelFFBTireSlip.ptr(), 0.0f, 0.50f, "%.2f");
            ImGui::SliderFloat("Collision", Settings::WheelFFBWallImpact.ptr(), 0.0f, 1.0f, "%.2f");
            ImGui::Checkbox("Hardware GUID_Spring", Settings::WheelFFBUseHardwareSpring.ptr());
            ImGui::SameLine();
            ImGui::Checkbox("Hardware GUID_Damper", Settings::WheelFFBUseHardwareDamper.ptr());
            ImGui::Checkbox("Hardware road/slip sine effects", Settings::WheelFFBUsePeriodicEffects.ptr());
            ImGui::SameLine();
            ImGui::Checkbox("Diagnostic logging", Settings::WheelFFBDebugLog.ptr());
            ImGui::Checkbox("Record driving telemetry (10 Hz)", Settings::WheelFFBTelemetry.ptr());
            ImGui::Checkbox("Reverse SAT / ConstantForce", Settings::WheelFFBInvertForce.ptr());
            ImGui::SameLine();
            ImGui::Checkbox("Reverse Spring", Settings::WheelFFBInvertSpring.ptr());
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip("Use Reverse Spring only if the wheel pushes farther away from centre. ConstantForce direction is independent.");

            if (ImGui::Button("Save Force Feedback"))
                status_ = Settings::write(Module::UserIniPath)
                    ? "Force feedback settings saved." : "Could not save force feedback settings.";

            ImGui::SeparatorText("Safe direction test");
            if (ImGui::Button("Test Left (20%)"))
                WheelFFB_RequestDirectionTest(-1);
            ImGui::SameLine();
            if (ImGui::Button("Test Right (20%)"))
                WheelFFB_RequestDirectionTest(1);
            ImGui::SameLine();
            if (ImGui::Button("Stop Test"))
                WheelFFB_RequestDirectionTest(0);
            ImGui::TextDisabled("Direction tests are hard-capped at 20% and only run during active gameplay.");

            if (ImGui::Button("Load MOZA R3 Physics SAT"))
            {
                Settings::WheelFFBEnable = true;
                Settings::WheelFFBPhysicsSat = true;
                Settings::WheelFFBGlobalStrength = 0.70f;
                Settings::WheelFFBSpringStrength = 0.65f;
                Settings::WheelFFBSpringSaturation = 0.95f;
                Settings::WheelFFBDamperStrength = 0.28f;
                Settings::WheelFFBSteeringWeight = 1.45f;
                Settings::WheelFFBGripLoss = 0.65f;
                Settings::WheelFFBWeightTransfer = 0.15f;
                Settings::WheelFFBSlewRate = 0.040f;
                Settings::WheelFFBRoadTexture = 0.30f;
                Settings::WheelFFBTireSlip = 0.20f;
                Settings::WheelFFBWallImpact = 0.38f;
                Settings::WheelFFBUseHardwareSpring = true;
                Settings::WheelFFBUseHardwareDamper = true;
                Settings::WheelFFBUsePeriodicEffects = true;
                Settings::WheelFFBInvertForce = true;
                Settings::WheelFFBInvertSpring = false;
                Settings::WheelFFBDebugLog = true;
                Settings::VibrationMode = 0;
                Settings::write(Module::UserIniPath);
                status_ = "Loaded MOZA R3 Physics SAT: lateral load, body slide and front scrub are separated; diagnostic logging enabled. Saved to user.ini.";
            }
            ImGui::SameLine();

            if (ImGui::Button("Load MOZA R3 Natural SAT"))
            {
                Settings::WheelFFBPhysicsSat = false;
                Settings::WheelFFBEnable = true;
                Settings::WheelFFBGlobalStrength = 0.70f;
                Settings::WheelFFBSpringStrength = 0.65f;
                Settings::WheelFFBSpringSaturation = 0.95f;
                Settings::WheelFFBDamperStrength = 0.30f;
                Settings::WheelFFBSteeringWeight = 1.75f;
                Settings::WheelFFBGripLoss = 0.65f;
                Settings::WheelFFBWeightTransfer = 0.20f;
                Settings::WheelFFBSlewRate = 0.045f;
                Settings::WheelFFBRoadTexture = 0.30f;
                Settings::WheelFFBTireSlip = 0.20f;
                Settings::WheelFFBWallImpact = 0.38f;
                Settings::WheelFFBUseHardwareSpring = true;
                Settings::WheelFFBUseHardwareDamper = true;
                Settings::WheelFFBUsePeriodicEffects = true;
                Settings::WheelFFBInvertForce = true;
                Settings::WheelFFBInvertSpring = false;
                Settings::VibrationMode = 0;
                Settings::write(Module::UserIniPath);
                status_ = "Loaded MOZA R3 Natural SAT: smooth progressive SAT, low-speed-only spring assist and single DirectInput COM wheel FFB. Saved to user.ini.";
            }

            if (!Settings::UseNewInput)
            {
            ImGui::SeparatorText("Wheel options");
            int deadzonePercent = int(float(Settings::SteeringDeadZone) * 100.0f + 0.5f);
            if (ImGui::SliderInt("Steering Deadzone", &deadzonePercent, 0, 20, "%d%%"))
                Settings::SteeringDeadZone = deadzonePercent / 100.0f;

            if (ImGui::Button("Apply Now"))
            {
                UniversalWheelProfile::apply_now();
                status_ = "Applied to the current legacy game device.";
            }
            ImGui::SameLine();
            if (ImGui::Button("Save Wheel Profile"))
                save();
            }

            if (target_ != BindTarget::None)
            {
                ImGui::Separator();
                ImGui::TextColored(ImVec4(1, 1, 0, 1), "Listening for input...  (Esc cancels)");
            }
            if (!status_.empty())
                ImGui::TextWrapped("%s", status_.c_str());

            ImGui::Spacing();
            ImGui::TextDisabled(
                Settings::UseNewInput
                    ? "Input setup: Input Bindings only. FFB setup: this Force Feedback page only. Restart after switching to a different physical wheel."
                    : "Legacy compatibility input and FFB are configured on this page. Restart after switching to a different physical wheel.");
        }

        static WheelSetupWindow instance;
    };

    WheelSetupWindow WheelSetupWindow::instance;
}
