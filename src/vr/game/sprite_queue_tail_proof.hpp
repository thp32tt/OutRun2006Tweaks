#pragma once

// OutRun priority-list nodes can be freed/relinked inside an exact producer
// before the hook returns. Never dereference the captured old tail until a
// bounded walk from the CURRENT live root proves it is still linked. This is
// the source-of-truth queue path for 19 original GOAL B9200 glyph producers,
// +TIME sprites/numbers and projected rank/result siblings.
namespace OutRunVR::SpriteQueue
{
    template<class Node>
    constexpr Node* FirstVerifiedAppendedNode(
        Node* root, Node* oldTail, Node* newTail, unsigned bound) noexcept
    {
        if (!root || !newTail || newTail == root ||
            newTail == oldTail || bound == 0)
            return nullptr;
        // An empty priority-list root is its own tail_4 sentinel.
        // Exact +TIME/GOAL/rank producers can be the first writers to that
        // priority in a frame; do not lose their whole newly queued batch.
        // Still prove the NEW tail is in the live bounded chain before
        // tagging anything, including when the old tail is the root.
        Node* first = (!oldTail || oldTail == root) ? root->next_0 : nullptr;
        for (Node* node = root->next_0;
             node && bound != 0; node = node->next_0, --bound)
        {
            if (node == oldTail)
                first = node->next_0;
            if (node == newTail)
                return first;
        }
        return nullptr; // detached old tail, foreign node or cyclic/long list
    }
    // Native SpriteNode tails may be recycled or moved when an original
    // producer rebuilds a priority list. Even a currently linked new tail
    // proves nothing about a DIFFERENT root captured before the producer.
    // Reject that source association instead of tagging foreign HUD nodes.
    template<class Node>
    constexpr Node* FirstVerifiedAppendedNodeOnStableRoot(
        Node* oldRoot, Node* currentRoot, Node* oldTail,
        Node* newTail, unsigned bound) noexcept
    {
        return oldRoot && oldRoot == currentRoot
            ? FirstVerifiedAppendedNode(currentRoot, oldTail, newTail, bound)
            : nullptr;
    }
    // The common original 0x2C808/0x2C9DB glyph paths use this same
    // bounded proof. A rebuilt list, detached old tail or cyclic chain
    // must not gain ScreenHud ownership from a previous glyph's snapshot.
    namespace Regression
    {
        struct Node
        {
            Node* next_0 = nullptr;
        };
        constexpr bool TextGlyphQueueRebuildGuards() noexcept
        {
            Node root{}, first{}, oldTail{}, appended{}, replacement{},
                foreign{}, cycleA{}, cycleB{};
            root.next_0 = &first;
            first.next_0 = &oldTail;
            oldTail.next_0 = &appended;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &appended, 8) != &appended)
                return false;
            // A first write after the empty sentinel is a real glyph.
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &root, &appended, 8) != &first)
                return false;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &replacement, &oldTail, &appended, 8))
                return false;
            root.next_0 = &first;
            first.next_0 = &appended; // oldTail was detached/recycled.
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &appended, 8))
                return false;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &foreign, 8))
                return false;
            root.next_0 = &cycleA;
            cycleA.next_0 = &cycleB;
            cycleB.next_0 = &cycleA;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &foreign, 4))
                return false;
            return true;
        }
        static_assert(TextGlyphQueueRebuildGuards(),
            "Original glyphs must not inherit a rebuilt/foreign queue tail");

        // Original 0x4B9D80 "6th/6" is a two-family native GPU HUD
        // batch: one animated first-position sprite plus clip-digit siblings.
        // Both paths must fail closed on a recycled/replaced priority root,
        // rather than gifting a foreign left-/right-eye node ScreenHud.
        constexpr bool FixedFnRankBatchQueueRootGuards() noexcept
        {
            Node root{}, earlier{}, oldTail{}, first{}, last{},
                rebuilt{}, foreign{}, cycle{};
            root.next_0 = &earlier;
            earlier.next_0 = &oldTail;
            oldTail.next_0 = &first;
            first.next_0 = &last;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &last, 5) != &first)
                return false; // valid first and clipped siblings
            // A first-ever 6th/6 write may append to the root sentinel.
            root.next_0 = &first;
            first.next_0 = &last;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &root, &last, 5) != &first)
                return false;
            // The old tail pointer can be physically reused/relinked
            // under a NEW root: tail reachability alone is insufficient.
            rebuilt.next_0 = &oldTail;
            oldTail.next_0 = &first;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &rebuilt, &oldTail, &last, 5))
                return false;
            // A replaced/detached old tail is never dereferenced.
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &last, 5))
                return false;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &root, &foreign, 5))
                return false;
            root.next_0 = &cycle;
            cycle.next_0 = &cycle;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &last, 5))
                return false;
            return true;
        }
        static_assert(FixedFnRankBatchQueueRootGuards(),
            "Both original 6th/6 sprite families require stable priority roots");

        // Exact native HUD/ESC clips may enqueue several siblings after
        // one original E8. Bounded proof must cover the last sibling and
        // reject a replaced root or relinked old queue tail.
        constexpr bool ExactClipQueueRebuildGuards() noexcept
        {
            Node root{}, oldTail{}, first{}, second{}, other{}, newRoot{};
            root.next_0 = &oldTail;
            oldTail.next_0 = &first;
            first.next_0 = &second;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &second, 4) != &first)
                return false;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &second, 2))
                return false;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &newRoot, &oldTail, &second, 4))
                return false;
            oldTail.next_0 = &other;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &oldTail, &second, 4))
                return false;
            return true;
        }
        static_assert(ExactClipQueueRebuildGuards(),
            "Exact HUD/ESC sibling lists must prove stable-root reachability");

        // A live stage/checkpoint/result or generic BA9D0 HUD glyph group
        // can replace its priority root while the native call is pending.
        // Its previous tail can even be reattached under the new root.
        // An old-tail-only check would mis-tag those foreign screen glyphs.
        constexpr bool HudTextRootRebuildGuards() noexcept
        {
            Node beforeRoot{}, old{}, a{}, b{}, afterRoot{}, recycled{}, alien{};
            beforeRoot.next_0 = &old;
            old.next_0 = &a;
            a.next_0 = &b;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &beforeRoot, &beforeRoot, &old, &b, 4) != &a)
                return false;
            // A new root linking the same old tail is NOT an append.
            afterRoot.next_0 = &old;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &beforeRoot, &afterRoot, &old, &b, 4))
                return false;
            // Prior tail detached from the still-live root is also foreign.
            beforeRoot.next_0 = &recycled;
            recycled.next_0 = &b;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &beforeRoot, &beforeRoot, &old, &b, 4))
                return false;
            // An empty-root priority receiving its first glyph remains valid.
            beforeRoot.next_0 = &a;
            a.next_0 = &b;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &beforeRoot, &beforeRoot, &beforeRoot, &b, 3) != &a)
                return false;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &beforeRoot, &beforeRoot, &beforeRoot, &alien, 3))
                return false;
            return true;
        }
        static_assert(HudTextRootRebuildGuards(),
            "HUD text must not borrow a rebuilt or recycled priority root");

    }

}