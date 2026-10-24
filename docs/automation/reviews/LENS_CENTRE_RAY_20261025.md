# Central lens ray correction — 2026-10-25 KST

TASK_ID: USER-DX9EX-LENS-CENTRE-20261025. Direct user request: fix only the
doubled/misaligned centre flare. Feature: DX9EX:VIS:LENS_FLARE_CENTRE.
Base: 990158b51293b294033c2466558d637df74936d0, R26+HUD.
RUNTIME_VALIDATION=UNTESTED. No optical completion or score claimed.

## Evidence and limits

- User captures 6fbc67b1 and 81c4a685 declare source 50ea48da3f7308528bd230a250b7e69dc67ca710.
  Selected and installed DLL SHA256 agree:
  098e6f57cb17549a30161eb985258983212640abeb7694115e769f29449bb265.
  Runtime loaded-module hash is NOT_ATTESTED. They are not evidence of the
  newer screen-family changes in 846a4b5b / 3b3d6a18.
- The longer capture logs C993 WORLD PROOF rawOwned=0 repeatedly, while
  the CABE R69 fusion path is observed. The short capture has no gameplay
  central-ray evidence. LensFlareCentreEnabled=true; CullingCameraSync=true.
- Upstream emoose hooks_graphics scopes Clr_SceneEffect and temporarily
  changes the near plane to 0.05. That behavior is preserved.
- Existing canonical EXE map separates D3A5 -> C980 -> C993 from CABE.
  The existing r4dius/outrun2-decomp reference, race_course_passes.cpp blob
  22985e118c172467c566fe58d5b08f280c565ee2, places C993 sun components on
  artificial view planes (-1, -0.2, far) through camera +1C0. This supports
  direction reprojection, not applying IPD to these artificial depths.
- CONFIRMED_STATIC: copying identical original clip coordinates to two
  asymmetric projection views does not yield the same reconstructed ray.
  Numeric counterexample with projection centre X=+0.12/-0.18 fails under
  the current copy behavior; the actual new C++ helper passes.
- HYPOTHESIS: correcting that central-only ray mismatch resolves this
  user's visible duplication/placement. Exact current-source HMD proof is
  absent; queued sun components are not promoted by this change.

## Change

C993's existing narrow four-object classifier retains projected-screen
authority and now keeps an exact centre token. R26 alone unprojects the
original WVP, applies common head rotation only when its source was not
already camera-synchronized, applies eye-local rotation and actual eye FOV.
Head/IPD translations are excluded from artificial sun planes. Raw-WVP
camera synchronization is recorded with that source and cleared on invalidation;
the mutable setting alone is never treated as proof that synchronization ran.

CABE outer discs, the existing second-570008 suppression, HUD, GOAL, +TIME,
rank/rival, F11, resolution, culling, cockpit and host composition are untouched.
No new hook address, alpha suppression or extra GPU draw is introduced.
The existing R26 two-eye submission/restore path is retained. Bounded telemetry
`VR LENS C993 RAY EYES` records pose, actual eye HRESULTs and restore status.

## Validation

- C++ numerical smoke: asymmetric horizontal/vertical projection, head roll,
  eye cant, translation exclusion, camera-sync double-rotation prevention,
  invalid pose rejection and no partial output: PASS locally.
- Existing protected CABE fusion verifier: PASS.
- Original HUD CALL contract: 71 sites and 22 negative cases PASS.
- Existing R84 lens source verifier already fails at the base: it requires
  `ScopedExactLensCentreGpuDraw` removed by the previous screen-family patch.
  It was not weakened or bypassed for this change. Exact-SHA CI results must
  be recorded separately; no full-suite PASS is inferred from local checks.
- Windows host CMake builds and executes the new numerical smoke as a host
  dependency. Only GitHub-hosted normal Windows build is authorized.

Acceptance after CI: exact new DLL/host, centre visible once and placed with
the sun while turning head; outer discs unchanged. Inspect new C993 eye
telemetry; absence means the corrected direct draw was not reached, not PASS.
