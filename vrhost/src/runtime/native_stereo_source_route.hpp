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

    // Before choosing the newest R41 DirectGPU frame or ACKing its older
    // siblings, prove the complete stereo frame/pose contract. An incomplete
    // newer Present must not suppress a complete earlier menu/race frame.
    [[nodiscard]] constexpr bool NativeDirectFrameSelectable(
        std::uint32_t frame, std::uint32_t generation,
        std::uint32_t slot, std::uint32_t ringSize,
        std::uint32_t poseSequence, std::uint32_t flags,
        std::uint32_t requiredFlags, bool stereoActive,
        bool presentInFlight, bool directTransport) noexcept
    {
        return frame != 0u && generation != 0u &&
            slot < ringSize && poseSequence != 0u &&
            stereoActive && !presentInFlight && directTransport &&
            (flags & requiredFlags) == requiredFlags;
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

    // A native DirectGPU-only game/menu frame may lack a desktop capture.
    // Flat XR projection and theater may use its two verified GPU hold eyes.
    // Classic mono/SBS requires a separately valid current desktop frame.
    [[nodiscard]] constexpr StereoSourceRoute ChooseFlatPresentationSource(
        StereoSourceRoute committedStereo, bool classicFrameReady) noexcept
    {
        if (committedStereo == StereoSourceRoute::DirectGpu)
            return StereoSourceRoute::DirectGpu;
        return classicFrameReady ? StereoSourceRoute::Sbs
                                 : StereoSourceRoute::None;
    }

    // Native eyes are full-frame, NOT halves of an SBS texture. Theater is
    // intentionally mono, while a world-locked menu retains independent eyes.
    [[nodiscard]] constexpr bool FlatPresentationNeedsSbsCrop(
        StereoSourceRoute selected, bool classicSourceIsSbs) noexcept
    {
        return selected == StereoSourceRoute::Sbs && classicSourceIsSbs;
    }

    // The source may change while GPU eyes are copied. Verify the second
    // seqlock snapshot matches the exact producer, texture pair AND eye pose
    // before pairing new game pixels with OpenXR views / acknowledging a slot.
    template <typename Frame>
    [[nodiscard]] bool SameStereoFrameIdentity(
        const Frame& before, const Frame& after) noexcept
    {
        if (before.magic != after.magic ||
            before.protocolVersion != after.protocolVersion ||
            before.structSize != after.structSize ||
            before.clientPid != after.clientPid ||
            before.state != after.state ||
            before.frameId != after.frameId ||
            before.sourcePoseSequence != after.sourcePoseSequence ||
            before.presentationMode != after.presentationMode ||
            before.flags != after.flags ||
            before.failureReason != after.failureReason ||
            before.backbufferWidth != after.backbufferWidth ||
            before.backbufferHeight != after.backbufferHeight ||
            before.presentQpc != after.presentQpc)
            return false;
        // Frame.v2 reserved[0..6]: DirectGPU handles, extent, format,
        // generation, slot; [7..9]: producer build identity. An SBS -> GPU
        // transition must never inherit the previous frame's eye textures.
        for (std::uint32_t i = 0; i < 10u; ++i)
            if (before.reserved[i] != after.reserved[i]) return false;
        for (std::uint32_t eye = 0; eye < 2u; ++eye)
        {
            for (std::uint32_t i = 0; i < 4u; ++i)
                if (before.eye[eye].orientation[i] != after.eye[eye].orientation[i])
                    return false;
            for (std::uint32_t i = 0; i < 3u; ++i)
                if (before.eye[eye].position[i] != after.eye[eye].position[i])
                    return false;
            const auto& a = before.eye[eye].fov;
            const auto& b = after.eye[eye].fov;
            if (a.angleLeft != b.angleLeft || a.angleRight != b.angleRight ||
                a.angleUp != b.angleUp || a.angleDown != b.angleDown)
                return false;
        }
        return true;
    }
}
