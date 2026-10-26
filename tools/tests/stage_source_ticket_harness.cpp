#include "vr/game/hud_command_batch.hpp"
#include "vr/game/stage_extension_source_admission.hpp"
#include <cstdio>
using namespace OutRunVR::GameSemantic;
OutRunVR::HudCommandBatch::Ledger HudBatch{};
std::uint64_t DirectStageTicket=11;
std::uint64_t NextDirectStageTicket=0;
namespace safetyhook { struct Context {}; }
namespace Settings { bool VREnabled=true,VRTelemetry=false; }
namespace Game { int* current_mode=nullptr; int* game_mode=nullptr; }
namespace spdlog { template<class... Args> void info(Args...) {} }
unsigned StageExtensionDepth=1,flushes=0,tags=0;
std::uint64_t StageExtensionEntrySerial=0,StageExtensionCompleted=0;
std::array<void*,2> StageExtensionBefore{},StageExtensionRootsBefore{};
OutRunVR::StageExtension::SourceAdmission StageExtensionAdmission{true,true,9};
RenderScope StageExtensionSavedScope=RenderScope::None;
struct Owner { void reset() {} } StageExtensionDirectDrawOwner;
template<class... Args> void TagAppendedNodes(Args...) { ++tags; }
void FlushD3DXAtDirectStageSourceExit() { ++flushes; HudBatch.onFlushSuccess(); }
// @ACTUAL_PREDICATE@
// @ACTUAL_BEGIN@
// @ACTUAL_COMPLETE@
// @ACTUAL_LEAVE@
bool restorable() {
    return HudBatch.matchesGpuOwner(false,nullptr,0) &&
        CanRestoreDeferredResultOwner(HudBatch.active,false,HudBatch.homogeneous,
            HudBatch.drawCount,true,HudBatch.scope,HudBatch.producer);
}
void draw(std::uint64_t ticket) {
    const auto snapshot=HudBatch.snapshot();
    HudBatch.completeNativeDraw(snapshot,true,RenderScope::ScreenHud,ProducerToken::StageExtensionTime);
#ifdef HAVE_STAGE_TICKET
    HudBatch.recordDirectStageTicket(ticket);
#endif
}
void prepare(void* sprite,std::uint64_t ticket) {
    HudBatch.begin(sprite,true); DirectStageTicket=ticket; draw(ticket);
    StageExtensionDepth=1; StageExtensionAdmission={true,true,9};
    Settings::VREnabled=true; SpriteQueueDepth=0; SpriteQueueNodeEpoch=10;
    flushes=tags=0;
}
int main() {
    int sprite=0,node=0;
    safetyhook::Context ctx;
    prepare(&sprite,11);
    const auto generation=HudBatch.generation;
    StageExtensionLeave(ctx);
    if(restorable()) { std::puts("FAIL rejected E8 still restores delayed direct +TIME owner"); return 1; }
    if(!HudBatch.active||HudBatch.drawCount!=1||HudBatch.generation!=generation||flushes||tags) return 2;
    // Same source and queue epoch: retain the established source-exit Flush.
    prepare(&sprite,12); SpriteQueueNodeEpoch=9; StageExtensionLeave(ctx);
    if(flushes!=1||tags!=1||HudBatch.drawCount) return 3;
    prepare(&sprite,13); Settings::VREnabled=false; StageExtensionLeave(ctx);
    Settings::VREnabled=true;
    if(restorable()||flushes||tags||HudBatch.drawCount!=1) return 4;
#ifdef HAVE_STAGE_TICKET
    if(DirectStageTicket!=0) return 5;
    // Rejecting ticket 14 cannot revoke an unrelated direct ticket 15.
    prepare(&sprite,15); DirectStageTicket=14; CompleteD3DXDirectStageSource(false);
    if(!restorable()) return 6;
    // Queued +TIME retains its node/epoch authority.
    HudBatch.begin(&sprite,true);
    HudBatch.recordDraw(RenderScope::ScreenHud,ProducerToken::StageExtensionTime,true,&node,9);
    DirectStageTicket=15; CompleteD3DXDirectStageSource(false);
    if(!HudBatch.homogeneous||!HudBatch.matchesGpuOwner(true,&node,9)) return 7;
    // A new Begin for GOAL is a different generation/source, never revoked.
    HudBatch.begin(&sprite,true);
    HudBatch.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime020);
    DirectStageTicket=15; CompleteD3DXDirectStageSource(false);
    if(!restorable()) return 8;
    prepare(&sprite,16); draw(17); DirectStageTicket=16;
    CompleteD3DXDirectStageSource(false);
    if(HudBatch.homogeneous||HudBatch.drawCount!=2) return 9;
    HudBatch.onFlushSuccess();
    if(HudBatch.directStageTicket) return 10;
    // An accepted source whose Flush is deferred preserves its valid owner.
    prepare(&sprite,18); CompleteD3DXDirectStageSource(true);
    if(!restorable()||DirectStageTicket) return 11;
    // Reset/foreign object already invalidated the ledger: never resurrect it.
    prepare(&sprite,19); HudBatch.invalidate(); CompleteD3DXDirectStageSource(false);
    if(HudBatch.active||HudBatch.sprite||restorable()) return 12;
    // No source ticket cannot authorize a new direct stage batch.
    prepare(&sprite,0);
    if(restorable()) return 13;
    BeginDirectStageSource();
    if(DirectStageTicket!=1) return 14;
    NextDirectStageTicket=UINT64_MAX;
    BeginDirectStageSource();
    if(DirectStageTicket) return 15;
#endif
    std::puts("PASS +TIME actual source exit: rejected queue/VR ticket, native batch preservation, accepted/deferred, mixed, queued, foreign source and lifecycle controls");
}
