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

## Role-C specialized handoff — 2026-09-22 00:30 KST

POST_FIX_REVIEW:
- candidate_sha: `176b850fe2db753f56a056b6ff001b804e5e4ebe`
- base_sha: `d568d714bd048abadd7ba28ba3ee2a760af65796`
- finding_ids: `HUD-SEMANTIC-TIMEATTACK-RANGE-GAP-001`
- changed files/functions: `src/vr/hud_semantics.hpp` / `ClassifyKnownHudCallsite`
- intended hunks: extend `DispTimeAttack2D` lower boundary from `0x0BE300` to `0x0BE270`; add compile-time positive/negative boundary assertions.
- unintended_diff: PASS on exact base; candidate is exactly 1 commit ahead, 0 behind, one source file, +3/-1.
- active_call_path: semantic classifier source change, not verifier-only.
- dependency/regression risks: current integration has moved to `a50ee775636e5572f7976f2d1374089741b510b0`; candidate is now diverged from current integration and must not be integrated directly.
- deterministic checks: preserve positive `0x0BE2D9 -> ScreenHud`, negative `0x0BE261 -> Unknown`, adjacent `HUD_GOAL_TIME` boundary, compile/build.
- CI evidence: no workflow runs associated with candidate SHA at review time.
- verdict: NEEDS_CHANGES (stale base only; exact-base changeset itself is sane).
- required review: B exact-SHA review was PASS for this candidate; regenerated current-base SHA requires B + C again.
- exact correction: recreate the same minimal 4-line source delta from current integration HEAD, then build/CI and reroute exact regenerated SHA to B and C.

FINDING_ORGANIZATION:
- `HUD-SEMANTIC-TIMEATTACK-RANGE-GAP-001`: READY / stale candidate evidence retained, current-base recreation required.
- `B-R30-PRIMITIVE-COUNT-OVERFLOW-001`: NEEDS_REVIEW; do not send to D until caller bounds are established.
- `B-R32-FENCE-ORDER-CROSSTRACE-001`: NEEDS_REVIEW; do not send to D until GPU ordering evidence is established.

D_IMPLEMENT_NEXT:
1. `HUD-SEMANTIC-TIMEATTACK-RANGE-GAP-001` | READY | `src/vr/hud_semantics.hpp::ClassifyKnownHudCallsite` | recreate exact 0x0BE270 lower-bound + two assertions on current HEAD | verifier: compile-time boundary assertions + build | dependency: stale candidate only | review: B+C | priority: P0 unblock/integration-ready.
2. `VR-SKYGLOW-ACTIVE-GATE-001` | READY | SkyGlow ownership/active gate in current stereo renderer path | gate ownership on actual runtime/stereo-active eligibility while preserving `SkyGlowFactor=1` | verifier: deterministic active/inactive gate cases + build | dependency: current renderer path | review: B+C | priority: P1.
3. `VR-NEARPLANE-ACTIVE-GATE-001` | READY | near-plane override eligibility path | apply override only under actual runtime VR eligibility | verifier: deterministic eligible/ineligible state cases + build | dependency: state/render boundary | review: A+B+C | priority: P1.
4. `VR-SEMANTIC-NEXTDRAW-STALE-HEART-001` | READY | semantic next-draw consume/clear lifetime | prevent HEART semantic leakage across skipped/ineligible draw | verifier: skipped-draw lifetime regression | dependency: semantic state lifetime | review: A+B+C | priority: P1.

READY_for_D: 4
nextAction: D must recreate the Time Attack patch from integration `a50ee775636e5572f7976f2d1374089741b510b0`; do not merge `176b850f...` directly. After creation, run build/CI and obtain B exact-SHA domain PASS plus C exact-SHA changeset-sanity PASS.