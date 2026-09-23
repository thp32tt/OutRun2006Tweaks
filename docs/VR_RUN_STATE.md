# VR Run State

Updated: 2026-09-20 23:10 KST

## Current checkpoint
- C0 RECOVER: complete — analyzed user logs from matrix `VRM-20260920-803144005c0e`
- C1 REVIEW: complete — delivered D3D9 SAFE path was an R26/R23 regression-isolation build, not the intended completed DX9Ex renderer
- C2 IMPLEMENT: complete — created `vr-d3d9ex-focus`, removed DXVK/DX12 from its dedicated workflow, added four DX9Ex-only comparison candidates and automatic per-variant log collection
- C3 VALIDATE: in progress — DX9Ex-only workflow run `35515548121`
- C4 COMMIT: complete for workflow/test-harness changes
- C5 PACKAGE: pending successful P1-P4 builds
- C6 STATE: current document

## Strategy change
DX9Ex is now the only active renderer target. DXVK, multiview and DX12 are frozen until the user accepts a correct and smooth DX9Ex reference. The generic Build workflow is disabled on `vr-d3d9ex-focus`; only the dedicated DX9Ex four-variant matrix should compile runtime candidates.

## Why the previous package regressed
The last D3D9 SAFE build explicitly compiled the R26/R23/R22/R13/R9 chain and excluded R29-R34 plus renderer R29. Runtime did reach TRUE STEREO SBS compose, so the new corruption was not a simple stereo-transport failure. In heavy gameplay samples the log rose to roughly 1,800-2,000 draws per Present and more than 568k semantic rejects, matching the expensive conservative replay path. The recovery launcher also forced 60 FPS, interpolation OFF and cadence OFF while the OpenXR host reported 90 Hz, adding a separate source of visible judder.

## DX9Ex four-build set
1. `P1_C1_FAST_WORLD`: R29 fast L+R + restored R27/R28 perspective-world classifier.
2. `P2_C2_FAST_HUD`: P1 + R30 HUD/XYZRHW/SkyGlow.
3. `P3_FULL_R34`: full R29-R34 chain.
4. `P4_R26_HUD_SAFE`: R26 world + R30 HUD/effect overlay, conservative comparison.

All use `PreferD3D9Ex=true`, allow fallback when DirectGPU sharing is not ready, enable dynamic OpenXR PhaseLock, remove the forced 60-FPS test cap after XR cadence becomes active, enable interpolation, and keep `SkyGlowFactor=1`.

## Next runtime test
Test P1 -> P2 -> P3 in that order. Use P4 only if the fast-path candidates remain badly corrupted or as a conservative comparison. Use the same short gameplay segment each time and upload the automatically generated `DX9EX_LOG_<variant>_<time>.zip`.


## Checkpoint 2026-09-21 02:06 KST
- C0 RECOVER: restored source head `2827f20d456d5fb266cfbefbd4435df0f9952569`, state and run `35516112968`.
- C1 REVIEW: no renderer review repeated because binary inputs were unchanged. Failure isolation found all P1-P4 Win32 DLL jobs and the common x64 host succeeded; only package assembly failed at PowerShell `$variant:` parsing.
- C2 IMPLEMENT: preserved packager delimiter fix `2827f20`; added missing declared runtime keys for experimental unlock, Desktop Duplication fallback and dynamic XR cadence in `ee94dc8051b6de8c0b6ce67d9bdd8b613b98363c`.
- C3 VALIDATE: reused artifacts from run `35516112968`. Four distinct x86 DLL hashes and one shared x64 host were confirmed. Follow-up workflow `35524755335` is running against the corrected INI.
- C4 COMMIT: config fix committed through GitHub CAS; `vr-openxr` and paused backends were untouched.
- C5 PACKAGE: local deterministic package `OutRun2_VR_DX9EX_4PACK_f46024f7005c.zip`; SHA256 `ba1757865c445e5f63d37041a1f10dbed8a3137ae049960ec752fc5c9b0fb44b`.
- C6 STATE: complete. Each inner ZIP contains 11 files, passes its own SHA256SUMS, has PE32 x86 `dinput8.dll` and PE32+ x64 `outrun-vr-host.exe`, and excludes DXVK, multiview and DX12 payloads.

## Next action
Quest 3/VDXR runtime evidence is now the gate: test P1 first, then P2 and P3 in the same scene; use P4 only as the conservative fallback. Upload the four auto-collected `DX9EX_LOG` archives. Do not resume other backends.


## Final CI seal
- Workflow `35524755335` completed successfully at source `ee94dc8051b6de8c0b6ce67d9bdd8b613b98363c`: host, P1-P4 games, package assembly and package validation all passed.
- Final artifact ID: `10609329194`; artifact/SHA256: `a21825389f0731ffc62dc23314a1415261bf05fcdf07f4accd4d92a0aa46e630`.
- Frozen test matrix: `DX9EX-20260920-ee94dc8051b6`. Runtime validation is the only remaining acceptance gate.


## Four-role Work pipeline reconciliation — 2026-09-21 03:58 KST

The repository-side automation environment is now aligned with the active four hourly Work roles.

- Integration/source of truth: `vr-d3d9ex-focus`
- A REVIEW store: `vr-d3d9ex-review`
- B FIX store: `vr-d3d9ex-candidate/<finding-id>-<run-id>`
- C VALIDATION/SUPPORT store: `vr-d3d9ex-support`
- D INTEGRATION/PLANNER: sole autonomous production writer and central state/queue/history owner.

Durable coordination:
- `docs/VR_AUTODEV_PROTOCOL.md`
- `docs/VR_WORK_QUEUE.json`
- `docs/VR_RUNTIME_FEEDBACK.json`
- `docs/automation/README.md`
- `docs/automation/RUN_RECORD_TEMPLATE.json`

The active DX9Ex validation workflow now accepts isolated B candidate branches and uses branch-scoped concurrency, so one candidate cannot cancel another candidate or the integration validation run.

Central runtime-candidate WIP limit is 3. Two materially different failed fixes for the same unchanged failure become BLOCKED. A/B/C publish evidence/proposals on their own branches; D imports them idempotently and updates the central queue.

DXVK/multiview/DX12 remain blocked by policy until the DX9Ex reference is user accepted. The next normal human validation remains one CORRECTNESS test unless concrete evidence requires CONTROL/PERFORMANCE comparison.


## Canonical automation role/schedule update — 2026-09-22 KST

Current autonomous pipeline contract supersedes all older role descriptions:

- A :00 — architecture/state/lifetime/OpenXR-lifecycle/synchronization deep review; review-only.
- N100 :10 — auxiliary review-only fresh Chat; findings and delta checkpoint go to Issue #6.
- B :20 — rendering/stereo/visual/performance/frame-pacing deep review; review-only.
- C :35 — IMPLEMENT on isolated candidate branches + deterministic verification/CI + bounded self-recovery. C never writes the integration branch.
- D :45 — independent exact-SHA review + regression/baseline release gate + CI validation + sole integration/final package writer.
- Older text describing B as a fix worker, C as review-only/general validation, or D as the normal product-fix author is historical context only and must not override this contract.
- N100 follows the durable repository baseline/regression policy even when launched outside these Chat automations.

### USER_RUNTIME_VERIFIED baseline lock

- The moving `vr-d3d9ex-focus` HEAD is not the runtime baseline.
- Only matching Quest 3 / VDXR USER_RUNTIME_VERIFIED evidence may establish or advance the protected baseline.
- STATICALLY_VERIFIED or BUILD_VERIFIED results never replace runtime baseline evidence.
- Every runtime-visible behavior confirmed as fixed becomes a protected invariant under its stable regression key.
- C must emit `BASELINE_DELTA` and revalidate every triggered protected regression before handoff.
- D must compare both protected-baseline -> prospective merged tree and current-HEAD -> prospective merged tree; silent loss of a prior fix or reintroduction of a known-bad value/path blocks integration.
- If integration HEAD moves after candidate validation, the prospective merged tree must be revalidated.
- A failed HMD test reopens the existing regression key and preserves the last known-good baseline.

## Overnight handoff — 2026-09-24 01:50 KST

- Protected runtime baseline remains R51 `17ad376bfdf7939f0851c0c629e4fa094a84f28a`.
- PC-clean rebuild of exact R51 was user-tested and reproduced the same functional result as the preserved R51 artifact: world/road/vehicles good 3D; white HUD/rank defects unchanged.
- EXE-map HUD candidate `8d21824f9502b3354fae679972a90868a0cce562` was built clean on PC runner run `35888306771`; package SHA256 `701a57ca5e4a1ba413bcdd75ad6fc6ecc320f6fc3dbb0dbd5a0597cb6ba81d89`.
- HMD result: **FAILED intended HUD/rank fix**. White text and position/rank HUD remain doubled/head-following. Vehicle rank labels remain detached from their cars and head-following. R51 world 3D remained correct.
- New decisive telemetry: `semanticHudAccepted=93681` but renderer `semanticOverlayBypass=0` throughout the session. Producer tagging reaches R30 draw ownership but is not visible at the earlier c64/WVP head-injection boundary.
- Runtime evidence: matrix `PC-R51-HUD-MAP`, session `20260923T164207853Z-2202b186`, uploaded ZIP SHA256 `25be7a39d7daad4073e0b1765e9c6312a13f0b077898a84e4b1a17bf1dfe6731`.
- Performance remains a separate lane: peak `drawsPerPresent≈3929.3`, lower-Present `max≈16.639 ms`; DirectGPU transport stayed healthy (`frames=13187`, `fallbacks=4`, `fenceTimeout=0`).
- Next checkpoint: trace exact producer -> node-tag -> queue-select -> c64 upload -> draw semantic lifetime, plus Calc3D2D/vehicle-anchor propagation for rival rank markers. Do not broaden generic queue-to-HUD ownership.
- **PC runner is disabled until explicit user re-authorization.** Overnight scheduled work is review/static analysis/EXE-map/documentation and normal cloud CI only.

