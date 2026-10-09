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
    Setting<bool> KoreanHudLayoutTrace{
        "Localization",
        "KoreanHudLayoutTrace",
        false,
        "IGR-042 HUD time/heart plus IGR-043 Stage/Rank text diagnostics. Logs bounded text IDs, "
        "stock coordinates, screen-space dimensions and compact keyline eligibility; "
        "does not change rendering, text selection or any DDS. Requires KoreanTextOverlayTest."
    };
}


namespace KoreanRuntime
{
    static constexpr size_t TextEntryCount = 1356;
    static constexpr size_t MaxQueuedDraws = 1024;
    static constexpr size_t MaxFormattedBytes = 4096;
    // Return site immediately after the stock local text-object Sumo_Printf("%s", text)
    // call at VA 0x48F455. B206 proved Edit License feeds the native player-name
    // field into this text object, so resolving only a sidecar-backed alias here
    // changes local presentation without touching save/ranking/network bytes.
    static constexpr uintptr_t LocalTextObjectPrintfReturnOffset = 0x8F45A;

    struct DrawCommand
    {
        uint32_t textId = TextEntryCount;
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
    inline static std::bitset<TextEntryCount> FormatMismatchLogged{};
    inline static std::mutex StateMutex{};
    inline static std::vector<DrawCommand> DrawQueue{};
    // IGR-042: bound opt-in log cardinality across repeated HUD frames/animation.
    // Only the render thread inserts keys; normal gameplay never enters the probe.
    inline static std::unordered_set<std::string> HudLayoutTraceSeen{};
    static constexpr size_t MaxHudLayoutTraceKeys = 96;
    // A203 IGR-043: log unique translated runtime Stage-vs-Rank collisions only.
    // This cannot detect a baked q44/q49 DDS-vs-overlay collision: live game
    // sprite composition evidence is still required before an asset rewrite.
    inline static std::unordered_set<std::string> StageRankOverlapSeen{};
    static constexpr size_t MaxStageRankOverlapKeys = 32;

    // Korean player-name storage must not replace the game's 16-byte legacy
    // field with UTF-8. Fixed-width ranking/network/save consumers proven by
    // B205/B206 require that native field to remain byte-compatible. The
    // sidecar below is deliberately keyed by an ASCII-safe alias which can be
    // stored in that native field later, once the input/render hooks are proven.
    static constexpr size_t NativePlayerNameFieldBytes = 16;
    static constexpr size_t NativePlayerNamePayloadBytes = NativePlayerNameFieldBytes - 1;
    static constexpr size_t KoreanPlayerNameAliasHashChars = 13;
    static constexpr char KoreanPlayerNameAliasPrefix = 'K';
    static constexpr char KoreanPlayerNameAliasAlphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    static constexpr char KoreanPlayerNameSidecarFilename[] = "KoreanPlayerNames.tsv";
    // Reserved transient token used only while the stock name-entry object is
    // being edited. It is never persisted and can therefore carry the composed
    // UTF-8 preview through the already-proven A142 local text-object renderer.
    static constexpr char KoreanPlayerNamePreviewAlias[] = "KAAAAAAAAAAAAA";
    static_assert(1 + KoreanPlayerNameAliasHashChars <= NativePlayerNamePayloadBytes);
    static_assert(
        sizeof(KoreanPlayerNamePreviewAlias) - 1 ==
        1 + KoreanPlayerNameAliasHashChars);

    inline static bool KoreanPlayerNameSidecarLoaded = false;
    inline static std::unordered_map<std::string, std::string> AliasToKoreanPlayerName{};
    inline static std::unordered_map<std::string, std::string> KoreanPlayerNameToAlias{};
    inline static std::string KoreanPlayerNamePreviewUtf8{};
    inline static std::mutex KoreanPlayerNameSidecarMutex{};

    static std::filesystem::path KoreanPlayerNameSidecarPath()
    {
        return Module::ExePath.parent_path() / "SaveGame" / KoreanPlayerNameSidecarFilename;
    }

    static bool IsValidKoreanPlayerNameUtf8(const std::string& value)
    {
        if (value.empty())
            return false;

        for (size_t i = 0; i < value.size();)
        {
            const uint8_t lead = static_cast<uint8_t>(value[i]);
            if (lead == '\t' || lead == '\r' || lead == '\n' || lead == 0 || lead == 0x7F)
                return false;

            if (lead < 0x20)
                return false;

            if (lead < 0x80)
            {
                ++i;
                continue;
            }

            size_t continuation = 0;
            uint32_t codepoint = 0;
            if (lead >= 0xC2 && lead <= 0xDF)
            {
                continuation = 1;
                codepoint = lead & 0x1F;
            }
            else if (lead >= 0xE0 && lead <= 0xEF)
            {
                continuation = 2;
                codepoint = lead & 0x0F;
            }
            else if (lead >= 0xF0 && lead <= 0xF4)
            {
                continuation = 3;
                codepoint = lead & 0x07;
            }
            else
            {
                return false;
            }

            if (i + continuation >= value.size())
                return false;

            for (size_t j = 1; j <= continuation; ++j)
            {
                const uint8_t next = static_cast<uint8_t>(value[i + j]);
                if ((next & 0xC0) != 0x80)
                    return false;
                codepoint = (codepoint << 6) | (next & 0x3F);
            }

            if ((continuation == 2 && codepoint < 0x800) ||
                (continuation == 3 && codepoint < 0x10000) ||
                (codepoint >= 0xD800 && codepoint <= 0xDFFF) ||
                codepoint > 0x10FFFF)
            {
                return false;
            }

            i += continuation + 1;
        }

        return true;
    }

    static bool IsValidKoreanPlayerNameAlias(const std::string& alias)
    {
        if (alias.size() != 1 + KoreanPlayerNameAliasHashChars ||
            alias.front() != KoreanPlayerNameAliasPrefix)
        {
            return false;
        }

        for (size_t i = 1; i < alias.size(); ++i)
        {
            if (!std::strchr(KoreanPlayerNameAliasAlphabet, alias[i]))
                return false;
        }
        return true;
    }

    static uint64_t HashKoreanPlayerNameAlias(const std::string& utf8, uint32_t salt)
    {
        uint64_t hash = 14695981039346656037ULL;
        constexpr uint64_t prime = 1099511628211ULL;

        for (const unsigned char ch : utf8)
        {
            hash ^= ch;
            hash *= prime;
        }

        // Delimit the UTF-8 payload from the collision salt so appending bytes
        // to a name cannot alias the same hash input as a salted shorter name.
        hash ^= 0xFF;
        hash *= prime;
        for (unsigned shift = 0; shift < 32; shift += 8)
        {
            hash ^= static_cast<uint8_t>((salt >> shift) & 0xFF);
            hash *= prime;
        }
        return hash;
    }

    static std::string MakeKoreanPlayerNameAlias(const std::string& utf8, uint32_t salt)
    {
        uint64_t hash = HashKoreanPlayerNameAlias(utf8, salt);
        std::string alias(1 + KoreanPlayerNameAliasHashChars, 'A');
        alias[0] = KoreanPlayerNameAliasPrefix;

        for (size_t i = 0; i < KoreanPlayerNameAliasHashChars; ++i)
        {
            const size_t pos = alias.size() - 1 - i;
            alias[pos] = KoreanPlayerNameAliasAlphabet[hash & 0x1F];
            hash >>= 5;
        }
        return alias;
    }

    static bool LoadKoreanPlayerNameSidecarLocked()
    {
        if (KoreanPlayerNameSidecarLoaded)
            return true;

        AliasToKoreanPlayerName.clear();
        KoreanPlayerNameToAlias.clear();

        const std::filesystem::path path = KoreanPlayerNameSidecarPath();
        if (!std::filesystem::exists(path))
        {
            KoreanPlayerNameSidecarLoaded = true;
            return true;
        }

        std::ifstream file(path, std::ios::binary);
        if (!file)
        {
            spdlog::error(
                "Korean player-name sidecar: failed to open '{}'",
                path.string());
            return false;
        }

        size_t loaded = 0;
        size_t rejected = 0;
        std::string line;
        while (std::getline(file, line))
        {
            if (!line.empty() && line.back() == '\r')
                line.pop_back();

            const size_t tab = line.find('\t');
            if (tab == std::string::npos)
            {
                ++rejected;
                continue;
            }

            const std::string alias = line.substr(0, tab);
            const std::string name = line.substr(tab + 1);
            if (!IsValidKoreanPlayerNameAlias(alias) ||
                alias == KoreanPlayerNamePreviewAlias ||
                !IsValidKoreanPlayerNameUtf8(name))
            {
                ++rejected;
                continue;
            }

            const auto aliasIt = AliasToKoreanPlayerName.find(alias);
            const auto nameIt = KoreanPlayerNameToAlias.find(name);
            if ((aliasIt != AliasToKoreanPlayerName.end() && aliasIt->second != name) ||
                (nameIt != KoreanPlayerNameToAlias.end() && nameIt->second != alias))
            {
                ++rejected;
                continue;
            }

            AliasToKoreanPlayerName[alias] = name;
            KoreanPlayerNameToAlias[name] = alias;
            ++loaded;
        }

        KoreanPlayerNameSidecarLoaded = true;
        spdlog::info(
            "Korean player-name sidecar: loaded {} mappings ({} rejected) from '{}'",
            loaded,
            rejected,
            path.string());
        return true;
    }

    static bool SaveKoreanPlayerNameSidecarLocked()
    {
        const std::filesystem::path path = KoreanPlayerNameSidecarPath();
        const std::filesystem::path temp = path.string() + ".tmp";

        std::error_code ec;
        std::filesystem::create_directories(path.parent_path(), ec);
        if (ec)
        {
            spdlog::error(
                "Korean player-name sidecar: failed to create SaveGame directory: {}",
                ec.message());
            return false;
        }

        std::vector<std::pair<std::string, std::string>> rows(
            AliasToKoreanPlayerName.begin(),
            AliasToKoreanPlayerName.end());
        std::sort(rows.begin(), rows.end());

        {
            std::ofstream file(temp, std::ios::binary | std::ios::trunc);
            if (!file)
            {
                spdlog::error(
                    "Korean player-name sidecar: failed to create temporary file '{}'",
                    temp.string());
                return false;
            }

            for (const auto& [alias, name] : rows)
                file << alias << '\t' << name << '\n';

            file.flush();
            if (!file)
            {
                spdlog::error(
                    "Korean player-name sidecar: failed while writing '{}'",
                    temp.string());
                return false;
            }
        }

        if (!MoveFileExW(
                temp.c_str(),
                path.c_str(),
                MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
        {
            const DWORD error = GetLastError();
            std::filesystem::remove(temp, ec);
            spdlog::error(
                "Korean player-name sidecar: atomic replace failed for '{}' (Win32 error {})",
                path.string(),
                error);
            return false;
        }

        return true;
    }

    // This function only creates/persists a compatibility alias. It does not
    // write the game's native 0x7C23E0 name field and therefore does not alter
    // ranking/network/save behavior. A later, separately validated input hook
    // can call it once the Hangul composition path is proven.
    static bool EnsureKoreanPlayerNameAlias(
        const std::string& utf8,
        std::string& alias)
    {
        if (!IsValidKoreanPlayerNameUtf8(utf8))
            return false;

        std::scoped_lock lock(KoreanPlayerNameSidecarMutex);
        if (!LoadKoreanPlayerNameSidecarLocked())
            return false;

        if (const auto existing = KoreanPlayerNameToAlias.find(utf8);
            existing != KoreanPlayerNameToAlias.end())
        {
            alias = existing->second;
            return true;
        }

        for (uint32_t salt = 0; salt < 4096; ++salt)
        {
            const std::string candidate = MakeKoreanPlayerNameAlias(utf8, salt);
            if (candidate == KoreanPlayerNamePreviewAlias)
                continue;

            const auto collision = AliasToKoreanPlayerName.find(candidate);
            if (collision != AliasToKoreanPlayerName.end())
            {
                if (collision->second == utf8)
                {
                    alias = candidate;
                    KoreanPlayerNameToAlias[utf8] = candidate;
                    return true;
                }
                continue;
            }

            AliasToKoreanPlayerName[candidate] = utf8;
            KoreanPlayerNameToAlias[utf8] = candidate;
            if (!SaveKoreanPlayerNameSidecarLocked())
            {
                AliasToKoreanPlayerName.erase(candidate);
                KoreanPlayerNameToAlias.erase(utf8);
                return false;
            }

            alias = candidate;
            return true;
        }

        spdlog::error(
            "Korean player-name sidecar: exhausted deterministic alias collision salts");
        return false;
    }

    static bool LookupKoreanPlayerName(
        const char* nativeAlias,
        std::string& utf8)
    {
        if (!nativeAlias)
            return false;

        size_t length = 0;
        while (length < NativePlayerNamePayloadBytes && nativeAlias[length] != '\0')
            ++length;
        const std::string alias(nativeAlias, length);
        if (!IsValidKoreanPlayerNameAlias(alias))
            return false;

        std::scoped_lock lock(KoreanPlayerNameSidecarMutex);
        if (alias == KoreanPlayerNamePreviewAlias)
        {
            if (KoreanPlayerNamePreviewUtf8.empty())
                return false;
            utf8 = KoreanPlayerNamePreviewUtf8;
            return true;
        }

        if (!LoadKoreanPlayerNameSidecarLocked())
            return false;

        const auto it = AliasToKoreanPlayerName.find(alias);
        if (it == AliasToKoreanPlayerName.end())
            return false;

        utf8 = it->second;
        return true;
    }


    // B208: deterministic Korean-name composition foundation.
    //
    // The stock name-entry selector exposes digits + latin a-z on its base
    // character page. B207 proved that selections 10..35 map exactly to a..z,
    // which lets a future input hook reuse those 26 physical choices as a
    // standard 2-beolsik keyboard without guessing sprite ordering. This
    // composer is intentionally not wired into the game yet: the stock
    // controls, native field, sidecar alias, and rendering paths stay unchanged
    // until the visual Jamo atlas and local-name renderer are validated.
    static constexpr size_t KoreanPlayerNameMaxCodepoints = NativePlayerNamePayloadBytes;

    static constexpr char32_t ComposeHangulCodepoint(int choseong, int jungseong, int jongseong)
    {
        return static_cast<char32_t>(
            0xAC00 + ((choseong * 21 + jungseong) * 28) + jongseong);
    }

    static constexpr char32_t BaseJamoForLatinSelection(uint32_t selection)
    {
        // selection 10..35 == latin a..z on the stock page-1 byte table.
        constexpr char32_t map[26] = {
            U'\u3141', U'\u3160', U'\u314A', U'\u3147', U'\u3137', U'\u3139', U'\u314E',
            U'\u3157', U'\u3151', U'\u3153', U'\u314F', U'\u3163', U'\u3161', U'\u315C',
            U'\u3150', U'\u3154', U'\u3142', U'\u3131', U'\u3134', U'\u3145', U'\u3155',
            U'\u314D', U'\u3148', U'\u314C', U'\u315B', U'\u314B'
        };
        return selection >= 10 && selection <= 35 ? map[selection - 10] : U'\0';
    }

    static constexpr char32_t ShiftedJamoForLatinSelection(uint32_t selection)
    {
        const char32_t base = BaseJamoForLatinSelection(selection);
        switch (selection)
        {
        case 14: return U'\u3138'; // e
        case 24: return U'\u3152'; // o
        case 25: return U'\u3156'; // p
        case 26: return U'\u3143'; // q
        case 27: return U'\u3132'; // r
        case 29: return U'\u3146'; // t
        case 32: return U'\u3149'; // w
        default: return base;
        }
    }

    static_assert(BaseJamoForLatinSelection(10) == U'\u3141'); // A key
    static_assert(BaseJamoForLatinSelection(26) == U'\u3142'); // Q key
    static_assert(BaseJamoForLatinSelection(35) == U'\u314B'); // Z key
    static_assert(ShiftedJamoForLatinSelection(26) == U'\u3143');
    static_assert(ShiftedJamoForLatinSelection(27) == U'\u3132');
    static_assert(ComposeHangulCodepoint(0, 0, 0) == U'\uAC00');
    static_assert(ComposeHangulCodepoint(18, 0, 4) == U'\uD55C');
    static_assert(ComposeHangulCodepoint(0, 18, 8) == U'\uAE00');

    class HangulNameComposer
    {
    public:
        void Reset()
        {
            committed_.clear();
            ClearCurrent();
        }

        bool Empty() const
        {
            return committed_.empty() && choseong_ < 0;
        }

        size_t VisibleCodepoints() const
        {
            return committed_.size() + (choseong_ >= 0 ? 1u : 0u);
        }

        bool PushLatinSelection(uint32_t selection, bool shifted)
        {
            const char32_t jamo = shifted
                ? ShiftedJamoForLatinSelection(selection)
                : BaseJamoForLatinSelection(selection);
            return jamo != U'\0' && PushJamo(jamo);
        }

        bool PushDigitSelection(uint32_t selection)
        {
            constexpr char32_t digits[10] = {
                U'1', U'2', U'3', U'4', U'5',
                U'6', U'7', U'8', U'9', U'0'
            };
            if (selection >= 10)
                return false;
            return PushLiteral(digits[selection]);
        }

        bool PushSpace()
        {
            return PushLiteral(U' ');
        }

        bool Backspace()
        {
            if (jongseong_ != 0)
            {
                if (previousJongseong_ != 0)
                {
                    jongseong_ = previousJongseong_;
                    previousJongseong_ = 0;
                }
                else
                {
                    jongseong_ = 0;
                }
                return true;
            }

            if (jungseong_ >= 0)
            {
                if (previousJungseong_ >= 0)
                {
                    jungseong_ = previousJungseong_;
                    previousJungseong_ = PreviousMedialState(jungseong_);
                }
                else
                {
                    jungseong_ = -1;
                }
                return true;
            }

            if (choseong_ >= 0)
            {
                if (previousChoseong_ >= 0)
                {
                    choseong_ = previousChoseong_;
                    previousChoseong_ = -1;
                }
                else
                {
                    choseong_ = -1;
                }
                return true;
            }

            if (!committed_.empty())
            {
                committed_.pop_back();
                return true;
            }

            return false;
        }

        std::string Utf8() const
        {
            std::string out;
            out.reserve((committed_.size() + 1) * 3);
            for (const char32_t cp : committed_)
                AppendUtf8Codepoint(out, cp);
            if (choseong_ >= 0)
                AppendUtf8Codepoint(out, CurrentCodepoint());
            return out;
        }

        // Seed the editor from an existing stock ASCII name or a previously
        // persisted Korean sidecar name. Existing codepoints stay committed;
        // newly selected Jamo compose after them, and BACKSPACE removes one
        // visible codepoint at a time until fresh composition begins.
        bool LoadUtf8Literal(const std::string& utf8)
        {
            if (!IsValidKoreanPlayerNameUtf8(utf8))
                return false;

            std::u32string decoded;
            decoded.reserve(KoreanPlayerNameMaxCodepoints);

            for (size_t i = 0; i < utf8.size();)
            {
                const uint8_t lead = static_cast<uint8_t>(utf8[i]);
                uint32_t cp = 0;
                size_t continuation = 0;
                if (lead < 0x80)
                {
                    cp = lead;
                }
                else if (lead <= 0xDF)
                {
                    cp = lead & 0x1F;
                    continuation = 1;
                }
                else if (lead <= 0xEF)
                {
                    cp = lead & 0x0F;
                    continuation = 2;
                }
                else
                {
                    cp = lead & 0x07;
                    continuation = 3;
                }

                for (size_t j = 1; j <= continuation; ++j)
                    cp = (cp << 6) | (static_cast<uint8_t>(utf8[i + j]) & 0x3F);

                if (decoded.size() >= KoreanPlayerNameMaxCodepoints)
                    return false;
                decoded.push_back(static_cast<char32_t>(cp));
                i += continuation + 1;
            }

            Reset();
            committed_ = std::move(decoded);
            return true;
        }

        bool PushPrintableAscii(char ch)
        {
            const unsigned char value = static_cast<unsigned char>(ch);
            if (value < 0x20 || value > 0x7E)
                return false;
            return PushLiteral(static_cast<char32_t>(value));
        }

    private:
        std::u32string committed_{};
        int choseong_ = -1;
        int jungseong_ = -1;
        int jongseong_ = 0;
        int previousChoseong_ = -1;
        int previousJungseong_ = -1;
        int previousJongseong_ = 0;

        static int InitialIndex(char32_t jamo)
        {
            switch (jamo)
            {
            case U'\u3131': return 0;  case U'\u3132': return 1;  case U'\u3134': return 2;
            case U'\u3137': return 3;  case U'\u3138': return 4;  case U'\u3139': return 5;
            case U'\u3141': return 6;  case U'\u3142': return 7;  case U'\u3143': return 8;
            case U'\u3145': return 9;  case U'\u3146': return 10; case U'\u3147': return 11;
            case U'\u3148': return 12; case U'\u3149': return 13; case U'\u314A': return 14;
            case U'\u314B': return 15; case U'\u314C': return 16; case U'\u314D': return 17;
            case U'\u314E': return 18; default: return -1;
            }
        }

        static int MedialIndex(char32_t jamo)
        {
            switch (jamo)
            {
            case U'\u314F': return 0;  case U'\u3150': return 1;  case U'\u3151': return 2;
            case U'\u3152': return 3;  case U'\u3153': return 4;  case U'\u3154': return 5;
            case U'\u3155': return 6;  case U'\u3156': return 7;  case U'\u3157': return 8;
            case U'\u3158': return 9;  case U'\u3159': return 10; case U'\u315A': return 11;
            case U'\u315B': return 12; case U'\u315C': return 13; case U'\u315D': return 14;
            case U'\u315E': return 15; case U'\u315F': return 16; case U'\u3160': return 17;
            case U'\u3161': return 18; case U'\u3162': return 19; case U'\u3163': return 20;
            default: return -1;
            }
        }

        static int FinalIndex(char32_t jamo)
        {
            switch (jamo)
            {
            case U'\u3131': return 1;  case U'\u3132': return 2;  case U'\u3133': return 3;
            case U'\u3134': return 4;  case U'\u3135': return 5;  case U'\u3136': return 6;
            case U'\u3137': return 7;  case U'\u3139': return 8;  case U'\u313A': return 9;
            case U'\u313B': return 10; case U'\u313C': return 11; case U'\u313D': return 12;
            case U'\u313E': return 13; case U'\u313F': return 14; case U'\u3140': return 15;
            case U'\u3141': return 16; case U'\u3142': return 17; case U'\u3144': return 18;
            case U'\u3145': return 19; case U'\u3146': return 20; case U'\u3147': return 21;
            case U'\u3148': return 22; case U'\u314A': return 23; case U'\u314B': return 24;
            case U'\u314C': return 25; case U'\u314D': return 26; case U'\u314E': return 27;
            default: return 0;
            }
        }

        static char32_t InitialCompatibilityJamo(int choseong)
        {
            constexpr char32_t map[19] = {
                U'\u3131', U'\u3132', U'\u3134', U'\u3137', U'\u3138', U'\u3139', U'\u3141',
                U'\u3142', U'\u3143', U'\u3145', U'\u3146', U'\u3147', U'\u3148', U'\u3149',
                U'\u314A', U'\u314B', U'\u314C', U'\u314D', U'\u314E'
            };
            return choseong >= 0 && choseong < 19 ? map[choseong] : U'\0';
        }

        static int DoubleInitial(int left, int right)
        {
            if (left == 0 && right == 0) return 1;
            if (left == 3 && right == 3) return 4;
            if (left == 7 && right == 7) return 8;
            if (left == 9 && right == 9) return 10;
            if (left == 12 && right == 12) return 13;
            return -1;
        }

        static int CombineMedial(int left, int right)
        {
            if (left == 8 && right == 0) return 9;   // ㅗ+ㅏ=ㅘ
            if (left == 8 && right == 1) return 10;  // ㅗ+ㅐ=ㅙ
            if (left == 8 && right == 20) return 11; // ㅗ+ㅣ=ㅚ
            if (left == 9 && right == 20) return 10; // ㅘ+ㅣ=ㅙ
            if (left == 13 && right == 4) return 14; // ㅜ+ㅓ=ㅝ
            if (left == 13 && right == 5) return 15; // ㅜ+ㅔ=ㅞ
            if (left == 13 && right == 20) return 16;// ㅜ+ㅣ=ㅟ
            if (left == 14 && right == 20) return 15;// ㅝ+ㅣ=ㅞ
            if (left == 18 && right == 20) return 19;// ㅡ+ㅣ=ㅢ
            return -1;
        }

        static int PreviousMedialState(int medial)
        {
            // Enables stepwise BACKSPACE for chained compound vowels:
            // ㅙ -> ㅘ -> ㅗ, ㅞ -> ㅝ -> ㅜ, etc.
            switch (medial)
            {
            case 9:  return 8;  // ㅘ -> ㅗ
            case 10: return 8;  // direct ㅙ -> ㅗ (when prior history was not ㅘ)
            case 11: return 8;  // ㅚ -> ㅗ
            case 14: return 13; // ㅝ -> ㅜ
            case 15: return 13; // direct ㅞ -> ㅜ (when prior history was not ㅝ)
            case 16: return 13; // ㅟ -> ㅜ
            case 19: return 18; // ㅢ -> ㅡ
            default: return -1;
            }
        }

        static int CombineFinal(int left, int right)
        {
            if (left == 1 && right == 19) return 3;   // ㄱ+ㅅ=ㄳ
            if (left == 4 && right == 22) return 5;   // ㄴ+ㅈ=ㄵ
            if (left == 4 && right == 27) return 6;   // ㄴ+ㅎ=ㄶ
            if (left == 8 && right == 1) return 9;    // ㄹ+ㄱ=ㄺ
            if (left == 8 && right == 16) return 10;  // ㄹ+ㅁ=ㄻ
            if (left == 8 && right == 17) return 11;  // ㄹ+ㅂ=ㄼ
            if (left == 8 && right == 19) return 12;  // ㄹ+ㅅ=ㄽ
            if (left == 8 && right == 25) return 13;  // ㄹ+ㅌ=ㄾ
            if (left == 8 && right == 26) return 14;  // ㄹ+ㅍ=ㄿ
            if (left == 8 && right == 27) return 15;  // ㄹ+ㅎ=ㅀ
            if (left == 17 && right == 19) return 18; // ㅂ+ㅅ=ㅄ
            return -1;
        }

        static bool SplitFinal(int combined, int& first, int& second)
        {
            switch (combined)
            {
            case 3: first = 1; second = 19; return true;
            case 5: first = 4; second = 22; return true;
            case 6: first = 4; second = 27; return true;
            case 9: first = 8; second = 1; return true;
            case 10: first = 8; second = 16; return true;
            case 11: first = 8; second = 17; return true;
            case 12: first = 8; second = 19; return true;
            case 13: first = 8; second = 25; return true;
            case 14: first = 8; second = 26; return true;
            case 15: first = 8; second = 27; return true;
            case 18: first = 17; second = 19; return true;
            default: return false;
            }
        }

        static int FinalToInitial(int jongseong)
        {
            switch (jongseong)
            {
            case 1: return 0;  case 2: return 1;  case 4: return 2;
            case 7: return 3;  case 8: return 5;  case 16: return 6;
            case 17: return 7; case 19: return 9; case 20: return 10;
            case 21: return 11; case 22: return 12; case 23: return 14;
            case 24: return 15; case 25: return 16; case 26: return 17;
            case 27: return 18; default: return -1;
            }
        }

        static void AppendUtf8Codepoint(std::string& out, char32_t cp)
        {
            if (cp <= 0x7F)
            {
                out.push_back(static_cast<char>(cp));
            }
            else if (cp <= 0x7FF)
            {
                out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
                out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
            }
            else if (cp <= 0xFFFF)
            {
                out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
                out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
                out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
            }
            else
            {
                out.push_back(static_cast<char>(0xF0 | (cp >> 18)));
                out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
                out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
                out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
            }
        }

        char32_t CurrentCodepoint() const
        {
            if (choseong_ < 0)
                return U'\0';
            if (jungseong_ < 0)
                return InitialCompatibilityJamo(choseong_);
            return ComposeHangulCodepoint(choseong_, jungseong_, jongseong_);
        }

        bool CanAddVisibleCodepoint() const
        {
            return VisibleCodepoints() < KoreanPlayerNameMaxCodepoints;
        }

        void ClearCurrent()
        {
            choseong_ = -1;
            jungseong_ = -1;
            jongseong_ = 0;
            previousChoseong_ = -1;
            previousJungseong_ = -1;
            previousJongseong_ = 0;
        }

        void StartInitial(int choseong)
        {
            ClearCurrent();
            choseong_ = choseong;
        }

        void StartVowel(int jungseong)
        {
            ClearCurrent();
            choseong_ = 11; // implicit ㅇ
            jungseong_ = jungseong;
        }

        void FlushCurrent()
        {
            if (choseong_ >= 0)
                committed_.push_back(CurrentCodepoint());
            ClearCurrent();
        }

        bool PushLiteral(char32_t cp)
        {
            if (choseong_ >= 0)
            {
                if (!CanAddVisibleCodepoint())
                    return false;
                FlushCurrent();
            }
            else if (committed_.size() >= KoreanPlayerNameMaxCodepoints)
            {
                return false;
            }

            committed_.push_back(cp);
            return true;
        }

        bool PushJamo(char32_t jamo)
        {
            const int consonant = InitialIndex(jamo);
            const int vowel = MedialIndex(jamo);

            if (consonant >= 0)
            {
                const int final = FinalIndex(jamo);
                if (choseong_ < 0)
                {
                    if (committed_.size() >= KoreanPlayerNameMaxCodepoints)
                        return false;
                    StartInitial(consonant);
                    return true;
                }

                if (jungseong_ < 0)
                {
                    const int doubled = DoubleInitial(choseong_, consonant);
                    if (doubled >= 0)
                    {
                        previousChoseong_ = choseong_;
                        choseong_ = doubled;
                        return true;
                    }

                    if (!CanAddVisibleCodepoint())
                        return false;
                    FlushCurrent();
                    StartInitial(consonant);
                    return true;
                }

                if (jongseong_ == 0 && final != 0)
                {
                    jongseong_ = final;
                    previousJongseong_ = 0;
                    return true;
                }

                if (jongseong_ != 0 && final != 0)
                {
                    const int combined = CombineFinal(jongseong_, final);
                    if (combined >= 0)
                    {
                        previousJongseong_ = jongseong_;
                        jongseong_ = combined;
                        return true;
                    }
                }

                if (!CanAddVisibleCodepoint())
                    return false;
                FlushCurrent();
                StartInitial(consonant);
                return true;
            }

            if (vowel >= 0)
            {
                if (choseong_ < 0)
                {
                    if (committed_.size() >= KoreanPlayerNameMaxCodepoints)
                        return false;
                    StartVowel(vowel);
                    return true;
                }

                if (jungseong_ < 0)
                {
                    jungseong_ = vowel;
                    previousJungseong_ = -1;
                    return true;
                }

                if (jongseong_ == 0)
                {
                    const int combined = CombineMedial(jungseong_, vowel);
                    if (combined >= 0)
                    {
                        previousJungseong_ = jungseong_;
                        jungseong_ = combined;
                        return true;
                    }

                    if (!CanAddVisibleCodepoint())
                        return false;
                    FlushCurrent();
                    StartVowel(vowel);
                    return true;
                }

                if (!CanAddVisibleCodepoint())
                    return false;

                int firstFinal = 0;
                int secondFinal = 0;
                const int priorFinal = jongseong_;
                if (SplitFinal(priorFinal, firstFinal, secondFinal))
                {
                    jongseong_ = firstFinal;
                    previousJongseong_ = 0;
                    const int nextInitial = FinalToInitial(secondFinal);
                    FlushCurrent();
                    if (nextInitial < 0)
                        return false;
                    StartInitial(nextInitial);
                    jungseong_ = vowel;
                    return true;
                }

                const int nextInitial = FinalToInitial(priorFinal);
                if (nextInitial < 0)
                    return false;
                jongseong_ = 0;
                previousJongseong_ = 0;
                FlushCurrent();
                StartInitial(nextInitial);
                jungseong_ = vowel;
                return true;
            }

            return false;
        }
    };

    // A143: connect the B208 composer to the exact B207 name-entry dispatch
    // boundary. The hook runs after the stock code loads the current selection
    // into EAX and before it decides between character/control paths.
    static constexpr uintptr_t NameEntryDispatchOffset = 0x692B6;
    static constexpr size_t NameEntryBufferOffset = 0x5F4;
    static constexpr size_t NameEntryPageOffset = 0xEC;
    static constexpr size_t NameEntryCurrentLengthOffset = 0x6F6;
    static constexpr uint32_t NameEntryBackspaceSelection = 0x26;
    static constexpr uint32_t NameEntryEndSelection = 0x2B;
    static constexpr uint32_t NameEntrySuppressedSelection = 0x2C;
    static constexpr uintptr_t NameEntryByteTableOffset = 0x24C81B;

    inline static HangulNameComposer KoreanNameEntryComposer{};
    inline static uintptr_t KoreanNameEntryActiveObject = 0;
    inline static bool KoreanNameEntryUnsupportedSymbolLogged = false;

    static char* KoreanNameEntryBuffer(uintptr_t object)
    {
        return reinterpret_cast<char*>(object + NameEntryBufferOffset);
    }

    static int16_t* KoreanNameEntryCurrentLength(uintptr_t object)
    {
        return reinterpret_cast<int16_t*>(object + NameEntryCurrentLengthOffset);
    }

    static uint32_t KoreanNameEntryPage(uintptr_t object)
    {
        return *reinterpret_cast<uint32_t*>(object + NameEntryPageOffset);
    }

    static void SetKoreanPlayerNamePreview(const std::string& utf8)
    {
        std::scoped_lock lock(KoreanPlayerNameSidecarMutex);
        KoreanPlayerNamePreviewUtf8 = utf8;
    }

    static void ClearKoreanPlayerNamePreview()
    {
        std::scoped_lock lock(KoreanPlayerNameSidecarMutex);
        KoreanPlayerNamePreviewUtf8.clear();
    }

    static void BeginKoreanNameEntry(uintptr_t object)
    {
        if (KoreanNameEntryActiveObject == object)
        {
            const char* currentBuffer = KoreanNameEntryBuffer(object);
            const std::string currentUtf8 = KoreanNameEntryComposer.Utf8();
            const bool bufferMatchesComposer =
                (currentUtf8.empty() && currentBuffer[0] == '\0') ||
                (!currentUtf8.empty() &&
                 std::strncmp(
                     currentBuffer,
                     KoreanPlayerNamePreviewAlias,
                     sizeof(KoreanPlayerNamePreviewAlias) - 1) == 0 &&
                 currentBuffer[sizeof(KoreanPlayerNamePreviewAlias) - 1] == '\0');
            if (bufferMatchesComposer)
                return;

            // The stock parent can recycle this object after a cancel/re-entry.
            // If its buffer no longer carries our preview token, discard stale
            // transient composition and seed from the newly loaded native name.
            KoreanNameEntryActiveObject = 0;
        }

        KoreanNameEntryComposer.Reset();
        ClearKoreanPlayerNamePreview();

        const char* buffer = KoreanNameEntryBuffer(object);
        size_t length = 0;
        while (length < NativePlayerNamePayloadBytes && buffer[length] != '\0')
            ++length;

        if (length != 0)
        {
            const std::string native(buffer, length);
            std::string resolved;
            if (LookupKoreanPlayerName(native.c_str(), resolved))
            {
                KoreanNameEntryComposer.LoadUtf8Literal(resolved);
            }
            else if (!IsValidKoreanPlayerNameAlias(native) &&
                     IsValidKoreanPlayerNameUtf8(native))
            {
                KoreanNameEntryComposer.LoadUtf8Literal(native);
            }
        }

        KoreanNameEntryActiveObject = object;
    }

    static void SyncKoreanNameEntryPreview(uintptr_t object)
    {
        const std::string utf8 = KoreanNameEntryComposer.Utf8();
        char* buffer = KoreanNameEntryBuffer(object);

        if (utf8.empty())
        {
            std::memset(buffer, 0, NativePlayerNameFieldBytes);
            *KoreanNameEntryCurrentLength(object) = 0;
            ClearKoreanPlayerNamePreview();
            return;
        }

        constexpr size_t previewAliasLength = sizeof(KoreanPlayerNamePreviewAlias) - 1;
        std::memset(buffer, 0, NativePlayerNameFieldBytes);
        std::memcpy(buffer, KoreanPlayerNamePreviewAlias, previewAliasLength);
        *KoreanNameEntryCurrentLength(object) =
            static_cast<int16_t>(KoreanNameEntryComposer.VisibleCodepoints());
        SetKoreanPlayerNamePreview(utf8);
    }

    static bool PushKoreanNameEntrySelection(
        uintptr_t object,
        uint32_t selection)
    {
        const uint32_t page = KoreanNameEntryPage(object);

        if (selection <= 9 &&
            (page == 1 || page == 3 || page == 4 || page == 5))
        {
            return KoreanNameEntryComposer.PushDigitSelection(selection);
        }

        if (selection >= 10 && selection <= 35)
        {
            if (page == 1 || page == 3 || page == 4)
            {
                const bool shifted = page == 3 || page == 4;
                const bool pushed =
                    KoreanNameEntryComposer.PushLatinSelection(selection, shifted);
                if (pushed && page == 3)
                    *reinterpret_cast<uint32_t*>(object + NameEntryPageOffset) = 1;
                return pushed;
            }
        }

        // Selection 0x25 is an intentional duplicate of table slot 0x24.
        const uint32_t tableSelection = selection == 0x25 ? 0x24 : selection;
        if (tableSelection <= 0x24 && page >= 1 && page <= 5)
        {
            const uint8_t* table = Module::exe_ptr<uint8_t>(
                NameEntryByteTableOffset + page * 0x25 + tableSelection);
            if (table && *table >= 0x20 && *table <= 0x7E)
                return KoreanNameEntryComposer.PushPrintableAscii(
                    static_cast<char>(*table));
        }

        if (!KoreanNameEntryUnsupportedSymbolLogged)
        {
            KoreanNameEntryUnsupportedSymbolLogged = true;
            spdlog::warn(
                "Korean name entry: unsupported legacy symbol selection {} on page {}; "
                "selection ignored to protect UTF-8/alias integrity",
                selection,
                page);
        }
        return false;
    }

    static void InterceptKoreanNameEntry(SafetyHookContext& ctx)
    {
        if (!Settings::KoreanTextOverlayTest ||
            !Settings::OverlayEnabled ||
            !TranslationsLoaded)
        {
            return;
        }

        const uintptr_t object = static_cast<uintptr_t>(ctx.esi);
        if (!object)
            return;

        const uint32_t selection = static_cast<uint32_t>(ctx.eax);
        if (selection < NameEntryBackspaceSelection)
        {
            BeginKoreanNameEntry(object);
            if (PushKoreanNameEntrySelection(object, selection))
            {
                SyncKoreanNameEntryPreview(object);
                ctx.eax = NameEntrySuppressedSelection;
            }
            else if (KoreanNameEntryActiveObject == object)
            {
                // Once Korean editing is active, never let an unsupported
                // legacy/high-byte glyph contaminate the transient alias.
                ctx.eax = NameEntrySuppressedSelection;
            }
            return;
        }

        if (selection == NameEntryBackspaceSelection)
        {
            BeginKoreanNameEntry(object);
            if (KoreanNameEntryComposer.Backspace())
                SyncKoreanNameEntryPreview(object);
            else
                SyncKoreanNameEntryPreview(object);
            ctx.eax = NameEntrySuppressedSelection;
            return;
        }

        // Keep page/control behavior 0x27..0x2A byte-for-byte stock.
        if (selection != NameEntryEndSelection ||
            KoreanNameEntryActiveObject != object)
        {
            return;
        }

        const std::string utf8 = KoreanNameEntryComposer.Utf8();
        if (utf8.empty())
        {
            // Let stock END enforce its minimum-length rule on an empty buffer.
            ClearKoreanPlayerNamePreview();
            return;
        }

        std::string persistentAlias;
        if (!EnsureKoreanPlayerNameAlias(utf8, persistentAlias))
        {
            spdlog::error(
                "Korean name entry: failed to persist compatibility alias; "
                "blocking END to avoid losing the composed UTF-8 name");
            ctx.eax = NameEntrySuppressedSelection;
            return;
        }

        char* buffer = KoreanNameEntryBuffer(object);
        std::memset(buffer, 0, NativePlayerNameFieldBytes);
        std::memcpy(
            buffer,
            persistentAlias.data(),
            (std::min)(persistentAlias.size(), NativePlayerNamePayloadBytes));
        *KoreanNameEntryCurrentLength(object) =
            static_cast<int16_t>(persistentAlias.size());

        ClearKoreanPlayerNamePreview();
        KoreanNameEntryActiveObject = 0;
        KoreanNameEntryComposer.Reset();

        // EAX remains 0x2B. Stock minimum-length checking, result state,
        // finalizer, parent 16-byte copy to 0x7C23E0, and all legacy
        // save/ranking/network/replay consumers continue unchanged.
    }

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

        // Pointer identity is authoritative. A string-content fallback is only
        // safe when duplicate stock strings share the same Korean translation.
        const std::string key(text);
        const auto [it, inserted] = TextToId.emplace(key, id);
        if (!inserted && it->second != id)
        {
            const uint32_t prior = it->second;
            if (prior >= TextEntryCount || Translations[prior] != Translations[id])
                it->second = static_cast<uint32_t>(TextEntryCount);
        }
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

    struct PrintfFormatInfo
    {
        std::string safeFormat;
        std::vector<std::string> signature;
        bool valid = true;
    };

    static bool IsPrintfConversion(char ch)
    {
        switch (ch)
        {
        case 'd': case 'i': case 'u': case 'o': case 'x': case 'X':
        case 'f': case 'F': case 'e': case 'E': case 'g': case 'G':
        case 'a': case 'A': case 'c': case 'C': case 's': case 'S':
        case 'p':
            return true;
        default:
            return false;
        }
    }

    static PrintfFormatInfo AnalyzePrintfFormat(const std::string& format)
    {
        PrintfFormatInfo info;
        info.safeFormat.reserve(format.size() + 8);

        for (size_t i = 0; i < format.size();)
        {
            if (format[i] != '%')
            {
                info.safeFormat.push_back(format[i++]);
                continue;
            }

            if (i + 1 < format.size() && format[i + 1] == '%')
            {
                info.safeFormat.append("%%");
                i += 2;
                continue;
            }

            size_t p = i + 1;
            while (p < format.size() && std::strchr("-+ #0'", format[p]))
                ++p;

            if (p < format.size() && format[p] == '*')
            {
                info.signature.emplace_back("*width");
                ++p;
            }
            else
            {
                while (p < format.size() && format[p] >= '0' && format[p] <= '9')
                    ++p;
            }

            if (p < format.size() && format[p] == '.')
            {
                ++p;
                if (p < format.size() && format[p] == '*')
                {
                    info.signature.emplace_back("*precision");
                    ++p;
                }
                else
                {
                    while (p < format.size() && format[p] >= '0' && format[p] <= '9')
                        ++p;
                }
            }

            std::string length;
            if (p + 2 < format.size() && format.compare(p, 3, "I64") == 0)
            {
                length = "I64";
                p += 3;
            }
            else if (p + 2 < format.size() && format.compare(p, 3, "I32") == 0)
            {
                length = "I32";
                p += 3;
            }
            else if (p < format.size() && std::strchr("hljztL", format[p]))
            {
                length.push_back(format[p++]);
                if (p < format.size() &&
                    (length[0] == 'h' || length[0] == 'l') &&
                    format[p] == length[0])
                {
                    length.push_back(format[p++]);
                }
            }

            if (p < format.size() && format[p] == 'n')
            {
                info.valid = false; // Never permit printf's memory-write conversion.
                return info;
            }

            if (p < format.size() && IsPrintfConversion(format[p]))
            {
                info.safeFormat.append(format, i, (p - i) + 1);
                info.signature.emplace_back(length + format[p]);
                i = p + 1;
                continue;
            }

            // A bare/unknown percent is visible text (for example 100%).
            // Escape it before passing the translation to printf.
            info.safeFormat.append("%%");
            ++i;
        }

        return info;
    }

    static std::string CollapseEscapedPercents(const std::string& format)
    {
        std::string out;
        out.reserve(format.size());
        for (size_t i = 0; i < format.size(); ++i)
        {
            if (format[i] == '%' && i + 1 < format.size() && format[i + 1] == '%')
            {
                out.push_back('%');
                ++i;
            }
            else
            {
                out.push_back(format[i]);
            }
        }
        return out;
    }

    static void LogFormatMismatchOnce(
        uint32_t id,
        const PrintfFormatInfo& original,
        const PrintfFormatInfo& translated)
    {
        std::scoped_lock lock(StateMutex);
        if (id >= TextEntryCount || FormatMismatchLogged.test(id))
            return;

        FormatMismatchLogged.set(id);
        spdlog::warn(
            "KoreanTextOverlayTest: text_id={} printf signature mismatch/unsafe "
            "(stock_args={}, korean_args={}, stock_valid={}, korean_valid={}); "
            "keeping stock English text for this draw",
            id,
            original.signature.size(),
            translated.signature.size(),
            original.valid,
            translated.valid);
    }

    static bool FormatTranslation(
        uint32_t id,
        const char* originalFormat,
        uintptr_t firstArgAddress,
        std::string& formatted)
    {
        if (!originalFormat || id >= TextEntryCount)
            return false;

        const PrintfFormatInfo original = AnalyzePrintfFormat(originalFormat);
        const PrintfFormatInfo translated = AnalyzePrintfFormat(Translations[id]);
        if (!original.valid || !translated.valid || original.signature != translated.signature)
        {
            LogFormatMismatchOnce(id, original, translated);
            return false;
        }

        if (translated.signature.empty())
        {
            formatted = CollapseEscapedPercents(Translations[id]);
            return true;
        }

#if defined(_M_IX86)
        char buffer[MaxFormattedBytes]{};
        va_list args = reinterpret_cast<va_list>(firstArgAddress);
        const int result = _vsnprintf_s(
            buffer,
            sizeof(buffer),
            _TRUNCATE,
            translated.safeFormat.c_str(),
            args);
        if (result >= 0 || buffer[0] != '\0')
        {
            formatted.assign(buffer);
            return true;
        }
#endif
        return false;
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

    static void Queue(uint32_t id, std::string formatted)
    {
        if (formatted.empty())
            return;

        DrawCommand cmd;
        cmd.textId = id;
        cmd.text = std::move(formatted);
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

        // A142: local player-name sidecar render substitution.
        // The stock local text object prints its buffer through Sumo_Printf("%s", text)
        // at VA 0x48F455. Restrict the new path to that exact return site and to a
        // valid A141 sidecar alias. This deliberately leaves the native 16-byte
        // field, ranking/network/replay consumers, and every non-sidecar string intact.
        const uintptr_t returnAddress = *reinterpret_cast<const uintptr_t*>(stack);
        const uintptr_t localTextObjectReturn =
            reinterpret_cast<uintptr_t>(Module::exe_ptr(LocalTextObjectPrintfReturnOffset));
        if (returnAddress == localTextObjectReturn && std::strcmp(*formatSlot, "%s") == 0)
        {
            const char* const* stringArgSlot =
                reinterpret_cast<const char* const*>(stack + 8);
            std::string koreanPlayerName;
            if (stringArgSlot && *stringArgSlot &&
                LookupKoreanPlayerName(*stringArgSlot, koreanPlayerName))
            {
                Queue(static_cast<uint32_t>(TextEntryCount), koreanPlayerName);

                thread_local std::string hiddenPlayerNameLayout;
                hiddenPlayerNameLayout = BuildHiddenLayout(*stringArgSlot);
                *formatSlot = hiddenPlayerNameLayout.c_str();
                return;
            }
        }

        uint32_t id = 0;
        if (!ResolveTextId(*formatSlot, id))
            return;

        std::string formatted;
        if (!FormatTranslation(id, *formatSlot, stack + 8, formatted))
            return;

        Queue(id, formatted);

        thread_local std::string hiddenLayout;
        hiddenLayout = BuildHiddenLayout(formatted);

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
        return IM_COL32(r, g, b, a);
    }

    static ImU32 CompactOutlineColor(uint32_t argb)
    {
        const uint8_t a = static_cast<uint8_t>((argb >> 24) & 0xFF);
        const uint8_t r = static_cast<uint8_t>((argb >> 16) & 0xFF);
        const uint8_t g = static_cast<uint8_t>((argb >> 8) & 0xFF);
        const uint8_t b = static_cast<uint8_t>(argb & 0xFF);

        // Keep the stock alpha while deriving a dark keyline from the stock
        // text colour. This follows the game's compact HUD/speech-bubble
        // treatment without inventing a new palette.
        return IM_COL32(
            static_cast<uint8_t>(r / 5),
            static_cast<uint8_t>(g / 5),
            static_cast<uint8_t>(b / 5),
            a);
    }

    static bool NeedsCompactReadabilityStroke(const DrawCommand& cmd)
    {
        const float cellHeight =
            static_cast<float>(cmd.cellHeight == 0 ? 16 : std::abs(cmd.cellHeight));
        const float logicalFontHeight =
            cellHeight * (std::max)(0.05f, std::fabs(cmd.scaleY));

        // User in-game regressions IGR-006/007 show the compact HUD/bubble path
        // losing source weight, so those small cells still get a keyline.
        // The 2026-10-07 in-game confirmation-dialog review showed text ID 935
        // ("확실합니까?") becoming visibly too heavy because the same HUD
        // reinforcement was applied to menu/modal copy. Keep that dialog on the
        // clean Semilight face; do not solve menu readability by thickening it.
        if (cmd.textId == 935)
            return false;

        return cmd.textId < TextEntryCount && logicalFontHeight <= 24.0f;
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

        // A203: opt-in probe has no effect on command order or text pixels.
        struct StageRankBox
        {
            uint32_t id;
            bool stage;
            ImVec4 rect;
        };
        std::vector<StageRankBox> stageRankBoxes;
        if (Settings::KoreanHudLayoutTrace)
            stageRankBoxes.reserve(16);

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

            const bool stageText = cmd.text.find("스테이지") != std::string::npos;
            const bool rankText = cmd.text.find("랭크") != std::string::npos ||
                                  cmd.text.find("순위") != std::string::npos;
            if (Settings::KoreanHudLayoutTrace && cmd.textId < TextEntryCount &&
                (stageText || rankText))
            {
                stageRankBoxes.push_back({cmd.textId, stageText,
                                          ImVec4(x, y, x + size.x, y + size.y)});
            }

            // IGR-042 has unresolved source attribution: actual HUD text may
            // originate here, in a baked DDS, or both. Trace only matching
            // translated draw commands when explicitly opted in, without
            // changing their rendering order, glyph pixels or stock layout.
            if (Settings::KoreanHudLayoutTrace &&
                cmd.textId < TextEntryCount &&
                (cmd.text.find("하트") != std::string::npos ||
                 cmd.text.find("시간") != std::string::npos ||
                 stageText || rankText))
            {
                std::ostringstream key;
                key << cmd.textId << ':' << cmd.x << ':' << cmd.y << ':'
                    << cmd.cellHeight << ':' << cmd.scaleY << ':'
                    << cmd.flags << ':' << cmd.color;
                if (HudLayoutTraceSeen.size() < MaxHudLayoutTraceKeys &&
                    HudLayoutTraceSeen.insert(key.str()).second)
                {
                    spdlog::info(
                        "KoreanHudLayoutTrace: id={} source_xy=({}, {}) source_cell_h={} "
                        "scale_y={} flags=0x{:X} color_argb=0x{:08X} "
                        "screen_bbox=({:.2f},{:.2f},{:.2f},{:.2f}) "
                        "font_px={:.2f} compact_keyline={} translated='{}'",
                        cmd.textId, cmd.x, cmd.y, cmd.cellHeight, cmd.scaleY,
                        cmd.flags, cmd.color, x, y, size.x, size.y, fontSize,
                        NeedsCompactReadabilityStroke(cmd), cmd.text);
                }
            }

            if (NeedsCompactReadabilityStroke(cmd))
            {
                // Reinforce compact Korean glyphs inside their existing
                // calculated text footprint. The fine clip rectangle prevents
                // the readability stroke from expanding the prior layout box,
                // which is required for dense HUD and speech-bubble regions.
                const float stroke = std::clamp(fontSize * 0.055f, 1.0f, 2.0f);
                const ImVec4 clip(x, y, x + size.x, y + size.y);
                const ImU32 outline = CompactOutlineColor(cmd.color);
                const ImVec2 offsets[] = {
                    ImVec2(-stroke, 0.0f),
                    ImVec2(stroke, 0.0f),
                    ImVec2(0.0f, -stroke),
                    ImVec2(0.0f, stroke),
                    ImVec2(-stroke, -stroke),
                    ImVec2(stroke, -stroke),
                    ImVec2(-stroke, stroke),
                    ImVec2(stroke, stroke)
                };

                for (const ImVec2& offset : offsets)
                {
                    drawList->AddText(
                        font,
                        fontSize,
                        ImVec2(x + offset.x, y + offset.y),
                        outline,
                        cmd.text.c_str(),
                        nullptr,
                        0.0f,
                        &clip);
                }
            }

            drawList->AddText(
                font,
                fontSize,
                ImVec2(x, y),
                ConvertColor(cmd.color),
                cmd.text.c_str());
        }

        // A203 IGR-043: a strict runtime-runtime overlap is new evidence,
        // not proof of a q49 DDS defect or a permission to change its pixels.
        if (Settings::KoreanHudLayoutTrace)
        {
            for (size_t i = 0; i < stageRankBoxes.size(); ++i)
            {
                for (size_t j = i + 1; j < stageRankBoxes.size(); ++j)
                {
                    const auto& a = stageRankBoxes[i];
                    const auto& b = stageRankBoxes[j];
                    if (a.stage == b.stage)
                        continue;
                    const float left = (std::max)(a.rect.x, b.rect.x);
                    const float top = (std::max)(a.rect.y, b.rect.y);
                    const float right = (std::min)(a.rect.z, b.rect.z);
                    const float bottom = (std::min)(a.rect.w, b.rect.w);
                    if (left >= right || top >= bottom)
                        continue;
                    std::ostringstream key;
                    key << a.id << ':' << b.id << ':'
                        << static_cast<int>(left) << ':' << static_cast<int>(top);
                    if (StageRankOverlapSeen.size() < MaxStageRankOverlapKeys &&
                        StageRankOverlapSeen.insert(key.str()).second)
                    {
                        spdlog::warn(
                            "KoreanStageRankOverlapTrace: IGR-043 id_pair=({}, {}) "
                            "intersection=({:.2f},{:.2f},{:.2f},{:.2f}) "
                            "RUNTIME_TEXT_ONLY DDS_AND_OTHER_LAYERS_UNVERIFIED",
                            a.id, b.id, left, top, right, bottom);
                    }
                }
            }
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


class KoreanNameEntryHook : public Hook
{
    static constexpr uintptr_t DispatchOffset = 0x692B6;
    static constexpr uint8_t ExpectedDispatchBytes[] = {
        0x83, 0xF8, 0x26, 0x7D, 0x68,
        0x0F, 0xBF, 0x8E, 0xFA, 0x06, 0x00, 0x00
    };

    inline static SafetyHookMid DispatchHook{};

    static void DispatchDest(SafetyHookContext& ctx)
    {
        KoreanRuntime::InterceptKoreanNameEntry(ctx);
    }

public:
    std::string_view description() override
    {
        return "KoreanNameEntry";
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

        const uint8_t* dispatch = Module::exe_ptr(DispatchOffset);
        if (!dispatch ||
            std::memcmp(
                dispatch,
                ExpectedDispatchBytes,
                sizeof(ExpectedDispatchBytes)) != 0)
        {
            spdlog::error(
                "Korean name entry: dispatch signature mismatch at EXE+0x{:X}; "
                "leaving stock input untouched",
                DispatchOffset);
            return false;
        }

        return true;
    }

    bool apply() override
    {
        DispatchHook = safetyhook::create_mid(
            Module::exe_ptr(DispatchOffset),
            DispatchDest);
        spdlog::info(
            "Korean name entry: installed B207 character/END bridge at EXE+0x{:X}",
            DispatchOffset);
        return !!DispatchHook;
    }

    static KoreanNameEntryHook instance;
};

KoreanNameEntryHook KoreanNameEntryHook::instance;


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