#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    bool IsCurrentGameDevice(IDirect3DDevice9* device) noexcept;
    bool IsInternalStereoPassActive();
    bool StereoWantedForCurrentFrame() noexcept;
    bool TargetIsCurrentBackBuffer() noexcept;
    IDirect3DDevice9* StereoInstalledDeviceSnapshot() noexcept;
    bool IsVRTelemetryEnabled() noexcept;
}
