#!/usr/bin/env python3
"""Fault-inject the actual R7 bootstrap and restore functions, not GPU pixels."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
r7 = (root / "src/vr/d3d9/stereo_renderer_r7.inc").read_text()
r29 = (root / "src/vr/d3d9/stereo_renderer_r29.cpp").read_text()
body = r7[r7.index("bool RestoreRightPassState("):
          r7.index("std::uint32_t NextStereoFrameId()")]
prepare = r7[r7.index("bool PrepareDuplicatedDraw("):
             r7.index("struct R7VisualTraceContext")]
draw = r7[r7.index("HRESULT ExecuteStereoDraw("):
          r7.index("HRESULT __stdcall DrawPrimitiveUPDest(")]
assert prepare.index("if(bootstrapRestoreFailed)return false;") < prepare.index("BuildEyeConstants(")
assert draw.index("if(bootstrapRestoreFailed){") < draw.index("return E_FAIL; // no raw LEFT fallback")
assert draw.index("return E_FAIL; // no raw LEFT fallback") < draw.index("PREPARE_REJECT_SINGLE")
owner = r29[r29.index("HRESULT R29GuardStableDraw("):]
assert owner.index("if (bootstrapRestoreFailed)") < owner.index("if ((!RightDepthSynchronized")
prefix = r'''
#include "depth_clear_replay_stamp.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
using HRESULT=int; using DWORD=unsigned;
constexpr HRESULT E_FAIL=-1;
#define FAILED(x) ((x)<0)
#define SUCCEEDED(x) ((x)>=0)
constexpr DWORD D3DCLEAR_ZBUFFER=2,D3DCLEAR_STENCIL=4;
struct D3DRECT{};
struct D3DSURFACE_DESC { unsigned Width=100,Height=100,Format=1,MultiSampleType=0,MultiSampleQuality=0; };
struct CandidatePairMock {std::uint64_t generation=1;} ExternalAtomicCandidates;
unsigned probeStep=0,retireProbe=0,retireStep=0;
bool retireCandidate=false;
void probe(){if(++probeStep==retireProbe)++ExternalAtomicCandidates.generation;}
struct IDirect3DSurface9 {
    D3DSURFACE_DESC desc{};
    HRESULT GetDesc(D3DSURFACE_DESC* d){*d=desc;probe();return 0;}
};
struct D3DVIEWPORT9 { unsigned X=0,Y=0,Width=100,Height=100; };
unsigned step=0,failAt=0,clearCalls=0,restoreCalls=0,notes=0;
unsigned bootstrapCandidateClears=0;
bool inCandidate=false;
bool testingFollowup=false;
unsigned followupCalls[2]{},followupClears[2]{};

HRESULT candidateClearHr=0;
HRESULT call(){++step;if(step==retireStep)++ExternalAtomicCandidates.generation;return step==failAt?E_FAIL:0;}
struct IDirect3DDevice9 {
    HRESULT GetViewport(D3DVIEWPORT9* v){*v={};probe();return 0;}
    HRESULT SetViewport(const D3DVIEWPORT9*){return call();}
    HRESULT SetDepthStencilSurface(IDirect3DSurface9*){return call();}
};
struct Hook {
    unsigned kind;
    explicit operator bool()const{return true;}
    template<class R,class... Args> R stdcall(Args...){
        if(kind==2&&inCandidate){++bootstrapCandidateClears;return candidateClearHr;}
        if(kind==2)++clearCalls;
        return call();
    }
};
Hook SetRenderTargetHook{0},SetDepthStencilSurfaceHook{1},ClearHook{2};
struct InternalPassScope{};
IDirect3DSurface9 leftRt,leftDepth,rightRt,rightDepth;
IDirect3DSurface9 *TrackedRenderTarget=&leftRt,*TrackedDepthStencil=&leftDepth,
    *RightEyeSurface=&rightRt,*RightEyeDepth=&rightDepth;
D3DSURFACE_DESC BackBufferDesc{},LastMainDepthClearDesc{};
OutRunVR::DepthClearReplayStamp LastMainDepthClearStamp{};
bool RightDepthSynchronized=false,RightStencilSynchronized=false,FirstDepthBootstrapLogged=true;
unsigned DepthBootstrapAttempts=0,DepthBootstrapSuccesses=0;
std::uint64_t PresentEpoch=7;
std::uint64_t ExternalAtomicReplayEpoch=0;
enum class R7CandidateSeedResult { Unavailable, Seeded, DirtyRestore };
R7CandidateSeedResult bootstrapReplay=R7CandidateSeedResult::Unavailable;
R7CandidateSeedResult followupResults[2]{R7CandidateSeedResult::Seeded,R7CandidateSeedResult::Seeded};
unsigned bootstrapReplayCalls=0;
template<class Call> R7CandidateSeedResult R7ReplayInactiveEye(IDirect3DDevice9*,
    unsigned eye,IDirect3DSurface9* rt,IDirect3DSurface9* depth,Call& clear){
    if(testingFollowup){
        assert(eye<2&&rt==(eye?RightEyeSurface:TrackedRenderTarget)&&depth==(eye?RightEyeDepth:TrackedDepthStencil));
        ++followupCalls[eye];
        const auto outcome=followupResults[eye];
        if(outcome==R7CandidateSeedResult::Seeded){
            ++followupClears[eye];inCandidate=true;const auto hr=clear();inCandidate=false;
            return FAILED(hr)?R7CandidateSeedResult::Unavailable:outcome;
        }
        return outcome;
    }
    assert(eye==1&&rt==RightEyeSurface&&depth==RightEyeDepth);
    ++bootstrapReplayCalls;
    if(retireCandidate)++ExternalAtomicCandidates.generation;
    if(bootstrapReplay==R7CandidateSeedResult::Seeded){
        inCandidate=true;const auto hr=clear();inCandidate=false;
        return FAILED(hr)?R7CandidateSeedResult::Unavailable:bootstrapReplay;
    }
    return bootstrapReplay;
}
float LastMainDepthClearZ=1;
DWORD LastMainDepthClearStencil=0;
bool DepthDescMatches(const D3DSURFACE_DESC& a,const D3DSURFACE_DESC& b){
    return a.Width==b.Width&&a.Height==b.Height&&a.Format==b.Format;
}
bool FormatHasStencil(unsigned){return true;}
bool RestoreWvpOneRegisterAtATime(IDirect3DDevice9*,const float*){return true;}
void NoteRestoreFailure(const char*){++notes;}
namespace spdlog{template<class... T> void info(T...){}}
'''
suffix = r'''
int main(){
    IDirect3DDevice9 dev;
    // Setup RT, depth, viewport, clear; then independent RT/depth/viewport
    // restore attempts. On setup failure the restoration still runs.
    for(unsigned failure=0;failure<=7;++failure){
        step=clearCalls=notes=DepthBootstrapSuccesses=0;
        failAt=failure;
        RightDepthSynchronized=RightStencilSynchronized=false;
        LastMainDepthClearStamp.Record(7,6);
        bool dirty=true;
        ExternalAtomicReplayEpoch=7;
        const bool ok=TryBootstrapRightDepthFromRecentClear(&dev,&dirty);
        assert(ExternalAtomicReplayEpoch==0);
        assert(ok==(failure==0));
        const bool restoreFailed=failure>=5;
        assert(dirty==restoreFailed && notes==unsigned(restoreFailed));
        assert(RightDepthSynchronized==ok && RightStencilSynchronized==ok);
        assert(DepthBootstrapSuccesses==unsigned(ok));
        assert(LastMainDepthClearStamp.Current(7)==!restoreFailed);
        assert(clearCalls==unsigned(failure==0||failure>=4));
        assert(step==(failure>=1&&failure<=3?failure+3:7));
        if(restoreFailed){
            const auto before=step;
            assert(!TryBootstrapRightDepthFromRecentClear(&dev,&dirty));
            assert(!dirty && step==before); // invalidated receipt cannot replay
        }
    }
    // Exact bootstrap body: candidate RIGHT replay precedes live Clear;
    // unavailable/failed candidate permits stock, dirty restore vetoes live.
    for(auto result:{R7CandidateSeedResult::Seeded,R7CandidateSeedResult::Unavailable,
                     R7CandidateSeedResult::DirtyRestore})
    for(unsigned failure:{0u,1u,4u,5u})
    for(HRESULT candidateHr:{0,E_FAIL}){
        step=clearCalls=notes=DepthBootstrapSuccesses=0;
        bootstrapReplayCalls=bootstrapCandidateClears=0;
        failAt=failure;bootstrapReplay=result;candidateClearHr=candidateHr;
        RightDepthSynchronized=RightStencilSynchronized=false;
        LastMainDepthClearStamp.Record(7,6);ExternalAtomicReplayEpoch=7;
        bool dirty=false;
        const bool reached=failure!=1;
        const bool innerDirty=reached&&result==R7CandidateSeedResult::DirtyRestore;
        const bool outerDirty=(failure==5&&!innerDirty) || (failure==4&&innerDirty);
        const bool ok=TryBootstrapRightDepthFromRecentClear(&dev,&dirty);
        assert(bootstrapReplayCalls==unsigned(reached));
        assert(bootstrapCandidateClears==unsigned(reached&&result==R7CandidateSeedResult::Seeded));
        assert(clearCalls==unsigned(reached&&!innerDirty));
        assert(dirty==(innerDirty||outerDirty));
        assert(notes==unsigned(dirty));
        assert(ok==(failure==0&&!innerDirty));
        assert(RightDepthSynchronized==ok&&RightStencilSynchronized==ok);
        assert(LastMainDepthClearStamp.Current(7)==!dirty);
        const bool retained=ok&&result==R7CandidateSeedResult::Seeded&&candidateHr==0;
        assert(ExternalAtomicReplayEpoch==(retained?7u:0u));
    }
    // Generation retirement at each getter, setter, inner replay, live
    // clear and restore must stop further calls on the retired device.
    unsigned retirementCases=0;
    for(unsigned phase=0;phase<=11;++phase)
    for(bool failing:{false,true}){
        step=probeStep=clearCalls=notes=DepthBootstrapSuccesses=0;
        bootstrapReplayCalls=bootstrapCandidateClears=0;
        retireProbe=phase<=3?phase:0;
        retireStep=phase>=4&&phase<=10?phase-3:0;
        retireCandidate=phase==11;
        failAt=failing?retireStep:0;
        bootstrapReplay=R7CandidateSeedResult::Unavailable;
        RightDepthSynchronized=RightStencilSynchronized=false;
        LastMainDepthClearStamp.Record(7,6);ExternalAtomicReplayEpoch=7;
        bool dirty=false;
        const bool ok=TryBootstrapRightDepthFromRecentClear(&dev,&dirty);
        assert(ok==(phase==0)&&dirty==(phase!=0));
        assert(notes==unsigned(phase!=0)&&DepthBootstrapSuccesses==unsigned(ok));
        assert(RightDepthSynchronized==ok&&RightStencilSynchronized==ok);
        assert(LastMainDepthClearStamp.Current(7)==ok);
        assert(probeStep==(phase>=1&&phase<=3?phase:3u));
        assert(step==(phase>=1&&phase<=3?0u:phase>=4&&phase<=10?phase-3:phase==11?3u:7u));
        assert(clearCalls==unsigned(phase==0||(phase>=7&&phase<=10)));
        assert(ExternalAtomicReplayEpoch==0);
        ++retirementCases;
    }
    retireProbe=retireStep=0;retireCandidate=false;
    std::cout<<"R7_BOOTSTRAP_GENERATION_PASS "<<retirementCases<<"\n";
    // No opt-in/receipt: do not perform any candidate operations.
    step=clearCalls=notes=bootstrapReplayCalls=bootstrapCandidateClears=0;
    failAt=0;RightDepthSynchronized=RightStencilSynchronized=false;
    LastMainDepthClearStamp.Record(7,6);ExternalAtomicReplayEpoch=0;
    assert(TryBootstrapRightDepthFromRecentClear(&dev));
    assert(bootstrapReplayCalls==0&&bootstrapCandidateClears==0&&clearCalls==1&&step==7);
    LastMainDepthClearStamp.Record(7,6);
    TrackedRenderTarget=nullptr;step=0;bool dirty=true;
    assert(!TryBootstrapRightDepthFromRecentClear(&dev,&dirty)&&!dirty&&step==0);
    std::cout<<"R7_DEPTH_BOOTSTRAP_RESTORE_PASS\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p / "probe.cpp").write_text(prefix + body + suffix)
    subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror",
                    "-Wno-unused-variable","-I",str(root / "src/vr/d3d9"),
                    str(p/"probe.cpp"),"-o",str(p/"probe")],check=True)
    subprocess.run([str(p/"probe")],check=True)

# Iter54: exercise the actual ClearDest body with the same mocked driver
# and actual RestoreRightPassState. A color-only clear must also revoke
# both depth/stencil proofs when restoration is dirty.
clear_body = r7[r7.index("HRESULT __stdcall ClearDest("):
                r7.index("HRESULT __stdcall SetRenderTargetDest(")]
clear_prefix = prefix + r'''
#include <atomic>
#define __stdcall
using D3DCOLOR=unsigned;
constexpr DWORD D3DCLEAR_TARGET=1;
constexpr HRESULT D3D_OK=0;
std::atomic<bool> StereoBaseCallbacksArmed{true};
bool InternalStereoPass=false, wanted=true, backbuffer=true,
    mrt=false, resources=true, coverage=true, FrameRightDrawFailed=false,FrameStereoIncomplete=false;
unsigned coverageCalls=0, poisons=0, candidateCalls=0;
unsigned internalClearCalls=0;
DWORD internalClearFlags=0;
template<class Call> HRESULT R7ExecuteRawCandidateVb(IDirect3DDevice9*,Call&& call,bool up,bool indexed,DWORD flags){
    assert(!up&&!indexed);++internalClearCalls;internalClearFlags=flags;
    return call();
}
namespace Settings { bool VRExternalFerrariTest=false,VRF50ExternalModel=false; }
R7CandidateSeedResult candidateResult=R7CandidateSeedResult::Unavailable;
R7CandidateSeedResult R7BeginExternalAtomicResourceTransaction(IDirect3DDevice9*,
    const D3DVIEWPORT9&,DWORD,D3DCOLOR,float,DWORD){
    ++candidateCalls;return candidateResult;
}
namespace OutRunVR {
enum Failure {StereoFailureMrtActive, StereoFailureResourceUnavailable,
    StereoFailureClearFailed, StereoFailureViewportUnavailable};
}
void PoisonFrame(OutRunVR::Failure){++poisons;}
bool IsGameDevice(IDirect3DDevice9* d){return d!=nullptr;}
bool StereoWanted(){return wanted;}
bool TargetIsBackBuffer(){return backbuffer;}
bool AnyAuxRenderTargetActive(){return mrt;}
bool EnsureStereoResources(IDirect3DDevice9*){return resources;}
bool SurfaceHasStencil(IDirect3DSurface9* s){return s!=nullptr;}
bool ClearCoversStereoBackbuffer(IDirect3DDevice9*,DWORD,const D3DRECT*){
    ++coverageCalls;return coverage;
}
void RecordFullMainDepthClear(IDirect3DDevice9*,DWORD,const D3DRECT*,DWORD flags,float,DWORD){
    const auto bits=flags&(D3DCLEAR_ZBUFFER|D3DCLEAR_STENCIL);
    if(bits&&backbuffer&&coverage)LastMainDepthClearStamp.Record(PresentEpoch,bits);
}
'''
clear_suffix = r'''
void ResetProbe(unsigned failure){
    step=clearCalls=notes=poisons=coverageCalls=candidateCalls=0;failAt=failure;
    Settings::VRExternalFerrariTest=Settings::VRF50ExternalModel=false;
    candidateResult=R7CandidateSeedResult::Unavailable;
    RightDepthSynchronized=RightStencilSynchronized=true;
    FrameRightDrawFailed=FrameStereoIncomplete=false;
    testingFollowup=false;followupCalls[0]=followupCalls[1]=followupClears[0]=followupClears[1]=0;
    candidateClearHr=0;
    LastMainDepthClearStamp.Record(PresentEpoch,6);
    wanted=backbuffer=resources=coverage=true;mrt=false;
    InternalStereoPass=false;StereoBaseCallbacksArmed=true;
    internalClearCalls=internalClearFlags=0;ExternalAtomicReplayEpoch=0;
}
int main(){
    IDirect3DDevice9 dev;
    // LEFT clear, then RIGHT RT/depth/viewport/clear, then all three
    // restore calls. For setup failures all restore calls still run.
    for(DWORD flags:{1u,2u,4u,6u,7u})
        for(unsigned failure=0;failure<=8;++failure){
            ResetProbe(failure);
            const HRESULT hr=ClearDest(&dev,0,nullptr,flags,0,1.f,0);
            const bool dirty=failure>=6;
            assert(hr==((failure==1||dirty)?E_FAIL:D3D_OK));
            assert(notes==unsigned(dirty));
            assert(coverageCalls==unsigned(failure==0));
            if(dirty){
                assert(!RightDepthSynchronized&&!RightStencilSynchronized);
                assert(!LastMainDepthClearStamp.Current(PresentEpoch));
                const unsigned before=step;
                bool restoreFailed=true;
                assert(!TryBootstrapRightDepthFromRecentClear(&dev,&restoreFailed));
                assert(!restoreFailed&&step==before);
            }else if(failure>=2){
                assert(RightDepthSynchronized==!(flags&D3DCLEAR_ZBUFFER));
                assert(RightStencilSynchronized==!(flags&D3DCLEAR_STENCIL));
                assert(FrameRightDrawFailed&&poisons==1);
                assert(LastMainDepthClearStamp.Current(PresentEpoch));
            }else if(failure==0){
                assert(RightDepthSynchronized&&RightStencilSynchronized);
                assert(LastMainDepthClearStamp.Current(PresentEpoch));
            }
            assert(step==(failure==1?1:failure>=2&&failure<=4?failure+3:8));
        }
    ResetProbe(0);wanted=false;
    assert(ClearDest(&dev,0,nullptr,6,0,1.f,0)==D3D_OK&&step==1&&notes==0);
    ResetProbe(0);backbuffer=false;
    assert(ClearDest(&dev,0,nullptr,6,0,1.f,0)==D3D_OK&&step==1&&notes==0);
    ResetProbe(0);mrt=true;
    assert(ClearDest(&dev,0,nullptr,6,0,1.f,0)==D3D_OK&&step==1&&poisons==1);
    ResetProbe(0);resources=false;
    assert(ClearDest(&dev,0,nullptr,6,0,1.f,0)==D3D_OK&&step==1&&poisons==1);
    for(auto outcome:{R7CandidateSeedResult::Unavailable,R7CandidateSeedResult::Seeded,R7CandidateSeedResult::DirtyRestore}){
        ResetProbe(0);Settings::VRExternalFerrariTest=true;candidateResult=outcome;
        const bool dirty=outcome==R7CandidateSeedResult::DirtyRestore;
        assert(ClearDest(&dev,0,nullptr,7,0,1.f,0)==(dirty?E_FAIL:D3D_OK));
        assert(candidateCalls==1&&notes==unsigned(dirty));
        assert(RightDepthSynchronized==!dirty&&RightStencilSynchronized==!dirty);
        assert(LastMainDepthClearStamp.Current(PresentEpoch)==!dirty);
    }
    ResetProbe(0);Settings::VRF50ExternalModel=true;
    assert(ClearDest(&dev,0,nullptr,1,0,1.f,0)==D3D_OK&&candidateCalls==0);
    ResetProbe(5);Settings::VRF50ExternalModel=true;
    assert(ClearDest(&dev,0,nullptr,7,0,1.f,0)==D3D_OK&&candidateCalls==0);
    for(DWORD flags:{1u,2u,4u,7u})
        for(unsigned failure:{0u,1u}){
            ResetProbe(failure);InternalStereoPass=true;ExternalAtomicReplayEpoch=7;
            assert(ClearDest(&dev,0,nullptr,flags,0,1.f,0)==(failure?E_FAIL:D3D_OK));
            assert(step==1&&internalClearCalls==1&&internalClearFlags==flags);
        }
    ResetProbe(0);StereoBaseCallbacksArmed=false;ExternalAtomicReplayEpoch=7;
    assert(ClearDest(&dev,0,nullptr,7,0,1.f,0)==D3D_OK);
    assert(step==1&&internalClearCalls==0&&ExternalAtomicReplayEpoch==0);
    // Actual follow-up Clear path: each eye is replayed before its live Clear.
    // The stock clear count and HRESULT must survive unavailable candidates.
    unsigned cases=0;
    for(DWORD flags:{1u,2u,4u,6u,7u})
    for(auto l:{R7CandidateSeedResult::Seeded,R7CandidateSeedResult::Unavailable,R7CandidateSeedResult::DirtyRestore})
    for(auto r:{R7CandidateSeedResult::Seeded,R7CandidateSeedResult::Unavailable,R7CandidateSeedResult::DirtyRestore})
    for(unsigned failure=0;failure<=8;++failure){
        ResetProbe(failure);testingFollowup=true;ExternalAtomicReplayEpoch=PresentEpoch;
        followupResults[0]=l;followupResults[1]=r;
        const bool ld=l==R7CandidateSeedResult::DirtyRestore;
        const bool rightReached=!ld&&l==R7CandidateSeedResult::Seeded&&(failure==0||failure>=5);
        const bool rd=rightReached&&r==R7CandidateSeedResult::DirtyRestore;
        const bool outerDirty=!ld&&((!rd&&failure>=6)||(rd&&failure>=5&&failure<=7));
        const bool dirty=ld||rd||outerDirty;
        const auto hr=ClearDest(&dev,0,nullptr,flags,0,1.f,0);
        assert(hr==((dirty||failure==1)?E_FAIL:D3D_OK));
        assert(followupCalls[0]==1&&followupCalls[1]==unsigned(rightReached));
        assert(notes==unsigned(dirty));
        assert(ExternalAtomicReplayEpoch==((failure==0&&l==R7CandidateSeedResult::Seeded&&r==R7CandidateSeedResult::Seeded)?PresentEpoch:0));
        if(dirty)assert(!RightDepthSynchronized&&!RightStencilSynchronized&&!LastMainDepthClearStamp.Current(PresentEpoch));
        if(ld)assert(clearCalls==0);
        if(rd)assert(clearCalls==1);
        ++cases;
    }
    for(unsigned mask=1;mask<=16;mask*=2){
        ResetProbe(0);testingFollowup=true;ExternalAtomicReplayEpoch=PresentEpoch;
        wanted=!(mask&1);backbuffer=!(mask&2);mrt=mask&4;resources=!(mask&8);FrameStereoIncomplete=mask&16;
        assert(ClearDest(&dev,0,nullptr,2,0,1.f,0)==D3D_OK);
        assert(!ExternalAtomicReplayEpoch&&!followupCalls[0]&&!followupCalls[1]);++cases;
    }
    unsigned retireCases=0;
    for(unsigned phase=2;phase<=8;++phase)
    for(bool failing:{false,true}){
        ResetProbe(failing?phase:0);
        retireStep=phase;
        const auto hr=ClearDest(&dev,0,nullptr,7,0,1.f,0);
        assert(hr==E_FAIL&&step==phase&&notes==1);
        assert(!RightDepthSynchronized&&!RightStencilSynchronized&&!LastMainDepthClearStamp.Current(PresentEpoch));
        assert(!ExternalAtomicReplayEpoch&&coverageCalls==0);
        retireStep=0;
        ++retireCases;
    }
    std::cout<<"R7_CLEAR_GENERATION_PASS "<<retireCases<<"\n";
    std::cout<<"R7_FOLLOWUP_CLEAR_PASS "<<cases<<"\n";
    std::cout<<"R7_CLEAR_RESTORE_RECEIPT_PASS\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p / "probe.cpp").write_text(clear_prefix + body + clear_body + clear_suffix)
    subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror",
                    "-Wno-unused-variable","-I",str(root / "src/vr/d3d9"),
                    str(p/"probe.cpp"),"-o",str(p/"probe")],check=True)
    subprocess.run([str(p/"probe")],check=True)

# Iter52: verify upper dispatch handles dirty restoration, never declines to a
# raw/lower draw. Compile the actual R33 readiness function and exercise every
# readiness combination, including depthless draws after a dirty restoration.
r30 = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text()
r32 = (root / "src/vr/d3d9/stereo_renderer_r32.cpp").read_text()
r33 = (root / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text()
assert "return TryBootstrapRightDepthFromRecentClear(device, restoreFailed);" in r29
assert "return R29OwnerTryBootstrapRightDepth(device, restoreFailed);" in r30
assert "return R30SupportTryBootstrapRightDepth(d, restoreFailed);" in r32
assert r30.count("return state.bootstrapRestoreFailed") == 5
assert r30.count("? OutRunVR::StereoLowerDraw::Attempt<HRESULT>::Handled(E_FAIL)") >= 5
assert "if (state.bootstrapRestoreFailed)\n                    return false;" in r30
assert "if (bootstrapRestoreFailed)\n                    return R30ScreenDrawAttempt::Handled(E_FAIL);" in r30
assert r33.count("return bootstrapRestoreFailed ? R32ReviewOwnedResult{true, E_FAIL}") == 2
start = r33.index("bool R33PrepareRightDepthStereo(")
end = r33.index("\n        }", start) + len("\n        }")
body = r33[start:end]
prefix = r'''
#include <cassert>
#include <iostream>
struct IDirect3DDevice9{};
bool tracked,depthSync,stencilSync,depthTest,stencilTest,dirty,detach;
unsigned calls;
bool R32ReviewTrackedDepthStencil(){return tracked;}
bool R32ReviewRightDepthInSync(){return depthSync;}
bool R32ReviewRightStencilInSync(){return stencilSync;}
bool R32ReviewDepthTestActive(IDirect3DDevice9*){return depthTest;}
bool R32ReviewStencilTestActive(IDirect3DDevice9*){return stencilTest;}
bool R32ReviewTryBootstrapRightDepth(IDirect3DDevice9*,bool* failed){
    ++calls; *failed=dirty;
    if(detach)tracked=false;
    return false;
}
'''
suffix = r'''
int main(){
    IDirect3DDevice9 d;
    for(unsigned slot=0;slot<16;++slot)
    for(unsigned mask=0;mask<128;++mask){
        tracked=mask&1; depthSync=mask&2; stencilSync=mask&4;
        depthTest=mask&8; stencilTest=mask&16; dirty=mask&32; detach=mask&64;
        const bool attempt=tracked&&(!depthSync||!stencilSync);
        const bool expectedDirty=attempt&&dirty;
        const bool expectedReady=!expectedDirty&&
            (!tracked||(attempt&&detach)||((depthSync||!depthTest)&&(stencilSync||!stencilTest)));
        calls=0; bool failed=true;
        const bool ready=R33PrepareRightDepthStereo(&d,failed);
        assert(ready==expectedReady && failed==expectedDirty && calls==unsigned(attempt));
        // A declined route may fallback; a dirty result is owned failure.
        assert((!ready&&!failed)==(!expectedReady&&!expectedDirty));
    }
    std::cout<<"R33_DEPTH_BOOTSTRAP_BRIDGE_PASS\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p / "probe.cpp").write_text(prefix + body + suffix)
    subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror",
                    str(p/"probe.cpp"),"-o",str(p/"probe")],check=True)
    subprocess.run([str(p/"probe")],check=True)

# Iter71: compile the actual R23 baseline candidate entrypoint with the
# authoritative baseline flags and fault-injected R7 transaction.
r23 = (root / "src/vr/d3d9/stereo_renderer_r23.cpp").read_text()
r9 = (root / "src/vr/d3d9/stereo_renderer.cpp").read_text()
body = r23[r23.index("HRESULT R23SeedExternalCandidateFromBaseline("):
           r23.index("bool R23RecoveryNeedsBaseline()")]
owner = r23[r23.index("HRESULT __stdcall ClearDestR23("):
            r23.index("void R23BeforeTopLevelDraw(")]
assert owner.index("ExternalAtomicReplayEpoch=0;") < owner.index("const HRESULT hr = ClearHook.stdcall<HRESULT>")
assert owner.index("R23DepthBaselineSafe(") < owner.index("R23InitializeStereoFromAuthoritativeBaseline(")
assert owner.index("R23InitializeStereoFromAuthoritativeBaseline(") < owner.index("R23SeedExternalCandidateFromBaseline(")
assert "if(FAILED(R23SeedExternalCandidateFromBaseline(device,actual,stencilSafe,color)))\n                return E_FAIL;" in owner
copy = r9[r9.index("bool R9RestoreMonoBeforePresent("):r9.index("void R9MaybeLogSummary()")]
assert copy.index("ExternalAtomicReplayEpoch=0;") < copy.index("device->StretchRect(")
assert "ExternalAtomicReplayEpoch=0;\n\t\t\tif (++PresentEpoch == 0)" in r9
prefix = r'''
#include <cassert>
#include <cstdint>
#include <iostream>
using HRESULT=int;using DWORD=unsigned;using D3DCOLOR=unsigned;
constexpr HRESULT D3D_OK=0,E_FAIL=-1;
constexpr DWORD D3DCLEAR_TARGET=1,D3DCLEAR_ZBUFFER=2,D3DCLEAR_STENCIL=4;
struct IDirect3DDevice9{};
struct Surface{};
Surface depth;
Surface* TrackedDepthStencil=&depth;
namespace Settings {bool VRExternalFerrariTest,VRF50ExternalModel;}
namespace OutRunVR::State {struct D3D9RasterSnapshot{unsigned viewport=123;};}
bool FrameStereoIncomplete,FrameRightDrawFailed,mrt,mainTarget,hasStencil;
bool RightDepthSynchronized,RightStencilSynchronized,R9StereoSeeded,R9MonoSeeded,R9MonoBackupGap;
std::uint64_t ExternalAtomicReplayEpoch;
float R23DepthClearZ=.625f;
DWORD R23StencilClearValue=37;
struct Stamp{unsigned invalidated=0;void Invalidate(){++invalidated;}} LastMainDepthClearStamp;
unsigned notes,calls,expectedFlags;
enum class R7CandidateSeedResult {Unavailable,Seeded,DirtyRestore};
R7CandidateSeedResult outcome;
bool AnyAuxRenderTargetActive(){return mrt;}
bool TargetIsBackBuffer(){return mainTarget;}
bool SurfaceHasStencil(Surface*){return hasStencil;}
void NoteRestoreFailure(const char*){++notes;FrameRightDrawFailed=true;FrameStereoIncomplete=true;}
R7CandidateSeedResult R7BeginExternalAtomicResourceTransaction(IDirect3DDevice9* d,
    unsigned viewport,DWORD flags,D3DCOLOR color,float z,DWORD stencil){
    ++calls;assert(d&&viewport==123&&flags==expectedFlags&&color==0x12345678);
    assert(z==.625f&&stencil==(hasStencil?37u:0u));
    if(outcome==R7CandidateSeedResult::Seeded)ExternalAtomicReplayEpoch=71;
    return outcome;
}
'''
suffix = r'''
int main(){
    IDirect3DDevice9 dev;
    unsigned cases=0;
    for(unsigned mask=0;mask<512;++mask)
    for(auto result:{R7CandidateSeedResult::Unavailable,R7CandidateSeedResult::Seeded,
                     R7CandidateSeedResult::DirtyRestore}){
        Settings::VRExternalFerrariTest=mask&1;Settings::VRF50ExternalModel=mask&2;
        TrackedDepthStencil=(mask&4)?&depth:nullptr;
        FrameStereoIncomplete=mask&8;FrameRightDrawFailed=mask&16;
        mrt=mask&32;mainTarget=mask&64;hasStencil=mask&128;
        const bool stencilSafe=mask&256;
        const bool invoke=(mask&3)&&(mask&4)&&!(mask&56)&&mainTarget&&(!hasStencil||stencilSafe);
        expectedFlags=3|(hasStencil?4u:0u);outcome=result;
        RightDepthSynchronized=RightStencilSynchronized=R9StereoSeeded=R9MonoSeeded=true;
        R9MonoBackupGap=false;ExternalAtomicReplayEpoch=0;
        notes=calls=LastMainDepthClearStamp.invalidated=0;
        const auto hr=R23SeedExternalCandidateFromBaseline(&dev,{},stencilSafe,0x12345678);
        const bool dirty=invoke&&result==R7CandidateSeedResult::DirtyRestore;
        const bool seeded=invoke&&result==R7CandidateSeedResult::Seeded;
        assert(hr==(dirty?E_FAIL:D3D_OK)&&calls==unsigned(invoke)&&notes==unsigned(dirty));
        assert(ExternalAtomicReplayEpoch==(seeded?71u:0u));
        assert(RightDepthSynchronized==!dirty&&RightStencilSynchronized==!dirty);
        assert(R9StereoSeeded==!dirty&&R9MonoSeeded==!dirty&&R9MonoBackupGap==dirty);
        assert(LastMainDepthClearStamp.invalidated==unsigned(dirty));
        ++cases;
    }
    std::cout<<"R23_EXTERNAL_BASELINE_PASS "<<cases<<"\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p / "probe.cpp").write_text(prefix + body + suffix)
    subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror",
                    str(p/"probe.cpp"),"-o",str(p/"probe")],check=True)
    subprocess.run([str(p/"probe")],check=True)
