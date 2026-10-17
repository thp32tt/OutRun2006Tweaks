#pragma once
#include <cstring>
#include <type_traits>
#include <utility>

// R84 original base-projection inverse reuse across shader HUD, GOAL/+TIME,
// world-projected overlays and lens effects. The game may change its FOV or
// projection within a frame: compare all input bytes rather than only pose or
// Present epoch. A failed inversion always invalidates the old entry.
namespace OutRunVR::R30Projection
{
    template <typename Matrix>
    class ExactInverseCache final
    {
        static_assert(std::is_trivially_copyable<Matrix>::value,
            "Projection cache requires exact byte-stable matrix storage");
    public:
        template <typename Invert>
        bool get(const Matrix& source, Matrix& output, Invert&& invert) noexcept
        {
            if (valid_ && std::memcmp(&source_, &source, sizeof(Matrix)) == 0)
            {
                output = inverse_;
                return true;
            }
            Matrix computed{};
            if (!std::forward<Invert>(invert)(source, computed))
            {
                invalidate();
                return false;
            }
            source_ = source;
            inverse_ = computed;
            output = computed;
            valid_ = true;
            return true;
        }

        void invalidate() noexcept { valid_ = false; }

    private:
        Matrix source_{};
        Matrix inverse_{};
        bool valid_ = false;
    };
}
