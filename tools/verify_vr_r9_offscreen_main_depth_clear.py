#!/usr/bin/env python3
"""R9 offscreen shared-main-depth Clear path + destructive source controls.

Scope: exact native HRESULT, one original Clear, strict COM-depth identity,
and no stereo mutation for foreign/color-only/failed operations.
Quest3/OpenXR pixels are not simulated here.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cpp = (root/"src/vr/d3d9/stereo_renderer.cpp").read_text(encoding="utf-8")
header = (root/"src/vr/game/offscreen_depth_clear_lineage.hpp").read_text(encoding="utf-8")
workflow = (root/".github/workflows/vr-dx9ex-active.yml").read_text(encoding="utf-8")
start = cpp.index("HRESULT __stdcall ClearDestR9(")
end = cpp.index("template <typename ActualDraw, typename LegacyDraw>", start)
clear = cpp[start:end]

def safe_clear(s: str) -> bool:
    markers = (
        "if (!wanted || !mainTarget)",
        "const HRESULT originalHr = R9ClearCallbackHook.stdcall<HRESULT>(",
        "const auto lineage = OutRunVR::OffscreenDepthClearLineage::Decide(",
        "SUCCEEDED(originalHr), wanted, !mainTarget, R9StereoSeeded,",
        "R9CurrentDepthCanMirror() && TrackedDepthStencil,",
        "(flags & D3DCLEAR_ZBUFFER) != 0,",
        "(flags & D3DCLEAR_STENCIL) != 0,",
        "FormatHasStencil(R9MainDepthDesc.Format),",
        "RightDepthSynchronized, RightStencilSynchronized);",
        "if (lineage.mainContentChanged)",
        "if (lineage.invalidateDepth)",
        "RightDepthSynchronized = false;",
        "if (lineage.invalidateStencil)",
        "RightStencilSynchronized = false;",
        "++R9MainDepthContentSerial;",
        "return originalHr;",
    )
    pos = [s.find(x) for x in markers]
    return min(pos) >= 0 and pos == sorted(pos) and s.count(
        "const HRESULT originalHr = R9ClearCallbackHook.stdcall<HRESULT>(") == 1

assert '#include "vr/game/offscreen_depth_clear_lineage.hpp"' in cpp
assert safe_clear(clear)
for name, old, bad in (
    ("ignore original HRESULT", "SUCCEEDED(originalHr), wanted", "true, wanted"),
    ("ignore stereo mode", "SUCCEEDED(originalHr), wanted", "SUCCEEDED(originalHr), true"),
    ("ignore exact main COM resource", "R9CurrentDepthCanMirror() && TrackedDepthStencil,", "true,"),
    ("lose depth clear flag", "(flags & D3DCLEAR_ZBUFFER) != 0,", "true,"),
    ("lose stencil clear flag", "(flags & D3DCLEAR_STENCIL) != 0,", "true,"),
    ("lose right-depth invalidation", "RightDepthSynchronized = false;", "/* depth unchanged */"),
    ("lose right-stencil invalidation", "RightStencilSynchronized = false;", "/* stencil unchanged */"),
    ("advance no content serial", "++R9MainDepthContentSerial;", "/* missing serial */"),
    ("lose original HRESULT", "return originalHr;", "return S_OK;"),
):
    assert old in clear, name+" test setup"
    assert not safe_clear(clear.replace(old,bad,1)), name
for s in (
    "originalSucceeded && stereoWanted &&",
    "offscreenTarget && mainStereoSeeded && exactMainDepthBound",
    "validOwner && clearDepth",
    "validOwner && clearStencil && mainHasStencil",
    "depthWritten || stencilWritten",
    "depthWritten && rightDepthSynchronized",
    "stencilWritten && rightStencilSynchronized",
):
    assert s in header, "C++ pure policy contract lost: "+s
assert header.count("static_assert(") >= 12
assert "'tools/verify_vr_r9_offscreen_main_depth_clear.py'" in workflow
assert "'src/vr/game/offscreen_depth_clear_lineage.hpp'" in workflow
print("PASS R9 shared-main offscreen Clear: physical-success-only depth/stencil lineage, 12 C++ constexpr cases, 9 destructive controls; HMD UNTESTED")
