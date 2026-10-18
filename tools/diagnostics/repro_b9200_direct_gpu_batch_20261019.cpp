// Behavioral regression for source-proven GOAL B9200 D3DX deferred GPU batches.
// c++ -std=c++20 -I. tools/diagnostics/repro_b9200_direct_gpu_batch_20261019.cpp -o /tmp/b9200_probe && /tmp/b9200_probe
#include "../../src/vr/game/hud_command_batch.hpp"
#include <cassert>
using namespace OutRunVR::GameSemantic;
using OutRunVR::HudCommandBatch::Ledger;
int main() {
    int sprite=0, other=0, queue=0;
    Ledger l;
    const auto hud=RenderScope::ScreenHud;
    const auto goal=ProducerToken::ResultTextB9200;
    l.begin(&sprite,true);
    auto s=l.snapshot();
    assert(l.completeNativeDraw(s,true,hud,goal,true,false,nullptr,0,true));
    s=l.snapshot();
    assert(l.completeNativeDraw(s,true,hud,goal,true,false,nullptr,0,true));
    assert(l.provenDirectB9200 && l.exactUniformOwner() && l.drawCount==2);
    assert(l.matchesGpuOwner(false,nullptr,0) && !l.matchesGpuOwner(true,&queue,1));
    l.onFlushSuccess();
    assert(!l.provenDirectB9200 && !l.exactUniformOwner());
    l.begin(&sprite,true);
    s=l.snapshot();
    assert(l.completeNativeDraw(s,true,hud,goal,true,false,nullptr,0,false));
    assert(!l.homogeneous && !l.provenDirectB9200);
    l.begin(&sprite,true);
    s=l.snapshot();
    assert(l.completeNativeDraw(s,true,hud,goal,true,false,nullptr,0,true));
    s=l.snapshot();
    assert(l.completeNativeDraw(s,true,hud,goal,true,false,nullptr,0,false));
    assert(!l.homogeneous && !l.exactUniformOwner());
    l.begin(&sprite,true);
    s=l.snapshot();
    assert(l.completeNativeDraw(s,true,hud,goal,true,true,&queue,5,false));
    assert(!l.provenDirectB9200 && l.matchesGpuOwner(true,&queue,5));
    assert(!l.matchesGpuOwner(true,&queue,6));
    l.begin(&sprite,true);
    s=l.snapshot();
    assert(l.completeNativeDraw(s,true,hud,goal,true,false,nullptr,0,true));
    assert(l.completeNativeEnd(l.snapshot()));
    assert(!l.active && !l.provenDirectB9200);
    l.begin(&sprite,true);
    s=l.snapshot();
    assert(l.completeNativeDraw(s,true,hud,goal,true,false,nullptr,0,true));
    l.invalidate();
    assert(!l.provenDirectB9200 && !l.sprite);
    l.begin(&other,true);
    assert(l.sprite==&other && !l.provenDirectB9200);
}
