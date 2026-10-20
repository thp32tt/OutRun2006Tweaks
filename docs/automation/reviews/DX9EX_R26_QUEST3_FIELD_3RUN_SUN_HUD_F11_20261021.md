# DX9Ex R26 Quest 3 field report — 3 consecutive captures (2026-10-21 KST)

Status: **partial improvement confirmed in headset; remaining optical bugs NOT FIXED.**
Direct user-authorized fix task. Scheduled DX9Ex REVIEW_ONLY automation policy remains unchanged.

## Input runs (user uploaded, not stored in repo)

| Session ID | Profile | Source | Notable |
|---|---|---|---|
| `20261020T154512586Z-128303ea` | PERFORMANCE | `3f9ccd3b122d` | `SkyGlowFactor=0`, backbuffer 3440x1440, MSAA2 |
| `20261020T154943238Z-ebe01a01` | CORRECTNESS | `3f9ccd3b122d` | `SkyGlowFactor=4`, backbuffer 3440x1440, MSAA4, first C993 hide absent in this run |
| `20261020T155629142Z-881e3904` | CORRECTNESS | `3f9ccd3b122d` | `SkyGlowFactor=4`, 3440x1440, MSAA4, `VR LENS C993 CENTER HIDDEN` proven |

SHA/session identities come from `CURRENT_VR_SESSION.json`/game DLL and game log. User's 4:3/main-menu, Ferrari geometry observations are physical HMD evidence, not inferred from screenshots.

## Confirmed resolution result

- `VR SOURCE COORDINATES: follow original game config 3440x1440` on all runs.
- `VR EYE RESOLUTION: ... SOURCE keeps 3440x1440` on all runs.
- `VR D3D9 probe: backbuffer=3440x1440` on all runs.
- OpenXR physical eyes continue 2496x2688; the earlier corrupt game-portrait 2496x2688 backbuffer did NOT recur.
- User confirmed true 4:3 restored and vehicle no longer bleeds beyond the selection menu. Do not regress this.

## HUD quality: confirmed scale multiplication, cause not yet isolated

- Shipped `HudScale=0.55`, `Hud1080pReference=true`.
- R26 `hud_1080p_reference.hpp` computes `(1920/1080)/(3440/1440)=0.744186` contain-fit; total game HUD scale = **0.409302**. This is *not* the game render resolution, and the actual HUD texture sampling/filtering is not proven to be the cause.
- Report: driving HUD and other objects show jagged/pixelated edges. Possible source sprite minification/reprojection vs native texture filtering vs MSAA; do not raise the game resolution or globally weaken MSAA to address this without A/B proof. A/B `Hud1080pReference=false` keeps `HudScale=0.55` and can isolate additional containment minification.
- The PERFORMANCE run used SkyGlow 0 and MSAA2; CORRECTNESS uses SkyGlow 4, MSAA4. Do not use their performance/optics as exact matched A/B without source condition alignment.

## F11 HMD: stereo fixed, size broken

- `VR R30 F11 IMGUI SCREEN2D` FOV-only route observed; bilateral left/right HRESULT=0 for 3440x1440 source, eye-specific scissor observed.
- User confirms F11 in gameplay is now a *single* window, but huge, options invisible. Main-menu F11 already normal.
- `src/overlay/hooks_overlay.cpp` computed `vrFontMultiplier=ceil(2.573*4)/4=2.75` due 3440/1440 vs portrait eye aspect 2496/2688, and `overlay.cpp` creates a `1130*2.75` x `600*2.75` shell clipped to source extent.
- **Implemented:** cap font and shell to 1.25x *only while gameplay F11 is actually visible*, leave FOV-only XR projection and native menu F11 as-is. Needs optical verification.

## Sun, flare C993 and CABE

- Both performance and correctness have `VR P0 LENS CENTRE: 0xD3A5 + C993`, outer CABE effect calls include IDs 5701646, 5701635.. etc.
- C993 original center 0x570002 *was skipped* in 2/3 captures: `VR LENS C993 CENTER HIDDEN: ... parent=1 owner=1 queue=0`. User nevertheless reports distracting doubled central spot and **two stage-one suns**.
- Therefore the single C993 hide is an ineffective strategy and is not a valid stereo fix. **Implemented:** restored `LensFlareCentreEnabled=true` source default and shipped INI; kept the switch for explicit user A/B only. Added `VR SUN C993 ORIGINAL DRAW` (source/parent owner) and `VR SUN C993 WORLD PROOF` (same-call raw WVP, pose, world route) bounded diagnostic events.
- No assertion yet whether duplicates arise from CABE halo vs SceneEffect sky vs eye projection, and no suppress-all or zero-disparity blanket fix. Upcoming recording must correlate stage-one sun/rings with original producer and per-eye pixels before any world matrix retarget.

## Unresolved HUD/stage/rank

- User says +TIME is split, displaced to the right and moves with their head. State init proves producer hooks, not optical success. In the longer correctness session `VR R26 RESULT_HUD_EYES` left/right S_OK for result progress; the user still observes two progress records. These are different producers. Do not globally share one HUD pose.
- Current `R30IsExactResultHudDraw` only recognizes `IsExactFiniteResultHud`; +TIME has distinct `StageExtensionTime` producer and fixed-function/D3DX paths. Next compare explicit producer, original game c64/FFP and physical eye route (left/right), capture eye-relative actual screen coordinates and determine if double image comes from wrong head inverse or mixed R29/R30 ownership.
- Rank physical logs `navipub=1 anchorValid=0 projected=0` and `0xBAEE2 rawFinite=true projectionValid=0 navipubDepth=1`; these are NaviPub screen HUD observations, not automatically failed real car anchors. HUD trace contains RankMarker/sub_4BAD20 WORLD_BILLBOARD class and `projectedMarkerSemanticCount=0`, so world projection still needs an exact per-producer run. User confirms DX11 test markers fully normal, but R26+HUD marker parity remains unverified.

## Change policy and next HMD test

- R26+HUD remains the sole default; R84 is comparison only. Preserve landscape 3440x1440 game source, world/backbuffer dimensions, and 0.55 HUD scale.
- After Windows CI exact SHA success, use its packaged test, set `[VR] LensFlareCentreEnabled=true` (user INI may retain older false). For F11 verify options visible and shell single on game and front-end.
- Compare stage-one sun with `SkyGlowFactor=0` vs `4` at same MSAA, and +TIME at same pose, use fresh log ZIP. Do not claim resolved until binocular optics validate.
- Game/HMD not accessible in CI: **RUNTIME_VALIDATION=UNTESTED** for new changes; no score for re-reporting prior results.
