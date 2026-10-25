# Independent menu canvas and VR source resolution

TASK_ID: USER-DX9EX-MENU-RENDER-SEPARATION-20261025
Feature: DX9EX:VIS:MAIN_MENU / DX9EX:SYMPTOM:MAIN_MENU
Source mode: CHAT_DIRECT; user explicitly authorized implementation.
Base: 2c37e2ff76012283c1028de90e5ca757b1f6dbba, vr-d3d9ex-focus.
Runtime: UNTESTED. New candidate, not a promoted HMD baseline.

## Source findings and design

R26 allocates actual eye rendering from the game backbuffer extent. Merely
allocating a different OpenXR swapchain does not increase the source rendering
resolution. `ApplyVrEyeResolutionAfterConfig` already supports selecting the XR
recommended extent before native UI initialization, but its additional
`PreferD3D9Ex` gate blocked that policy with the shipped false provider preference.
Remove that dependency without changing the provider/transport preference.
Manual paired RenderWidth/Height and explicit command line dimensions win;
unavailable host extent retains the game configuration after a bounded wait.

Keep a single physical game target and the existing native 640x480 logical menu
canvas. The title/main menu content is contained at 4:3 inside that target.
The host crops the known authored content and projects it at 4:3 in both eyes.
Game render dimensions affect sampling density, not the menu's optical size.
The aspect-preserving PC mirror remains independently fitted to the monitor.

Rejected alternatives: switching physical resolution at menu transitions adds
Reset/lost-resource and stale UI-transform risk; a second independent menu render
target requires redirecting the game's mixed sprite/3D/selection draw chain and
new capture ownership. Neither is required for independent 4:3 display size.
This change does NOT claim a separate fixed-resolution menu texture or bypass
Desktop Duplication. Desktop capture still bounds menu sampling quality.

## Implementation and validation plan

1. Reproduce the provider-coupled source-selection gate with a failing test.
2. Remove that gate; retain original config-init timing and all manual/fallback rules.
3. Register VR.MenuScale (0.50..1.00; default 1.00). Read game-adjacent base/user
   INI with the established PID/HWND cache and user-INI precedence. Apply only to
   TITLE/MENU; keep selector and other states unchanged. Explicit diagnostic
   OUTRUN_VR_MENU_OPTICAL_COVERAGE still wins.
4. Invalidate cached menu composition on saved scale changes even without new
   desktop pixels. Do not reallocate game/XR buffers for a menu-size change.
5. Test real C++ geometry and source wiring, then exact-SHA hosted Windows
   R26 game, host, R84 compile control, package and required isolation/inspector gates.

## Local evidence

- New source wiring regression failed before at the PreferD3D9Ex dependency;
  passes after implementation.
- Compiled production `menu_content_aspect_smoke.cpp` with g++ C++17: PASS,
  including title/main scaling, selector/unknown isolation, malformed/NaN scale,
  environment precedence, and equal optical 4:3 extents for 1920x1080,
  3440x1440 and 2496x2688 source crops.
- Existing menu letterbox/fragment/mutation, mirror fit, unified source and
  manual-game-coordinate regression checks: PASS after aligning two stale
  default assertions with the already-shipped Unified=true / FollowGame=false.
- R26+HUD, Hud1080pReference=true, HudScale=0.55, DriverSeatView=false,
  rival/rank/world draw routing, DirectGPU protocol and input/FFB unchanged.

## User settings / acceptance

`[VR] AutoRenderResolution=true`, `RenderWidth=0`, `RenderHeight=0` selects the
live XR extent when available at startup. A valid manual pair is the override.
`MenuScale=1.00` is the largest binocular-safe menu; 0.85 reduces it uniformly.
Saved F11 MenuScale changes are picked up within the 2.5-second config poll.
Restart after changing game render dimensions. Existing .user.ini overrides win.

Quest3 acceptance: check title/main 4:3 at MenuScale 1.00 and 0.85; selector full
width; enter/leave race without Reset; HUD/F11/rival positions; desktop resolution
changes do not change the 4:3 optical size; inspect VR EYE RESOLUTION / VR UNIFIED
SOURCE, VR PC MIRROR and VR MENU ASPECT logs. Compare FPS at the actual selected
source extent: choosing more pixels can cost GPU time. No FPS claim is made.

## Resume / CI gate repairs (2026-10-25)

Initial material b65c346da8481706f4bf80a42e41f011065950f2 passed General Test
Build run 40173837070 (Windows R26 game + host + package), while Active
40173837089 stopped on a stale lens verifier. The remaining policy tests exposed
a stale F11 verifier. These now assert the existing projected-sun C993 scope and
finite F11 projection plus bilateral affine fallback; neither runtime owner was
modified. Intermediate source-only success is not the final Active gate.

Correction to the initial provider finding: the official test launchers force
PreferD3D9Ex=true. The shipped INI false value therefore does not establish the
root cause of the user's observed menu issue. Provider-independent startup
selection still makes direct and launcher startup policies consistent.

Follow-up review CONVERSION-DX9EX-01484 identified same-owner refresh failures
resetting the new MenuScale to 1. A failed process/path lookup or absence of both
config files now retains the previous accepted scale/crop for that HWND/PID.
New owners reset to defaults. Base/user values are staged before publication.
This does not claim an atomic filesystem snapshot across simultaneous INI writes
or preservation of an unreadable individual user INI when the base is readable.
Changed-area regression failed before and passes after the new refresh logic.

Baseline delta: protected user-tested R26+HUD 0cff83cf remains the immutable
hardware baseline. This task changes startup source selection and host title/menu
optical sizing; race HUD scale, selectors, world draw ownership, input/FFB and
DriverSeatView defaults are unchanged. Title/menu optics and selected source
performance require new exact-package Quest3/VDXR acceptance, not baseline promotion.

Active run 40195398274 at 74fdf953 stopped on the composite P0 verifier's duplicate
superseded F11/C993 assertions. Updated those to current finite+affine F11,
exact projected-sun admission/token/fallback and all three bounded raw-WVP
callsites. Function extraction/injection now skips forward declarations. Full
composite positive and destructive tests pass locally; production lens/F11 source
is unchanged. The actual host config function was additionally extracted and
compiled against deterministic Win32 API shims: same-owner OpenProcess/path/
missing-files failure, new PID/HWND reset, user precedence, explicit 1.0 and NaN
cases pass. Final integrated CI remains required on the validation SHA.
