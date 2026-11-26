"""Compile the exact production R7 attachment preflight against a fake D3D9 device."""
from pathlib import Path
import subprocess
import tempfile

source = Path("src/vr/d3d9/stereo_renderer_r7.inc").read_text()
start = source.index("bool CaptureStereoInitState(")
end = source.index("bool EnsureStereoResources(", start)
capture = source[start:end]
init = source[end:source.index("void NoteRestoreFailure(", end)]
# Failed preflight must precede retirement, allocation and any state mutation.
guard = init.index("if (!CaptureStereoInitState(")
assert guard < init.index("ReleaseStereoResources();") < init.index("device->CreateRenderTarget(")
assert init.index("currentDepth,desc,savedViewport)) return false;") < init.index("ReleaseStereoResources();")
assert "TrackedRenderTarget=currentRt;" in init
assert "TrackedDepthStencil=currentDepth;" in init
assert "GetViewport(" not in init
assert "ReplaceSurfaceRef(TrackedRenderTarget,BackBuffer)" not in init

stub = r'''
#include <cassert>
using HRESULT = int;
constexpr HRESULT D3DERR_NOTFOUND=-2, E_FAIL=-1, S_OK=0;
constexpr int D3DBACKBUFFER_TYPE_MONO=0;
bool FAILED(HRESULT h) { return h<0; }
struct D3DSURFACE_DESC { int width=0; };
struct D3DVIEWPORT9 { int width=0; };
struct IDirect3DSurface9 {
    int refs=0; HRESULT descHr=S_OK;
    HRESULT GetDesc(D3DSURFACE_DESC* d) { d->width=1920; return descHr; }
    void Release() { assert(refs>0); --refs; }
};
template<class T> void ReleaseCom(T*& p) { if(p) {p->Release();p=nullptr;} }
struct IDirect3DDevice9 {
    IDirect3DSurface9 back,rt,depth;
    HRESULT backHr=S_OK,rtHr=S_OK,depthHr=S_OK,viewHr=S_OK;
    bool noBack=false,noRt=false,noDepth=false;
    int viewCalls=0;
    static HRESULT get(IDirect3DSurface9** out,IDirect3DSurface9& s,HRESULT hr,bool empty) {
        *out=empty?nullptr:&s; if(*out) ++s.refs; return hr;
    }
    HRESULT GetBackBuffer(int,int,int,IDirect3DSurface9** out) {return get(out,back,backHr,noBack);}
    HRESULT GetRenderTarget(int,IDirect3DSurface9** out) {return get(out,rt,rtHr,noRt);}
    HRESULT GetDepthStencilSurface(IDirect3DSurface9** out) {return get(out,depth,depthHr,noDepth);}
    HRESULT GetViewport(D3DVIEWPORT9* v) {++viewCalls;v->width=800;return viewHr;}
};
'''
cases = r'''
void run(IDirect3DDevice9& d,bool expected,bool depthExpected=false) {
    IDirect3DSurface9 *b=nullptr,*r=nullptr,*z=nullptr;
    D3DSURFACE_DESC desc{}; D3DVIEWPORT9 view{};
    assert(CaptureStereoInitState(&d,b,r,z,desc,view)==expected);
    if(expected) {
        assert(b==&d.back && r==&d.rt && b!=r);
        assert((z==&d.depth)==depthExpected);
        assert(desc.width==1920 && view.width==800 && d.viewCalls==1);
        ReleaseCom(z); ReleaseCom(r); ReleaseCom(b);
    } else { assert(!b && !r && !z); }
    assert(d.back.refs==0 && d.rt.refs==0 && d.depth.refs==0);
}
int main() {
    {IDirect3DDevice9 d;run(d,true,true);}
    {IDirect3DDevice9 d;d.depthHr=D3DERR_NOTFOUND;d.noDepth=true;run(d,true);}
    {IDirect3DDevice9 d;d.backHr=E_FAIL;run(d,false);}
    {IDirect3DDevice9 d;d.noBack=true;run(d,false);}
    {IDirect3DDevice9 d;d.back.descHr=E_FAIL;run(d,false);}
    {IDirect3DDevice9 d;d.rtHr=E_FAIL;run(d,false);assert(d.viewCalls==0);}
    {IDirect3DDevice9 d;d.noRt=true;run(d,false);}
    {IDirect3DDevice9 d;d.depthHr=E_FAIL;run(d,false);}
    {IDirect3DDevice9 d;d.noDepth=true;run(d,false);}
    {IDirect3DDevice9 d;d.depthHr=D3DERR_NOTFOUND;run(d,false);}
    {IDirect3DDevice9 d;d.viewHr=E_FAIL;run(d,false);}
    // Retry after a transient getter failure is still permitted.
    {IDirect3DDevice9 d;d.rtHr=E_FAIL;run(d,false);d.rtHr=S_OK;run(d,true,true);}
}
'''
with tempfile.TemporaryDirectory() as temp:
    cpp = Path(temp) / "capture.cpp"
    exe = Path(temp) / "capture"
    cpp.write_text(stub + capture + cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print("R7 stereo initialization preflight: positive/negative/retry PASS")

# A1: compile the real inactive-pair allocator, not a policy surrogate.
owner_begin=source.index("struct R7AtomicCandidatePair")
owner_end=source.index("R7AtomicCandidatePair ExternalAtomicCandidates",owner_begin)
owner=source[owner_begin:owner_end]
assert "ExternalAtomicCandidates.Reset();" in source[source.index("void ReleaseStereoResources()"):source.index("bool CreateRightDepthForTracked(")]
clear=source[source.index("HRESULT __stdcall ClearDest("):source.index("HRESULT __stdcall SetRenderTargetDest(")]
assert clear.index("if(!restoreOk||candidateDirty)") < clear.index("R7BeginExternalAtomicResourceTransaction(device,savedViewport,flags,color,z,stencil)")
assert clear.index("R7ReplayInactiveEye(device,0") < clear.index("const HRESULT leftHr=clearCall();")
assert clear.index("R7ReplayInactiveEye(device,1") < clear.index("if(SUCCEEDED(rightHr)&&!candidateDirty)rightHr=clearCall();")
assert clear.index("if(SUCCEEDED(rightHr)&&!candidateDirty)rightHr=clearCall();") < clear.index("restoreOk=RestoreRightPassState(")
assert "if(ExternalAtomicReplayEpoch!=PresentEpoch&&!FrameStereoIncomplete&&!FrameRightDrawFailed&&" in clear
assert "Settings::VRExternalFerrariTest||Settings::VRF50ExternalModel" in clear
assert "SetRenderTarget" not in owner and "SetDepthStencilSurface" not in owner and "StretchRect" not in owner
atomic_stub=r'''
#include <cassert>
#include <cstdint>
#include <initializer_list>
using HRESULT=int;
using UINT=unsigned;
constexpr int FALSE=0, E_FAIL=-1, S_OK=0, D3DERR_NOTFOUND=-2;
bool FAILED(HRESULT h){return h<0;}
bool SUCCEEDED(HRESULT h){return h>=0;}
struct D3DCAPS9 {UINT NumSimultaneousRTs=1;};
struct D3DSURFACE_DESC {UINT Width=0,Height=0,Format=0,MultiSampleType=0,MultiSampleQuality=0;};
struct D3DVIEWPORT9 {UINT X=0,Y=0,Width=0,Height=0;};
struct RECT {int left=0,top=0,right=1920,bottom=1080;};
struct IDirect3DSurface9 {
    D3DSURFACE_DESC desc{};
    int refs=0;
    HRESULT GetDesc(D3DSURFACE_DESC* d){*d=desc;return S_OK;}
    void Release(){assert(refs>0);--refs;}
};
template<class T> void ReleaseCom(T*& p){if(p){p->Release();p=nullptr;}}
struct IDirect3DDevice9 {
    IDirect3DSurface9 made[32]{};
    unsigned calls=0,failAt=0,nullAt=0,mismatchAt=0;
    unsigned io=0,ioFail=0,clearCalls=0,liveWrites=0;
    UINT capsTargets=1,capsCalls=0,auxCalls=0;
    HRESULT capsHr=S_OK,auxHr[4]{S_OK,D3DERR_NOTFOUND,D3DERR_NOTFOUND,D3DERR_NOTFOUND};
    IDirect3DSurface9* aux[4]{};
    HRESULT GetDeviceCaps(D3DCAPS9* c){++capsCalls;c->NumSimultaneousRTs=capsTargets;return capsHr;}
    IDirect3DSurface9 *rt=nullptr,*depth=nullptr,*liveRt=nullptr,*liveDepth=nullptr;
    D3DVIEWPORT9 viewport{0,0,1920,1080};
    RECT scissor{4,5,1800,1000};
    HRESULT op(){return ++io==ioFail?E_FAIL:S_OK;}
    HRESULT GetRenderTarget(unsigned slot,IDirect3DSurface9** s){
        if(slot){assert(slot<capsTargets);++auxCalls;*s=aux[slot];if(*s)++(*s)->refs;return auxHr[slot];}
        *s=rt;if(rt)++rt->refs;return op();
    }
    HRESULT GetDepthStencilSurface(IDirect3DSurface9** s){*s=depth;if(depth)++depth->refs;return op();}
    HRESULT GetViewport(D3DVIEWPORT9* v){*v=viewport;return op();}
    HRESULT GetScissorRect(RECT* r){*r=scissor;return op();}
    HRESULT SetViewport(const D3DVIEWPORT9* v){auto h=op();if(!FAILED(h))viewport=*v;return h;}
    HRESULT SetScissorRect(const RECT* r){auto h=op();if(!FAILED(h))scissor=*r;return h;}
    HRESULT bindColor(IDirect3DSurface9* s){auto h=op();if(!FAILED(h)){rt=s;viewport={};scissor={};}return h;}
    HRESULT bindDepth(IDirect3DSurface9* s){auto h=op();if(!FAILED(h))depth=s;return h;}
    HRESULT clear(){++clearCalls;if(rt==liveRt||depth==liveDepth||!rt||!depth)++liveWrites;return op();}
    HRESULT create(UINT w,UINT h,UINT f,UINT m,UINT q,IDirect3DSurface9** out){
        auto& s=made[calls++];assert(!s.refs);
        if(calls==nullAt){*out=nullptr;return S_OK;}
        s.desc={w,h,f,m,q};if(calls==mismatchAt)++s.desc.Width;
        s.refs=1;*out=&s;return calls==failAt?E_FAIL:S_OK;
    }
    HRESULT CreateRenderTarget(UINT w,UINT h,UINT f,UINT m,UINT q,int,IDirect3DSurface9** out,void*){return create(w,h,f,m,q,out);}
    HRESULT CreateDepthStencilSurface(UINT w,UINT h,UINT f,UINT m,UINT q,int,IDirect3DSurface9** out,void*){return create(w,h,f,m,q,out);}
    void empty(){for(auto& s:made)assert(s.refs==0);}
};
'''
seed=source[source.index("enum class R7CandidateSeedResult"):source.index("// A successful seed is ONLY")]
atomic_cases=r'''
int main(){
    IDirect3DSurface9 lc{{1920,1080,1,4,0}},rc=lc;
    IDirect3DSurface9 ld{{1920,1080,2,4,0}},rd=ld;
    D3DVIEWPORT9 vp{0,0,1920,1080};
    IDirect3DDevice9 d;
    R7AtomicCandidatePair pair;
    auto ensure=[&](){return pair.Ensure(&d,&lc,&ld,&rc,&rd,vp);};
    assert(ensure()&&d.calls==4);
    assert(pair.eyes[0].color!=pair.eyes[1].color&&pair.eyes[0].depth!=pair.eyes[1].depth);
    assert(pair.eyes[0].color!=&lc&&pair.eyes[1].depth!=&rd);
    const auto gen=pair.generation;
    assert(ensure()&&d.calls==4&&pair.generation==gen&&d.capsCalls==1);
    pair.Reset();d.empty();assert(pair.generation!=gen&&!pair.device);
    assert(ensure()&&d.calls==8);pair.Reset();d.empty();
    for(unsigned k=1;k<=4;++k){
        IDirect3DDevice9 fail;fail.failAt=k;
        assert(!pair.Ensure(&fail,&lc,&ld,&rc,&rd,vp));fail.empty();
        assert(!pair.device&&!pair.eyes[0].color&&!pair.eyes[1].depth);
        IDirect3DDevice9 null;null.nullAt=k;
        assert(!pair.Ensure(&null,&lc,&ld,&rc,&rd,vp));null.empty();
        IDirect3DDevice9 mismatch;mismatch.mismatchAt=k;
        assert(!pair.Ensure(&mismatch,&lc,&ld,&rc,&rd,vp));mismatch.empty();
    }
    rd.desc.MultiSampleQuality=1;assert(!ensure()&&d.calls==8);
    rd=ld;vp.X=1;assert(!ensure()&&d.calls==8);vp.X=0;
    assert(!pair.Ensure(&d,&lc,&ld,&lc,&rd,vp)&&d.calls==8);
    assert(ensure());IDirect3DDevice9 other;
    assert(pair.Ensure(&other,&lc,&ld,&rc,&rd,vp));d.empty();
    pair.Reset();other.empty();
    assert(lc.refs==0&&ld.refs==0&&rc.refs==0&&rd.refs==0);
    assert(ensure());
    // 4 getters, 6 operations per eye, 5 independent restores.
    for(unsigned fail=0;fail<=21;++fail){
        d.io=d.clearCalls=d.liveWrites=0;d.ioFail=fail;
        d.rt=d.liveRt=&lc;d.depth=d.liveDepth=&ld;d.viewport=vp;
        d.scissor={4,5,1800,1000};
        const auto result=R7SeedInactivePair(pair,&d,&lc,&ld,
            [&](IDirect3DSurface9* s){return d.bindColor(s);},
            [&](IDirect3DSurface9* s){return d.bindDepth(s);},
            [&](){return d.clear();});
        assert(d.liveWrites==0&&lc.refs==0&&ld.refs==0);
        if(fail==0){assert(result==R7CandidateSeedResult::Seeded&&d.clearCalls==2);}
        else if(fail>=17){assert(result==R7CandidateSeedResult::DirtyRestore&&d.io==21);}
        else{assert(result==R7CandidateSeedResult::Unavailable);}
        if(fail<=16){
            assert(d.rt==&lc&&d.depth==&ld&&d.viewport.Width==1920&&d.scissor.left==4);
        }
        if(fail>=1&&fail<=4)assert(d.clearCalls==0);
        if(fail>=5&&fail<=16)assert(d.io==fail+5);
    }
    // Single-eye operation must not touch the other candidate.
    d.io=d.clearCalls=d.liveWrites=0;d.ioFail=0;
    d.rt=d.liveRt=&lc;d.depth=d.liveDepth=&ld;d.viewport=vp;
    auto color=[&](IDirect3DSurface9* s){return d.bindColor(s);};
    auto depth=[&](IDirect3DSurface9* s){return d.bindDepth(s);};
    for(unsigned eye=0;eye<2;++eye){
        unsigned draws=0;
        const auto result=R7SeedInactivePair(pair,&d,&lc,&ld,color,depth,
            [&](){++draws;assert(d.rt==pair.eyes[eye].color&&d.depth==pair.eyes[eye].depth);return d.clear();},eye,1);
        assert(result==R7CandidateSeedResult::Seeded&&draws==1);
        assert(d.rt==&lc&&d.depth==&ld&&d.liveWrites==0);
    }
    // A partial viewport is valid for a replay, not for a full seed.
    d.viewport={20,30,640,480};d.scissor={21,31,600,400};
    unsigned partialDraws=0;
    auto partial=[&](){++partialDraws;assert(d.viewport.X==20&&d.viewport.Y==30&&d.viewport.Width==640&&d.scissor.left==21);return d.clear();};
    assert(R7SeedInactivePair(pair,&d,&lc,&ld,color,depth,partial)==R7CandidateSeedResult::Unavailable);
    assert(partialDraws==0);
    assert(R7SeedInactivePair(pair,&d,&lc,&ld,color,depth,partial,0,1,false)==R7CandidateSeedResult::Seeded);
    assert(partialDraws==1&&d.rt==&lc&&d.depth==&ld&&d.viewport.X==20&&d.scissor.left==21&&d.liveWrites==0);
    d.viewport={1900,0,640,480};
    assert(R7SeedInactivePair(pair,&d,&lc,&ld,color,depth,partial,1,1,false)==R7CandidateSeedResult::Unavailable);
    assert(partialDraws==1&&d.rt==&lc&&d.depth==&ld);
    d.viewport=vp;
    const unsigned before=d.io;
    assert(R7SeedInactivePair(pair,&d,&lc,&ld,color,depth,[&](){return d.clear();},2,1)==R7CandidateSeedResult::Unavailable);
    assert(d.io==before);
    pair.Reset();d.empty();
    // Caps failures must precede all allocations; valid limits are cached.
    for(unsigned limit: {0u,5u,4u}){
        IDirect3DDevice9 bad;
        bad.capsTargets=limit;bad.capsHr=limit==4?E_FAIL:S_OK;
        assert(!pair.Ensure(&bad,&lc,&ld,&rc,&rd,vp));
        assert(bad.calls==0&&bad.capsCalls==1&&!pair.device&&pair.simultaneousTargets==0);
    }
    IDirect3DSurface9 auxSurface{};
    unsigned mrtCases=0;
    for(unsigned limit=1;limit<=4;++limit){
        IDirect3DDevice9 multi;multi.capsTargets=limit;
        assert(pair.Ensure(&multi,&lc,&ld,&rc,&rd,vp));
        assert(pair.simultaneousTargets==limit&&multi.capsCalls==1);
        // 3 states (unbound, S_OK null, failure) plus bound with each HRESULT.
        for(unsigned mask=0;mask<216;++mask){
            unsigned state=mask;bool safe=true;unsigned expectedQueries=0;
            for(unsigned slot=1;slot<limit;++slot){
                const unsigned k=state%6;state/=6;
                multi.aux[slot]=k>=3?&auxSurface:nullptr;
                multi.auxHr[slot]=(k%3==0)?D3DERR_NOTFOUND:(k%3==1?S_OK:E_FAIL);
                if(safe){++expectedQueries;safe=k<2;}
            }
            multi.io=multi.clearCalls=multi.liveWrites=multi.auxCalls=0;
            multi.rt=multi.liveRt=&lc;multi.depth=multi.liveDepth=&ld;
            multi.viewport=vp;multi.scissor={4,5,1800,1000};
            const auto result=R7SeedInactivePair(pair,&multi,&lc,&ld,
                [&](IDirect3DSurface9* a){return multi.bindColor(a);},
                [&](IDirect3DSurface9* a){return multi.bindDepth(a);},
                [&](){return multi.clear();});
            assert(multi.auxCalls==expectedQueries&&auxSurface.refs==0);
            assert(lc.refs==0&&ld.refs==0&&multi.rt==&lc&&multi.depth==&ld);
            assert(multi.liveWrites==0&&multi.clearCalls==(safe?2u:0u));
            assert(result==(safe?R7CandidateSeedResult::Seeded:R7CandidateSeedResult::Unavailable));
            if(!safe)assert(multi.io==4); // capture only, no setter or raster
            ++mrtCases;
        }
        pair.Reset();multi.empty();assert(pair.simultaneousTargets==0);
    }
    assert(mrtCases==864);
}
'''
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"atomic_candidate.cpp"
    exe=Path(temp)/"atomic_candidate"
    cpp.write_text(atomic_stub+owner+seed+atomic_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print("R7 A1 inactive pair allocation/reuse/reset/fault injection PASS")

# Actual R7 draw path must mirror both eyes before their live DIP, and raw
# R29 routes must not implicitly claim coverage.
draw=source[source.index("HRESULT ExecuteStereoDraw("):source.index("HRESULT __stdcall DrawPrimitiveDest(")]
assert draw.index("R7ReplayInactiveDraw(device,0") < draw.index("const HRESULT leftHr=drawCall();")
assert draw.index("R7ReplayInactiveDraw(device,1") < draw.index("rightHr=drawCall();")
assert "if(FAILED(rightHr)||!restoreOk)ExternalAtomicReplayEpoch=0;" in draw
assert "ExecuteStereoDraw(device,call,true)" in source[source.index("HRESULT __stdcall DrawPrimitiveDest("):source.index("HRESULT __stdcall DrawIndexedPrimitiveDest(")]
assert "ExecuteStereoDraw(device,call,true)" in source[source.index("HRESULT __stdcall DrawIndexedPrimitiveDest("):source.index("HRESULT __stdcall DrawPrimitiveUPDest(")]
up=source[source.index("HRESULT __stdcall DrawPrimitiveUPDest("):source.index("HRESULT __stdcall DrawIndexedPrimitiveUPDest(")]
iup=source[source.index("HRESULT __stdcall DrawIndexedPrimitiveUPDest("):source.index("HRESULT __stdcall ClearDest(")]
assert "ExecuteStereoDraw(device,call,true,true);" in up
assert "ExecuteStereoDraw(device,call,true,true,true);" in iup
assert "R7ExecuteRawCandidateVb(device,call,true);" in up
assert "R7ExecuteRawCandidateVb(device,call,true,true);" in iup
assert "InternalStereoPass&&!OutRunVR::DinoSidecar::ActiveExternalStereoMesh" in up and "InternalStereoPass&&!OutRunVR::DinoSidecar::ActiveExternalStereoMesh" in iup
assert "[&](){return drawCall();},eye,1,false);" in source
assert "if(changed)ExternalAtomicReplayEpoch=0;" in source
assert "ExternalAtomicReplayEpoch=0;" in clear

# Iter72: execute the actual raw explicit-surface write owner with fault
# injection; unknown source/depth/private writes cannot retain a receipt.
copy_owner=source[source.index("template<class Write>\n        HRESULT R7ExecuteAtomicSurfaceWrite("):source.index("HRESULT __stdcall StretchRectDest(")]
copy_stub=r'''
#include <cassert>
#include <atomic>
#include <cstdint>
#include <iostream>
using HRESULT=int;
constexpr HRESULT S_OK=0,E_FAIL=-1;
bool FAILED(HRESULT h){return h<0;}
struct IDirect3DDevice9{};struct IDirect3DSurface9{};
IDirect3DDevice9 game,other;
IDirect3DSurface9 left,right,ld,rd,cl,cr,czl,czr,unknown;
auto* BackBuffer=&left;auto* RightEyeSurface=&right;
auto* TrackedDepthStencil=&ld;auto* RightEyeDepth=&rd;
struct Pair{struct Eye{IDirect3DSurface9* color;IDirect3DSurface9* depth;};
    Eye eyes[2]{{&cl,&czl},{&cr,&czr}};IDirect3DDevice9* device=&game;
} ExternalAtomicCandidates;
struct Stamp{unsigned count=0;void Invalidate(){++count;}} LastMainDepthClearStamp;
std::atomic<bool> StereoBaseCallbacksArmed{true};
std::uint64_t ExternalAtomicReplayEpoch=9,PresentEpoch=9;
bool FrameStereoIncomplete=false,FrameRightDrawFailed=false;
bool IsGameDevice(IDirect3DDevice9* d){return d==&game;}
'''
copy_cases=r'''
int main(){
    IDirect3DSurface9* surfaces[]{nullptr,&left,&right,&ld,&rd,&cl,&cr,&czl,&czr,&unknown};
    unsigned cases=0;
    for(unsigned mode=0;mode<2;++mode)
    for(unsigned si=0;si<10;++si)
    for(unsigned di=0;di<10;++di)
    for(unsigned mask=0;mask<128;++mask){
        auto* device=(mask&1)?&other:&game;
        StereoBaseCallbacksArmed=!(mask&2);
        ExternalAtomicReplayEpoch=(mask&4)?0:9;
        FrameStereoIncomplete=mask&8;FrameRightDrawFailed=mask&16;
        ExternalAtomicCandidates.device=&game;
        LastMainDepthClearStamp.count=0;
        auto* s=mode?nullptr:surfaces[si];auto* d=surfaces[di];
        const bool enabled=!(mask&3),active=enabled&&!(mask&4);
        const bool eye=di==1||di==2,known=mode||si==1||si==2;
        const bool protectedWrite=di>=3&&di<=8;
        const bool liveFail=mask&32,replayFail=mask&64;
        const bool mirror=active&&eye&&known&&!(mask&24)&&!liveFail;
        unsigned calls=0;
        auto write=[&](IDirect3DSurface9* a,IDirect3DSurface9* b){
            ++calls;
            if(calls==1){assert(a==s&&b==d);return liveFail?E_FAIL:S_OK;}
            assert(mirror&&calls==2&&b==(di==1?&cl:&cr));
            assert(a==(mode?nullptr:(si==1?&cl:&cr)));
            return replayFail?E_FAIL:S_OK;
        };
        const auto hr=R7ExecuteAtomicSurfaceWrite(device,s,d,mode!=0,write);
        assert(hr==(liveFail?E_FAIL:S_OK)&&calls==1u+unsigned(mirror));
        const bool invalid=active&&(protectedWrite||(eye&&(!mirror||replayFail)));
        assert(ExternalAtomicReplayEpoch==((mask&4)||invalid?0u:9u));
        assert(LastMainDepthClearStamp.count==unsigned(enabled&&di==3));
        ++cases;
    }
    // Wrong allocation generation/device must not receive a second write.
    StereoBaseCallbacksArmed=true;FrameStereoIncomplete=FrameRightDrawFailed=false;
    ExternalAtomicReplayEpoch=9;ExternalAtomicCandidates.device=&other;
    unsigned calls=0;
    assert(R7ExecuteAtomicSurfaceWrite(&game,nullptr,&left,true,
        [&](auto*,auto*){++calls;return S_OK;})==S_OK);
    assert(calls==1&&ExternalAtomicReplayEpoch==0);
    std::cout<<"R7_EXPLICIT_SURFACE_WRITE_PASS "<<cases+1<<"\n";
}
'''
for hook,index in (("UpdateSurface",30),("StretchRect",34),("ColorFill",35)):
    assert f"{hook}VtableIndex = {index};" in source
    assert f"{hook}Hook=safetyhook::create_inline(vtable[{hook}VtableIndex],{hook}Dest,disabled);" in source
    assert f"!{hook}Hook" in source and f"&{hook}Hook" in source and f"{hook}Hook = {{}};" in source
assert "R7ExecuteAtomicSurfaceWrite(device,source,destination,false," in source
assert "R7ExecuteAtomicSurfaceWrite(device,nullptr,destination,true," in source
assert "FrameStereoMetadata={};ExternalAtomicReplayEpoch=0;if(++PresentEpoch" in source
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"explicit_surface.cpp"
    exe=Path(temp)/"explicit_surface"
    cpp.write_text(copy_stub+copy_owner+copy_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# UpdateSurface is a real base vtable owner. Compile its exact implementation,
# not a duplicate policy, and inspect receipts inside the original trampoline.
upload_start=source.index("HRESULT __stdcall UpdateSurfaceDest(")
upload_owner=source[upload_start:source.index("void ReleaseStereoResources()",upload_start)]
assert "return UpdateSurfaceHook.stdcall<HRESULT>" in upload_owner
upload_stub=r'''
#define __stdcall
struct RECT{int token;};struct POINT{int token;};
const RECT rect{123};const POINT point{456};
IDirect3DDevice9* expectedDevice=nullptr;
IDirect3DSurface9 *expectedSource=nullptr,*expectedDestination=nullptr;
const RECT* expectedRect=nullptr;const POINT* expectedPoint=nullptr;
std::uint64_t expectedEpoch=0;
unsigned expectedStamp=0,calls=0;
HRESULT injected=S_OK;
struct UploadHook{
    template<class R> R stdcall(IDirect3DDevice9* device,IDirect3DSurface9* source,
        const RECT* sr,IDirect3DSurface9* destination,const POINT* dp){
        ++calls;
        assert(device==expectedDevice&&source==expectedSource&&
            sr==expectedRect&&destination==expectedDestination&&dp==expectedPoint);
        assert(ExternalAtomicReplayEpoch==expectedEpoch);
        assert(LastMainDepthClearStamp.count==expectedStamp);
        return injected;
    }
} UpdateSurfaceHook;
'''
upload_cases=r'''
int main(){
    IDirect3DSurface9* surfaces[]{nullptr,&left,&right,&ld,&rd,&cl,&cr,&czl,&czr,&unknown};
    unsigned cases=0;
    for(unsigned si=0;si<10;++si)
    for(unsigned di=0;di<10;++di)
    for(unsigned mask=0;mask<128;++mask){
        StereoBaseCallbacksArmed=!(mask&1);
        expectedDevice=(mask&2)?&other:&game;
        ExternalAtomicReplayEpoch=(mask&4)?0:((mask&8)?8:9);
        expectedSource=surfaces[si];expectedDestination=surfaces[di];
        expectedRect=(mask&16)?nullptr:&rect;
        expectedPoint=(mask&32)?nullptr:&point;
        injected=(mask&64)?E_FAIL:S_OK;
        LastMainDepthClearStamp.count=0;calls=0;
        const bool owned=!(mask&3);
        expectedEpoch=owned&&di>=1&&di<=8?0:ExternalAtomicReplayEpoch;
        expectedStamp=unsigned(owned&&di==3);
        assert(UpdateSurfaceDest(expectedDevice,expectedSource,expectedRect,
            expectedDestination,expectedPoint)==injected);
        assert(calls==1&&ExternalAtomicReplayEpoch==expectedEpoch&&
            LastMainDepthClearStamp.count==expectedStamp);
        ++cases;
    }
    // Null unallocated candidate pointers must not classify null as protected.
    ExternalAtomicCandidates.eyes[0]={nullptr,nullptr};
    ExternalAtomicCandidates.eyes[1]={nullptr,nullptr};
    StereoBaseCallbacksArmed=true;ExternalAtomicReplayEpoch=9;
    expectedDevice=&game;expectedSource=&unknown;expectedDestination=nullptr;
    expectedRect=nullptr;expectedPoint=nullptr;
    expectedEpoch=9;expectedStamp=0;LastMainDepthClearStamp.count=0;calls=0;
    assert(UpdateSurfaceDest(&game,&unknown,nullptr,nullptr,nullptr)==injected);
    assert(calls==1&&ExternalAtomicReplayEpoch==9);
    std::cout<<"R7_UPDATE_SURFACE_OWNER_PASS "<<cases+1<<"\n";
}
'''
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"update_surface.cpp"
    exe=Path(temp)/"update_surface"
    cpp.write_text(copy_stub+upload_stub+upload_owner+upload_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter77: actual creation provenance and seed/replay entrypoints. No
# synthetic discard policy substituted for the production callbacks.
retention=source[source.index("constexpr GUID R7DepthRetentionGuid"):
                 source.index("// EXT16-011 A1: an inactive")]
entry=source[source.index("R7CandidateSeedResult R7BeginExternalAtomicResourceTransaction("):
             source.index("// Copy/fill methods write explicit surfaces")]
retention_stub=r'''
#define __stdcall
#include <cassert>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <iostream>
using HRESULT=int;using DWORD=unsigned;using UINT=unsigned;using BOOL=int;
using D3DFORMAT=int;using D3DMULTISAMPLE_TYPE=int;using D3DCOLOR=unsigned;
using HANDLE=void*;
constexpr HRESULT S_OK=0,E_FAIL=-1;
constexpr DWORD D3DPRESENTFLAG_DISCARD_DEPTHSTENCIL=2,D3DCLEAR_STENCIL=4;
bool SUCCEEDED(HRESULT h){return h>=0;}
struct GUID{unsigned a;unsigned short b,c;unsigned char d[8];};
struct D3DPRESENT_PARAMETERS{BOOL EnableAutoDepthStencil=1;DWORD Flags=0;};
struct D3DVIEWPORT9{};struct D3DRECT{};
struct IDirect3DSurface9{
    bool marked=false,writeFail=false,readFail=false;DWORD size=8;
    std::uint64_t proof=0;unsigned refs=0,writes=0;
    HRESULT SetPrivateData(const GUID&,const void* p,DWORD n,DWORD flags){
        ++writes;assert(n==8&&!flags);if(writeFail)return E_FAIL;
        std::memcpy(&proof,p,n);marked=true;return S_OK;
    }
    HRESULT GetPrivateData(const GUID&,void* p,DWORD* n){
        if(!marked||readFail)return E_FAIL;
        std::memcpy(p,&proof,8);*n=size;return S_OK;
    }
    void Release(){assert(refs);--refs;}
};
struct IDirect3DSwapChain9{
    D3DPRESENT_PARAMETERS pp{};bool fail=false;unsigned refs=0;
    HRESULT GetPresentParameters(D3DPRESENT_PARAMETERS* out){*out=pp;return fail?E_FAIL:S_OK;}
    void Release(){assert(refs);--refs;}
};
template<class T>void ReleaseCom(T*& p){if(p){p->Release();p=nullptr;}}
struct IDirect3DDevice9{
    bool game=true,chainFail=false,depthFail=false,nullChain=false,nullDepth=false;
    UINT chains=1;IDirect3DSwapChain9 chain;IDirect3DSurface9 depth;
    UINT GetNumberOfSwapChains(){return chains;}
    HRESULT GetSwapChain(UINT i,IDirect3DSwapChain9** out){assert(!i);*out=nullChain?nullptr:&chain;if(*out)++chain.refs;return chainFail?E_FAIL:S_OK;}
    HRESULT GetDepthStencilSurface(IDirect3DSurface9** out){*out=nullDepth?nullptr:&depth;if(*out)++depth.refs;return depthFail?E_FAIL:S_OK;}
};
std::atomic<bool> StereoBaseCallbacksArmed{true};
bool IsGameDevice(IDirect3DDevice9* d){return d&&d->game;}
IDirect3DSurface9* created=nullptr;HRESULT createHr=S_OK;unsigned creates=0;
struct CreateHook{
    template<class R>R stdcall(IDirect3DDevice9*,UINT w,UINT h,D3DFORMAT f,
        D3DMULTISAMPLE_TYPE m,DWORD q,BOOL,IDirect3DSurface9** out,HANDLE*){
        assert(w==1920&&h==1080&&f==3&&m==4&&q==1);++creates;
        if(out)*out=created;
        return createHr;
    }
} CreateDepthRetentionHook;
struct IDirect3DDevice9Ex:IDirect3DDevice9{};
HRESULT __stdcall CreateDepthRetentionDest(IDirect3DDevice9*,UINT,UINT,D3DFORMAT,
    D3DMULTISAMPLE_TYPE,DWORD,BOOL,IDirect3DSurface9**,HANDLE*);
bool delegateBase=false;unsigned exCreates=0;HRESULT exHr=S_OK;
HANDLE* expectedShared=nullptr;DWORD expectedUsage=0;
struct ExHook{
    template<class R>R stdcall(IDirect3DDevice9Ex* d,UINT w,UINT h,D3DFORMAT f,
        D3DMULTISAMPLE_TYPE m,DWORD q,BOOL,IDirect3DSurface9** out,HANDLE* shared,DWORD usage){
        assert(w==1920&&h==1080&&f==3&&m==4&&q==1);
        assert(shared==expectedShared&&usage==expectedUsage);++exCreates;
        if(delegateBase)CreateDepthRetentionDest(d,w,h,f,m,q,0,out,shared);
        else if(out)*out=created;
        return exHr;
    }
} CreateDepthRetentionExHook;
'''
entry_stub=r'''
enum class R7CandidateSeedResult{Unavailable,Seeded,DirtyRestore};
IDirect3DSurface9 left,right,color,rc;
IDirect3DSurface9 *TrackedDepthStencil=&left,*RightEyeDepth=&right,
    *TrackedRenderTarget=&color,*RightEyeSurface=&rc;
struct Pair{
    struct Desc{D3DFORMAT Format=3;}depthDesc;
    IDirect3DSurface9* provenLiveDepth[2]{};
    unsigned allocations=0,resets=0;bool allow=true;
    bool Ensure(IDirect3DDevice9*,IDirect3DSurface9*,IDirect3DSurface9*,
        IDirect3DSurface9*,IDirect3DSurface9*,const D3DVIEWPORT9&){++allocations;return allow;}
    void Reset(){++resets;provenLiveDepth[0]=provenLiveDepth[1]=nullptr;}
} ExternalAtomicCandidates;
std::uint64_t PresentEpoch=9,ExternalAtomicAllocationAttemptEpoch=0,ExternalAtomicReplayEpoch=0;
bool R7CandidatePresentBoundaryCovered=true;
bool R7CandidateResetBoundaryCovered=true;
unsigned R7CandidateResetInFlight=0;
bool chainCovered=true;
bool R7CandidateSwapChainCovered(IDirect3DDevice9*){return chainCovered;}
bool FormatHasStencil(D3DFORMAT){return false;}
struct InternalPassScope{InternalPassScope(){}~InternalPassScope(){}};
struct Hook{template<class R,class... A>R stdcall(A...){return S_OK;}}
    SetRenderTargetHook,SetDepthStencilSurfaceHook,ClearHook;
unsigned rasterCalls=0;
R7CandidateSeedResult seedResult=R7CandidateSeedResult::Seeded;
template<class C,class D,class R>R7CandidateSeedResult R7SeedInactivePair(
    Pair&,IDirect3DDevice9*,IDirect3DSurface9*,IDirect3DSurface9*,C,D,R raster,
    unsigned=0,unsigned=2,bool=true){
    ++rasterCalls;if(seedResult==R7CandidateSeedResult::Seeded)raster();return seedResult;
}
'''
retention_cases=r'''
int main(){
    unsigned cases=0;
    for(unsigned mask=0;mask<512;++mask){
        IDirect3DDevice9 d;d.chains=(mask&1)?2:1;d.chainFail=mask&2;
        d.nullChain=mask&4;d.chain.fail=mask&8;d.chain.pp.EnableAutoDepthStencil=!(mask&16);
        d.chain.pp.Flags=(mask&32)?2:0;d.depthFail=mask&64;
        d.nullDepth=mask&128;d.depth.writeFail=mask&256;
        R7CaptureFreshAutomaticDepth(&d);
        assert(R7DepthRetentionProven(&d.depth)==(mask==0));
        assert(d.chain.refs==0&&d.depth.refs==0);
        R7ForgetAutomaticDepthProof();
        assert(!R7DepthRetentionProven(&d.depth));++cases;
    }
    for(unsigned mask=0;mask<128;++mask){
        IDirect3DDevice9 d;IDirect3DSurface9 surface;IDirect3DSurface9* out=nullptr;
        d.game=!(mask&1);StereoBaseCallbacksArmed=!(mask&2);
        createHr=(mask&4)?E_FAIL:S_OK;created=(mask&8)?nullptr:&surface;
        surface.writeFail=mask&16;creates=0;
        auto hr=CreateDepthRetentionDest(&d,1920,1080,3,4,1,(mask&32)?1:0,
            (mask&64)?nullptr:&out,nullptr);
        assert(hr==createHr&&creates==1);
        assert(R7DepthRetentionProven(&surface)==(mask==0));
        R7ForgetAutomaticDepthProof();
        assert(R7DepthRetentionProven(&surface)==(mask==0));++cases;
    }
    // Direct Ex API and nested base delegation: only outer success,
    // non-discard, private resource and owned device can certify retention.
    HANDLE sharedHandle=nullptr;
    for(unsigned mask=0;mask<512;++mask){
        IDirect3DDevice9Ex ex;IDirect3DSurface9 surface;IDirect3DSurface9* out=nullptr;
        ex.game=!(mask&1);StereoBaseCallbacksArmed=!(mask&2);
        exHr=(mask&4)?E_FAIL:S_OK;created=(mask&8)?nullptr:&surface;
        surface.writeFail=mask&16;delegateBase=mask&128;
        expectedShared=(mask&256)?&sharedHandle:nullptr;
        expectedUsage=0x1000u;creates=0;exCreates=0;createHr=S_OK;
        const auto hr=CreateDepthRetentionExDest(&ex,1920,1080,3,4,1,(mask&32)?1:0,
            (mask&64)?nullptr:&out,expectedShared,expectedUsage);
        assert(hr==exHr&&exCreates==1&&creates==unsigned(delegateBase));
        assert(R7DepthCreationNesting==0);
        const bool expected=(mask&~128u)==0;
        assert(R7DepthRetentionProven(&surface)==expected);
        assert(surface.writes<=1);R7ForgetAutomaticDepthProof();
        assert(R7DepthRetentionProven(&surface)==expected);++cases;
    }
    {IDirect3DDevice9 ex;IDirect3DSurface9 surface;IDirect3DSurface9* out=nullptr;
     StereoBaseCallbacksArmed=true;created=&surface;createHr=S_OK;
     assert(CreateDepthRetentionDest(&ex,1920,1080,3,4,1,0,&out,&sharedHandle)==S_OK);
     assert(!R7DepthRetentionProven(&surface)&&surface.writes==0);}
    IDirect3DDevice9 d;D3DVIEWPORT9 vp;
    assert(R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0)==R7CandidateSeedResult::Unavailable);
    assert(rasterCalls==0&&ExternalAtomicCandidates.allocations==0);
    ++PresentEpoch;R7MarkDepthRetention(&left,0);
    R7CandidatePresentBoundaryCovered=false;
    assert(R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0)==R7CandidateSeedResult::Unavailable);
    assert(rasterCalls==0&&ExternalAtomicCandidates.allocations==0);
    R7CandidatePresentBoundaryCovered=true;
    R7CandidateResetBoundaryCovered=false;
    assert(R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0)==R7CandidateSeedResult::Unavailable);
    R7CandidateResetBoundaryCovered=true;R7CandidateResetInFlight=1;
    assert(R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0)==R7CandidateSeedResult::Unavailable);
    assert(rasterCalls==0&&ExternalAtomicCandidates.allocations==0);
    R7CandidateResetInFlight=0;
    chainCovered=false;
    assert(R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0)==R7CandidateSeedResult::Unavailable);
    assert(rasterCalls==0&&ExternalAtomicCandidates.allocations==0);
    ++PresentEpoch;chainCovered=true;
    assert(R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0)==R7CandidateSeedResult::Seeded);
    assert(rasterCalls==1&&ExternalAtomicReplayEpoch==PresentEpoch);
    unsigned draws=0;auto draw=[&](){++draws;return S_OK;};
    assert(R7ReplayInactiveEye(&d,0,&color,&left,draw)==R7CandidateSeedResult::Seeded);
    assert(R7ReplayInactiveEye(&d,1,&rc,&right,draw)==R7CandidateSeedResult::Seeded);
    assert(draws==2);
    assert(R7ReplayInactiveEye(&d,0,&color,&right,draw)==R7CandidateSeedResult::Unavailable);
    assert(draws==2&&ExternalAtomicReplayEpoch==0);
    for(unsigned eye: {0u,1u,2u}){
        ExternalAtomicReplayEpoch=PresentEpoch;
        assert(R7ReplayInactiveEye(&d,eye,&color,nullptr,draw)==R7CandidateSeedResult::Unavailable);
        assert(draws==2&&ExternalAtomicReplayEpoch==0);
    }
    left.size=4;assert(!R7DepthRetentionProven(&left));
    left.size=8;left.readFail=true;assert(!R7DepthRetentionProven(&left));
    std::cout<<"R7_DEPTH_RETENTION_PROOF_PASS "<<cases<<" plus seed/replay and malformed tag cases\n";
}
'''
assert "R7ForgetAutomaticDepthProof();ReleaseStereoResources();" in source
r13=(Path("src/vr/d3d9/stereo_renderer_r13.cpp").read_text())
assert "R7ForgetAutomaticDepthProof();\n            ReleaseStereoResources();" in r13
assert "InstallStereoHooks(device,true);" in source
assert "CreateDepthStencilSurfaceVtableIndex = 29;" in source
assert "CreateDepthStencilSurfaceExVtableIndex = 131;" in source
assert "CreateDepthRetentionExHook = {};" in source
assert "exTable[CreateDepthStencilSurfaceExVtableIndex]!=vtable[CreateDepthStencilSurfaceVtableIndex]" in source
assert "exTable[CreateDepthStencilSurfaceExVtableIndex],CreateDepthRetentionExDest,disabled" in source
assert "if(!CreateDepthRetentionExHook&&(exQuery!=E_NOINTERFACE||ex))\n                    CreateDepthRetentionHook={};" in source
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"depth_retention.cpp"
    exe=Path(temp)/"depth_retention"
    cpp.write_text("#include <initializer_list>\n"+retention_stub+retention+entry_stub+entry+retention_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter79: direct PresentEx may never enter the base Present epoch owner.
# Extract the actual trampoline and check receipts at the driver boundary.
present_ex=source[source.index("HRESULT __stdcall R7CandidatePresentExDest("):
                  source.index("enum class R7CandidateSeedResult")]
present_ex_stub=r'''
#include <cassert>
#include <atomic>
#include <cstdint>
#include <iostream>
#define __stdcall
using HRESULT=int;using DWORD=unsigned;using HWND=void*;
struct RECT{int value;};struct RGNDATA{int value;};
struct IDirect3DDevice9Ex{bool game=true;};
std::atomic<bool> StereoBaseCallbacksArmed{true};
bool IsGameDevice(IDirect3DDevice9Ex* d){return d&&d->game;}
std::uint64_t PresentEpoch=9,ExternalAtomicAllocationAttemptEpoch=0,ExternalAtomicReplayEpoch=0;
std::uint64_t expectedReplay=0,expectedAttempt=0;
IDirect3DDevice9Ex* expectedDevice=nullptr;
const RECT *expectedSource=nullptr,*expectedDest=nullptr;
HWND expectedWindow=nullptr;const RGNDATA* expectedDirty=nullptr;
DWORD expectedFlags=0;HRESULT result=0;unsigned calls=0;
struct PresentExHook{
    template<class R> R stdcall(IDirect3DDevice9Ex* d,const RECT* src,const RECT* dst,
        HWND window,const RGNDATA* dirty,DWORD flags){
        ++calls;
        assert(d==expectedDevice&&src==expectedSource&&dst==expectedDest&&
            window==expectedWindow&&dirty==expectedDirty&&flags==expectedFlags);
        assert(ExternalAtomicReplayEpoch==expectedReplay&&
            ExternalAtomicAllocationAttemptEpoch==expectedAttempt&&PresentEpoch==9);
        return result;
    }
} CandidatePresentExHook;
'''
present_ex_cases=r'''
int main(){
    RECT src{1},dst{2};RGNDATA dirty{3};int window=4;
    IDirect3DDevice9Ex game,other;other.game=false;
    for(unsigned mask=0;mask<2048;++mask){
        StereoBaseCallbacksArmed=!(mask&1);
        expectedDevice=(mask&2)?&other:&game;
        if(mask&4)expectedDevice=nullptr;
        ExternalAtomicReplayEpoch=(mask&8)?0:((mask&16)?8:9);
        ExternalAtomicAllocationAttemptEpoch=(mask&32)?9:0;
        expectedSource=(mask&64)?&src:nullptr;expectedDest=(mask&128)?&dst:nullptr;
        expectedWindow=(mask&256)?&window:nullptr;
        expectedDirty=(mask&512)?&dirty:nullptr;
        expectedFlags=mask;result=(mask&1024)?-1:0;calls=0;
        const bool owned=!(mask&7);
        expectedReplay=owned?0:ExternalAtomicReplayEpoch;
        expectedAttempt=owned?9:ExternalAtomicAllocationAttemptEpoch;
        assert(R7CandidatePresentExDest(expectedDevice,expectedSource,expectedDest,
            expectedWindow,expectedDirty,expectedFlags)==result);
        assert(calls==1&&PresentEpoch==9&&ExternalAtomicReplayEpoch==expectedReplay&&
            ExternalAtomicAllocationAttemptEpoch==expectedAttempt);
    }
    std::cout<<"R7_DIRECT_PRESENTEX_BOUNDARY_PASS 2048\\n";
}
'''
assert "PresentExVtableIndex = 121;" in source
assert "R7CandidatePresentBoundaryCovered=exQuery==E_NOINTERFACE&&!ex;" in source
assert "target,R7CandidatePresentExDest,disabled" in source
assert "R7CandidatePresentBoundaryCovered=static_cast<bool>(CandidatePresentExHook);" in source
assert "R7CandidatePresentBoundaryCovered=false;\n\t\t\tCandidatePresentExHook = {};" in source
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"present_ex.cpp"
    exe=Path(temp)/"present_ex"
    cpp.write_text(present_ex_stub+present_ex+present_ex_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter80: ResetEx may bypass classic Reset resource retirement.
reset_ex=source[source.index("HRESULT __stdcall R7CandidateResetExDest("):
                source.index("// Direct PresentEx can bypass")]
reset_ex_stub=r'''
#include <cassert>
#include <atomic>
#include <cstdint>
#include <iostream>
#define __stdcall
using HRESULT=int;
struct D3DPRESENT_PARAMETERS{int value;};
struct D3DDISPLAYMODEEX{int value;};
struct IDirect3DDevice9Ex{bool game=true;};
std::atomic<bool> StereoBaseCallbacksArmed{true};
bool IsGameDevice(IDirect3DDevice9Ex* d){return d&&d->game;}
std::uint64_t PresentEpoch=9,ExternalAtomicAllocationAttemptEpoch=0,ExternalAtomicReplayEpoch=0;
unsigned R7CandidateResetInFlight=0,proof=1,resets=0,calls=0,r9Retires=0;
bool allocated=true,owned=false,nested=false;
void R7ForgetAutomaticDepthProof(){++proof;}
void R9RetireDirectResetResources(){assert(R7CandidateResetInFlight==1);++r9Retires;}
unsigned transportRetires=0;
void RetireTransport() noexcept {assert(r9Retires==1);++transportRetires;}
using R7DirectResetTransportOwnerFn=void(*)() noexcept;
std::atomic<R7DirectResetTransportOwnerFn> R7DirectResetTransportOwner{nullptr};
unsigned baselineRetires=0;
void RetireBaseline() noexcept {assert(r9Retires==1&&transportRetires==0);++baselineRetires;}
std::atomic<R7DirectResetTransportOwnerFn> R7DirectResetBaselineOwner{nullptr};
unsigned rasterRetires=0;bool rasterValid=true;
void RetireRaster() noexcept {assert(R7CandidateResetInFlight==1);assert(rasterRetires==calls);++rasterRetires;rasterValid=false;}
std::atomic<R7DirectResetTransportOwnerFn> R7DirectResetRasterOwner{nullptr};
constexpr HRESULT D3D_OK=0;
unsigned lifecycleCalls=0;HRESULT lifecycleResult=0;
void Lifecycle(bool before,HRESULT hr) noexcept {
    assert(R7CandidateResetInFlight==1);
    assert(before?calls==0:calls==1);
    assert(lifecycleCalls==unsigned(!before));
    if(before)assert(hr==D3D_OK);else lifecycleResult=hr;
    ++lifecycleCalls;
}
using R7DirectResetLifecycleOwnerFn=void(*)(bool,HRESULT) noexcept;
std::atomic<R7DirectResetLifecycleOwnerFn> R7DirectResetLifecycleOwner{nullptr};
bool R7RetireDirectResetCore(){assert(r9Retires==1);assert(transportRetires==unsigned(bool(R7DirectResetTransportOwner.load())));return false;}
struct Pair{void Reset(){++resets;allocated=false;}} ExternalAtomicCandidates;
IDirect3DDevice9Ex* expectedDevice=nullptr;
D3DPRESENT_PARAMETERS* expectedParams=nullptr;
D3DDISPLAYMODEEX* expectedMode=nullptr;
HRESULT result=0;
struct Hook{
    template<class R> R stdcall(IDirect3DDevice9Ex* d,D3DPRESENT_PARAMETERS* p,D3DDISPLAYMODEEX* m){
        ++calls;assert(d==expectedDevice&&p==expectedParams&&m==expectedMode);
        const bool rasterOwned=owned&&bool(R7DirectResetRasterOwner.load());
        assert(lifecycleCalls==unsigned(owned&&bool(R7DirectResetLifecycleOwner.load())));
        assert(rasterRetires==unsigned(rasterOwned)&&rasterValid!=rasterOwned);
        // Simulate a reentrant getter repopulating old borrowed identities.
        rasterValid=true;
        assert(r9Retires==unsigned(owned));
        assert(baselineRetires==unsigned(owned&&bool(R7DirectResetBaselineOwner.load())));
        assert(transportRetires==unsigned(owned&&bool(R7DirectResetTransportOwner.load())));
        if(owned){
            assert(!allocated&&resets==1&&proof==2&&R7CandidateResetInFlight==1);
            assert(ExternalAtomicReplayEpoch==0&&ExternalAtomicAllocationAttemptEpoch==PresentEpoch);
            if(nested){PresentEpoch=1;ExternalAtomicAllocationAttemptEpoch=0;ExternalAtomicReplayEpoch=1;}
        }else{
            assert(allocated&&resets==0&&proof==1&&R7CandidateResetInFlight==0);
        }
        return result;
    }
} CandidateResetExHook;
'''
reset_ex_cases=r'''
int main(){
    IDirect3DDevice9Ex game,other;other.game=false;
    D3DPRESENT_PARAMETERS pp{7};D3DDISPLAYMODEEX mode{8};
    for(unsigned mask=0;mask<4096;++mask){
        R7DirectResetLifecycleOwner=(mask&2048)?Lifecycle:nullptr;
        R7DirectResetRasterOwner=(mask&1024)?RetireRaster:nullptr;
        R7DirectResetBaselineOwner=(mask&512)?RetireBaseline:nullptr;
        R7DirectResetTransportOwner=(mask&256)?RetireTransport:nullptr;
        StereoBaseCallbacksArmed=!(mask&1);
        expectedDevice=(mask&2)?&other:&game;
        if(mask&4)expectedDevice=nullptr;
        expectedParams=(mask&8)?&pp:nullptr;expectedMode=(mask&16)?&mode:nullptr;
        nested=mask&32;result=(mask&64)?-1:0;owned=!(mask&7);
        const std::uint64_t initialReplay=(mask&128)?9:0;
        PresentEpoch=9;ExternalAtomicAllocationAttemptEpoch=0;ExternalAtomicReplayEpoch=initialReplay;
        R7CandidateResetInFlight=0;proof=1;resets=0;calls=0;r9Retires=0;transportRetires=0;baselineRetires=0;rasterRetires=0;rasterValid=true;allocated=true;lifecycleCalls=0;lifecycleResult=123;
        assert(R7CandidateResetExDest(expectedDevice,expectedParams,expectedMode)==result);
        assert(calls==1&&R7CandidateResetInFlight==0);
        const bool rasterOwned=owned&&bool(R7DirectResetRasterOwner.load());
        assert(rasterRetires==(rasterOwned?2u:0u)&&rasterValid!=rasterOwned);
        const bool lifecycleOwned=owned&&bool(R7DirectResetLifecycleOwner.load());
        assert(lifecycleCalls==(lifecycleOwned?2u:0u));
        assert(lifecycleResult==(lifecycleOwned?result:123));
        assert(PresentEpoch==(owned&&nested?1u:9u));
        assert(ExternalAtomicReplayEpoch==(owned?0:initialReplay));
        assert(ExternalAtomicAllocationAttemptEpoch==(owned?PresentEpoch:0));
        assert(resets==(owned?1u:0u)&&proof==(owned?3u:1u)&&allocated==!owned);
    }
    std::cout<<"R7_DIRECT_RESETEX_BOUNDARY_PASS 4096\n";
}
'''
assert "ResetExVtableIndex = 132;" in source
assert "target,R7CandidateResetExDest,disabled" in source
assert "R7CandidateResetBoundaryCovered=static_cast<bool>(CandidateResetExHook);" in source
assert "R7CandidateResetBoundaryCovered=false;\n            CandidateResetExHook={};" in source
assert "R7CandidateResetInFlight||ExternalAtomicAllocationAttemptEpoch==PresentEpoch" in source
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"reset_ex.cpp"
    exe=Path(temp)/"reset_ex"
    cpp.write_text(reset_ex_stub+reset_ex+reset_ex_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter81: direct implicit chain Present and additional-chain creation are
# independent physical owners. Execute production callbacks with COM mocks.
chain_owner=source[source.index("HRESULT __stdcall R7CandidateAdditionalSwapChainDest("):
                   source.index("void ReleaseStereoResources();")]
chain_stub=r'''
#include <cassert>
#include <atomic>
#include <cstdint>
#include <iostream>
#define __stdcall
using HRESULT=int;using DWORD=unsigned;using HWND=void*;
bool SUCCEEDED(HRESULT hr){return hr>=0;}
struct RECT{};struct RGNDATA{};struct D3DPRESENT_PARAMETERS{};
struct IDirect3DDevice9{bool game=true;unsigned refs=0;void Release(){assert(refs);--refs;}};
struct IDirect3DSwapChain9{
    IDirect3DDevice9* owner=nullptr;HRESULT getHr=0;unsigned gets=0;
    HRESULT GetDevice(IDirect3DDevice9** out){++gets;*out=owner;if(owner)++owner->refs;return getHr;}
};
template<class T>void ReleaseCom(T*& p){if(p){p->Release();p=nullptr;}}
bool IsGameDevice(IDirect3DDevice9* d){return d&&d->game;}
std::atomic<bool> StereoBaseCallbacksArmed{true};
std::uint64_t PresentEpoch=9,ExternalAtomicAllocationAttemptEpoch=0,ExternalAtomicReplayEpoch=9;
bool R7CandidateAdditionalChainSeen=false;
std::uint64_t expectedReplay=0,expectedAttempt=0;
bool expectedAdditional=false;unsigned calls=0;HRESULT result=0;
IDirect3DDevice9* expectedDevice=nullptr;
IDirect3DSwapChain9* expectedChain=nullptr;
D3DPRESENT_PARAMETERS* expectedParams=nullptr;IDirect3DSwapChain9** expectedOut=nullptr;
const RECT *expectedSrc=nullptr,*expectedDst=nullptr;const RGNDATA* expectedDirty=nullptr;
HWND expectedWindow=nullptr;DWORD expectedFlags=0;
void Check(){++calls;assert(PresentEpoch==9&&ExternalAtomicReplayEpoch==expectedReplay&&
    ExternalAtomicAllocationAttemptEpoch==expectedAttempt&&R7CandidateAdditionalChainSeen==expectedAdditional);}
struct AdditionalHook{
    template<class R>R stdcall(IDirect3DDevice9* d,D3DPRESENT_PARAMETERS* p,IDirect3DSwapChain9** out){
        assert(d==expectedDevice&&p==expectedParams&&out==expectedOut);Check();return result;}
} CandidateAdditionalSwapChainHook;
struct PresentHook{
    template<class R>R stdcall(IDirect3DSwapChain9* c,const RECT* s,const RECT* d,HWND w,
        const RGNDATA* dirty,DWORD flags){
        assert(c==expectedChain&&s==expectedSrc&&d==expectedDst&&w==expectedWindow&&
            dirty==expectedDirty&&flags==expectedFlags);Check();
        if(c&&c->owner)assert(!c->owner->refs);
        return result;}
} CandidateSwapChainPresentHook;
'''
chain_cases=r'''
int main(){
    IDirect3DDevice9 game,other;other.game=false;
    IDirect3DSwapChain9 chain;IDirect3DSwapChain9* output=nullptr;
    RECT src,dst;RGNDATA dirty;D3DPRESENT_PARAMETERS params;int window=0;
    for(unsigned mask=0;mask<2048;++mask){
        StereoBaseCallbacksArmed=!(mask&1);chain.owner=(mask&2)?&other:&game;
        if(mask&4)chain.owner=nullptr;
        chain.getHr=(mask&8)?-1:0;expectedChain=(mask&16)?nullptr:&chain;
        expectedSrc=(mask&32)?&src:nullptr;expectedDst=(mask&64)?&dst:nullptr;
        expectedWindow=(mask&128)?&window:nullptr;expectedDirty=(mask&256)?&dirty:nullptr;
        result=(mask&512)?-1:0;expectedFlags=mask;
        ExternalAtomicReplayEpoch=(mask&1024)?0:9;ExternalAtomicAllocationAttemptEpoch=0;
        R7CandidateAdditionalChainSeen=false;expectedAdditional=false;calls=0;chain.gets=0;
        bool retire=!(mask&1)&&(!expectedChain||chain.getHr<0||!chain.owner||chain.owner->game);
        expectedReplay=retire?0:ExternalAtomicReplayEpoch;expectedAttempt=retire?9:0;
        assert(R7CandidateSwapChainPresentDest(expectedChain,expectedSrc,expectedDst,
            expectedWindow,expectedDirty,expectedFlags)==result);
        assert(calls==1&&chain.gets==unsigned(!(mask&1)&&expectedChain)&&!game.refs&&!other.refs);
    }
    for(unsigned mask=0;mask<128;++mask){
        StereoBaseCallbacksArmed=!(mask&1);expectedDevice=(mask&2)?&other:&game;
        if(mask&4)expectedDevice=nullptr;
        expectedParams=(mask&8)?&params:nullptr;expectedOut=(mask&16)?&output:nullptr;
        result=(mask&32)?-1:0;ExternalAtomicReplayEpoch=9;ExternalAtomicAllocationAttemptEpoch=0;
        R7CandidateAdditionalChainSeen=bool(mask&64);calls=0;
        bool retire=!(mask&7);
        expectedReplay=retire?0:9;expectedAttempt=retire?9:0;
        expectedAdditional=retire||R7CandidateAdditionalChainSeen;
        assert(R7CandidateAdditionalSwapChainDest(expectedDevice,expectedParams,expectedOut)==result);
        assert(calls==1&&R7CandidateAdditionalChainSeen==expectedAdditional);
    }
    std::cout<<"R7_SWAPCHAIN_PHYSICAL_OWNER_PASS 2176\n";
}
'''
assert "SwapChainPresentVtableIndex = 3;" in source
assert "CreateAdditionalSwapChainVtableIndex = 13;" in source
assert "chainTarget,R7CandidateSwapChainPresentDest,disabled" in source
assert "additionalTarget,R7CandidateAdditionalSwapChainDest,disabled" in source
assert "R7GetImplicitChainPresentTarget(device)==R7CandidateSwapChainPresentTarget" in source
assert "if(!R7CandidateSwapChainCovered(device))return R7CandidateSeedResult::Unavailable;" in source
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"swapchain.cpp"
    exe=Path(temp)/"swapchain"
    cpp.write_text(chain_stub+chain_owner+chain_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter82: a direct ResetEx can bypass the existing R13 common retirement.
# Test the actual R7 core retirement, not a second readiness predicate.
direct_reset_core=source[source.index("bool R7RetireDirectResetCore()"):
                         source.index("// Direct ResetEx bypasses")]
direct_core_stub=r'''
#include <cassert>
#include <iostream>
bool StereoResourcesReady=false,DirectTransportResourcesReady=false;
int obj=0;
int *BackBuffer=nullptr,*TrackedRenderTarget=nullptr,*TrackedDepthStencil=nullptr,
    *RightEyeSurface=nullptr,*RightEyeDepth=nullptr,*LeftResolveSurface=nullptr,
    *RightResolveSurface=nullptr;
bool FrameHadDuplicatedDraw=true,FrameHadWorldStereo=true;
unsigned FrameStereoPoseSequence=9;
struct Metadata{bool valid=false;} FrameStereoMetadata;
namespace OutRunVR{enum Reason{StereoFailureResourceUnavailable};}
unsigned releases=0,invalidations=0,poisons=0;
void ReleaseStereoResources(){
    ++releases;StereoResourcesReady=false;DirectTransportResourcesReady=false;
    BackBuffer=TrackedRenderTarget=TrackedDepthStencil=RightEyeSurface=
        RightEyeDepth=LeftResolveSurface=RightResolveSurface=nullptr;
}
void InvalidateTrackedRenderStates(){++invalidations;}
void PoisonFrame(OutRunVR::Reason reason){
    assert(reason==OutRunVR::StereoFailureResourceUnavailable);++poisons;
}
'''
direct_core_cases=r'''
int main(){
    for(unsigned mask=0;mask<512;++mask){
        StereoResourcesReady=bool(mask&1);
        BackBuffer=(mask&2)?&obj:nullptr;
        TrackedRenderTarget=(mask&4)?&obj:nullptr;
        TrackedDepthStencil=(mask&8)?&obj:nullptr;
        RightEyeSurface=(mask&16)?&obj:nullptr;
        RightEyeDepth=(mask&32)?&obj:nullptr;
        LeftResolveSurface=(mask&64)?&obj:nullptr;
        RightResolveSurface=(mask&128)?&obj:nullptr;
        DirectTransportResourcesReady=bool(mask&256);
        FrameHadDuplicatedDraw=FrameHadWorldStereo=true;
        FrameStereoPoseSequence=9;FrameStereoMetadata.valid=true;
        releases=invalidations=poisons=0;
        const bool owned=mask!=0;
        assert(R7RetireDirectResetCore()==owned);
        assert(releases==unsigned(owned)&&invalidations==unsigned(owned)&&poisons==unsigned(owned));
        assert(!StereoResourcesReady&&!DirectTransportResourcesReady&&!BackBuffer&&!TrackedRenderTarget&&
            !TrackedDepthStencil&&!RightEyeSurface&&!RightEyeDepth&&!LeftResolveSurface&&!RightResolveSurface);
        assert(FrameHadDuplicatedDraw==!owned&&FrameHadWorldStereo==!owned&&
            FrameStereoPoseSequence==(owned?0u:9u)&&FrameStereoMetadata.valid==!owned);
        // A nested classic owner already retired the entire R7 core.
        assert(!R7RetireDirectResetCore()&&releases==unsigned(owned));
    }
    std::cout<<"R7_DIRECT_RESET_CORE_PASS 512\n";
}
'''
reset_callback=source[source.index("HRESULT __stdcall R7CandidateResetExDest("):
                      source.index("// Direct PresentEx can bypass")]
assert reset_callback.index("if(!R7RetireDirectResetCore())ExternalAtomicCandidates.Reset();") < reset_callback.rindex("CandidateResetExHook.stdcall<HRESULT>")
assert reset_callback.index("ExternalAtomicAllocationAttemptEpoch=PresentEpoch;",reset_callback.index("if(!R7RetireDirectResetCore())")) < reset_callback.rindex("CandidateResetExHook.stdcall<HRESULT>")
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"direct_reset_core.cpp"
    exe=Path(temp)/"direct_reset_core"
    cpp.write_text(direct_core_stub+direct_reset_core+direct_core_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter83: exercise actual R9 independent ownership cleanup, including a
# R7-empty / R9-still-owned generation and repeated nested retirement.
r9_source=Path("src/vr/d3d9/stereo_renderer.cpp").read_text(encoding="utf-8")
r9_retire=r9_source[r9_source.index("void R9ReleaseMonoResources()"):
                    r9_source.index("bool R9CaptureMainDepth(")]
r9_stub=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
struct Surface{unsigned releases=0;};
template<class T> void ReleaseCom(T*& ptr){if(ptr){++ptr->releases;ptr=nullptr;}}
Surface *R9MonoDepth=nullptr,*R9MonoSurface=nullptr,
    *R9DeferredDepthIdentity=nullptr,*R9MainDepthIdentity=nullptr;
struct Desc{int width=0;} R9MainDepthDesc;
std::uint64_t R9MonoResourceGeneration=0,R9FirstFailureEpoch=0;
bool R9MonoSeeded=false,R9MonoBackupGap=false,R9MainDepthKnown=false,
    R9DeferredDepth=false,R9StereoSeeded=false,R9MonoElisionArmed=false,
    R9ExpectMainDepthAfterReset=false;
unsigned R9MonoElisionFailureStreak=0;
'''
r9_cases=r'''
int main(){
    for(unsigned mask=0;mask<1024;++mask){
        Surface md,mc,dd,main;
        R9MonoDepth=(mask&1)?&md:nullptr;
        R9MonoSurface=(mask&2)?&mc:nullptr;
        R9DeferredDepthIdentity=(mask&4)?&dd:nullptr;
        R9MainDepthIdentity=(mask&8)?&main:nullptr;
        R9MonoSeeded=bool(mask&16);R9MonoBackupGap=bool(mask&32);
        R9MainDepthKnown=bool(mask&64);R9DeferredDepth=bool(mask&128);
        R9StereoSeeded=bool(mask&256);R9MonoElisionArmed=bool(mask&512);
        R9MainDepthDesc.width=1920;R9MonoResourceGeneration=12;
        R9FirstFailureEpoch=9;R9MonoElisionFailureStreak=3;
        R9ExpectMainDepthAfterReset=false;
        for(int repeat=0;repeat<2;++repeat){
            R9RetireDirectResetResources();
            assert(!R9MonoDepth&&!R9MonoSurface&&!R9DeferredDepthIdentity&&!R9MainDepthIdentity);
            assert(!R9MonoSeeded&&!R9MonoBackupGap&&!R9MainDepthKnown&&!R9DeferredDepth);
            assert(!R9StereoSeeded&&!R9MonoElisionArmed&&R9ExpectMainDepthAfterReset);
            assert(!R9MainDepthDesc.width&&!R9MonoResourceGeneration&&!R9FirstFailureEpoch&&!R9MonoElisionFailureStreak);
            assert(md.releases==unsigned(bool(mask&1))&&mc.releases==unsigned(bool(mask&2)));
            assert(dd.releases==unsigned(bool(mask&4))&&main.releases==unsigned(bool(mask&8)));
        }
    }
    std::cout<<"R9_DIRECT_RESET_RETIRE_PASS 1024\\n";
}
'''
assert reset_callback.index("R9RetireDirectResetResources();") < reset_callback.index("if(!R7RetireDirectResetCore())")
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"r9_direct_reset.cpp"
    exe=Path(temp)/"r9_direct_reset"
    cpp.write_text(r9_stub+r9_retire+r9_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter84: test actual R13 ACK view/handle retirement and overlay boundary.
r13_source=Path("src/vr/d3d9/stereo_renderer_r13.cpp").read_text(encoding="utf-8")
r13_retire=r13_source[r13_source.index("void R13ReleaseAckState()"):
                     r13_source.index("bool R13EnsureAckState()")]
r13_stub=r'''
#include <cassert>
#include <atomic>
#include <iostream>
using HRESULT=int;using HANDLE=void*;
constexpr HRESULT D3D_OK=0;
std::atomic<bool> R13OverlayReady{false};
bool R13ForceMonoShadow=false,R13DirectCopyPathRejected=false;
HRESULT R13DirectCopyRejectHr=D3D_OK;
const void* R13AckState=nullptr;
HANDLE R13AckMapping=nullptr;
unsigned unmaps=0,closes=0;
void UnmapViewOfFile(const void* p){assert(p==R13AckState&&p);++unmaps;}
void CloseHandle(HANDLE h){assert(h==R13AckMapping&&h&&!R13AckState);++closes;}
'''
r13_cases=r'''
int main(){
    int view=1,handle=2;
    for(unsigned mask=0;mask<64;++mask){
        const bool armed=bool(mask&1);
        R13OverlayReady=armed;
        R13AckState=(mask&2)?&view:nullptr;
        R13AckMapping=(mask&4)?&handle:nullptr;
        R13ForceMonoShadow=bool(mask&8);
        R13DirectCopyPathRejected=bool(mask&16);
        R13DirectCopyRejectHr=(mask&32)?-1:0;
        unmaps=closes=0;
        for(int repeat=0;repeat<2;++repeat){
            R13RetireDirectResetTransport();
            assert(unmaps==unsigned(armed&&bool(mask&2)));
            assert(closes==unsigned(armed&&bool(mask&4)));
            assert(bool(R13AckState)==(!armed&&bool(mask&2)));
            assert(bool(R13AckMapping)==(!armed&&bool(mask&4)));
            assert(R13ForceMonoShadow==(!armed&&bool(mask&8)));
            assert(R13DirectCopyPathRejected==(!armed&&bool(mask&16)));
            assert(R13DirectCopyRejectHr==(!armed&&bool(mask&32)?-1:0));
        }
    }
    std::cout<<"R13_DIRECT_RESET_TRANSPORT_PASS 64\n";
}
'''
assert reset_callback.index("R7DirectResetTransportOwner.load(") < reset_callback.rindex("CandidateResetExHook.stdcall<HRESULT>")
assert "R7DirectResetTransportOwner.store(\n                            R13RetireDirectResetTransport," in r13_source
assert "R7DirectResetTransportOwner.store(nullptr," in r13_source
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"r13_direct_reset.cpp"
    exe=Path(temp)/"r13_direct_reset"
    cpp.write_text(r13_stub+r13_retire+r13_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter85: direct physical ResetEx invalidates the actual R22 baseline owner.
r22_source=Path("src/vr/d3d9/stereo_renderer_r22.cpp").read_text(encoding="utf-8")
r22_baseline=r22_source[r22_source.index("void R22FailClosedEligibility()"):
                        r22_source.index("bool R22CaptureGameScissor(")]
r22_direct=r22_source[r22_source.index("void R22RetireDirectResetBaseline()"):
                      r22_source.index("DWORD WINAPI R22InstallThread(")]
r22_stub=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <iostream>
namespace OutRunVR::RuntimeEligibility {
enum class InstallState { Pending, Ready, Failed };
unsigned calls=0;
bool eligible=true;
void FailClosed(){++calls;eligible=false;}
}
using State=OutRunVR::RuntimeEligibility::InstallState;
std::atomic<State> R22InstallState{State::Pending};
std::atomic<bool> R20StereoEligibilityGate{true};
bool R9StereoSeeded=true,R9MonoSeeded=true;
struct Shadow { bool valid=false; } R22ShadowState;
std::uint64_t R20DepthClearEpoch=0;
std::uint64_t R20DepthClearDrawSerial=0;
std::uint64_t R20DepthClearGeneration=0;
std::uint64_t R20StencilClearEpoch=0;
std::uint64_t R20StencilClearDrawSerial=0;
std::uint64_t R20StencilClearGeneration=0;
std::uint64_t R22DepthClearEpoch=0;
std::uint64_t R22DepthClearDrawSerial=0;
std::uint64_t R22DepthClearGeneration=0;
std::uint64_t R22StencilClearEpoch=0;
std::uint64_t R22StencilClearDrawSerial=0;
std::uint64_t R22StencilClearGeneration=0;
'''
r22_cases=r'''
int main(){
    using namespace OutRunVR::RuntimeEligibility;
    for(auto state:{State::Pending,State::Ready,State::Failed}){
        for(unsigned mask=0;mask<32;++mask){
            R22InstallState=state;
            calls=0;eligible=bool(mask&1);
            R20StereoEligibilityGate=bool(mask&2);
            R9StereoSeeded=bool(mask&4);R9MonoSeeded=bool(mask&8);
            R22ShadowState.valid=bool(mask&16);
            R20DepthClearEpoch=mask+1;
            R20DepthClearDrawSerial=mask+2;
            R20DepthClearGeneration=mask+3;
            R20StencilClearEpoch=mask+4;
            R20StencilClearDrawSerial=mask+5;
            R20StencilClearGeneration=mask+6;
            R22DepthClearEpoch=mask+7;
            R22DepthClearDrawSerial=mask+8;
            R22DepthClearGeneration=mask+9;
            R22StencilClearEpoch=mask+10;
            R22StencilClearDrawSerial=mask+11;
            R22StencilClearGeneration=mask+12;
            for(unsigned repeat=1;repeat<=2;++repeat){
                R22RetireDirectResetBaseline();
                const bool armed=state==State::Ready;
                assert(calls==(armed?repeat:0));
                assert(eligible==(!armed&&bool(mask&1)));
                assert(R20StereoEligibilityGate==(!armed&&bool(mask&2)));
                assert(R9StereoSeeded==(!armed&&bool(mask&4)));
                assert(R9MonoSeeded==(!armed&&bool(mask&8)));
                assert(R22ShadowState.valid==(!armed&&bool(mask&16)));
                assert(R20DepthClearEpoch==(armed?0:mask+1));
                assert(R20DepthClearDrawSerial==(armed?0:mask+2));
                assert(R20DepthClearGeneration==(armed?0:mask+3));
                assert(R20StencilClearEpoch==(armed?0:mask+4));
                assert(R20StencilClearDrawSerial==(armed?0:mask+5));
                assert(R20StencilClearGeneration==(armed?0:mask+6));
                assert(R22DepthClearEpoch==(armed?0:mask+7));
                assert(R22DepthClearDrawSerial==(armed?0:mask+8));
                assert(R22DepthClearGeneration==(armed?0:mask+9));
                assert(R22StencilClearEpoch==(armed?0:mask+10));
                assert(R22StencilClearDrawSerial==(armed?0:mask+11));
                assert(R22StencilClearGeneration==(armed?0:mask+12));
            }
        }
    }
    std::cout<<"R22_DIRECT_RESET_BASELINE_PASS 192\n";
}
'''
assert reset_callback.index("R7DirectResetBaselineOwner.load(") < reset_callback.index("R7DirectResetTransportOwner.load(")
assert "R7DirectResetBaselineOwner.store(\n                        R22RetireDirectResetBaseline," in r22_source
assert "R7DirectResetBaselineOwner.store(nullptr," in r22_source
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"r22_direct_reset.cpp"
    exe=Path(temp)/"r22_direct_reset"
    cpp.write_text(r22_stub+r22_baseline+r22_direct+r22_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter86: actual R33 viewport elision must re-query recycled COM addresses.
r33_source=Path("src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8")
r33_view=r33_source[r33_source.index("struct R33RightViewportExtent"):
                    r33_source.index("thread_local R33DepthStencilWriteState R33DepthStencilState")]
r33_retire=r33_source[r33_source.index("void R33InvalidateDepthStencilCache()"):
                      r33_source.index("// Preserve the original stencil-op semantics")]
r33_stub=r'''
#include <cassert>
#include <iostream>
using UINT=unsigned;
struct D3DSURFACE_DESC { UINT Width=0,Height=0; };
struct D3DVIEWPORT9 { UINT X=0,Y=0,Width=0,Height=0;float MinZ=0,MaxZ=1; };
struct IDirect3DSurface9 {
    UINT width=0,height=0,reads=0;bool fail=false;
    int GetDesc(D3DSURFACE_DESC* d){++reads;if(fail)return -1;*d={width,height};return 0;}
};
bool FAILED(int hr){return hr<0;}
struct DepthState { bool valid=false; } R33DepthStencilState;
'''
r33_cases=r'''
int main(){
    for(unsigned mask=0;mask<64;++mask){
        R33RetireDirectResetRaster();
        IDirect3DSurface9 right{640,480},saved{800,600};
        const D3DVIEWPORT9 oldRight{0,0,640,480},oldSaved{0,0,800,600};
        assert(R33TargetResetViewportMatches(&right,oldRight));
        assert(R33SavedTargetResetViewportMatches(&saved,oldSaved));
        R33DepthStencilState.valid=true;
        right.width=(mask&1)?640:1280;saved.height=(mask&2)?600:900;
        right.fail=bool(mask&4);saved.fail=bool(mask&8);
        // Reset can recycle the same addresses with different descriptors.
        R33RetireDirectResetRaster();
        if(mask&16)R33RetireDirectResetRaster();
        assert(!R33DepthStencilState.valid&&!R33RightViewport.valid&&!R33SavedViewport.valid);
        assert(!R33RightViewport.surface&&!R33SavedViewport.surface);
        const bool rightOld=R33TargetResetViewportMatches(&right,oldRight);
        const bool savedOld=R33SavedTargetResetViewportMatches(&saved,oldSaved);
        assert(rightOld==(!right.fail&&bool(mask&1)));
        assert(savedOld==(!saved.fail&&bool(mask&2)));
        assert(right.reads==2&&saved.reads==2);
        if(mask&32){
            right.fail=saved.fail=false;
            const D3DVIEWPORT9 newRight{0,0,right.width,right.height};
            const D3DVIEWPORT9 newSaved{0,0,saved.width,saved.height};
            assert(R33TargetResetViewportMatches(&right,newRight));
            assert(R33SavedTargetResetViewportMatches(&saved,newSaved));
        }
    }
    std::cout<<"R33_DIRECT_RESET_RASTER_PASS 64\n";
}
'''
assert "R7SetDirectResetRasterOwner(R33RetireDirectResetRaster);" in r33_source
assert "R7SetDirectResetRasterOwner(nullptr);" in r33_source
assert "R7DirectResetRasterOwner.store(owner,std::memory_order_release);" in source
assert reset_callback.index("if(retireRaster)retireRaster();") < reset_callback.index("R9RetireDirectResetResources();")
assert reset_callback.rindex("if(retireRaster)retireRaster();") > reset_callback.rindex("CandidateResetExHook.stdcall<HRESULT>")
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"r33_direct_reset.cpp"
    exe=Path(temp)/"r33_direct_reset"
    cpp.write_text(r33_stub+r33_view+r33_retire+r33_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Iter87: exercise the actual R32 reset owner and split-TU callback body.
r32_source=Path("src/vr/d3d9/stereo_renderer_r32.cpp").read_text(encoding="utf-8")
r32_reset=r32_source[r32_source.index("thread_local unsigned R32ClassicResetDepth"):
                      r32_source.index("void R32LogPerfWindow(")]
r32_direct=r32_source[r32_source.index("void R32ReviewDirectResetLifecycle("):
                       r32_source.index("HRESULT R32ReviewRunResetLifecycleCallback(")]
r32_identity=r32_source[r32_source.index("void R32ForgetDirectIdentity()"):
                         r32_source.index("}",r32_source.index("void R32ForgetDirectIdentity()"))+1]
r32_stub=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
using HRESULT=int;
constexpr HRESULT D3D_OK=0;
bool SUCCEEDED(HRESULT hr){return hr>=0;}
struct IDirect3DDevice9{bool game=true;};
bool R30SupportIsGameDevice(IDirect3DDevice9* d){return d&&d->game;}
unsigned effect=0,fast=0,live=0,renderer=0,arms=0;
bool telemetry=false;
void R30SupportInvalidateEffectStateCache(){++effect;}
void R31SupportResetFastPathState(){++fast;}
void R30SupportInvalidateLiveStateSample(){++live;}
void R30SupportInvalidateRendererStateAfterExternalRestore(){++renderer;}
std::uint32_t R32DirectHostPid=0,R32DirectHostLuidLow=0,R32DirectHostLuidHigh=0;
bool R32DirectCopyPathRejected=false,R32PerfWindowActive=false,R32FirstResetRearmLogged=false;
HRESULT R32DirectCopyRejectHr=D3D_OK;
unsigned R32FrameWorkloadCounters=0,R32PerfWindowCounters=0,R32PerfBaselineUs=0,
    R32LastPresentEndQpc=0,R32Counters=0,R32ResetEpochRearms=0,R32ResetFailures=0;
std::uint64_t R30SupportPresentEpoch(){return 19;}
namespace OutRunVR::R32 { std::uint64_t RearmMonoSafetyEpoch(std::uint64_t e){return e+2;} }
void R30SupportSetStereoRecoverySafetyThroughEpoch(std::uint64_t e){assert(e==21);++arms;}
bool R30SupportTelemetryEnabled(){return telemetry;}
namespace spdlog { void info(const char*){} }
'''
r32_cases=r'''
void dirty(){
    R32DirectHostPid=1;R32DirectHostLuidLow=2;R32DirectHostLuidHigh=3;
    R32DirectCopyPathRejected=true;R32DirectCopyRejectHr=-3;
    R32FrameWorkloadCounters=R32PerfWindowCounters=R32PerfBaselineUs=
        R32LastPresentEndQpc=R32Counters=7;
    R32PerfWindowActive=true;
}
void checkClean(){
    assert(!R32DirectHostPid&&!R32DirectHostLuidLow&&!R32DirectHostLuidHigh);
    assert(!R32DirectCopyPathRejected&&R32DirectCopyRejectHr==D3D_OK);
    assert(!R32FrameWorkloadCounters&&!R32PerfWindowCounters&&!R32PerfBaselineUs&&
        !R32LastPresentEndQpc&&!R32Counters&&!R32PerfWindowActive);
}
int main(){
    IDirect3DDevice9 game,other{false};
    for(unsigned mask=0;mask<64;++mask){
        const bool classic=mask&1,gameOwned=!(mask&2),nestedPhysical=mask&4;
        telemetry=bool(mask&8);
        const HRESULT hr=(mask&16)?-1:((mask&32)?1:0);
        effect=fast=live=renderer=arms=R32ResetEpochRearms=R32ResetFailures=0;
        dirty();unsigned physical=0;
        if(classic){
            const HRESULT got=R32WithResetLifecycle(gameOwned?&game:&other,[&](){
                ++physical;
                if(nestedPhysical&&gameOwned){
                    assert(R32ClassicResetDepth==1);
                    R32ReviewDirectResetLifecycle(true,D3D_OK);
                    assert(effect==0&&R32DirectHostPid==1);
                    R32ReviewDirectResetLifecycle(false,hr);
                    assert(effect==0&&arms==0);
                }
                return hr;
            });
            assert(got==hr&&R32ClassicResetDepth==0);
        }else{
            if(gameOwned){
                R32ReviewDirectResetLifecycle(true,D3D_OK);
                checkClean();assert(effect==1&&arms==0);
            }
            ++physical;dirty();
            if(gameOwned)R32ReviewDirectResetLifecycle(false,hr);
        }
        assert(physical==1);
        const unsigned expected=gameOwned?(classic?1:2):0;
        assert(effect==expected&&fast==expected&&live==expected&&renderer==expected);
        assert(arms==unsigned(gameOwned&&SUCCEEDED(hr)));
        assert(R32ResetEpochRearms==unsigned(gameOwned&&telemetry&&SUCCEEDED(hr)));
        assert(R32ResetFailures==unsigned(gameOwned&&telemetry&&!SUCCEEDED(hr)));
        if(gameOwned)checkClean();else assert(R32DirectHostPid==1);
    }
    std::cout<<"R32_DIRECT_RESET_LIFECYCLE_PASS 64\n";
}
'''
assert "R7SetDirectResetLifecycleOwner(R32ReviewDirectResetLifecycle);" in r33_source
assert "R7SetDirectResetLifecycleOwner(nullptr);" in r33_source
assert "R7DirectResetLifecycleOwner.store(owner,std::memory_order_release);" in source
assert reset_callback.index("if(lifecycle)lifecycle(true,D3D_OK);") < reset_callback.rindex("CandidateResetExHook.stdcall<HRESULT>")
assert reset_callback.index("if(lifecycle)lifecycle(false,hr);") > reset_callback.rindex("CandidateResetExHook.stdcall<HRESULT>")
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"r32_direct_reset.cpp"
    exe=Path(temp)/"r32_direct_reset"
    cpp.write_text(r32_stub+r32_identity+r32_reset+r32_direct+r32_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
