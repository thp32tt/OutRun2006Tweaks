#pragma once
#include "render_semantics.hpp"
#include "lens_centre_partial_wvp.hpp"
#include <cstdint>

// R84 shader HUD may receive the original c64..c67 as native D3D9 partial
// uploads. Reconstruct only a complete exact queued ScreenHud game matrix;
// R30's shader/pose/queue checks still independently authorize the two eyes.
// Source-tagged HUD and original C993 world flare are separate accumulators.
namespace OutRunVR::HudQueuedWvp
{
    using OutRunVR::GameSemantic::RenderScope;
    using OutRunVR::GameSemantic::ProducerToken;
    struct Upload final
    {
        OutRunVR::LensCentre::PartialWvpUpload rows{};
        const void* node = nullptr;
        ProducerToken producer = ProducerToken::None;
        constexpr void Reset() noexcept
        {
            rows.Reset();
            node = nullptr;
            producer = ProducerToken::None;
        }
        constexpr bool Append(std::uint32_t first, std::uint32_t count,
            const float* source, bool queueActive, RenderScope scope,
            ProducerToken sourceProducer, const void* sourceNode,
            std::uint64_t queueEpoch, std::uint64_t poseEpoch,
            std::uintptr_t shader, std::uint64_t shaderEpoch,
            std::uintptr_t device, std::uint64_t drawSerial) noexcept
        {
            // A matching shader and a short draw age are NOT proof of game
            // source. An exact producer, live node and queue epoch must
            // all be present before retaining any rows (including full).
            if (!queueActive || scope != RenderScope::ScreenHud ||
                sourceProducer == ProducerToken::None || !sourceNode ||
                !queueEpoch || !poseEpoch || !shader || !shaderEpoch ||
                !device || !source || !count)
            {
                Reset();
                return false;
            }
            if (sourceNode != node || sourceProducer != producer)
            {
                Reset();
                node = sourceNode;
                producer = sourceProducer;
            }
            // The queue epoch is the strict original-source call identity.
            // A different epoch, GPU draw, shader, device or pose restarts
            // accumulation; successful full upload permits only later
            // same-draw native row replacements (D3D9 retained registers).
            return rows.Append(first, count, source, queueEpoch,
                poseEpoch, shader, shaderEpoch, device, drawSerial, true);
        }
    };

    constexpr unsigned char NodeOne = 1, NodeTwo = 2;
    constexpr float FirstRows[8]{1,2,3,4,5,6,7,8};
    constexpr float LastRows[8]{9,10,11,12,13,14,15,16};
    constexpr float FullRows[16]{
        1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16};
    constexpr float RewrittenRow[4]{21,22,23,24};

    constexpr bool ExactNodeSplitAndSameDrawPartial() noexcept
    {
        Upload u{};
        const auto append = [&](std::uint32_t reg,std::uint32_t count,
            const float* p,std::uint64_t serial) constexpr {
            return u.Append(reg,count,p,true,RenderScope::ScreenHud,
                ProducerToken::OutRunHudText,&NodeOne,4,7,0x100,3,0x200,serial);
        };
        if (append(64,2,FirstRows,9) ||
            !append(66,2,LastRows,9) || u.rows.raw[15] != 16 ||
            !u.rows.CommitComplete() ||
            !append(65,1,RewrittenRow,9) ||
            u.rows.raw[0] != 1 || u.rows.raw[4] != 21 ||
            u.rows.raw[8] != 9 || u.rows.raw[15] != 16)
            return false;
        return !append(67,1,RewrittenRow,10) &&
            u.rows.covered == 0x08 && !u.rows.committedComplete;
    }
    constexpr bool RejectForeignQueuedOwnersAndReset() noexcept
    {
        Upload u{};
        if (!u.Append(64,2,FirstRows,true,RenderScope::ScreenHud,
                ProducerToken::OutRunHudText,&NodeOne,4,7,0x100,3,0x200,9))
            {} // a first half is intentionally incomplete
        else
            return false;
        // A new SpriteNode cannot complete the prior node's source rows.
        if (u.Append(66,2,LastRows,true,RenderScope::ScreenHud,
                ProducerToken::OutRunHudText,&NodeTwo,5,7,0x100,3,0x200,9) ||
            u.rows.covered != 0x0c)
            return false;
        // Even on the same node, a different producer revokes old rows.
        if (u.Append(64,2,FirstRows,true,RenderScope::ScreenHud,
                ProducerToken::ResultProgress,&NodeTwo,5,7,0x100,3,0x200,9) ||
            u.rows.covered != 0x03)
            return false;
        // World, unknown scope, absent queue, and reset never publish.
        if (u.Append(66,2,LastRows,true,RenderScope::WorldBillboard,
                ProducerToken::ResultProgress,&NodeTwo,5,7,0x100,3,0x200,9) ||
            u.rows.covered != 0)
            return false;
        if (u.Append(64,4,FullRows,false,RenderScope::ScreenHud,
                ProducerToken::OutRunHudText,&NodeOne,4,7,0x100,3,0x200,9))
            return false;
        u.Append(64,4,FullRows,true,RenderScope::ScreenHud,
            ProducerToken::OutRunHudText,&NodeOne,4,7,0x100,3,0x200,9);
        u.Reset();
        return !u.Append(66,2,LastRows,true,RenderScope::ScreenHud,
            ProducerToken::OutRunHudText,&NodeOne,4,7,0x100,3,0x200,9) &&
            u.rows.covered == 0x0c;
    }
    static_assert(ExactNodeSplitAndSameDrawPartial(),
        "queued HUD original c64 must reconstruct across native row writes");
    static_assert(RejectForeignQueuedOwnersAndReset(),
        "HUD eye source cannot borrow another node or stale device frame");
}
