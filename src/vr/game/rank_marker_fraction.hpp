#pragma once

#include <cmath>
#include <cstdint>
#include "sprite_queue_tail_proof.hpp"

namespace OutRunVR::RankMarker
{
    // Original sub_4BAD20 already chooses a physical point one game unit
    // above the target car: car-local (0,1,0) is transformed to camera/view
    // space and then projected by Calc3D2D. Only after that 3D projection
    // does the PC HUD apply a common -32 pixel Y lift in 640x480 space.
    // In HMD stereo that fixed angular lift makes the marker appear detached
    // from its car. Cancel only that common desktop lift for an exact
    // projected vehicle-rank owner; preserve every per-sprite offset.
    inline constexpr int VehicleAnchorDesktopLiftPixels(
        bool vrEnabled, bool projectedVehicleRank) noexcept
    {
        return vrEnabled && projectedVehicleRank ? 32 : 0;
    }

    static_assert(VehicleAnchorDesktopLiftPixels(true, true) == 32);
    static_assert(VehicleAnchorDesktopLiftPixels(false, true) == 0);
    static_assert(VehicleAnchorDesktopLiftPixels(true, false) == 0);

    // Apply the exact Calc3D2D subpixel remainder to every sprite produced
    // by the same vehicle-rank clip CALL. kind 0 is a SPRARGS position;
    // kind 1 is a transformed SPRARGS2 quad (translation lives in mtx_14).
    // Never edit an unknown node layout or publish a half-updated X/Y pair.
    // Preflight original rank kind-0 sprite positions and kind-1 transform
    // translations without mutating either coordinate. A multi-glyph rank
    // must never update its first child if a later sibling has invalid data.
    template <typename SpriteNodeT>
    bool FractionCandidate(const SpriteNodeT& node, float dx, float dy,
        float& candidateX, float& candidateY) noexcept
    {
        if (!std::isfinite(dx) || !std::isfinite(dy) ||
            std::fabs(dx) > 1.0f || std::fabs(dy) > 1.0f)
            return false;

        const float* x = nullptr;
        const float* y = nullptr;
        if (node.kind_C == 0u)
        {
            x = &node.args_10.float24;
            y = &node.args_10.float28;
        }
        else if (node.kind_C == 1u)
        {
            // D3DX row-vector sprite matrices carry translation in _41/_42;
            // UV, animation, shape and depth are deliberately unchanged.
            x = &node.args2_58.mtx_14._41;
            y = &node.args2_58.mtx_14._42;
        }
        else
            return false;

        const float nextX = *x + dx;
        const float nextY = *y + dy;
        if (!std::isfinite(nextX) || !std::isfinite(nextY))
            return false;
        candidateX = nextX;
        candidateY = nextY;
        return true;
    }

    template <typename SpriteNodeT>
    bool RestoreFraction(SpriteNodeT& node, float dx, float dy) noexcept
    {
        float x = 0.0f, y = 0.0f;
        if (!FractionCandidate(node, dx, dy, x, y))
            return false;
        if (node.kind_C == 0u)
        {
            node.args_10.float24 = x;
            node.args_10.float28 = y;
        }
        else
        {
            node.args2_58.mtx_14._41 = x;
            node.args2_58.mtx_14._42 = y;
        }
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
        // The original clip producer emits a logical rank marker containing
        // multiple animated/number siblings. Partial fraction repair makes
        // those siblings detach from one vehicle in different eyes. First
        // validate EVERY bounded live sibling, then apply the same native
        // Calc3D2D fraction to all of them. No queue node is modified when
        // an unexpected kind, NaN or truncated chain is encountered.
        unsigned count = 0;
        bool reachedTail = false;
        for (Node* node = first; node && count < bound; node = node->next_0)
        {
            float x = 0.0f, y = 0.0f;
            if (!FractionCandidate(*node, dx, dy, x, y))
                return 0u;
            ++count;
            if (node == newTail)
            {
                reachedTail = true;
                break;
            }
        }
        if (!reachedTail)
            return 0u;

        Node* node = first;
        for (unsigned i = 0; i < count; ++i)
        {
            // All children passed the exact same preflight above. The native
            // producer/queue is synchronous; no other callback mutates the
            // list between these two bounded passes.
            RestoreFraction(*node, dx, dy);
            node = node->next_0;
        }
        return count;
    }

    // An original vehicle rank producer may replace an entire priority
    // sentinel and later reattach the exact same old tail to that new root.
    // Current-root reachability alone cannot establish producer ownership.
    // Keep both original and live root identity before touching any child's
    // XY position; the downstream semantic tagger uses the same fence.
    template <typename Node>
    unsigned RestoreAppendedRankFractions(
        Node* sourceRoot, Node* currentRoot, Node* oldTail,
        Node* newTail, unsigned bound, float dx, float dy) noexcept
    {
        if (!sourceRoot || sourceRoot != currentRoot)
            return 0u;
        return RestoreAppendedRankFractions(
            currentRoot, oldTail, newTail, bound, dx, dy);
    }

}
