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
        if (!root || !newTail || newTail == oldTail || bound == 0)
            return nullptr;
        Node* first = oldTail ? nullptr : root->next_0;
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
