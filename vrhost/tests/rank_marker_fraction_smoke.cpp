#include "vr/game/rank_marker_fraction.hpp"
#include <cstdlib>
#include <cmath>
#include <cstdint>
#include <limits>

// A Release host build defines NDEBUG; ordinary assert() would silently
// erase the entire positive/negative visual-source regression matrix.
#define RANK_CHECK(condition) do { if (!(condition)) std::abort(); } while (false)

struct MockNode
{
    MockNode* next_0 = nullptr;
    std::uint32_t kind_C = 0;
    struct { float float24 = 0, float28 = 0; } args_10;
    struct { struct { float _11 = 2, _12 = 0, _21 = 0, _22 = 3, _41 = 0, _42 = 0; } mtx_14; } args2_58;
};

int main()
{
    using OutRunVR::RankMarker::RestoreFraction;
    MockNode clip{};
    clip.args_10.float24 = 100.0f;
    clip.args_10.float28 = 200.0f;
    RANK_CHECK(RestoreFraction(clip, 0.375f, -0.25f));
    RANK_CHECK(clip.args_10.float24 == 100.375f && clip.args_10.float28 == 199.75f);

    MockNode quad{};
    quad.kind_C = 1;
    quad.args2_58.mtx_14._41 = 50.0f;
    quad.args2_58.mtx_14._42 = 60.0f;
    const float beforeX = 4.0f * quad.args2_58.mtx_14._11 + quad.args2_58.mtx_14._41;
    const float beforeY = 5.0f * quad.args2_58.mtx_14._22 + quad.args2_58.mtx_14._42;
    RANK_CHECK(RestoreFraction(quad, 0.5f, -0.5f));
    RANK_CHECK(4.0f * quad.args2_58.mtx_14._11 + quad.args2_58.mtx_14._41 == beforeX + 0.5f);
    RANK_CHECK(5.0f * quad.args2_58.mtx_14._22 + quad.args2_58.mtx_14._42 == beforeY - 0.5f);
    RANK_CHECK(quad.args2_58.mtx_14._11 == 2.0f && quad.args2_58.mtx_14._22 == 3.0f);

    const float oldX = quad.args2_58.mtx_14._41, oldY = quad.args2_58.mtx_14._42;
    const auto infinity = std::numeric_limits<float>::infinity();
    RANK_CHECK(!RestoreFraction(quad, infinity, 0.5f));
    RANK_CHECK(!RestoreFraction(quad, 1.125f, 0.0f));
    RANK_CHECK(quad.args2_58.mtx_14._41 == oldX && quad.args2_58.mtx_14._42 == oldY);
    quad.kind_C = 9;
    RANK_CHECK(!RestoreFraction(quad, 0.5f, 0.5f));
    quad.kind_C = 1;
    quad.args2_58.mtx_14._41 = infinity;
    RANK_CHECK(!RestoreFraction(quad, 0.25f, 0.25f));
    RANK_CHECK(quad.args2_58.mtx_14._42 == oldY);

    // Production exact-rank sibling path, not a stand-in traversal: a
    // source CALL can replace the priority queue and free its prior tail.
    // All admitted kind-0/1 children must retain their car-relative
    // fractional Calc3D2D position before the stereo queue replays them.
    using OutRunVR::RankMarker::RestoreAppendedRankFractions;
    MockNode root{}, old{}, first{}, second{}, stale{}, foreign{};
    first.args_10.float24 = 100.0f;
    first.args_10.float28 = 200.0f;
    second.kind_C = 1;
    second.args2_58.mtx_14._41 = 50.0f;
    second.args2_58.mtx_14._42 = 60.0f;
    root.next_0 = &old;
    old.next_0 = &first;
    first.next_0 = &second;
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &old, &second, 4, 0.375f, -0.25f) == 2u);
    RANK_CHECK(first.args_10.float24 == 100.375f &&
           first.args_10.float28 == 199.75f);
    RANK_CHECK(second.args2_58.mtx_14._41 == 50.375f &&
           second.args2_58.mtx_14._42 == 59.75f);
    // Detached tail: its next_0 may be stale or reused by a foreign
    // producer. The current root is authoritative; DO NOT dereference old.
    stale.next_0 = &foreign;
    root.next_0 = &first;
    const float savedFirstX = first.args_10.float24;
    const float savedSecondX = second.args2_58.mtx_14._41;
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &stale, &second, 3, 0.5f, 0.5f) == 0u);
    RANK_CHECK(first.args_10.float24 == savedFirstX &&
           second.args2_58.mtx_14._41 == savedSecondX &&
           foreign.args_10.float24 == 0.0f);
    // A foreign/new tail, exhausted traversal bound or no newly
    // appended nodes must not displace any existing rank sprite.
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &first, &foreign, 4, 0.5f, 0.5f) == 0u);
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &first, &second, 1, 0.5f, 0.5f) == 0u);
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &second, &second, 3, 0.5f, 0.5f) == 0u);
    RANK_CHECK(first.args_10.float24 == savedFirstX &&
           second.args2_58.mtx_14._41 == savedSecondX);
    // Only the new child receives an offset when the old tail remains
    // live; malformed fraction/kind preserves the original geometry.
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &first, &second, 3, 0.125f, 0.25f) == 1u);
    RANK_CHECK(first.args_10.float24 == savedFirstX);
    RANK_CHECK(second.args2_58.mtx_14._41 == savedSecondX + 0.125f);
    const float savedFinalX = second.args2_58.mtx_14._41;
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &first, &second, 3, infinity, 0.25f) == 0u);
    second.kind_C = 99;
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &first, &second, 3, 0.25f, 0.25f) == 0u);
    RANK_CHECK(second.args2_58.mtx_14._41 == savedFinalX);
    // Same pointer identities can be reattached to a different sentinel
    // after native put_clip_sprite replaces its list. Old/new tails remain
    // reachable, yet all children belong to the foreign priority owner.
    MockNode foreignRoot{};
    first.next_0 = &second;
    foreignRoot.next_0 = &first;
    const float frozenFirstX = first.args_10.float24;
    const float frozenSecondX = second.args2_58.mtx_14._41;
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &foreignRoot, &first, &second, 4, 0.25f, -0.25f) == 0u);
    RANK_CHECK(RestoreAppendedRankFractions(
        static_cast<MockNode*>(nullptr), &foreignRoot,
        &first, &second, 4, 0.25f, -0.25f) == 0u);
    RANK_CHECK(first.args_10.float24 == frozenFirstX &&
        second.args2_58.mtx_14._41 == frozenSecondX);
    // Stable root + still-linked old tail DOES admit only the new child.
    RANK_CHECK(RestoreAppendedRankFractions(
        &foreignRoot, &foreignRoot, &first, &second,
        4, 0.125f, -0.125f) == 1u);
    RANK_CHECK(first.args_10.float24 == frozenFirstX &&
        second.args2_58.mtx_14._41 == frozenSecondX + 0.125f);
    // Cycling detached queue and malformed empty source remain fail closed.
    first.next_0 = &first;
    RANK_CHECK(RestoreAppendedRankFractions(
        &root, &old, &second, 4, 0.25f, 0.25f) == 0u);
    return 0;
}
