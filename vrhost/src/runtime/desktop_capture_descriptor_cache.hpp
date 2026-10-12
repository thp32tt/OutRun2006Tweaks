#pragma once
#include <cstdint>

// Cache the DXGI output-duplication *texture descriptor*, not its pixels or
// borrowed IDXGIResource. A duplication session has a fixed extent and format:
// mode/output changes invalidate the duplication, and the first captured image
// after a rebind must be validated through the actual D3D11 texture again.
// This removes an otherwise repeated driver GetDesc on every classic SBS
// capture without changing CopyResource, last-present, or frame selection.
namespace OutRunVrDesktopCaptureDescriptor
{
    struct Key
    {
        std::uintptr_t duplication = 0;
        std::uint32_t width = 0;
        std::uint32_t height = 0;
        std::uint32_t format = 0;
    };
    struct Cache
    {
        Key last{};
        bool valid = false;

        constexpr bool CanReuse(bool sameOutput, bool haveFrame,
            bool haveSourceAndView, const Key& current) const noexcept
        {
            return valid && sameOutput && haveFrame && haveSourceAndView &&
                current.duplication != 0 && current.width != 0 &&
                current.height != 0 &&
                last.duplication == current.duplication &&
                last.width == current.width &&
                last.height == current.height &&
                last.format == current.format;
        }
        constexpr void Record(const Key& current) noexcept
        {
            last = current;
            valid = current.duplication != 0 && current.width != 0 &&
                current.height != 0;
        }
        constexpr void Invalidate() noexcept { last = {}; valid = false; }
    };
}
