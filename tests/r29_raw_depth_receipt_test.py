#!/usr/bin/env python3
"""Compile actual R29 raw wrappers + R7 receipt helper with fake D3D calls.

Checks the physical-call boundary, not GPU rendering or an atomic stereo transaction.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
r29 = (root / "src/vr/d3d9/stereo_renderer_r29.cpp").read_text()
r7 = (root / "src/vr/d3d9/stereo_renderer_r7.inc").read_text()
raw = r29[r29.index("    HRESULT R29OwnerCallRawDrawPrimitive("):
          r29.index("    HRESULT R29OwnerCallRawPresent(")]
helper = r7[r7.index("void RevokeDepthClearReplayBeforeLeftDraw("):
            r7.index("bool ViewportCoversStereoBackbuffer(")]
raw_vb = r7[r7.index("template<class DrawCall>\n        R7CandidateSeedResult R7ReplayInactiveDraw("):r7.index("bool RestoreRightPassState(")]
# Both base R7 eye calls must route through the very helper compiled below.
base_draw = r7[r7.index("HRESULT ExecuteStereoDraw("):r7.index("HRESULT __stdcall DrawPrimitiveDest(")]
assert "R7ReplayInactiveDraw(device,0,TrackedRenderTarget,\n                    TrackedDepthStencil,drawCall,up,indexedUp)" in base_draw
assert "R7ReplayInactiveDraw(device,1,RightEyeSurface,RightEyeDepth,\n                        drawCall,up,indexedUp)" in base_draw
assert base_draw.count("replay==R7CandidateSeedResult::DirtyRestore") == 2
base_up = r7[r7.index("HRESULT __stdcall DrawPrimitiveUPDest("):r7.index("HRESULT __stdcall DrawIndexedPrimitiveUPDest(")]
base_iup = r7[r7.index("HRESULT __stdcall DrawIndexedPrimitiveUPDest("):r7.index("HRESULT __stdcall ClearDest(")]
assert "ExecuteStereoDraw(device,call,true,true);" in base_up
assert "ExecuteStereoDraw(device,call,true,true,true);" in base_iup
base_entrypoints = base_up + base_iup
prefix = r'''
#define __stdcall
#include "depth_clear_replay_stamp.hpp"
#include <cassert>
#include <atomic>
#include <cstdint>
#include <initializer_list>
#include <iostream>
using DWORD = unsigned;
using UINT = unsigned;
using INT = int;
using HRESULT = int;
using D3DPRIMITIVETYPE = int;
using D3DFORMAT = int;
constexpr DWORD D3DCLEAR_ZBUFFER = 2, D3DCLEAR_STENCIL = 4;
constexpr HRESULT S_OK=0;
struct IDirect3DSurface9 {
    int refs=0; void (*onRelease)()=nullptr;
    void Release(){assert(refs>0);--refs;if(onRelease)onRelease();}
};
struct IDirect3DVertexBuffer9 : IDirect3DSurface9 {};
struct IDirect3DIndexBuffer9 : IDirect3DSurface9 {};
IDirect3DVertexBuffer9 vertexBuffer;
IDirect3DIndexBuffer9 indexBuffer;
struct IDirect3DDevice9 {
    bool game;
    IDirect3DSurface9 *rt=nullptr,*depth=nullptr;
    bool rtFail=false,depthFail=false;
    unsigned rtGets=0,depthGets=0;
    void (*onRtGet)()=nullptr;void (*onDepthGet)()=nullptr;
    IDirect3DVertexBuffer9* vb=nullptr;
    IDirect3DIndexBuffer9* ib=nullptr;
    UINT offset=0,stride=0;
    bool streamGetFail=false,indexGetFail=false,streamSetFail=false,indexSetFail=false;
    unsigned streamSets=0,indexSets=0;
    HRESULT GetStreamSource(UINT,IDirect3DVertexBuffer9** out,UINT* o,UINT* s){
        *out=vb;if(vb)++vb->refs;*o=offset;*s=stride;return streamGetFail?-1:0;
    }
    HRESULT GetIndices(IDirect3DIndexBuffer9** out){*out=ib;if(ib)++ib->refs;return indexGetFail?-1:0;}
    HRESULT SetStreamSource(UINT,IDirect3DVertexBuffer9* p,UINT o,UINT s){
        ++streamSets;if(streamSetFail)return -1;vb=p;offset=o;stride=s;return 0;
    }
    HRESULT SetIndices(IDirect3DIndexBuffer9* p){++indexSets;if(indexSetFail)return -1;ib=p;return 0;}
    HRESULT GetRenderTarget(unsigned,IDirect3DSurface9** out){++rtGets;*out=rt;if(rt)++rt->refs;if(onRtGet)onRtGet();return rtFail?-1:0;}
    HRESULT GetDepthStencilSurface(IDirect3DSurface9** out){++depthGets;*out=depth;if(depth)++depth->refs;if(onDepthGet)onDepthGet();return depthFail?-1:0;}
};
template<class T> void ReleaseCom(T*& p){if(p){p->Release();p=nullptr;}}
constexpr HRESULT E_FAIL=-1;
bool FAILED(HRESULT h){return h<0;}
bool SUCCEEDED(HRESULT h){return h>=0;}
IDirect3DSurface9 leftColor,leftDepth,rightColor,rightDepth,otherColor,otherDepth;
IDirect3DSurface9 *TrackedRenderTarget=&leftColor,*TrackedDepthStencil=&leftDepth,
    *RightEyeSurface=&rightColor,*RightEyeDepth=&rightDepth;
bool FrameStereoIncomplete=false,FrameRightDrawFailed=false,aux=false,mainTarget=true;
bool RightDepthSynchronized=true,RightStencilSynchronized=true;
std::atomic<bool> OcclusionQueryTrackingUnavailable{false};
std::atomic<int> ActiveOcclusionQueries{0};
namespace OutRunVR::DinoSidecar { bool ActiveExternalStereoMesh=false; }
bool TargetIsBackBuffer(){return mainTarget;}
bool AnyAuxRenderTargetActive(){return aux;}
unsigned restoreFailures=0;
void NoteRestoreFailure(const char*){++restoreFailures;}
enum class R7CandidateSeedResult { Unavailable, Seeded, DirtyRestore };
R7CandidateSeedResult replayResult=R7CandidateSeedResult::Seeded;
unsigned replayCalls=0, replayEye=99; bool inReplay=false;
struct CandidatePairMock {std::uint64_t generation=1;IDirect3DDevice9* device=nullptr;} ExternalAtomicCandidates;
std::uint64_t R7CandidateBoundarySerial=0;
bool InternalStereoPass = false;
std::uint64_t PresentEpoch = 77;
std::uint64_t ExternalAtomicReplayEpoch=0;
OutRunVR::DepthClearReplayStamp LastMainDepthClearStamp{};
DWORD writes = 0, expectedAtCall = 0;
unsigned reads = 0, calls = 0, expectedHook = 0;
HRESULT injected = 0, candidateInjected = 0;
bool checkLiveInput=false;
IDirect3DVertexBuffer9* expectedVb=nullptr;
IDirect3DIndexBuffer9* expectedIb=nullptr;
bool IsGameDevice(IDirect3DDevice9* d) { return d && d->game; }
void (*onDepthMask)()=nullptr;void (*onReplayEnd)()=nullptr;
bool LeftDrawMayWriteDepth(IDirect3DDevice9*) { ++reads; if(onDepthMask)onDepthMask(); return writes & 2; }
bool LeftDrawMayWriteStencil(IDirect3DDevice9*) { ++reads; return writes & 4; }
struct Hook {
    unsigned id;
    template<class R, class... Args> R stdcall(IDirect3DDevice9* d,Args...) {
        assert(id == expectedHook);
        assert(LastMainDepthClearStamp.flags == expectedAtCall);
        if(!inReplay&&checkLiveInput){
            assert(d->vb==expectedVb&&d->ib==expectedIb);
            assert(d->offset==(expectedVb?12u:0u)&&d->stride==(expectedVb?32u:0u));
        }
        if(id>=2){d->vb=nullptr;d->offset=d->stride=0;}
        if(id==3)d->ib=nullptr;
        if(inReplay) return candidateInjected;
        ++calls;
        return injected;
    }
};
Hook DrawPrimitiveHook{0}, DrawIndexedPrimitiveHook{1},
     DrawPrimitiveUPHook{2}, DrawIndexedPrimitiveUPHook{3};
template<class DrawCall> R7CandidateSeedResult R7ReplayInactiveEye(IDirect3DDevice9* d,unsigned eye,IDirect3DSurface9* rt,IDirect3DSurface9* depth,DrawCall& draw,bool omit=false){
    assert(d->rt==rt&&d->depth==depth);++replayCalls;replayEye=eye;
    ExternalAtomicCandidates.device=d;
    if(replayResult==R7CandidateSeedResult::Seeded&&!omit){
        inReplay=true;const HRESULT hr=draw();inReplay=false;
        if(FAILED(hr))return R7CandidateSeedResult::Unavailable;
    }
    if(onReplayEnd)onReplayEnd();
    return replayResult;
}
'''
base_dispatch_stub = r'''
unsigned baseDispatches=0;
template<class DrawCall> HRESULT ExecuteStereoDraw(IDirect3DDevice9*,DrawCall&& draw,bool candidate,bool up,bool indexed=false){
    ++baseDispatches;assert(candidate&&up&&indexed==(expectedHook==3));
    if(OutRunVR::DinoSidecar::ActiveExternalStereoMesh)return E_FAIL;
    return draw();
}
'''
suffix = r'''
int main() {
    IDirect3DDevice9 game{true}, other{false};
    unsigned cases=0;
    for(unsigned family=0; family<4; ++family)
    for(bool internal: {false,true})
    for(bool correctDevice: {false,true})
    for(bool current: {false,true})
    for(unsigned cleared: {0u,2u,4u,6u})
    for(unsigned writeMask: {0u,2u,4u,6u})
    for(HRESULT failure: {0,-1,-17}) {
        LastMainDepthClearStamp.Record(current?77:76,cleared);
        InternalStereoPass=internal; writes=writeMask; injected=failure;
        ExternalAtomicReplayEpoch=77;
        expectedHook=family; calls=reads=0;
        const bool relevant=!internal&&correctDevice&&current&&cleared!=0;
        expectedAtCall=relevant?(cleared&~writes):cleared;
        auto* d=correctDevice?&game:&other;
        HRESULT actual=-99;
        switch(family) {
        case 0: actual=R29OwnerCallRawDrawPrimitive(d,0,0,1); break;
        case 1: actual=R29OwnerCallRawDrawIndexedPrimitive(d,0,0,0,3,0,1); break;
        case 2: actual=R29OwnerCallRawDrawPrimitiveUP(d,0,1,nullptr,0); break;
        case 3: actual=R29OwnerCallRawDrawIndexedPrimitiveUP(d,0,0,3,1,nullptr,0,nullptr,0); break;
        }
        assert(actual==failure && calls==1);
        assert(ExternalAtomicReplayEpoch==(correctDevice?0u:77u));
        assert(LastMainDepthClearStamp.flags==expectedAtCall);
        assert(reads==(relevant?unsigned(bool(cleared&2))+unsigned(bool(cleared&4)):0u));
        ++cases;
    }
    // Actual raw dispatch: both eyes, mismatched attachments, getter
    // failures, query/MRT, dirty restore and real live HRESULT propagation.
    for(unsigned family=0;family<2;++family)
    for(unsigned scenario=0;scenario<14;++scenario){
        game.rt=&leftColor;game.depth=&leftDepth;
        game.rtFail=game.depthFail=false;
        aux=false;mainTarget=true;FrameStereoIncomplete=false;FrameRightDrawFailed=false;
        ActiveOcclusionQueries=0;OcclusionQueryTrackingUnavailable=false;
        OutRunVR::DinoSidecar::ActiveExternalStereoMesh=false;
        InternalStereoPass=false;ExternalAtomicReplayEpoch=77;
        LastMainDepthClearStamp.Record(77,0);expectedAtCall=0;
        replayCalls=calls=restoreFailures=0;replayEye=99;expectedHook=family;
        RightDepthSynchronized=RightStencilSynchronized=true;
        replayResult=R7CandidateSeedResult::Seeded;injected=0;
        switch(scenario){
        case 1:game.rt=&rightColor;game.depth=&rightDepth;InternalStereoPass=true;break;
        case 2:game.depth=&rightDepth;break;
        case 3:game.rt=&otherColor;game.depth=&otherDepth;break;
        case 4:game.rtFail=true;break;
        case 5:game.depthFail=true;break;
        case 6:aux=true;break;
        case 7:ActiveOcclusionQueries=1;break;
        case 8:OcclusionQueryTrackingUnavailable=true;break;
        case 9:replayResult=R7CandidateSeedResult::Unavailable;break;
        case 10:replayResult=R7CandidateSeedResult::DirtyRestore;break;
        case 11:injected=-17;break;
        case 12:FrameStereoIncomplete=true;break;
        case 13:OutRunVR::DinoSidecar::ActiveExternalStereoMesh=true;break;
        }
        auto hr=family==0?R29OwnerCallRawDrawPrimitive(&game,0,0,1):
            R29OwnerCallRawDrawIndexedPrimitive(&game,0,0,0,3,0,1);
        const bool replay=scenario<=1||(scenario>=9&&scenario<=11);
        assert(replayCalls==unsigned(replay));
        if(replay)assert(replayEye==unsigned(scenario==1));
        assert(calls==unsigned(scenario!=10));
        assert(hr==(scenario==10?E_FAIL:injected));
        assert(ExternalAtomicReplayEpoch==(scenario<=1?77u:0u));
        assert(restoreFailures==unsigned(scenario==10));
        assert(RightDepthSynchronized==(scenario!=10)&&RightStencilSynchronized==(scenario!=10));
        for(auto* surface:{&leftColor,&leftDepth,&rightColor,&rightDepth,&otherColor,&otherDepth})assert(surface->refs==0);
        ++cases;
    }
    // UP candidate side effects must be restored BEFORE the live call.
    // Getter failure must not draw a candidate; dirty setter failure must
    // never issue a live draw, even if the other restoration setter succeeds.
    for(unsigned family=2;family<4;++family)
    for(bool bound:{false,true})
    for(unsigned scenario=0;scenario<9;++scenario){
        game.rt=&leftColor;game.depth=&leftDepth;
        game.rtFail=game.depthFail=false;aux=false;mainTarget=true;
        FrameStereoIncomplete=FrameRightDrawFailed=false;
        ActiveOcclusionQueries=0;OcclusionQueryTrackingUnavailable=false;
        OutRunVR::DinoSidecar::ActiveExternalStereoMesh=false;
        InternalStereoPass=false;ExternalAtomicReplayEpoch=77;
        LastMainDepthClearStamp.Record(77,0);expectedAtCall=0;
        replayCalls=calls=restoreFailures=0;expectedHook=family;
        RightDepthSynchronized=RightStencilSynchronized=true;
        replayResult=R7CandidateSeedResult::Seeded;injected=candidateInjected=0;
        game.vb=expectedVb=bound?&vertexBuffer:nullptr;
        game.ib=expectedIb=bound?&indexBuffer:nullptr;
        game.offset=bound?12u:0u;game.stride=bound?32u:0u;
        game.streamSets=game.indexSets=0;
        game.streamGetFail=game.indexGetFail=game.streamSetFail=game.indexSetFail=false;
        switch(scenario){
        case 1:game.rt=&rightColor;game.depth=&rightDepth;InternalStereoPass=true;break;
        case 2:game.streamGetFail=true;break;
        case 3:game.indexGetFail=true;break;
        case 4:game.streamSetFail=true;break;
        case 5:game.indexSetFail=true;break;
        case 6:candidateInjected=-17;break;
        case 7:injected=-17;break;
        case 8:ActiveOcclusionQueries=1;break;
        }
        checkLiveInput=true;
        const auto hr=family==2?R29OwnerCallRawDrawPrimitiveUP(&game,0,1,nullptr,0):
            R29OwnerCallRawDrawIndexedPrimitiveUP(&game,0,0,3,1,nullptr,0,nullptr,0);
        checkLiveInput=false;
        const bool dirty=scenario==4||(family==3&&scenario==5);
        const bool captured=scenario!=2&&!(family==3&&scenario==3)&&scenario!=8;
        const bool valid=(scenario<=1||(family==2&&(scenario==3||scenario==5)));
        assert(calls==unsigned(!dirty)&&restoreFailures==unsigned(dirty));
        assert(hr==(dirty?E_FAIL:injected));
        assert(replayCalls==unsigned(scenario!=8));
        assert(game.streamSets==unsigned(captured));
        assert(game.indexSets==unsigned(captured&&family==3));
        assert(ExternalAtomicReplayEpoch==(valid?77u:0u));
        assert(vertexBuffer.refs==0&&indexBuffer.refs==0);
        assert(RightDepthSynchronized==!dirty&&RightStencilSynchronized==!dirty);
        if(!dirty){assert(!game.vb);assert(game.ib==(family==3?nullptr:expectedIb));}
        for(auto* surface:{&leftColor,&leftDepth,&rightColor,&rightDepth,&otherColor,&otherDepth})assert(surface->refs==0);
        ++cases;
    }
    // Base R7 calls the shared candidate helper directly with already-bound eye state.
    // Unlike the raw owner, it must not execute a live draw from this helper.
    for(unsigned family=2;family<4;++family)
    for(unsigned eye=0;eye<2;++eye)
    for(bool bound:{false,true})
    for(unsigned scenario=0;scenario<7;++scenario){
        game.rt=eye?&rightColor:&leftColor;game.depth=eye?&rightDepth:&leftDepth;
        game.vb=bound?&vertexBuffer:nullptr;game.ib=bound?&indexBuffer:nullptr;
        game.offset=bound?12u:0u;game.stride=bound?32u:0u;
        game.streamGetFail=scenario==1;game.indexGetFail=scenario==2;
        game.streamSetFail=scenario==3;game.indexSetFail=scenario==4;
        candidateInjected=scenario==5?-17:0;
        replayResult=scenario==6?R7CandidateSeedResult::DirtyRestore:R7CandidateSeedResult::Seeded;
        ExternalAtomicReplayEpoch=77;LastMainDepthClearStamp.Record(77,0);
        expectedAtCall=0;expectedHook=family;calls=replayCalls=0;
        game.streamSets=game.indexSets=0;
        auto physical=[&](){return family==2?
            DrawPrimitiveUPHook.stdcall<HRESULT>(&game,0,1,nullptr,0):
            DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(&game,0,0,3,1,nullptr,0,nullptr,0);};
        const auto result=R7ReplayInactiveDraw(&game,eye,game.rt,game.depth,physical,true,family==3);
        const bool dirty=scenario==3||(family==3&&scenario==4)||scenario==6;
        const bool clean=scenario==0||(family==2&&(scenario==2||scenario==4));
        assert(result==(dirty?R7CandidateSeedResult::DirtyRestore:
            (clean?R7CandidateSeedResult::Seeded:R7CandidateSeedResult::Unavailable)));
        assert(ExternalAtomicReplayEpoch==(clean?77u:0u));
        assert(calls==0&&replayCalls==1&&replayEye==eye);
        assert(vertexBuffer.refs==0&&indexBuffer.refs==0);
        if(!dirty){
            assert(game.vb==(bound?&vertexBuffer:nullptr));
            assert(game.ib==(bound?&indexBuffer:nullptr));
            assert(game.offset==(bound?12u:0u)&&game.stride==(bound?32u:0u));
        }
        ++cases;
    }
    // Actual base UP entrypoints: internal owners mirror exact bound eyes,
    // mismatches invalidate, dirty input restoration blocks live raster.
    for(unsigned family=2;family<4;++family)
    for(unsigned scenario=0;scenario<9;++scenario){
        game.rt=&leftColor;game.depth=&leftDepth;
        game.rtFail=game.depthFail=false;aux=false;mainTarget=true;
        FrameStereoIncomplete=FrameRightDrawFailed=false;
        ActiveOcclusionQueries=0;OcclusionQueryTrackingUnavailable=false;
        OutRunVR::DinoSidecar::ActiveExternalStereoMesh=false;
        InternalStereoPass=true;ExternalAtomicReplayEpoch=77;
        LastMainDepthClearStamp.Record(77,0);expectedAtCall=0;
        replayCalls=calls=restoreFailures=baseDispatches=0;expectedHook=family;
        RightDepthSynchronized=RightStencilSynchronized=true;
        replayResult=R7CandidateSeedResult::Seeded;injected=candidateInjected=0;
        game.vb=expectedVb=&vertexBuffer;game.ib=expectedIb=&indexBuffer;
        game.offset=12;game.stride=32;
        game.streamGetFail=game.indexGetFail=game.streamSetFail=game.indexSetFail=false;
        switch(scenario){
        case 1:game.rt=&rightColor;game.depth=&rightDepth;break;
        case 2:game.depth=&rightDepth;break;
        case 3:game.depth=nullptr;break;
        case 4:game.streamSetFail=true;break;
        case 5:game.streamGetFail=true;break;
        case 6:OutRunVR::DinoSidecar::ActiveExternalStereoMesh=true;break;
        case 7:InternalStereoPass=false;break;
        case 8:ActiveOcclusionQueries=1;break;
        }
        checkLiveInput=true;
        const auto hr=family==2?DrawPrimitiveUPDest(&game,0,1,nullptr,0):
            DrawIndexedPrimitiveUPDest(&game,0,0,3,1,nullptr,0,nullptr,0);
        checkLiveInput=false;
        assert(baseDispatches==unsigned(scenario==6||scenario==7));
        assert(replayCalls==unsigned(scenario<=1||scenario==4||scenario==5));
        assert(calls==unsigned(scenario!=4&&scenario!=6));
        assert(hr==((scenario==4||scenario==6)?E_FAIL:0));
        assert(restoreFailures==unsigned(scenario==4));
        assert(ExternalAtomicReplayEpoch==((scenario<=1||scenario==6||scenario==7)?77u:0u));
        if(scenario<=1)assert(replayEye==scenario);
        assert(vertexBuffer.refs==0&&indexBuffer.refs==0);
        for(auto* surface:{&leftColor,&leftDepth,&rightColor,&rightDepth,&otherColor,&otherDepth})assert(surface->refs==0);
        ++cases;
    }
    // Actual raw replay owner used by the internal Clear entrypoint.
    // Clear flags, not render-state masks, govern the LEFT receipt.
    for(DWORD flags:{1u,2u,4u,7u})
    for(unsigned scenario=0;scenario<10;++scenario){
        game.rt=&leftColor;game.depth=&leftDepth;
        game.rtFail=game.depthFail=false;aux=false;mainTarget=true;
        FrameStereoIncomplete=FrameRightDrawFailed=false;
        ActiveOcclusionQueries=0;OcclusionQueryTrackingUnavailable=false;
        OutRunVR::DinoSidecar::ActiveExternalStereoMesh=false;
        InternalStereoPass=true;ExternalAtomicReplayEpoch=77;
        LastMainDepthClearStamp.Record(77,6);writes=0;
        replayCalls=calls=restoreFailures=0;replayEye=99;
        RightDepthSynchronized=RightStencilSynchronized=true;
        replayResult=R7CandidateSeedResult::Seeded;injected=candidateInjected=0;
        switch(scenario){
        case 1:game.rt=&rightColor;game.depth=&rightDepth;break;
        case 2:game.depth=&rightDepth;break;
        case 3:game.rtFail=true;break;
        case 4:replayResult=R7CandidateSeedResult::Unavailable;break;
        case 5:replayResult=R7CandidateSeedResult::DirtyRestore;break;
        case 6:injected=-17;break;
        case 7:candidateInjected=-17;break;
        case 8:ActiveOcclusionQueries=1;break;
        case 9:ExternalAtomicReplayEpoch=0;break;
        }
        unsigned candidateClears=0;
        auto clear=[&](){
            if(inReplay){++candidateClears;return candidateInjected;}
            ++calls;return injected;
        };
        const auto hr=R7ExecuteRawCandidateVb(&game,clear,false,false,flags);
        const bool dirty=scenario==5;
        const bool replay=scenario<=1||(scenario>=4&&scenario<=7);
        assert(replayCalls==unsigned(replay));
        assert(candidateClears==unsigned(replay&&scenario!=4&&scenario!=5));
        assert(calls==unsigned(!dirty)&&restoreFailures==unsigned(dirty));
        assert(hr==(dirty?E_FAIL:injected));
        assert(ExternalAtomicReplayEpoch==(scenario<=1?77u:0u));
        const DWORD expected=dirty?0u:(scenario==1||scenario==9?6u:(6u&~flags));
        assert(LastMainDepthClearStamp.flags==expected);
        assert(RightDepthSynchronized==!dirty&&RightStencilSynchronized==!dirty);
        for(auto* surface:{&leftColor,&leftDepth,&rightColor,&rightDepth,&otherColor,&otherDepth})assert(surface->refs==0);
        ++cases;
    }
    // Actual outer raw transaction: retire at each driver boundary, even
    // after a successful inner replay. Same-generation Present declines
    // candidate raster but keeps one physical stock call and its HRESULT.
    static unsigned interruptMode=0;
    auto interrupt=+[](){
        if(interruptMode==1)++ExternalAtomicCandidates.generation;
        if(interruptMode==2)++R7CandidateBoundarySerial;
        if(interruptMode==3)++PresentEpoch;
    };
    unsigned boundaryCases=0;
    for(unsigned eye=0;eye<2;++eye)
    for(unsigned phase=0;phase<=7;++phase)
    for(interruptMode=1;interruptMode<=3;++interruptMode)
    for(bool failedGetter:{false,true}){
        game.rt=eye?&rightColor:&leftColor;game.depth=eye?&rightDepth:&leftDepth;
        game.rtFail=failedGetter&&phase==1;game.depthFail=failedGetter&&phase==2;
        game.rtGets=game.depthGets=0;
        game.onRtGet=phase==1?interrupt:nullptr;
        game.onDepthGet=phase==2?interrupt:nullptr;
        onDepthMask=phase==3?interrupt:nullptr;
        onReplayEnd=phase==4?interrupt:nullptr;
        game.depth->onRelease=phase==5?interrupt:nullptr;
        game.rt->onRelease=phase==6?interrupt:nullptr;
        aux=false;mainTarget=true;FrameStereoIncomplete=FrameRightDrawFailed=false;
        ActiveOcclusionQueries=0;OcclusionQueryTrackingUnavailable=false;
        OutRunVR::DinoSidecar::ActiveExternalStereoMesh=false;
        InternalStereoPass=eye!=0;
        PresentEpoch=ExternalAtomicReplayEpoch=77;
        ExternalAtomicCandidates.device=&game;
        LastMainDepthClearStamp.Record(77,2);writes=0;
        calls=replayCalls=restoreFailures=reads=0;
        RightDepthSynchronized=RightStencilSynchronized=true;
        replayResult=R7CandidateSeedResult::Seeded;
        auto physical=[&](){
            if(!inReplay){++calls;if(phase==7)interrupt();return -17;}
            return 0;
        };
        const auto hr=R7ExecuteRawCandidateVb(&game,physical);
        const bool reached=phase!=0&&!(eye&&phase==3);
        const bool retired=reached&&interruptMode==1&&phase!=7;
        const bool replay=!(reached&&phase<=3);
        assert(game.rtGets==1&&game.depthGets==unsigned(phase!=1));
        assert(replayCalls==unsigned(replay));
        assert(calls==unsigned(!retired)&&hr==(retired?E_FAIL:-17));
        assert(restoreFailures==unsigned(retired));
        assert(RightDepthSynchronized==!retired&&RightStencilSynchronized==!retired);
        assert(ExternalAtomicReplayEpoch==0);
        if(retired)assert(LastMainDepthClearStamp.flags==0);
        assert(game.rt->refs==0&&game.depth->refs==0);
        game.onRtGet=game.onDepthGet=onDepthMask=onReplayEnd=nullptr;
        game.rt->onRelease=game.depth->onRelease=nullptr;
        ++boundaryCases;
    }
    assert(boundaryCases==96);
    std::cout<<"R7_RAW_CAPTURE_GENERATION_PASS "<<boundaryCases<<"\n";
    PresentEpoch=77;
    // Independent offscreen raw writes preserve a current candidate, but a
    // failed write or retirement cannot retain the old receipt.
    unsigned auxCases=0;
    for(bool fail:{false,true})for(bool retire:{false,true}){
        disjointRaw=true;
        ExternalAtomicReplayEpoch=PresentEpoch=77;
        const auto hr=R7ExecuteRawCandidateVb(&game,[&](){
            if(retire)++R7CandidateBoundarySerial;
            return fail?E_FAIL:0;
        });
        assert(hr==(fail?E_FAIL:0));
        assert(ExternalAtomicReplayEpoch==((fail||retire)?0u:77u));
        disjointRaw=false;++auxCases;
    }
    assert(auxCases==4);
    // Actual unmirrored raster helper, including failing stock calls.
    unsigned fallbackCases=0;
    for(bool gameDevice:{false,true})
    for(bool clear:{false,true})
    for(bool current:{false,true})
    for(DWORD cleared:{0u,2u,4u,6u})
    for(DWORD flags:{0u,1u,2u,4u,7u})
    for(DWORD mask:{0u,2u,4u,6u})
    for(HRESULT result:{0,-1,-17}){
        InternalStereoPass=false;
        LastMainDepthClearStamp.Record(current?77:76,cleared);
        ExternalAtomicReplayEpoch=77;writes=mask;reads=calls=0;
        const DWORD expected=gameDevice?(clear?(cleared&~flags):
            (current?(cleared&~mask):cleared)):cleared;
        auto rawWrite=[&](){
            ++calls;
            assert(ExternalAtomicReplayEpoch==(gameDevice?0u:77u));
            assert(LastMainDepthClearStamp.flags==expected);
            return result;
        };
        assert(R7ExecuteUnmirroredGameRaster(gameDevice?&game:&other,rawWrite,clear,flags)==result);
        assert(calls==1);
        assert(reads==unsigned(gameDevice&&!clear&&current)*
            (unsigned((cleared&2)!=0)+unsigned((cleared&4)!=0)));
        ++fallbackCases;
    }
    std::cout << "R7_UNMIRRORED_RASTER_PASS " << fallbackCases << "\n";
    std::cout << "R29_RAW_DEPTH_RECEIPT_PASS " << cases << "\\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p / "probe.cpp").write_text(prefix + "bool disjointRaw=false;\nbool R7CandidateDisjointOffscreenRaster(IDirect3DDevice9*){return disjointRaw;}\n" + helper + "struct R7NativeOmissionTicket {void* owner=nullptr;};\nR7NativeOmissionTicket R7CaptureNativeStockOmission(){return {};}\nvoid R7RecordNativeStockOmission(const R7NativeOmissionTicket&,unsigned,R7CandidateSeedResult){}\n"+raw_vb + raw + base_dispatch_stub + base_entrypoints + suffix)
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic", "-I", str(root / "src/vr/d3d9"),
                    str(p / "probe.cpp"), "-o", str(p / "probe")], check=True)
    subprocess.run([str(p / "probe")], check=True)

# Exact R22 entrypoints and R9 raw/mono ownership wiring.
r22=(root / "src/vr/d3d9/stereo_renderer_r22.cpp").read_text()
r9=(root / "src/vr/d3d9/stereo_renderer.cpp").read_text()
r9clear=r9[r9.index("HRESULT __stdcall ClearDestR9("):r9.index("template <typename ActualDraw, typename LegacyDraw>")]
r9draw=r9[r9.index("HRESULT R9ExecuteDraw("):r9.index("HRESULT __stdcall DrawPrimitiveDestR9(")]
assert r9clear.count("R7ExecuteUnmirroredGameRaster(device,")==3
assert r9draw.count("return R7ExecuteUnmirroredGameRaster(device,actualDraw);")==5
assert "R9ReplayMonoDraw(device, actualDraw, monoHr)" in r9draw
assert "return actualDraw();" not in r9draw
r22owner=r22[r22.index("HRESULT __stdcall ClearDestR22("):r22.index("void R22RollbackHooks()")]
assert r22owner.count("R7ExecuteUnmirroredGameRaster(device,")==10
assert r22owner.count("},true,flags);")==2
r22stub=r'''
#include "depth_clear_replay_stamp.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <initializer_list>
#define __stdcall
using DWORD=unsigned;using UINT=unsigned;using INT=int;using HRESULT=int;
using D3DCOLOR=unsigned;using D3DPRIMITIVETYPE=int;using D3DFORMAT=int;
constexpr DWORD D3DCLEAR_ZBUFFER=2,D3DCLEAR_STENCIL=4;
struct D3DRECT{};
struct IDirect3DDevice9{bool game;};
bool InternalStereoPass=false,eligible=true,captured=true;
bool R9StereoSeeded=true,RightDepthSynchronized=true,RightStencilSynchronized=true;
unsigned R22GameScissor=0;
std::uint64_t ExternalAtomicReplayEpoch=77,PresentEpoch=77;
OutRunVR::DepthClearReplayStamp LastMainDepthClearStamp{};
bool IsGameDevice(IDirect3DDevice9* d){return d&&d->game;}
bool LeftDrawMayWriteDepth(IDirect3DDevice9*){return true;}
bool LeftDrawMayWriteStencil(IDirect3DDevice9*){return false;}
bool R22StereoCallbacksEligible(){return eligible;}
struct R22ReplayScope{bool stateValid;explicit R22ReplayScope(IDirect3DDevice9*):stateValid(captured){}};
unsigned failures=0,calls=0,expectedFamily=0;bool expectRaw=false;HRESULT result=0;
DWORD expectedStamp=6;
void R22FailClosedReplayState(IDirect3DDevice9*,const char*){++failures;}
bool TargetIsBackBuffer(){return true;}
bool R22GameClearCoversBackbuffer(DWORD,const D3DRECT*,unsigned){return true;}
void R22ObserveDepthBaseline(bool,bool,DWORD,HRESULT){}
void R22CancelUnsafeFirstSeed(IDirect3DDevice9*,bool,bool){}
bool SUCCEEDED(HRESULT h){return h>=0;}
struct Hook{
    unsigned family;bool raw;
    template<class R,class... Args> R stdcall(IDirect3DDevice9*,Args...){
        assert(family==expectedFamily&&raw==expectRaw);
        assert(ExternalAtomicReplayEpoch==(raw?0u:77u));
        assert(LastMainDepthClearStamp.flags==expectedStamp);
        ++calls;return result;
    }
};
Hook ClearHook{0,true},DrawPrimitiveHook{1,true},DrawIndexedPrimitiveHook{2,true},
     DrawPrimitiveUPHook{3,true},DrawIndexedPrimitiveUPHook{4,true};
Hook R22ClearR20Hook{0,false},R22DrawPrimitiveR9Hook{1,false},
     R22DrawIndexedPrimitiveR9Hook{2,false},R22DrawPrimitiveUPR9Hook{3,false},
     R22DrawIndexedPrimitiveUPR9Hook{4,false};
'''
r22cases=r'''
int main(){
    IDirect3DDevice9 game{true},other{false};
    unsigned cases=0;
    for(unsigned family=0;family<5;++family)
    for(unsigned mask=0;mask<16;++mask)
    for(HRESULT hr:{0,-1,-17}){
        auto* d=(mask&1)?&other:&game;
        InternalStereoPass=mask&2;eligible=!(mask&4);captured=!(mask&8);
        const bool top=!(mask&3);
        expectRaw=top&&(!eligible||!captured);
        expectedFamily=family;result=hr;calls=failures=0;
        ExternalAtomicReplayEpoch=77;LastMainDepthClearStamp.Record(77,6);
        expectedStamp=expectRaw?4u:6u;
        HRESULT got=-99;
        switch(family){
        case 0:got=ClearDestR22(d,0,nullptr,2,0,1.f,0);break;
        case 1:got=DrawPrimitiveDestR22(d,0,0,1);break;
        case 2:got=DrawIndexedPrimitiveDestR22(d,0,0,0,3,0,1);break;
        case 3:got=DrawPrimitiveUPDestR22(d,0,1,nullptr,0);break;
        case 4:got=DrawIndexedPrimitiveUPDestR22(d,0,0,3,1,nullptr,0,nullptr,0);break;
        }
        assert(got==hr&&calls==1&&failures==unsigned(top&&eligible&&!captured));
        ++cases;
    }
    std::cout<<"R22_RAW_FALLBACK_ENTRYPOINTS_PASS "<<cases<<"\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    p=Path(directory)
    (p/"probe.cpp").write_text(r22stub+"bool R7CandidateDisjointOffscreenRaster(IDirect3DDevice9*){return false;}\n"+helper+r22owner+r22cases)
    subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror","-pedantic",
                    "-I",str(root/"src/vr/d3d9"),str(p/"probe.cpp"),"-o",str(p/"probe")],check=True)
    subprocess.run([str(p/"probe")],check=True)
