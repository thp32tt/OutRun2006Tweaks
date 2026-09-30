#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    bool IsGameStateBlockRecording() noexcept;
    bool IsStateBlockTrackingReliable() noexcept;
    void FlushPendingStateBlockResync(IDirect3DDevice9* device) noexcept;
}
