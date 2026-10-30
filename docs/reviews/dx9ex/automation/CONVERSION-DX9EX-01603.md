# CONVERSION-DX9EX-01603 — R85 projected-sun helper translation/yaw matrix controls (LENS_FLARE_ONLY / REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01603
PRODUCTION_ID=CONVERSION-DX9EX-01603
EVENT_ID=CONVERSION-DX9EX-01603-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=937a0d1c1a12161e307ab74b5a1db704f08009ee
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_SHA;PRECOMMIT_HEAD_RECHECKED
MODE=DX9EX_REVIEW_ONLY
REVIEW_SCOPE=LENS_FLARE_ONLY
DX9EX_REVIEW_ONLY=ON
CODE_CHANGE=NO
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
ROOT_CAUSE=UNCONFIRMED
NEW_FINDING=STATIC_HELPER_MATH_BOUNDARY_CONFIRMED_BY_SEVEN_COMPILED_CONTROLS_STOCK_WVP_TRANSLATION_SURVIVES_WHILE_HEAD_AND_EYE_TRANSLATION_ARE_REMOVED;NO_NEW_RUNTIME_DEFECT_PROVEN
NEW_FINDING_RUNTIME=NONE
RUNTIME_VALIDATION=UNTESTED
AUTOMATION_VALIDATION=DOCS_ONLY_PENDING_REMOTE_READBACK

## Independent test, not a repeat of 01602

01602 tested R30 right-eye HRESULT/return-HR/diagnostic disagreement. 01560 had traced separate asymmetric FOV construction, 01562 demonstrated same-shader/age raw-WVP ownership limitations, 01563 checked mixed-time camera-sync source diagnostics, and the 2026-10-29 04:36 R85 review checked post-Draw camera-sync log re-reads. None of those is re-scored. This task instead executes *translation- and yaw-perturbation negative controls* on the pure R85 projected-sun matrix helper and identifies which transformations remain able to carry source spatial motion. No game/device/OpenXR simulation is claimed.

The pinned `src/vr/d3d9/projected_sun_ray.hpp::BuildProjectedSunRay` implements, in D3D row-vector order, `stockWvp * inverseBaseProjection * headRotation * eyeRotation * eyeProjection`; it sets translation components [3][0..2] of headRotation and eyeRotation to zero. When `sourceCameraSynced=true`, it substitutes identity for headRotation. Importantly, it does **not** clear the spatial terms in `stockWvp`. This is an input-provenance boundary, not a demonstrated defect: original game WVP can intentionally encode the changing game-camera sun ray.

A small standalone C++17 harness transcribed the pinned helper's complete finite-check/multiplication/translation/sync logic and compiled locally with `g++ -std=c++17 -O2 -Wall -Wextra`. All assertions are *controlled mathematical examples*, not an actual OutRun 2006 run or official CI. Numerical examples use identity stock/base/eye matrices except for the explicitly varied component; projection differences use an illustrative eye X scale (1 versus 0.92), not captured Quest3 FOV. Output: **7/7 PASS**.

| Independent helper control | Observed in standalone harness | Meaning / limit |
| --- | --- | --- |
| Identity inputs | PASS: identity output | Harness neutral control. |
| Alter head x-translation +100 and eye x-translation -10 | PASS: output equal to untranslated neutral | The helper alone cannot introduce stereo IPD translation through those two supplied matrix translations. |
| Rotate head 90 degrees with `sourceCameraSynced=false` | PASS: output differs | Unsynced branch can respond to head orientation for fixed original WVP. |
| Rotate head 90 degrees with `sourceCameraSynced=true` | PASS: output equals neutral | Synced branch deliberately delegates head-orientation motion to the already-synced source WVP; fixed source under real head yaw would appear head-locked, but source is not known fixed in game. |
| Change eye projection X scale from 1 to 0.92 | PASS: output differs | Distinct FOV projections need not yield identical eye constants; not evidence of duplicate emitter or correct HMD pixels. |
| Change original `stockWvp.m[3][0]` from 0 to 0.4 | PASS: output differs | Head/eye translation removal does **not** remove original source WVP translation. Whether this is correct requires retail producer/world-bearing evidence. |
| NaN stock matrix | PASS: returns false without modifying sentinel output | Bad input is fail-closed inside the helper, before native drawing. |

No alternate hook, game patch, CI skip, HMD log, game binary or package was created. This local harness is outside the Git tree; no game or runtime source was changed.

## SOURCE_TRACE — current GitHub-pinned files and exact 1-based lines

1. `src/hooks_graphics.cpp:995-1100,1107-1135,1137-1290` (blob `982f55dc91c00faf336c06317006fe4aba11db1a`): original CABE source object/alpha, `0x570008` ordinal1/2 deferred diagnostic window, original `Game::DrawObjectAlpha_Internal`, plus C993 four projected IDs (`0x570002/006/00F/010`), direct queue admission, scope and `ProducerToken::None`. Source-call counts cannot certify physical PMT/texture or colour pixels.
2. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:1978-2006,2008-2046,2337-2399,5537-5572` (blob `83a2821bd53d043d7df0557f46627d0af1205d48`): exact current screen semantic and original raw-WVP recovery with shader/age gates, distinct from a physical 405890/404700 source/mesh proof. R44 gets stock matrix first; extended SceneEffect only if necessary. The 01562 ownership gap is inherited, not new.
3. Same file `:5732-5819`: R85 projected sun uses `GetLatchedHeadInverse` with exact poseSequence, `GetLastRawGameWvpCameraSynced()`, identity eye rotation, individual `stereo.eyeFov[eye]` through `ProjectionFromFov`, then `BuildProjectedSunRay` and transposed c64 per eye. `VR TRACE LENS R85 BUILD` is a **pre-Draw** calculation receipt.
4. `src/vr/d3d9/projected_sun_ray.hpp:11-56` (blob `29e1e4c3fbd9d8aefb3ed913ad0374fc6902a7b4`): directly checked finite guard, matrix multiplication order, sync head identity, head/eye translation stripping and untouched stock WVP.
5. `src/vr/game/outrun_renderer.cpp:1701-1717,1718-1757` (blob `9b845778272e59585df8e2ae570f6da260cb8ec9`): invalidation and original c64 publication, including `LastRawGameWvpCameraSynced=CullingCameraOverridden`, shader/draw/semantic/queue/pose provenance. No current physical sun-specific WVP or camera record captured.
6. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6860-7065,7135-7238,7605-7744`: screen shader admission and E_NOTIMPL lower fallback; LEFT c64/native draw, RIGHT RT/depth/viewport/c64/native draw and restoration. This task did **not** revalidate the 01602 HRESULT distinction, nor claim that 2 eye draws are duplicates.
7. `vrhost/src/runtime/r23_runtime_hardening.hpp:36-75,105-128` (blob `64b4308013d0d579c5ea6c47504657a280c845e8`), `vrhost/src/runtime/r24_black_screen_guard.hpp:584-640` (blob `34d1234ab50f15c39451c39bdb9182f44d62e91c`), and `vrhost/src/main_r23.cpp:3860-3942` (blob `15c5ea065f4cc2c30ebd2d45aefbaa48581f4ede`): final-frame/layer receipt and host OpenXR submission are separate from helper math and native RT attempts. Earlier R24 mixed-fallback and cached local-pv caveats remain inherited, not independently reproduced.

## HYPOTHESIS_LEDGER — separate static assertions from headset hypotheses

| ID | Status | Prior evidence -> new observation | Concrete falsifier / promotion rule |
| --- | --- | --- | --- |
| A duplicate original emitter | OPEN | C993 four objects and CABE ordinal1/2 are intended possible sources; math controls never invoke original producers. | Prove unintended extra original object+sourceCallSerial+405890/404700 PMT/mesh/pass and same-eye RGB write beyond legitimate materials. |
| B same-eye opaque queue/D3DX/native replay | BLOCKED_RUNTIME | 01602 right success-return caveat inherited. New tests establish no draw multiplicity at all. | Join original 405360/4052C0 queue, SpriteNode/D3DX Flush if present, PMT, texture0+blend, native drawSerial and L/R RT colour deltas; count duplicate writes only within SAME eye/source/pass. |
| C head/eye translation causes the helper's centre double | **REFUTED_FOR_HELPER_TRANSLATION_ONLY** | New compiled head/eye +/-translation control leaves helper output invariant. This does not refute original stock WVP translations, upstream world-camera errors, another renderer route or host reuse. | Produce source-authenticated fixed `stockWvp` and matched R85 c64 whose head/eye-only translation changes output; otherwise examine original stock c64 and downstream. |
| C per-eye asymmetric FOV duplicates a source emitter | OPEN_OPTICS; MATH_NOT_DUPLICATION | Different eye projections produce different c64 with a single original stockWvp; per-eye differences are expected. | Same-source same-eye 2 independent physical RGB writes, not just two distinct eye constants. |
| D intentional disc/halo/pass mistaken for two suns | OPEN | C993 `0x570002` sun disc and `0x570006` glow are separately scoped; CABE `0x570008` has two normal ordinals. | Match texture/alpha/mesh/colour ROI for each original material in one eye then two eyes. |
| E stale XR projection/composite | BLOCKED_RUNTIME | Host acceptance is independent of these matrix tests; previous R24 receipt gaps inherited only. | Final accepted actual XR projection.views L/R, arrayIndex, image-frame ID/QPC, texture RGB and yaw-aligned per-eye image. |
| F source-camera head-follow | OPEN_CONDITIONAL | New compiled synced/unsynced head-yaw controls: `cameraSynced=1` removes *helper* yaw response, requiring a correctly head-synced original WVP. `stockWvp` translation survives. | On two fixed-world sun yaws, join original sun/game view + c64 writeSerial/pose/sync with R85 generated matrices, actual native RT centroids and accepted XR views; show whether original source WVP changes coherently with head pose. |

## SOURCE_TRACE boundaries, evidence gaps and next falsification

EVIDENCE_SOURCE=GitHub exact pinned source and local C++ helper-transcription 7/7 PASS.
EVIDENCE_DISASM=PRIOR_ONLY: canonical original C993/CABE/405360/4052C0/405890/404700 evidence cited in earlier tasks; no fresh retail bytes or new Ghidra evidence read.
EVIDENCE_LOG=NONE_NEW: no executed game native draw, texture/alpha, R30 transaction, R19 frame/QPC, R24 accepted frame or captured per-eye RGB.
EVIDENCE_USER_REPORT=Prior Quest3 central double/head-follow; current SHA not reproduced. Code comment in R30 flat-CABE classifier refers to a 2026-10-30 HMD falsification of a **different experimental deferred-ray promotion**, but this task has not independently reviewed that test video/build and does not promote any SHA to PASS.
EVIDENCE_GAPS=No original sun C993 per-object c64+camera view/sync provenance; no exact 405360→4052C0→405890/404700 PMT/texture/alpha/pass; no R30 left/right c64 upload hashes, native GPU eye colour deltas or host-composited fresh XR eye images; no matched Quest3/VDXR two-yaw capture.
NEXT_FALSIFICATION_TEST=On ONE exact C993 0x570002 source and one separate CABE 0x570008 material, correlate sourceCallSerial+sequence+original PMT+texture/alpha with original raw stockWvp hash/writeSerial/sourcePoseEpoch/cameraSynced and R85 BUILD `cameraSyncedApplied`. For equal source WVP at two head yaws, predict synced=1 helper output constant (requires source WVP itself to move in a correctly synced game); unsynced=0 helper output changes by headInverse. Control with changed stockWvp translation but fixed head/eye shifts. Then require R30 successful physical L/R draw receipts, actual per-eye PRE/POST RGB centroids and accepted R24/R32 xrEndFrame projection.view pointers/poses; verify whether source and optics disagree before assigning F/E/B. No unsafe B9200 hook.
PATCH_CANDIDATE_ONLY=CONDITIONAL_DIAGNOSTIC_NOT_APPLIED: If same-build physical evidence shows original `stockWvp` and `cameraSyncedApplied` mismatch the *same sun source*, consider narrow read-only receipt correlation at `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5537-5572,5739-5805` and `src/vr/game/outrun_renderer.cpp:1718-1757`: log one exact sourceCallSerial+raw writeSerial/pose/c64 hash+sync+eye WVP hash; avoid route changes. Reject this candidate if existing log joins already prove same record and appropriate source motion. Preserve direct C993 and deferred CABE, alpha/texture order, R26+HUD baseline, R84 nondefault and no hook insertion.
REGRESSION_RISK=DOCS_ONLY_NONE; any future optical/source mutation risks suppressing legitimate halo/ghost, double-applying yaw, upsetting asymmetric eye FOV, poison/fallback and host layer continuity. Do not infer Quest3 acceptance or FPS from compilation.
NEXT_REVIEW=LENS_FLARE:C993_R85_STOCK_WVP_CAMERA_SYNC_SAME_SOURCE_TWO_YAW_TO_NATIVE_EYE_RGB_AND_ACCEPTED_XR_PROVENANCE
