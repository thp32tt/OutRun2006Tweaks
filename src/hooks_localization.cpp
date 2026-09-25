#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <algorithm>
#include <array>
#include <bitset>
#include <cstdarg>
#include <cstdint>
#include <cfloat>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include <imgui.h>

#include "game_addrs.hpp"
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

    Setting<bool> KoreanTextOverlayTest{
        "Localization",
        "KoreanTextOverlayTest",
        false,
        "Experimental full Korean text test renderer. Tracks stock text IDs, suppresses "
        "their English glyph output, and redraws Korean UTF-8 text through the existing "
        "D3D9 ImGui overlay. Requires Overlay.Enabled=true."
    };
}


namespace KoreanRuntime
{
    static constexpr size_t TextEntryCount = 1356;
    static constexpr size_t MaxQueuedDraws = 1024;
    static constexpr size_t MaxFormattedBytes = 4096;

    struct DrawCommand
    {
        std::string text;
        int16_t x = 0;
        int16_t y = 0;
        int16_t cellHeight = 16;
        float scaleY = 1.0f;
        uint32_t color = 0xFFFFFFFF;
        uint32_t flags = 1;
    };

    inline static std::array<std::string, TextEntryCount> Translations{};
    inline static bool TranslationsLoaded = false;
    inline static std::unordered_map<const char*, uint32_t> PointerToId{};
    inline static std::unordered_map<std::string, uint32_t> TextToId{};
    inline static std::mutex StateMutex{};
    inline static std::vector<DrawCommand> DrawQueue{};

    static std::string UnescapeField(const std::string& input)
    {
        std::string out;
        out.reserve(input.size());
        for (size_t i = 0; i < input.size(); ++i)
        {
            if (input[i] != '\\' || i + 1 >= input.size())
            {
                out.push_back(input[i]);
                continue;
            }

            const char next = input[++i];
            switch (next)
            {
            case 'n': out.push_back('\n'); break;
            case 'r': out.push_back('\r'); break;
            case 't': out.push_back('\t'); break;
            case '\\': out.push_back('\\'); break;
            default:
                out.push_back('\\');
                out.push_back(next);
                break;
            }
        }
        return out;
    }

    static bool LoadTranslations()
    {
        if (TranslationsLoaded)
            return true;

        const std::filesystem::path candidates[] = {
            Module::DllPath.parent_path() / "localization" / "text" / "runtime_ko.tsv",
            Module::DllPath.parent_path() / "runtime_ko.tsv"
        };

        std::ifstream file;
        std::filesystem::path loadedPath;
        for (const auto& path : candidates)
        {
            file.open(path, std::ios::binary);
            if (file)
            {
                loadedPath = path;
                break;
            }
            file.clear();
        }

        if (!file)
        {
            spdlog::error(
                "KoreanTextOverlayTest: runtime_ko.tsv was not found next to the DLL; "
                "leaving stock English text untouched");
            return false;
        }

        size_t loaded = 0;
        std::string line;
        while (std::getline(file, line))
        {
            if (!line.empty() && line.back() == '\r')
                line.pop_back();

            const size_t tab = line.find('\t');
            if (tab == std::string::npos)
                continue;

            try
            {
                const uint32_t id = static_cast<uint32_t>(std::stoul(line.substr(0, tab)));
                if (id >= TextEntryCount)
                    continue;

                Translations[id] = UnescapeField(line.substr(tab + 1));
                if (!Translations[id].empty())
                    ++loaded;
            }
            catch (...)
            {
                continue;
            }
        }

        TranslationsLoaded = loaded > 0;
        if (TranslationsLoaded)
        {
            spdlog::info(
                "KoreanTextOverlayTest: loaded {} Korean text rows from '{}'",
                loaded,
                loadedPath.string());
        }
        return TranslationsLoaded;
    }

    static void RememberText(uint32_t id, const char* text)
    {
        if (!Settings::KoreanTextOverlayTest || !text || id >= TextEntryCount)
            return;
        if (!TranslationsLoaded || Translations[id].empty())
            return;

        std::scoped_lock lock(StateMutex);
        PointerToId[text] = id;
        TextToId.emplace(std::string(text), id);
    }

    static bool ResolveTextId(const char* text, uint32_t& id)
    {
        if (!text)
            return false;

        std::scoped_lock lock(StateMutex);

        if (const auto it = PointerToId.find(text); it != PointerToId.end())
        {
            id = it->second;
            return id < TextEntryCount && !Translations[id].empty();
        }

        if (const auto it = TextToId.find(std::string(text)); it != TextToId.end())
        {
            id = it->second;
            return id < TextEntryCount && !Translations[id].empty();
        }

        return false;
    }

    static std::string FormatTranslation(const std::string& format, uintptr_t firstArgAddress)
    {
        if (format.find('%') == std::string::npos)
            return format;

        char buffer[MaxFormattedBytes]{};
#if defined(_M_IX86)
        va_list args = reinterpret_cast<va_list>(firstArgAddress);
        const int result = _vsnprintf_s(
            buffer,
            sizeof(buffer),
            _TRUNCATE,
            format.c_str(),
            args);
        if (result >= 0 || buffer[0] != '\0')
            return std::string(buffer);
#endif
        return format;
    }

    static std::string BuildHiddenLayout(const std::string& utf8)
    {
        std::string hidden;
        hidden.reserve(utf8.size());

        for (size_t i = 0; i < utf8.size();)
        {
            const unsigned char ch = static_cast<unsigned char>(utf8[i]);
            if (ch == '\n' || ch == '\r' || ch == '\t')
            {
                hidden.push_back(static_cast<char>(ch));
                ++i;
                continue;
            }

            if (ch < 0x80)
            {
                hidden.push_back(' ');
                ++i;
                continue;
            }

            hidden.push_back(' ');
            size_t advance = 1;
            if ((ch & 0xE0) == 0xC0) advance = 2;
            else if ((ch & 0xF0) == 0xE0) advance = 3;
            else if ((ch & 0xF8) == 0xF0) advance = 4;

            i += (std::min)(advance, utf8.size() - i);
        }

        return hidden;
    }

    static void Queue(uint32_t id, uintptr_t firstArgAddress)
    {
        if (id >= TextEntryCount || Translations[id].empty())
            return;

        DrawCommand cmd;
        cmd.text = FormatTranslation(Translations[id], firstArgAddress);
        cmd.x = *Module::exe_ptr<int16_t>(0x556BB8);
        cmd.y = *Module::exe_ptr<int16_t>(0x556BBA);
        cmd.cellHeight = *Module::exe_ptr<int16_t>(0x556BBE);
        cmd.scaleY = *Module::exe_ptr<float>(0x556BC8);
        cmd.color = *Module::exe_ptr<uint32_t>(0x556BCC);
        cmd.flags = *Module::exe_ptr<uint32_t>(0x556BD8);

        std::scoped_lock lock(StateMutex);
        if (DrawQueue.size() < MaxQueuedDraws)
            DrawQueue.emplace_back(std::move(cmd));
    }

    static void InterceptPrint(SafetyHookContext& ctx)
    {
        if (!Settings::KoreanTextOverlayTest || !Settings::OverlayEnabled)
            return;
        if (!TranslationsLoaded)
            return;

        const uintptr_t stack = static_cast<uintptr_t>(ctx.esp);
        const char** formatSlot = reinterpret_cast<const char**>(stack + 4);
        if (!formatSlot || !*formatSlot)
            return;

        uint32_t id = 0;
        if (!ResolveTextId(*formatSlot, id))
            return;

        Queue(id, stack + 8);

        thread_local std::string hiddenLayout;
        hiddenLayout = BuildHiddenLayout(
            FormatTranslation(Translations[id], stack + 8));

        // Preserve newlines/layout progression while ensuring the stock 7-bit
        // glyph path has no visible English characters to draw.
        *formatSlot = hiddenLayout.c_str();
    }

    static ImU32 ConvertColor(uint32_t argb)
    {
        const uint8_t a = static_cast<uint8_t>((argb >> 24) & 0xFF);
        const uint8_t r = static_cast<uint8_t>((argb >> 16) & 0xFF);
        const uint8_t g = static_cast<uint8_t>((argb >> 8) & 0xFF);
        const uint8_t b = static_cast<uint8_t>(argb & 0xFF);
        return IM_COL32(r, g, b, a ? a : 0xFF);
    }

    static void Draw()
    {
        if (!Settings::KoreanTextOverlayTest || !Settings::OverlayEnabled)
            return;
        if (!TranslationsLoaded || ImGui::GetCurrentContext() == nullptr)
            return;

        std::vector<DrawCommand> queue;
        {
            std::scoped_lock lock(StateMutex);
            queue.swap(DrawQueue);
        }

        if (queue.empty())
            return;

        ImDrawList* drawList = ImGui::GetForegroundDrawList();
        ImFont* font = ImGui::GetFont();
        const ImVec2 display = ImGui::GetIO().DisplaySize;

        float sx = display.x / 640.0f;
        float sy = display.y / 480.0f;
        if (Game::screen_scale)
        {
            sx = Game::screen_scale->x;
            sy = Game::screen_scale->y;
        }

        const bool uniformUi = Settings::UIScalingMode > 0;
        const float uiScale = uniformUi ? ((sx < sy) ? sx : sy) : 1.0f;
        const float mapScaleX = uniformUi ? uiScale : sx;
        const float mapScaleY = uniformUi ? uiScale : sy;
        const float centerX = uniformUi ? (display.x - (640.0f * uiScale)) * 0.5f : 0.0f;

        for (const DrawCommand& cmd : queue)
        {
            if (cmd.text.empty())
                continue;

            const float cellHeight = static_cast<float>(cmd.cellHeight == 0 ? 16 : std::abs(cmd.cellHeight));
            const float logicalFontHeight = (std::max)(8.0f, cellHeight * (std::max)(0.05f, std::fabs(cmd.scaleY)));
            const float fontSize = (std::max)(8.0f, logicalFontHeight * mapScaleY);

            float logicalX = static_cast<float>(cmd.x);
            float logicalY = static_cast<float>(cmd.y);

            // Match the stock vertical alignment helper at 0x42C390.
            if (cmd.flags & 0x08)
                logicalY -= cellHeight * 0.5f;
            else if (cmd.flags & 0x10)
                logicalY -= cellHeight;

            float x = (logicalX * mapScaleX) + centerX;
            const float y = logicalY * mapScaleY;

            const ImVec2 size = font->CalcTextSizeA(
                fontSize,
                FLT_MAX,
                0.0f,
                cmd.text.c_str());

            // Match stock left/center/right behavior: bit 0 = left, bit 2 = centered.
            if ((cmd.flags & 0x01) == 0)
            {
                if (cmd.flags & 0x04)
                    x -= size.x * 0.5f;
                else
                    x -= size.x;
            }

            drawList->AddText(
                font,
                fontSize,
                ImVec2(x, y),
                ConvertColor(cmd.color),
                cmd.text.c_str());
        }
    }
}

void KoreanLocalization_DrawOverlay()
{
    KoreanRuntime::Draw();
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

        KoreanRuntime::RememberText(id, originalText);
        if (returnedText != originalText)
            KoreanRuntime::RememberText(id, returnedText);

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
        Settings::KoreanTextOverlayTest.needs_restart();
    }

    bool validate() override
    {
        if (!Settings::KoreanLocalizationTrace &&
            !Settings::KoreanProofTextOverride &&
            !Settings::KoreanTextOverlayTest)
            return false;

        if (Settings::KoreanTextOverlayTest)
        {
            if (!Settings::OverlayEnabled)
            {
                spdlog::error(
                    "KoreanTextOverlayTest: Overlay.Enabled must be true; "
                    "leaving stock English text untouched");
                return false;
            }

            if (!KoreanRuntime::LoadTranslations())
                return false;
        }

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


class KoreanTextOverlayPrintHook : public Hook
{
    static constexpr uintptr_t SprPrintfOffset = 0x2CCE0;
    static constexpr uintptr_t SumoPrintfOffset = 0x2CDD0;

    static constexpr uint8_t ExpectedSprPrintfBytes[] = {
        0x81, 0xEC, 0x08, 0x01, 0x00, 0x00, 0xA1, 0x00,
        0x5A, 0x73, 0x00, 0x8B, 0x8C, 0x24, 0x0C, 0x01
    };

    static constexpr uint8_t ExpectedSumoPrintfBytes[] = {
        0x81, 0xEC, 0x04, 0x01, 0x00, 0x00, 0xA1, 0x00,
        0x5A, 0x73, 0x00, 0x8B, 0x8C, 0x24, 0x08, 0x01
    };

    inline static SafetyHookMid SprPrintfHook{};
    inline static SafetyHookMid SumoPrintfHook{};

    static void SprPrintfDest(SafetyHookContext& ctx)
    {
        KoreanRuntime::InterceptPrint(ctx);
    }

    static void SumoPrintfDest(SafetyHookContext& ctx)
    {
        KoreanRuntime::InterceptPrint(ctx);
    }

public:
    std::string_view description() override
    {
        return "KoreanTextOverlayPrint";
    }

    void declare_settings() override
    {
        Settings::KoreanTextOverlayTest.needs_restart();
    }

    bool validate() override
    {
        if (!Settings::KoreanTextOverlayTest)
            return false;

        if (!Settings::OverlayEnabled || !KoreanRuntime::LoadTranslations())
            return false;

        const uint8_t* spr = Module::exe_ptr(SprPrintfOffset);
        const uint8_t* sumo = Module::exe_ptr(SumoPrintfOffset);
        if (!spr || !sumo)
            return false;

        if (std::memcmp(spr, ExpectedSprPrintfBytes, sizeof(ExpectedSprPrintfBytes)) != 0)
        {
            spdlog::error(
                "KoreanTextOverlayTest: sprPrintf signature mismatch at EXE+0x{:X}",
                SprPrintfOffset);
            return false;
        }

        if (std::memcmp(sumo, ExpectedSumoPrintfBytes, sizeof(ExpectedSumoPrintfBytes)) != 0)
        {
            spdlog::error(
                "KoreanTextOverlayTest: Sumo_Printf signature mismatch at EXE+0x{:X}",
                SumoPrintfOffset);
            return false;
        }

        return true;
    }

    bool apply() override
    {
        SprPrintfHook = safetyhook::create_mid(
            Module::exe_ptr(SprPrintfOffset),
            SprPrintfDest);
        SumoPrintfHook = safetyhook::create_mid(
            Module::exe_ptr(SumoPrintfOffset),
            SumoPrintfDest);

        spdlog::info(
            "KoreanTextOverlayTest: installed UTF-8 text interception on sprPrintf/Sumo_Printf");
        return !!SprPrintfHook && !!SumoPrintfHook;
    }

    static KoreanTextOverlayPrintHook instance;
};

KoreanTextOverlayPrintHook KoreanTextOverlayPrintHook::instance;


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
