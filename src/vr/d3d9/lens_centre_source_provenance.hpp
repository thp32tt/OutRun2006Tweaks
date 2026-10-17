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
    // R33 prepares the left-eye C993 c64 and then invokes the original
    // game draw before dispatching the right eye. A nested game draw may
    // replace the exact producer, physical draw or bound shader in between.
    // Both eyes must belong to ONE original physical sun submission.
    struct StereoDrawSource
    {
        std::uint64_t centreCall = 0;
        std::uint64_t drawSerial = 0;
        std::uint64_t shaderEpoch = 0;
        std::uint32_t poseSequence = 0;
        std::uintptr_t shader = 0;
        bool exactDirectCentre = false;
    };
    constexpr bool SameStereoDrawSource(
        const StereoDrawSource& before,
        const StereoDrawSource& after) noexcept
    {
        return before.exactDirectCentre && after.exactDirectCentre &&
            before.centreCall != 0 &&
            before.centreCall == after.centreCall &&
            before.drawSerial != 0 &&
            before.drawSerial == after.drawSerial &&
            before.poseSequence != 0 &&
            before.poseSequence == after.poseSequence &&
            before.shader != 0 && before.shader == after.shader &&
            before.shaderEpoch != 0 &&
            before.shaderEpoch == after.shaderEpoch;
    }
    // R84 C993: left native Draw can reenter and replace original-game
    // c64 even when the exact producer, shader, pose and draw survive.
    // Preserve one raw GPU upload generation for BOTH physical eye draws.
    struct RawStereoSource
    {
        std::uint64_t writeSerial = 0;
        std::uint64_t writtenDraw = 0;
        std::uint64_t centreCall = 0;
        std::uint64_t writtenCentreCall = 0;
        std::uint64_t poseEpoch = 0;
        std::uint64_t writtenPoseEpoch = 0;
        std::uintptr_t shader = 0;
        std::uint64_t shaderEpoch = 0;
        bool exactDirectRaw = false;
    };
    constexpr bool SameRawStereoSource(
        const RawStereoSource& before, const RawStereoSource& after) noexcept
    {
        return before.exactDirectRaw && after.exactDirectRaw &&
            before.writeSerial != 0 &&
            before.writeSerial == after.writeSerial &&
            before.writtenDraw == after.writtenDraw &&
            before.centreCall != 0 &&
            before.centreCall == before.writtenCentreCall &&
            before.centreCall == after.centreCall &&
            after.centreCall == after.writtenCentreCall &&
            before.poseEpoch != 0 &&
            before.poseEpoch == before.writtenPoseEpoch &&
            before.poseEpoch == after.poseEpoch &&
            after.poseEpoch == after.writtenPoseEpoch &&
            before.shader != 0 && before.shader == after.shader &&
            before.shaderEpoch != 0 &&
            before.shaderEpoch == after.shaderEpoch;
    }
    static_assert(SameRawStereoSource(
        {21, 11, 7, 7, 9, 9, 0x100, 3, true},
        {21, 11, 7, 7, 9, 9, 0x100, 3, true}));
    static_assert(!SameRawStereoSource(
        {21, 11, 7, 7, 9, 9, 0x100, 3, true},
        {22, 11, 7, 7, 9, 9, 0x100, 3, true}));
    static_assert(!SameRawStereoSource(
        {21, 11, 7, 7, 9, 9, 0x100, 3, true},
        {21, 11, 7, 7, 9, 8, 0x100, 3, true}));

    static_assert(SameStereoDrawSource(
        {7, 30, 11, 9, 0x100, true}, {7, 30, 11, 9, 0x100, true}));
    static_assert(!SameStereoDrawSource(
        {7, 30, 11, 9, 0x100, true}, {7, 31, 11, 9, 0x100, true}));
    static_assert(!SameStereoDrawSource(
        {7, 30, 11, 9, 0x100, true}, {7, 30, 12, 9, 0x100, true}));
    static_assert(!SameStereoDrawSource(
        {7, 30, 11, 9, 0x100, true}, {7, 30, 11, 9, 0x100, false}));

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
