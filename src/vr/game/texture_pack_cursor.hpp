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

    // UI xstset and scene xmtset each own a Cursor. Reentering the same pack
    // continues its indexed DDS sequence; new path/slot restarts at zero.
    // The scene caller passes a constant slot because its XmtIndex denotes
    // the object *inside* the current pack, not the pack identity.
    class Cursor final
    {
        std::string name_;
        int slot_ = 0;
        std::uint64_t next_ = 0;
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
            selected_ = true;
            return true;
        }

        std::uint64_t NextIndex() noexcept { return next_++; }
        const std::string& Name() const noexcept { return name_; }
    };
}
