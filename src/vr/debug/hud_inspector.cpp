#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <intrin.h>

#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <mutex>
#include <string_view>
#include <unordered_map>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"

namespace Settings
{
    Setting<bool> VRHudInspector{
        "VR", "HudInspector", false,
        "Passive HUD/sprite reverse-engineering trace. Records unique sprite call sites, IDs and coordinates with EXE RVAs so static EXE analysis can map them back to game functions."
    };
}

namespace OutRunVRHudInspector
{
    namespace
    {
        enum class EventKind : std::uint32_t
        {
            PutSprite = 1,
            SpriteAnim = 2,
            ClipSprite = 3,
            PutSprite2 = 4,
            SprPrintf = 5,
            SumoPrintf = 6
        };

        SafetyHookInline SpriteAnimHook{};
        SafetyHookInline ClipSpriteHook{};
        SafetyHookMid FontHook{};
        SafetyHookMid PriorityHook{};
        SafetyHookMid ColorHook{};
        SafetyHookMid ScaleHook{};
        SafetyHookMid LocateHook{};
        SafetyHookMid SprPrintfHook{};
        SafetyHookMid SumoPrintfHook{};

        struct FontState
        {
            std::uint32_t font = 0;
            std::uint32_t priority = 0;
            std::uint32_t color = 0;
            float scaleX = 0.0f;
            float scaleY = 0.0f;
            std::int32_t x = 0;
            std::int32_t y = 0;
        };

        thread_local FontState CurrentFont{};

        std::mutex TraceMutex;
        std::ofstream TraceFile;
        std::unordered_map<std::uint64_t, std::uint32_t> Seen;
        std::uint64_t TraceLines = 0;
        ULONGLONG StartMs = 0;

        std::uint32_t ExeSizeOfImage() noexcept
        {
            if (!Module::ExeHandle)
                return 0;
            const auto* base = reinterpret_cast<const std::uint8_t*>(Module::ExeHandle);
            const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base);
            if (dos->e_magic != IMAGE_DOS_SIGNATURE)
                return 0;
            const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(base + dos->e_lfanew);
            if (nt->Signature != IMAGE_NT_SIGNATURE)
                return 0;
            return nt->OptionalHeader.SizeOfImage;
        }

        std::uint32_t ToExeRva(const void* address) noexcept
        {
            const auto base = reinterpret_cast<std::uintptr_t>(Module::ExeHandle);
            const auto value = reinterpret_cast<std::uintptr_t>(address);
            const auto size = static_cast<std::uintptr_t>(ExeSizeOfImage());
            if (!base || !value || value < base || !size || value >= base + size)
                return 0;
            return static_cast<std::uint32_t>(value - base);
        }

        const char* KnownCaller(std::uint32_t callRva) noexcept
        {
            switch (callRva)
            {
                case 0x0BB0FB:
                case 0x0BB133:
                case 0x0BB16C:
                case 0x0BB1A5:
                case 0x0BB21F:
                case 0x0BB241:
                case 0x0BB271:
                case 0x0BB2BC:
                case 0x0BB2D0:
                    return "RankMarker/sub_4BAD20";
                default:
                    break;
            }

            if (callRva >= 0x0BAD20 && callRva < 0x0BB320)
                return "RankMarker/sub_4BAD20";
            if (callRva >= 0x0B9E00 && callRva < 0x0BA100)
                return "DispRank";
            if (callRva >= 0x0BE300 && callRva < 0x0BEA80)
                return "DispTimeAttack2D";
            if (callRva >= 0x0BD900 && callRva < 0x0BE100)
                return "GhostGap";
            if (callRva >= 0x0BEA80 && callRva < 0x0BEE80)
                return "NaviPub_Disp";
            return "";
        }

        std::uint64_t MakeKey(EventKind kind, std::uint32_t callRva,
            std::uint32_t arg0, std::uint32_t arg1) noexcept
        {
            std::uint64_t h = 1469598103934665603ull;
            auto mix = [&h](std::uint32_t v) {
                h ^= v;
                h *= 1099511628211ull;
            };
            mix(static_cast<std::uint32_t>(kind));
            mix(callRva);
            mix(arg0);
            mix(arg1);
            return h;
        }

        bool ShouldWrite(std::uint64_t key, std::uint32_t& count)
        {
            count = ++Seen[key];
            return count == 1 || (count <= 1024 && (count & (count - 1)) == 0);
        }

        int CurrentMode() noexcept
        {
            return Game::current_mode ? static_cast<int>(*Game::current_mode) : -1;
        }

        int CurrentStage() noexcept
        {
            return Game::stg_stage_num ? static_cast<int>(*Game::stg_stage_num) : -1;
        }

        template <typename T>
        T ReadStackValue(std::uintptr_t address) noexcept
        {
            T value{};
            std::memcpy(&value, reinterpret_cast<const void*>(address), sizeof(value));
            return value;
        }

        bool CopyTextPreview(const char* source, char* output,
            std::size_t capacity) noexcept
        {
            if (!source || !output || capacity == 0)
                return false;
            output[0] = '\0';
#if defined(_MSC_VER)
            __try
            {
                std::size_t i = 0;
                for (; i + 1 < capacity; ++i)
                {
                    const char ch = source[i];
                    if (!ch)
                        break;
                    output[i] = (ch == '\r' || ch == '\n') ? ' ' : ch;
                }
                output[i] = '\0';
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                output[0] = '\0';
                return false;
            }
#else
            std::size_t i = 0;
            for (; i + 1 < capacity && source[i]; ++i)
                output[i] = (source[i] == '\r' || source[i] == '\n') ? ' ' : source[i];
            output[i] = '\0';
            return true;
#endif
        }

        std::uint32_t HashText(const char* text) noexcept
        {
            std::uint32_t hash = 2166136261u;
            if (!text)
                return 0;
            for (const unsigned char* p =
                    reinterpret_cast<const unsigned char*>(text); *p; ++p)
            {
                hash ^= *p;
                hash *= 16777619u;
            }
            return hash;
        }

        void WriteCsvText(const char* text)
        {
            TraceFile << '"';
            if (text)
            {
                for (const char* p = text; *p; ++p)
                {
                    if (*p == '"')
                        TraceFile << '"' << '"';
                    else
                        TraceFile << *p;
                }
            }
            TraceFile << '"';
        }

        void WriteEvent(EventKind kind, const char* eventName,
            const void* returnAddress,
            std::uint32_t arg0, std::uint32_t arg1,
            double arg2 = 0.0, double arg3 = 0.0,
            double arg4 = 0.0, double arg5 = 0.0,
            double arg6 = 0.0, double arg7 = 0.0,
            std::uint32_t textHash = 0, const char* text = nullptr)
        {
            if (!TraceFile)
                return;

            const std::uint32_t returnRva = ToExeRva(returnAddress);
            const std::uint32_t callRva =
                returnRva >= 5 ? returnRva - 5 : returnRva;
            const std::uint64_t key = MakeKey(kind, callRva, arg0, arg1);

            std::lock_guard lock(TraceMutex);
            std::uint32_t count = 0;
            if (!ShouldWrite(key, count))
                return;

            TraceFile
                << (GetTickCount64() - StartMs) << ','
                << eventName << ','
                << "0x" << std::hex << std::setw(8) << std::setfill('0') << returnRva << ','
                << "0x" << std::setw(8) << callRva << std::dec << ','
                << KnownCaller(callRva) << ','
                << CurrentMode() << ','
                << CurrentStage() << ','
                << arg0 << ','
                << arg1 << ','
                << arg2 << ','
                << arg3 << ','
                << arg4 << ','
                << arg5 << ','
                << arg6 << ','
                << arg7 << ','
                << textHash << ',';
            WriteCsvText(text);
            TraceFile << ',' << count << '\n';

            if ((++TraceLines & 63ull) == 0)
                TraceFile.flush();
        }

        int __cdecl SpriteAnimDest(std::uint32_t spriteId, float x, float y,
            int a4, int a5, float alpha)
        {
            WriteEvent(EventKind::SpriteAnim, "sprani_play_ae_auth_alpha",
                _ReturnAddress(), spriteId,
                static_cast<std::uint32_t>(a4),
                x, y, static_cast<double>(a5), alpha);
            return SpriteAnimHook.unsafe_ccall<int>(
                spriteId, x, y, a4, a5, alpha);
        }

        int __cdecl ClipSpriteDest(int xstnum, int x, int y,
            std::uint32_t flags, float priority, std::uint32_t color)
        {
            WriteEvent(EventKind::ClipSprite, "put_clip_sprite",
                _ReturnAddress(),
                static_cast<std::uint32_t>(xstnum), flags,
                static_cast<double>(x), static_cast<double>(y),
                priority, static_cast<double>(color));
            return ClipSpriteHook.unsafe_ccall<int>(
                xstnum, x, y, flags, priority, color);
        }

        void FontDest(safetyhook::Context& ctx)
        {
            CurrentFont.font = ReadStackValue<std::uint32_t>(ctx.esp + 4);
        }

        void PriorityDest(safetyhook::Context& ctx)
        {
            CurrentFont.priority = ReadStackValue<std::uint32_t>(ctx.esp + 4);
        }

        void ColorDest(safetyhook::Context& ctx)
        {
            CurrentFont.color = ReadStackValue<std::uint32_t>(ctx.esp + 4);
        }

        void ScaleDest(safetyhook::Context& ctx)
        {
            CurrentFont.scaleX = ReadStackValue<float>(ctx.esp + 4);
            CurrentFont.scaleY = ReadStackValue<float>(ctx.esp + 8);
        }

        void LocateDest(safetyhook::Context& ctx)
        {
            CurrentFont.x = ReadStackValue<std::int32_t>(ctx.esp + 4);
            CurrentFont.y = ReadStackValue<std::int32_t>(ctx.esp + 8);
        }

        void TracePrintfEntry(EventKind kind, const char* eventName,
            safetyhook::Context& ctx)
        {
            const auto returnAddress = reinterpret_cast<const void*>(
                ReadStackValue<std::uintptr_t>(ctx.esp));
            const char* format = ReadStackValue<const char*>(ctx.esp + 4);
            char preview[192]{};
            CopyTextPreview(format, preview, sizeof(preview));
            const std::uint32_t textHash = HashText(preview);

            WriteEvent(kind, eventName, returnAddress,
                textHash, CurrentFont.font,
                static_cast<double>(CurrentFont.priority),
                static_cast<double>(CurrentFont.x),
                static_cast<double>(CurrentFont.y),
                CurrentFont.scaleX, CurrentFont.scaleY,
                static_cast<double>(CurrentFont.color),
                textHash, preview);
        }

        void SprPrintfDest(safetyhook::Context& ctx)
        {
            TracePrintfEntry(EventKind::SprPrintf, "sprPrintf", ctx);
        }

        void SumoPrintfDest(safetyhook::Context& ctx)
        {
            TracePrintfEntry(EventKind::SumoPrintf, "Sumo_Printf", ctx);
        }

        bool OpenTrace()
        {
            try
            {
                const auto path =
                    Module::DllPath.parent_path() /
                    "OutRun2006Tweaks-hudtrace.csv";
                const bool empty =
                    !std::filesystem::exists(path) ||
                    std::filesystem::file_size(path) == 0;

                TraceFile.open(path, std::ios::out | std::ios::app);
                if (!TraceFile)
                    return false;

                StartMs = GetTickCount64();
                if (empty)
                {
                    TraceFile
                        << "# schema=outrun-hudtrace-v2\n"
                        << "# exe_timestamp="
                        << Util::GetModuleTimestamp(Module::ExeHandle) << "\n"
                        << "# exe_size_of_image=" << ExeSizeOfImage() << "\n"
                        << "# module_base=runtime-only; all addresses below are ASLR-safe RVAs\n"
                        << "elapsed_ms,event,return_rva,call_rva,known_area,mode,stage,"
                           "arg0,arg1,arg2,arg3,arg4,arg5,arg6,arg7,text_hash,text,count\n";
                    TraceFile.flush();
                }
                return true;
            }
            catch (const std::exception& e)
            {
                spdlog::warn("VR HUD INSPECTOR: failed to open trace: {}", e.what());
                return false;
            }
        }

        void ResetHooks() noexcept
        {
            SumoPrintfHook = {};
            SprPrintfHook = {};
            LocateHook = {};
            ScaleHook = {};
            ColorHook = {};
            PriorityHook = {};
            FontHook = {};
            ClipSpriteHook = {};
            SpriteAnimHook = {};
        }

    }

    // Feed points used by the existing texture hooks. Keeping put_sprite_ex on
    // its already-established hook avoids stacking two inline detours on the
    // same game function and preserves the real game caller return address.
    void TracePutSprite(SPRARGS* sprargs, float priority,
        const void* returnAddress)
    {
        if (!sprargs)
            return;
        WriteEvent(EventKind::PutSprite, "put_sprite_ex", returnAddress,
            sprargs->xstnum_0, sprargs->top_4,
            sprargs->left_8, sprargs->bottom_C,
            sprargs->right_10, sprargs->scaleX,
            sprargs->scaleY, priority);
    }

    void TracePutSprite2(SPRARGS2* sprargs, float priority,
        const void* returnAddress)
    {
        if (!sprargs)
            return;
        WriteEvent(EventKind::PutSprite2, "put_sprite_ex2", returnAddress,
            sprargs->xstnum_0, sprargs->child_B4 ? 1u : 0u,
            sprargs->color_4,
            sprargs->TopLeft_54.x, sprargs->TopLeft_54.y,
            sprargs->BottomRight_78.x, sprargs->BottomRight_78.y,
            priority);
    }

    namespace
    {
        class VRHudInspectorHook : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRHudInspector";
            }

            bool validate() override
            {
                return Settings::VREnabled.get() &&
                    Settings::VRHudInspector.get();
            }

            void declare_settings() override
            {
                Settings::VRHudInspector.needs_restart();
            }

            bool apply() override
            {
                if (!OpenTrace())
                    return false;

                SpriteAnimHook = safetyhook::create_inline(
                    Game::sprani_play_ae_auth_alpha, SpriteAnimDest);
                ClipSpriteHook = safetyhook::create_inline(
                    Game::put_clip_sprite, ClipSpriteDest);
                FontHook = safetyhook::create_mid(
                    Game::sprSetPrintFont, FontDest);
                PriorityHook = safetyhook::create_mid(
                    Game::sprSetFontPriority, PriorityDest);
                ColorHook = safetyhook::create_mid(
                    Game::sprSetFontColor, ColorDest);
                ScaleHook = safetyhook::create_mid(
                    Game::sprSetFontScale, ScaleDest);
                LocateHook = safetyhook::create_mid(
                    Game::sprLocateP, LocateDest);
                SprPrintfHook = safetyhook::create_mid(
                    Game::sprPrintf, SprPrintfDest);
                SumoPrintfHook = safetyhook::create_mid(
                    Game::Sumo_Printf, SumoPrintfDest);

                if (!SpriteAnimHook || !ClipSpriteHook ||
                    !FontHook || !PriorityHook || !ColorHook ||
                    !ScaleHook || !LocateHook ||
                    !SprPrintfHook || !SumoPrintfHook)
                {
                    spdlog::error(
                        "VR HUD INSPECTOR: one or more sprite hooks failed; disabling inspector");
                    ResetHooks();
                    return false;
                }

                spdlog::info(
                    "VR HUD INSPECTOR: passive sprite/text caller RVA tracing active; texture hooks feed sprite geometry, direct hooks feed sprani/clip, mid-hooks feed sprPrintf/Sumo_Printf plus font state; output=OutRun2006Tweaks-hudtrace.csv");
                return true;
            }

            static VRHudInspectorHook instance;
        };

        VRHudInspectorHook VRHudInspectorHook::instance;
    }
}
