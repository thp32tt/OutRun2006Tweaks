#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Exactly one real game CPU/GDI surface write per native game frame. Foreign,
// overlapping or unfinished acquisitions cannot become publishable DX11 pixels.
struct GameNativeCpuSurfaceTicket {
    std::uintptr_t owner{}, surface{};
    std::uint32_t left{}, top{}, right{}, bottom{};
    [[nodiscard]] constexpr bool active() const noexcept { return owner && surface; }
    [[nodiscard]] constexpr bool begin(std::uintptr_t device, std::uintptr_t identity,
        std::uint32_t l, std::uint32_t t, std::uint32_t r, std::uint32_t b,
        std::uint32_t w, std::uint32_t h) noexcept {
        if (active() || !device || !identity || !w || !h ||
            l >= r || t >= b || r > w || b > h) return false;
        owner=device; surface=identity; left=l; top=t; right=r; bottom=b;
        return true;
    }
    [[nodiscard]] constexpr bool matches(std::uintptr_t device,
        std::uintptr_t identity, std::uint32_t l, std::uint32_t t,
        std::uint32_t r, std::uint32_t b) const noexcept {
        return active() && device==owner && identity==surface &&
            l==left && t==top && r==right && b==bottom;
    }
    constexpr void reset() noexcept { *this={}; }
};
}
