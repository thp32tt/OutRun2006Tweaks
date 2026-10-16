#pragma once
#include <cstdint>
#include "render_semantics.hpp"

namespace OutRunVR::SceneEffectWvp
{
    // Same shader, pose and nearby draw is insufficient: a previous world
    // object may have written c64 just before a different SceneEffect.
    struct Evidence
    {
        GameSemantic::RenderScope currentScope, writtenScope;
        GameSemantic::ProducerToken currentProducer, writtenProducer;
        bool queued;
        const void* currentQueueNode;
        const void* writtenQueueNode;
        std::uint64_t currentQueueEpoch, writtenQueueEpoch;
        std::uint64_t currentPoseEpoch, writtenPoseEpoch;
        std::uintptr_t currentShader, writtenShader;
        std::uint64_t currentShaderEpoch, writtenShaderEpoch;
        std::uint64_t nextDrawSerial, writtenDrawSerial;
    };

    constexpr bool OwnsOriginalWorldWvp(const Evidence& e) noexcept
    {
        using namespace GameSemantic;
        if (e.currentScope != RenderScope::SceneEffect ||
            e.writtenScope != RenderScope::SceneEffect ||
            e.currentProducer != e.writtenProducer ||
            !e.currentPoseEpoch || e.currentPoseEpoch != e.writtenPoseEpoch ||
            !e.currentShader || e.currentShader != e.writtenShader ||
            !e.currentShaderEpoch || e.currentShaderEpoch != e.writtenShaderEpoch ||
            !e.nextDrawSerial || e.nextDrawSerial <= e.writtenDrawSerial ||
            e.nextDrawSerial - e.writtenDrawSerial > 12u)
            return false;
        if (e.queued)
            return e.currentQueueNode != nullptr &&
                e.currentQueueNode == e.writtenQueueNode &&
                e.currentQueueEpoch != 0 &&
                e.currentQueueEpoch == e.writtenQueueEpoch;
        // A numeric queue epoch can survive queue teardown. Direct call
        // identity depends on BOTH queue node pointers being absent.
        return e.currentQueueNode == nullptr &&
            e.writtenQueueNode == nullptr;
    }
}
