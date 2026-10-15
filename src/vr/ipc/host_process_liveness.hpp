#pragma once
// Only live Windows host processes may provide auto XR source dimensions.
// HostState is a persistent mapping; HostAlive alone survives crash/kill.
// Nonblocking, closes every OS HANDLE, never starts or awaits OpenXR.
#include <Windows.h>
#include <cstdint>
namespace OutRunVR::HostProcess
{
    inline bool IsAlive(std::uint32_t pid) noexcept
    {
        if (!pid) return false;
        HANDLE process = OpenProcess(SYNCHRONIZE, FALSE, pid);
        if (!process) return false;
        const DWORD result = WaitForSingleObject(process, 0);
        CloseHandle(process);
        return result == WAIT_TIMEOUT;
    }
}
