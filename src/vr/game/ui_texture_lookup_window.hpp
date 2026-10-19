#pragma once

// Original OutRun get_texture calls feed at most one native put_sprite_ex2
// submission. Texture pointers can be recycled by a later car-selector/menu
// xstset, so a cached address alone is never durable sprite ownership.
namespace OutRunVR::SpriteUV
{
    template<class Texture> class TextureLookupWindow
    {
    public:
        struct Submission
        {
            Texture* sprite = nullptr;
            Texture* mask = nullptr;
            int spriteId = 0;
            int maskId = 0;
            constexpr bool SpriteMatches(Texture* submitted) const noexcept
            {
                return submitted && sprite == submitted;
            }
            constexpr bool MaskMatches(Texture* submitted) const noexcept
            {
                return submitted && mask == submitted;
            }
        };
    private:
        Submission pending_{};
    public:
        constexpr void Clear() noexcept { pending_ = {}; }
        constexpr void Observe(Texture* returned, int id, bool hasScale) noexcept
        {
            // A failed texture lookup is a hard boundary: never turn a
            // previously valid sprite into the next selection-mask owner.
            if (!returned) { Clear(); return; }
            pending_.mask = pending_.sprite;
            pending_.maskId = pending_.spriteId;
            pending_.sprite = hasScale ? returned : nullptr;
            pending_.spriteId = hasScale ? id : 0;
        }
        constexpr Submission Consume() noexcept
        {
            const auto current = pending_;
            Clear();
            return current;
        }
    };

    namespace Regression
    {
        constexpr bool TextureLookupSubmissionGuards() noexcept
        {
            struct Texture { int id = 0; } mask{}, sprite{}, foreign{};
            TextureLookupWindow<Texture> window{};
            window.Observe(&mask, 7, true);
            window.Observe(&sprite, 8, true);
            const auto paired = window.Consume();
            if (!paired.SpriteMatches(&sprite) || paired.spriteId != 8 ||
                !paired.MaskMatches(&mask) || paired.maskId != 7 ||
                paired.SpriteMatches(&mask) || paired.MaskMatches(&foreign))
                return false;
            const auto reused = window.Consume();
            if (reused.SpriteMatches(&sprite) || reused.MaskMatches(&mask))
                return false; // one native submission owns one binding window
            window.Observe(&mask, 7, true);
            window.Observe(nullptr, 9, false);
            const auto failed = window.Consume();
            if (failed.SpriteMatches(&mask) || failed.MaskMatches(&mask) ||
                failed.SpriteMatches(nullptr) || failed.MaskMatches(nullptr))
                return false; // native failed load must not leak the prior mask
            window.Observe(&mask, 7, true);
            window.Observe(&sprite, 8, false);
            const auto plain = window.Consume();
            if (plain.SpriteMatches(&sprite) || !plain.MaskMatches(&mask) ||
                plain.maskId != 7)
                return false; // unscaled parent may have a scaled child mask
            window.Observe(&sprite, 8, true);
            window.Clear();
            const auto newPack = window.Consume();
            return !newPack.SpriteMatches(&sprite) &&
                   !newPack.MaskMatches(&mask);
        }
        static_assert(TextureLookupSubmissionGuards(),
            "Car selector sprite/mask must require a live, one-shot texture lookup");
    }
}
