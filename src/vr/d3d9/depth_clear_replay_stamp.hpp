#pragma once
#include <cstdint>

namespace OutRunVR {
// A full clear receipt belongs to the currently tracked LEFT depth surface.
// Descriptor equality is allocation compatibility, not content identity.
// Binding transitions (including unbind/rebind) and resource retirement
// revoke the receipt before it can authorize a RIGHT clear replay.
struct DepthClearReplayStamp final {
    std::uint64_t epoch=0;
    std::uint32_t flags=0;
    constexpr void Record(std::uint64_t current,std::uint32_t cleared) noexcept {
        epoch=current; flags=cleared;
    }
    constexpr void Invalidate() noexcept { epoch=0; flags=0; }
    constexpr void OnBindingChange(bool changed) noexcept {
        if(changed) Invalidate();
    }
    constexpr bool Current(std::uint64_t current) const noexcept {
        return epoch!=0 && epoch==current && flags!=0;
    }
};
} // namespace OutRunVR
