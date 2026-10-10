# DX9Ex R84 -> Production Convergence Plan

## 2026-10-10 user override: one R84 functional acceptance unit (ACTIVE)

This section supersedes the historical Gate 2 "one seam per material task", one child AUTO task per seam, and sequential independent seam compile rules below. Those instructions describe earlier investigation/checkpoints, not new production terminal task boundaries. `docs/DX9EX_AUTODEV_PRIORITY_20261010.md`, `AGENTS.md` and `docs/automation/QUEUE_CONTROLLER_CONTRACT.md` are the current dispatch and terminal authority.

**Single feature acceptance:** finish the remaining R33→R32→R31→R30→R29 textual `.cpp` implementation extraction into independently compiled translation units and linkable header/owner contracts; reconcile `cmake.toml` and generated `CMakeLists.txt`, remove obsolete `HEADER_FILE_ONLY` and textual `.cpp` includes, preserve StateBlock/Reset/DirectGPU/stereo/HUD/FFB semantics, add fail-closed structural regression guards, then run a full Win32 compile/link and debug/rebuild until the required exact-SHA DX9Ex Active and Domain Isolation workflows succeed. Reuse existing APPLIED_EQUIVALENT/SUPERSEDED runtime modules; R84 donor stays read-only.

**No micro-finish:** R32/R31 helper extraction, one static test, isolated seam commit, `FEATURE_READY`, CI pending/failed, or a 30-minute chat rollover is a checkpoint, NOT functional DONE. Keep the stable R84 feature/work_key/TASK_ID across all related repairs and multiple bounded commits. Do not skip remaining compilation/debugging by closing a subtask and selecting an unrelated small one. If a real non-HMD blocker cannot be resolved, persist BLOCKED with specific job/error and resume cursor, never SUPERSEDED/DONE.

**Closeout:** Only after the complete source/build ownership change and exact-SHA full-chain/Active/Domain gates are green, set `SUPERSEDED_BY_DX9EX_FOCUS` with material SHA and run IDs. A separate Quest3/VDXR hardware acceptance remains UNTESTED unless actually verified. The Docker worker reads updated GitHub policy at next dispatch; user deploys/reloads the controller separately.


Status: **ACTIVE**  
Canonical production branch: `vr-d3d9ex-focus`  
Plan base HEAD: `bd32098ce0be130aa3a64ca2d507275bf08ab69f`  
R84 donor/reference branch: `vr-refactor-r84-2000c-20261001`  
Recovered donor HEAD: `40e998500fc758dd3b078d9df2ecc2a57a19bc5d`  
Execution environment: **external Docker queue controller**  
Runtime authority: **Quest 3 / VDXR exact-build evidence only**

## Objective

Finish the reason R84 existed: carry its still-valid structural improvements into the current production DX9Ex code without discarding newer fixes that independently accumulated on `vr-d3d9ex-focus`.

R84 is no longer an active development branch and its cycle counter is not a completion metric. It remains read-only evidence until this plan closes it as `SUPERSEDED_BY_DX9EX_FOCUS`.

## Non-negotiable rules

- Never wholesale merge or blanket cherry-pick the divergent R84 branch.
- Rebase reasoning on the latest focus HEAD before every material task.
- One ownership/interface seam per material task; keep changes reviewable and reversible.
- Structural extraction must preserve runtime behavior. It must not silently change Reset/ResetEx order, StateBlock semantics, DirectGPU ACK/fence/slot reuse, HUD/XYZRHW/SkyGlow policy, recenter, effect placement, fallback order, or protected world stereo.
- Use current focus regression knowledge and the upstream-first HUD evidence rule.
- Prefer RED -> GREEN deterministic verifiers for each changed boundary.
- Exact hosted compile/link and required DX9Ex gates must pass before the next seam.
- Do not weaken a verifier merely to obtain green. Classify PRODUCT_DEFECT vs VERIFIER_DEFECT from the intended current contract.
- Runtime claims remain `UNTESTED` until the exact build is tested on Quest 3/VDXR.
- Architecture v3 live authority and downstream DX11/DXVK remain downstream of this convergence.

## Gate 0 — restore a green production base

Queue: `DX9EX-R84-PORT-GATE0-00505`

Current material SHA `28d2f5f37ed1dbeee5b8509d5e29001cc84631d6` changed post-Present unresolved-slot ownership. DX9Ex Active Validation run `37554749168`, policy job `112578296612`, failed because the reset/transport verifier observed a changed bounded publication order.

Required result:

1. Recover the exact source diff and verifier expectation.
2. Decide whether current code violates intended slot ownership, or the verifier encodes superseded ordering.
3. Make the smallest coherent repair; preserve fail-closed behavior.
4. Require exact-SHA DX9Ex Active Validation and Domain Isolation success.
5. Persist a durable run record and only then mark Gate 0 DONE.

No R84 source port starts while Gate 0 is red.

## Gate 1 — R84-to-focus structural inventory

Queue: `DX9EX-R84-PORT-INVENTORY-001`

Create `docs/automation/r84-port/R84_TO_FOCUS_INVENTORY.json` and a concise Markdown matrix. Every meaningful R84 structural unit must be assigned exactly one disposition:

- `APPLIED_EQUIVALENT` — current focus already has the same responsibility/benefit through newer code.
- `PORT_REQUIRED` — still valuable and absent from current focus.
- `SUPERSEDED` — current focus has a newer/better design and the R84 unit must not be ported.
- `DEFERRED_RUNTIME_RISK` — potentially valuable but cannot be safely behavior-neutral without later runtime evidence.

At minimum inspect:

- core dispatch/final/review support APIs;
- R29-R34 hook/interface boundaries;
- screen-space/HUD/XYZRHW interfaces;
- stereo runtime/math facades;
- frame lifecycle/recovery APIs;
- StateBlock/raster/depth ownership;
- DirectGPU transport runtime/facades;
- performance/dispatch telemetry;
- CMake split gates and HEADER_FILE_ONLY ownership;
- `verify_vr_refactor_contract.py` coverage.

The inventory task changes no runtime source.

## Gate 2 — selective seam ports

Queue parent: `DX9EX-R84-PORT-SEAMS-001`

Generate one child AUTO task per `PORT_REQUIRED` seam. Default order:

1. R34 / R33 final-dispatch boundary
2. R33 / R32 review/dispatch-support boundary
3. R32 / R31 support/state boundary
4. R31 / R30 screen-space boundary
5. R30 / R29 stereo-base boundary
6. lower Present/Reset/DirectGPU targets required to remove remaining cross-layer textual ownership

For each child task:

- start from latest focus;
- compare donor implementation and current-focus equivalent callers/lifetimes;
- port interface/ownership only, not stale runtime policy;
- add/repair a fail-closed structural verifier;
- exact hosted compile/link;
- DX9Ex Active Validation;
- Domain Isolation;
- record changed paths, before/after SHA, run/job IDs, and rollback point.

Do not batch multiple seams merely to reduce task count.

## Gate 3 — production graph cleanup

Queue: `DX9EX-R84-PORT-CLEANUP-001`

Only after all required seams compile independently:

- reconcile `cmake.toml` first and generated `CMakeLists.txt`;
- remove obsolete `HEADER_FILE_ONLY` ownership where independent TUs are now authoritative;
- remove textual `.cpp` includes that are no longer required;
- retain exactly one stereo owner and one renderer owner for every configured graph;
- remove gate-only compatibility shims proven obsolete;
- add guards that fail if retired textual implementation includes return.

Require a full exact hosted build/validation pass.

## Gate 4 — closeout

Queue: `DX9EX-R84-CONVERGENCE-CLOSEOUT-001`

R84 may be declared superseded only when:

- Gate 0 is green;
- the inventory has no unclassified meaningful structural item;
- every `PORT_REQUIRED` item is integrated and exact-SHA validated;
- every `SUPERSEDED` / `DEFERRED_RUNTIME_RISK` item has explicit rationale;
- production CMake/source ownership is coherent;
- final structural verifier and DX9Ex Active Validation are green;
- durable state records final focus SHA, donor SHA, validation evidence, and HMD-only obligations.

Closeout value: `SUPERSEDED_BY_DX9EX_FOCUS`.

Do **not** automatically delete the R84 branch after closeout. Keep it as historical evidence until an explicit cleanup decision.

## Docker worker selection algorithm

At every cycle:

1. Fetch current focus HEAD and durable queue/state.
2. Resume any immutable in-progress material task first.
3. If Gate 0 is not DONE, work only Gate 0 (or an independent critical safety regression needed to unblock it).
4. Otherwise choose the highest-priority executable `DX9EX-R84-PORT-*` item with all dependencies DONE.
5. If a parent seam item needs decomposition, create exactly one bounded child task and complete it through validation before creating the next.
6. Never create filler tasks/cycles because the donor campaign once had a numeric cycle target.
7. If a task becomes genuinely HMD-only, mark the exact gate and continue another structurally independent `PORT_REQUIRED` item.
8. After closeout, return to the normal DX9Ex/HMD/Architecture-v3 queue.

## Protected visual/runtime obligations after convergence

Structural green is not visual/runtime green. The following remain separately tracked until exact HMD evidence resolves them: doubled/head-follow white HUD/menu text and selectors, rival/rank marker anchoring, 4th/5th rank duplication, +TIME/checkpoint/goal/result duplication, gameplay F11 menu diplopia, lens flare/start shadow regressions, recenter, and dense-building/sand/spray frame-time behavior.
