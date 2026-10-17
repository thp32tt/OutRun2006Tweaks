#include "vr/game/hud_command_batch.hpp"
#include <climits>
using namespace OutRunVR::HudCommandBatch;
using namespace OutRunVR::GameSemantic;
int main()
{
    Ledger l{};
    unsigned char spriteA = 0, spriteB = 0;
    if (l.active || l.sprite || l.exactUniformOwner())
        return 1;
    l.begin(&spriteA, true);
    if (!l.active || l.generation != 1 || l.drawCount != 0)
        return 2;
    // Multiple glyphs of one producer remain one homogeneous GPU batch.
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    if (!l.exactUniformOwner() || l.drawCount != 2 ||
        l.producer != ProducerToken::StageExtensionTime)
        return 3;
    // GPU Flush doesn't force a new Begin nor relabel the next batch.
    l.boundaryReady=true;
    l.onFlushSuccess();
    if (!l.active || l.boundaryReady || l.drawCount ||
        l.exactUniformOwner())
        return 4;
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime020);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime150);
    if (l.homogeneous || l.exactUniformOwner())
        return 5;
    l.onFlushSuccess();
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::ResultTextB9200);
    // The actual hook rejects B9200 as a deferred GPU batch separately:
    // this ledger never upgrades a non-whitelisted producer.
    if (l.producer != ProducerToken::ResultTextB9200)
        return 6;
    l.onFlushFailure();
    if (l.active || l.exactUniformOwner() || l.drawCount != 0 ||
        l.scope != RenderScope::None ||
        l.producer != ProducerToken::None || !l.homogeneous)
        return 7;
    l.begin(&spriteB,true);
    if (l.generation != 2 || l.sprite != &spriteB ||
        l.producer != ProducerToken::None)
        return 8;
    l.recordDraw(RenderScope::WorldBillboard, ProducerToken::RivalMarkerSprani);
    if (!l.exactUniformOwner())
        return 9;
    l.end();
    if (l.active || l.drawCount || l.producer != ProducerToken::None ||
        l.sprite != &spriteB)
        return 10;
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    l.invalidate();
    if (l.active || l.sprite || l.drawCount || l.exactUniformOwner())
        return 11;
    l.begin(&spriteA,false);
    if (l.active || l.exactUniformOwner() || l.generation != 3)
        return 12;
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::None);
    if (l.exactUniformOwner())
        return 13;
    // A nested native INVALIDCALL retains the exact +TIME owner, draw count,
    // queue boundary and generation until the original Flush/End.
    l.onFlushSuccess();
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime);
    l.boundaryReady = true;
    const auto oldGeneration = l.generation;
    l.onBeginResult(&spriteA, false, true);
    if (!l.active || l.sprite != &spriteA || !l.boundaryReady ||
        !l.exactUniformOwner() || l.drawCount != 1 ||
        l.generation != oldGeneration)
        return 14;
    // A failed device/driver Begin must NOT allow an old numeric +TIME
    // producer to be replayed under the next game SpriteQueue/End.
    l.onBeginResult(&spriteA, false, false);
    if (l.active || l.sprite || l.boundaryReady || l.exactUniformOwner() ||
        l.drawCount || l.producer != ProducerToken::None ||
        l.generation != oldGeneration)
        return 15;
    l.onBeginResult(&spriteA, true, false);
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::GoalTime020);
    if (!l.exactUniformOwner() || l.producer != ProducerToken::GoalTime020 ||
        l.generation != oldGeneration + 1)
        return 16;
    // An INVALIDCALL from a foreign sprite cannot inherit a live GOAL batch.
    l.onBeginResult(&spriteB, false, true);
    if (l.exactUniformOwner() || l.active || l.sprite)
        return 17;

    // Native D3DX callback reentrancy: a previous Flush must not discard a
    // fresh Begin/Draw that registered AFTER the outer Flush began.
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime);
    const auto outerFlush = l.snapshot();
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::GoalTime020);
    if (l.completeNativeFlush(outerFlush,true) ||
        !l.exactUniformOwner() ||
        l.producer != ProducerToken::GoalTime020 ||
        l.generation != outerFlush.generation + 1)
        return 18;

    // A same-generation reentrant Draw invalidates uncertain GPU submit
    // ordering; no old +TIME/GOAL tag may survive the outer Flush return.
    const auto sameBeginFlush = l.snapshot();
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::GoalTime020);
    if (l.completeNativeFlush(sameBeginFlush,true) ||
        l.active || l.exactUniformOwner() || l.drawCount)
        return 19;

    l.begin(&spriteA,true);
    const auto normalDraw = l.snapshot();
    if (!l.completeNativeDraw(normalDraw,true,
            RenderScope::ScreenHud,ProducerToken::StageExtensionTime) ||
        !l.exactUniformOwner() || l.drawCount != 1)
        return 20;
    const auto normalFlush = l.snapshot();
    if (!l.completeNativeFlush(normalFlush,true) ||
        !l.active || l.drawCount || l.exactUniformOwner())
        return 21;

    // The outer native Draw cannot reattribute a newer Begin's glyphs.
    const auto oldDraw = l.snapshot();
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime150);
    if (l.completeNativeDraw(oldDraw,true,
            RenderScope::ScreenHud,ProducerToken::StageExtensionTime) ||
        !l.exactUniformOwner() ||
        l.producer != ProducerToken::GoalTime150)
        return 22;

    // A failed same-generation Draw cannot keep a possibly half-submitted
    // +TIME batch; the original HRESULT is handled by the live hook.
    const auto failingDraw = l.snapshot();
    if (l.completeNativeDraw(failingDraw,false,
            RenderScope::ScreenHud,ProducerToken::StageExtensionTime) ||
        l.active || l.exactUniformOwner())
        return 23;

    l.begin(&spriteB,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime020);
    const auto outerEnd = l.snapshot();
    l.begin(&spriteB,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    if (l.completeNativeEnd(outerEnd) || !l.exactUniformOwner() ||
        l.producer != ProducerToken::StageExtensionTime)
        return 24;
    const auto nativeEnd = l.snapshot();
    if (!l.completeNativeEnd(nativeEnd) || l.active || l.exactUniformOwner())
        return 25;

    // A recycled sprite pointer across device loss is a NEW generation and
    // must never be owned by an old Flush/Draw completion.
    l.begin(&spriteA,true);
    const auto beforeReset = l.snapshot();
    l.invalidate();
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    if (l.completeNativeFlush(beforeReset,true) ||
        !l.exactUniformOwner())
        return 26;
    return 0;
}