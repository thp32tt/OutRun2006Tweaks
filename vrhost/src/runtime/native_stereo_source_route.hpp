#pragma once
#include <cstdint>

namespace OutRunVrNativeEyePair
{
    // Transport reset may restart native frame IDs while older slots remain
    // readable. The game Present timestamp orders distinct generations;
    // numeric frame IDs only order frames within one generation.
    [[nodiscard]] constexpr bool NativeFrameIdNewer(
        std::uint32_t older, std::uint32_t newer) noexcept
    {
        return newer != older &&
            static_cast<std::int32_t>(newer - older) > 0;
    }

    [[nodiscard]] constexpr bool PreferNativeDirectFrame(
        std::uint32_t candidateGeneration, std::uint32_t candidateFrame,
        std::int64_t candidatePresentQpc,
        std::uint32_t currentGeneration, std::uint32_t currentFrame,
        std::int64_t currentPresentQpc) noexcept
    {
        if (!candidateGeneration || !candidateFrame) return false;
        if (!currentGeneration || !currentFrame) return true;
        // A reset creates a new generation with its own frame counter.
        // Within one generation the producer's frame order is authoritative:
        // delayed or noisy Present QPC samples must not roll back that order.
        if (candidateGeneration == currentGeneration)
            return NativeFrameIdNewer(currentFrame, candidateFrame);

        // Only independent generations need wall-clock ordering. An absent
        // timestamp cannot displace a known Present, and equal timestamps
        // cannot establish which transport generation is newer.
        if (candidatePresentQpc <= 0)
            return false;
        if (currentPresentQpc <= 0)
            return true;
        return candidatePresentQpc > currentPresentQpc;
    }

    [[nodiscard]] constexpr bool DirectFrameAlreadyProcessed(
        std::uint32_t generation, std::uint32_t frame,
        std::uint32_t consumedGeneration, std::uint32_t consumedFrame) noexcept
    {
        return generation != 0 && generation == consumedGeneration &&
            consumedFrame != 0 &&
            !NativeFrameIdNewer(consumedFrame, frame);
    }

    // Source routing is a property of the LAST successfully committed frame,
    // not the presence of cached shared handles or a prior stereo snapshot.
    enum class StereoSourceRoute : std::uint8_t { None, DirectGpu, Sbs };

    [[nodiscard]] constexpr StereoSourceRoute ChooseStereoSource(
        bool directCommitted, bool leftEyeReady, bool rightEyeReady,
        bool sbsCommitted, bool sbsViewReady) noexcept
    {
        if (directCommitted && leftEyeReady && rightEyeReady)
            return StereoSourceRoute::DirectGpu;
        if (sbsCommitted && sbsViewReady)
            return StereoSourceRoute::Sbs;
        return StereoSourceRoute::None;
    }
}
