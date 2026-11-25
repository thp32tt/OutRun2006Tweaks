#!/usr/bin/env python3
"""Compile the actual R30 descriptor/registry path against fake D3D buffers."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text()
lookup = src[src.index("        struct R30ShadowLookupCache"):
             src.index("        std::uint64_t R30ShadowWrites")]
body = src[src.index("        template <typename Buffer>\n        R30ShadowPtr R30FindShadow("):
           src.index("        void R30BeginObservedLock(")]
release_vb = src[src.index("        ULONG __stdcall R30VertexBufferReleaseDest("):
                 src.index("        HRESULT __stdcall R30IndexBufferLockDest(")]
release_ib = src[src.index("        ULONG __stdcall R30IndexBufferReleaseDest("):
                 src.index("        bool R30EnsureVertexBufferHooks(")]
prefix = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <iostream>
using UINT=unsigned; using DWORD=unsigned; using ULONG=unsigned;
#define __stdcall
#define FAILED(hr) ((hr)<0)
constexpr unsigned D3DFVF_POSITION_MASK=14, D3DFVF_XYZRHW=4;
constexpr unsigned D3DFMT_INDEX16=101, D3DFMT_INDEX32=102;
constexpr unsigned R30MaxShadowBytes=1024;
struct D3DVERTEXBUFFER_DESC { unsigned Size=32, Usage=0, Pool=0, FVF=2; };
struct D3DINDEXBUFFER_DESC { unsigned Size=32, Usage=0, Pool=0, Format=0; };
template<class D> struct Buffer {
    D desc{}; unsigned queries=0, refs=0; int hr=0;
    int GetDesc(D* out) { ++queries; if(hr>=0) *out=desc; return hr; }
};
using IDirect3DVertexBuffer9=Buffer<D3DVERTEXBUFFER_DESC>;
using IDirect3DIndexBuffer9=Buffer<D3DINDEXBUFFER_DESC>;
struct R30BufferShadow { unsigned size=0, usage=0, pool=0, indexFormat=0; };
using R30ShadowPtr=std::shared_ptr<R30BufferShadow>;
std::mutex R30ShadowRegistryMutex;
std::unordered_map<IDirect3DVertexBuffer9*,R30ShadowPtr> R30VertexShadows;
std::unordered_map<IDirect3DIndexBuffer9*,R30ShadowPtr> R30IndexShadows;
std::atomic<std::uint64_t> R30ShadowRegistryEpoch{1};
std::atomic<bool> R30VertexBufferHooksReady{true}, R30IndexBufferHooksReady{true};
struct Hook { template<class R,class B> R stdcall(B* b) { return b->refs; } };
Hook R30VertexBufferReleaseHook, R30IndexBufferReleaseHook;
'''
suffix = r'''
template<class B, class Ensure, class Find, class Release, class Eligible>
void exercise(Ensure ensure, Find find, Release release, Eligible eligible,
              std::atomic<bool>& ready) {
    B b{};
    assert(!ensure(&b));
    for(unsigned i=0;i<64;++i) assert(!ensure(&b));
    assert(b.queries==1 && !find(&b)); // rejected, not an allocated shadow
    b.refs=1; assert(release(&b)==1);
    assert(!ensure(&b) && b.queries==1);
    b.refs=0; assert(release(&b)==0);
    eligible(b);
    auto valid=ensure(&b);
    assert(valid && b.queries==2 && ensure(&b)==valid);
    assert(find(&b)==valid && b.queries==2);
    release(&b);
    B transient{}; eligible(transient); transient.hr=-1;
    assert(!ensure(&transient) && !ensure(&transient) && transient.queries==2);
    transient.hr=0; assert(ensure(&transient) && transient.queries==3);
    release(&transient);
    B partial{}; ready=false;
    assert(!ensure(&partial) && !ensure(&partial) && partial.queries==2);
    ready=true;
    assert(!ensure(&partial) && !ensure(&partial) && partial.queries==3);
    // Mirror rollback's map clearing and epoch invalidation. Next descriptor
    // at the same address must not inherit an old negative cache result.
    { std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);
      R30VertexShadows.clear(); R30IndexShadows.clear();
      R30ShadowRegistryEpoch.fetch_add(1,std::memory_order_release); }
    eligible(partial); assert(ensure(&partial) && partial.queries==4);
    release(&partial);
}
int main() {
    exercise<IDirect3DVertexBuffer9>(R30EnsureVertexShadow,R30FindVertexShadow,
        R30VertexBufferReleaseDest,[](auto& b){b.desc.FVF=0;},R30VertexBufferHooksReady);
    exercise<IDirect3DIndexBuffer9>(R30EnsureIndexShadow,R30FindIndexShadow,
        R30IndexBufferReleaseDest,[](auto& b){b.desc.Format=D3DFMT_INDEX16;},R30IndexBufferHooksReady);
    IDirect3DVertexBuffer9 vb{}; vb.desc.FVF=D3DFVF_XYZRHW;
    vb.desc.Size=R30MaxShadowBytes+1;
    assert(!R30EnsureVertexShadow(&vb) && !R30EnsureVertexShadow(&vb) && vb.queries==1);
    R30VertexBufferReleaseDest(&vb);
    vb.desc.Size=R30MaxShadowBytes; assert(R30EnsureVertexShadow(&vb));
    R30VertexBufferReleaseDest(&vb);
    IDirect3DIndexBuffer9 ib{}; ib.desc.Format=D3DFMT_INDEX32; ib.desc.Size=0;
    assert(!R30EnsureIndexShadow(&ib) && !R30EnsureIndexShadow(&ib) && ib.queries==1);
    R30IndexBufferReleaseDest(&ib);
    ib.desc.Size=32; assert(R30EnsureIndexShadow(&ib));
    R30IndexBufferReleaseDest(&ib);
    std::cout<<"R30_SHADOW_DESCRIPTOR_CACHE_PASS\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p / "probe.cpp").write_text(prefix + lookup + body + release_vb + release_ib + suffix)
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic", str(p / "probe.cpp"),
                    "-o", str(p / "probe")], check=True)
    subprocess.run([str(p / "probe")], check=True)
