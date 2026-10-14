#pragma once
// Bounds shared by packaged R26+HUD and full-chain R30 IndexedPrimitiveUP.
#include <cstdint>
#include <limits>
namespace OutRunVR::R30IndexedUpBounds {
inline constexpr std::uint32_t MaxVertices=262144u;
inline constexpr std::uint32_t MaxIndices=524288u;
inline constexpr std::uint32_t PrimitiveElements(
    std::uint32_t type,std::uint32_t count) noexcept {
    constexpr auto max=(std::numeric_limits<std::uint32_t>::max)();
    if(!count) return 0u;
    switch(type) {
    case 1: return count; // POINTLIST
    case 2: return count<=max/2u?count*2u:0u; // LINELIST
    case 3: return count<max?count+1u:0u; // LINESTRIP
    case 4: return count<=max/3u?count*3u:0u; // TRIANGLELIST
    case 5: case 6: return count<=max-2u?count+2u:0u; // STRIP/FAN
    default: return 0u;
    }
}
inline constexpr bool DeclaredWindow(
    std::uint32_t first,std::uint32_t count,std::uint32_t& end) noexcept {
    const std::uint64_t wide=static_cast<std::uint64_t>(first)+count;
    if(!count||wide>MaxVertices) return false;
    end=static_cast<std::uint32_t>(wide);return true;
}
inline constexpr bool LocalIndex(std::uint32_t index,std::uint32_t first,
    std::uint32_t end,std::uint32_t& local) noexcept {
    if(index<first||index>=end) return false;
    local=index-first;return true;
}
}
