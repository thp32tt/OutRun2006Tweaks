#pragma once
// A single native offscreen Clear can modify the exact main depth resource
// even though RT0 is not the stereo backbuffer. Pure policy, no GPU queries.
namespace OutRunVR::OffscreenDepthClearLineage
{
    struct Decision
    {
        bool mainContentChanged = false;
        bool invalidateDepth = false;
        bool invalidateStencil = false;
    };

    constexpr Decision Decide(bool originalSucceeded, bool stereoWanted,
        bool offscreenTarget, bool mainStereoSeeded, bool exactMainDepthBound,
        bool clearDepth, bool clearStencil, bool mainHasStencil,
        bool rightDepthSynchronized, bool rightStencilSynchronized) noexcept
    {
        const bool validOwner = originalSucceeded && stereoWanted &&
            offscreenTarget && mainStereoSeeded && exactMainDepthBound;
        const bool depthWritten = validOwner && clearDepth;
        const bool stencilWritten = validOwner && clearStencil && mainHasStencil;
        return {depthWritten || stencilWritten,
            depthWritten && rightDepthSynchronized,
            stencilWritten && rightStencilSynchronized};
    }

    static_assert(Decide(true,true,true,true,true,true,false,true,true,true).invalidateDepth);
    static_assert(!Decide(true,true,true,true,true,true,false,true,true,true).invalidateStencil);
    static_assert(Decide(true,true,true,true,true,false,true,true,true,true).invalidateStencil);
    static_assert(!Decide(true,true,true,true,true,false,true,false,true,true).mainContentChanged);
    static_assert(!Decide(false,true,true,true,true,true,true,true,true,true).mainContentChanged);
    static_assert(!Decide(true,false,true,true,true,true,true,true,true,true).mainContentChanged);
    static_assert(!Decide(true,true,false,true,true,true,true,true,true,true).mainContentChanged);
    static_assert(!Decide(true,true,true,false,true,true,true,true,true,true).mainContentChanged);
    static_assert(!Decide(true,true,true,true,false,true,true,true,true,true).mainContentChanged);
    static_assert(!Decide(true,true,true,true,true,false,false,true,true,true).mainContentChanged);
    // Already-unsynchronized right-eye content must remain unsynchronized,
    // but successful native main-depth writes still advance the depth serial.
    static_assert(Decide(true,true,true,true,true,true,false,true,false,false).mainContentChanged);
    static_assert(!Decide(true,true,true,true,true,true,false,true,false,false).invalidateDepth);
}
