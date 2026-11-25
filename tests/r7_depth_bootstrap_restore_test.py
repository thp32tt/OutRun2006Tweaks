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
struct IDirect3DSurface9 {
    D3DSURFACE_DESC desc{};
    HRESULT GetDesc(D3DSURFACE_DESC* d){*d=desc;return 0;}
};
struct D3DVIEWPORT9 { unsigned X=0,Y=0,Width=100,Height=100; };
unsigned step=0,failAt=0,clearCalls=0,restoreCalls=0,notes=0;
HRESULT call(){return ++step==failAt?E_FAIL:0;}
struct IDirect3DDevice9 {
    HRESULT GetViewport(D3DVIEWPORT9* v){*v={};return 0;}
    HRESULT SetViewport(const D3DVIEWPORT9*){return call();}
    HRESULT SetDepthStencilSurface(IDirect3DSurface9*){return call();}
};
struct Hook {
    unsigned kind;
    explicit operator bool()const{return true;}
    template<class R,class... Args> R stdcall(Args...){
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
        const bool ok=TryBootstrapRightDepthFromRecentClear(&dev,&dirty);
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
