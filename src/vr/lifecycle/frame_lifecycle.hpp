#pragma once

#include <Windows.h>
#include <d3d9.h>
#include <cstdint>

namespace OutRunVRStereo
{
    void NotifyTopLevelDraw(IDirect3DDevice9* device) noexcept;
    std::uint64_t TopLevelDrawSerial() noexcept;
}
