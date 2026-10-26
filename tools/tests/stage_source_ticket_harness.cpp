#include "vr/game/hud_command_batch.hpp"
#include "vr/game/stage_extension_source_admission.hpp"
#include <cstdio>
#include <functional>
#include <optional>
#include <atomic>
#include <vector>
#include <cstdint>
#define __stdcall
using HRESULT=std::int32_t;
using D3DCOLOR=std::uint32_t;
struct IDirect3DTexture9 {};
struct RECT { int left,top,right,bottom; };
struct D3DVECTOR { float x,y,z; };
constexpr HRESULT OK=0,FAIL=-123;
bool SUCCEEDED(HRESULT hr){return hr>=0;}
bool FAILED(HRESULT hr){return hr<0;}
using namespace OutRunVR::GameSemantic;
OutRunVR::HudCommandBatch::Ledger HudBatch{};
std::uint64_t DirectStageTicket=11;
std::uint64_t NextDirectStageTicket=0;
namespace safetyhook { struct Context {}; }
namespace Settings { bool VREnabled=true,VRTelemetry=false; }
enum class GameState { STATE_GAME, STATE_GOAL };
namespace Game { GameState mode=GameState::STATE_GAME; GameState* current_mode=&mode; int* game_mode=nullptr; }
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
// @ACTUAL_LIFETIME@
void* liveSprite=nullptr;
namespace Module {
template<class T> T* exe_ptr(unsigned) { return reinterpret_cast<T*>(&liveSprite); }
}
namespace OutRunVR::GoalResult {
bool CanBindDirectB9200D3DXDraw(bool,bool,bool,bool,bool){return false;}
}
bool OriginalB9200GoalStackActive(){return false;}
unsigned goalEntries=0;
void FlushD3DXBeforeDirectGoalSource(){++goalEntries;}
std::atomic<unsigned> StageFlushes{},GoalFlushes{},StageFallbacks{},GoalFallbacks{},
                      Flushes{},Failures{};
struct NativeDraw {
    std::function<HRESULT(void*,IDirect3DTexture9*,const RECT*,
                          const D3DVECTOR*,const D3DVECTOR*,D3DCOLOR)> call;
    template<class R> R stdcall(void* s,IDirect3DTexture9* t,const RECT* r,
                               const D3DVECTOR* c,const D3DVECTOR* p,D3DCOLOR color){
        return call(s,t,r,c,p,color);
    }
} Draw_hk;
struct NativeSubmit {
    std::function<HRESULT(void*)> call;
    template<class R> R stdcall(void* s){return call(s);}
} Flush_hk,End_hk;
static HRESULT __stdcall FlushDest(void*);
bool FlushTracked(void* self){return SUCCEEDED(FlushDest(self));}
// @ACTUAL_NATIVE_HOOKS@
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
    // Execute complete production DrawDest/FlushDest/EndDest functions. Only
    // the native D3DX methods are fakes; real scopes, ledger and predicates run.
    struct Observation {RenderScope scope;ProducerToken producer;void* self;};
    std::vector<Observation> submissions;
    unsigned nativeDraws=0,implicitFlush=0;
    HRESULT drawResult=OK,submitResult=OK;
    int reentry=0;
    IDirect3DTexture9 texture;
    RECT rect{1,2,3,4}; D3DVECTOR center{1,2,3},pos{4,5,6};
    bool arguments=true;
    Flush_hk.call=End_hk.call=[&](void* self){
        submissions.push_back({EffectiveScope(),CurrentRenderProducerToken(),self});
        return submitResult;
    };
    Draw_hk.call=[&](void* self,IDirect3DTexture9* t,const RECT* r,
                    const D3DVECTOR* c,const D3DVECTOR* p,D3DCOLOR color) {
        ++nativeDraws;
        arguments=arguments&&self==&sprite&&t==&texture&&r==&rect&&
                  c==&center&&p==&pos&&color==0xff123456u;
        if(implicitFlush) {--implicitFlush;FlushDest(self);}
        if(reentry==1) {
            HudBatch.begin(self,true);
            HudBatch.recordDraw(RenderScope::ScreenHud,ProducerToken::GoalTime020);
        } else if(reentry==2) DirectStageTicket=9999;
        return drawResult;
    };
    auto nativeDraw=[&](){
        const auto before=nativeDraws;
        const auto hr=DrawDest(&sprite,&texture,&rect,&center,&pos,0xff123456u);
        return hr==drawResult&&nativeDraws==before+1&&arguments;
    };
    auto start=[&](std::uint64_t ticket) {
        HudBatch.begin(&sprite,true);liveSprite=&sprite;
        DirectStageTicket=ticket;SpriteQueueDepth=0;SpriteQueueNodeEpoch=9;
        CurrentScope=RenderScope::None;
        submissions.clear();drawResult=submitResult=OK;reentry=0;implicitFlush=0;
    };
    // Texture-change internal Flush must leave Draw as first command in a
    // new batch, carrying the same source ticket, not a per-glyph forced Flush.
    start(31);
    {
        ScopedExactProducerSemantic owner(RenderScope::ScreenHud,nullptr,true,
                                          ProducerToken::StageExtensionTime);
        if(!nativeDraw()||!submissions.empty()||HudBatch.directStageTicket!=31) return 20;
        implicitFlush=1;
        if(!nativeDraw()||submissions.size()!=1||HudBatch.drawCount!=1||
           HudBatch.directStageTicket!=31||!HudBatch.homogeneous) return 21;
    }
    CompleteD3DXDirectStageSource(false);
    submitResult=FAIL;
    if(FlushDest(&sprite)!=FAIL||submissions.size()!=2||
       submissions.back().producer==ProducerToken::StageExtensionTime) return 22;
    // Successful native End after rejection still executes once, with its
    // original return value and no resurrection of the rejected HUD owner.
    submitResult=OK;
    if(EndDest(&sprite)!=OK||submissions.size()!=3||HudBatch.active||
       submissions.back().producer==ProducerToken::StageExtensionTime) return 23;
    // Accepted pending source restores at delayed End, then restores caller.
    start(32);
    {
        ScopedExactProducerSemantic owner(RenderScope::ScreenHud,nullptr,true,
                                          ProducerToken::StageExtensionTime);
        if(!nativeDraw()) return 24;
    }
    CompleteD3DXDirectStageSource(true);
    if(EndDest(&sprite)!=OK||submissions.size()!=1||
       submissions.back().producer!=ProducerToken::StageExtensionTime||
       CurrentRenderProducerToken()!=ProducerToken::None) return 25;
    // A native callback that starts a different Begin must preserve that
    // new generation's GOAL ledger; outer Draw cannot stamp the old ticket.
    start(33);reentry=1;
    {
        ScopedExactProducerSemantic owner(RenderScope::ScreenHud,nullptr,true,
                                          ProducerToken::StageExtensionTime);
        if(!nativeDraw()) return 26;
    }
    CompleteD3DXDirectStageSource(false);
    if(!HudBatch.homogeneous||HudBatch.producer!=ProducerToken::GoalTime020||
       HudBatch.directStageTicket||HudBatch.drawCount!=1) return 27;
    // Same-generation source replacement revokes provenance but keeps the
    // native Draw/HRESULT; a missing or failed ticket must not acquire HUD.
    start(34);reentry=2;
    {
        ScopedExactProducerSemantic owner(RenderScope::ScreenHud,nullptr,true,
                                          ProducerToken::StageExtensionTime);
        if(!nativeDraw()||HudBatch.exactUniformOwner()||HudBatch.directStageTicket) return 28;
    }
    start(0);
    {
        ScopedExactProducerSemantic owner(RenderScope::ScreenHud,nullptr,true,
                                          ProducerToken::StageExtensionTime);
        if(!nativeDraw()||HudBatch.homogeneous) return 29;
    }
    start(35);drawResult=FAIL;
    {
        ScopedExactProducerSemantic owner(RenderScope::ScreenHud,nullptr,true,
                                          ProducerToken::StageExtensionTime);
        if(!nativeDraw()||HudBatch.directStageTicket) return 30;
    }
    // Shared vtable receiving a foreign sprite's Flush/End cannot consume
    // or reattribute the tracked game sprite's pending direct batch.
    start(36);
    {
        ScopedExactProducerSemantic owner(RenderScope::ScreenHud,nullptr,true,
                                          ProducerToken::StageExtensionTime);
        if(!nativeDraw()) return 31;
    }
    const auto pending=HudBatch.snapshot();
    if(FlushDest(&node)!=OK||EndDest(&node)!=OK||!HudBatch.unchanged(pending)||
       submissions.size()!=2||
       submissions[0].producer==ProducerToken::StageExtensionTime||
       submissions[1].producer==ProducerToken::StageExtensionTime) return 32;
    std::puts("PASS +TIME actual source exit: rejected queue/VR ticket, native batch preservation, accepted/deferred, mixed, queued, foreign source and lifecycle controls");
    std::puts("PASS production DrawDest/FlushDest/EndDest: native arguments/HRESULT/count, implicit Flush, delayed owner, rejected ticket, new Begin, changed ticket, failed Draw and foreign sprite");
}

