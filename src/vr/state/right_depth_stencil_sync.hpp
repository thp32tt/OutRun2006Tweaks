#pragma once

namespace OutRunVRStereo
{
    bool IsRightDepthSynchronized() noexcept;
    bool IsRightStencilSynchronized() noexcept;
    void InvalidateRightDepthSync() noexcept;
    void InvalidateRightStencilSync() noexcept;
    void InvalidateRightDepthStencilSync() noexcept;
}
