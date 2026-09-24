#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <bitset>
#include <cstdint>
#include <cstring>
#include <mutex>

#include "hook_mgr.hpp"
#include "plugin.hpp"

namespace Settings
{
    Setting<bool> KoreanLocalizationTrace{
        "Localization",
        "KoreanTrace",
        false,
        "Experimental Korean-localization text resolver trace. "
        "Logging only; does not replace or modify game text."
    };
}

class KoreanLocalizationTraceHook : public Hook
{
    static constexpr uintptr_t TextResolverOffset = 0x65EB0;
    static constexpr size_t TextEntryCount = 1356;
    static constexpr size_t MaxUniqueLogEntries = 128;

    static constexpr uint8_t ExpectedResolverBytes[] = {
        0x8B, 0x44, 0x24, 0x04,
        0x8B, 0x0D, 0x74, 0x8D, 0x7F, 0x00,
        0x8B, 0x04, 0x81,
        0xC3
    };

    inline static SafetyHookInline TextResolverHook{};
    inline static std::bitset<TextEntryCount> SeenIds{};
    inline static std::mutex SeenMutex{};
    inline static size_t UniqueLogEntries = 0;

    static char* __cdecl TextResolverDest(uint32_t id)
    {
        char* text = TextResolverHook.call<char*>(id);

        if (id < TextEntryCount)
        {
            std::scoped_lock lock(SeenMutex);
            if (!SeenIds.test(id) && UniqueLogEntries < MaxUniqueLogEntries)
            {
                SeenIds.set(id);
                ++UniqueLogEntries;
                spdlog::info(
                    "KoreanLocalizationTrace: text_id={} text='{}'",
                    id,
                    text ? text : "<null>");
            }
        }

        return text;
    }

public:
    std::string_view description() override
    {
        return "KoreanLocalizationTrace";
    }

    void declare_settings() override
    {
        Settings::KoreanLocalizationTrace.needs_restart();
    }

    bool validate() override
    {
        if (!Settings::KoreanLocalizationTrace)
            return false;

        const uint8_t* resolver = Module::exe_ptr(TextResolverOffset);
        if (!resolver)
        {
            spdlog::error("KoreanLocalizationTrace: EXE module is unavailable");
            return false;
        }

        if (std::memcmp(
                resolver,
                ExpectedResolverBytes,
                sizeof(ExpectedResolverBytes)) != 0)
        {
            spdlog::error(
                "KoreanLocalizationTrace: resolver signature mismatch at EXE+0x{:X}; "
                "refusing to install localization research hook",
                TextResolverOffset);
            return false;
        }

        return true;
    }

    bool apply() override
    {
        TextResolverHook = safetyhook::create_inline(
            Module::exe_ptr(TextResolverOffset),
            TextResolverDest);
        return true;
    }

    static KoreanLocalizationTraceHook instance;
};

KoreanLocalizationTraceHook KoreanLocalizationTraceHook::instance;
