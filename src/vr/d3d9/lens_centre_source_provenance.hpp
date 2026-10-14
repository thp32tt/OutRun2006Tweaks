#pragma once
#include <cstdint>

namespace OutRunVR::LensCentre
{
    struct RawWvpEvidence
    {
        std::uint64_t currentCall, writtenCall;
        std::uint64_t nextDraw, writtenDraw;
        std::uintptr_t shader, writtenShader;
        std::uint64_t shaderEpoch, writtenShaderEpoch;
        bool spatialCentreSource, exactCentreProducer, noQueue;
    };
    constexpr bool OwnsRawWvp(const RawWvpEvidence& e) noexcept
    {
        return e.currentCall != 0 && e.currentCall == e.writtenCall &&
            e.nextDraw > e.writtenDraw &&
            e.nextDraw - e.writtenDraw <= 128u &&
            e.shader != 0 && e.shader == e.writtenShader &&
            e.shaderEpoch != 0 && e.shaderEpoch == e.writtenShaderEpoch &&
            e.spatialCentreSource && e.exactCentreProducer && e.noQueue;
    }
    // These constexpr positive/negative regressions compile in the actual
    // R26+HUD Windows game DLL, not merely in an unrelated test executable.
    static_assert(OwnsRawWvp({7,7,40,27,0x100,0x100,11,11,true,true,true}),
                  "this C993 central draw accepts only source-owned raw c64");
    static_assert(OwnsRawWvp({7,7,140,12,0x100,0x100,11,11,true,true,true}),
                  "same original centre call accepts bounded c64 batches");
    static_assert(!OwnsRawWvp({7,7,141,12,0x100,0x100,11,11,true,true,true}),
                  "draw age over 128 cannot reuse stale WVP");
    static_assert(!OwnsRawWvp({7,6,40,27,0x100,0x100,11,11,true,true,true}),
                  "previous sun invocation is different source");
    static_assert(!OwnsRawWvp({0,0,40,27,0x100,0x100,11,11,true,true,true}),
                  "unowned source cannot enter centre transform");
    static_assert(!OwnsRawWvp({7,7,27,27,0x100,0x100,11,11,true,true,true}),
                  "raw write must precede actual draw");
    static_assert(!OwnsRawWvp({7,7,40,27,0x100,0x200,11,11,true,true,true}),
                  "shader switch must reject raw c64");
    static_assert(!OwnsRawWvp({7,7,40,27,0x100,0x100,11,12,true,true,true}),
                  "shader epoch switch must reject raw c64");
    static_assert(!OwnsRawWvp({7,7,40,27,0x100,0x100,11,11,false,true,true}),
                  "flat effect source cannot become a sun");
    static_assert(!OwnsRawWvp({7,7,40,27,0x100,0x100,11,11,true,false,true}),
                  "other alpha and CABE rings cannot become a sun");
    static_assert(!OwnsRawWvp({7,7,40,27,0x100,0x100,11,11,true,true,false}),
                  "queue node cannot steal direct C993 ownership");
}
