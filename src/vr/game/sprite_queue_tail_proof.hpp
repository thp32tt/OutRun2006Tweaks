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
}
