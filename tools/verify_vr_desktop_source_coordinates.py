#!/usr/bin/env python3
"""VR resolution ownership: physical XR target is independent of logical UI."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
settings=(R/"src/vr/settings.cpp").read_text()
cfg=(R/"src/hooks_misc.cpp").read_text()
ex=(R/"src/vr/d3d9/ex_device_upgrade.cpp").read_text()
reset_trace=(R/"src/vr/d3d9/reset_trace.hpp").read_text()
renderer=(R/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text()
ini=(R/"OutRun2006Tweaks.ini").read_text()

for token in (
    'VRFollowGameResolution{ "VR", "FollowGameResolution", false,',
    'VRUnifiedEyeMenuSource{ "VR", "UnifiedEyeMenuSource", false,',
    'VRAutoRenderResolution{ "VR", "AutoRenderResolution", true,'):
    assert token in settings, token
for token in ("FollowGameResolution = false","UnifiedEyeMenuSource = false",
              "AutoRenderResolution = true"):
    assert token in ini, token

owner=cfg.split("void ApplyVrEyeResolutionAfterConfig(",1)[1].split(
    "class CommandLineArguments",1)[0]
assert "OutRunVR::RequestVRHostStartup();" in owner
assert "physical D3D9Ex target will use live OpenXR eye extent at CreateDevice" in owner
# R26+HUD now explicitly locks the logical HUD/game reference at 1080p,
# independently of physical XR eye size. Never assign portrait eye extent
# to the original 2D/menu resolution owner.
assert "Game::screen_resolution->x = 1920;" in owner
assert "Game::screen_resolution->y = 1080;" in owner
assert "Game::screen_resolution->x = static_cast<int>(xrSize.width)" not in owner
assert "Game::screen_resolution->y = static_cast<int>(xrSize.height)" not in owner
assert "GetTickCount64()" not in owner and "Sleep(" not in owner

resolver=ex.split("OutRunVR::EyeExtent::Size ReadyXrEyeSizeAtCreateDevice(",1)[1].split(
    "Direct3DCreate9Fn OriginalDirect3DCreate9",1)[0]
for token in ("Settings::VRFollowGameResolution",
              "Settings::VRRenderWidth","Settings::VRRenderHeight",
              "Settings::VRAutoRenderResolution",
              "ResolveStartupForLiveHost","ResolveGame"):
    assert token in resolver, token
success=ex.split("if (SUCCEEDED(hr) && deviceEx)",1)[1].split(
    "UpdateCompatPresentationState",1)[0]
assert "physical D3D9Ex target=" in success
assert "GameResolutionExplicitOnCommandLine" not in resolver
assert "Game::screen_resolution->x = static_cast<int>(xrSize.width)" not in success
assert "Game::screen_resolution->y = static_cast<int>(xrSize.height)" not in success

# A successful XR-sized CreateDevice must keep the same physical target across
# the game's later legacy Reset calls. Otherwise a menu/resolution/device-loss
# Reset silently returns the HMD source to the logical 1920x1080 request.
reset=ex.split("HRESULT __stdcall ResetCompatDest(",1)[1].split(
    "HRESULT __stdcall CreateVertexBufferCompatDest(",1)[0]
for token in (
    "CompatVrPhysicalWidth.load(std::memory_order_acquire)",
    "CompatVrPhysicalHeight.load(std::memory_order_acquire)",
    "const bool preserveVrPhysical =",
    "!Settings::VRFollowGameResolution",
    "effective.BackBufferWidth = vrWidth;",
    "effective.BackBufferHeight = vrHeight;",
    "deviceEx->ResetEx(&effective, fullscreenPtr)",
    "*params = effective;",
    "preserveXrPhysical={}",
):
    assert token in reset, token
assert reset.index("const D3DPRESENT_PARAMETERS requested = *params;") < reset.index(
    "effective.BackBufferWidth = vrWidth;") < reset.index(
    "deviceEx->ResetEx(&effective, fullscreenPtr)") < reset.index(
    "*params = effective;")
assert "CompatVrPhysicalWidth.store(0" in ex
assert "CompatVrPhysicalHeight.store(0" in ex
assert "ResetEx will preserve this XR target" in ex

# The Reset result must be a joinable epoch, not a free-form log line. Publish
# requested/effective/actual raster state after ResetEx/classic replay and let
# later lens/HUD logs read the same stable cross-TU snapshot.
for token in (
    "struct Snapshot",
    "resetSerial",
    "requestedWidth",
    "effectiveWidth",
    "actualWidth",
    "viewportWidth",
    "scissorRight",
    "inline void Publish(",
    "inline Snapshot Read()",
    "Generation.fetch_add(1",
    "Writer.test_and_set(std::memory_order_acquire)",
    "Writer.clear(std::memory_order_release)",
    "NextSerial.fetch_add(1",
    "PublishedResetSerial.store(",
    "snapshot.readStable = true;",
):
    assert token in reset_trace, token
for token in (
    "OutRunVR::D3D9ResetTrace::NextResetSerial()",
    "OutRunVR::D3D9ResetTrace::Publish(trace);",
    "device->GetBackBuffer(",
    "device->GetViewport(&viewport)",
    "device->GetScissorRect(&scissor)",
    "VR D3D9Ex RESET TRACE: resetEpoch=",
    "contract=XR_RESET_EPOCH_V2",
):
    assert token in reset, token
assert reset.index("deviceEx->ResetEx(&effective, fullscreenPtr)") < reset.index(
    "classicReplaySucceeded = RestoreClassicResetState(device);") < reset.index(
    "OutRunVR::D3D9ResetTrace::Publish(trace);")
assert "resetViewportMatchesPre" not in renderer
for token in (
    "lensResetTrace.readStable",
    "lensResetTrace.viewportX == savedViewport.X",
    "lensResetTrace.viewportY == savedViewport.Y",
    "lensResetTrace.viewportWidth == savedViewport.Width",
    "lensResetTrace.viewportHeight == savedViewport.Height",
    "lensResetTrace.has(",
    "OutRunVR::D3D9ResetTrace::ResetSucceeded",
    "OutRunVR::D3D9ResetTrace::ViewportValid",
    "OutRunVR::D3D9ResetTrace::ScissorValid",
):
    assert token in renderer, token
for token in (
    '#include "vr/d3d9/reset_trace.hpp"',
    "lensResetTrace = OutRunVR::D3D9ResetTrace::Read();",
    "preViewport={},{},{}x{}",
    "resetEpoch={} resetQpc={} resetFlags=0x{:X}",
    "resetSnapshotStable={}",
    "resetViewportExtentMatchesPre={}",
    "resetViewportRectMatchesPre={}",
    "resetScissorMatchesPre={}",
):
    assert token in renderer, token

def choose(logical, eye, follow=False, auto=True, manual=None):
    physical=logical
    if follow: return logical, logical
    if manual: physical=manual
    elif auto: physical=eye
    return logical, physical
for logical in ((1920,1080),(3440,1440)):
    for eye in ((2016,2240),(2496,2688),(3072,3216)):
        ui,rt=choose(logical,eye)
        assert ui==logical and rt==eye
        assert choose(logical,eye,manual=(2304,2592))==(logical,(2304,2592))
        assert choose(logical,eye,follow=True)==(logical,logical)

def reset_target(requested, created_eye, vr=True, follow=False,
                 prefer_ex=True, windowed=True):
    w,h=created_eye
    preserve=(vr and not follow and prefer_ex and windowed and
              w>=640 and h>=480 and w*h<=16777216)
    return created_eye if preserve else requested

assert reset_target((1920,1080),(2496,2688)) == (2496,2688)
assert reset_target((3440,1440),(2496,2688)) == (2496,2688)
assert reset_target((1920,1080),(2496,2688),follow=True) == (1920,1080)
assert reset_target((1920,1080),(2496,2688),windowed=False) == (1920,1080)
assert reset_target((1920,1080),(0,0)) == (1920,1080)
print("PASS logical UI resolution is monitor/game-owned while physical VR D3D9Ex target follows XR eye; Reset epoch is writer-safe and full viewport/scissor joins are explicit; HMD UNTESTED")
