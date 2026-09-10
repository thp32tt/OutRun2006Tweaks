#pragma once

#include <algorithm>
#include <cctype>
#include <string>

#include "hook_mgr.hpp"
#include "plugin.hpp"

// Some MOZA R3 driver/firmware combinations expose the wheel to DirectInput
// without the vendor string "MOZA" in the product/instance name. The game can
// still use that device perfectly, but our experimental helpers previously
// filtered it out by name before they ever tried CreateDevice/FFB.
//
// Keep explicit user device-name overrides intact. Only the shipped R3 default
// "MOZA" is relaxed to an empty filter, which means:
//   * menu helpers: first attached DirectInput controller
//   * FFB engine:   first attached non-virtual FORCEFEEDBACK controller
// Both helpers log the real selected Windows device name once opened, so a
// later build can pin a more specific name if needed.
namespace Settings
{
    extern Setting<std::string> WheelMenuR3DeviceName;
    extern Setting<std::string> WheelFFBDeviceName;
}

namespace
{
    static std::string r3_autoselect_lower(std::string value)
    {
        std::transform(value.begin(), value.end(), value.begin(),
            [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        return value;
    }

    class WheelR3DeviceAutoSelect : public Hook
    {
    public:
        std::string_view description() override
        {
            return "WheelR3DeviceAutoSelect";
        }

        bool validate() override
        {
            return Settings::WheelInputCompatibility && !Settings::UseNewInput;
        }

        bool apply() override
        {
            bool changed = false;

            if (r3_autoselect_lower(Settings::WheelMenuR3DeviceName.get()) == "moza")
            {
                // Keep the name: strict-first/fallback selection happens in the reader.
                changed = true;
            }

            if (r3_autoselect_lower(Settings::WheelFFBDeviceName.get()) == "moza")
            {
                // Keep the name: strict-first/fallback selection happens in the FFB engine.
                changed = true;
            }

            if (changed)
            {
                spdlog::info(
                    "WheelR3DeviceAutoSelect: MOZA default uses strict-name-first selection with an FFB-only fallback");
            }

            return true;
        }

        static WheelR3DeviceAutoSelect instance;
    };

    WheelR3DeviceAutoSelect WheelR3DeviceAutoSelect::instance;
}
