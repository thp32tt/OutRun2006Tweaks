# OutRun VR Scheduled Run History

This cumulative history records resumable scheduled development runs for the `vr-d3d9ex-focus` branch. Compilation success is not runtime VR acceptance.

## Run 0001 — 2026-09-21 02:59 KST

- Time (Asia/Seoul): start 2026-09-21 02:59:17; end 2026-09-21 03:00:40.
- Elapsed: wall time 1m 23s. Active-review time is not independently measurable; no compile/build time was spent.
- Trigger/context: scheduled DX9Ex-first checkpoint recovery run.
- Starting branch/SHA: `vr-d3d9ex-focus` at `6c9e400303ecd401d06cbbc7b306e69da4917f7d`.
- Ending source SHA: unchanged at `6c9e400303ecd401d06cbbc7b306e69da4917f7d`; this history publication adds a documentation-only commit.
- Recovered checkpoint: `C6_STATE`.
- Recovered nextAction: obtain Quest 3/VDXR evidence for P1, then P2 and P3; use P4 only as a conservative fallback.
- Components reviewed: `docs/VR_AUTODEV_STATE.json`, `docs/VR_RUN_STATE.md`, `docs/VR_REVIEW_FINDINGS.md`, branch head, frozen matrix identity and prior CI/package records.
- Findings: source/config/package inputs are unchanged; no new user runtime log or hardware result was available. The required cumulative history file was absent and is created by this run.
- False positives cleared: none; no renderer hypothesis was re-evaluated without new evidence.
- Source changes: none. `vr-openxr`, DXVK, multiview and DX12 were not modified.
- Validation: recovered CI run `35524755335` remains successful for the x64 D3D11 host, all four Win32 DX9Ex candidates, package assembly and package validation.
- CI/artifact: [run 35524755335](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/35524755335); artifact `OutRun2-VR-DX9EX-4PACK-ee94dc8051b6de8c0b6ce67d9bdd8b613b98363c` (ID `10609329194`).
- Package: `OutRun2_VR_DX9EX_4PACK_ee94dc8051b6.zip`; SHA256 `a21825389f0731ffc62dc23314a1415261bf05fcdf07f4accd4d92a0aa46e630`.
- P1 status: relevant; primary first runtime test for fast world classification.
- P2 status: relevant; second test adding HUD/XYZRHW/SkyGlow correction.
- P3 status: relevant; third test of the full R29-R34 chain.
- P4 status: relevant only as conservative fallback/reference.
- Runtime evidence: still required. Successful compilation/package validation must not be interpreted as Quest 3/VDXR correctness or smoothness.
- Blockers/retry count: hardware runtime evidence pending; retry count 0.
- Result: **NO MATERIAL CHANGE / NO BUILD NEEDED**.
- Exact nextAction: test identical menu/car/race scenes in P1 -> P2 -> P3 order, use P4 only if needed, and upload each auto-collected `DX9EX_LOG_<variant>_<time>.zip`.


## Automation environment reconciliation — 2026-09-21 03:58 KST

- Scope: repository-side setup for the active A(:00) / B(:15) / C(:30) / D(:45) Work schedules.
- Integration source of truth remains `vr-d3d9ex-focus`.
- Added durable protocol, central queue, normalized runtime-feedback inbox and common role-run record schema.
- Initialized A store on `vr-d3d9ex-review` and C store on `vr-d3d9ex-support`.
- B is restricted to isolated `vr-d3d9ex-candidate/<finding-id>-<run-id>` branches.
- D alone owns production integration plus central queue/state/history.
- `.github/workflows/vr-dx9ex-active.yml` now triggers for both integration and candidate branches; concurrency is branch-scoped.
- Runtime candidate WIP cap: 3. Fix-attempt cap per unchanged failure: 2.
- Added lightweight coordination validator `tools/Test-VRAutodevCoordination.ps1` and workflow `.github/workflows/vr-autodev-coordination.yml`.
- No DXVK/multiview/DX12 development was enabled.
- This setup changes automation/CI coordination; it does not claim new Quest 3/VDXR runtime correctness.

## D integration run — 2026-09-21 11:47 KST

- Starting integration: `f03e54997d4a247ff65037aee4166614288922d5`; runtime source identity remained `8cca78df85fef21a38e66f20fcf9ae867c4779cb` throughout source-review work.
- N100 Issue #6 was inspected and contained zero comments, so no N100 finding was imported or double-counted.
- Verified B dedicated ledger `B-20260921T1112KST` at CP20 with 20 persisted distinct entries. Dedicated `vr-d3d9ex-review-a` and `vr-d3d9ex-review-c` branches were created successfully and fast-forwarded to current integration state, removing the prior persistence blocker.
- Revalidated `DX9EX-RESET-STATEBLOCK-001`: R15 still retains `D3DSBT_ALL` across ResetEx. The prepared patch was recovered but production source was not rewritten from truncated connector excerpts. Added deterministic verifier prototype on the isolated reset candidate branch.
- Revalidated `DX9EX-SKYGLOW-001`: current R30 ping-pong composite source is reversed relative to the last blur output for both one-step and two-step paths. Added deterministic verifier prototype `9bd3f9ab81b0e3549328d367bddcb16c3c8a4d97` on an isolated candidate branch.
- Revalidated `DX9EX-PERF-PRODUCER-FENCE-001`: DirectGPU producer uses `GetData(D3DGETDATA_FLUSH)` plus bounded `SwitchToThread` polling with `ProducerFenceBudgetMs=2`; no performance conclusion was inferred without runtime measurements.
- Implemented `DX9EX-TEST-HOST-SMOKES-CI-001` as candidate `bad74c80d37e5b57b9f7ae761cc7e7a2af180c29`. Validation run `35555390587` passed policy, x64 host build, eight deterministic no-HMD smoke executables, Win32 game build, package assembly and package validation. Candidate package artifact ID `10620160445`, digest `sha256:8ae8866b0f54255e88c7714bdd00ff2810641b92a70f549e09fa81457d4dbf1c`.
- Integrated the CI-only smoke-test gate as `0eec5ac145dd1b1e75957756c5794d7e12c6c17e`; runtime source code was unchanged.
- Found a new CI utilization gap: dedicated review-branch checkpoint pushes triggered the heavyweight generic Build workflow. Prepared and verified a net one-line candidate adding `vr-d3d9ex-review-*` to `branches-ignore`, then integrated it as `2f9e87c23714376adcc03be5d2f1daeb8a50e8da`. A/C review branch fast-forwards to this commit produced no workflow runs, confirming the exclusion works.
- Rebased stale `VR-HOST-002` onto current integration source without textual conflict by overlaying its nine exact candidate blobs on integration tree. New exact candidate is `f26188501e1da3dd9139c7a32407bd6353da9780`, branch `vr-d3d9ex-candidate/VR-HOST-002-rebase-D-20260921T1151KST`, validation run `35555560993`. Queue status is `NEEDS_POST_REVIEW`; A/B/C must review this exact SHA after deterministic build success before production integration.
- Runtime test scope remains unchanged: one CORRECTNESS test, `TargetRefreshRateHz=0`, `SkyGlowFactor=1`; no new HMD-visible correctness/performance claim was made.
- Exact next actions: consume `35555560993`; collect exact-SHA A/B/C post-review for `f2618850...`; apply Reset/SkyGlow production fixes only through safe complete-source materialization; then minimize the next HMD test to the newest validated CORRECTNESS package.
