# DX9Ex Optical Route Probe Development Policy

**Effective:** 2026-10-20 KST  
**Branch:** `vr-d3d9ex-focus`  
**Status:** ACTIVE user-directed visual-debugging policy

## Decision

After the 2026-10-19 Quest 3 visual patch set failed as a group, stop stacking symptom-specific renderer guesses on the active R84 chain.

**Superseded 2026-10-20 14:36 KST:** R26+HUD is now the development and test mainline, with R26_SAFE an alias/control and R84_TEST an explicit comparison only. The original rationale below is historical.

For every reopened visual defect, use this order:

1. Freeze unrelated visual edits.
2. Compare the same source/package inputs with `CURRENT_FOCUS` (R26+HUD) versus `R84_TEST`.
3. Identify the actual physical GPU draw with a bounded per-draw fingerprint.
4. Run an **Optical Route Probe** for that draw only.
5. Permanently change routing only after one route is positively identified.
6. Run changed-area regressions and the final exact-SHA integration gate.
7. Keep `RUNTIME_VALIDATION=UNTESTED` until the matching Quest 3/VDXR build is physically verified.

## Mandatory A/B isolation

Interpret the first R26/R84 comparison as follows:

- **R26_SAFE good / R84 bad:** investigate R29-R33 classification, eye ownership, WVP/pose, right-eye submission or restore.
- **Both bad:** investigate common producer, queue/D3DX batching, UIScaling/logical coordinates, original draw ownership, game-side source resolution or host composition.
- **Both good:** reject the suspected renderer cause and inspect packaging/config/build identity.
- **Different visual failure in each:** keep both routes isolated; do not merge fixes.

Do not silently switch the user package to R84_TEST. R26+HUD is the default and R84 is a diagnostic control only.

## Physical Draw Fingerprint

Do not classify a sky, flare, HUD element, particle or result glyph from semantic scope or alpha/Z state alone.

A bounded fingerprint should capture as many of these as are available without changing rendering behavior:

- original producer/call RVA and `ProducerToken`
- queue node / queue epoch / D3DX batch identity
- Draw API, primitive type/count and indexed/non-indexed form
- VS/PS identity and shader epoch
- FVF / vertex declaration
- texture identity/hash or bound texture pointer generation
- Z enable/write, alpha blend/test, cull mode and relevant stencil state
- raw original c64 WVP serial/provenance and pose epoch
- left/right target identity and draw HRESULT
- restore HRESULT and final route
- frame/present/OpenXR submit identity

A fingerprint is diagnostic identity, not permanent ownership by itself. Prefer original producer evidence when available.

## Optical Route Probe

For one confirmed draw, allow a runtime diagnostic route selector with these conceptual modes:

- `Native`: unchanged original game draw
- `RotationOnly`: HMD rotation/FOV, no head translation and no IPD translation
- `WorldStereo`: full per-eye world WVP
- `ZeroDisparity`: same original stock transform in both eyes
- `FiniteHud`: source-owned finite binocular HUD plane
- `Hidden`: diagnostic-only suppression to confirm draw identity

The probe must be fail-closed, opt-in, per-fingerprint, reversible without rebuild when practical, and must not globally widen `SceneEffect`, `ScreenOverlay2D`, alpha, FVF or texture classes.

## First applications

1. **Sky:** identify base sky/cloud/light draws independently. Shader sky does not inherit fixed-function `SkyRotationOnly` automatically. If a confirmed base-sky shader draw is correct only under `RotationOnly`, add a positive sky owner and preserve unrelated SceneEffect/lens/light draws.
2. **Lens centre:** isolate the central C993-related physical draw from outer CABE rings and SkyGlow; probe only the confirmed centre.
3. **+TIME / GOAL:** fingerprint sprite and numeric/glyph batches separately; compare Native, FiniteHud and ZeroDisparity without touching timer logic.
4. **Vehicle rank:** preserve Calc3D2D/projected-car anchor and independently probe the terminal physical draw.
5. **F11:** treat external ImGui separately from original game HUD and world rendering.

## Coordinate/source isolation

Because 2026-10-19 introduced broad game/menu source-resolution changes, do not attribute a visual correction to R29-R33 until coordinate/source effects are isolated. During diagnosis, explicitly record `VRUnifiedEyeMenuSource`, game source extent, logical UI viewport and XR eye extent.

A global resolution/coordinate change and a renderer-route change must not be evaluated as one unseparated patch.

## Failure discipline

If a same-day group of visual patches fails in HMD:

- stop adding further speculative fixes to the same chain;
- preserve the failed SHA and user verdict as evidence;
- revert or disable broad experimental routing where required for isolation;
- restart from R26/R84 control and physical draw identity;
- do not declare success from CI, static simulation, counters or HMD-less preview.

HMD-less preview may validate draw presence, left/right routing and gross placement only. It is not Quest 3 optical acceptance.

## Completion

A visual defect is complete only when:

- the physical draw/source is positively identified;
- the selected route is narrowly implemented with protected negative cases;
- final exact-SHA DX9Ex Active game/host/package and required isolation/inspector checks pass;
- and the exact package is accepted in Quest 3/VDXR for that symptom.

Until the last condition: `RUNTIME_VALIDATION=UNTESTED`.
