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
    }

}