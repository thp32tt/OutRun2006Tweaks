#!/usr/bin/env python3
"""Compile the actual R7 auxiliary raster admission with fake D3D attachments."""
from pathlib import Path
import subprocess, tempfile
s=Path("src/vr/d3d9/stereo_renderer_r7.inc").read_text()
a=s.index("bool R7CandidateDisjointOffscreenRaster(IDirect3DDevice9* device) noexcept\n")
b=s.index("// Replay one physical draw",a)
stub=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
using UINT=unsigned;using HRESULT=int;
constexpr HRESULT S_OK=0,D3DERR_NOTFOUND=-1,E_FAIL=-2;
bool SUCCEEDED(HRESULT h){return h>=0;}
struct IDirect3DSurface9{int refs=0;};
IDirect3DSurface9 lc,rc,ld,rd,pc[2],pd[2],aux,auxDepth;
std::uint64_t PresentEpoch=3,ExternalAtomicReplayEpoch=3,R7CandidateBoundarySerial=0;
bool InternalStereoPass=false,R7CandidateResetInFlight=false,R7VehicleStageInFlight=false,mainTarget=false,mrt=false;
struct Key{std::uint64_t present=0;} R7StagedVehicle;
namespace OutRunVR::DinoSidecar{void* ActiveNativeVehicleStockReplay=nullptr;}
struct IDirect3DDevice9{
 IDirect3DSurface9* rt[4]{&aux,nullptr,nullptr,nullptr};IDirect3DSurface9* depth=&auxDepth;
 unsigned calls=0,retireAt=0,failAt=0;
 HRESULT get(IDirect3DSurface9* p,IDirect3DSurface9** out){
  ++calls;if(calls==retireAt)++R7CandidateBoundarySerial;
  *out=nullptr;if(calls==failAt)return E_FAIL;
  if(!p)return D3DERR_NOTFOUND;
  *out=p;++p->refs;return S_OK;
 }
 HRESULT GetRenderTarget(UINT i,IDirect3DSurface9** out){return get(rt[i],out);}
 HRESULT GetDepthStencilSurface(IDirect3DSurface9** out){return get(depth,out);}
} game;
struct Pair{struct Eye{IDirect3DSurface9* color;IDirect3DSurface9* depth;};
 Eye eyes[2]{{&pc[0],&pd[0]},{&pc[1],&pd[1]}};
 IDirect3DSurface9* provenLiveColor[2]{&lc,&rc},*provenLiveDepth[2]{&ld,&rd};
 IDirect3DDevice9* device=&game;unsigned simultaneousTargets=4;std::uint64_t generation=1;
} ExternalAtomicCandidates;
IDirect3DSurface9* TrackedRenderTarget=&aux,*TrackedDepthStencil=&auxDepth;
bool TargetIsBackBuffer(){return mainTarget;}
bool AnyAuxRenderTargetActive(){return mrt;}
void ReleaseCom(IDirect3DSurface9*& p){if(p){assert(p->refs>0);--p->refs;p=nullptr;}}
'''
cases=r'''
int main(){
 assert(R7CandidateDisjointOffscreenRaster(&game));assert(game.calls==5);
 for(auto* surface:{&lc,&rc,&ld,&rd,&pc[0],&pc[1],&pd[0],&pd[1]}){
  game.rt[0]=TrackedRenderTarget=surface;assert(!R7CandidateDisjointOffscreenRaster(&game));
  game.rt[0]=TrackedRenderTarget=&aux;
  game.depth=TrackedDepthStencil=surface;assert(!R7CandidateDisjointOffscreenRaster(&game));
 }
 game.depth=TrackedDepthStencil=&auxDepth;
 for(unsigned i=1;i<4;++i){game.rt[i]=&lc;assert(!R7CandidateDisjointOffscreenRaster(&game));game.rt[i]=nullptr;}
 for(unsigned i=1;i<=5;++i){
  game.calls=0;game.retireAt=i;assert(!R7CandidateDisjointOffscreenRaster(&game));
  game.calls=0;game.retireAt=0;game.failAt=i;assert(!R7CandidateDisjointOffscreenRaster(&game));game.failAt=0;
 }
 R7StagedVehicle.present=PresentEpoch;assert(!R7CandidateDisjointOffscreenRaster(&game));R7StagedVehicle.present=0;
 game.depth=TrackedDepthStencil=nullptr;assert(R7CandidateDisjointOffscreenRaster(&game));
 assert(!lc.refs&&!rc.refs&&!ld.refs&&!rd.refs&&!aux.refs&&!auxDepth.refs);
 std::cout<<"R7_DISJOINT_OFFSCREEN_PASS\n";
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/"probe.cpp").write_text(stub+s[a:b]+cases)
 subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror",str(p/"probe.cpp"),"-o",str(p/"probe")],check=True)
 subprocess.run([str(p/"probe")],check=True)
