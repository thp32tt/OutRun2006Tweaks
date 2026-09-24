#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <bitset>
#include <cstdint>
#include <cstring>
#include <mutex>
#include <string>
#include <unordered_set>

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

    Setting<bool> KoreanK3Trace{
        "Localization",
        "KoreanK3Trace",
        false,
        "K3 research trace. Logs a limited set of text-width strings and glyph bytes "
        "without changing layout or rendering."
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


class KoreanK3TraceHook : public Hook
{
    static constexpr uintptr_t StringWidthOffset = 0x2C480;
    static constexpr uintptr_t GlyphDrawOffset = 0x2C720;
    static constexpr size_t MaxUniqueStrings = 128;
    static constexpr size_t MaxLoggedGlyphCodes = 128;
    static constexpr size_t MaxPreviewBytes = 96;

    static constexpr uint8_t ExpectedStringWidthBytes[] = {
        0x83, 0xEC, 0x10, 0x56, 0x57, 0x33, 0xFF, 0x8B,
        0xF0, 0x89, 0x7C, 0x24, 0x08, 0x8D, 0x50, 0x01
    };

    static constexpr uint8_t ExpectedGlyphDrawBytes[] = {
        0x8B, 0x0D, 0xA0, 0x6B, 0x95, 0x00, 0x83, 0xEC,
        0x4C, 0x85, 0xC9, 0x0F, 0x84, 0xE1, 0x00, 0x00
    };

    inline static SafetyHookMid StringWidthHook{};
    inline static SafetyHookMid GlyphDrawHook{};
    inline static std::mutex TraceMutex{};
    inline static std::unordered_set<std::string> SeenStrings{};
    inline static std::unordered_set<uint32_t> SeenFontHandles{};
    inline static std::bitset<256> SeenGlyphCodes{};
    inline static size_t LoggedGlyphCodes = 0;

    static constexpr uintptr_t FontTexturePtrOffset = 0x556BA0;
    static constexpr uintptr_t KerningTableOffset = 0x556BA4;
    static constexpr uintptr_t FontHandleOffset = 0x556BAC;
    static constexpr uintptr_t TextureWidthOffset = 0x556BB0;
    static constexpr uintptr_t TextureHeightOffset = 0x556BB2;
    static constexpr uintptr_t CursorXOffset = 0x556BB8;
    static constexpr uintptr_t CursorYOffset = 0x556BBA;
    static constexpr uintptr_t CellWidthOffset = 0x556BBC;
    static constexpr uintptr_t CellHeightOffset = 0x556BBE;
    static constexpr uintptr_t ScaleXOffset = 0x556BC4;
    static constexpr uintptr_t ScaleYOffset = 0x556BC8;
    static constexpr uintptr_t ColorOffset = 0x556BCC;
    static constexpr uintptr_t LayerOffset = 0x556BD0;
    static constexpr uintptr_t BaseCodeOffset = 0x556BD4;
    static constexpr uintptr_t FlagsOffset = 0x556BD8;
    static constexpr uintptr_t LetterSpacingOffset = 0x556BDC;
    static constexpr uintptr_t LineAdvanceOffset = 0x556BE0;

    static std::string PreviewString(const char* text)
    {
        if (!text)
            return {};

        size_t len = 0;
        while (len < MaxPreviewBytes && text[len] != '\0')
            ++len;

        return std::string(text, len);
    }

    static void StringWidthDest(SafetyHookContext& ctx)
    {
        const char* text = reinterpret_cast<const char*>(ctx.eax);
        if (!text)
            return;

        const std::string preview = PreviewString(text);
        if (preview.empty())
            return;

        std::scoped_lock lock(TraceMutex);

        const uint32_t fontHandle = *Module::exe_ptr<uint32_t>(FontHandleOffset);
        if (SeenFontHandles.insert(fontHandle).second)
        {
            const uintptr_t texturePtr =
                reinterpret_cast<uintptr_t>(*Module::exe_ptr<void*>(FontTexturePtrOffset));
            const uintptr_t kerningPtr =
                reinterpret_cast<uintptr_t>(*Module::exe_ptr<void*>(KerningTableOffset));

            spdlog::info(
                "KoreanK3Trace: font_state handle=0x{:08X} texture={:p} kerning={:p} "
                "tex={}x{} cell={}x{} cursor=({}, {}) scale=({:.4f}, {:.4f}) "
                "color=0x{:08X} layer={} base_code={} flags=0x{:08X} spacing={:.4f} line_advance={:.4f}",
                fontHandle,
                reinterpret_cast<void*>(texturePtr),
                reinterpret_cast<void*>(kerningPtr),
                *Module::exe_ptr<uint16_t>(TextureWidthOffset),
                *Module::exe_ptr<uint16_t>(TextureHeightOffset),
                *Module::exe_ptr<int16_t>(CellWidthOffset),
                *Module::exe_ptr<int16_t>(CellHeightOffset),
                *Module::exe_ptr<int16_t>(CursorXOffset),
                *Module::exe_ptr<int16_t>(CursorYOffset),
                *Module::exe_ptr<float>(ScaleXOffset),
                *Module::exe_ptr<float>(ScaleYOffset),
                *Module::exe_ptr<uint32_t>(ColorOffset),
                *Module::exe_ptr<uint32_t>(LayerOffset),
                *Module::exe_ptr<uint32_t>(BaseCodeOffset),
                *Module::exe_ptr<uint32_t>(FlagsOffset),
                *Module::exe_ptr<float>(LetterSpacingOffset),
                *Module::exe_ptr<float>(LineAdvanceOffset));
        }

        if (SeenStrings.size() >= MaxUniqueStrings)
            return;

        if (SeenStrings.insert(preview).second)
        {
            bool hasHighBit = false;
            for (unsigned char ch : preview)
            {
                if (ch >= 0x80)
                {
                    hasHighBit = true;
                    break;
                }
            }

            spdlog::info(
                "KoreanK3Trace: width_text='{}' bytes={} high_bit={}",
                preview,
                preview.size(),
                hasHighBit);
        }
    }

    static void GlyphDrawDest(SafetyHookContext& ctx)
    {
        const uint8_t glyph = static_cast<uint8_t>(ctx.eax & 0xFF);

        std::scoped_lock lock(TraceMutex);
        if (SeenGlyphCodes.test(glyph) || LoggedGlyphCodes >= MaxLoggedGlyphCodes)
            return;

        SeenGlyphCodes.set(glyph);
        ++LoggedGlyphCodes;

        spdlog::info(
            "KoreanK3Trace: glyph_code=0x{:02X} ascii_printable={}",
            glyph,
            glyph >= 0x20 && glyph <= 0x7E);
    }

public:
    std::string_view description() override
    {
        return "KoreanK3Trace";
    }

    void declare_settings() override
    {
        Settings::KoreanK3Trace.needs_restart();
    }

    bool validate() override
    {
        if (!Settings::KoreanK3Trace)
            return false;

        const uint8_t* width = Module::exe_ptr(StringWidthOffset);
        const uint8_t* glyph = Module::exe_ptr(GlyphDrawOffset);
        if (!width || !glyph)
            return false;

        if (std::memcmp(width, ExpectedStringWidthBytes, sizeof(ExpectedStringWidthBytes)) != 0)
        {
            spdlog::error(
                "KoreanK3Trace: string-width signature mismatch at EXE+0x{:X}; refusing hook",
                StringWidthOffset);
            return false;
        }

        if (std::memcmp(glyph, ExpectedGlyphDrawBytes, sizeof(ExpectedGlyphDrawBytes)) != 0)
        {
            spdlog::error(
                "KoreanK3Trace: glyph-draw signature mismatch at EXE+0x{:X}; refusing hook",
                GlyphDrawOffset);
            return false;
        }

        return true;
    }

    bool apply() override
    {
        StringWidthHook = safetyhook::create_mid(
            Module::exe_ptr(StringWidthOffset),
            StringWidthDest);

        GlyphDrawHook = safetyhook::create_mid(
            Module::exe_ptr(GlyphDrawOffset),
            GlyphDrawDest);

        spdlog::info(
            "KoreanK3Trace: installed width/glyph research hooks at EXE+0x{:X} and EXE+0x{:X}",
            StringWidthOffset,
            GlyphDrawOffset);
        return true;
    }

    static KoreanK3TraceHook instance;
};

KoreanK3TraceHook KoreanK3TraceHook::instance;
