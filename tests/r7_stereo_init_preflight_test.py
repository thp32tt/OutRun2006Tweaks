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
assert init.index("currentDepth,desc,savedViewport,retired))") < init.index("ReleaseStereoResources();")
assert init.index("if(captureRetired)*captureRetired=true;") < init.index("ReleaseStereoResources();")
assert "EnsureStereoResources(device,&bootstrapRestoreFailed)" in source
assert "if(captureRetired)return E_FAIL;" in source
assert "TrackedRenderTarget=currentRt;" in init
assert "TrackedDepthStencil=currentDepth;" in init
assert "GetViewport(" not in init
assert "ReplaceSurfaceRef(TrackedRenderTarget,BackBuffer)" not in init

stub = r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <initializer_list>
std::uint64_t generation=1;
unsigned calls=0,retireAt=0,releaseRetireAt=0,releases=0;
std::uint64_t R7EyeStateGeneration(){return generation;}
void step(){if(++calls==retireAt)++generation;}
using HRESULT = int;
constexpr HRESULT D3DERR_NOTFOUND=-2, E_FAIL=-1, S_OK=0;
constexpr int D3DBACKBUFFER_TYPE_MONO=0;
bool FAILED(HRESULT h) { return h<0; }
struct D3DSURFACE_DESC { int width=0; };
struct D3DVIEWPORT9 { int width=0; };
struct IDirect3DSurface9 {
    int refs=0; HRESULT descHr=S_OK;
    HRESULT GetDesc(D3DSURFACE_DESC* d) { step(); d->width=1920; return descHr; }
    void Release() { assert(refs>0); --refs; if(++releases==releaseRetireAt)++generation; }
};
template<class T> void ReleaseCom(T*& p) { if(p) {p->Release();p=nullptr;} }
struct IDirect3DDevice9 {
    IDirect3DSurface9 back,rt,depth;
    HRESULT backHr=S_OK,rtHr=S_OK,depthHr=S_OK,viewHr=S_OK;
    bool noBack=false,noRt=false,noDepth=false;
    int viewCalls=0;
    static HRESULT get(IDirect3DSurface9** out,IDirect3DSurface9& s,HRESULT hr,bool empty) {
        step(); *out=empty?nullptr:&s; if(*out) ++s.refs; return hr;
    }
    HRESULT GetBackBuffer(int,int,int,IDirect3DSurface9** out) {return get(out,back,backHr,noBack);}
    HRESULT GetRenderTarget(int,IDirect3DSurface9** out) {return get(out,rt,rtHr,noRt);}
    HRESULT GetDepthStencilSurface(IDirect3DSurface9** out) {return get(out,depth,depthHr,noDepth);}
    HRESULT GetViewport(D3DVIEWPORT9* v) {step();++viewCalls;v->width=800;return viewHr;}
};
'''
cases = r'''
void run(IDirect3DDevice9& d,bool expected,bool depthExpected=false) {
    IDirect3DSurface9 *b=nullptr,*r=nullptr,*z=nullptr;
    D3DSURFACE_DESC desc{}; D3DVIEWPORT9 view{};
    bool retired=false;
    assert(CaptureStereoInitState(&d,b,r,z,desc,view,retired)==expected);
    assert(!retired);
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
    unsigned cases=0;
    for(unsigned phase=1;phase<=5;++phase)
    for(bool failing:{false,true}){
        IDirect3DDevice9 d;
        if(failing){
            switch(phase){
            case 1:d.backHr=E_FAIL;break;
            case 2:d.back.descHr=E_FAIL;break;
            case 3:d.rtHr=E_FAIL;break;
            case 4:d.depthHr=E_FAIL;break;
            case 5:d.viewHr=E_FAIL;break;
            }
        }
        calls=releases=0;retireAt=phase;releaseRetireAt=0;
        IDirect3DSurface9 *b=nullptr,*r=nullptr,*z=nullptr;
        D3DSURFACE_DESC desc{};D3DVIEWPORT9 view{};bool retired=false;
        assert(!CaptureStereoInitState(&d,b,r,z,desc,view,retired)&&retired);
        assert(calls==phase&&!b&&!r&&!z);
        assert(!d.back.refs&&!d.rt.refs&&!d.depth.refs);
        ++cases;
    }
    for(unsigned release=1;release<=3;++release){
        IDirect3DDevice9 d;d.viewHr=E_FAIL;
        calls=releases=retireAt=0;releaseRetireAt=release;
        IDirect3DSurface9 *b=nullptr,*r=nullptr,*z=nullptr;
        D3DSURFACE_DESC desc{};D3DVIEWPORT9 view{};bool retired=false;
        assert(!CaptureStereoInitState(&d,b,r,z,desc,view,retired)&&retired);
        assert(calls==5&&releases==3&&!b&&!r&&!z);
        assert(!d.back.refs&&!d.rt.refs&&!d.depth.refs);
        ++cases;
    }
    calls=releases=retireAt=releaseRetireAt=0;
    {IDirect3DDevice9 d;run(d,true,true);}
    std::cout<<"R7_INIT_CAPTURE_GENERATION_PASS "<<cases<<" + fresh retry\\n";
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
std::uint64_t R7CandidateBoundarySerial=0;
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
    void (*onDesc)()=nullptr;
    void (*onRelease)()=nullptr;
    HRESULT GetDesc(D3DSURFACE_DESC* d){*d=desc;if(onDesc)onDesc();return S_OK;}
    void Release(){assert(refs>0);--refs;if(onRelease)onRelease();}
};
template<class T> void ReleaseCom(T*& p){if(p){p->Release();p=nullptr;}}
struct IDirect3DDevice9 {
    IDirect3DSurface9 made[32]{};
    unsigned calls=0,failAt=0,nullAt=0,mismatchAt=0;
    unsigned retireAt=0,retireDescAt=0;
    bool retireCaps=false;
    void (*onRetire)()=nullptr;
    unsigned io=0,ioFail=0,clearCalls=0,liveWrites=0;
    unsigned interruptIo=0,interruptAux=0;
    void (*onInterrupt)()=nullptr;
    UINT capsTargets=1,capsCalls=0,auxCalls=0;
    HRESULT capsHr=S_OK,auxHr[4]{S_OK,D3DERR_NOTFOUND,D3DERR_NOTFOUND,D3DERR_NOTFOUND};
    IDirect3DSurface9* aux[4]{};
    HRESULT GetDeviceCaps(D3DCAPS9* c){++capsCalls;c->NumSimultaneousRTs=capsTargets;if(retireCaps&&onRetire)onRetire();return capsHr;}
    IDirect3DSurface9 *rt=nullptr,*depth=nullptr,*liveRt=nullptr,*liveDepth=nullptr;
    D3DVIEWPORT9 viewport{0,0,1920,1080};
    RECT scissor{4,5,1800,1000};
    HRESULT op(){++io;if(io==interruptIo&&onInterrupt)onInterrupt();return io==ioFail?E_FAIL:S_OK;}
    HRESULT GetRenderTarget(unsigned slot,IDirect3DSurface9** s){
        if(slot){assert(slot<capsTargets);++auxCalls;*s=aux[slot];if(*s)++(*s)->refs;
            if(auxCalls==interruptAux&&onInterrupt)onInterrupt();
            return auxHr[slot];}
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
        s.refs=1;*out=&s;
        if(calls==retireDescAt)s.onDesc=onRetire;
        if(calls==retireAt&&onRetire)onRetire();
        return calls==failAt?E_FAIL:S_OK;
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
    auto ensure=[&](){return pair.Ensure(&d,&lc,&ld,&rc,&rd,vp,[]{return true;});};
    assert(ensure()&&d.calls==4);
    assert(pair.eyes[0].color!=pair.eyes[1].color&&pair.eyes[0].depth!=pair.eyes[1].depth);
    assert(pair.eyes[0].color!=&lc&&pair.eyes[1].depth!=&rd);
    const auto gen=pair.generation;
    assert(ensure()&&d.calls==4&&pair.generation==gen&&d.capsCalls==1);
    pair.Reset();d.empty();assert(pair.generation!=gen&&!pair.device);
    assert(ensure()&&d.calls==8);pair.Reset();d.empty();
    for(unsigned k=1;k<=4;++k){
        IDirect3DDevice9 fail;fail.failAt=k;
        assert(!pair.Ensure(&fail,&lc,&ld,&rc,&rd,vp,[]{return true;}));fail.empty();
        assert(!pair.device&&!pair.eyes[0].color&&!pair.eyes[1].depth);
        IDirect3DDevice9 null;null.nullAt=k;
        assert(!pair.Ensure(&null,&lc,&ld,&rc,&rd,vp,[]{return true;}));null.empty();
        IDirect3DDevice9 mismatch;mismatch.mismatchAt=k;
        assert(!pair.Ensure(&mismatch,&lc,&ld,&rc,&rd,vp,[]{return true;}));mismatch.empty();
    }
    rd.desc.MultiSampleQuality=1;assert(!ensure()&&d.calls==8);
    rd=ld;vp.X=1;assert(!ensure()&&d.calls==8);vp.X=0;
    assert(!pair.Ensure(&d,&lc,&ld,&lc,&rd,vp,[]{return true;})&&d.calls==8);
    assert(ensure());IDirect3DDevice9 other;
    assert(pair.Ensure(&other,&lc,&ld,&rc,&rd,vp,[]{return true;}));d.empty();
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
    // Interrupt the exact allocator at every live descriptor, caps query,
    // creation and created-descriptor query. No retired cache may reappear.
    static R7AtomicCandidatePair* resetPair=nullptr;
    resetPair=&pair;
    auto retire=+[](){resetPair->Reset();};
    // Release may synchronously enter Reset. All four references must
    // already be detached, with a retired generation and no live proof.
    // An interrupted replacement must not allocate in the newer generation.
    static unsigned releaseCallbacks=0;
    static std::uint64_t releaseGeneration=0;
    auto duringRelease=+[](){
        ++releaseCallbacks;
        assert(resetPair->generation!=releaseGeneration&&!resetPair->device);
        assert(!resetPair->eyes[0].color&&!resetPair->eyes[0].depth&&
            !resetPair->eyes[1].color&&!resetPair->eyes[1].depth);
        assert(!resetPair->provenLiveColor[0]&&!resetPair->provenLiveDepth[1]&&
            resetPair->simultaneousTargets==0);
        resetPair->Reset();
    };
    unsigned releaseCases=0;
    for(unsigned mode=0;mode<3;++mode)
    for(unsigned phase=0;phase<=4;++phase){
        IDirect3DDevice9 oldDevice,replacement;
        assert(pair.Ensure(&oldDevice,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        pair.provenLiveColor[0]=&lc;pair.provenLiveDepth[1]=&rd;
        releaseGeneration=pair.generation;releaseCallbacks=0;
        if(phase)oldDevice.made[phase-1].onRelease=duringRelease;
        auto newLc=lc,newRc=rc;
        ++newLc.desc.Format;++newRc.desc.Format;
        if(mode==0)pair.Reset();
        else if(mode==1)
            assert(pair.Ensure(&replacement,&lc,&ld,&rc,&rd,vp,[]{return true;})==(phase==0));
        else
            assert(pair.Ensure(&oldDevice,&newLc,&ld,&newRc,&rd,vp,[]{return true;})==(phase==0));
        assert(releaseCallbacks==unsigned(phase!=0));
        for(unsigned i=0;i<4;++i)assert(oldDevice.made[i].refs==0);
        if(phase||mode==0){
            assert(!pair.device&&replacement.calls==0&&oldDevice.calls==4);
            assert(pair.Ensure(&replacement,&lc,&ld,&rc,&rd,vp,[]{return true;})&&replacement.calls==4);
        }else{
            assert(pair.device==(mode==1?&replacement:&oldDevice));
            assert(replacement.calls==(mode==1?4u:0u)&&oldDevice.calls==(mode==2?8u:4u));
        }
        pair.Reset();oldDevice.empty();replacement.empty();++releaseCases;
    }
    assert(releaseCases==15);
    IDirect3DSurface9* live[]{&lc,&ld,&rc,&rd};
    // Present does not necessarily retire the candidate generation.
    // Likewise, replacing a borrowed live attachment can leave the cache
    // generation unchanged. Stop at the first affected driver boundary.
    static bool liveOwned=true;
    static unsigned lostMode=0,readCount=0,interruptRead=0;
    auto loseOwnership=+[](){
        if(lostMode==0)liveOwned=false;
        else ++R7CandidateBoundarySerial;
    };
    auto readLive=+[](){
        if(++readCount==interruptRead){
            if(lostMode==0)liveOwned=false;
            else ++R7CandidateBoundarySerial;
        }
    };
    unsigned ownershipCases=0;
    for(lostMode=0;lostMode<2;++lostMode)
    for(unsigned phase=0;phase<=13;++phase){
        IDirect3DDevice9 allocating;
        liveOwned=true;readCount=0;interruptRead=phase<=4?phase:0;
        for(auto* surf:live)surf->onDesc=readLive;
        allocating.onRetire=loseOwnership;
        allocating.retireCaps=phase==5;
        if(phase>=6&&phase<=9)allocating.retireAt=phase-5;
        if(phase>=10)allocating.retireDescAt=phase-9;
        const auto boundary=R7CandidateBoundarySerial;
        const auto owned=[&](){return liveOwned&&boundary==R7CandidateBoundarySerial;};
        assert(pair.Ensure(&allocating,&lc,&ld,&rc,&rd,vp,owned)==(phase==0));
        for(auto* surf:live)surf->onDesc=nullptr;
        assert(readCount==(phase>=1&&phase<=4?phase:4u));
        assert(allocating.capsCalls==unsigned(phase==0||phase>=5));
        const unsigned expected=phase==0?4u:phase<=5?0u:phase<=9?phase-5:phase<=11?2u:4u;
        assert(allocating.calls==expected);
        if(phase){assert(!pair.device);allocating.empty();}
        pair.Reset();allocating.empty();++ownershipCases;
    }
    assert(ownershipCases==28);
    // A cached pair may be retired while replacing its descriptors/device.
    for(lostMode=0;lostMode<2;++lostMode)
    for(unsigned mode=0;mode<2;++mode)
    for(unsigned phase=0;phase<=4;++phase){
        IDirect3DDevice9 oldDevice,replacement;
        assert(pair.Ensure(&oldDevice,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        if(phase)oldDevice.made[phase-1].onRelease=loseOwnership;
        liveOwned=true;const auto boundary=R7CandidateBoundarySerial;
        const auto owned=[&](){return liveOwned&&boundary==R7CandidateBoundarySerial;};
        auto newLc=lc,newRc=rc;++newLc.desc.Format;++newRc.desc.Format;
        const bool ok=mode?pair.Ensure(&oldDevice,&newLc,&ld,&newRc,&rd,vp,owned):
            pair.Ensure(&replacement,&lc,&ld,&rc,&rd,vp,owned);
        assert(ok==(phase==0));
        assert(oldDevice.calls==(mode&&!phase?8u:4u));
        assert(replacement.calls==(!mode&&!phase?4u:0u));
        if(phase)assert(!pair.device);
        pair.Reset();oldDevice.empty();replacement.empty();++ownershipCases;
    }
    assert(ownershipCases==48);
    for(unsigned k=0;k<4;++k){
        IDirect3DDevice9 interruptedDevice;
        assert(pair.Ensure(&interruptedDevice,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        const auto beforeGeneration=pair.generation;
        live[k]->onDesc=retire;
        assert(!pair.Ensure(&interruptedDevice,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        live[k]->onDesc=nullptr;
        assert(pair.generation!=beforeGeneration&&!pair.device&&interruptedDevice.calls==4);
        interruptedDevice.empty();
        assert(pair.Ensure(&interruptedDevice,&lc,&ld,&rc,&rd,vp,[]{return true;})&&interruptedDevice.calls==8);
        pair.Reset();interruptedDevice.empty();
    }
    for(unsigned phase=0;phase<9;++phase){
        IDirect3DDevice9 interruptedDevice;
        interruptedDevice.onRetire=retire;
        interruptedDevice.retireCaps=phase==0;
        if(phase>=1&&phase<=4)interruptedDevice.retireAt=phase;
        if(phase>=5)interruptedDevice.retireDescAt=phase-4;
        assert(!pair.Ensure(&interruptedDevice,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        assert(!pair.device&&!pair.eyes[0].color&&!pair.eyes[1].depth);
        interruptedDevice.empty();
        const unsigned expected=phase==0?0u:phase<=4?phase:phase<=6?2u:4u;
        assert(interruptedDevice.calls==expected);
        interruptedDevice.retireCaps=false;
        interruptedDevice.retireAt=interruptedDevice.retireDescAt=0;
        assert(pair.Ensure(&interruptedDevice,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        assert(interruptedDevice.calls==expected+4);
        pair.Reset();interruptedDevice.empty();
    }
    // Caps failures must precede all allocations; valid limits are cached.
    for(unsigned limit: {0u,5u,4u}){
        IDirect3DDevice9 bad;
        bad.capsTargets=limit;bad.capsHr=limit==4?E_FAIL:S_OK;
        assert(!pair.Ensure(&bad,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        assert(bad.calls==0&&bad.capsCalls==1&&!pair.device&&pair.simultaneousTargets==0);
    }
    IDirect3DSurface9 auxSurface{};
    unsigned mrtCases=0;
    for(unsigned limit=1;limit<=4;++limit){
        IDirect3DDevice9 multi;multi.capsTargets=limit;
        assert(pair.Ensure(&multi,&lc,&ld,&rc,&rd,vp,[]{return true;}));
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
    // Every physical capture getter is a reset/present boundary. Stop
    // before the next getter and never bind or restore untouched state.
    unsigned captureCases=0;
    for(unsigned mode=0;mode<2;++mode)
    for(unsigned phase=0;phase<=7;++phase){
        IDirect3DDevice9 capture;capture.capsTargets=4;
        assert(pair.Ensure(&capture,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        capture.rt=capture.liveRt=&lc;capture.depth=capture.liveDepth=&ld;
        capture.interruptIo=phase<=4?phase:0;
        capture.interruptAux=phase>4?phase-4:0;
        capture.onInterrupt=mode?+[](){++R7CandidateBoundarySerial;}:retire;
        const auto result=R7SeedInactivePair(pair,&capture,&lc,&ld,
            [&](IDirect3DSurface9* a){return capture.bindColor(a);},
            [&](IDirect3DSurface9* a){return capture.bindDepth(a);},
            [&](){return capture.clear();});
        const auto expected=phase?(mode?R7CandidateSeedResult::Unavailable:R7CandidateSeedResult::DirtyRestore):R7CandidateSeedResult::Seeded;
        assert(result==expected);
        assert(capture.io==(phase?(phase<=4?phase:4u):21u));
        assert(capture.auxCalls==(phase?(phase<=4?0u:phase-4):3u));
        assert(capture.clearCalls==(phase?0u:2u)&&capture.liveWrites==0);
        assert(capture.rt==&lc&&capture.depth==&ld&&lc.refs==0&&ld.refs==0);
        pair.Reset();capture.empty();++captureCases;
    }
    assert(captureCases==16);
    // Even an ordinary failed getter can retire live ownership while its
    // acquired references are released. No stale live fallback or setters.
    unsigned captureCleanupCases=0;
    for(unsigned mode=0;mode<3;++mode)
    for(unsigned phase=1;phase<=5;++phase)
    for(unsigned releaseDepth=0;releaseDepth<2;++releaseDepth){
        IDirect3DDevice9 capture;capture.capsTargets=2;
        assert(pair.Ensure(&capture,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        capture.rt=capture.liveRt=&lc;capture.depth=capture.liveDepth=&ld;
        capture.ioFail=phase<=4?phase:0;
        if(phase==5)capture.auxHr[1]=E_FAIL;
        auto* released=releaseDepth?&ld:&lc;
        released->onRelease=mode==1?retire:mode==2?+[](){++R7CandidateBoundarySerial;}:nullptr;
        const auto result=R7SeedInactivePair(pair,&capture,&lc,&ld,
            [&](IDirect3DSurface9* a){return capture.bindColor(a);},
            [&](IDirect3DSurface9* a){return capture.bindDepth(a);},
            [&](){return capture.clear();});
        released->onRelease=nullptr;
        const bool retired=mode==1&&(!releaseDepth||phase>=2);
        assert(result==(retired?R7CandidateSeedResult::DirtyRestore:R7CandidateSeedResult::Unavailable));
        assert(capture.io==(phase<=4?phase:4u)&&capture.auxCalls==unsigned(phase==5));
        assert(!capture.clearCalls&&!capture.liveWrites&&lc.refs==0&&ld.refs==0);
        assert(capture.rt==&lc&&capture.depth==&ld);
        pair.Reset();capture.empty();++captureCleanupCases;
    }
    assert(captureCleanupCases==30);
    // Physical present during each restore operation still requires full
    // recovery but must not return a successful raster receipt. Retirement
    // stops before any subsequent old-generation setter. Include both
    // final saved COM releases as possible synchronous boundaries.
    unsigned restoreBoundaryCases=0;
    for(unsigned mode=0;mode<2;++mode)
    for(unsigned phase=16;phase<=23;++phase){
        IDirect3DDevice9 recovery;
        assert(pair.Ensure(&recovery,&lc,&ld,&rc,&rd,vp,[]{return true;}));
        recovery.rt=recovery.liveRt=&lc;recovery.depth=recovery.liveDepth=&ld;
        auto interrupt=mode?+[](){++R7CandidateBoundarySerial;}:retire;
        recovery.onInterrupt=interrupt;
        recovery.interruptIo=phase>=17&&phase<=21?phase:0;
        if(phase==22)ld.onRelease=interrupt;
        if(phase==23)lc.onRelease=interrupt;
        const auto result=R7SeedInactivePair(pair,&recovery,&lc,&ld,
            [&](IDirect3DSurface9* a){return recovery.bindColor(a);},
            [&](IDirect3DSurface9* a){return recovery.bindDepth(a);},
            [&](){return recovery.clear();});
        ld.onRelease=lc.onRelease=nullptr;
        const auto expected=phase==16?R7CandidateSeedResult::Seeded:
            mode?R7CandidateSeedResult::Unavailable:R7CandidateSeedResult::DirtyRestore;
        assert(result==expected&&recovery.clearCalls==2&&recovery.liveWrites==0);
        assert(recovery.io==(!mode&&phase>=17&&phase<=21?phase:21u));
        if(mode||phase==16||phase>=22)
            assert(recovery.rt==&lc&&recovery.depth==&ld&&recovery.viewport.Width==vp.Width&&recovery.scissor.left==4);
        assert(lc.refs==0&&ld.refs==0);
        pair.Reset();recovery.empty();++restoreBoundaryCases;
    }
    assert(restoreBoundaryCases==16);
    // Reset/retire during the first raster: stop before eye 2 and never
    // restore stale attachments into the new generation.
    IDirect3DDevice9 retiring;
    assert(pair.Ensure(&retiring,&lc,&ld,&rc,&rd,vp,[]{return true;}));
    retiring.rt=retiring.liveRt=&lc;retiring.depth=retiring.liveDepth=&ld;
    unsigned rasters=0;
    const auto interrupted=R7SeedInactivePair(pair,&retiring,&lc,&ld,
        [&](IDirect3DSurface9* a){return retiring.bindColor(a);},
        [&](IDirect3DSurface9* a){return retiring.bindDepth(a);},
        [&](){++rasters;pair.Reset();return S_OK;});
    assert(interrupted==R7CandidateSeedResult::DirtyRestore&&rasters==1);
    assert(retiring.io==9&&lc.refs==0&&ld.refs==0);
    retiring.empty();
    // A physical present is not a reset: stop raster, but restore saved live state.
    IDirect3DDevice9 presenting;
    assert(pair.Ensure(&presenting,&lc,&ld,&rc,&rd,vp,[]{return true;}));
    presenting.rt=presenting.liveRt=&lc;presenting.depth=presenting.liveDepth=&ld;
    rasters=0;
    assert(R7SeedInactivePair(pair,&presenting,&lc,&ld,
        [&](IDirect3DSurface9* a){return presenting.bindColor(a);},
        [&](IDirect3DSurface9* a){return presenting.bindDepth(a);},
        [&](){++rasters;++R7CandidateBoundarySerial;return S_OK;})==R7CandidateSeedResult::Unavailable);
    assert(rasters==1&&presenting.rt==&lc&&presenting.depth==&ld);
    assert(presenting.viewport.Width==vp.Width&&presenting.scissor.left==4);
    assert(lc.refs==0&&ld.refs==0);
    pair.Reset();presenting.empty();
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
assert "if(changed&&TargetIsBackBuffer())ExternalAtomicReplayEpoch=0;" in source
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
    std::uint64_t generation=1;
    IDirect3DSurface9* provenLiveColor[2]{&left,&right};
    IDirect3DSurface9* provenLiveDepth[2]{&ld,&rd};
} ExternalAtomicCandidates;
struct Stamp{unsigned count=0;void Invalidate(){++count;}} LastMainDepthClearStamp;
std::atomic<bool> StereoBaseCallbacksArmed{true};
std::uint64_t ExternalAtomicReplayEpoch=9,PresentEpoch=9,R7CandidateBoundarySerial=0;
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
        const bool escapingRead=!mode&&si>=1&&si<=8&&!eye;
        const bool invalid=active&&(protectedWrite||escapingRead||(eye&&(!mirror||replayFail)));
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
    // A successful physical call may retire or replace the pair before
    // returning, even if a new receipt uses the same numeric epoch.
    unsigned interruptions=0;
    for(unsigned fill=0;fill<2;++fill)
    for(unsigned phase=1;phase<=2;++phase)
    for(unsigned mode=0;mode<6;++mode){
        ExternalAtomicCandidates.device=&game;
        ExternalAtomicCandidates.provenLiveColor[0]=&left;
        ExternalAtomicCandidates.provenLiveColor[1]=&right;
        BackBuffer=&left;RightEyeSurface=&right;
        PresentEpoch=ExternalAtomicReplayEpoch=9;
        calls=0;
        auto write=[&](IDirect3DSurface9* a,IDirect3DSurface9* b){
            ++calls;
            if(calls==1){assert(a==(fill?nullptr:&left)&&b==&right);}
            else{assert(a==(fill?nullptr:&cl)&&b==&cr);}
            if(calls==phase){
                switch(mode){
                case 0:++ExternalAtomicCandidates.generation;break;
                case 1:++R7CandidateBoundarySerial;break;
                case 2:++PresentEpoch;ExternalAtomicReplayEpoch=PresentEpoch;break;
                case 3:RightEyeSurface=&unknown;break;
                case 4:ExternalAtomicCandidates.provenLiveColor[1]=&unknown;break;
                case 5:ExternalAtomicCandidates.provenLiveColor[0]=&unknown;break;
                }
            }
            return S_OK;
        };
        assert(R7ExecuteAtomicSurfaceWrite(&game,fill?nullptr:&left,&right,fill,write)==S_OK);
        const bool relevant=!(fill&&mode==5);
        assert(calls==(phase==1&&relevant?1u:2u));
        assert(ExternalAtomicReplayEpoch==(relevant?0u:9u));
        ++interruptions;
    }
    assert(interruptions==24);
    std::cout<<"R7_EXPLICIT_SURFACE_WRITE_PASS "<<cases+1+interruptions<<"\n";
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
# The auxiliary raster owner has its own actual-body regression fixture.
a=entry.index("// A verified auxiliary pass may preserve")
b=entry.index("// Replay one physical draw",a)
entry=entry[:a]+entry[b:]
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
    void (*onRead)()=nullptr;
    HRESULT SetPrivateData(const GUID&,const void* p,DWORD n,DWORD flags){
        ++writes;assert(n==8&&!flags);if(writeFail)return E_FAIL;
        std::memcpy(&proof,p,n);marked=true;return S_OK;
    }
    HRESULT GetPrivateData(const GUID&,void* p,DWORD* n){
        if(!marked||readFail)return E_FAIL;
        std::memcpy(p,&proof,8);*n=size;if(onRead)onRead();return S_OK;
    }
    void Release(){assert(refs);--refs;}
};
struct IDirect3DSwapChain9{
    D3DPRESENT_PARAMETERS pp{};bool fail=false;unsigned refs=0;
    HRESULT GetPresentParameters(D3DPRESENT_PARAMETERS* out){*out=pp;return fail?E_FAIL:S_OK;}
    void Release(){assert(refs);--refs;}
};
template<class T>void ReleaseCom(T*& p){if(p){p->Release();p=nullptr;}}
void R7ForgetAutomaticDepthProof() noexcept;
struct IDirect3DDevice9{
    bool game=true,chainFail=false,depthFail=false,nullChain=false,nullDepth=false,interruptDepth=false;
    UINT chains=1;IDirect3DSwapChain9 chain;IDirect3DSurface9 depth;
    UINT GetNumberOfSwapChains(){return chains;}
    HRESULT GetSwapChain(UINT i,IDirect3DSwapChain9** out){assert(!i);*out=nullChain?nullptr:&chain;if(*out)++chain.refs;return chainFail?E_FAIL:S_OK;}
    HRESULT GetDepthStencilSurface(IDirect3DSurface9** out){*out=nullDepth?nullptr:&depth;if(*out)++depth.refs;if(interruptDepth)R7ForgetAutomaticDepthProof();return depthFail?E_FAIL:S_OK;}
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
namespace Settings { bool VRExternalFerrariNativeCallbackReplacement=true,VRDirectGpuOnly=true; }
bool GameplayActive(){return true;}
bool seedAssetsReady=true;
bool R7NativeAssetsSeedReady(IDirect3DDevice9*) noexcept {return seedAssetsReady;}
enum class R7CandidateSeedResult{Unavailable,Seeded,DirtyRestore};
IDirect3DSurface9 left,right,color,rc;
IDirect3DSurface9 *TrackedDepthStencil=&left,*RightEyeDepth=&right,
    *TrackedRenderTarget=&color,*RightEyeSurface=&rc;
struct Pair{
    struct Desc{D3DFORMAT Format=3;}depthDesc;
    IDirect3DSurface9* provenLiveColor[2]{};
    IDirect3DSurface9* provenLiveDepth[2]{};
    std::uint64_t generation=1;
    unsigned allocations=0,resets=0;bool allow=true;
    void (*onEnsure)()=nullptr;
    template<class LiveCurrent>
    bool Ensure(IDirect3DDevice9*,IDirect3DSurface9*,IDirect3DSurface9*,
        IDirect3DSurface9*,IDirect3DSurface9*,const D3DVIEWPORT9&,LiveCurrent current){
        assert(current());++allocations;if(onEnsure)onEnsure();return allow&&current();
    }
    void Reset(){++resets;++generation;provenLiveColor[0]=provenLiveColor[1]=nullptr;provenLiveDepth[0]=provenLiveDepth[1]=nullptr;}
} ExternalAtomicCandidates;
std::uint64_t PresentEpoch=9,ExternalAtomicAllocationAttemptEpoch=0,ExternalAtomicReplayEpoch=0;
std::uint64_t R7CandidateBoundarySerial=0;
bool R7CandidatePresentBoundaryCovered=true;
bool R7CandidateResetBoundaryCovered=true;
unsigned R7CandidateResetInFlight=0;
bool chainCovered=true;
void (*onChain)()=nullptr;
bool R7CandidateSwapChainCovered(IDirect3DDevice9*){if(onChain)onChain();return chainCovered;}
bool FormatHasStencil(D3DFORMAT){return false;}
struct InternalPassScope{InternalPassScope(){}~InternalPassScope(){}};
struct Hook{template<class R,class... A>R stdcall(A...){return S_OK;}}
    SetRenderTargetHook,SetDepthStencilSurfaceHook,ClearHook;
unsigned rasterCalls=0;
unsigned interruptRaster=0;
R7CandidateSeedResult seedResult=R7CandidateSeedResult::Seeded;
template<class C,class D,class R>R7CandidateSeedResult R7SeedInactivePair(
    Pair&,IDirect3DDevice9*,IDirect3DSurface9*,IDirect3DSurface9*,C,D,R raster,
    unsigned=0,unsigned=2,bool=true){
    ++rasterCalls;if(seedResult==R7CandidateSeedResult::Seeded)raster();
    if(interruptRaster==1)++PresentEpoch;
    if(interruptRaster==2)ExternalAtomicCandidates.Reset();
    if(interruptRaster==3)TrackedRenderTarget=&rc;
    if(interruptRaster==4)ExternalAtomicReplayEpoch=0;
    if(interruptRaster==5){++R7CandidateBoundarySerial;ExternalAtomicReplayEpoch=0;ExternalAtomicAllocationAttemptEpoch=PresentEpoch;}
    return seedResult;
}
'''
retention_cases=r'''
int main(){
    // Same-frame clean Clear failure is retryable, unlike a physical boundary.
    {
        IDirect3DDevice9 d; D3DVIEWPORT9 vp{};
        R7MarkDepthRetention(&left,0);
        seedResult=R7CandidateSeedResult::Unavailable;
        assert(R7BeginExternalAtomicResourceTransaction(&d,vp,0,0,1,0)==R7CandidateSeedResult::Unavailable);
        assert(ExternalAtomicAllocationAttemptEpoch==0);
        seedResult=R7CandidateSeedResult::Seeded;
        assert(R7BeginExternalAtomicResourceTransaction(&d,vp,0,0,1,0)==R7CandidateSeedResult::Seeded);
        assert(R7BeginExternalAtomicResourceTransaction(&d,vp,0,0,1,0)==R7CandidateSeedResult::Unavailable);
        ++PresentEpoch;ExternalAtomicReplayEpoch=0;
        Settings::VRDirectGpuOnly=false;
        auto before=ExternalAtomicCandidates.allocations;
        assert(R7BeginExternalAtomicResourceTransaction(&d,vp,0,0,1,0)==R7CandidateSeedResult::Unavailable);
        assert(ExternalAtomicCandidates.allocations==before);
        Settings::VRDirectGpuOnly=true;
        seedAssetsReady=false;
        assert(R7BeginExternalAtomicResourceTransaction(&d,vp,0,0,1,0)==R7CandidateSeedResult::Unavailable);
        assert(ExternalAtomicCandidates.allocations==before);
        seedAssetsReady=true;
        ExternalAtomicAllocationAttemptEpoch=0;
        ExternalAtomicCandidates.allocations=0;rasterCalls=0;left.marked=false;left.writes=0;
    }

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
    // ResetEx recovery must match the old resource-owned tag, not just PP.
    for(unsigned mask=0;mask<256;++mask){
        IDirect3DDevice9 d;
        const auto previous=R7AutomaticDepthGeneration;
        if(!(mask&1))R7MarkDepthRetention(&d.depth,(mask&2)?previous+9:previous);
        R7ForgetAutomaticDepthProof();
        d.chain.pp.Flags=(mask&4)?D3DPRESENTFLAG_DISCARD_DEPTHSTENCIL:0;
        d.chain.pp.EnableAutoDepthStencil=!(mask&8);
        d.depthFail=mask&16;d.depth.writeFail=mask&32;
        d.interruptDepth=mask&64;d.depth.readFail=mask&128;
        const auto writes=d.depth.writes;
        R7RevalidateRetainedAutomaticDepth(&d,previous);
        assert(R7DepthRetentionProven(&d.depth)==(mask==0));
        assert(d.depth.writes==writes+unsigned((mask&~32u)==0));
        assert(!d.chain.refs&&!d.depth.refs);++cases;
    }
    {IDirect3DDevice9 d;d.interruptDepth=true;
     R7CaptureFreshAutomaticDepth(&d);
     assert(!R7DepthRetentionProven(&d.depth)&&!d.depth.writes&&!d.depth.refs);}
    {IDirect3DDevice9 d;R7MarkDepthRetention(&d.depth,0);
     const auto previous=R7AutomaticDepthGeneration;R7ForgetAutomaticDepthProof();
     R7RevalidateRetainedAutomaticDepth(&d,previous);
     assert(R7DepthRetentionProven(&d.depth)&&d.depth.writes==1&&d.depth.proof==0);}
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
    // Both eye identities must match the seeded receipt, not depth alone.
    for(unsigned eye=0;eye<2;++eye){
        ExternalAtomicReplayEpoch=PresentEpoch;
        assert(R7ReplayInactiveEye(&d,eye,eye?&color:&rc,eye?&right:&left,draw)==R7CandidateSeedResult::Unavailable);
        assert(draws==2&&ExternalAtomicReplayEpoch==0);
    }
    // Interrupt the production seed/replay at the physical raster boundary.
    for(unsigned mode=1;mode<=5;++mode){
        ++PresentEpoch;TrackedRenderTarget=&color;interruptRaster=0;
        assert(R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0)==R7CandidateSeedResult::Seeded);
        interruptRaster=mode;
        const auto got=R7ReplayInactiveEye(&d,0,&color,&left,draw);
        assert(got==R7CandidateSeedResult::Unavailable&&ExternalAtomicReplayEpoch==0);
        TrackedRenderTarget=&color;ExternalAtomicReplayEpoch=0;
        ++PresentEpoch;
        if(mode!=4){
            assert(R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0)==R7CandidateSeedResult::Unavailable);
            assert(ExternalAtomicReplayEpoch==0);
        }
    }
    interruptRaster=0;TrackedRenderTarget=&color;
    // Interrupt each of the three real GetPrivateData proof reads.
    // Same-epoch attachment replacement and generation retirement must
    // not lead to allocation, candidate raster or receipt publication.
    static unsigned readCount=0,readPhase=0,readMode=0;
    unsigned proofCases=0;
    for(readMode=0;readMode<6;++readMode)
    for(readPhase=0;readPhase<=3;++readPhase){
        ++PresentEpoch;ExternalAtomicReplayEpoch=0;
        TrackedRenderTarget=&color;TrackedDepthStencil=&left;
        RightEyeSurface=&rc;RightEyeDepth=&right;
        R7CandidateResetInFlight=0;readCount=0;
        left.onRead=+[](){
            if(++readCount!=readPhase)return;
            switch(readMode){
            case 0:TrackedRenderTarget=&rc;break;
            case 1:TrackedDepthStencil=&right;break;
            case 2:RightEyeDepth=&left;break;
            case 3:ExternalAtomicCandidates.Reset();break;
            case 4:++R7CandidateBoundarySerial;break;
            case 5:R7CandidateResetInFlight=1;break;
            }
        };
        const auto allocations=ExternalAtomicCandidates.allocations;
        const auto rasters=rasterCalls;
        const auto got=R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0);
        assert(got==(readPhase?R7CandidateSeedResult::Unavailable:R7CandidateSeedResult::Seeded));
        assert(readCount==(readPhase?readPhase:3u));
        assert(ExternalAtomicCandidates.allocations==allocations+unsigned(readPhase!=1));
        assert(rasterCalls==rasters+unsigned(readPhase==0||readPhase==3));
        assert(ExternalAtomicReplayEpoch==(readPhase?0u:PresentEpoch));
        ++proofCases;
    }
    assert(proofCases==24);
    left.onRead=nullptr;R7CandidateResetInFlight=0;
    TrackedRenderTarget=&color;TrackedDepthStencil=&left;RightEyeDepth=&right;
    // Both the swap-chain coverage query and allocator must respect the
    // real transaction's ownership snapshot, before any raster.
    static unsigned ownershipMode=0;
    auto interruptOwnership=+[](){
        switch(ownershipMode){
        case 1:++PresentEpoch;break;
        case 2:++R7CandidateBoundarySerial;break;
        case 3:TrackedRenderTarget=&rc;break;
        case 4:RightEyeDepth=&left;break;
        case 5:R7CandidateResetInFlight=1;break;
        }
    };
    unsigned entryOwnershipCases=0;
    for(unsigned location=0;location<2;++location)
    for(ownershipMode=0;ownershipMode<=5;++ownershipMode){
        ++PresentEpoch;ExternalAtomicReplayEpoch=0;
        TrackedRenderTarget=&color;RightEyeDepth=&right;R7CandidateResetInFlight=0;
        onChain=location?nullptr:interruptOwnership;
        ExternalAtomicCandidates.onEnsure=location?interruptOwnership:nullptr;
        const auto allocations=ExternalAtomicCandidates.allocations,rasters=rasterCalls;
        assert(R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0)==
            (ownershipMode?R7CandidateSeedResult::Unavailable:R7CandidateSeedResult::Seeded));
        assert(ExternalAtomicCandidates.allocations==allocations+unsigned(location||!ownershipMode));
        assert(rasterCalls==rasters+unsigned(!ownershipMode));
        assert(ExternalAtomicReplayEpoch==(ownershipMode?0u:PresentEpoch));
        ++entryOwnershipCases;
    }
    assert(entryOwnershipCases==12);
    onChain=nullptr;ExternalAtomicCandidates.onEnsure=nullptr;
    TrackedRenderTarget=&color;RightEyeDepth=&right;R7CandidateResetInFlight=0;
    // Dirty restore retires only the pair owned by this transaction.
    // A newer generation may have appeared before the old call unwinds.
    for(unsigned mode=0;mode<3;++mode){
        ++PresentEpoch;ExternalAtomicReplayEpoch=0;
        seedResult=mode?R7CandidateSeedResult::DirtyRestore:R7CandidateSeedResult::Seeded;
        interruptRaster=mode==2?2:0;
        const auto before=ExternalAtomicCandidates.generation;
        const auto resets=ExternalAtomicCandidates.resets;
        const auto got=R7BeginExternalAtomicResourceTransaction(&d,vp,3,0,1,0);
        assert(got==seedResult);
        assert(ExternalAtomicCandidates.generation==before+unsigned(mode!=0));
        assert(ExternalAtomicCandidates.resets==resets+unsigned(mode!=0));
        assert(ExternalAtomicReplayEpoch==(mode?0u:PresentEpoch));
    }
    interruptRaster=0;seedResult=R7CandidateSeedResult::Seeded;
    left.size=4;assert(!R7DepthRetentionProven(&left));
    left.size=8;left.readFail=true;assert(!R7DepthRetentionProven(&left));
    std::cout<<"R7_DEPTH_RETENTION_PROOF_PASS "<<cases<<" plus seed/replay and malformed tag cases\n";
}
'''
assert "R7ForgetAutomaticDepthProof();ReleaseStereoResources();" in source
r13=(Path("src/vr/d3d9/stereo_renderer_r13.cpp").read_text())
assert "R7ForgetAutomaticDepthProof();\n            ReleaseStereoResources();" in r13
assert r13.index("const auto previousDepthGeneration=R7AutomaticDepthGeneration;") < r13.index("R13ResetCommonPre(device,notification);") < r13.index("R7RevalidateRetainedAutomaticDepth(device,previousDepthGeneration);")
assert "if(notification.outermost&&SUCCEEDED(hr))R7RevalidateRetainedAutomaticDepth(device,previousDepthGeneration);" in source
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
std::uint64_t R7CandidateBoundarySerial=0,expectedSerial=0;
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
            ExternalAtomicAllocationAttemptEpoch==expectedAttempt&&PresentEpoch==9&&R7CandidateBoundarySerial==expectedSerial);
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
        expectedSerial=R7CandidateBoundarySerial+unsigned(owned);
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
reset_notification=source[source.index("thread_local unsigned R7ResetNotificationDepth=0;"):
                          source.index("void R7RetireDirectResetFrameIdentity();")]
reset_frame=source[source.index("void R7RetireDirectResetFrameIdentity()\n"):
                   source.index("struct ScreenVertex{")]
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
unsigned R7CandidateResetInFlight=0,resets=0,calls=0,r9Retires=0;
std::uint64_t proof=1;
bool allocated=true,owned=false,nested=false;
std::uint64_t& R7AutomaticDepthGeneration=proof;
void R7ForgetAutomaticDepthProof(){++proof;}
bool SUCCEEDED(HRESULT hr){return hr>=0;}
unsigned depthRecoveries=0;
void R7RevalidateRetainedAutomaticDepth(IDirect3DDevice9Ex* d,std::uint64_t previous){
    assert(d&&d->game&&previous==1&&proof==3&&R7CandidateResetInFlight==1);++depthRecoveries;
}
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
unsigned hostResets=0,framePublications=0,stereoPublications=0,renderInvalidations=0;
namespace OutRunVRRenderer {
    void NotifyGameReset(){++hostResets;}
    std::uint64_t GetBeginSceneCallCount(){return 17;}
}
namespace OutRunVR {
    constexpr int StereoDisabled=0,StereoFailureResourceUnavailable=7;
}
struct Stamp{bool valid=true;void Invalidate(){valid=false;}} LastMainDepthClearStamp;
struct Identity{int value=0;} QuestNativePairLatch,LastMainDepthClearDesc,FrameStereoMetadata;
float LastMainDepthClearZ=0;
unsigned LastMainDepthClearStencil=5,FrameStereoPoseSequence=42;
std::uint64_t LastBeginSceneCountAtPresent=3;
bool FrameHadDuplicatedDraw=true,FrameHadWorldStereo=true,FrameRightDrawFailed=true;
bool FramePoseMismatchLogged=true,FrameStereoIncomplete=false;
void InvalidateTrackedRenderStates(){++renderInvalidations;}
void PoisonFrame(int reason){assert(reason==OutRunVR::StereoFailureResourceUnavailable);FrameStereoIncomplete=true;}
void PublishStereoState(int state,bool world,unsigned pose,unsigned frame){
    assert(state==0&&!world&&!pose&&!frame);++stereoPublications;
}
void PublishRenderFrame(int state,unsigned frame,unsigned pose,int qpc,int reason,void* stereo){
    assert(state==0&&!frame&&!pose&&!qpc&&reason==7&&!stereo);
    assert(FrameStereoIncomplete&&FrameStereoPoseSequence==0&&QuestNativePairLatch.value==0);
    ++framePublications;
}
bool classic=false;
struct Hook{
    template<class R> R stdcall(IDirect3DDevice9Ex* d,D3DPRESENT_PARAMETERS* p,D3DDISPLAYMODEEX* m){
        ++calls;assert(d==expectedDevice&&p==expectedParams&&m==expectedMode);
        assert(hostResets==unsigned(owned||classic));
        assert(framePublications==unsigned(owned&&!classic));
        assert(stereoPublications==framePublications);
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
            if(nested){R7ResetNotificationScope inner;inner.Notify();PresentEpoch=1;ExternalAtomicAllocationAttemptEpoch=0;ExternalAtomicReplayEpoch=1;}
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
    for(unsigned mask=0;mask<8192;++mask){
        classic=mask&4096;
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
        R7CandidateResetInFlight=0;proof=1;depthRecoveries=0;resets=0;calls=0;r9Retires=0;transportRetires=0;baselineRetires=0;rasterRetires=0;rasterValid=true;allocated=true;lifecycleCalls=0;lifecycleResult=123;
        hostResets=0;framePublications=0;stereoPublications=0;renderInvalidations=0;
        QuestNativePairLatch={3};LastMainDepthClearStamp.valid=true;LastMainDepthClearDesc={4};
        FrameStereoMetadata={5};FrameStereoPoseSequence=42;LastBeginSceneCountAtPresent=3;
        LastMainDepthClearZ=0;LastMainDepthClearStencil=5;
        FrameHadDuplicatedDraw=true;FrameHadWorldStereo=true;FrameRightDrawFailed=true;
        FramePoseMismatchLogged=true;FrameStereoIncomplete=false;
        if(classic){
            R7ResetNotificationScope outer;outer.Notify();
            assert(R7CandidateResetExDest(expectedDevice,expectedParams,expectedMode)==result);
            outer.Notify(); // idempotent even if owner attempts to notify again
        }else assert(R7CandidateResetExDest(expectedDevice,expectedParams,expectedMode)==result);
        assert(calls==1&&R7CandidateResetInFlight==0&&R7ResetNotificationDepth==0);
        const bool direct=owned&&!classic;
        assert(depthRecoveries==unsigned(direct&&result>=0));
        assert(hostResets==unsigned(owned||classic));
        assert(framePublications==unsigned(direct)&&renderInvalidations==unsigned(direct));
        assert(FrameStereoIncomplete==direct&&FrameStereoPoseSequence==(direct?0u:42u));
        assert(QuestNativePairLatch.value==(direct?0:3)&&LastMainDepthClearStamp.valid!=direct);
        assert(FrameStereoMetadata.value==(direct?0:5)&&LastMainDepthClearDesc.value==(direct?0:4));
        assert(LastMainDepthClearZ==(direct?1.0f:0.0f)&&LastMainDepthClearStencil==(direct?0u:5u));
        assert(LastBeginSceneCountAtPresent==(direct?17u:3u));
        assert(FrameHadDuplicatedDraw!=direct&&FrameHadWorldStereo!=direct&&FrameRightDrawFailed!=direct&&FramePoseMismatchLogged!=direct);
        const bool rasterOwned=owned&&bool(R7DirectResetRasterOwner.load());
        assert(rasterRetires==(rasterOwned?2u:0u)&&rasterValid!=rasterOwned);
        const bool lifecycleOwned=owned&&bool(R7DirectResetLifecycleOwner.load());
        assert(lifecycleCalls==(lifecycleOwned?2u:0u));
        assert(lifecycleResult==(lifecycleOwned?result:123));
        assert(PresentEpoch==(owned&&nested?1u:(direct?10u:9u)));
        assert(ExternalAtomicReplayEpoch==(owned?0:initialReplay));
        assert(ExternalAtomicAllocationAttemptEpoch==(owned?PresentEpoch:0));
        assert(resets==(owned?1u:0u)&&proof==(owned?3u:1u)&&allocated==!owned);
    }
    std::cout<<"R7_DIRECT_RESETEX_BOUNDARY_PASS 8192\n";
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
    cpp.write_text(reset_ex_stub.replace('struct Hook{',reset_notification+reset_frame+'struct Hook{',1)+reset_ex+reset_ex_cases)
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
std::uint64_t R7CandidateBoundarySerial=0,expectedSerial=0;
std::uint64_t expectedReplay=0,expectedAttempt=0;
bool expectedAdditional=false;unsigned calls=0;HRESULT result=0;
IDirect3DDevice9* expectedDevice=nullptr;
IDirect3DSwapChain9* expectedChain=nullptr;
D3DPRESENT_PARAMETERS* expectedParams=nullptr;IDirect3DSwapChain9** expectedOut=nullptr;
const RECT *expectedSrc=nullptr,*expectedDst=nullptr;const RGNDATA* expectedDirty=nullptr;
HWND expectedWindow=nullptr;DWORD expectedFlags=0;
void Check(){++calls;assert(PresentEpoch==9&&ExternalAtomicReplayEpoch==expectedReplay&&
    ExternalAtomicAllocationAttemptEpoch==expectedAttempt&&R7CandidateAdditionalChainSeen==expectedAdditional&&R7CandidateBoundarySerial==expectedSerial);}
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
        expectedSerial=R7CandidateBoundarySerial+unsigned(retire);
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
        expectedSerial=R7CandidateBoundarySerial+unsigned(retire);
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
chain_gate="if(!ownershipCurrent()||!R7CandidateSwapChainCovered(device)||\n                !ownershipCurrent()||ExternalAtomicCandidates.generation!=chainGeneration)\n                return cleanDecline();"
assert chain_gate in source
assert source.index("const auto chainGeneration=ExternalAtomicCandidates.generation;") < source.index(chain_gate) < source.index("if(!ExternalAtomicCandidates.Ensure(device,lc,ld,rc,rd,viewport,ownershipCurrent))")
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

# Iter88: both classic owners hold the same notification scope through the physical call.
r13_reset=Path("src/vr/d3d9/stereo_renderer_r13.cpp").read_text()
r13_pre=r13_reset[r13_reset.index("void R13ResetCommonPre("):r13_reset.index("HRESULT __stdcall ResetDestR13(")]
r13_dest=r13_reset[r13_reset.index("HRESULT __stdcall ResetDestR13("):r13_reset.index("template <typename DrawCall>",r13_reset.index("HRESULT __stdcall ResetDestR13("))]
assert "notification.Notify();" in r13_pre and "QuestNativePairLatch = {};" in r13_pre
assert r13_dest.index("R7ResetNotificationScope notification;") < r13_dest.index("R13ResetCommonPre(device,notification);") < r13_dest.index("ResetCompatDevice(device, params, hr)")
classic_reset=source[source.index("HRESULT __stdcall ResetDest("):source.index("constexpr std::uint32_t StereoInstallPending")]
assert classic_reset.index("R7ResetNotificationScope notification;") < classic_reset.index("notification.Notify();") < classic_reset.index("ResetCompatDevice(device,params,hr)")
assert reset_ex.index("notification.Notify();") < reset_ex.index("R7RetireDirectResetFrameIdentity();") < reset_ex.rindex("CandidateResetExHook.stdcall<HRESULT>")


# Iter93: exercise the real UP input-state transaction, with a minimal
# attachment owner mock that reports retired generation as DirtyRestore.
up_start=source.index("template<class DrawCall>\n        R7CandidateSeedResult R7ReplayInactiveDraw(")
up_owner=source[up_start:source.index("// Raw R29/R30 owners",up_start)]
up_input_stub=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
using HRESULT=int;using UINT=unsigned;
constexpr HRESULT S_OK=0,E_FAIL=-1;
bool SUCCEEDED(HRESULT hr){return hr>=0;}
bool FAILED(HRESULT hr){return hr<0;}
enum class R7CandidateSeedResult {Unavailable,Seeded,DirtyRestore};
struct IDirect3DSurface9{};
struct Buffer {unsigned refs=0;void Release(){assert(refs);--refs;}};
using IDirect3DVertexBuffer9=Buffer;
using IDirect3DIndexBuffer9=Buffer;
template<class T>void ReleaseCom(T*& p){if(p){p->Release();p=nullptr;}}
struct IDirect3DDevice9;
struct Pair {std::uint64_t generation=1;IDirect3DDevice9* device=nullptr;} ExternalAtomicCandidates;
std::uint64_t R7CandidateBoundarySerial=0,ExternalAtomicReplayEpoch=9;
struct IDirect3DDevice9{
    Buffer vb,ib;
    unsigned phase=0,mode=0,streamGets=0,indexGets=0,draws=0,streamSets=0,indexSets=0;
    bool indexed=false,nullVb=false,nullIb=false;
    HRESULT event(unsigned step){
        if(phase!=step)return S_OK;
        if(mode==1){++ExternalAtomicCandidates.generation;ExternalAtomicCandidates.device=nullptr;}
        if(mode==2)++R7CandidateBoundarySerial;
        return mode==3?E_FAIL:S_OK;
    }
    HRESULT GetStreamSource(UINT stream,Buffer** b,UINT* offset,UINT* stride){
        assert(stream==0);++streamGets;*b=nullVb?nullptr:&vb;if(*b)++(*b)->refs;
        *offset=12;*stride=32;return event(1);
    }
    HRESULT GetIndices(Buffer** b){assert(indexed);++indexGets;*b=nullIb?nullptr:&ib;if(*b)++(*b)->refs;return event(2);}
    HRESULT Draw(){++draws;return event(3);}
    HRESULT SetStreamSource(UINT stream,Buffer* b,UINT offset,UINT stride){
        assert(ExternalAtomicCandidates.device==this&&stream==0);
        assert(b==(nullVb?nullptr:&vb)&&offset==(nullVb?0u:12u)&&stride==(nullVb?0u:32u));
        ++streamSets;return event(4);
    }
    HRESULT SetIndices(Buffer* b){
        assert(ExternalAtomicCandidates.device==this&&indexed&&b==(nullIb?nullptr:&ib));
        ++indexSets;return event(5);
    }
};
template<class DrawCall>R7CandidateSeedResult R7ReplayInactiveEye(IDirect3DDevice9* d,unsigned,
    IDirect3DSurface9*,IDirect3DSurface9*,DrawCall& draw){
    const auto gen=ExternalAtomicCandidates.generation,serial=R7CandidateBoundarySerial;
    const auto hr=draw();
    if(ExternalAtomicCandidates.generation!=gen||ExternalAtomicCandidates.device!=d)
        return R7CandidateSeedResult::DirtyRestore;
    if(FAILED(hr)||R7CandidateBoundarySerial!=serial)return R7CandidateSeedResult::Unavailable;
    return R7CandidateSeedResult::Seeded;
}
'''
up_input_stub += "bool R7NativeStockOnlyDraw(){return false;}\nvoid R7RecordNativeStockOmission(unsigned,R7CandidateSeedResult){}\n"
up_input_cases=r'''
int main(){
    unsigned cases=0;
    for(unsigned indexed=0;indexed<2;++indexed)
    for(unsigned nulls=0;nulls<4;++nulls)
    for(unsigned phase=0;phase<=5;++phase)
    for(unsigned mode=1;mode<=3;++mode){
        IDirect3DDevice9 d;d.indexed=indexed;d.nullVb=nulls&1;d.nullIb=nulls&2;
        d.phase=phase;d.mode=mode;
        ExternalAtomicCandidates={1,&d};R7CandidateBoundarySerial=0;ExternalAtomicReplayEpoch=9;
        auto draw=[&](){return d.Draw();};
        const auto result=R7ReplayInactiveDraw(&d,0,nullptr,nullptr,draw,true,indexed);
        const bool reached=phase!=0&&(indexed||(phase!=2&&phase!=5));
        const bool captureAbort=reached&&phase<=2;
        const bool reset=reached&&mode==1;
        const bool drawExpected=!captureAbort;
        const bool streamExpected=drawExpected&&!(reset&&phase==3);
        const bool indexExpected=streamExpected&&indexed&&!(reset&&phase==4);
        assert(d.streamGets==1&&d.indexGets==unsigned(indexed&&!(captureAbort&&phase==1)));
        assert(d.draws==unsigned(drawExpected)&&d.streamSets==unsigned(streamExpected)&&d.indexSets==unsigned(indexExpected));
        const bool dirty=reset||(reached&&mode==3&&phase>=4);
        const auto expected=dirty?R7CandidateSeedResult::DirtyRestore:
            reached?R7CandidateSeedResult::Unavailable:R7CandidateSeedResult::Seeded;
        assert(result==expected&&ExternalAtomicReplayEpoch==(reached?0u:9u));
        assert(d.vb.refs==0&&d.ib.refs==0);
        ++cases;
    }
    // Non-UP draws do not capture or restore input state.
    IDirect3DDevice9 d;ExternalAtomicCandidates={1,&d};ExternalAtomicReplayEpoch=9;
    auto draw=[&](){return d.Draw();};
    assert(R7ReplayInactiveDraw(&d,0,nullptr,nullptr,draw,false,false)==R7CandidateSeedResult::Seeded);
    assert(d.draws==1&&!d.streamGets&&!d.indexGets&&!d.streamSets&&!d.indexSets);
    std::cout<<"R7_UP_GENERATION_RESTORE_PASS "<<cases+1<<"\n";
}
'''
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"up_generation.cpp"
    exe=Path(temp)/"up_generation"
    cpp.write_text(up_input_stub+up_owner+up_input_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)


# Iter106: actual initial RIGHT bind/clear and shared restore transaction.
init_tx_begin=source.index("bool R7InitializeRightAttachments(")
init_tx=source[init_tx_begin:source.index("// Capture real LEFT attachments",init_tx_begin)]
restore_begin=source.index("bool RestoreRightPassState(")
restore_tx=source[restore_begin:source.index("bool TryBootstrapRightDepthFromRecentClear(",restore_begin)]
assert "R7InitializeRightAttachments(device,RightEyeSurface,RightEyeDepth," in init
assert init.index("if(!R7InitializeRightAttachments(") < init.index("if(dirty)") < init.index("StereoResourcesReady=true")
assert "if(R7EyeStateGeneration()==generation)ReleaseStereoResources();" in init
assert "NoteRestoreFailure(\"R7 initial RIGHT attachment transaction\");" in init
init_tx_stub=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
using HRESULT=int;using DWORD=unsigned;
constexpr HRESULT S_OK=0,E_FAIL=-1;
constexpr DWORD D3DCLEAR_TARGET=1,D3DCLEAR_ZBUFFER=2,D3DCLEAR_STENCIL=4;
#define D3DCOLOR_XRGB(r,g,b) 0u
bool SUCCEEDED(HRESULT hr){return hr>=0;} bool FAILED(HRESULT hr){return hr<0;}
std::uint64_t generation=1;
std::uint64_t R7EyeStateGeneration(){return generation;}
struct D3DRECT{};struct D3DVIEWPORT9{unsigned Width;};struct D3DSURFACE_DESC{unsigned Format;};
unsigned calls=0,failAt=0,retireAt=0,scope=0,clearCount=0,flagsSeen=0,restoreMask=0;
HRESULT step(){assert(scope);++calls;if(calls==retireAt)++generation;return calls==failAt?E_FAIL:S_OK;}
struct IDirect3DSurface9{unsigned format=1;HRESULT GetDesc(D3DSURFACE_DESC* d){auto hr=step();d->Format=format;return hr;}};
struct IDirect3DDevice9{
 IDirect3DSurface9 *rt=nullptr,*depth=nullptr,*savedRt=nullptr,*savedDepth=nullptr;
 D3DVIEWPORT9 view{800};
 HRESULT SetDepthStencilSurface(IDirect3DSurface9* s){if(s==savedDepth)restoreMask|=2;auto hr=step();if(SUCCEEDED(hr))depth=s;return hr;}
 HRESULT SetViewport(const D3DVIEWPORT9* v){if(v->Width==800)restoreMask|=4;auto hr=step();if(SUCCEEDED(hr))view=*v;return hr;}
};
struct InternalPassScope{InternalPassScope(){++scope;}~InternalPassScope(){--scope;}};
bool FormatHasStencil(unsigned f){return f==1;}
struct RtHook{template<class H>H stdcall(IDirect3DDevice9* d,unsigned,IDirect3DSurface9* s){if(s==d->savedRt)restoreMask|=1;auto hr=step();if(SUCCEEDED(hr))d->rt=s;return hr;}} SetRenderTargetHook;
struct DsHook{bool enabled=true;explicit operator bool()const{return enabled;}template<class H>H stdcall(IDirect3DDevice9* d,IDirect3DSurface9* s){return d->SetDepthStencilSurface(s);}} SetDepthStencilSurfaceHook;
struct ClHook{template<class H>H stdcall(IDirect3DDevice9*,unsigned,const D3DRECT*,DWORD flags,DWORD,float,unsigned){++clearCount;flagsSeen=flags;return step();}} ClearHook;
struct Candidate{std::uint64_t& generation;} ExternalAtomicCandidates{generation};
bool RestoreWvpOneRegisterAtATime(IDirect3DDevice9*,const float*){assert(false);return false;}
'''
init_tx_cases=r'''
int main(){
 unsigned cases=0;
 for(bool depth:{false,true})for(bool stencil:{false,true})for(bool hook:{false,true}){
  const unsigned clearAt=depth?5:4,total=clearAt+3;
  for(unsigned phase=0;phase<=total;++phase)for(unsigned mode=0;mode<3;++mode){
   IDirect3DSurface9 left,z,right,rz;rz.format=stencil?1:2;
   IDirect3DDevice9 d;d.rt=d.savedRt=&left;d.depth=d.savedDepth=&z;
   generation=1;calls=clearCount=flagsSeen=restoreMask=0;failAt=mode==1||mode==2?phase:0;retireAt=mode==0||mode==2?phase:0;SetDepthStencilSurfaceHook.enabled=hook;
   bool dirty=false;const bool ok=R7InitializeRightAttachments(&d,&right,depth?&rz:nullptr,&left,&z,{1920},{800},1,dirty);
   const bool fault=phase!=0;const bool retired=fault&&mode!=1;
   assert(ok==!fault);assert(dirty==(retired||(fault&&phase>clearAt)));
   if(retired)assert(calls==phase);else if(fault&&phase<=clearAt)assert(calls==phase+3);else assert(calls==total);
   if(!dirty){assert(d.rt==&left&&d.depth==&z&&d.view.Width==800&&restoreMask==7);}
   if(!retired)assert(restoreMask==7);
   assert(clearCount==unsigned(!fault||phase>=clearAt));
   if(clearCount)assert(flagsSeen==(D3DCLEAR_TARGET|(depth?D3DCLEAR_ZBUFFER:0u)|(depth&&stencil?D3DCLEAR_STENCIL:0u)));
   assert(scope==0);++cases;
  }
 }
 bool dirty=false;IDirect3DDevice9 d;calls=0;generation=2;assert(!R7InitializeRightAttachments(&d,nullptr,nullptr,nullptr,nullptr,{1920},{800},1,dirty)&&dirty&&!calls);
 std::cout<<"R7_INIT_ATTACHMENT_TRANSACTION_PASS "<<cases+1<<'\n';
}
'''
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/"init_attachment_transaction.cpp"
    exe=Path(temp)/"init_attachment_transaction"
    cpp.write_text(init_tx_stub+restore_tx+init_tx+init_tx_cases)
    subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(cpp),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
