#pragma once
#include <array>
#include <cmath>

// A texture replacement changes the UV/pixel scale only for a single original
// put_sprite call. The game may reuse the same SPRARGS/SPRARGS2 storage for
// menu, car selection, and child mask sprites: never permanently rewrite it.
namespace OutRunVR::SpriteUV
{
    inline bool PositiveFinite(float x, float y) noexcept
    {
        return std::isfinite(x) && std::isfinite(y) &&
            x > 0.0f && y > 0.0f;
    }

    template<class Args> class ScopedSprArgs2Scale
    {
        Args* args_ = nullptr;
        std::array<float, 8> old_{};
    public:
        ScopedSprArgs2Scale() = default;
        ScopedSprArgs2Scale(const ScopedSprArgs2Scale&) = delete;
        ScopedSprArgs2Scale& operator=(const ScopedSprArgs2Scale&) = delete;
        ~ScopedSprArgs2Scale() { Restore(); }

        bool Apply(Args* args, float sx, float sy) noexcept
        {
            if (args_ || !args || !PositiveFinite(sx, sy))
                return false;
            const std::array<float, 8> original{
                args->left_88, args->left_A0,
                args->right_90, args->right_98,
                args->bottom_84, args->bottom_8C,
                args->top_94, args->top_9C};
            for (float v : original)
                if (!std::isfinite(v)) return false;
            const std::array<float, 8> next{
                1.0f - (1.0f - original[0]) * sx,
                1.0f - (1.0f - original[1]) * sx,
                1.0f - (1.0f - original[2]) * sx,
                1.0f - (1.0f - original[3]) * sx,
                original[4] * sy, original[5] * sy,
                original[6] * sy, original[7] * sy};
            for (float v : next)
                if (!std::isfinite(v)) return false;
            old_ = original;
            args_ = args;
            args->left_88 = next[0]; args->left_A0 = next[1];
            args->right_90 = next[2]; args->right_98 = next[3];
            args->bottom_84 = next[4]; args->bottom_8C = next[5];
            args->top_94 = next[6]; args->top_9C = next[7];
            return true;
        }
        void Restore() noexcept
        {
            if (!args_) return;
            args_->left_88 = old_[0]; args_->left_A0 = old_[1];
            args_->right_90 = old_[2]; args_->right_98 = old_[3];
            args_->bottom_84 = old_[4]; args_->bottom_8C = old_[5];
            args_->top_94 = old_[6]; args_->top_9C = old_[7];
            args_ = nullptr;
        }
    };

    template<class Args> class ScopedSprArgsScale
    {
        Args* args_ = nullptr;
        std::array<float, 6> old_{};
    public:
        ScopedSprArgsScale() = default;
        ScopedSprArgsScale(const ScopedSprArgsScale&) = delete;
        ScopedSprArgsScale& operator=(const ScopedSprArgsScale&) = delete;
        ~ScopedSprArgsScale() { Restore(); }

        bool Apply(Args* args, float sx, float sy) noexcept
        {
            if (args_ || !args || !PositiveFinite(sx, sy))
                return false;
            const std::array<float, 6> original{
                args->top_4, args->left_8, args->bottom_C,
                args->right_10, args->scaleX, args->scaleY};
            for (float v : original)
                if (!std::isfinite(v)) return false;
            const std::array<float, 6> next{
                original[0] * sy, original[1] * sx,
                original[2] * sy, original[3] * sx,
                original[4] / sx, original[5] / sy};
            for (float v : next)
                if (!std::isfinite(v)) return false;
            old_ = original;
            args_ = args;
            args->top_4 = next[0]; args->left_8 = next[1];
            args->bottom_C = next[2]; args->right_10 = next[3];
            args->scaleX = next[4]; args->scaleY = next[5];
            return true;
        }
        void Restore() noexcept
        {
            if (!args_) return;
            args_->top_4 = old_[0]; args_->left_8 = old_[1];
            args_->bottom_C = old_[2]; args_->right_10 = old_[3];
            args_->scaleX = old_[4]; args_->scaleY = old_[5];
            args_ = nullptr;
        }
    };
}
