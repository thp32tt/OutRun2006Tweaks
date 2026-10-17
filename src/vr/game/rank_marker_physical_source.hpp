#pragma once
#include "render_semantics.hpp"
#include <cmath>
#include <cstdint>

// Physical GPU left/right rank transaction. A rank SpriteNode's projected
// Calc3D2D anchor is a live queue cursor; native Draw can re-enter the game's
// producer or shader hook. A prepared right eye may only reuse the exact
// source that was current when the left eye was submitted.
namespace OutRunVR::RankMarker
{
    struct PhysicalRankSource
    {
        GameSemantic::RenderScope scope;
        GameSemantic::ProducerToken producer;
        bool queued;
        const void* queueNode;
        std::uint64_t queueEpoch;
        GameSemantic::ProjectedMarkerInfo marker;
        std::uint64_t poseEpoch;
        std::uintptr_t shader;
        std::uint64_t shaderEpoch;
    };

    inline bool ValidRankSource(const PhysicalRankSource& s) noexcept
    {
        const bool rankProducer =
            s.producer == GameSemantic::ProducerToken::RankMarkerSprani ||
            s.producer == GameSemantic::ProducerToken::RankMarkerClipSprite ||
            s.producer == GameSemantic::ProducerToken::RivalMarkerSprani;
        return s.scope == GameSemantic::RenderScope::ProjectedWorldMarker2D &&
            rankProducer && s.marker.valid &&
            std::isfinite(s.marker.viewX) &&
            std::isfinite(s.marker.viewY) &&
            std::isfinite(s.marker.viewZ) &&
            s.poseEpoch != 0 &&
            (s.shader == 0 || s.shaderEpoch != 0) &&
            (s.queued ? (s.queueNode && s.queueEpoch != 0) :
                        (!s.queueNode && s.queueEpoch == 0));
    }

    inline bool SameRankSourceAfterNativeLeft(
        const PhysicalRankSource& before,
        const PhysicalRankSource& after) noexcept
    {
        return ValidRankSource(before) && ValidRankSource(after) &&
            before.scope == after.scope &&
            before.producer == after.producer &&
            before.queued == after.queued &&
            before.queueNode == after.queueNode &&
            before.queueEpoch == after.queueEpoch &&
            before.marker.viewX == after.marker.viewX &&
            before.marker.viewY == after.marker.viewY &&
            before.marker.viewZ == after.marker.viewZ &&
            before.poseEpoch == after.poseEpoch &&
            before.shader == after.shader &&
            before.shaderEpoch == after.shaderEpoch;
    }
}
