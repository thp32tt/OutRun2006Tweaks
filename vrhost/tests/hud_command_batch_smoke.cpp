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
    return 0;
}