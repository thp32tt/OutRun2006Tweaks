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

## Runtime handoff — 2026-09-24 01:50 KST

- Source tested: `8d21824f9502b3354fae679972a90868a0cce562`, R51 EXE-map HUD producer candidate.
- PC clean build run: `35888306771` SUCCESS; package SHA256 `701a57ca5e4a1ba413bcdd75ad6fc6ecc320f6fc3dbb0dbd5a0597cb6ba81d89`.
- HMD session: `PC-R51-HUD-MAP / A_CONTROL / CORRECTNESS / 20260923T164207853Z-2202b186`.
- Result: world 3D preserved, intended HUD/rank corrections failed.
- Key evidence: `semanticHudAccepted=93681` while renderer `semanticOverlayBypass=0`; white/rank HUD still doubles and follows head; vehicle rank markers remain detached/head-locked.
- Next scheduled-run priority: static ordering analysis for HUD semantic lifetime at c64 and EXE-map anchor-flow analysis for rival rank markers. No new runtime candidate until the ordering gap is explained.
- User ended the PC-runner session. Self-hosted PC builds are forbidden until explicit re-authorization; overnight scheduled tasks may continue review/static analysis and normal cloud CI.

