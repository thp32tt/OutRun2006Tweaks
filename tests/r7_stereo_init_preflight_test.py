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
