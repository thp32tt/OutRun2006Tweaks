#pragma once

#include <cstdint>
#include <string>
#include <string_view>

namespace OutRunVR::TexturePacks
{
    // Text and game-slot identity, never caller char* identity. The original
    // engine can reuse a mutable filename buffer while switching packs.
    constexpr bool SameSource(std::string_view stored, int storedSlot,
        std::string_view incoming, int incomingSlot) noexcept
    {
        return storedSlot == incomingSlot && stored == incoming;
    }
    static_assert(SameSource("selector.xst", 3, "selector.xst", 3));
    static_assert(!SameSource("selector.xst", 3, "selector.xst", 4));
    static_assert(!SameSource("selector.xst", 3, "car.xst", 3));

    // Freeze the first known gamepad family for the entire texture session.
    // PC has no pad subdirectory but is still a real selection. If that
    // initial selection is not latched, later hot-plugging Xbox/PS can load
    // half the UI replacement sprites from a different family.
    class SessionPadFamily final
    {
        int selected_ = 0;
        bool locked_ = false;
    public:
        constexpr void Observe(int current, int forced, int none) noexcept
        {
            if (locked_)
                return;
            const int candidate = forced != none ? forced : current;
            if (candidate != none)
            {
                selected_ = candidate;
                locked_ = true;
            }
        }
        constexpr bool Locked() const noexcept { return locked_; }
        constexpr int Type() const noexcept { return selected_; }
    };

    // UI xstset and scene xmtset each own a Cursor. Reentering the same pack
    // continues its indexed DDS sequence; new path/slot restarts at zero.
    // The scene caller passes a constant slot because its XmtIndex denotes
    // the object *inside* the current pack, not the pack identity.
    class Cursor final
    {
        std::string name_;
        int slot_ = 0;
        std::uint64_t next_ = 0;
        int lastGameTextureIndex_ = -1;
        bool selected_ = false;

    public:
        bool Select(const char* name, int slot)
        {
            if (!name)
                return false;
            const std::string_view incoming(name);
            if (selected_ && SameSource(name_, slot_, incoming, slot))
                return false;
            name_.assign(incoming.data(), incoming.size());
            slot_ = slot;
            next_ = 0;
            lastGameTextureIndex_ = -1;
            selected_ = true;
            return true;
        }

        std::uint64_t NextIndex() noexcept { return next_++; }

        // LoadXstsetSprite may repeat the identical filename/slot while a
        // UI/car-selector pack is loading; that is NOT by itself a restart.
        // Instead use the game's actual per-pack texture number. Returning
        // to its first texture after a later one proves a new load pass, even
        // when the mutable XST filename and slot are unchanged. Otherwise
        // stale indexed DDS ordinals can resolve a different car/UI sprite.
        // Ignore invalid numbers and ordinary backward seeks inside a pass;
        // scene XMT packs keep their original independent sequence.
        std::uint64_t NextIndexForGameTexture(int gameTextureIndex) noexcept
        {
            if (selected_ && gameTextureIndex >= 0)
            {
                if (lastGameTextureIndex_ > gameTextureIndex &&
                    gameTextureIndex <= 1)
                    next_ = 0;
                lastGameTextureIndex_ = gameTextureIndex;
            }
            return NextIndex();
        }
        const std::string& Name() const noexcept { return name_; }
    };
}
