#pragma once

// R21 last-resort crash evidence for the x64 OpenXR host.
// Produces a small text fault record plus a minidump beside the host executable.
// This is deliberately diagnostic only; it does not attempt recovery from an
// access violation or alter the OpenXR/D3D11 runtime state.

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <Windows.h>
#include <DbgHelp.h>

#include <cstdint>
#include <cstdio>
#include <cwchar>

namespace OutRunVrR21CrashDiagnostics
{
    inline constexpr const char* BuildId = "R21-crash-dump-20260916";

    inline void BuildSiblingPath(const wchar_t* fileName,
        wchar_t out[MAX_PATH]) noexcept
    {
        out[0] = L'\0';
        DWORD n = GetModuleFileNameW(nullptr, out, MAX_PATH);
        if (!n || n >= MAX_PATH)
        {
            wcsncpy_s(out, MAX_PATH, fileName, _TRUNCATE);
            return;
        }
        wchar_t* slash = wcsrchr(out, L'\\');
        if (!slash)
        {
            wcsncpy_s(out, MAX_PATH, fileName, _TRUNCATE);
            return;
        }
        *(slash + 1) = L'\0';
        wcsncat_s(out, MAX_PATH, fileName, _TRUNCATE);
    }

    inline void WriteFaultText(EXCEPTION_POINTERS* ep) noexcept
    {
        wchar_t path[MAX_PATH]{};
        BuildSiblingPath(L"outrun-vr-host-crash.txt", path);
        HANDLE file = CreateFileW(path, GENERIC_WRITE, FILE_SHARE_READ,
            nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE)
            return;

        const EXCEPTION_RECORD* er = ep ? ep->ExceptionRecord : nullptr;
        const void* exceptionAddress = er ? er->ExceptionAddress : nullptr;
        MEMORY_BASIC_INFORMATION mbi{};
        HMODULE module = nullptr;
        if (exceptionAddress &&
            VirtualQuery(exceptionAddress, &mbi, sizeof(mbi)) == sizeof(mbi))
            module = static_cast<HMODULE>(mbi.AllocationBase);

        wchar_t modulePath[MAX_PATH]{};
        if (module)
            GetModuleFileNameW(module, modulePath, MAX_PATH);

        char moduleUtf8[MAX_PATH * 3]{};
        if (modulePath[0])
            WideCharToMultiByte(CP_UTF8, 0, modulePath, -1,
                moduleUtf8, static_cast<int>(sizeof(moduleUtf8)), nullptr, nullptr);

        const std::uintptr_t address =
            reinterpret_cast<std::uintptr_t>(exceptionAddress);
        const std::uintptr_t base = reinterpret_cast<std::uintptr_t>(module);
        const std::uintptr_t rva = base && address >= base ? address - base : 0;

        unsigned long long operation = ~0ull;
        unsigned long long target = 0;
        if (er && er->ExceptionCode == EXCEPTION_ACCESS_VIOLATION &&
            er->NumberParameters >= 2)
        {
            operation = static_cast<unsigned long long>(er->ExceptionInformation[0]);
            target = static_cast<unsigned long long>(er->ExceptionInformation[1]);
        }

        char text[2048]{};
        const int len = _snprintf_s(text, sizeof(text), _TRUNCATE,
            "build=%s\r\n"
            "pid=%lu tid=%lu\r\n"
            "exception=0x%08lX\r\n"
            "exceptionAddress=0x%016llX\r\n"
            "module=%s\r\n"
            "moduleBase=0x%016llX\r\n"
            "rva=0x%llX\r\n"
            "avOperation=%llu (0=read,1=write,8=execute)\r\n"
            "avTarget=0x%016llX\r\n",
            BuildId,
            GetCurrentProcessId(), GetCurrentThreadId(),
            er ? static_cast<unsigned long>(er->ExceptionCode) : 0ul,
            static_cast<unsigned long long>(address),
            moduleUtf8[0] ? moduleUtf8 : "<unknown>",
            static_cast<unsigned long long>(base),
            static_cast<unsigned long long>(rva),
            operation, target);

        if (len > 0)
        {
            DWORD written = 0;
            WriteFile(file, text, static_cast<DWORD>(len), &written, nullptr);
            FlushFileBuffers(file);
        }
        CloseHandle(file);
    }

    inline void WriteMiniDump(EXCEPTION_POINTERS* ep) noexcept
    {
        wchar_t path[MAX_PATH]{};
        BuildSiblingPath(L"outrun-vr-host-crash.dmp", path);
        HANDLE file = CreateFileW(path, GENERIC_WRITE, FILE_SHARE_READ,
            nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE)
            return;

        MINIDUMP_EXCEPTION_INFORMATION exceptionInfo{};
        exceptionInfo.ThreadId = GetCurrentThreadId();
        exceptionInfo.ExceptionPointers = ep;
        exceptionInfo.ClientPointers = FALSE;

        const MINIDUMP_TYPE type = static_cast<MINIDUMP_TYPE>(
            MiniDumpWithThreadInfo |
            MiniDumpWithIndirectlyReferencedMemory |
            MiniDumpWithUnloadedModules);
        MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(), file,
            type, ep ? &exceptionInfo : nullptr, nullptr, nullptr);
        FlushFileBuffers(file);
        CloseHandle(file);
    }

    inline LONG WINAPI UnhandledExceptionFilter(EXCEPTION_POINTERS* ep) noexcept
    {
        WriteFaultText(ep);
        WriteMiniDump(ep);
        // Preserve normal Windows crash handling/WER after collecting evidence.
        return EXCEPTION_CONTINUE_SEARCH;
    }

    struct Installer
    {
        Installer() noexcept
        {
            SetUnhandledExceptionFilter(UnhandledExceptionFilter);
        }
    };

    inline Installer InstallOnce{};
}
