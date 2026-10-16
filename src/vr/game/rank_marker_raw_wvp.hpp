#pragma once
#include <cstdint>
#include <cmath>
#include <cstring>

// The original game-uploaded c64 must own the *same* rank SpriteNode,
// shader epoch, pose and draw before it can replace a possibly stereo-
// injected live GPU c64. Unproved sources keep ONE native original draw;
// never treat a head-injected live GPU constant as a stock rank WVP.
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
    // R84 shader rank stereo MUST consume a proved original game c64.
    // Prevalidate all rows and publish atomically; missing proof or malformed
    // matrices must not replace the old live GPU c64 or submit either eye.
    inline bool SelectOriginalRankWvpForStereo(bool owned,
        const float (&rawGameWvp)[16], float (&selected)[16]) noexcept
    {
        if (!owned)
            return false;
        for (float value : rawGameWvp)
            if (!std::isfinite(value))
                return false;
        std::memcpy(selected, rawGameWvp, sizeof(selected));
        return true;
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
