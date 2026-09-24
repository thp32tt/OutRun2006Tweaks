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
        "Logging only unless a separate proof override is enabled."
    };

    Setting<bool> KoreanProofTextOverride{
        "Localization",
        "KoreanProofTextOverride",
        false,
        "K2 resolver proof. Replaces only text ID 0 with an ASCII marker. "
        "This does not enable Hangul rendering and is disabled by default."
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
    inline static char ProofTextId0[] = "[KOR-PROOF] Screen Position";

    static char* __cdecl TextResolverDest(uint32_t id)
    {
        char* originalText = TextResolverHook.call<char*>(id);
        char* returnedText = originalText;

        if (Settings::KoreanProofTextOverride && id == 0)
            returnedText = ProofTextId0;

        if (Settings::KoreanLocalizationTrace && id < TextEntryCount)
        {
            std::scoped_lock lock(SeenMutex);
            if (!SeenIds.test(id) && UniqueLogEntries < MaxUniqueLogEntries)
            {
                SeenIds.set(id);
                ++UniqueLogEntries;
                spdlog::info(
                    "KoreanLocalizationTrace: text_id={} original='{}' returned='{}' proof_override={}",
                    id,
                    originalText ? originalText : "<null>",
                    returnedText ? returnedText : "<null>",
                    Settings::KoreanProofTextOverride && id == 0);
            }
        }

        return returnedText;
    }

public:
    std::string_view description() override
    {
        return "KoreanLocalizationTrace";
    }

    void declare_settings() override
    {
        Settings::KoreanLocalizationTrace.needs_restart();
        Settings::KoreanProofTextOverride.needs_restart();
    }

    bool validate() override
    {
        if (!Settings::KoreanLocalizationTrace && !Settings::KoreanProofTextOverride)
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

        spdlog::info(
            "KoreanLocalizationTrace: trace={} proof_text_override={}",
            Settings::KoreanLocalizationTrace.get(),
            Settings::KoreanProofTextOverride.get());
        return true;
    }

    static KoreanLocalizationTraceHook instance;
};

KoreanLocalizationTraceHook KoreanLocalizationTraceHook::instance;
