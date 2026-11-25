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
assert clear.index("if(!restoreOk)") < clear.index("R7BeginExternalAtomicResourceTransaction(device,savedViewport,flags,color,z,stencil)")
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
