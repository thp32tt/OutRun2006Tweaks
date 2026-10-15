#pragma once
// OpenXR stereo array swapchains have one common per-slice extent.
// This host/game ABI-independent policy converts two runtime recommendations
// into the *actually allocated* common extent. No desktop-size substitution.
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace OutRunVR::EyeExtent
{
    struct Size { std::uint32_t width{}, height{}; };
    struct ViewLimits { Size recommended{}, maximum{}; };
    constexpr bool Valid(Size s) noexcept { return s.width > 0 && s.height > 0; }
    constexpr bool Equal(Size a, Size b) noexcept
    { return a.width == b.width && a.height == b.height; }

    inline Size ResolveHost(ViewLimits left, ViewLimits right, float scale) noexcept
    {
        if (!Valid(left.recommended) || !Valid(right.recommended) ||
            !Valid(left.maximum) || !Valid(right.maximum) ||
            !std::isfinite(scale) || scale <= 0.0f)
            return {};
        // Array layers must share one size. Each eye's maximum constrains both.
        const std::uint32_t capW = std::min({left.maximum.width, right.maximum.width, 8192u});
        const std::uint32_t capH = std::min({left.maximum.height, right.maximum.height, 8192u});
        const std::uint32_t recW = std::max(left.recommended.width, right.recommended.width);
        const std::uint32_t recH = std::max(left.recommended.height, right.recommended.height);
        // Clamp *before* float -> uint conversion to prevent overflow or UB.
        const double w = std::clamp(static_cast<double>(recW) * scale, 1.0,
            static_cast<double>(capW));
        const double h = std::clamp(static_cast<double>(recH) * scale, 1.0,
            static_cast<double>(capH));
        return {static_cast<std::uint32_t>(std::lround(w)),
                static_cast<std::uint32_t>(std::lround(h))};
    }
    inline Size ResolveGame(Size published, Size deviceCaps) noexcept
    {
        // Never silently clamp the game RT below the host's actual swapchain.
        // Such a mismatch must instead select the existing safe SBS fallback.
        if (!Valid(published) || !Valid(deviceCaps) ||
            published.width > deviceCaps.width ||
            published.height > deviceCaps.height ||
            published.width > 8192u || published.height > 8192u)
            return {};
        return published;
    }
    inline Size ResolveStartup(Size left, Size right) noexcept
    {
        // Game D3D9Ex uses one per-eye target, never two widths side by side.
        // Host already publishes its allocated common swapchain extent.
        // If host generations disagree, refuse to resize the game at startup.
        if (!Valid(left) || !Equal(left, right) ||
            left.width < 640u || left.height < 480u ||
            left.width > 8192u || left.height > 8192u ||
            static_cast<std::uint64_t>(left.width) * left.height > 16777216ull)
            return {};
        return left;
    }
    class Generation
    {
        Size active_{};
        std::uint32_t number_{};
    public:
        bool NeedsAllocation(Size required) const noexcept
        { return Valid(required) && !Equal(active_, required); }
        bool Matches(Size required) const noexcept
        { return Valid(required) && Equal(active_, required); }
        void Commit(Size size) noexcept
        {
            if (!Valid(size)) return;
            active_ = size;
            if (++number_ == 0) ++number_;
        }
        void Reset() noexcept { active_ = {}; if (++number_ == 0) ++number_; }
        Size Active() const noexcept { return active_; }
        std::uint32_t Number() const noexcept { return number_; }
    };
}
