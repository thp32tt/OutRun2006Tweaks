# DX9Ex P0 Visual Composition Convergence

Status: ACTIVE / NO HMD CANDIDATE

## Trigger
DX9Ex 00519 (9a3e08cc62b6a36a8196936eacead8cc08fcc756) is USER_RUNTIME_FAIL: menu/car-selection textures missing; HUD/rank/rival/+TIME/menu arrows/YES-NO/lens flare doubled or head-following; performance not accepted.

## Evidence order
1. Original emoose/OutRun2006Tweaks hooks_uiscaling/hooks_graphics/interpolation/game_addrs.
2. Fork R65-R74/R73-era HMD history and regression ledgers.
3. Canonical OR2006C2C.EXE identity + disassembly/XREF/byte contracts.
4. Current producer -> SpriteNode -> replay -> queue -> fixed-function/VS draw ownership.
5. Deterministic static verifier.
6. Quest 3/VDXR only after 1-5 are green.

## Closure matrix
- Menu/car-selection textures: MANAGED LockRect must remain compatible; translated DYNAMIC textures must not waste bounded CPU-shadow memory.
- Screen HUD: exact ownership for rank/position, gear/rev, time/goal/results/+TIME/checkpoint, hearts/rival/ghost/C2C, menu arrows, YES/NO, 6th/6 and glyph paths.
- Vehicle markers: rank 1st-3rd, 4th+ clip digits and rival marker preserve Calc3D2D payload; fixed-function XYZRHW and shader/c64 paths both support ProjectedWorldMarker2D.
- Lens flare/SceneEffect: reconcile original camera/z-near/interpolation path with current R29/R30 ownership; no broad alpha heuristic.
- F11 overlay stays external and cannot consume game semantic tokens.
- World stereo remains protected; no blanket queue-to-ScreenHud.
- Launcher proves canonical EXE semantic identity before launch and packages analyze_outrun_assets.py.

## Exit gate
tools/verify_vr_visual_composition_p0.py plus canonical binary/HUD cadence/producer provenance/cross-thread registry/projected marker/Sumo replay/recenter/reset-transport/Domain Isolation gates must all be green before another HMD candidate is requested.

## Cross-domain source review (2026-10-08, AI 2)
- Before attempting another HUD-only correction, read [the 150-file game/host source screen and targeted ownership/error-path review](automation/reviews/AI2_QUEST3_CROSS_DOMAIN_SOURCE_REVIEW_20261008.md). It distinguishes the **packaged R26+HUD/R23 owner** from CI-only R33, exact HUD c64 upload-vs-node-draw timing, generic-overlay live-c64 use, R30 lazy VB/IB shadow fallback, off-path world semantic tokens, F11 presentation-state predicate divergence, and UI DDS replacement vs original fallback / R15/legacy-XMT resource failures.
- New assertions should be **one targeted negative contract per proven defect**, never unchanged-source 1000/5000 repetitions. A static pass is never Quest 3 visual proof; `RUNTIME_VALIDATION=UNTESTED` until the exact candidate is headset-tested.

## Second AI2 whole-render-lifetime review (2026-10-08, 14:17 KST)
- [Second independent Quest3 cross-domain deep review](automation/reviews/AI2_QUEST3_SECOND_30MIN_RENDER_LIFETIME_REVIEW_20261008.md): pinned ImGui DX9 FVF XYZ/orthographic fixed-function Draw **falls outside both active R30 stereo HUD owners** despite F11 semantic scope, then enters lower R9 unchanged-transform non-world replay. Also documents unscoped rank/rival projected anchor validity, tick/interpolation/replay skew, untagged XYZRHW screen-Z world promotion (and host world-stereo readiness contamination), uncapped process-global VB/IB CPU shadows, inherited shallow sprite pointers, and fixed-function SceneEffect gap.
- Treat the prior DDS original-retry finding as **source-fixed in CONVERSION-DX9EX-00551**, exact material a440a6ff386a... static CI succeeded, HMD still UNTESTED. Never repeat unchanged HUD 1000/5000 loops; use one negative contract and a frozen Quest3 test after each relevant source change.

## 2026-10-08 — review-to-source P0 remediation (AI 2)

- [Implemented two-review Quest 3 remediation and evidence status](automation/reviews/AI2_QUEST3_P0_REVIEW_FIX_IMPLEMENTATION_20261008.md) on `vr-d3d9ex-focus`. Active R26+HUD now owns **only explicitly scoped gameplay F11 ImGui fixed-function XYZ/orthographic** through two-eye finite recentered projection, with eye-adjusted per-command scissor and complete state restoration. No broad menu/selector/world XYZ promotion.
- R30 adds **64MiB total CPU VB/IB shadow cap**, skips unneeded capture during F11 external overlay, and separates untagged flat RHW=1 inferred effects from **host-authoritative world-stereo evidence**. Existing confirmed world semantics remain permitted.
- P0 static verifier checks these exact owners and has six **distinct fail-before source mutations**; Active/HUD/Full Source workflows now watch `external/imgui` and `.gitmodules`. No 1000/5000 repeated static loops.
- The parallel `CONVERSION-DX9EX-00551` original DDS restore fix remains a separate already applied change; no redundant recreation.
- **Status:** source committed at material `f2e290417fe9e4f6f822f0009feca7410103adf7`. Exact material CI and Quest3/VDXR must be reported separately. Original user `CONVERSION-DX9EX-00519` HMD FAIL still applies until one exact-build visual retest; `RUNTIME_VALIDATION=UNTESTED`.
- Not auto-modified without proof: car-specific Calc3D2D anchor freshness, c64-before-SpriteNode HUD ownership, fixed-function lens SceneEffect, R15 partial texture copy, inherited upstream Sumo pointer lifetime, and pinned ImGui atlas failure handling. Review report states precise log/negative test needed for each.

## 2026-10-08 — RANK/RIVAL ORIGINAL CALL reconciliation (AI 2)

- [Original emoose ↔ current fork / exact canonical EXE 71 CALL rank, rival and shared HUD repair](automation/reviews/AI2_QUEST3_RANK_RIVAL_ORIGINAL_ADDRESS_RECONCILIATION_20261008.md).
- Production material `79a0dcb7495d7a8af9eb0d410d716bf72f024444`: original `0xBAD20` rank producer entry now owns/clears each car's Calc3D2D projected sample and discarded subpixel offset; exact `0xBAEE7` rank Calc capture is gated against NaviPub screen-HUD callers. Old rank animated siblings are preserved; 4th/5th+ `0xBB21F..0xBB2D0` clips and exact-address menu/result ScreenHud clips now tag **all** generated SpriteNode siblings and only edit SPRARGS `kind_C==0` position floats.
- Rival `0xBB6F5` producer → `0xBB796` original CALL now passes a **single consumed projected anchor** to all generated nodes (no implicit stale last-car sample), keeping `WorldBillboard` fail-soft and full no-tick Sumo replay payload.
- **CI**: DX9Ex Active `37741691863`, EXE HUD Inspector `37741691867`, Domain Isolation `37741692068` all SUCCESS for code SHA; Full Source Impact `37741692064` source and host-analysis SUCCESS with game analysis pending when first recorded. Package artifact `11533599078` sha256 `c7909cb0511373bc27bb56bc679069ba0326d83257f8d1d48b3b61f512797ef7`.
- **Runtime remains UNTESTED**; historic 00519 Quest3/VDXR HMD visual failure still OPEN until one exact-build test. Other HUD symptoms (lens, +TIME, finish record, c64 provenance) are not automatically declared fixed solely because the original exact CALLs and all-node ownership pass static CI.
