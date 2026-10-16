#pragma once

#include <cmath>
#include <cstdint>
#include "sprite_queue_tail_proof.hpp"

namespace OutRunVR::RankMarker
{
    // Apply the exact Calc3D2D subpixel remainder to every sprite produced
    // by the same vehicle-rank clip CALL. kind 0 is a SPRARGS position;
    // kind 1 is a transformed SPRARGS2 quad (translation lives in mtx_14).
    // Never edit an unknown node layout or publish a half-updated X/Y pair.
    template <typename SpriteNodeT>
    bool RestoreFraction(SpriteNodeT& node, float dx, float dy) noexcept
    {
        if (!std::isfinite(dx) || !std::isfinite(dy) ||
            std::fabs(dx) > 1.0f || std::fabs(dy) > 1.0f)
            return false;

        float* x = nullptr;
        float* y = nullptr;
        if (node.kind_C == 0u)
        {
            x = &node.args_10.float24;
            y = &node.args_10.float28;
        }
        else if (node.kind_C == 1u)
        {
            // D3DXVec4Transform uses row-vector matrices. _41/_42 move
            // every corner equally without modifying UV, depth or shape.
            x = &node.args2_58.mtx_14._41;
            y = &node.args2_58.mtx_14._42;
        }
        else
            return false;

        const float nextX = *x + dx;
        const float nextY = *y + dy;
        if (!std::isfinite(nextX) || !std::isfinite(nextY))
            return false;
        *x = nextX;
        *y = nextY;
        return true;
    }
    // The original 4th+ place rank clip CALL may rebuild its SpriteNode
    // priority list while producing several glyph siblings. Its captured
    // tail is borrowed, and can be detached/freed before the CALL returns.
    // Prove both old and new tails belong to the *current* queue first,
    // then apply the same native Calc3D2D fraction to every proven sibling.
    // The subsequent exact-source semantic registration uses the identical
    // queue proof; no foreign sprite receives a rank displacement.
    template <typename Node>
    unsigned RestoreAppendedRankFractions(Node* root, Node* oldTail,
        Node* newTail, unsigned bound, float dx, float dy) noexcept
    {
        Node* first = OutRunVR::SpriteQueue::FirstVerifiedAppendedNode(
            root, oldTail, newTail, bound);
        if (!first)
            return 0u;
        unsigned restored = 0;
        for (Node* node = first; node && bound != 0; --bound)
        {
            if (RestoreFraction(*node, dx, dy))
                ++restored;
            if (node == newTail)
                break;
            node = node->next_0;
        }
        return restored;
    }

}
