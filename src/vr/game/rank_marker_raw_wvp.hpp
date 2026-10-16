#pragma once
#include <cstdint>

// The original game-uploaded c64 must own the *same* rank SpriteNode,
// shader epoch, pose and draw before it can replace a possibly stereo-
// injected live GPU c64. Unproved sources keep the existing R84 route.
namespace OutRunVR::RankMarker
{
    struct RawWvpEvidence
    {
        std::uint64_t currentPose, writtenPose;
        std::uint64_t nextDraw, writtenDraw;
        std::uintptr_t currentShader, writtenShader;
        std::uint64_t currentShaderEpoch, writtenShaderEpoch;
        bool exactRank, exactUploadedRank, sameQueueOwner;
    };
    constexpr bool OwnsRawGameWvp(const RawWvpEvidence& e) noexcept
    {
        return e.exactRank && e.exactUploadedRank && e.sameQueueOwner &&
            e.currentPose != 0 && e.currentPose == e.writtenPose &&
            e.nextDraw > e.writtenDraw &&
            e.nextDraw - e.writtenDraw <= 12u &&
            e.currentShader != 0 &&
            e.currentShader == e.writtenShader &&
            e.currentShaderEpoch != 0 &&
            e.currentShaderEpoch == e.writtenShaderEpoch;
    }
    static_assert(OwnsRawGameWvp({5,5,101,99,0x100,0x100,3,3,true,true,true}));
    static_assert(!OwnsRawGameWvp({5,4,101,99,0x100,0x100,3,3,true,true,true}));
    static_assert(!OwnsRawGameWvp({5,5,113,100,0x100,0x100,3,3,true,true,true}));
    static_assert(!OwnsRawGameWvp({5,5,101,99,0x100,0x200,3,3,true,true,true}));
    static_assert(!OwnsRawGameWvp({5,5,101,99,0x100,0x100,3,4,true,true,true}));
    static_assert(!OwnsRawGameWvp({5,5,101,99,0x100,0x100,3,3,true,true,false}));
    static_assert(!OwnsRawGameWvp({5,5,101,99,0x100,0x100,3,3,false,true,true}));
    static_assert(!OwnsRawGameWvp({5,5,101,99,0x100,0x100,3,3,true,false,true}));
}
