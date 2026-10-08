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
- **CI**: DX9Ex Active `37741691863`, EXE HUD Inspector `37741691867`, Domain Isolation `37741692068` all SUCCESS for code SHA; Full Source Impact `37741692064` **SUCCESS** (Win32 game and x64 host MSVC /analyze included). All four runs verified the same material SHA. Package artifact `11533599078` sha256 `c7909cb0511373bc27bb56bc679069ba0326d83257f8d1d48b3b61f512797ef7`.
- **Runtime remains UNTESTED**; historic 00519 Quest3/VDXR HMD visual failure still OPEN until one exact-build test. Other HUD symptoms (lens, +TIME, finish record, c64 provenance) are not automatically declared fixed solely because the original exact CALLs and all-node ownership pass static CI.

## LENS +TIME +GOAL ORIGINAL EXE 2026-10-08 — source repair

- [Deep original-mod / canonical OR2006C2C.EXE / fork renderer reconciliation and P0 source repair](automation/reviews/AI2_QUEST3_LENS_TIME_GOAL_SOURCE_REPAIR_20261008.md).
- **Material SHA `5011d1e7ca53d73b2cffc7e841dc39e5a57aa6c1`**: exact EXE lens `0xCABE` / original `Clr_SceneEffect` semantic now owned in fixed-function `R30ConfigureXyzrhwWorldEffect` as well as the preexisting shader proof. Nonflat RHW/depth effect remains spatial; flat no-depth effect is finite world-fixed HUD plane (no broad alpha heuristic). Original upstream 0.05 near-plane override/restore unchanged. Shader `ScreenHud` +TIME/checkpoint/goal glyph draws no longer lose R30 owner from stale verified-world/R28 state; exact world gate remains for `semanticWorld`. Stage/result `Sumo_Printf` `0x975EE/0x97727/0x977FB` glyph `0x2C808/0x2C9DB` and clip `0x97BB7/0x97DA7` use original CALLs with full sibling `ScreenHud` tagging.
- Existing 71 exact HUD CALL binary signatures, newer original rank/rival repair, and prior parallel `CONVERSION-DX9EX-00552` scene/cube DDS original-header fallback retained. P0 exact-owner self-check includes four **different** single-fault injections; no 1000/5000 unchanged-source tests.
- Exact material **DX9Ex Active 37745084656 SUCCESS** (Win32 game/host/R33/package), **EXE HUD Inspector 37745084596 SUCCESS**, **Domain Isolation 37745084546 SUCCESS**; Full Source Impact `37745084597` **SUCCESS** (game+host MSVC analyzers). All four exact material CI gates SUCCESS. Packaged artifact `11535334283` sha256 `a78b81a36332b0300e1f6bb7208c39529a7c1cdb052f1e5835d832cedf5d1169`.
- **Quest 3 / VDXR:** `RUNTIME_VALIDATION=UNTESTED`. Historical 00519 headset failure remains OPEN until user runs this exact SHA. Source-level fixes cannot prove actual HMD optical convergence; lens source `0xCF4E` projection/skyglow and game-specific final scene pacing need real single-build observation.

## 2026-10-08 — Original lens producer windows + Sumo masked replay lifetime (AI 2)

- [Durable, resumable deep review with raw original-mod / canonical EXE / active R26+R30 evidence and all intermediate C0-C4 checkpoints](automation/reviews/AI2_QUEST3_LENS_TIME_GOAL_DEEP_AUDIT_CONTINUATION_20261008.md).
- Disassembly P0 correction: exact lens `0xCABE` DrawObjectAlpha call lies **before** the separately declared `0xCAE0` Calc3D2D producer region containing `0xCF4E`. Previous inspector coupled two different producer windows without validating address containment. Current analyzer splits the windows and validates actual canonical `CALL E8 rel32` → `0x56D0` and `0x49940`. Do not assume the two source points share one projected light anchor without additional XREF proof.
- Replay memory fix: `src/hooks_framerate.cpp::SumoUISpriteReplay` formerly kept shallow `SPRARGS2::child_B4` pointers to the original per-frame SpriteNode pool; now captures bounded independent mask chain copies for `kind_C==1`, detects repeats/cycles and excessive chains, and skips invalid replay rather than dereferencing reclaimed nodes. HUD Inspector + Active both execute four **distinct** deterministic negative tests via `tools/verify_vr_sumo_replay_semantics.py`. Do not change original 0x43FA10 extension-time expiry logic.
- Latest code material `3ae95aaf2492336724828992147c3cba824fd1af`, test-only refinement `02f3ab062708fbb385668376ab1b4781d000263f`; same edits are present in concurrently advanced 00558 integration SHA `b14901f8b70b1b6fda8a9aded1e340147a453e68`. DX9Ex Active `37752619285` / HUD Inspector `37752619496` / Full Source Impact `37752619267` (Win32 game and x64 host MSVC analyze) / Domain Isolation `37752619334`: **all 4 SUCCESS on exact integrated code SHA**. Validated ZIP artifact `11538619117`, sha256 `6085109d2fb0664d4e6cd645d1cf72b2b21e20a5910580c4ddf4e4eeadb75ad1` (2,750,394 bytes). Runtime visual HMD UNTESTED.
- Quest3/VDXR `RUNTIME_VALIDATION=UNTESTED`; historical 00519 HMD lens/+TIME/goal visual FAIL remains open until one exact candidate is tested. Code/source static success is not optical acceptance.

## 2026-10-08 — AI 2 whole-regression original/EXE/current-source deep research handoff (documentation only)

- **Required before the next related source patch:** [Checkpointed original-mod + canonical EXE producer + current DX9Ex renderer cross-research](automation/reviews/AI2_DX9EX_RUNTIME_EVIDENCE_DEEP_RESEARCH_20261008.md). C0/C1/C2/C3/C4 checkpoints were independently committed to `vr-d3d9ex-focus` so a chat/controller restart can resume by GitHub alone.
- The report cross-maps lens/SceneEffect, +TIME/checkpoint/goal/result, 6th/6 and other white HUD, 1–5th/rival markers, option arrows/YES-NO, F11 external ImGui, DDS/car selector, start shadows, SkyGlow, recenter, frame cadence to original calls, EXE rel32 contracts, currently applied source repairs and distinct remaining tests.
- Treat **already source-fixed/CI-verified paths as protected**, not as new unpatched findings: 00557 nested near-plane, 00558 negative clipW, fixed-function lens, ScreenHud owner precedence, Sumo deep mask replay, all-node glyph/rank tagging, ImGui XYZ orthographic L/R and DDS original fallback. The historical 00519 HMD failure stays OPEN; **new source changes require new evidence and Quest3/VDXR acceptance**.
- Research-only commit: this addendum and the linked report do NOT change D3D9 game/host source, do NOT rerun unchanged HUD 1000/5000 audits and do NOT imply a successful headset test.
