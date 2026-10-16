#include "vr/game/goal_result_parent_provenance.hpp"
#include <array>
#include <cstddef>
#include <cstdint>

// Execute the EXACT production C++ whitelist (not a Python/regex surrogate).
// A successful native run proves only source-identity arithmetic; physical
// Quest3/VDXR binocular placement and game-stack unwind remain UNTESTED.
int main()
{
    using namespace OutRunVR::GoalResult;
    if (OriginalB9200CallReturns.size() != 19u ||
        !CheckParentReturnProvenance())
        return 1;
    constexpr std::array<std::uintptr_t, 4> images{{
        0x00400000u, 0x01000000u, 0x20000000u, 0x7F000000u
    }};
    for (const auto base : images)
    {
        for (std::size_t i = 0; i < OriginalB9200CallReturns.size(); ++i)
        {
            const auto ret = base + OriginalB9200CallReturns[i];
            if (!IsOriginalB9200ParentReturn(base, ret))
                return 2;
            // An exact EXE E8 return and the bytes on either side are
            // distinct: old rva+5 post-CALL detours crashed at 97C5F/97E75.
            if (IsOriginalB9200ParentReturn(base, ret - 1u) ||
                IsOriginalB9200ParentReturn(base, ret + 1u))
                return 3;
            for (std::size_t j = 0; j < i; ++j)
                if (OriginalB9200CallReturns[i] ==
                    OriginalB9200CallReturns[j])
                    return 4;
        }
        for (const auto unrelated : {
                 0x0002C80Du, // shared glyph E8 not a B9200 parent
                 0x000989B2u, // +TIME numeric helper
                 0x000BEA5Fu, // separate final GOAL helper
                 0x00097C5Fu, // prior crash EIP inside detached midhook
                 0x00097E75u  // second crash EIP inside detached midhook
             })
            if (IsOriginalB9200ParentReturn(base, base + unrelated))
                return 5;
        if (IsOriginalB9200ParentReturn(base, base) ||
            IsOriginalB9200ParentReturn(base, base - 1u) ||
            IsOriginalB9200ParentReturn(0u, base + 0x973B4u))
            return 6;
    }
    return 0;
}
