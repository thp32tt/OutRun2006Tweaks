#pragma once
#include <cstddef>

namespace outrun::vr::dx11::live_game_frame {
// Live menu, vehicle and race shader/declaration/blend combinations can
// exceed a bounded resident set without becoming unsupported D3D9 states.
// Retire only the oldest successful resident AFTER creating its replacement.
// A failed native Create* keeps every previously compiled program intact;
// the original D3D9 Draw/Present, input and FFB always remain authoritative.
struct LiveGameShaderCacheReplacement {
    template<class Cache>
    [[nodiscard]] static bool retire_oldest_if_full(
        Cache& cache, std::size_t residentLimit) noexcept {
        if (residentLimit == 0u) return false;
        if (cache.size() < residentLimit) return true;
        auto oldest = cache.begin();
        if (oldest == cache.end()) return false;
        for (auto current = cache.begin(); current != cache.end(); ++current)
            if (current->second.lastUse < oldest->second.lastUse)
                oldest = current;
        cache.erase(oldest);
        return true;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
