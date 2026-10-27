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
        // Reentrant native left Draw may select the same node under another
        // draw or FVF. RIGHT must retain the original physical command.
        std::uint64_t drawSerial;
        std::uint32_t fvf;
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
            s.poseEpoch != 0 && s.drawSerial != 0 &&
            (s.shader == 0 || s.shaderEpoch != 0) &&
            (s.queued ? (s.queueNode && s.queueEpoch != 0) :
                        (!s.queueNode && s.queueEpoch == 0));
    }


    // The original GPU c64 admitted by R30 must belong to the same car,
    // SpriteNode, pose and shader at each R33 physical eye submission.
    // Native Draw and right-eye state setters may synchronously reenter a
    // different game c64 producer without changing the projected marker.
    struct OriginalRankWvpSource
    {
        std::uint64_t writeSerial = 0;
        std::uint64_t writtenDraw = 0;
        std::uint64_t poseEpoch = 0;
        std::uintptr_t shader = 0;
        std::uint64_t shaderEpoch = 0;
        GameSemantic::RenderScope scope = GameSemantic::RenderScope::None;
        GameSemantic::ProducerToken producer = GameSemantic::ProducerToken::None;
        const void* queueNode = nullptr;
        std::uint64_t queueEpoch = 0;
    };
    inline bool CoherentOriginalRankWvp(
        const PhysicalRankSource& physical,
        const OriginalRankWvpSource& raw) noexcept
    {
        return ValidRankSource(physical) &&
            physical.shader != 0 && physical.shaderEpoch != 0 &&
            raw.writeSerial != 0 && raw.writtenDraw != 0 &&
            raw.writtenDraw < physical.drawSerial &&
            physical.drawSerial - raw.writtenDraw <= 12u &&
            raw.poseEpoch == physical.poseEpoch &&
            raw.shader == physical.shader &&
            raw.shaderEpoch == physical.shaderEpoch &&
            raw.scope == physical.scope &&
            raw.producer == physical.producer &&
            raw.queueNode == physical.queueNode &&
            raw.queueEpoch == physical.queueEpoch;
    }
    inline bool SameOriginalRankWvp(
        const OriginalRankWvpSource& a,
        const OriginalRankWvpSource& b) noexcept
    {
        return a.writeSerial != 0 && a.writtenDraw != 0 &&
            a.writeSerial == b.writeSerial &&
            a.writtenDraw == b.writtenDraw &&
            a.poseEpoch == b.poseEpoch &&
            a.shader == b.shader && a.shaderEpoch == b.shaderEpoch &&
            a.scope == b.scope && a.producer == b.producer &&
            a.queueNode == b.queueNode && a.queueEpoch == b.queueEpoch;
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
            before.drawSerial == after.drawSerial &&
            before.fvf == after.fvf &&
            before.shader == after.shader &&
            before.shaderEpoch == after.shaderEpoch;
    }
}
