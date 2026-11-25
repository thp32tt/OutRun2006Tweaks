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
prefix = r'''
#include "depth_clear_replay_stamp.hpp"
#include <cassert>
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
struct IDirect3DDevice9 { bool game; };
bool InternalStereoPass = false;
std::uint64_t PresentEpoch = 77;
std::uint64_t ExternalAtomicReplayEpoch=0;
OutRunVR::DepthClearReplayStamp LastMainDepthClearStamp{};
DWORD writes = 0, expectedAtCall = 0;
unsigned reads = 0, calls = 0, expectedHook = 0;
HRESULT injected = 0;
bool IsGameDevice(IDirect3DDevice9* d) { return d && d->game; }
bool LeftDrawMayWriteDepth(IDirect3DDevice9*) { ++reads; return writes & 2; }
bool LeftDrawMayWriteStencil(IDirect3DDevice9*) { ++reads; return writes & 4; }
struct Hook {
    unsigned id;
    template<class R, class... Args> R stdcall(Args...) {
        assert(id == expectedHook);
        assert(LastMainDepthClearStamp.flags == expectedAtCall);
        ++calls;
        return injected;
    }
};
Hook DrawPrimitiveHook{0}, DrawIndexedPrimitiveHook{1},
     DrawPrimitiveUPHook{2}, DrawIndexedPrimitiveUPHook{3};
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
    std::cout << "R29_RAW_DEPTH_RECEIPT_PASS " << cases << "\\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p / "probe.cpp").write_text(prefix + helper + raw + suffix)
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic", "-I", str(root / "src/vr/d3d9"),
                    str(p / "probe.cpp"), "-o", str(p / "probe")], check=True)
    subprocess.run([str(p / "probe")], check=True)
