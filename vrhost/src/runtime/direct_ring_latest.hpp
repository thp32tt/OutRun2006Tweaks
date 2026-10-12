#pragma once
#include <cstddef>
#include <cstdint>

// R41 newest-frame-wins: find the current producer generation and its newest
// eligible unconsumed DirectGPU frame in ONE ring scan. The newest *basic*
// frame determines the generation even when it cannot be selected (e.g. a
// slot is invalid or its frame ID was already presented). Never select a
// stale old-generation candidate merely because it was encountered first.
namespace OutRunVrDirectRingLatest
{
    inline constexpr std::size_t NoIndex = static_cast<std::size_t>(-1);
    struct Selection
    {
        std::size_t index = NoIndex;
        std::uint32_t generation = 0;
        bool haveGeneration = false;
    };

    template<class Frame, class IsBasic, class IsEligible,
        class Generation, class FrameBefore>
    Selection Pick(const Frame* frames, std::size_t count, IsBasic isBasic,
        IsEligible isEligible, Generation generationOf,
        FrameBefore before) noexcept
    {
        Selection result{};
        std::uint32_t newestFrame = 0;
        for (std::size_t i = 0; i < count; ++i)
        {
            const auto& frame = frames[i];
            if (!isBasic(frame))
                continue;
            const std::uint32_t generation = generationOf(frame);
            if (!result.haveGeneration || before(newestFrame, frame.frameId))
            {
                newestFrame = frame.frameId;
                if (!result.haveGeneration || result.generation != generation)
                {
                    result.index = NoIndex;
                    // A newer frame can introduce a generation whose older,
                    // eligible frame appeared earlier in ring order. Backfill
                    // only on the rare generation change, keeping the steady
                    // generation's hot path single-pass.
                    for (std::size_t prior = 0; prior < i; ++prior)
                    {
                        const auto& earlier = frames[prior];
                        if (isBasic(earlier) &&
                            generationOf(earlier) == generation &&
                            isEligible(earlier) &&
                            (result.index == NoIndex ||
                             before(frames[result.index].frameId, earlier.frameId)))
                            result.index = prior;
                    }
                }
                result.generation = generation;
                result.haveGeneration = true;
            }
            // Candidates encountered before the latest generation was known
            // are discarded on a generation switch; later matching slots can
            // still supply the newest eligible frame of that generation.
            if (generation == result.generation && isEligible(frame) &&
                (result.index == NoIndex ||
                 before(frames[result.index].frameId, frame.frameId)))
                result.index = i;
        }
        return result;
    }
}
