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
        if (!root || !oldTail || !newTail || newTail == root ||
            newTail == oldTail || bound == 0)
            return nullptr;
        // An empty priority-list root is its own tail_4 sentinel.
        // Exact +TIME/GOAL/rank producers can be the first writers to that
        // priority in a frame; do not lose their whole newly queued batch.
        // Still prove the NEW tail is in the live bounded chain before
        // tagging anything, including when the old tail is the root.
        Node* first = oldTail == root ? root->next_0 : nullptr;
        for (Node* node = root->next_0;
             node && bound != 0; node = node->next_0, --bound)
        {
            if (node == oldTail)
                first = node->next_0;
            if (node == newTail)
            {
                // Root->tail_4 must be a *terminal* node. A recycled tail
                // reachable inside a rebuilt/cyclic priority chain is not a
                // completed producer append and can otherwise give later
                // foreign sprites the previous HUD/+TIME/GOAL eye owner.
                return node->next_0 == nullptr ? first : nullptr;
            }
        }
        return nullptr; // detached old tail, foreign node or cyclic/long list
    }

    // Rival R26 known-good recovery: the original queue consumer clears
    // sprite_prio_root[prio] to nullptr after each priority pass. Therefore an
    // exact 0xBB796 sprani producer can legitimately be the FIRST writer into
    // a priority with no pre-existing root/tail. Historical R26 handled this
    // with root->next_0. Recover that case without dereferencing any stale
    // pointer: the caller must prove BOTH old root and old tail were null.
    template<class Node>
    constexpr Node* FirstVerifiedNewRootAppendedChain(
        Node* oldRoot, Node* oldTail,
        Node* currentRoot, Node* newTail, unsigned bound) noexcept
    {
        if (oldRoot || oldTail || !currentRoot || !newTail ||
            newTail == currentRoot || bound == 0)
            return nullptr;
        Node* first = currentRoot->next_0;
        if (!first)
            return nullptr;
        for (Node* node = first;
             node && bound != 0; node = node->next_0, --bound)
        {
            if (node == newTail)
                return node->next_0 == nullptr ? first : nullptr;
        }
        return nullptr;
    }

    namespace RivalNewRootRegression
    {
        struct Node { Node* next_0 = nullptr; };
        constexpr bool Proof() noexcept
        {
            Node root{}, one{}, two{}, foreign{}, cycle{};
            root.next_0 = &one;
            one.next_0 = &two;
            if (FirstVerifiedNewRootAppendedChain(
                    nullptr, nullptr, &root, &two, 3) != &one)
                return false;
            if (FirstVerifiedNewRootAppendedChain(
                    &root, nullptr, &root, &two, 3))
                return false;
            if (FirstVerifiedNewRootAppendedChain(
                    nullptr, &root, &root, &two, 3))
                return false;
            if (FirstVerifiedNewRootAppendedChain(
                    nullptr, nullptr, &root, &foreign, 3))
                return false;
            two.next_0 = &cycle;
            if (FirstVerifiedNewRootAppendedChain(
                    nullptr, nullptr, &root, &two, 3))
                return false;
            return true;
        }
        static_assert(Proof(),
            "Rival new-root recovery must require null pre-root and terminal live tail");
    }

    // ABC C experiment: a *single* new child under a replaced root can be
    // recovered only when the old root was an EMPTY sentinel at source entry.
    // The caller must separately prove same GOAL, same queue epoch and one
    // exact original full-result E8 (never a generic HUD or rival callback).
    // Never dereference oldRoot/oldTail: the old list may have been freed.
    template<class Node>
    constexpr Node* FirstVerifiedRebuiltEmptySingleChild(
        Node* oldRoot, Node* oldTail, bool wasEmptyAtEntry,
        Node* currentRoot, Node* newTail, unsigned bound) noexcept
    {
        if (!wasEmptyAtEntry || !oldRoot || oldTail != oldRoot ||
            !currentRoot || currentRoot == oldRoot || !newTail ||
            newTail == currentRoot || newTail == oldRoot || bound < 1)
            return nullptr;
        // Requiring EXACTLY one child rejects foreign leading/trailing
        // siblings and cycles; the game source itself is unchanged.
        return currentRoot->next_0 == newTail &&
               newTail->next_0 == nullptr ? newTail : nullptr;
    }

    namespace AbcGoalExperiment
    {
        struct Node { Node* next_0 = nullptr; };
        constexpr bool SingleChildOwnerProof() noexcept
        {
            Node oldRoot{}, newRoot{}, one{}, two{}, foreign{};
            newRoot.next_0 = &one;
            if (FirstVerifiedRebuiltEmptySingleChild(
                    &oldRoot, &oldRoot, true, &newRoot, &one, 2) != &one)
                return false;
            if (FirstVerifiedRebuiltEmptySingleChild(
                    &oldRoot, &oldRoot, false, &newRoot, &one, 2))
                return false;
            if (FirstVerifiedRebuiltEmptySingleChild(
                    &oldRoot, &foreign, true, &newRoot, &one, 2))
                return false;
            if (FirstVerifiedRebuiltEmptySingleChild(
                    &oldRoot, &oldRoot, true, &oldRoot, &one, 2))
                return false;
            if (FirstVerifiedRebuiltEmptySingleChild(
                    &oldRoot, &oldRoot, true, &newRoot, &one, 0))
                return false;
            one.next_0 = &two; // second sibling: no global GOAL adoption
            if (FirstVerifiedRebuiltEmptySingleChild(
                    &oldRoot, &oldRoot, true, &newRoot, &one, 2))
                return false;
            one.next_0 = nullptr;
            newRoot.next_0 = &foreign; // a foreign head: cannot prove owner
            foreign.next_0 = &one;
            if (FirstVerifiedRebuiltEmptySingleChild(
                    &oldRoot, &oldRoot, true, &newRoot, &one, 2))
                return false;
            one.next_0 = &one; // terminal tail must not be cyclic
            newRoot.next_0 = &one;
            if (FirstVerifiedRebuiltEmptySingleChild(
                    &oldRoot, &oldRoot, true, &newRoot, &one, 2))
                return false;
            return true;
        }
        static_assert(SingleChildOwnerProof(),
            "ABC C GOAL root-rebuild needs proven single terminal child");
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

        // Reject malformed snapshots and a reused "tail" that has become
        // an interior node in the live priority list. The real native
        // empty-list sentinel is root itself, NOT a null old-tail pointer.
        // All valid siblings remain tagged, including first-in-priority
        // +TIME, 6th/6, and GOAL draws.
        constexpr bool TerminalTailQueueOwnershipGuards() noexcept
        {
            Node root{}, old{}, first{}, last{}, later{}, cycle{};
            root.next_0 = &old;
            old.next_0 = &first;
            first.next_0 = &last;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &old, &last, 4) != &first)
                return false;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, static_cast<Node*>(nullptr), &last, 4))
                return false; // missing before-tail is NOT empty-list proof
            // An old tail may have been recycled or the new tail can be an
            // intermediate node while an unrelated producer extends the list.
            last.next_0 = &later;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &old, &last, 5))
                return false;
            // The purported new tail is a member of a ring, not a terminal.
            later.next_0 = &last;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &old, &later, 5))
                return false;
            // The original game may use root as the empty priority sentinel.
            root.next_0 = &first;
            first.next_0 = &last;
            last.next_0 = nullptr;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &root, &last, 3) != &first)
                return false;
            // Bound exhaustion must not turn a partial walk into a tag.
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &root, &last, 1))
                return false;
            // Cycle before the alleged tail also fails without touching it.
            first.next_0 = &cycle;
            cycle.next_0 = &first;
            if (FirstVerifiedAppendedNodeOnStableRoot(
                    &root, &root, &root, &last, 4))
                return false;
            return true;
        }
        static_assert(TerminalTailQueueOwnershipGuards(),
            "Only a bounded live terminal priority tail may acquire GPU eye ownership");

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