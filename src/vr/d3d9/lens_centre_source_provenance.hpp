#pragma once
#include <cstdint>

namespace OutRunVR::LensCentre
{
    struct RawWvpEvidence
    {
        std::uint64_t currentCall, writtenCall;
        std::uint64_t currentPoseEpoch, writtenPoseEpoch;
        std::uint64_t nextDraw, writtenDraw;
        std::uintptr_t shader, writtenShader;
        std::uint64_t shaderEpoch, writtenShaderEpoch;
        bool spatialCentreSource, exactCentreProducer, noQueue;
    };
    constexpr bool OwnsRawWvp(const RawWvpEvidence& e) noexcept
    {
        return e.currentCall != 0 && e.currentCall == e.writtenCall &&
            e.currentPoseEpoch != 0 &&
            e.currentPoseEpoch == e.writtenPoseEpoch &&
            e.nextDraw > e.writtenDraw &&
            e.nextDraw - e.writtenDraw <= 128u &&
            e.shader != 0 && e.shader == e.writtenShader &&
            e.shaderEpoch != 0 && e.shaderEpoch == e.writtenShaderEpoch &&
            e.spatialCentreSource && e.exactCentreProducer && e.noQueue;
    }
    // A central C993 sun must never be consumed by the historic verified
    // world shader / rebind path before its own game-upload proof is checked.
    // Missing source evidence is not permission to borrow a previous road WVP.
    enum class WorldRoute : std::uint8_t
    {
        HistoricalWorld,
        ExactCentreStereo,
        PreserveOriginal
    };
    constexpr WorldRoute SelectWorldRoute(bool exactCentre, bool rawOwned) noexcept
    {
        if (!exactCentre)
            return WorldRoute::HistoricalWorld;
        return rawOwned ? WorldRoute::ExactCentreStereo
                        : WorldRoute::PreserveOriginal;
    }
    // R33's early raster-guard bypass must never hand the exact central sun
    // to the historical R29 world transform. The stereo-ready path still
    // requires original-c64 proof and physical left/right submission.
    constexpr bool PreserveOriginalBeforeRasterResync(
        bool exactDirectCentre, bool rasterReady) noexcept
    {
        return exactDirectCentre && !rasterReady;
    }
    static_assert(PreserveOriginalBeforeRasterResync(true, false));
    static_assert(!PreserveOriginalBeforeRasterResync(true, true));
    static_assert(!PreserveOriginalBeforeRasterResync(false, false));

    // When R30 cannot prove the C993 game c64 or R33 cannot submit its
    // precise stereo path, preserve the original draw. Never retry a
    // generic world WVP route with possibly head-injected live constants.
    constexpr bool PreserveOriginalAtUpperDispatch(
        bool exactDirectCentre, bool provenCentreStereo,
        bool stereoHandled) noexcept
    {
        return exactDirectCentre && (!provenCentreStereo || !stereoHandled);
    }
    static_assert(PreserveOriginalAtUpperDispatch(true, false, false));
    static_assert(PreserveOriginalAtUpperDispatch(true, true, false));
    static_assert(!PreserveOriginalAtUpperDispatch(true, true, true));
    static_assert(!PreserveOriginalAtUpperDispatch(false, false, false));

    static_assert(SelectWorldRoute(true, true) == WorldRoute::ExactCentreStereo);
    static_assert(SelectWorldRoute(true, false) == WorldRoute::PreserveOriginal);
    static_assert(SelectWorldRoute(false, true) == WorldRoute::HistoricalWorld);
    static_assert(SelectWorldRoute(false, false) == WorldRoute::HistoricalWorld);

    // These constexpr positive/negative regressions compile in the actual
    // R26+HUD Windows game DLL, not merely in an unrelated test executable.
    static_assert(OwnsRawWvp({7,7,9,9,40,27,0x100,0x100,11,11,true,true,true}),
                  "this C993 central draw accepts only source-owned raw c64");
    static_assert(OwnsRawWvp({7,7,9,9,140,12,0x100,0x100,11,11,true,true,true}),
                  "same original centre call accepts bounded c64 batches");
    static_assert(!OwnsRawWvp({7,7,9,9,141,12,0x100,0x100,11,11,true,true,true}),
                  "draw age over 128 cannot reuse stale WVP");
    static_assert(!OwnsRawWvp({7,7,9,8,40,27,0x100,0x100,11,11,true,true,true}),
                  "pre-recenter c64 must never be reprojected using the new pose");
    static_assert(!OwnsRawWvp({7,7,0,0,40,27,0x100,0x100,11,11,true,true,true}),
                  "invalidated frame pose must not own the centre's raw WVP");
    static_assert(!OwnsRawWvp({7,6,9,9,40,27,0x100,0x100,11,11,true,true,true}),
                  "previous sun invocation is different source");
    static_assert(!OwnsRawWvp({0,0,9,9,40,27,0x100,0x100,11,11,true,true,true}),
                  "unowned source cannot enter centre transform");
    static_assert(!OwnsRawWvp({7,7,9,9,27,27,0x100,0x100,11,11,true,true,true}),
                  "raw write must precede actual draw");
    static_assert(!OwnsRawWvp({7,7,9,9,40,27,0x100,0x200,11,11,true,true,true}),
                  "shader switch must reject raw c64");
    static_assert(!OwnsRawWvp({7,7,9,9,40,27,0x100,0x100,11,12,true,true,true}),
                  "shader epoch switch must reject raw c64");
    static_assert(!OwnsRawWvp({7,7,9,9,40,27,0x100,0x100,11,11,false,true,true}),
                  "flat effect source cannot become a sun");
    static_assert(!OwnsRawWvp({7,7,9,9,40,27,0x100,0x100,11,11,true,false,true}),
                  "other alpha and CABE rings cannot become a sun");
    static_assert(!OwnsRawWvp({7,7,9,9,40,27,0x100,0x100,11,11,true,true,false}),
                  "queue node cannot steal direct C993 ownership");
}
