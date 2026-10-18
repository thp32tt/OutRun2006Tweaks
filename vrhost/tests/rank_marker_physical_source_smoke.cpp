#include "vr/game/rank_marker_physical_source.hpp"
#include "vr/game/hud_native_source_transaction.hpp"
#include <limits>
#include <iostream>
using namespace OutRunVR;
using namespace OutRunVR::RankMarker;

int main()
{
    const int node = 1, otherNode = 2;
    PhysicalRankSource queued{
        GameSemantic::RenderScope::ProjectedWorldMarker2D,
        GameSemantic::ProducerToken::RankMarkerClipSprite,
        true, &node, 8u, {true, 2.5f, -3.0f, -17.0f},
        31u, 41u, 0x142u, 0u, 0u}; // Original fixed-function FVF 0x142, no VS.
    if (!SameRankSourceAfterNativeLeft(queued, queued)) return 1;
    const auto rejects = [&](const PhysicalRankSource& changed) {
        return !SameRankSourceAfterNativeLeft(queued, changed);
    };
    auto m = queued;
    m.queueNode = &otherNode; if (!rejects(m)) return 2;
    m = queued; ++m.queueEpoch; if (!rejects(m)) return 3;
    m = queued; m.queued = false; if (!rejects(m)) return 4;
    m = queued; m.marker.viewX += 1.0f; if (!rejects(m)) return 5;
    m = queued; m.marker.viewY -= 1.0f; if (!rejects(m)) return 6;
    m = queued; m.marker.viewZ = -9.0f; if (!rejects(m)) return 7;
    m = queued; m.marker.valid = false; if (!rejects(m)) return 8;
    m = queued; m.poseEpoch = 32; if (!rejects(m)) return 9;
    m = queued; m.producer =
        GameSemantic::ProducerToken::RivalMarkerSprani;
    if (!rejects(m)) return 10;
    m = queued; m.scope = GameSemantic::RenderScope::ScreenHud;
    if (!rejects(m)) return 11;
    m = queued; m.marker.viewZ =
        std::numeric_limits<float>::quiet_NaN();
    if (!rejects(m)) return 12;
    m = queued; m.shader = 0x1234; m.shaderEpoch = 4;
    if (!rejects(m)) return 13;
    auto shaderRank = queued;
    shaderRank.shader = 0x1234;
    shaderRank.shaderEpoch = 4;
    shaderRank.producer = GameSemantic::ProducerToken::RankMarkerSprani;
    if (!SameRankSourceAfterNativeLeft(shaderRank, shaderRank)) return 14;
    m = shaderRank; ++m.shaderEpoch;
    if (SameRankSourceAfterNativeLeft(shaderRank,m)) return 15;
    m = shaderRank; m.shader = 0x4321;
    if (SameRankSourceAfterNativeLeft(shaderRank,m)) return 16;
    m = shaderRank; m.shaderEpoch = 0;
    if (SameRankSourceAfterNativeLeft(shaderRank,m)) return 17;
    PhysicalRankSource direct{
        GameSemantic::RenderScope::ProjectedWorldMarker2D,
        GameSemantic::ProducerToken::RivalMarkerSprani,
        false, nullptr, 0, {true, -1.f, 2.f, -12.f},
        7, 11, 0x142u, 0, 0};
    if (!SameRankSourceAfterNativeLeft(direct,direct)) return 18;
    m = direct; m.queueNode = &node;
    if (SameRankSourceAfterNativeLeft(direct,m)) return 19;
    m = direct; m.queueEpoch = 1;
    if (SameRankSourceAfterNativeLeft(direct,m)) return 20;
    m = direct; m.poseEpoch = 0;
    if (SameRankSourceAfterNativeLeft(direct,m)) return 21;
    m = direct; m.producer = GameSemantic::ProducerToken::LensFlareCentre;
    if (SameRankSourceAfterNativeLeft(direct,m)) return 22;
    // Even with unchanged node, marker and shader, do not submit a second
    // physical command or a different fixed-function vertex layout to RIGHT.
    m = queued; ++m.drawSerial;
    if (!rejects(m)) return 23;
    m = queued; m.drawSerial = 0;
    if (!rejects(m)) return 24;
    m = queued; m.fvf = 0x144u;
    if (!rejects(m)) return 25;
    m = direct; ++m.drawSerial;
    if (SameRankSourceAfterNativeLeft(direct, m)) return 26;
    m = direct; m.fvf = 0u;
    if (SameRankSourceAfterNativeLeft(direct, m)) return 27;
    if (!SameRankSourceAfterNativeLeft(queued, queued)) return 28;

    // R33 shader-c64 route must pair both eyes to the SAME moving vehicle
    // after the native LEFT callback. This is independent from R30's
    // fixed-function/XYZRHW owner already using this physical stamp.
    auto shaderQueued = shaderRank;
    shaderQueued.fvf = 0u; // declaration-only shader path
    if (!SameRankSourceAfterNativeLeft(shaderQueued, shaderQueued)) return 29;
    m = shaderQueued; m.marker.viewX += 0.1f;
    if (SameRankSourceAfterNativeLeft(shaderQueued, m)) return 30;
    m = shaderQueued; m.queueNode = &otherNode;
    if (SameRankSourceAfterNativeLeft(shaderQueued, m)) return 31;
    m = shaderQueued; ++m.queueEpoch;
    if (SameRankSourceAfterNativeLeft(shaderQueued, m)) return 32;
    m = shaderQueued; m.poseEpoch = 0;
    if (SameRankSourceAfterNativeLeft(shaderQueued, m)) return 33;
    m = shaderQueued; m.scope = GameSemantic::RenderScope::ScreenHud;
    m.producer = GameSemantic::ProducerToken::DispRankClipSprite;
    if (SameRankSourceAfterNativeLeft(shaderQueued, m)) return 34;
    m = shaderQueued; ++m.drawSerial;
    if (SameRankSourceAfterNativeLeft(shaderQueued, m)) return 35;
    m = shaderQueued; m.fvf = 0x142u;
    if (SameRankSourceAfterNativeLeft(shaderQueued, m)) return 36;
    // Shader-mediated direct rival marker must not borrow the 6th/6 HUD
    // or an unrelated direct world-effect producer.
    auto shaderDirect = direct;
    shaderDirect.shader = 0x1234;
    shaderDirect.shaderEpoch = 9;
    shaderDirect.fvf = 0u;
    if (!SameRankSourceAfterNativeLeft(shaderDirect, shaderDirect)) return 37;
    m = shaderDirect; m.producer = GameSemantic::ProducerToken::DispRankFirst;
    if (SameRankSourceAfterNativeLeft(shaderDirect, m)) return 38;
    m = shaderDirect; ++m.shaderEpoch;
    if (SameRankSourceAfterNativeLeft(shaderDirect, m)) return 39;
    // Native FVF142 fixed-function 6th/6 rank, NOT the car-rank marker.
    HudNativeSource::FixedFnRankHudStamp rankHud{{
        GameSemantic::RenderScope::ScreenHud,
        GameSemantic::ProducerToken::DispRankFirst,
        &node, 8u, true, 0u}, 31u, 41u, 0x142u, true};
    if (!HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud, rankHud)) return 40;
    auto hudChanged = rankHud;
    hudChanged.command.queueNode = &otherNode;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 41;
    hudChanged = rankHud; ++hudChanged.command.queueEpoch;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 42;
    hudChanged = rankHud; hudChanged.command.producer =
        GameSemantic::ProducerToken::DispRankClipSprite;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 43;
    hudChanged = rankHud; ++hudChanged.poseEpoch;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 44;
    hudChanged = rankHud; ++hudChanged.drawSerial;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 45;
    hudChanged = rankHud; hudChanged.fvf = 0x144u;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 46;
    hudChanged = rankHud; hudChanged.vertexShaderAbsent = false;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 47;
    hudChanged = rankHud; hudChanged.command.scope =
        GameSemantic::RenderScope::ProjectedWorldMarker2D;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 48;
    hudChanged = rankHud; hudChanged.command.producer =
        GameSemantic::ProducerToken::StageExtensionTime;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 49;
    hudChanged = rankHud; hudChanged.command.producer =
        GameSemantic::ProducerToken::None;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 50;
    hudChanged = rankHud; hudChanged.command.queueNode = nullptr;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(rankHud,hudChanged)) return 51;
    auto directHud = rankHud;
    directHud.command.queued = false;
    directHud.command.queueNode = nullptr;
    directHud.command.queueEpoch = 0;
    directHud.command.producer = GameSemantic::ProducerToken::DispRankClipSprite;
    if (!HudNativeSource::SameFixedFnRankHudAfterLeft(directHud,directHud)) return 52;
    hudChanged = directHud; hudChanged.command.queueEpoch = 1;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(directHud,hudChanged)) return 53;
    hudChanged = directHud; hudChanged.command.producer =
        GameSemantic::ProducerToken::RivalMarkerSprani;
    if (HudNativeSource::SameFixedFnRankHudAfterLeft(directHud,hudChanged)) return 54;
    // Identical physical marker with a different ORIGINAL c64 writer is
    // not the same moving car source (even if live GPU c64 was overwritten).
    OriginalRankWvpSource rankRaw{
        100u, 40u, 31u, 0x1234u, 4u,
        GameSemantic::RenderScope::ProjectedWorldMarker2D,
        GameSemantic::ProducerToken::RankMarkerSprani,
        &node, 8u};
    if (!CoherentOriginalRankWvp(shaderRank, rankRaw) ||
        !SameOriginalRankWvp(rankRaw, rankRaw)) return 55;
    auto rawChanged = rankRaw;
    ++rawChanged.writeSerial;
    if (SameOriginalRankWvp(rankRaw, rawChanged)) return 56;
    rawChanged = rankRaw; ++rawChanged.writtenDraw;
    if (SameOriginalRankWvp(rankRaw, rawChanged)) return 57;
    rawChanged = rankRaw; ++rawChanged.poseEpoch;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 58;
    rawChanged = rankRaw; rawChanged.shader = 0x4321;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 59;
    rawChanged = rankRaw; ++rawChanged.shaderEpoch;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 60;
    rawChanged = rankRaw; rawChanged.queueNode = &otherNode;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 61;
    rawChanged = rankRaw; ++rawChanged.queueEpoch;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 62;
    rawChanged = rankRaw;
    rawChanged.producer = GameSemantic::ProducerToken::RivalMarkerSprani;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 63;
    rawChanged = rankRaw;
    rawChanged.scope = GameSemantic::RenderScope::ScreenHud;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 64;
    rawChanged = rankRaw; rawChanged.writeSerial = 0;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 65;
    rawChanged = rankRaw; rawChanged.writtenDraw = shaderRank.drawSerial;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 66;
    rawChanged = rankRaw; rawChanged.writtenDraw = 28;
    if (CoherentOriginalRankWvp(shaderRank, rawChanged)) return 67;
    if (CoherentOriginalRankWvp(direct, rankRaw)) return 68;
    if (!CoherentOriginalRankWvp(shaderQueued, rankRaw)) return 69;
    std::cout << "R84 rank original c64 right-eye source fence PASS\n";
    std::cout << "R84 FVF142 physical DispRank 6th/6 command fence PASS\n";
    std::cout << "R84 physical projected rank source transaction PASS\n";
    return 0;
}
