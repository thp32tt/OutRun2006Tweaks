#pragma once

#include <d3d9.h>

namespace OutRunVR::Lifecycle
{
    bool IsCompatResetDevice(IDirect3DDevice9* device) noexcept;
    bool ResetReplaySucceeded() noexcept;
}
