#!/usr/bin/env python3
"""Deterministic guards for the staged VR R-series flattening."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def text(rel: str) -> str:
    p = ROOT / rel
    if not p.exists():
        errors.append(f"missing required refactor file: {rel}")
        return ""
    return p.read_text(encoding="utf-8")

r22 = text("src/vr/d3d9/stereo_renderer_r22.cpp")
r23 = text("src/vr/d3d9/stereo_renderer_r23.cpp")
r9 = text("src/vr/d3d9/stereo_renderer.cpp")
r13 = text("src/vr/d3d9/stereo_renderer_r13.cpp")
r20 = text("src/vr/d3d9/stereo_renderer_r20.cpp")
r21 = text("src/vr/d3d9/stereo_renderer_r21.cpp")
r29 = text("src/vr/d3d9/stereo_renderer_r29.cpp")
r30 = text("src/vr/d3d9/stereo_renderer_r30.cpp")
r30_safe = text("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
r26 = text("src/vr/d3d9/stereo_renderer_r26.cpp")
r31 = text("src/vr/d3d9/stereo_renderer_r31.cpp")
r32 = text("src/vr/d3d9/stereo_renderer_r32.cpp")
r33 = text("src/vr/d3d9/stereo_renderer_r33.cpp")
r34_path = ROOT / "src/vr/d3d9/stereo_renderer_r34.cpp"
if r34_path.exists():
    errors.append("retired R34 source shim reappeared")
cmake = text("CMakeLists.txt")
cmake_toml = text("cmake.toml")
renderer_r29 = text("src/vr/game/outrun_renderer_r29.cpp")
draw_class = text("src/vr/render/draw_class.hpp")
raster = text("src/vr/state/d3d9_raster_state.hpp")
state_block_tracker = text("src/vr/state/state_block_tracker.hpp")
state_block_recovery = text("src/vr/state/state_block_recovery.hpp")
state_block_events = text("src/vr/state/state_block_events.hpp")
vr_openxr_workflow = text(".github/workflows/vr-openxr.yml")
r23_runtime_hardening = text("vrhost/src/runtime/r23_runtime_hardening.hpp")
sbs_capture_override = text("vrhost/src/runtime/sbs_capture_override.hpp")
overlay_hooks = text("src/overlay/hooks_overlay.cpp")
render_semantics = text("src/vr/game/render_semantics.hpp")
r30_support_api = text("src/vr/core/r30_support_api.hpp")
r30_safe = text("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
text("tools/verify_vr_hook_graph.py")

# R84 R32 lower target pointer and installed-device ownership preflight.
# Returning the wrong target replaces a physical hook and is a hard fail.
# The installed device is borrowed via the original atomic acquire load.
def r32_target_address_owner_ok(api, lower, upper):
    contracts = (
        ("ResetTarget", "ResetDestR22"),
        ("PresentTarget", "PresentDestR13"),
        ("DirectTransportTarget", "ResolveDirectTransportR13"),
        ("SetRenderStateTarget", "SetRenderStateDestR29"),
    )
    for suffix, original in contracts:
        if ("void* R30Support" + suffix + "() noexcept;") not in api:
            return False
        if not re.search(
            r"void\* R30Support" + suffix +
            r"\(\) noexcept\s*\{\s*return reinterpret_cast<void\*>\(&" +
            original + r"\);\s*\}", lower):
            return False
        if ("void* R32Review" + suffix +
            "() noexcept{return R30Support" + suffix + "();}") not in upper:
            return False
    return all((
        "IDirect3DDevice9* R30SupportInstalledDevice() noexcept;" in api,
        bool(re.search(
            r"IDirect3DDevice9\* R30SupportInstalledDevice\(\) noexcept"
            r"\s*\{\s*return StereoInstalledDevice.load\("
            r"std::memory_order_acquire\);\s*\}", lower)),
        "IDirect3DDevice9* R32ReviewInstalledDevice() noexcept{return R30SupportInstalledDevice();}" in upper,
    ))

if not r32_target_address_owner_ok(r30_support_api, r30, r32):
    errors.append("R32 hook targets or installed-device original acquire owner lost")
for label, edited_lower, edited_upper in (
    ("Reset target replaced with present", r30.replace(
        "return reinterpret_cast<void*>(&ResetDestR22);",
        "return reinterpret_cast<void*>(&PresentDestR13);", 1), r32),
    ("Present target replaced with Reset", r30.replace(
        "return reinterpret_cast<void*>(&PresentDestR13);",
        "return reinterpret_cast<void*>(&ResetDestR22);", 1), r32),
    ("Direct transport target replaced", r30.replace(
        "return reinterpret_cast<void*>(&ResolveDirectTransportR13);",
        "return reinterpret_cast<void*>(&PresentDestR13);", 1), r32),
    ("render state target replaced", r30.replace(
        "return reinterpret_cast<void*>(&SetRenderStateDestR29);",
        "return reinterpret_cast<void*>(&ResetDestR22);", 1), r32),
    ("installed device relaxed load", r30.replace(
        "return StereoInstalledDevice.load(std::memory_order_acquire);",
        "return StereoInstalledDevice.load(std::memory_order_relaxed);", 1), r32),
    ("installed device fabricated null", r30.replace(
        "return StereoInstalledDevice.load(std::memory_order_acquire);",
        "return nullptr;", 1), r32),
    ("R32 bypasses Reset owner", r30, r32.replace(
        "R30SupportResetTarget();", "reinterpret_cast<void*>(&ResetDestR22);", 1)),
    ("R32 bypasses Present owner", r30, r32.replace(
        "R30SupportPresentTarget();", "reinterpret_cast<void*>(&PresentDestR13);", 1)),
    ("R32 bypasses transport owner", r30, r32.replace(
        "R30SupportDirectTransportTarget();", "reinterpret_cast<void*>(&ResolveDirectTransportR13);", 1)),
    ("R32 bypasses renderstate owner", r30, r32.replace(
        "R30SupportSetRenderStateTarget();", "reinterpret_cast<void*>(&SetRenderStateDestR29);", 1)),
    ("R32 bypasses device owner", r30, r32.replace(
        "R30SupportInstalledDevice();",
        "StereoInstalledDevice.load(std::memory_order_acquire);", 1)),
):
    if edited_lower == r30 and edited_upper == r32:
        errors.append("R84 lower target negative mutation not applied: " + label)
    elif r32_target_address_owner_ok(r30_support_api, edited_lower, edited_upper):
        errors.append("R84 lower target negative mutation survived: " + label)

# R84: R32 no longer directly mutates R9 frame stereo accounting.
# The old source wrote the four world flags/counters before latching pose only
# when 0, the HUD path increments its own counter, and right failure is sticky.
# Preserve that exact order/condition, with no new WVP, shader or HUD policy.
def r32_frame_duplicate_lower_owner_ok(api, r30_impl, r32_impl):
    expected_world = """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
"""
    expected_hud = """    void R30SupportRecordHudStereoDuplicate() noexcept
    {
        FrameHadDuplicatedDraw = true;
        ++DuplicatedDraws;
        ++NonWorldDuplicatedDraws;
    }
"""
    expected_fail = """    void R30SupportMarkFrameRightDrawFailed() noexcept
    {
        FrameRightDrawFailed = true;
    }
"""
    return all((
        "void R30SupportRecordWorldStereoDuplicate(" in api,
        "const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept;" in api,
        "void R30SupportRecordHudStereoDuplicate() noexcept;" in api,
        "void R30SupportMarkFrameRightDrawFailed() noexcept;" in api,
        expected_world in r30_impl,
        expected_hud in r30_impl,
        expected_fail in r30_impl,
        """    void R32ReviewRecordWorldStereoDuplicate(std::uint32_t p, const OutRunVRRenderer::LatchedStereoFrame& s) noexcept
    {
        R30SupportRecordWorldStereoDuplicate(p, s);
    }
    void R32ReviewRecordHudStereoDuplicate() noexcept { R30SupportRecordHudStereoDuplicate(); }
    void R32ReviewMarkFrameRightDrawFailed() noexcept { R30SupportMarkFrameRightDrawFailed(); }
""" in r32_impl,
    ))

if not r32_frame_duplicate_lower_owner_ok(r30_support_api, r30, r32):
    errors.append("R32 R9 frame duplicate owner lost flags/counters/first pose latch")
for label, mutated_r30, mutated_r32 in (
    ("world duplicate flag lost", r30.replace(
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
""",
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = false;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
""", 1), r32),
    ("world stereo flag lost", r30.replace(
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
""",
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = false;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
""", 1), r32),
    ("world increment lost", r30.replace(
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
""",
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        (void)0;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
""", 1), r32),
    ("pose first write only broken", r30.replace(
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
""",
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence != 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
""", 1), r32),
    ("world pose metadata lost", r30.replace(
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            FrameStereoMetadata = stereo;
        }
    }
""",
        """    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        FrameHadDuplicatedDraw = true;
        FrameHadWorldStereo = true;
        ++DuplicatedDraws;
        ++WorldStereoDraws;
        if (FrameStereoPoseSequence == 0)
        {
            FrameStereoPoseSequence = poseSequence;
            (void)stereo;
        }
    }
""", 1), r32),
    ("HUD duplicate count lost", r30.replace(
        """    void R30SupportRecordHudStereoDuplicate() noexcept
    {
        FrameHadDuplicatedDraw = true;
        ++DuplicatedDraws;
        ++NonWorldDuplicatedDraws;
    }
""",
        """    void R30SupportRecordHudStereoDuplicate() noexcept
    {
        FrameHadDuplicatedDraw = true;
        (void)0;
        ++NonWorldDuplicatedDraws;
    }
""", 1), r32),
    ("HUD nonworld count lost", r30.replace(
        """    void R30SupportRecordHudStereoDuplicate() noexcept
    {
        FrameHadDuplicatedDraw = true;
        ++DuplicatedDraws;
        ++NonWorldDuplicatedDraws;
    }
""",
        """    void R30SupportRecordHudStereoDuplicate() noexcept
    {
        FrameHadDuplicatedDraw = true;
        ++DuplicatedDraws;
        (void)0;
    }
""", 1), r32),
    ("right draw failure flag lost", r30.replace(
        """    void R30SupportMarkFrameRightDrawFailed() noexcept
    {
        FrameRightDrawFailed = true;
    }
""",
        """    void R30SupportMarkFrameRightDrawFailed() noexcept
    {
        FrameRightDrawFailed = false;
    }
""", 1), r32),
    ("R32 direct world frame write restored", r30, r32.replace(
        "R30SupportRecordWorldStereoDuplicate(p, s);",
        "FrameHadWorldStereo = true;", 1)),
    ("R32 HUD owner bypass", r30, r32.replace(
        "R30SupportRecordHudStereoDuplicate();",
        "++NonWorldDuplicatedDraws;", 1)),
    ("R32 right failure owner bypass", r30, r32.replace(
        "R30SupportMarkFrameRightDrawFailed();",
        "FrameRightDrawFailed = true;", 1)),
):
    if mutated_r30 == r30 and mutated_r32 == r32:
        errors.append("R84 frame owner negative mutation not applied: " + label)
    elif r32_frame_duplicate_lower_owner_ok(
            r30_support_api, mutated_r30, mutated_r32):
        errors.append("R84 frame owner negative mutation survived: " + label)

# R84 raw draw and Present trampoline owner: R30 invokes exact stock hooks,
# never the higher R30 stereo/hud lower-draw override (double dispatch risk).
# All arguments and HRESULT must pass unchanged; no zero-count "success".
def r32_raw_trampoline_owner_ok(api, lower, upper):
    contracts = (
        ("DrawPrimitive", "DrawPrimitiveHook.stdcall<HRESULT>(d,t,s,p)",
         "R30SupportCallRawDrawPrimitive(d,t,s,p)"),
        ("DrawIndexedPrimitive", "DrawIndexedPrimitiveHook.stdcall<HRESULT>(d,t,b,m,n,s,p)",
         "R30SupportCallRawDrawIndexedPrimitive(d,t,b,m,n,s,p)"),
        ("DrawPrimitiveUP", "DrawPrimitiveUPHook.stdcall<HRESULT>(d,t,p,data,st)",
         "R30SupportCallRawDrawPrimitiveUP(d,t,p,data,st)"),
        ("DrawIndexedPrimitiveUP",
         "DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(\n            d,t,m,n,p,idx,f,v,st)",
         "R30SupportCallRawDrawIndexedPrimitiveUP(d,t,m,n,p,idx,f,v,st)"),
        ("Present", "PresentHook.stdcall<HRESULT>(d,s,dst,w,r)",
         "R30SupportCallRawPresent(d,s,dst,w,r)"),
    )
    for suffix, original_hook, delegated_call in contracts:
        lower_api = "R30SupportCallRaw" + suffix
        review_api = "R32ReviewCallRaw" + suffix
        if lower_api + "(" not in api:
            return False
        if not re.search(
            r"HRESULT\s+" + lower_api +
            r"\([^{};]*\) noexcept\s*\{\s*return " +
            re.escape(original_hook) + r";\s*\}", lower):
            return False
        if not re.search(
            r"HRESULT\s+" + review_api +
            r"\([^{};]*\) noexcept\s*\{\s*return " +
            re.escape(delegated_call) + r";\s*\}", upper):
            return False
    return True

if not r32_raw_trampoline_owner_ok(r30_support_api, r30, r32):
    errors.append("R32 raw draw/Present dispatch must forward exact R9 hooks via R30")
for label, changed_r30, changed_r32 in (
    ("primitive silently succeeds", r30.replace(
        "return DrawPrimitiveHook.stdcall<HRESULT>(d,t,s,p);", "return S_OK;", 1), r32),
    ("indexed base vertex discarded", r30.replace(
        "return DrawIndexedPrimitiveHook.stdcall<HRESULT>(d,t,b,m,n,s,p);",
        "return DrawIndexedPrimitiveHook.stdcall<HRESULT>(d,t,0,m,n,s,p);", 1), r32),
    ("primitive UP stride discarded", r30.replace(
        "return DrawPrimitiveUPHook.stdcall<HRESULT>(d,t,p,data,st);",
        "return DrawPrimitiveUPHook.stdcall<HRESULT>(d,t,p,data,0);", 1), r32),
    ("indexed UP index format changed", r30.replace(
        "return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(\n            d,t,m,n,p,idx,f,v,st);",
        "return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(\n            d,t,m,n,p,idx,D3DFMT_INDEX16,v,st);", 1), r32),
    ("Present region dropped", r30.replace(
        "return PresentHook.stdcall<HRESULT>(d,s,dst,w,r);",
        "return PresentHook.stdcall<HRESULT>(d,s,dst,w,nullptr);", 1), r32),
    ("R32 primitive bypass", r30, r32.replace(
        "return R30SupportCallRawDrawPrimitive(d,t,s,p);",
        "return DrawPrimitiveHook.stdcall<HRESULT>(d,t,s,p);", 1)),
    ("R32 indexed bypass", r30, r32.replace(
        "return R30SupportCallRawDrawIndexedPrimitive(d,t,b,m,n,s,p);",
        "return DrawIndexedPrimitiveHook.stdcall<HRESULT>(d,t,b,m,n,s,p);", 1)),
    ("R32 UP bypass", r30, r32.replace(
        "return R30SupportCallRawDrawPrimitiveUP(d,t,p,data,st);",
        "return DrawPrimitiveUPHook.stdcall<HRESULT>(d,t,p,data,st);", 1)),
    ("R32 indexed UP bypass", r30, r32.replace(
        "return R30SupportCallRawDrawIndexedPrimitiveUP(d,t,m,n,p,idx,f,v,st);",
        "return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(d,t,m,n,p,idx,f,v,st);", 1)),
    ("R32 Present bypass", r30, r32.replace(
        "return R30SupportCallRawPresent(d,s,dst,w,r);",
        "return PresentHook.stdcall<HRESULT>(d,s,dst,w,r);", 1)),
):
    if changed_r30 == r30 and changed_r32 == r32:
        errors.append("R84 raw trampoline mutation not applied: " + label)
    elif r32_raw_trampoline_owner_ok(r30_support_api, changed_r30, changed_r32):
        errors.append("R84 raw trampoline negative mutation survived: " + label)

# R84 R32 stereo RT/depth-stencil switch invokes the original lower
# hook trampolines. R30 must preserve slot index, borrowed surface and HRESULT.
# An absent DS hook has a DIFFERENT original fallback: call the D3D9 device.
def r32_original_target_hooks_ok(api, lower, upper):
    return all((
        "HRESULT R30SupportCallOriginalSetRenderTarget(\n        IDirect3DDevice9* device, DWORD index,\n        IDirect3DSurface9* surface) noexcept;" in api,
        "HRESULT R30SupportCallOriginalSetDepthStencilSurface(\n        IDirect3DDevice9* device,\n        IDirect3DSurface9* surface) noexcept;" in api,
        bool(re.search(
            r"HRESULT R30SupportCallOriginalSetRenderTarget\(\s*"
            r"IDirect3DDevice9\* device, DWORD index,\s*IDirect3DSurface9\* surface\)"
            r" noexcept\s*\{\s*return SetRenderTargetHook.stdcall<HRESULT>"
            r"\(device, index, surface\);\s*\}", lower)),
        bool(re.search(
            r"HRESULT R30SupportCallOriginalSetDepthStencilSurface\(\s*"
            r"IDirect3DDevice9\* device,\s*IDirect3DSurface9\* surface\)"
            r" noexcept\s*\{\s*return SetDepthStencilSurfaceHook\s*\?"
            r"\s*SetDepthStencilSurfaceHook.stdcall<HRESULT>\(device, surface\)"
            r"\s*:\s*device->SetDepthStencilSurface\(surface\);\s*\}", lower)),
        "R32ReviewSetRenderTarget(IDirect3DDevice9* d, DWORD i, IDirect3DSurface9* s) noexcept { return R30SupportCallOriginalSetRenderTarget(d,i,s); }" in upper,
        "R32ReviewSetDepthStencilSurface(IDirect3DDevice9* d, IDirect3DSurface9* s) noexcept { return R30SupportCallOriginalSetDepthStencilSurface(d,s); }" in upper,
    ))

if not r32_original_target_hooks_ok(r30_support_api, r30, r32):
    errors.append("R32 target/depth-stencil original hooks or fallback lost R30 lower owner")
for label, changed_r30, changed_r32 in (
    ("RT original hook bypass", r30.replace(
        "return SetRenderTargetHook.stdcall<HRESULT>(device, index, surface);",
        "return device->SetRenderTarget(index, surface);", 1), r32),
    ("RT index zeroed", r30.replace(
        "return SetRenderTargetHook.stdcall<HRESULT>(device, index, surface);",
        "return SetRenderTargetHook.stdcall<HRESULT>(device, 0u, surface);", 1), r32),
    ("RT surface erased", r30.replace(
        "return SetRenderTargetHook.stdcall<HRESULT>(device, index, surface);",
        "return SetRenderTargetHook.stdcall<HRESULT>(device, index, nullptr);", 1), r32),
    ("DS absent-hook fallback removed", r30.replace(
        "return SetDepthStencilSurfaceHook\n            ? SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, surface)\n"
        "            : device->SetDepthStencilSurface(surface);",
        "return SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, surface);", 1), r32),
    ("DS hook bypass", r30.replace(
        "return SetDepthStencilSurfaceHook\n            ? SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, surface)\n"
        "            : device->SetDepthStencilSurface(surface);",
        "return device->SetDepthStencilSurface(surface);", 1), r32),
    ("R32 RT direct-owner bypass", r30, r32.replace(
        "return R30SupportCallOriginalSetRenderTarget(d,i,s);",
        "return SetRenderTargetHook.stdcall<HRESULT>(d,i,s);", 1)),
    ("R32 DS direct-owner bypass", r30, r32.replace(
        "return R30SupportCallOriginalSetDepthStencilSurface(d,s);",
        "return d->SetDepthStencilSurface(s);", 1)),
):
    if changed_r30 == r30 and changed_r32 == r32:
        errors.append("R84 original target-hook negative mutation not applied: " + label)
    elif r32_original_target_hooks_ok(r30_support_api, changed_r30, changed_r32):
        errors.append("R84 original target-hook negative mutation survived: " + label)

# R84 R32 resource/depth readiness: keep lower allocation, recent-clear depth
# bootstrap and independent depth/stencil live D3D9 state predicates. A forced
# success could expose an incomplete right eye; swapped predicates suppress
# stencil-only validation. Do not mutate per-frame state in this interface.
def r32_resource_depth_owner_ok(api, lower, upper):
    services = (
        ("EnsureStereoResources", "EnsureStereoResources"),
        ("TryBootstrapRightDepth", "TryBootstrapRightDepthFromRecentClear"),
        ("DepthTestActive", "DepthTestActive"),
        ("StencilTestActive", "StencilTestActive"),
    )
    for name, original in services:
        if ("bool R30Support" + name +
                "(IDirect3DDevice9* device) noexcept;") not in api:
            return False
        if not re.search(
            r"bool R30Support" + name +
            r"\(IDirect3DDevice9\* device\) noexcept\s*\{\s*return " +
            original + r"\(device\);\s*\}", lower):
            return False
        if ("bool R32Review" + name +
            "(IDirect3DDevice9* d) noexcept { return R30Support" + name +
            "(d); }") not in upper:
            return False
    return True

if not r32_resource_depth_owner_ok(r30_support_api, r30, r32):
    errors.append("R32 stereo-resource/depth readiness no longer delegates original lower owners")
for label, altered_r30, altered_r32 in (
    ("resource allocation false success", r30.replace(
        "return EnsureStereoResources(device);", "return true;", 1), r32),
    ("right-depth bootstrap erased", r30.replace(
        "return TryBootstrapRightDepthFromRecentClear(device);", "return false;", 1), r32),
    ("depth test forced off", r30.replace(
        "return DepthTestActive(device);", "return false;", 1), r32),
    ("stencil test forced on", r30.replace(
        "return StencilTestActive(device);", "return true;", 1), r32),
    ("depth and stencil swapped", r30.replace(
        "return DepthTestActive(device);", "return StencilTestActive(device);", 1), r32),
    ("R32 resource bypass", r30, r32.replace(
        "return R30SupportEnsureStereoResources(d);", "return EnsureStereoResources(d);", 1)),
    ("R32 bootstrap bypass", r30, r32.replace(
        "return R30SupportTryBootstrapRightDepth(d);", "return TryBootstrapRightDepthFromRecentClear(d);", 1)),
    ("R32 depth bypass", r30, r32.replace(
        "return R30SupportDepthTestActive(d);", "return DepthTestActive(d);", 1)),
    ("R32 stencil bypass", r30, r32.replace(
        "return R30SupportStencilTestActive(d);", "return StencilTestActive(d);", 1)),
):
    if altered_r30 == r30 and altered_r32 == r32:
        errors.append("R84 resource/depth readiness mutation was not applied: " + label)
    elif r32_resource_depth_owner_ok(r30_support_api, altered_r30, altered_r32):
        errors.append("R84 resource/depth readiness negative mutation survived: " + label)

# R84 R32/R31 compile-ownership follow-up: borrowed right-eye surface reads
# must stay in the R30/lower owner, not R32's private textual include chain.
# The API preserves raw pointer identity and lifetime (no AddRef/release).
if "IDirect3DSurface9* R30SupportBorrowedRightEyeSurface() noexcept;" not in r30_support_api:
    errors.append("R30 right-eye borrowed surface owner declaration missing")
if not re.search(
    r"IDirect3DSurface9\* R30SupportBorrowedRightEyeSurface\(\) noexcept"
    r"\s*\{\s*return RightEyeSurface;\s*\}", r30):
    errors.append("R30 borrowed right-eye surface owner must return original lower pointer")
if not re.search(
    r"IDirect3DSurface9\* R32ReviewRightEyeSurface\(\) noexcept"
    r"\s*\{\s*return R30SupportBorrowedRightEyeSurface\(\);\s*\}", r32):
    errors.append("R32 must consume R30 borrowed right-eye surface owner, not lower private state")

# R84: right-eye depth is a borrowed lower resource, not the color surface.
# Move only the R32 lookup across R30; do not AddRef, Release, cache or
# mask a null/failed allocation. Use negative controls for swapped identity,
# a forced null pointer and a bypass of the independent-TU owner facade.
def r32_borrowed_right_depth_boundary_ok(api, owner, consumer):
    return (
        "IDirect3DSurface9* R30SupportBorrowedRightEyeDepth() noexcept;" in api
        and bool(re.search(
            r"IDirect3DSurface9\*\s+R30SupportBorrowedRightEyeDepth"
            r"\(\) noexcept\s*\{\s*return RightEyeDepth;\s*\}", owner))
        and bool(re.search(
            r"IDirect3DSurface9\*\s+R32ReviewRightEyeDepth"
            r"\(\) noexcept\s*\{\s*return R30SupportBorrowedRightEyeDepth\(\);\s*\}",
            consumer))
    )

if not r32_borrowed_right_depth_boundary_ok(r30_support_api, r30, r32):
    errors.append("R32 right-eye depth must borrow original R9 depth through R30 owner")
for label, mutated_r30, mutated_r32 in (
    ("depth confused with color surface", r30.replace(
        "return RightEyeDepth;", "return RightEyeSurface;", 1), r32),
    ("depth incorrectly forced null", r30.replace(
        "return RightEyeDepth;", "return nullptr;", 1), r32),
    ("R32 bypasses depth owner", r30, r32.replace(
        "return R30SupportBorrowedRightEyeDepth();", "return RightEyeDepth;", 1)),
):
    if mutated_r30 == r30 and mutated_r32 == r32:
        errors.append("R84 right-depth negative mutation not applied: " + label)
    elif r32_borrowed_right_depth_boundary_ok(
            r30_support_api, mutated_r30, mutated_r32):
        errors.append("R84 right-depth negative mutation survived: " + label)

# R84 borrowed tracked RT/depth owner seam. These are two reads from the same
# tracked-surface ownership domain, never COM AddRef/release or value copies.
def check_r32_tracked_surface_borrow(source_h, source_r30, source_r32):
    for suffix, raw in (
        ("TrackedRenderTarget", "TrackedRenderTarget"),
        ("TrackedDepthStencil", "TrackedDepthStencil"),
    ):
        owner = "R30SupportBorrowed" + suffix
        consumer = "R32Review" + suffix
        if f"IDirect3DSurface9* {owner}() noexcept;" not in source_h:
            return False
        if not re.search(
            r"IDirect3DSurface9\*\s+" + owner +
            r"\(\) noexcept\s*\{\s*return " + raw + r";\s*\}",
            source_r30):
            return False
        if not re.search(
            r"IDirect3DSurface9\*\s+" + consumer +
            r"\(\) noexcept\s*\{\s*return " + owner + r"\(\);\s*\}",
            source_r32):
            return False
    return True

if not check_r32_tracked_surface_borrow(r30_support_api, r30, r32):
    errors.append("R32 tracked RT/depth borrowed owner facade is missing, swapped or bypassed")
for label, altered_r30, altered_r32 in (
    ("direct R32 tracked RT bypass", r30,
     r32.replace("return R30SupportBorrowedTrackedRenderTarget();",
                 "return TrackedRenderTarget;", 1)),
    ("wrong tracked depth owner", r30.replace(
        "return TrackedDepthStencil;", "return TrackedRenderTarget;", 1), r32),
    ("wrong tracked RT owner", r30.replace(
        "return TrackedRenderTarget;", "return TrackedDepthStencil;", 1), r32),
):
    if altered_r30 == r30 and altered_r32 == r32:
        errors.append("R84 tracked surface test mutation not applied: " + label)
    elif check_r32_tracked_surface_borrow(r30_support_api, altered_r30, altered_r32):
        errors.append("R84 tracked surface regression mutation survived: " + label)

# R32 reads the same latched pose sequence through the R30 owner boundary.
if "std::uint32_t R30SupportFrameStereoPoseSequence() noexcept;" not in r30_support_api:
    errors.append("R30 missing frame stereo pose sequence owner declaration")
if not re.search(r"R30SupportFrameStereoPoseSequence\(\) noexcept\s*\{\s*return FrameStereoPoseSequence;\s*\}", r30):
    errors.append("R30 frame pose-sequence query lost exact original value")
if not re.search(r"R32ReviewFrameStereoPoseSequence\(\) noexcept\s*\{\s*return R30SupportFrameStereoPoseSequence\(\);\s*\}", r32):
    errors.append("R32 bypassed R30 frame pose-sequence owner query")

# R84 R29 effect/stereo boundary is R30-owned, while R32 is hook-free.
# Exact delegation preserves lower stereo readiness, cached fragile classification,
# output-by-reference and one-per-stereo-pair telemetry without new policy.
def r29_effect_boundary_ok(api, producer, consumer):
    required_header = (
        "bool R30SupportStableStereoBase(IDirect3DDevice9* device) noexcept;",
        "bool R30SupportFragileEffectCached(IDirect3DDevice9* device,\n        bool& fragile) noexcept;",
        "void R30SupportNoteStableTwoEyeDraw() noexcept;",
    )
    required_owner = (
        "return R29StableStereoBase(device);",
        "return R29FragileEffectCached(device, fragile);",
        "R29TelemetryNoteStableTwoEyeDraw();",
    )
    required_consumer = (
        "R32ReviewStableStereoBase(IDirect3DDevice9* d) noexcept { return R30SupportStableStereoBase(d); }",
        "R32ReviewFragileEffectCached(IDirect3DDevice9* d, bool& f) noexcept { return R30SupportFragileEffectCached(d,f); }",
        "R32ReviewNoteStableTwoEyeDraw() noexcept { R30SupportNoteStableTwoEyeDraw(); }",
    )
    return (all(x in api for x in required_header) and
            all(x in producer for x in required_owner) and
            all(x in consumer for x in required_consumer))

if not r29_effect_boundary_ok(r30_support_api, r30, r32):
    errors.append("R30/R32 R29-effect owner delegates or API signatures changed")
for label, altered_owner, altered_consumer in (
    ("stereo-readiness forced true", r30.replace(
        "return R29StableStereoBase(device);", "return true;", 1), r32),
    ("fragile output lost", r30.replace(
        "return R29FragileEffectCached(device, fragile);", "return true;", 1), r32),
    ("telemetry omitted", r30.replace(
        "R29TelemetryNoteStableTwoEyeDraw();", "(void)0;", 1), r32),
    ("R32 bypassed owner", r30, r32.replace(
        "return R30SupportStableStereoBase(d);", "return R29StableStereoBase(d);", 1)),
):
    if altered_owner == r30 and altered_consumer == r32:
        errors.append("R29 owner mutation failed to apply: " + label)
    elif r29_effect_boundary_ok(r30_support_api, altered_owner, altered_consumer):
        errors.append("R29 effect/stereo negative mutation survived: " + label)

# R84 R9 depth/stencil metadata must remain read-only and owned by R30.
# A missing generation or invented stencil flag would poison R33's depth cache.
def r9_main_depth_boundary_ok(api, producer, consumer):
    decls = (
        "std::uint64_t R30SupportMainDepthGeneration() noexcept;",
        "bool R30SupportMainDepthHasStencil() noexcept;",
    )
    owners = (
        "std::uint64_t R30SupportMainDepthGeneration() noexcept\n    {\n        return R9MainDepthGenerationValue();\n    }",
        "bool R30SupportMainDepthHasStencil() noexcept\n    {\n        return R9TrackedMainDepthHasStencil();\n    }",
    )
    callers = (
        "R32ReviewMainDepthGeneration() noexcept { return R30SupportMainDepthGeneration(); }",
        "R32ReviewMainDepthHasStencil() noexcept { return R30SupportMainDepthHasStencil(); }",
    )
    return (all(x in api for x in decls) and
            all(x in producer for x in owners) and
            all(x in consumer for x in callers))

if not r9_main_depth_boundary_ok(r30_support_api, r30, r32):
    errors.append("R30/R32 R9 main depth generation/stencil read-only facade missing")
for label, mutated_owner, mutated_consumer in (
    ("generation zeroed", r30.replace(
        "return R9MainDepthGenerationValue();", "return 0;", 1), r32),
    ("stencil forced true", r30.replace(
        "return R9TrackedMainDepthHasStencil();", "return true;", 1), r32),
    ("R32 generation bypass", r30, r32.replace(
        "return R30SupportMainDepthGeneration();",
        "return R9MainDepthGenerationValue();", 1)),
):
    if mutated_owner == r30 and mutated_consumer == r32:
        errors.append("R9 depth owner mutation not applied: " + label)
    elif r9_main_depth_boundary_ok(r30_support_api, mutated_owner, mutated_consumer):
        errors.append("R9 depth owner mutation survived: " + label)

# R84 R9 right-depth/stencil synchronization remains lower-owned. Both
# invalidation flags must be forwarded unchanged, and the two readiness
# queries must never be conflated or forced true.
def r9_right_sync_boundary_ok(api, producer, consumer):
    decl = (
        "void R30SupportInvalidateRightDepthStencilSync(\n        bool invalidateDepth, bool invalidateStencil) noexcept;",
        "bool R30SupportRightDepthInSync() noexcept;",
        "bool R30SupportRightStencilInSync() noexcept;",
    )
    owner = (
        "R9InvalidateRightDepthStencilSync(invalidateDepth, invalidateStencil);",
        "return R9IsRightDepthInSync();",
        "return R9IsRightStencilInSync();",
    )
    caller = (
        "R32ReviewInvalidateRightDepthStencilSync(bool d, bool s) noexcept { R30SupportInvalidateRightDepthStencilSync(d, s); }",
        "R32ReviewRightDepthInSync() noexcept { return R30SupportRightDepthInSync(); }",
        "R32ReviewRightStencilInSync() noexcept { return R30SupportRightStencilInSync(); }",
    )
    return (all(x in api for x in decl) and all(x in producer for x in owner) and
            all(x in consumer for x in caller))

if not r9_right_sync_boundary_ok(r30_support_api, r30, r32):
    errors.append("R30/R32 right depth/stencil sync API no longer preserves lower R9 contract")
for label, changed_r30, changed_r32 in (
    ("invalidation flags swapped", r30.replace(
        "R9InvalidateRightDepthStencilSync(invalidateDepth, invalidateStencil);",
        "R9InvalidateRightDepthStencilSync(invalidateStencil, invalidateDepth);", 1), r32),
    ("depth falsely in sync", r30.replace(
        "return R9IsRightDepthInSync();", "return true;", 1), r32),
    ("stencil falsely in sync", r30.replace(
        "return R9IsRightStencilInSync();", "return true;", 1), r32),
    ("R32 bypasses R30", r30, r32.replace(
        "return R30SupportRightDepthInSync();", "return R9IsRightDepthInSync();", 1)),
):
    if changed_r30 == r30 and changed_r32 == r32:
        errors.append("R9 right-sync mutation not applied: " + label)
    elif r9_right_sync_boundary_ok(r30_support_api, changed_r30, changed_r32):
        errors.append("R9 right-sync mutation survived: " + label)


# R84 R9 left-draw depth/stencil write eligibility must remain independent.
# False flags incorrectly preserve stale right-eye depth; true flags can force
# unnecessary invalidation. The R30 owner forwards the exact original queries.
def r9_left_write_eligibility_owner_ok(api, producer, consumer):
    return all((
        "bool R30SupportLeftDrawMayWriteDepth(IDirect3DDevice9* device) noexcept;" in api,
        "bool R30SupportLeftDrawMayWriteStencil(IDirect3DDevice9* device) noexcept;" in api,
        bool(re.search(
            r"bool R30SupportLeftDrawMayWriteDepth\(IDirect3DDevice9\* device\) noexcept"
            r"\s*\{\s*return LeftDrawMayWriteDepth\(device\);\s*\}", producer)),
        bool(re.search(
            r"bool R30SupportLeftDrawMayWriteStencil\(IDirect3DDevice9\* device\) noexcept"
            r"\s*\{\s*return LeftDrawMayWriteStencil\(device\);\s*\}", producer)),
        "R32ReviewLeftDrawMayWriteDepth(IDirect3DDevice9* d) noexcept { return R30SupportLeftDrawMayWriteDepth(d); }" in consumer,
        "R32ReviewLeftDrawMayWriteStencil(IDirect3DDevice9* d) noexcept { return R30SupportLeftDrawMayWriteStencil(d); }" in consumer,
    ))

if not r9_left_write_eligibility_owner_ok(r30_support_api, r30, r32):
    errors.append("R32 left-draw depth/stencil write eligibility must delegate via R30")
for label, changed_r30, changed_r32 in (
    ("depth falsely always writeable", r30.replace(
        "return LeftDrawMayWriteDepth(device);", "return true;", 1), r32),
    ("stencil falsely never writeable", r30.replace(
        "return LeftDrawMayWriteStencil(device);", "return false;", 1), r32),
    ("depth/stencil swapped", r30.replace(
        "return LeftDrawMayWriteDepth(device);",
        "return LeftDrawMayWriteStencil(device);", 1), r32),
    ("R32 depth bypasses R30", r30, r32.replace(
        "return R30SupportLeftDrawMayWriteDepth(d);",
        "return LeftDrawMayWriteDepth(d);", 1)),
    ("R32 stencil bypasses R30", r30, r32.replace(
        "return R30SupportLeftDrawMayWriteStencil(d);",
        "return LeftDrawMayWriteStencil(d);", 1)),
):
    if changed_r30 == r30 and changed_r32 == r32:
        errors.append("R84 write-eligibility negative mutation not applied: " + label)
    elif r9_left_write_eligibility_owner_ok(
            r30_support_api, changed_r30, changed_r32):
        errors.append("R84 write-eligibility negative mutation survived: " + label)

# The original R9 depth-content write event remains R9-owned. R32's R30
# boundary is behavior-neutral: one call in, one exact R9 notification out.
def r9_depth_content_write_boundary_ok(api, producer, consumer):
    signature = "void R30SupportNoteMainDepthContentWrite() noexcept"
    if api.count(signature + ";") != 1 or producer.count(signature) != 1:
        return False
    owned_body = producer.split(signature, 1)[1].split("}", 1)[0]
    return (
        "".join(owned_body.split()) == "{R9NoteMainDepthContentWrite();"
        and consumer.count(
            "void R32ReviewNoteMainDepthContentWrite() noexcept { R30SupportNoteMainDepthContentWrite(); }"
        ) == 1
    )

if not r9_depth_content_write_boundary_ok(r30_support_api, r30, r32):
    errors.append("R32 main-depth write lost the R30 -> R9 owner notification contract")
_owner_signature = "void R30SupportNoteMainDepthContentWrite() noexcept"
_owner_tail = r30.split(_owner_signature, 1)[1].split("}", 1)[0] + "}"
_owner_block = _owner_signature + _owner_tail
for label, changed_r30, changed_r32 in (
    ("R9 depth write side effect erased", r30.replace(
        _owner_block, _owner_block.replace("R9NoteMainDepthContentWrite();", "(void)0;"), 1), r32),
    ("R32 bypasses R30 depth write owner", r30, r32.replace(
        "void R32ReviewNoteMainDepthContentWrite() noexcept { R30SupportNoteMainDepthContentWrite(); }",
        "void R32ReviewNoteMainDepthContentWrite() noexcept { R9NoteMainDepthContentWrite(); }", 1)),
):
    if changed_r30 == r30 and changed_r32 == r32:
        errors.append("R9 depth-write negative mutation not applied: " + label)
    elif r9_depth_content_write_boundary_ok(r30_support_api, changed_r30, changed_r32):
        errors.append("R9 depth-write negative mutation survived: " + label)

# F11/Tweaks ImGui is external screen-space UI. During gameplay it must not
# consume a pending game semantic token, and it must enter the already-proven
# SCREEN_OVERLAY_2D stereo convergence path instead of falling back to R26.
for marker in (
    "ScopedExternalOverlaySemantic",
    "ExternalOverlaySemanticDepth",
    "if (ExternalOverlaySemanticDepth != 0)",
):
    if marker not in render_semantics:
        errors.append(f"render semantics missing external-overlay guard: {marker}")
for marker in (
    "ScopedExternalOverlaySemantic",
    "RenderScope::ScreenOverlay2D",
    "ImGui_ImplDX9_RenderDrawData",
):
    if marker not in overlay_hooks:
        errors.append(f"F11 overlay missing explicit stereo semantic scope: {marker}")
if "CorroboratesScreenOverlay2D" not in r30_safe or "semanticOverlay2D" not in r30_safe:
    errors.append("active R26+R30 path missing SCREEN_OVERLAY_2D owner route")

if "R22FailClosedReplayState" in r23:
    errors.append("R23 retained private R22 fail-closed replay dependency")
if "FailClosedTrackedRasterReplay(" not in r22:
    errors.append("R22 missing fail-closed raster owner API")
if "FailClosedTrackedRasterReplay(" not in r23:
    errors.append("R23 missing fail-closed raster owner API use")

if "R23GameDrawSerial" in r29:
    errors.append("R29 retained direct R23 draw-serial state dependency")
if "TopLevelDrawSerial()" not in r29:
    errors.append("R29 missing R23 draw-serial owner query")

if "R22PrimeShadowState" in r31:
    errors.append("R31 retained private R22 raster-prime dependency")
if "PrimeTrackedRasterShadow(" not in r22:
    errors.append("R22 missing raster-prime owner API")
if "PrimeTrackedRasterShadow" not in r31:
    errors.append("R31 missing raster-prime owner API use")

for banned in ("R22ScissorSnapshot", "R22CaptureGameScissor",
               "R22GameClearCoversBackbuffer"):
    if banned in r23:
        errors.append(
            f"R23 retained private R22 raster helper dependency: {banned}")
for marker in ("CaptureTrackedRasterState(", "TrackedGameClearCoversBackbuffer("):
    if marker not in r22:
        errors.append(f"R22 missing raster owner API: {marker}")
    if marker not in r23:
        errors.append(f"R23 missing raster owner API use: {marker}")

for banned in ("R22ShadowState", "R22StateBlockTrackingReliable"):
    if banned in r23:
        errors.append(f"R23 regained direct lower-layer state dependency: {banned}")
if "R22StateBlockTrackingReliable" in r22:
    errors.append("R22 retained removed StateBlock reliability authority")
if "StateBlockTracker::SetLifecycleHooksReady(stateBlockHooks)" not in r22.replace("\n", " ").replace("  ", " "):
    # Whitespace-independent fallback below checks the two required markers.
    if not ("SetLifecycleHooksReady(" in r22 and "stateBlockHooks" in r22):
        errors.append("R22 missing neutral StateBlock lifecycle coverage publication")
if "StateBlockTracker::SetLifecycleHooksReady(false)" not in r22:
    errors.append("R22 rollback/install path missing lifecycle coverage reset")

for rel, source in (
    ("R20", r20), ("R23", r23), ("R29", r29),
    ("R30", r30), ("R30_SAFE", r30_safe),
    ("R31", r31), ("R32", r32), ("R33", r33),
):
    for banned in ("R9MainDepthContentSerial", "R9MonoDepthContentSerial"):
        if banned in source:
            errors.append(
                f"{rel} retained direct R9 depth-content state dependency: {banned}")
for marker in (
    "R9SynchronizeDepthContentSerials()",
    "R9NoteMainDepthContentWrite()",
):
    if marker not in r9:
        errors.append(f"R9 missing depth-content owner API: {marker}")
for rel, source in (("R20", r20), ("R23", r23)):
    if "R9SynchronizeDepthContentSerials()" not in source:
        errors.append(f"{rel} missing R9 depth-content synchronization owner API")

for rel, source in (("R30", r30), ("R30_SAFE", r30_safe)):
    if "R9NoteMainDepthContentWrite()" not in source:
        errors.append(f"{rel} missing R9 main-depth write owner API")

for rel, source in (("R20", r20), ("R23", r23)):
    if re.search(r"\bR9MainDepthGeneration\b", source):
        errors.append(
            f"{rel} retained direct R9 main-depth generation dependency")
    if "R9MainDepthGenerationValue()" not in source:
        errors.append(
            f"{rel} missing R9 main-depth generation owner query")
if re.search(r"\bR9MainDepthGeneration\b", r33):
    errors.append("R33 retained direct R9 main-depth generation dependency")
if "R32ReviewMainDepthGeneration()" not in r33:
    errors.append("R33 missing R32 review facade for main-depth generation")
if "R9MainDepthGenerationValue()" not in r9:
    errors.append("R9 missing main-depth generation owner query API")

# Post-1100 dispatcher flattening: R33 is the sole draw dispatcher allowed to
# call the R30 lower-draw boundary. R31 is StateBlock/cache-only and must not
# regain either the public lower-draw calls or R30 private hook storage.
for rel, source in (("R31", r31), ("R33", r33)):
    for banned in (
        "R30DrawPrimitiveR29Hook",
        "R30DrawIndexedPrimitiveR29Hook",
        "R30DrawPrimitiveUPR29Hook",
        "R30DrawIndexedPrimitiveUPR29Hook",
    ):
        if banned in source:
            errors.append(
                f"{rel} retained direct R30 lower-hook storage dependency: {banned}")
for marker, facade in (
    ("R30CallLowerDrawPrimitive(", "R32ReviewCallLowerDrawPrimitive("),
    ("R30CallLowerDrawIndexedPrimitive(", "R32ReviewCallLowerDrawIndexedPrimitive("),
    ("R30CallLowerDrawPrimitiveUP(", "R32ReviewCallLowerDrawPrimitiveUP("),
    ("R30CallLowerDrawIndexedPrimitiveUP(", "R32ReviewCallLowerDrawIndexedPrimitiveUP("),
):
    if marker not in r30:
        errors.append(f"R30 missing lower-draw owner boundary: {marker}")
    if facade not in r33:
        errors.append(f"R33 missing R32 split facade for lower-draw owner boundary: {facade}")
    if marker in r31:
        errors.append(f"R31 regained retired R30 lower-draw owner boundary use: {marker}")

# Owner boundaries are not marker-only: each wrapper must still delegate to the
# matching R29 hook storage so refactor flattening cannot silently reroute a
# draw family while satisfying the public boundary name.
for owner, lower_hook in (
    ("R30CallLowerDrawPrimitive", "R30DrawPrimitiveR29Hook.stdcall<HRESULT>("),
    ("R30CallLowerDrawIndexedPrimitive", "R30DrawIndexedPrimitiveR29Hook.stdcall<HRESULT>("),
    ("R30CallLowerDrawPrimitiveUP", "R30DrawPrimitiveUPR29Hook.stdcall<HRESULT>("),
    ("R30CallLowerDrawIndexedPrimitiveUP", "R30DrawIndexedPrimitiveUPR29Hook.stdcall<HRESULT>("),
):
    owner_start = r30.find(f"{owner}(")
    owner_end = r30.find("\n    }", owner_start)
    if owner_start < 0 or owner_end < 0 or lower_hook not in r30[owner_start:owner_end]:
        errors.append(
            f"R30 lower-draw owner boundary lost matching delegation: {owner}")

# R31 prerequisite polling must observe R30 through an owner status query.
if re.search(r"\bR30InstallState\b", r31):
    errors.append("R31 retained direct R30 install-state dependency")
if "R30InstallStatus()" not in r30:
    errors.append("R30 missing install-state owner query")
if "R30InstallStatus()" not in r31:
    errors.append("R31 missing R30 install-state owner query")

status_start = r30.find("R30InstallStatus()")
status_end = r30.find("\n    }", status_start)
if status_start < 0 or status_end < 0 or \
        "R30InstallState.load(std::memory_order_acquire)" not in r30[status_start:status_end]:
    errors.append("R30 install-state owner query lost acquire-load semantics")

# R32 fail-closed gating may ask whether the R9 stereo baseline is seeded, but
# the seed flag and the R9 query remain lower-owned. R32 must consume that
# predicate through the explicit R30 support boundary.
if re.search(r"\bR9StereoSeeded\b", r32):
    errors.append("R32 retained direct R9 stereo-seed dependency")
if "R9StereoBaselineSeeded()" not in r9:
    errors.append("R9 missing stereo-seed owner query")
if "R30SupportStereoBaselineSeeded()" not in r30:
    errors.append("R30 missing R9 stereo-seed support facade")
if "R30SupportStereoBaselineSeeded()" not in r32:
    errors.append("R32 missing R30 stereo-seed support facade")
if "R9StereoBaselineSeeded()" in r32:
    errors.append("R32 bypassed R30 and regained direct R9 stereo-seed owner query")

seed_start = r9.find("R9StereoBaselineSeeded()")
seed_end = r9.find("\n\t}", seed_start)
if seed_start < 0 or seed_end < 0 or \
        "return R9StereoSeeded;" not in r9[seed_start:seed_end]:
    errors.append("R9 stereo-seed owner query lost direct baseline-state semantics")

support_seed_start = r30.find("R30SupportStereoBaselineSeeded()")
support_seed_end = r30.find("\n    }", support_seed_start)
if support_seed_start < 0 or support_seed_end < 0 or \
        "return R9StereoBaselineSeeded();" not in r30[support_seed_start:support_seed_end]:
    errors.append("R30 stereo-seed support facade lost exact R9 owner delegation")

# Post-1000 R33 owner-boundary continuation: the final dispatcher may ask R9
# whether the currently tracked main depth carries stencil, but must not read
# R9's private identity/descriptor/known-state tuple directly.
if "inline bool R9TrackedMainDepthHasStencil() noexcept" not in r9:
    errors.append("R9 missing tracked-main-depth stencil owner query API")
if "R32ReviewMainDepthHasStencil()" not in r33:
    errors.append("R33 missing R32 review facade for tracked-main-depth stencil owner query")
for banned in ("R9MainDepthKnown", "R9MainDepthIdentity", "R9MainDepthDesc"):
    if banned in r33:
        errors.append(
            f"R33 retained direct R9 main-depth metadata dependency: {banned}")

# Post-1000 successor: R33 must not directly mutate R9-owned right-depth/
# stencil synchronization flags. Preserve exact invalidation semantics through
# one lower-owner API so later final-dispatch cleanup cannot split ownership.
r9_depth_sync_owner = re.search(
    r"inline void R9InvalidateRightDepthStencilSync\(\s*"
    r"bool invalidateDepth, bool invalidateStencil\) noexcept\s*"
    r"\{(?P<body>.*?)\n\t\}",
    r9,
    re.DOTALL,
)
if not r9_depth_sync_owner:
    errors.append("R9 missing right depth/stencil sync invalidation owner API")
else:
    sync_body = r9_depth_sync_owner.group("body")
    sync_order = [
        sync_body.find("if (invalidateDepth)"),
        sync_body.find("RightDepthSynchronized = false;"),
        sync_body.find("if (invalidateStencil)"),
        sync_body.find("RightStencilSynchronized = false;"),
    ]
    if min(sync_order) < 0 or sync_order != sorted(sync_order):
        errors.append(
            "R9 right-depth sync owner API must preserve depth/stencil invalidation order")
for banned in ("RightDepthSynchronized = false;",
               "RightStencilSynchronized = false;"):
    if banned in r33:
        errors.append(
            f"R33 retained direct R9 right-depth sync mutation: {banned}")
if r33.count("R32ReviewInvalidateRightDepthStencilSync(") < 2:
    errors.append(
        "R33 missing R32 review facade for right-depth sync invalidation at left-write and fail-close boundaries")

# Post-1000 successor: R33 may consult right depth/stencil synchronization
# readiness only through R9 owner queries. Direct reads split ownership just as
# direct writes do and make later final-dispatch flattening harder to reason about.
for marker in (
    "inline bool R9IsRightDepthInSync() noexcept",
    "inline bool R9IsRightStencilInSync() noexcept",
):
    if marker not in r9:
        errors.append(f"R9 missing right depth/stencil sync owner query: {marker}")
for raw in ("RightDepthSynchronized", "RightStencilSynchronized"):
    if re.search(rf"\b{raw}\b", r33):
        errors.append(f"R33 retained direct R9 right-depth sync read: {raw}")
if r33.count("R32ReviewRightDepthInSync()") < 4:
    errors.append("R33 missing R32 review facade depth-sync query at both world/HUD readiness gates")
if r33.count("R32ReviewRightStencilInSync()") < 4:
    errors.append("R33 missing R32 review facade stencil-sync query at both world/HUD readiness gates")
if "return RightDepthSynchronized;" not in r9:
    errors.append("R9 depth-sync owner query no longer preserves tracked-state read")
if "return RightStencilSynchronized;" not in r9:
    errors.append("R9 stencil-sync owner query no longer preserves tracked-state read")

if "R9DrawCalls" in r20:
    errors.append("R20 retained direct R9 draw-count dependency")
if "R9DrawCallCount()" not in r20:
    errors.append("R20 missing R9 draw-count owner query")
if "R9DrawCallCount()" not in r9:
    errors.append("R9 missing draw-count owner query API")

for rel, source in (("R30", r30), ("R30_SAFE", r30_safe)):
    if "--R9DrawCalls;" in source:
        errors.append(f"{rel} retained direct R9 draw-count rollback")
    if "R9UndoStereoDrawCount();" not in source:
        errors.append(f"{rel} missing R9 draw-count rollback owner API")
if "R9UndoStereoDrawCount()" not in r9:
    errors.append("R9 missing draw-count rollback owner API")

if "R9NoteMainDepthContentWrite()" not in r29:
    errors.append("R29 missing R9 main-depth write owner API")
if "R32ReviewNoteMainDepthContentWrite()" not in r33:
    errors.append("R33 missing R32 review facade for R9 main-depth write owner API")
if "R9NoteMainDepthContentWrite()" in r31:
    errors.append("R31 regained retired draw-side main-depth accounting")
# The R32 split now delegates the same R9 side effect through the R30 owner.
# Keep this legacy review check aligned with the exact negative-mutation
# owner-boundary contract above; do not require an obsolete direct R9 call.
if "void R32ReviewNoteMainDepthContentWrite() noexcept { R30SupportNoteMainDepthContentWrite(); }" not in r32:
    errors.append("R32 split facade must delegate main-depth accounting through R30 to the R9 owner API")

for banned in ("R23GameDrawSerial", "R23BeforeTopLevelDraw", "GetTopLevelDrawSerial()"):
    if banned in r26:
        errors.append(f"R26 regained R23 implementation dependency: {banned}")

if "R23GameDrawSerial" in r30_safe:
    errors.append("active R30-safe HUD path retained direct R23 draw-serial state")
if "TopLevelDrawSerial() + 1u" not in r30_safe:
    errors.append("active R30-safe HUD path missing R23 draw-serial owner query")

for marker, source, owner in (
    ("InvalidateLiveStateSample()", r23, "R23"),
    ("InvalidateEffectStateCache()", r29, "R29"),
    ("ArmStereoRecoverySafety(", r29, "R29"),
):
    if marker not in source:
        errors.append(f"{owner} missing explicit cache invalidation API: {marker}")

for banned in (
    "R29Effect",
    "R23LastStateSampleDrawSerial",
    "R23LastStateSampleEpoch",
    "R22ShadowState",
    "R29ArmMonoSafety",
):
    if banned in r31:
        errors.append(
            f"R31 regained direct lower-layer cache mutation: {banned}")

for marker in (
    "InvalidateEffectStateCache()",
    "InvalidateTrackedRasterShadow()",
    "InvalidateLiveStateSample()",
    "TryGetTrackedViewport(viewport)",
):
    if marker not in r31:
        errors.append(
            f"R31 missing owner cache invalidation boundary: {marker}")

required_r22 = (
    '#include "../state/d3d9_raster_state.hpp"',
    "using R22ScissorSnapshot = OutRunVR::State::D3D9RasterSnapshot;",
    "GetTrackedRasterShadow()",
    "TryGetTrackedViewport(",
    "SetTrackedRasterShadow(",
    "InvalidateTrackedRasterShadow()",
    "IsTrackedStateBlockReliable()",
)
for marker in required_r22:
    if marker not in r22:
        errors.append(f"R22 missing state-boundary marker: {marker}")

for marker in (
    "enum class DrawClass",
    "FromGameSemantic",
    "FromHudSpace",
    "FromPassSemantic",
):
    if marker not in draw_class:
        errors.append(f"draw semantic contract missing: {marker}")

if "SameRasterSnapshot" not in raster:
    errors.append("neutral raster snapshot comparison missing")

for marker in (
    "class StateBlockTracker",
    "SetR22Reliable(",
    "R22Reliable()",
    "SetEventConsumerReady(",
    "EventConsumerReady()",
    "Reliable()",
    "SetLifecycleHooksReady(",
    "LifecycleHooksReady()",
    "MarkCoverageLost()",
    "ResetCoverageLoss()",
    "CoverageLost()",
    "RequireResync()",
    "ConsumeResync()",
    "NoteRecording()",
    "NoteApply()",
    "RecordingGeneration()",
    "ApplyGeneration()",
    "SetRecording(",
    "Recording()",
):
    if marker not in state_block_tracker:
        errors.append(f"StateBlockTracker missing API marker: {marker}")

for rel, source in (
    ("R22", r22),
    ("R31", r31),
    ("R33", r33),
):
    if '../state/state_block_tracker.hpp' not in source:
        errors.append(f"{rel} missing neutral StateBlockTracker include")
if '../state/state_block_events.hpp' not in r22:
    errors.append("R22 missing neutral StateBlock event boundary include")

for rel, source in (("R32", r32), ("R33", r33)):
    if "R31StateBlockTrackingReliable" in source:
        errors.append(
            f"{rel} regained removed R31 StateBlock reliability dependency")

for banned in ("R31StateBlockRecordings", "R31StateBlockApplies"):
    for rel, source in (("R32", r32), ("R33", r33)):
        if banned in source:
            errors.append(
                f"{rel} regained R31 StateBlock generation dependency: {banned}")
    if banned in r31:
        errors.append(
            f"R31 retained migrated StateBlock generation owner: {banned}")

for marker in (
    "class StateBlockEvents",
    "Configure(",
    "Configured()",
    "Clear()",
    "NotifyBegin(",
    "NotifyEnd(",
    "NotifyApply(",
):
    if marker not in state_block_events:
        errors.append(f"StateBlockEvents missing API marker: {marker}")

clear_events = re.search(
    r"static void Clear\(\) noexcept\s*\{(?P<body>.*?)\n        \}",
    state_block_events,
    re.DOTALL,
)
if not clear_events:
    errors.append("StateBlockEvents Clear body missing")
else:
    clear_body = clear_events.group("body")
    begin_clear = clear_body.find("BeginCallback().store(nullptr")
    end_clear = clear_body.find("EndCallback().store(nullptr")
    apply_clear = clear_body.find("ApplyCallback().store(nullptr")
    if min(begin_clear, end_clear, apply_clear) < 0:
        errors.append("StateBlockEvents callback clear marker missing")
    elif not (begin_clear < end_clear and begin_clear < apply_clear):
        errors.append(
            "StateBlockEvents must clear Begin before terminal callbacks")

configure_events = re.search(
    r"static void Configure\(BeginFn begin, EndFn end, ApplyFn apply\) noexcept\s*\{(?P<body>.*?)\n        \}",
    state_block_events,
    re.DOTALL,
)
if not configure_events:
    errors.append("StateBlockEvents Configure body missing")
else:
    configure_body = configure_events.group("body")
    begin_publish = configure_body.find("BeginCallback().store")
    end_publish = configure_body.find("EndCallback().store")
    apply_publish = configure_body.find("ApplyCallback().store")
    if min(begin_publish, end_publish, apply_publish) < 0:
        errors.append("StateBlockEvents callback publication marker missing")
    elif not (end_publish < begin_publish and apply_publish < begin_publish):
        errors.append(
            "StateBlockEvents must publish End/Apply callbacks before Begin")

for marker in (
    "class StateBlockRecovery",
    "Configure(",
    "Clear()",
    "FlushPendingResync(",
    "StateBlockTracker::ConsumeResync()",
):
    if marker not in state_block_recovery:
        errors.append(f"StateBlockRecovery missing API marker: {marker}")

clear_recovery = re.search(
    r"static void Clear\(\) noexcept\s*\{(?P<body>.*?)\n        \}",
    state_block_recovery,
    re.DOTALL,
)
if not clear_recovery:
    errors.append("StateBlockRecovery Clear body missing")
else:
    clear_body = clear_recovery.group("body")
    if "ResynchronizeShaderEpoch().store(nullptr" not in clear_body or \
            "PrimeShadowState().store(nullptr" not in clear_body:
        errors.append("StateBlockRecovery Clear must withdraw both providers")

flush_match = re.search(
    r"static void FlushPendingResync\(IDirect3DDevice9\* device\) noexcept\s*\{(?P<body>.*?)\n        \}",
    state_block_recovery,
    re.DOTALL,
)
if not flush_match:
    errors.append("StateBlockRecovery FlushPendingResync body missing")
else:
    flush_body = flush_match.group("body")
    callback_ready = flush_body.find("if (!resynchronizeShaderEpoch || !primeShadowState)")
    consume = flush_body.find("StateBlockTracker::ConsumeResync()")
    shader_resync = flush_body.find("resynchronizeShaderEpoch(device)")
    shadow_prime = flush_body.find("primeShadowState(device)")
    if min(callback_ready, consume, shader_resync, shadow_prime) < 0:
        errors.append("StateBlockRecovery recovery-order marker missing")
    elif not callback_ready < consume < shader_resync < shadow_prime:
        errors.append(
            "StateBlockRecovery must validate callbacks before consuming resync "
            "and preserve shader-resync before shadow-prime ordering")

# Cycle 911-1000 owner-boundary convergence.
# Upper layers may update lower-layer telemetry only through owner APIs.
for rel, source in (("R31", r31), ("R32", r32), ("R33", r33)):
    if "++R29StableTwoEyeDraws;" in source:
        errors.append(
            f"{rel} retained direct R29 stable-two-eye telemetry mutation")
    if "++R30ScreenSpaceFovDraws;" in source:
        errors.append(
            f"{rel} retained direct R30 screen-space telemetry mutation")

if "R29TelemetryNoteStableTwoEyeDraw()" not in r29:
    errors.append("R29 missing stable-two-eye telemetry owner API")
if "R30TelemetryNoteScreenSpaceFovDraw()" not in r30:
    errors.append("R30 missing screen-space telemetry owner API")

# R84 R9 mono-backup gap and stereo failure poisoning are fail-closed side effects.
# R32 must call the original lower owner through R30 without suppressing the
# counter/gap transition or erasing the reported failure reason/site/HRESULT.
def r9_mono_failure_owner_ok(api, owner, consumer):
    return all((
        "void R30SupportNoteStereoDrawWithoutMonoBackup() noexcept;" in api,
        "void R30SupportReportStereoFailure(\n        OutRunVR::StereoFailureReason reason,\n        const char* site, HRESULT hr) noexcept;" in api,
        bool(re.search(r"void R30SupportNoteStereoDrawWithoutMonoBackup\(\) noexcept"
                       r"\s*\{\s*R9NoteStereoDrawWithoutMonoBackup\(\);\s*\}", owner)),
        bool(re.search(
            r"void R30SupportReportStereoFailure\(\s*"
            r"OutRunVR::StereoFailureReason reason,\s*const char\* site,\s*HRESULT hr\)"
            r" noexcept\s*\{\s*R9Poison\(reason, site, hr\);\s*\}", owner)),
        "void R32ReviewNoteStereoDrawWithoutMonoBackup() noexcept { R30SupportNoteStereoDrawWithoutMonoBackup(); }" in consumer,
        "R32ReviewReportStereoFailure(OutRunVR::StereoFailureReason r, const char* s, HRESULT hr) noexcept { R30SupportReportStereoFailure(r,s,hr); }" in consumer,
    ))

if not r9_mono_failure_owner_ok(r30_support_api, r30, r32):
    errors.append("R32 R9 mono-backup/failure owner lost exact R30 delegations")
_mono_body = ("void R30SupportNoteStereoDrawWithoutMonoBackup() noexcept\n"
              "    {\n        R9NoteStereoDrawWithoutMonoBackup();\n    }")
for label, changed_r30, changed_r32 in (
    ("mono backup gap side effect erased", r30.replace(
        _mono_body, _mono_body.replace(
            "R9NoteStereoDrawWithoutMonoBackup();", "(void)0;"), 1), r32),
    ("poison reason discarded", r30.replace(
        "R9Poison(reason, site, hr);",
        "R9Poison(OutRunVR::StereoFailureNone, site, hr);", 1), r32),
    ("poison site discarded", r30.replace(
        "R9Poison(reason, site, hr);", "R9Poison(reason, nullptr, hr);", 1), r32),
    ("poison HRESULT discarded", r30.replace(
        "R9Poison(reason, site, hr);", "R9Poison(reason, site, S_OK);", 1), r32),
    ("R32 bypasses mono owner", r30, r32.replace(
        "R30SupportNoteStereoDrawWithoutMonoBackup();",
        "R9NoteStereoDrawWithoutMonoBackup();", 1)),
    ("R32 bypasses poison owner", r30, r32.replace(
        "R30SupportReportStereoFailure(r,s,hr);",
        "R9Poison(r,s,hr);", 1)),
):
    if changed_r30 == r30 and changed_r32 == r32:
        errors.append("R9 mono failure owner mutation not applied: " + label)
    elif r9_mono_failure_owner_ok(r30_support_api, changed_r30, changed_r32):
        errors.append("R9 mono failure owner negative mutation survived: " + label)

# A duplicated stereo draw without a complete independent mono replay has one
# R9-owned accounting transition: increment draw calls + mark the mono backup
# incomplete. Upper layers must not reproduce that state pair themselves.
for rel, source in (
    ("R29", r29), ("R30", r30), ("R30_SAFE", r30_safe), ("R33", r33),
):
    for banned in ("++R9DrawCalls;", "R9MonoBackupGap = true;"):
        if banned in source:
            errors.append(
                f"{rel} retained direct R9 stereo-draw accounting mutation: {banned}")
    expected = (
        "R32ReviewNoteStereoDrawWithoutMonoBackup();"
        if rel == "R33" else "R9NoteStereoDrawWithoutMonoBackup();")
    if expected not in source:
        errors.append(
            f"{rel} missing stereo-draw accounting owner API use: {expected}")
for banned in ("++R9DrawCalls;", "R9MonoBackupGap = true;",
               "R9NoteStereoDrawWithoutMonoBackup();"):
    if banned in r31:
        errors.append(
            f"R31 regained retired stereo-draw accounting: {banned}")
# R32 calls the explicit R30 lower-owner bridge; R30 remains responsible for
# invoking the original R9 draw-count/mono-backup-gap transition exactly once.
if "void R32ReviewNoteStereoDrawWithoutMonoBackup() noexcept { R30SupportNoteStereoDrawWithoutMonoBackup(); }" not in r32:
    errors.append("R32 split facade must delegate stereo-draw accounting via R30 to the R9 owner API")
if "R9NoteStereoDrawWithoutMonoBackup()" not in r9:
    errors.append("R9 missing stereo-draw accounting owner API")

# R32 may consume R13 DirectGPU contracts, but readiness, ACK mapping and R13's
# safety telemetry remain R13-owned state.
for banned in (
    "R13OverlayReady.load(",
    "R13ReadGpuCompletedFrame(",
    "++R13SafeAckBackpressure;",
):
    if banned in r32:
        errors.append(
            f"R32 retained direct R13 DirectGPU owner-state dependency: {banned}")
for marker in (
    "R13OverlayReadyForTransport()",
    "R13TryGetGpuCompletionSnapshot(",
    "R13NoteSafeAckBackpressure()",
):
    if marker not in r13:
        errors.append(f"R13 missing DirectGPU owner API: {marker}")
if "R30SupportTryGetGpuCompletionSnapshot(" not in r32:
    errors.append("R32 missing R30 facade for R13 ACK snapshot/rebind")
if "R13TryGetGpuCompletionSnapshot(" in r32 or "R13GpuCompletionSnapshot" in r32:
    errors.append("R32 regained direct R13 ACK snapshot/rebind dependency")
if "R30SupportNoteSafeAckBackpressure()" not in r32:
    errors.append("R32 missing R30 facade for R13 ACK-backpressure telemetry")
if "R13NoteSafeAckBackpressure()" in r32:
    errors.append("R32 regained direct R13 ACK-backpressure telemetry dependency")
if "R30SupportOverlayReadyForTransport()" not in r32:
    errors.append("R32 missing R30 facade for R13 overlay readiness")
if "R13OverlayReadyForTransport()" in r32:
    errors.append("R32 regained direct R13 overlay-readiness dependency")
for retired in (
    "R13ReadGpuCompletedFrame(",
    "R13TryGetGpuCompletedFrame(",
):
    if retired in r13:
        errors.append(f"R13 retained retired per-slot ACK compatibility surface: {retired}")
    if retired in r32:
        errors.append(f"R32 regained retired per-slot ACK compatibility surface: {retired}")
if "R13ReadGpuCompletionSnapshotWithRebind(" not in r13:
    errors.append("R13 missing bounded ACK snapshot rebind owner")

for rel, source in (("R32", r32), ("R33", r33)):
    for banned in (
        "R31FastWorldDraws",
        "R31FastWorldLiveValidations",
        "R31FastWorldValidationRejects",
        "R31HudDraws",
        "R31Frame",
        "R31Window",
    ):
        if banned in source:
            errors.append(
                f"{rel} retained direct R31 telemetry state dependency: {banned}")

for marker in (
    "R31TelemetryNoteFastWorld()",
    "R31TelemetryNoteHud()",
    "R31TelemetryNoteFallback()",
    "R31TelemetryNoteUnstable()",
    "R31TelemetryNoteFragile()",
    "R31TelemetryResetFrameWindow()",
    "R31TelemetryFrameSnapshot()",
    "R31TelemetryLiveWvpChecks()",
    "R31TelemetryLiveWvpRejects()",
):
    if marker not in r31:
        errors.append(f"R31 missing owner telemetry API: {marker}")

for name, required in (
    ("R31TelemetryNoteFastWorld", ("++R31FastWorldDraws;", "++R31Frame.fastWorld;")),
    ("R31TelemetryNoteHud", ("++R31HudDraws;", "++R31Frame.hud;")),
):
    match = re.search(
        rf"inline void {name}\(\) noexcept\s*\{{(?P<body>.*?)\n        \}}",
        r31,
        re.DOTALL,
    )
    if not match:
        errors.append(f"R31 telemetry owner body missing: {name}")
        continue
    body = match.group("body")
    if f"{name}();" in body:
        errors.append(f"R31 telemetry owner recurses into itself: {name}")
    for required_marker in required:
        if required_marker not in body:
            errors.append(
                f"R31 telemetry owner missing counter update: {name} -> {required_marker}")

window_decl = r31.find("R31WindowPerf R31Window{};")
reset_window = r31.find("inline void R31TelemetryResetFrameWindow()")
if min(window_decl, reset_window) < 0 or not window_decl < reset_window:
    errors.append(
        "R31 telemetry reset API must be declared after the R31 window owner")

for banned in (
    "R31BlockedVerifiedGeneration =",
    "R31FastWorldCandidates =",
    "R31EyeCache =",
):
    if banned in r32:
        errors.append(
            f"R32 retained direct R31 reset-state ownership: {banned}")
    if banned in r33:
        errors.append(
            f"upper renderer retained direct R31 reset-state ownership: {banned}")

reset_fast = re.search(
    r"inline void R31ResetFastPathState\(\) noexcept\s*\{(?P<body>.*?)\n        \}",
    r31,
    re.DOTALL,
)
if not reset_fast:
    errors.append("R31 fast-path reset owner API missing")
else:
    reset_body = reset_fast.group("body")
    reset_order = [
        reset_body.find("R31BlockedVerifiedGeneration = 0;"),
        reset_body.find("R31FastWorldCandidates = 0;"),
        reset_body.find("R31EyeCache = {};"),
        reset_body.find("R31TelemetryResetFrameWindow();"),
    ]
    if min(reset_order) < 0 or reset_order != sorted(reset_order):
        errors.append(
            "R31 fast-path reset API must preserve blocked/candidate/eye/telemetry order")

if "R31SupportResetFastPathState();" not in r32:
    errors.append("R32 reset path missing R31 support reset API")

for banned, owner_api in (
    ("R29Effect = {};", "R30SupportInvalidateEffectStateCache();"),
    ("R23LastStateSampleDrawSerial = 0;", "R30SupportInvalidateLiveStateSample();"),
    ("R23LastStateSampleEpoch = 0;", "R30SupportInvalidateLiveStateSample();"),
):
    if banned in r32:
        errors.append(
            f"R32 retained lower-layer reset-state ownership: {banned}")
    if owner_api not in r32:
        errors.append(
            f"R32 reset path missing lower-layer owner API: {owner_api}")

for banned in ("R29Effect.", "R23GameDrawSerial"):
    if banned in r32:
        errors.append(
            f"R32 retained direct R29 effect telemetry dependency: {banned}")

for marker in (
    "struct R29EffectTelemetrySnapshot",
    "TryGetEffectTelemetrySnapshot(",
):
    if marker not in r29:
        errors.append(f"R29 missing effect telemetry owner API: {marker}")

if "TryGetEffectTelemetrySnapshot(effect)" not in r32:
    errors.append("R32 workload telemetry missing R29 owner snapshot API")

if "R22ShadowState =" in r33:
    errors.append("R33 final dispatcher retained direct R22 raster-shadow mutation")

for banned in ("R22ReplayScope", "R22FailClosedReplayState"):
    if banned in r33:
        errors.append(
            f"R33 final dispatcher retained private R22 raster-replay dependency: {banned}")
if "class R22RasterReplayGuard" not in r22:
    errors.append("R22 missing public raster-replay owner guard")
if "R22RasterReplayGuard replay(" not in r30:
    errors.append("R32 split facade missing R22 raster-replay owner guard delegation")
if "R32ReviewRunRasterReplayGuard(" not in r33:
    errors.append("R33 final dispatcher missing R32 raster-replay split facade")

if "R29ArmMonoSafety(" in r33:
    errors.append("R33 retained private R29 mono-safety helper dependency")
if "R32ReviewArmStereoRecoverySafety(" not in r33:
    errors.append("R33 missing R32 review facade for stereo-recovery safety API")
for banned in ("R29ArmMonoSafety(", "R29MonoSafetyThroughEpoch"):
    if banned in r32:
        errors.append(
            f"R32 retained private R29 recovery-safety dependency: {banned}")
if "void R32ReviewArmStereoRecoverySafety(std::uint64_t n) noexcept { ArmStereoRecoverySafety(n); }" not in r32:
    errors.append(
        "R32 split facade must delegate final-draw recovery-safety arming to the lower owner API")
if "SetStereoRecoverySafetyThroughEpoch(" not in r32:
    errors.append(
        "R32 missing exact-epoch R29 recovery-safety owner API")
if "SetStereoRecoverySafetyThroughEpoch(" not in r29:
    errors.append("R29 missing exact-epoch recovery-safety owner API")

for marker, source, owner in (
    ("R9InstallStatus()", r9, "R9"),
    ("R13InstallStatus()", r13, "R13"),
    ("R20InstallStatus()", r20, "R20"),
    ("R21InstallStatus()", r21, "R21"),
):
    if marker not in source:
        errors.append(f"{owner} missing install-state owner query API: {marker}")

for rel, source in (("R20", r20), ("R21", r21), ("R23", r23)):
    for banned in ("R9InstallState", "R9InstallReady", "R9InstallFailed",
                   "R13InstallState", "R13InstallReady", "R13InstallFailed"):
        if banned in source:
            errors.append(
                f"{rel} retained direct lower install-state dependency: {banned}")
for rel, source in (("R21", r21), ("R23", r23)):
    if "R20InstallState" in source:
        errors.append(f"{rel} retained direct R20 install-state dependency")
if "R21InstallState" in r23:
    errors.append("R23 retained direct R21 install-state dependency")
if "R22InstallState" in r23:
    errors.append("R23 retained direct R22 install-state dependency")

for marker in ("R9InstallStatus()", "R13InstallStatus()",
               "R20InstallStatus()", "R21InstallStatus()", "R22InstallStatus()"):
    if marker not in r23:
        errors.append(f"R23 missing prerequisite install owner query: {marker}")

# R32 is hook-free and no longer owns an async install/status relay. R33 must
# consume the real lower prerequisite owner APIs directly before installing the
# final Reset/Present/DirectGPU/draw transaction.
for retired in (
    "R32InstallState",
    "R32InstallThread",
    "VRStereoR32ReviewHook",
    "R32InstallStatus()",
    "OpenXRVRStereoR32Review",
):
    if retired in r32:
        errors.append(f"R32 retained retired async install/status shim: {retired}")

for marker, source, owner in (
    ("R13InstallStatus()", r13, "R13"),
    ("R22InstallStatus()", r22, "R22"),
    ("R31InstallStatus()", r31, "R31"),
):
    if marker not in source:
        errors.append(f"{owner} missing install-state owner query API: {marker}")
# R84 source split relocated R13/R22 install-state reads behind R30's
# lower-owned aggregation. R32 must depend only on that aggregation and R31.
def r30_lower_prerequisite_aggregation_ok(api, lower, upper):
    match = re.search(
        r"R30SupportLowerPrerequisiteStatus\(\) noexcept\s*\{(.*?)\n    \}",
        lower, re.DOTALL)
    if not match:
        return False
    body = match.group(1)
    return all((
        "R30SupportLowerPrerequisiteStatus() noexcept;" in api,
        "const auto r22 = R22InstallStatus();" in body,
        "const auto r13 = R13InstallStatus();" in body,
        "if (r22 == State::Failed || r13 == R13InstallStatusValue::Failed)" in body,
        "return State::Failed;" in body,
        "if (r22 == State::Ready && r13 == R13InstallStatusValue::Ready)" in body,
        "return State::Ready;" in body,
        "return State::Pending;" in body,
        "const auto r31 = R31SupportInstallStatus();" in upper,
        "const auto lower = R30SupportLowerPrerequisiteStatus();" in upper,
        "if (r31 == State::Failed || lower == State::Failed) return State::Failed;" in upper,
        "if (r31 == State::Ready && lower == State::Ready) return State::Ready;" in upper,
    ))

if not r30_lower_prerequisite_aggregation_ok(r30_support_api, r30, r32):
    errors.append("R30/R32 lower prerequisite owner aggregation lost fail-closed semantics")

for label, changed_r30, changed_r32 in (
    ("R13 failed prerequisite ignored", r30.replace(
        "r22 == State::Failed || r13 == R13InstallStatusValue::Failed",
        "r22 == State::Failed", 1), r32),
    ("R22 failed prerequisite ignored", r30.replace(
        "r22 == State::Failed || r13 == R13InstallStatusValue::Failed",
        "r13 == R13InstallStatusValue::Failed", 1), r32),
    ("R13 ready state forced", r30.replace(
        "r22 == State::Ready && r13 == R13InstallStatusValue::Ready",
        "r22 == State::Ready", 1), r32),
    ("R31 failed prerequisite ignored", r30, r32.replace(
        "r31 == State::Failed || lower == State::Failed",
        "lower == State::Failed", 1)),
    ("R32 lower owner bypass", r30, r32.replace(
        "const auto lower = R30SupportLowerPrerequisiteStatus();",
        "const auto lower = State::Ready;", 1)),
):
    if changed_r30 == r30 and changed_r32 == r32:
        errors.append("R84 prerequisite negative mutation not applied: " + label)
    elif r30_lower_prerequisite_aggregation_ok(
            r30_support_api, changed_r30, changed_r32):
        errors.append("R84 prerequisite negative mutation survived: " + label)
if "R32ReviewPrerequisiteStatus()" not in r33:
    errors.append("R33 missing R32 split facade prerequisite query")

for banned in (
    "R13InstallState", "R13InstallReady", "R13InstallFailed",
    "R22InstallState", "R31InstallState", "R32InstallState",
    "R32InstallStatus()",
):
    if banned in r33:
        errors.append(f"R33 retained direct/retired prerequisite state dependency: {banned}")
if "R33InstallStatus()" in r33:
    errors.append("R33 retained obsolete compatibility-only install-status observer API")
if "R33InstallState" in r33:
    errors.append("R33 retained write-only final install state after observer retirement")

# Post-1100 DirectGPU-owner flattening: R32 keeps transport/fence/ACK semantics
# as a hook-free helper while R33 owns the physical hook over the R13 transport
# callback and wraps its trampoline with the R32 owner helper.
for banned in (
    "SafetyHookInline R32ResolveDirectR13Hook{};",
    "ResolveDirectTransportR32(",
    "safetyhook::create_inline(",
):
    if banned in r32:
        errors.append(f"R32 retained retired physical DirectGPU ownership: {banned}")
for marker in (
    "bool R32ResolveDirectTransport(",
    "R30SupportOverlayReadyForTransport()",
    "return lowerResolve();",
    "R32EnsureDirectResources(device)",
    "std::uint32_t selected = OutRunVR::RenderFrameRingSize;",
    "R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)",
    "DirectTransportFrameReadyAfterPresent() is",
    "R30SupportMarkDirectTransportSlotPending(selected, frameId);",
    "R30SupportSetActiveDirectTransportSlot(selected);",
):
    if marker not in r32:
        errors.append(f"R32 missing hook-free DirectGPU owner contract: {marker}")
resolve_r32_start = r32.find("bool R32ResolveDirectTransport(")
resolve_r32_end = r32.find("void R32InvalidateResetCaches() noexcept", resolve_r32_start)
if min(resolve_r32_start, resolve_r32_end) < 0:
    errors.append("R32 DirectGPU owner helper boundaries unavailable")
else:
    resolve_r32 = r32[resolve_r32_start:resolve_r32_end]
    for banned in (
        "R32WaitProducerFence(slot.fence)",
        "R32ProducerFencePending[selected] = true;",
        "R32ProducerPendingFrame[selected] = frameId;",
    ):
        if banned in resolve_r32:
            errors.append(f"R32 retained redundant pre-Present fence wait state: {banned}")

for marker in (
    "SafetyHookInline R33ResolveDirectR13Hook{};",
    "R32ReviewDirectTransportTarget()",
    "ResolveDirectTransportDestR33",
    "R32ReviewResolveDirectTransport(",
    "R33ResolveDirectR13Hook.call<bool>",
):
    if marker not in r33:
        errors.append(f"R33 missing final DirectGPU hook contract: {marker}")
for banned in (
    "R32ResolveDirectR13Hook",
    "ResolveDirectTransportR32",
):
    if banned in r33:
        errors.append(f"R33 retained retired R32 physical DirectGPU symbol: {banned}")

# Post-1100 Reset-owner flattening: R32 keeps the corrected reset lifecycle
# semantics but no longer owns a physical Reset hook. R33 hooks R22 Reset
# directly and wraps that lower call with the R32 lifecycle owner helper.
for banned in (
    "SafetyHookInline R32ResetR22Hook{};",
    "HRESULT __stdcall ResetDestR32(",
    "reinterpret_cast<void*>(&ResetDestR22), ResetDestR32",
):
    if banned in r32:
        errors.append(f"R32 retained retired physical Reset ownership: {banned}")
for marker in (
    "HRESULT R32WithResetLifecycle(",
    "const HRESULT hr = lowerReset();",
    "R32ResetAfterGameReset();",
    "R32InvalidateResetCaches();",
    "++R32ResetFailures",
):
    if marker not in r32:
        errors.append(f"R32 missing Reset lifecycle owner contract: {marker}")
for marker in (
    "SafetyHookInline R33ResetR22Hook{};",
    "R32ReviewResetTarget()",
    "R32ReviewRunResetLifecycle(",
    "R33ResetR22Hook.stdcall<HRESULT>",
):
    if marker not in r33:
        errors.append(f"R33 missing direct Reset owner contract: {marker}")
for banned in (
    "R33ResetR32Hook",
    "reinterpret_cast<void*>(&ResetDestR32)",
):
    if banned in r33:
        errors.append(f"R33 retained retired R32 Reset chain: {banned}")

# Post-1100 Present-owner flattening: R32 keeps telemetry semantics but no
# longer owns a physical Present hook. R33 hooks R13 Present directly and wraps
# that lower call with the R32 telemetry owner helper.
for banned in (
    "SafetyHookInline R32PresentR13Hook{};",
    "HRESULT __stdcall PresentDestR32(",
    "reinterpret_cast<void*>(&PresentDestR13), PresentDestR32",
):
    if banned in r32:
        errors.append(f"R32 retained retired physical Present ownership: {banned}")
for marker in (
    "HRESULT R32WithPresentTelemetry(",
    "const HRESULT hr = lowerPresent();",
    "R32FinalizeFramePerf(",
    "R32LogPerfWindow()",
):
    if marker not in r32:
        errors.append(f"R32 missing Present telemetry owner contract: {marker}")
for marker in (
    "SafetyHookInline R33PresentR13Hook{};",
    "R32ReviewPresentTarget()",
    "R32ReviewRunPresentTelemetry(",
    "R33PresentR13Hook.stdcall<HRESULT>",
):
    if marker not in r33:
        errors.append(f"R33 missing direct Present owner contract: {marker}")
for banned in (
    "R33PresentR32Hook",
    "reinterpret_cast<void*>(&PresentDestR32)",
):
    if banned in r33:
        errors.append(f"R33 retained retired R32 Present chain: {banned}")

# Post-1000 hook-chain flattening: all former R34 runtime responsibilities are
# owned by R33. The source shim and historical R34 compatibility Hook/status
# alias are both retired and must stay absent.
for marker in (
    "R33GuardStereoRasterState(",
    "R33SynchronizeResetReplayGuardState(",
    "R33ReportInstallResult(",
    "R33ResetReplayBlocked",
    "LastResetStateReplaySucceeded()",
    "TestCooperativeLevel()",
    "R32ReviewTryXyzrhwPrimitiveVB(",
    "R32ReviewTryXyzrhwIndexedPrimitiveVB(",
    "R32ReviewTryXyzrhwPrimitiveUP(",
    "R32ReviewTryXyzrhwIndexedPrimitiveUP(",
):
    if marker not in r33:
        errors.append(f"R33 missing folded final-dispatch responsibility: {marker}")

for banned in (
    "class VRStereoR34ResetGuardHook",
    "OpenXRVRStereoR34ResetGuard",
    "R33InstallStatus()",
):
    if banned in r33:
        errors.append(
            f"R33 retained retired R34 compatibility observer/status alias: {banned}")

# Post-1000 successor: after the R34 shim retirement, the normal full-chain
# build must compile R33 directly. Comparison modes may disable R33 in favor of
# their isolated owner, but R34 must never become a compiled stereo owner again.
post_review = re.search(
    r"set\(OUTRUN_VR_POST_REVIEW_FINAL_TUS(?P<body>.*?)\)",
    cmake,
    re.DOTALL,
)
if not post_review:
    errors.append("CMake post-review final-TU list missing")
else:
    body = post_review.group("body")
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in body:
        errors.append("CMake full-chain final TU must terminate directly at R33")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in body:
        errors.append("CMake retained R34 shim as post-review compiled final TU")

if "src/vr/d3d9/stereo_renderer_r34.cpp" in cmake:
    errors.append("CMake retained retired R34 source shim")

owners = re.search(
    r"set\(_vr_stereo_owner_candidates(?P<body>.*?)\)",
    cmake,
    re.DOTALL,
)
if not owners:
    errors.append("CMake stereo-owner candidate list missing")
else:
    body = owners.group("body")
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in body:
        errors.append("CMake stereo-owner candidates missing R33 final dispatcher")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in body:
        errors.append("CMake stereo-owner candidates still include R34 shim")

for option in (
    "OUTRUN_VR_SAFE_DRAW_COMPARE",
    "OUTRUN_VR_R26_HUD_COMPARE",
    "OUTRUN_VR_C1_COMPARE OR OUTRUN_VR_C2_COMPARE",
):
    start = cmake.find(f"if({option})")
    end = cmake.find("endif()", start)
    if start < 0 or end <= start:
        errors.append(f"CMake comparison block missing: {option}")
        continue
    block = cmake[start:end]
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in block:
        errors.append(f"CMake comparison block must disable R33 final owner: {option}")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in block:
        errors.append(f"CMake comparison block still toggles obsolete R34 shim owner: {option}")

# CMakeLists.txt is generated from cmake.toml. Guard the generator source too
# so cmkr cannot silently restore R34 as the compiled stereo owner.
generator_post_review = re.search(
    r"set\(OUTRUN_VR_POST_REVIEW_FINAL_TUS(?P<body>.*?)\)",
    cmake_toml, re.DOTALL)
if not generator_post_review:
    errors.append("cmake.toml post-review final-TU list missing")
else:
    body = generator_post_review.group("body")
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in body:
        errors.append("cmake.toml full-chain final TU must terminate directly at R33")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in body:
        errors.append("cmake.toml retained R34 shim as post-review compiled final TU")
if "src/vr/d3d9/stereo_renderer_r34.cpp" in cmake_toml:
    errors.append("cmake.toml retained retired R34 source shim")
generator_owners = re.search(
    r"set\(_vr_stereo_owner_candidates(?P<body>.*?)\)", cmake_toml, re.DOTALL)
if not generator_owners:
    errors.append("cmake.toml stereo-owner candidate list missing")
else:
    body = generator_owners.group("body")
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in body:
        errors.append("cmake.toml stereo-owner candidates missing R33 final dispatcher")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in body:
        errors.append("cmake.toml stereo-owner candidates still include R34 shim")
for option in ("OUTRUN_VR_SAFE_DRAW_COMPARE", "OUTRUN_VR_R26_HUD_COMPARE",
               "OUTRUN_VR_C1_COMPARE OR OUTRUN_VR_C2_COMPARE"):
    start = cmake_toml.find(f"if({option})")
    end = cmake_toml.find("endif()", start)
    if start < 0 or end <= start:
        errors.append(f"cmake.toml comparison block missing: {option}")
        continue
    owner_block = cmake_toml[start:end]
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in owner_block:
        errors.append(f"cmake.toml comparison block must disable R33 final owner: {option}")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in owner_block:
        errors.append(f"cmake.toml comparison block still toggles obsolete R34 shim owner: {option}")

for banned in ("R22FailClosedEligibility();", "R22ResetBaselineTracking();"):
    if banned in r33:
        errors.append(f"R33 retained direct R22 reset fail-close primitive: {banned}")
if "FailClosedResetBaselineState();" not in r33:
    errors.append("R33 missing consolidated R22 reset fail-close owner API")

if "FailClosedDepthStencilState();" not in r33:
    errors.append("R33 final dispatcher missing consolidated depth/stencil owner API")

install_start = r33.find("DWORD WINAPI R33InstallThread(")
install_end = r33.find("class VRStereoR33DispatchHook", install_start)
if install_start < 0 or install_end <= install_start:
    errors.append("R33 install transaction body missing")
else:
    install_body = r33[install_start:install_end]
    prerequisite_facade = install_body.find(
        "const auto prerequisites = R32ReviewPrerequisiteStatus();")
    if prerequisite_facade < 0:
        errors.append("R33 must query lower prerequisite readiness through the R32 split facade")
    for retired in ("R32InstallStatus()", "R32InstallState"):
        if retired in install_body:
            errors.append(f"R33 install retained retired R32 readiness relay: {retired}")
    for marker in (
        "prerequisites == State::Failed",
        "prerequisites == State::Ready",
    ):
        if marker not in install_body:
            errors.append(f"R33 install missing direct prerequisite gate: {marker}")
    sync_pos = install_body.find(
        "R33SynchronizeResetReplayGuardState(installedDevice)")
    publish_pos = install_body.find(
        "R33ReportInstallResult(true)", sync_pos)
    if min(sync_pos, publish_pos) < 0 or not (sync_pos < publish_pos):
        errors.append(
            "R33 must synchronize replay-health before terminal publication")


fail_closed_depth = re.search(
    r"inline void FailClosedDepthStencilState\(\) noexcept\s*\{(?P<body>.*?)\n    \}",
    r33,
    re.DOTALL,
)
if not fail_closed_depth:
    errors.append("R33 consolidated depth/stencil fail-close owner API missing")
else:
    depth_body = fail_closed_depth.group("body")
    depth_order = [
        depth_body.find("R33InvalidateDepthStencilCache();"),
        depth_body.find("R32ReviewInvalidateRightDepthStencilSync(true, true);"),
    ]
    if min(depth_order) < 0 or depth_order != sorted(depth_order):
        errors.append(
            "R33 depth/stencil fail-close API must preserve cache then R9 sync invalidation order")

fail_closed_reset = re.search(
    r"inline void FailClosedResetBaselineState\(\) noexcept\s*\{(?P<body>.*?)\n    \}",
    r22,
    re.DOTALL,
)
if not fail_closed_reset:
    errors.append("R22 consolidated reset fail-close owner API missing")
else:
    fail_closed_body = fail_closed_reset.group("body")
    fail_closed_order = [
        fail_closed_body.find("R22FailClosedEligibility();"),
        fail_closed_body.find("R22ResetBaselineTracking();"),
        fail_closed_body.find("InvalidateTrackedRasterShadow();"),
    ]
    if min(fail_closed_order) < 0 or fail_closed_order != sorted(fail_closed_order):
        errors.append(
            "R22 reset fail-close owner API must preserve eligibility/baseline/raster order")

if "R31FlushPendingStateBlockResync" in r33:
    errors.append("R33 regained R31 StateBlock resync execution dependency")
if "StateBlockRecovery::FlushPendingResync(device)" not in r33:
    errors.append("R33 missing neutral StateBlock recovery boundary")
if "StateBlockRecovery::Configure(" not in r31:
    errors.append("R31 missing neutral StateBlock recovery callback registration")
if "StateBlockEvents::Configure(" not in r31:
    errors.append("R31 missing neutral StateBlock event callback registration")
coverage_reset = r31.find("StateBlockTracker::ResetCoverageLoss()")
event_configure = r31.find("StateBlockEvents::Configure(")
if min(coverage_reset, event_configure) < 0 or not coverage_reset < event_configure:
    errors.append(
        "R31 must reset stale coverage before publishing StateBlock event callbacks")
for marker in (
    "StateBlockEvents::NotifyBegin(device)",
    "StateBlockEvents::NotifyEnd(device, hr)",
    "StateBlockEvents::NotifyApply(device, hr)",
):
    if marker not in r22:
        errors.append(f"R22 StateBlock owner missing neutral event dispatch: {marker}")
    if marker in r31:
        errors.append(f"R31 regained physical StateBlock event dispatch: {marker}")

if "StateBlockTracker::LifecycleHooksReady()" not in r31:
    errors.append("R31 missing R22 StateBlock lifecycle-coverage gate")
if "R22 lifecycle hooks are authoritative; R31 is event-consumer only" not in r31:
    errors.append("R31 missing authoritative R22 lifecycle-owner path")
if "R31 physical StateBlock fallback retired; fast-path trust remains disabled" not in r31:
    errors.append("R31 missing fail-closed no-fallback lifecycle path")
for banned in (
    "R31CreateStateBlockHook",
    "R31BeginStateBlockHook",
    "R31EndStateBlockHook",
    "R31StateBlockApplyHook",
    "R31StateBlockApplyTarget",
    "StateBlockApplyDestR31(",
    "R31EnsureStateBlockApplyHook(",
    "CreateStateBlockDestR31(",
    "BeginStateBlockDestR31(",
    "EndStateBlockDestR31(",
):
    if banned in r31:
        errors.append(f"R31 retained retired physical StateBlock ownership: {banned}")
if "StateBlockTracker::SetEventConsumerReady(" not in r31 or \
        "StateBlockEvents::Configured()" not in r31:
    errors.append("R31 missing neutral event-consumer readiness publication")
install_start = r31.find("DWORD WINAPI R31InstallThread(")
install_end = r31.find("class VRStereoR31PerfHook", install_start)
if install_start < 0 or install_end <= install_start:
    errors.append("R31 install transaction body missing")
else:
    install_body = r31[install_start:install_end]
    recovery_configure_pos = install_body.find("StateBlockRecovery::Configure(")
    configure_pos = install_body.find("StateBlockEvents::Configure(")
    lifecycle_owner_pos = install_body.find("const bool lifecycleReady =")
    degraded_log_pos = install_body.find(
        "R31 physical StateBlock fallback retired; fast-path trust remains disabled")
    coverage_degrade_pos = install_body.rfind(
        "StateBlockTracker::MarkCoverageLost()", 0, degraded_log_pos)
    consumer_ready_pos = install_body.find("StateBlockTracker::SetEventConsumerReady(true)")
    ready_pos = install_body.find("R31InstallState.store(State::Ready", consumer_ready_pos)
    if min(recovery_configure_pos, configure_pos, lifecycle_owner_pos,
            coverage_degrade_pos, degraded_log_pos,
            consumer_ready_pos, ready_pos) < 0 or not (
            recovery_configure_pos < configure_pos < lifecycle_owner_pos <
            coverage_degrade_pos < degraded_log_pos <
            consumer_ready_pos < ready_pos):
        errors.append(
            "R31 must configure StateBlock consumers, fail closed without R22 "
            "lifecycle coverage, then publish readiness")

    if "safetyhook::create_inline(" in install_body:
        errors.append("R31 install regained physical hook creation after retirement")

    fail_start = install_body.find("const auto failInstall =")
    fail_end = install_body.find(
        "                    };\n\n                    OutRunVR::State::StateBlockTracker::SetEventConsumerReady(false)",
        fail_start)
    if fail_start < 0 or fail_end <= fail_start:
        errors.append("R31 install rollback boundary missing")
    else:
        fail_body = install_body[fail_start:fail_end]
        order = [
            fail_body.find("StateBlockTracker::SetEventConsumerReady(false)"),
            fail_body.find("StateBlockEvents::Clear()"),
            fail_body.find("StateBlockRecovery::Clear()"),
            fail_body.find("StateBlockTracker::MarkCoverageLost()"),
            fail_body.find("R31InstallState.store(State::Failed"),
        ]
        if min(order) < 0 or order != sorted(order):
            errors.append(
                "R31 rollback must withdraw readiness, event/recovery callbacks, "
                "mark coverage lost, then fail closed")
if "StateBlockEvents::Clear()" not in r31:
    errors.append("R31 failure path missing StateBlock event rollback")

dirty_match = re.search(
    r"void R31MarkStateBlockCachesDirty\(\) noexcept\s*\{(?P<body>.*?)\n        \}",
    r31,
    re.DOTALL,
)
if not dirty_match:
    errors.append("R31 StateBlock cache-dirty boundary missing")
elif "StateBlockRecovery::Configure(" in dirty_match.group("body"):
    errors.append(
        "R31 StateBlock recovery callbacks must be configured once at install, "
        "not rewritten on every lifecycle event")
if "SetR31Reliable" in state_block_tracker or "R31Reliable" in state_block_tracker:
    errors.append("StateBlockTracker retained obsolete R31 reliability naming")
if "SetR31Reliable" in r31 or "R31Reliable" in r31:
    errors.append("R31 retained obsolete overloaded StateBlock reliability producer")

r22_apply_owner = re.search(
    r"bool R22EnsureStateBlockApplyHook\(.*?\n        \}",
    r22,
    re.DOTALL,
)
if not r22_apply_owner:
    errors.append("R22 shared StateBlock Apply hook owner body missing")
elif "StateBlockTracker::MarkCoverageLost()" not in r22_apply_owner.group(0):
    errors.append(
        "R22 shared StateBlock Apply owner must preserve coverage-loss semantics")

if "R31FlushPendingStateBlockResync" in r31:
    errors.append("R31 retained obsolete StateBlock resync execution wrapper")

for rel, source in (("R31", r31), ("R32", r32), ("R33", r33)):
    if "R31StateBlockRecording" in source:
        errors.append(
            f"{rel} regained R31 StateBlock recording-state dependency")

for banned in ("IsGameStateBlockRecording", "IsStateBlockTrackingReliable"):
    if banned in r31:
        errors.append(f"R31 retained obsolete StateBlock status export: {banned}")
    if banned in renderer_r29:
        errors.append(f"renderer R29 retained stereo StateBlock status dependency: {banned}")

for marker in ("StateBlockTracker::Recording()", "StateBlockTracker::Reliable()"):
    if marker not in renderer_r29:
        errors.append(f"renderer R29 missing neutral StateBlock status access: {marker}")

# Terminal post-R34/R33 closure: the generic OpenXR hardening workflow must
# describe the current final-dispatch/teardown contracts, not historical
# physical-hook/status symbols retired by the completed flattening chain.
for retired in (
    "IsFailed(R20InstallState)",
    "IsFailed(R22InstallState)",
    "R31StateBlockTrackingReliable",
    "R31 fast left-eye c64 rollback",
    "R32ResetR22Hook",
    "'ResetDestR22'",
    "VR R32 REVIEW2",
    "R30DrawPrimitiveR29Hook",
    "R33ResetR32Hook.stdcall<HRESULT>",
    "Preserve acquiredImage",
    "'Release(Projection);'",
    "'Release(Theater);'",
):
    if retired in vr_openxr_workflow:
        errors.append(
            f"generic OpenXR hardening workflow retained retired marker: {retired}")

for marker in (
    "R20InstallStatus()",
    "R21InstallStatus()",
    "R22InstallStatus()",
    "StateBlockTracker::LifecycleHooksReady()",
    "StateBlockTracker::SetEventConsumerReady(true)",
    "R31 physical StateBlock fallback retired; fast-path trust remains disabled",
    "R32WithResetLifecycle",
    "R32WithPresentTelemetry",
    "R32ResolveDirectTransport",
    "R32 is a hook-free functional owner",
    "R33DrawPrimitiveR30Hook",
    "R33ResetR22Hook.stdcall<HRESULT>",
    "R33PresentR13Hook.stdcall<HRESULT>",
    "R33ResolveDirectR13Hook.call<bool>",
    "direct R31/R22/R13 prerequisite ownership",
    "PrepareForParentSessionDestroy()",
    "ForgetAfterParentSessionDestroy()",
    "Projection.PrepareForParentSessionDestroy();",
    "Theater.PrepareForParentSessionDestroy();",
    "Projection.ForgetAfterParentSessionDestroy();",
    "Theater.ForgetAfterParentSessionDestroy();",
):
    if marker not in vr_openxr_workflow:
        errors.append(
            f"generic OpenXR hardening workflow missing terminal marker: {marker}")

r23_guard_start = vr_openxr_workflow.find(
    "'vrhost/src/runtime/r23_runtime_hardening.hpp' = @(")
r23_guard_end = vr_openxr_workflow.find(
    "'vrhost/src/runtime/d3d9ex_direct_passthrough_r32.hpp' = @(",
    r23_guard_start)
if r23_guard_start < 0 or r23_guard_end <= r23_guard_start:
    errors.append("generic OpenXR R23 host hardening marker block missing")
else:
    r23_guard_block = vr_openxr_workflow[r23_guard_start:r23_guard_end]
    if "'SafeTransportGeneration'" in r23_guard_block:
        errors.append(
            "generic OpenXR R23 host hardening retained obsolete transport-generation marker")
    for marker in (
        "ExpectedDirectDxgiFormat",
        "DirectSafeEyeMatchesCommittedFrame",
        "SafeEyesOwnFrame(frame)",
        "EnsureSafeFrame(frame.frameId)",
    ):
        if marker not in r23_guard_block:
            errors.append(
                f"generic OpenXR R23 host hardening missing current marker: {marker}")

for marker in (
    "ExpectedDirectDxgiFormat",
    "DirectSafeEyeMatchesCommittedFrame",
    "SafeEyesOwnFrame(frame)",
    "EnsureSafeFrame(frame.frameId)",
):
    if marker not in r23_runtime_hardening:
        errors.append(f"R23 runtime hardening missing current safe-eye marker: {marker}")

for marker in (
    "bool PrepareForParentSessionDestroy() noexcept",
    "void ForgetAfterParentSessionDestroy() noexcept",
    "Projection.PrepareForParentSessionDestroy();",
    "Theater.PrepareForParentSessionDestroy();",
    "Projection.ForgetAfterParentSessionDestroy();",
    "Theater.ForgetAfterParentSessionDestroy();",
    "xrDestroySession destroys child swapchains/spaces",
):
    if marker not in sbs_capture_override:
        errors.append(f"SBS teardown contract missing current marker: {marker}")

misplaced_tracker = ROOT / "src/vr/d3d9/state/state_block_tracker.hpp"
if misplaced_tracker.exists():
    errors.append(
        "misplaced legacy StateBlockTracker copy still exists under src/vr/d3d9/state")

for p in (ROOT / "src/vr/d3d9").glob("stereo_renderer_r*.cpp"):
    m = re.fullmatch(r"stereo_renderer_r(\d+)\.cpp", p.name)
    if m and int(m.group(1)) > 34:
        errors.append(f"new legacy R overlay forbidden during flattening: {p.name}")

if errors:
    print("VR refactor contract FAILED", file=sys.stderr)
    for error in errors:
        print(f" - {error}", file=sys.stderr)
    raise SystemExit(1)

print("VR refactor contract PASS")
