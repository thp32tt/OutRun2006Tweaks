#pragma once

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <filesystem>
#include <string>

#include <spdlog/spdlog.h>

namespace OutRunVR::X86OpenXRProbe
{
    inline std::wstring ReadActiveRuntime32() noexcept
    {
        HKEY key = nullptr;
        const LSTATUS open = RegOpenKeyExW(
            HKEY_LOCAL_MACHINE,
            L"SOFTWARE\\Khronos\\OpenXR\\1",
            0,
            KEY_QUERY_VALUE | KEY_WOW64_32KEY,
            &key);
        if (open != ERROR_SUCCESS)
            return {};

        wchar_t value[1024]{};
        DWORD type = 0;
        DWORD bytes = sizeof(value);
        const LSTATUS query = RegQueryValueExW(
            key, L"ActiveRuntime", nullptr, &type,
            reinterpret_cast<BYTE*>(value), &bytes);
        RegCloseKey(key);
        if (query != ERROR_SUCCESS ||
            (type != REG_SZ && type != REG_EXPAND_SZ))
            return {};

        if (type == REG_EXPAND_SZ)
        {
            wchar_t expanded[2048]{};
            const DWORD n = ExpandEnvironmentStringsW(
                value, expanded, static_cast<DWORD>(std::size(expanded)));
            if (n > 0 && n < std::size(expanded))
                return expanded;
        }
        return value;
    }

    inline void Run() noexcept
    {
#if defined(_WIN64)
        spdlog::info(
            "VR X86 OPENXR PROBE: skipped because this module is 64-bit");
#else
        const std::wstring runtime = ReadActiveRuntime32();
        const bool runtimeExists =
            !runtime.empty() && std::filesystem::exists(runtime);

        HMODULE loader = LoadLibraryW(L"openxr_loader.dll");
        FARPROC getInstanceProcAddr =
            loader ? GetProcAddress(loader, "xrGetInstanceProcAddr") : nullptr;
        FARPROC createInstance =
            loader ? GetProcAddress(loader, "xrCreateInstance") : nullptr;

        spdlog::info(
            "VR X86 OPENXR PROBE: processBits=32 activeRuntime32='{}' runtimeFileExists={} loader32={} xrGetInstanceProcAddr={} xrCreateInstance={}; x86 direct OpenXR remains experimental and x64 host stays authoritative",
            std::filesystem::path(runtime).string(),
            runtimeExists ? 1 : 0,
            loader ? 1 : 0,
            getInstanceProcAddr ? 1 : 0,
            createInstance ? 1 : 0);

        if (loader)
            FreeLibrary(loader);
#endif
    }
}
