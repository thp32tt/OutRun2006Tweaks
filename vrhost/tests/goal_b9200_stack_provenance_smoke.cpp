#include "vr/game/goal_result_parent_provenance.hpp"
#include "vr/game/sprite_queue_tail_proof.hpp"
#include <array>
#include <cstddef>
#include <cstdint>

// Execute the EXACT production C++ whitelist (not a Python/regex surrogate).
// A successful native run proves only source-identity arithmetic; physical
// Quest3/VDXR binocular placement and game-stack unwind remain UNTESTED.

// GOAL text can emit multiple children per parent and may rebuild its list
// inside put_sprite_ex. This exercises the production queue proof rather
// than reimplementing the pointer algorithm in a standalone test.
static bool VerifyOriginalGoalGlyphQueue() noexcept
{
    struct Node { Node* next_0 = nullptr; };
    using OutRunVR::SpriteQueue::FirstVerifiedAppendedNode;
    Node root{}, old{}, leftGlyph{}, rightGlyph{}, stale{}, foreign{};
    root.next_0 = &old;
    old.next_0 = &leftGlyph;
    leftGlyph.next_0 = &rightGlyph;
    if (FirstVerifiedAppendedNode<Node>(&root, &old, &rightGlyph, 4) !=
            &leftGlyph ||
        FirstVerifiedAppendedNode<Node>(&root, nullptr, &rightGlyph, 4) !=
            &old ||
        FirstVerifiedAppendedNode<Node>(&root, &old, &old, 4) ||
        FirstVerifiedAppendedNode<Node>(&root, &old, &foreign, 4) ||
        FirstVerifiedAppendedNode<Node>(&root, &old, &rightGlyph, 2))
        return false;
    // If a new GOAL glyph source clears the queue and reuses the root,
    // the stale old pointer is not dereferenced or used to tag new nodes.
    root.next_0 = &leftGlyph;
    if (FirstVerifiedAppendedNode<Node>(&root, &old, &rightGlyph, 3) ||
        FirstVerifiedAppendedNode<Node>(&root, &stale, &rightGlyph, 3) ||
        FirstVerifiedAppendedNode<Node>(&root, &leftGlyph, &rightGlyph, 3) !=
            &rightGlyph ||
        FirstVerifiedAppendedNode<Node>(&root, nullptr, &rightGlyph, 3) !=
            &leftGlyph)
        return false;
    // Neither a missing tail nor a self-referential queue can authorize
    // tagging unknown sprites. No former node is accessed after a rebuild.
    if (FirstVerifiedAppendedNode<Node>(&root, nullptr, nullptr, 3))
        return false;
    leftGlyph.next_0 = &leftGlyph;
    return FirstVerifiedAppendedNode<Node>(&root, &old, &rightGlyph, 3) == nullptr;
}

int main()
{
    using namespace OutRunVR::GoalResult;
    if (!VerifyOriginalGoalGlyphQueue())
        return 7;
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
