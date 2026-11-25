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
struct IDirect3DSurface9 { int refs=0; void Release(){assert(refs>0);--refs;} };
struct IDirect3DVertexBuffer9 : IDirect3DSurface9 {};
struct IDirect3DIndexBuffer9 : IDirect3DSurface9 {};
IDirect3DVertexBuffer9 vertexBuffer;
IDirect3DIndexBuffer9 indexBuffer;
struct IDirect3DDevice9 {
    bool game;
    IDirect3DSurface9 *rt=nullptr,*depth=nullptr;
    bool rtFail=false,depthFail=false;
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
    HRESULT GetRenderTarget(unsigned,IDirect3DSurface9** out){*out=rt;if(rt)++rt->refs;return rtFail?-1:0;}
    HRESULT GetDepthStencilSurface(IDirect3DSurface9** out){*out=depth;if(depth)++depth->refs;return depthFail?-1:0;}
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
bool LeftDrawMayWriteDepth(IDirect3DDevice9*) { ++reads; return writes & 2; }
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
template<class DrawCall> R7CandidateSeedResult R7ReplayInactiveEye(IDirect3DDevice9* d,unsigned eye,IDirect3DSurface9* rt,IDirect3DSurface9* depth,DrawCall& draw){
    assert(d->rt==rt&&d->depth==depth);++replayCalls;replayEye=eye;
    if(replayResult==R7CandidateSeedResult::Seeded){
        inReplay=true;const HRESULT hr=draw();inReplay=false;
        if(FAILED(hr))return R7CandidateSeedResult::Unavailable;
    }
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
    std::cout << "R29_RAW_DEPTH_RECEIPT_PASS " << cases << "\\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p / "probe.cpp").write_text(prefix + helper + raw_vb + raw + base_dispatch_stub + base_entrypoints + suffix)
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic", "-I", str(root / "src/vr/d3d9"),
                    str(p / "probe.cpp"), "-o", str(p / "probe")], check=True)
    subprocess.run([str(p / "probe")], check=True)
