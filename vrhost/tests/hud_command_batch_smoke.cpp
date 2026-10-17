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
    // D3DXSprite::Draw may implicitly Flush an older texture during the
    // original Draw call. A successful nested Flush starts a fresh batch;
    // the returning Draw MUST retain its incoming +TIME/GOAL GPU owner.
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    const auto beforeImplicitFlushDraw = l.snapshot();
    const auto implicitFlush = l.snapshot();
    if (!l.completeNativeFlush(implicitFlush,true) ||
        l.drawCount != 0 || !l.active)
        return 27;
    if (!l.completeNativeDraw(beforeImplicitFlushDraw,true,
            RenderScope::ScreenHud,ProducerToken::GoalTime020,true) ||
        !l.exactUniformOwner() || l.drawCount != 1 ||
        l.producer != ProducerToken::GoalTime020 ||
        l.lastSuccessfulFlushMutationSerial != 0)
        return 28;

    // The same native ordering also applies to another +TIME sprite after
    // D3DX changes its source texture; neither native Begin nor extra Flush
    // is injected by the mod into the common same-texture path.
    const auto nextDraw = l.snapshot();
    if (!l.completeNativeDraw(nextDraw,true,
            RenderScope::ScreenHud,ProducerToken::GoalTime020,true) ||
        l.drawCount != 2 || !l.homogeneous)
        return 29;
    const auto nativeSecondFlush = l.snapshot();
    if (!l.completeNativeFlush(nativeSecondFlush,true) ||
        !l.active || l.drawCount)
        return 30;

    // A caller that changes producer inside the native callback cannot
    // claim an old Flush's clean-batch recovery token.
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime150);
    const auto changedSourceDraw = l.snapshot();
    const auto changedSourceFlush = l.snapshot();
    if (!l.completeNativeFlush(changedSourceFlush,true) ||
        l.completeNativeDraw(changedSourceDraw,true,
            RenderScope::ScreenHud,ProducerToken::StageExtensionTime,false) ||
        l.active || l.exactUniformOwner())
        return 31;

    // A failed implicit GPU Flush still invalidates the synthetic owner
    // and must never publish the returning Draw as an exact ScreenHud batch.
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    const auto beforeFailedInternalFlush = l.snapshot();
    const auto failingFlush = l.snapshot();
    if (l.completeNativeFlush(failingFlush,false) ||
        l.completeNativeDraw(beforeFailedInternalFlush,true,
            RenderScope::ScreenHud,ProducerToken::StageExtensionTime,true) ||
        l.active || l.exactUniformOwner())
        return 32;

    // An inner Draw in the same generation is NOT an internal native Flush;
    // the returning older callback may not steal that queued producer.
    l.begin(&spriteA,true);
    const auto reentrantDraw = l.snapshot();
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime150);
    if (l.completeNativeDraw(reentrantDraw,true,
            RenderScope::ScreenHud,ProducerToken::StageExtensionTime,true) ||
        l.active || l.exactUniformOwner())
        return 33;

    // A newly successful Begin supersedes the original Draw even if the
    // pointer is recycled. A stale callback must not own the next session.
    l.begin(&spriteA,true);
    const auto oldGenerationDraw = l.snapshot();
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime020);
    if (l.completeNativeDraw(oldGenerationDraw,true,
            RenderScope::ScreenHud,ProducerToken::StageExtensionTime,true) ||
        !l.exactUniformOwner() ||
        l.producer != ProducerToken::GoalTime020)
        return 34;

    // A producer can change during native Draw without any hooked D3DX
    // mutation. That Draw must not inherit the prior +TIME GPU eye owner.
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    const auto beforeUntrackedSourceChange = l.snapshot();
    if (l.completeNativeDraw(beforeUntrackedSourceChange,true,
            RenderScope::ScreenHud,ProducerToken::StageExtensionTime,false) ||
        l.active || l.exactUniformOwner() || l.drawCount ||
        l.producer != ProducerToken::None)
        return 35;

    // An actual later Begin reopens the native batch; unchanged-source
    // +TIME glyphs still batch normally rather than flushing each Draw.
    l.begin(&spriteB,true);
    const auto cleanAfterSourceChange = l.snapshot();
    if (!l.completeNativeDraw(cleanAfterSourceChange,true,
            RenderScope::ScreenHud,ProducerToken::StageExtensionTime,true) ||
        !l.exactUniformOwner() || l.drawCount != 1 ||
        l.producer != ProducerToken::StageExtensionTime)
        return 36;

    // Same original +TIME token across two distinct SpriteNodes is NOT one
    // native GPU submission owner. The first queue node cannot absorb direct
    // numeric glyphs nor borrow the previous node's eye/pose epoch.
    l.begin(&spriteA, true);
    const int nodeA = 10, nodeB = 20;
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime);
    if (l.queued || l.queueNode || l.queueEpoch != 0 ||
        !l.exactUniformOwner())
        return 37;
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                 true, &nodeA, 41);
    if (l.homogeneous || l.exactUniformOwner())
        return 38;
    l.onFlushSuccess();
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                 true, &nodeA, 41);
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                 true, &nodeA, 41);
    if (!l.exactUniformOwner() || !l.queued || l.queueNode != &nodeA ||
        l.queueEpoch != 41 || l.drawCount != 2)
        return 39;
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                 true, &nodeB, 42);
    if (l.homogeneous || l.exactUniformOwner())
        return 40;
    l.onFlushSuccess();
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                 true, nullptr, 42);
    if (l.exactUniformOwner())
        return 41;
    l.onFlushSuccess();
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
                 true, &nodeA, 0);
    if (l.exactUniformOwner())
        return 42;
    l.onFlushSuccess();
    l.recordDraw(RenderScope::ScreenHud, ProducerToken::StageExtensionTime);
    if (!l.exactUniformOwner() || l.queued || l.queueNode || l.queueEpoch)
        return 43;

    // Preserve per-queue +TIME source and reject stale or recycled nodes.
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime,
                 true,&nodeA,77);
    if (!l.matchesGpuOwner(true,&nodeA,77) ||
        l.matchesGpuOwner(true,&nodeB,77) ||
        l.matchesGpuOwner(true,&nodeA,78) ||
        l.matchesGpuOwner(false,nullptr,0))
        return 44;
    l.onFlushSuccess();
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    if (!l.matchesGpuOwner(false,nullptr,0) ||
        l.matchesGpuOwner(true,&nodeA,77))
        return 45;
    // Direct and queued owner mixtures cannot be promoted to either.
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime,
                 true,&nodeA,77);
    if (l.homogeneous || l.matchesGpuOwner(true,&nodeA,77))
        return 46;
    l.onFlushSuccess();
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime020,
                 true,&nodeB,81);
    if (!l.matchesGpuOwner(true,&nodeB,81) ||
        l.matchesGpuOwner(true,&nodeB,80) ||
        l.matchesGpuOwner(false,nullptr,0))
        return 47;
    l.invalidate();
    if (!l.matchesGpuOwner(false,nullptr,0))
        return 48;
    // Corrupted direct metadata must not impersonate an exact glyph owner.
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    l.queueEpoch=88;
    if (l.matchesGpuOwner(false,nullptr,0))
        return 49;
    l.onFlushFailure();
    l.begin(&spriteA,true);
    l.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
    if (!l.matchesGpuOwner(false,nullptr,0))
        return 50;
    return 0;
}