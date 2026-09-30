#pragma once

#include <cstdint>

namespace OutRunVRStereo
{
    bool IsDirectTransportOverlayReady() noexcept;
    bool ReadDirectTransportGpuCompletedFrame(
        std::uint32_t slotIndex, std::uint32_t& completedFrame) noexcept;
    void NoteDirectTransportAckBackpressure() noexcept;
    bool IsDirectTransportInstallReady() noexcept;
    bool IsDirectTransportInstallFailed() noexcept;
}
