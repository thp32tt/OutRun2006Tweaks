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
using HRESULT=int;
using UINT=unsigned;
constexpr int FALSE=0, E_FAIL=-1, S_OK=0;
bool FAILED(HRESULT h){return h<0;}
bool SUCCEEDED(HRESULT h){return h>=0;}
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
    IDirect3DSurface9 *rt=nullptr,*depth=nullptr,*liveRt=nullptr,*liveDepth=nullptr;
    D3DVIEWPORT9 viewport{0,0,1920,1080};
    RECT scissor{4,5,1800,1000};
    HRESULT op(){return ++io==ioFail?E_FAIL:S_OK;}
    HRESULT GetRenderTarget(unsigned,IDirect3DSurface9** s){*s=rt;if(rt)++rt->refs;return op();}
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
    assert(ensure()&&d.calls==4&&pair.generation==gen);
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
upload_owner=source[source.index("HRESULT __stdcall UpdateSurfaceDest("):
                    source.index("void ReleaseStereoResources()")]
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
