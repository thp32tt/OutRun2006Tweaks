# DX9Ex functional-feature completion gate — 2026-10-10 21:40 KST (top precedence)

- **User directive: work and debug by COMPLETE FUNCTION, not one tiny change per finished work item.** Applies to autonomous C DX9Ex and controller dispatch. Read `docs/DX9EX_AUTODEV_PRIORITY_20261010.md` and `docs/automation/QUEUE_CONTROLLER_CONTRACT.md` latest active feature-scoped sections at every dispatch. These override older single-seam/small-task terminal practices.
- Keep one stable FEATURE_ID / work_key / TASK_ID for a functional deliverable across multiple meaningful code commits, local negative tests, integrated Win32 build/link, error repair and same-SHA DX9Ex Active + Domain Isolation CI. Only the feature-level acceptance checklist all-green can reach DONE_BUILD_VERIFIED; `FEATURE_READY`, `PENDING_CONTROLLER_EXACT_SHA`, partial compile, one passing test, a skipped/failing required job and chat rollover are not completion. Resume the same TASK_ID on error or rollover, respecting existing live claims; never increment score for partial micro-commits or retry.
- **R84 is one whole outstanding feature:** finish remaining R33→R32→R31→R30→R29 independent TU/headers/lower-symbol boundaries and cmkr/CMake/HEADER_FILE_ONLY reconciliation, full Win32 compile/link, fix build failures, pass relevant exact-SHA gates, then close `SUPERSEDED_BY_DX9EX_FOCUS`; no per-seam terminal DONE. Existing working hook/state/FFB/HUD behavior and immutable rollback are protected.
- Repair true blockers under the same feature; classify irrecoverable cases BLOCKED with exact evidence, not DONE. Quest3 hardware remains UNTESTED until actually exercised. DX11 A continues independently, DXVK B stays frozen. GitHub policy commit is NOT proof of live Docker reload; deployment is done by the user.
- Known nonterminal example: DX9Ex 00590 SHA dbf6678e had `FEATURE_READY` yet DX9Ex Active run 38051682030 failed the R31 Apply-generation verifier, skipping full-chain work. Treat it as pending repair/validation, not a completed function.

# Effective backend execution policy (2026-10-10; supersedes older cross-lane freezes)

- **A DX11 Native ACTIVE** at `vr-dx11-native-r71`, highest global conversion priority; independent A development MUST NOT wait for DX9Ex visual, R84 or Architecture v3 Quest3 acceptance.
- **C DX9Ex ACTIVE concurrently** at `vr-d3d9ex-focus`. Latest user instruction: P0 unresolved VR optics/HUD correctness; in parallel P1 finish finite remaining R84 structural optimization (physical hooks, state ownership, device reset/lifetime, redundant work), OpenXR per-eye sizing and measured performance. Do not treat a 50% effort target as a quota or endlessly extend R84. Working FFB v0.2/gamepad input is frozen except proven integration regression. Follow `docs/DX9EX_AUTODEV_PRIORITY_20261010.md` for acceptance and no scope creep.
- **B DXVK FROZEN** for new development/build/distribution/promotion until an explicit later user decision. DX12 reference-only. Do not edit FFB upstream or localization from C.
- **Immutable DX9Ex rollback baseline**: `dx9ex-baseline-20261010` at `fcd18ddd89f6dd40a8246fcf8591f086811149f1`; never mutate or reset.
- **Policy precedence**: the latest user-directed `docs/DX9EX_AUTODEV_PRIORITY_20261010.md` and this header override contradictory historical FFB-first, R84-unbounded, allocation quota, queue and controller text. Update controller deployment separately; document changes do not prove a live worker reload. Historical technical evidence, HMD acceptance gates and regression cases are NOT deleted.
- **DX9Ex Architecture v3** acceptance gates only DX9Ex live IPC promotion, not separate DX11 A source work. B DXVK does not auto-unfreeze when an XR/HMD/Architecture gate passes.
- **GitHub actual-state controls**: verify latest remote HEAD, active claim/work_key/file overlap and exact-SHA Actions. No status-only commit that cancels an active CI run; a C0-C6 source result does not prove Quest3/VDXR gameplay. Controller deployment/parallel runtime must be independently checked; documents alone do not prove it.

## VR integration of finalized FFB — 2026-10-10 (user-authorized exception)

- FFB development is complete. **Do not edit the original FFB release, its dedicated branch, or its source files as a separate development task.** The approved integration target is `vr-d3d9ex-focus` only.
- VR must integrate the **completed FFB v0.2 source implementation**, not replace it with stubs, a partial adapter, or documentation-only knowledge transfer. Preserve the exact finalized FFB implementation in VR unless an integration-specific change is demonstrably required; any such change belongs to VR integration and must not propagate back to the FFB original.
- The existing VR integration commit `1b12a55f2ae277da7c8a545ca37ce8059ba891d1` already copied nine v0.2 files. Continue by resolving build, initialization, input, linkage and runtime integration on VR. Do not revert the imported files solely to satisfy the historical domain guard.
- The current `tools/verify_domain_isolation.py` forbids FFB-owned file edits on VR. This user-approved **finalized FFB-to-VR integration** is a narrow, auditable exception: permit only exact, pinned release-v0.2 source copies on the VR branch (verify content SHA against release), or documented integration-specific edits, without relaxing restrictions for localization, DX11/DXVK or future independent FFB development. Update the guard with targeted tests; do not disable the guard globally.
- Maintain protected DX9Ex visual baseline and keep HMD runtime validation `UNTESTED` until actually measured. A CI PASS alone does not prove wheel hardware compatibility.

## DX9Ex autonomous development allocation override — 2026-10-10

This is the latest user-directed allocation override and supersedes the 2026-09-29 DX9Ex maintenance-only / <=10% allocation restriction and any older P0 freeze that would prohibit authorized new DX9Ex work. This is an engineering-effort target, not a CI scheduling guarantee.

- **DX9Ex autonomous development allocation: 50%** of VR backend engineering effort. DX9Ex is ACTIVE, not maintenance/reference-only. Other backend lanes remain isolated; rebalance remaining effort without silently disabling DX11/DXVK or localization.
- Freeze the latest user-accepted DX9Ex build as a protected rollback/visual-regression baseline; new development must occur as forward commits on `vr-d3d9ex-focus` without silently overwriting or claiming a new HMD-accepted baseline.
- **P0:** Port the latest released wheel FFB implementation, preserving existing VR input and isolating FFB changes. Confirm release provenance and interfaces before modifying.
- **P1:** Finish DX9Ex structural optimization/refactor, preserving proven HUD, stereo, device-reset and lifecycle behavior.
- **P2:** Follow Virtual Desktop/OpenXR recommended per-eye render resolution safely; handle D3D9Ex reset and resource lifetime. Do not equate desktop resolution with per-eye extent or silently double the backbuffer.
- **P3:** Optimize frame pacing/performance toward **120 FPS on RTX 4070 with Virtual Desktop High**. This is a measured runtime target, not a source-CI PASS claim; retain scalable settings.
- Outstanding GOAL/+TIME, rank attachment and central lens visual faults remain tracked regression/P0 safety gates, not grounds to suppress the new development priorities. Preserve user-confirmed visual PASS and do not promote an HMD-UNTESTED candidate as accepted.
- Each development turn must produce meaningful implementation and focused validation where feasible; never count status-only reviews, repeated same-SHA CI, or bookkeeping commits as feature completion. Preserve `RUNTIME_VALIDATION=UNTESTED` until actual exact-build Quest 3/VDXR testing.
- GitHub is source of truth; follow existing domain isolation, exact-SHA CI, rollback and N100 storage rules. No repeated 1000/5000 HUD static audits.

## 2026-10-10 exact ORIGINAL EXE P0 GOAL/+TIME/central lens material

- Read `docs/automation/reviews/DX9EX_P0_GOAL_EXTTIME_LENS_ORIGINAL_DISASSEMBLY_FIX_20261010.md` and the original ELF/PE-independent x86 artifacts from `tools/disasm_outrun_goal_flare_p0.py` / OutRun EXE HUD Inspector. Verified original SHA `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`; do NOT infer producer identity from alpha, color, or generic queue.
- **GOAL 0–99% (93% photo)**: separately own 19 verified original `0x97xxx -> 0xB9200` E8 **result/record text** calls with `ProducerToken::ResultTextB9200, ScreenHud`. The `0x97BE4/0x97DEC -> 0x2D200` percent animation is a distinct group. Leave final 100% results and BOTH GOAL helpers `0xBEA5A/0xBEA5F` untouched.
- **In-game OutRun course-change +TIME** candidate: **SIX original source E8**: sprite `0x9898E/0x98A36/0x98AC6 -> 0x29530` IDs `0x2C00B4/B5/6C` **and separate numeric text `0x989AD/0x98A89 -> 0x973C0`, `0x98A10 -> 0x974E0`**. The later output calls were revealed by expanded canonical x86 disassembly, and all six need one atomic hook/rollback. `ProducerToken::StageExtensionTime` tags only actual newly queued siblings as ScreenHud. No time counter, world render, or original animation suppression; exact targets verified but ID-to-user `+TIME` HMD optical proof pending.
- **Lens CENTRE only** candidate: disasm proves `0xD3A0` object `0x570002`, `0xD3A5 -> 0xC980 -> DrawObjectAlpha_Internal` separate from already-scoped outer discs `0xD5F5..0xD796 -> 0xC9A0 -> 0xCABE`. Change ONLY `0xD3A5..0xD3AA` to exact temporary WorldBillboard and restore. 3–4 outer discs PASS and NEVER remap globally. Preserve upstream mod Clr_SceneEffect temporary 0.05m near clip.
- Exact-SHA CI source is `36fe4f117213f77863abdf5a061dc6cc5b7bf754`, DX9Ex Active workflow `37959849499`, Inspector `37959849553`; check actual SUCCESS before creating user build. CI build only checks source contract; **all new optics `RUNTIME_VALIDATION=UNTESTED` until one later user HMD test**.
- Do not undo HMD PASS in 6th/6, menus, car selection, rival icon, final GOAL 100%, outer flare discs, F11, and recenter. Avoid 1000/5000 duplicate loop tests or unattended claims.

## 2026-10-10 P0 DX9Ex deep research material — source fixes are NOT an HMD pass

- **Read** `docs/automation/reviews/DX9EX_DEEPRESEARCH_P0_20261010.md` and prior `DX9EX_HMD_FEEDBACK_20261009_2348_RANK_TIME_PERF_RESOLUTION.md`. Preserve exact a6f8497 optical successes and distinguish 93%-GOAL animation from completed results.
- 1–5 **car-detached** ordinal: source `b9e26c25d8e95d01b9aa56fcdd018d18d6ffe647` adds exact `RankMarkerSubActiveDepth` authority as **OR fallback** for `Calc3D2D` 0xBAEE7 while NaviPub ScreenHud is excluded. Negative test `8403708c...`. This is a runtime-risking candidate, **UNTESTED in Quest3**; never claim actual vehicle attachment or change already-good OutRun rival.
- True SkyGlow GPU-work mismatch: two HMD launch profiles forcibly overrode game default SkyGlowFactor **4** to **1** (full-resolution vs quarter width/height), during observed 90Hz frame spikes. Restore launcher's factor 4 without disabling effect; VR Test Policy `37955227606 SUCCESS`. Still must compare runtime before claiming FPS improvement.
- Exact result 93% progress and OutRun `+TIME`: original distinct producers `0x97BE4/0x97DEC` vs `0x975EE/0x97727/0x977FB` have bounded queued-priority/phase diagnostic only; leave both GOAL original helpers `0xBEA5A/0xBEA5F`, completed screen, game time/logic unchanged. Existing earlier source tagging is NOT a proven optical solution.
- Lens original `EXE+0xCABE`: bounded `VR P0 FLARE OBJECT` id/alpha/flags logging identifies which child of ~4–5 flares might be centre; all actual draw paths unchanged. Need exact centre optical/draw ownership before a targeted fix; other 3–4 discs are USER PASS.
- Headset sizing: OpenXR recommends a **per-eye** extent, not desktop dimensions; `[VR] RenderWidth/RenderHeight` is already opt-in manual, not automatic. Do not silently upgrade game backbuffer to combined 2x eye extent without negotiation, D3D9Ex reset generation and performance gate.
- `RUNTIME_VALIDATION=UNTESTED` for all new code. Validation status per exact SHA only; no 1000/5000 repeated static tests. Do not ask the user to repeat the earlier same-SHA test.

## Latest authoritative HMD correction — 2026-10-10 KST (second attached a6f8497 session)

**Read first:** `docs/automation/reviews/DX9EX_HMD_FEEDBACK_20261009_2348_RANK_TIME_PERF_RESOLUTION.md` new 2026-10-10 section. USER CONFIRMED: final result progress rise = map/course title + time **both doubled and head-locked**; once progress fully completes = same title and time **normal HUD**. Lens flare = ~4–5 discs, **centre dot only** doubled/headlocked, remaining circles NORMAL. Earlier blanket "GOAL panel and time normal" is superseded, not an excuse to modify the completed-result working path. `+TIME` stage transition remains an independent failing animation, ranking 1–5 remain car-detached, while rival, 6th/6, menu YES/NO/arrows, car DDS stay normal.
**Runtime evidence**: `20261009T150616372Z-f33c5859` same material `a6f8497c2fbe83959984275c30fbf43aa6a72d55`, GOAL state=19 initial `producer=NONE scope=SCREEN_OVERLAY_2D` at 00:12:10/13 followed by `TEXT_GLYPH_PUTSPRITE scope=SCREEN_HUD` at 00:12:16. Mixed ownership is only a diagnostic *lead*, not proof which exact map/time glyph was malformed. `VRLensFlareProjected2D` installation alone does not isolate the central disc. Distinguish progress vs final in real output, do not globally remap untagged GOAL overlays or all flare discs; preserve both GOAL helper calls.
**NO_AUTO_OPTICAL_PASS**: analyzer's `status=OK` and zero R32 spikes cannot override direct headset FAIL. Do not repeat identical 1000/5000 static tests or require another identical-build user HMD trial. `RUNTIME_VALIDATION=UNTESTED` for all subsequent changes.

## DX9Ex Quest 3 2026-10-09 user HMD acceptance — authoritative next-step focus

- Read `docs/automation/reviews/DX9EX_HMD_FEEDBACK_20261009_2348_RANK_TIME_PERF_RESOLUTION.md` before modifying VR ranking, HUD, +TIME, performance or resolution. User tested exact `a6f8497c2fbe83959984275c30fbf43aa6a72d55`.
- **Preserve USER-REPORTED PASS with explicit phase boundary**: 1–5 place digits single/non-headlocked (still detached from cars), 6th/6 normal, menu arrows/YES-NO normal, car-selector DDS normal, OutRun rival attached; **map/course name and time are ONLY NORMAL on the fully COMPLETED final-result screen after the progress meter finishes**. During progress rise **BOTH duplicate and head-follow**. Never label the entire GOAL/result sequence PASS.
- **Open optical faults**: 1–5 place indicators still do **not follow their cars** (despite stereo fusion); transient OutRun checkpoint/extension `+TIME` doubled/headlocked; **result progress-rising map name AND result time** doubled/headlocked while fully completed result name/time is NORMAL; flare ~4–5 discs with **ONLY centre disc** doubled/headlocked, other discs NORMAL. The rival marker is correct. Avoid blanket 2D->world or all-flare flattening, and never delete either original GOAL helper.
- **Source/runtime evidence**: rank+rival aggregate `projected[semantic=9197,buildOk=9107]` is NOT an ordinal optical PASS. HMD log contains rank producers but *no* rank-only `VR R57 rank Calc3D2D` callback log. First `R62 ... RANK_MARKER_CLIP` was `owner=SCREEN_HUD marker=0`; NaviPub ScreenHud may be legitimate, so establish original producer identity before changing routing.
- **Perf and resolution**: 88 R28 Present windows, 63 had max over 11.111ms at headset 90Hz; session max 29.917ms, old R32 spike count zero was a diagnostic false-clear. Game default/backbuffer was PC-monitor `3440x1440`. Opt-in `[VR] RenderWidth/RenderHeight` now permits independent internal source size; BOTH=0 deliberately keeps desktop source by default to avoid worsening measured frame drops. This is **not** automatic XR recommended-size selection. Mirror window scaling must not rewrite eye textures.
- One Quest3 HMD session already completed tonight; no repeated same-SHA optical test. New source CI PASS is not an HMD proof. Avoid duplicated 1000/5000 static verifications.

## DX9Ex 2026-10-09 deep source review: LINK_TIMEUP/GIVEUP and GOAL time source parity

- Read `docs/automation/reviews/DX9EX_DEEP_GOAL_TIMING_MULTIPATH_REVIEW_20261009.md` and `docs/automation/reviews/AI2_GOAL_ENDTIME_WHITE_ALPHA_STEREO_CAUSE_REVIEW_20261009.md` before restoring HUD: **race-end GOAL/TIMEUP white time doubles immediately BEFORE restart; restart/TRYAGAIN itself is correct mono 2D; +TIME was the one remaining historically unresolved item after later 6th/6 and car4/5 successes**.
- Source-proven missed state: x64 host and `Game::is_vr_gameplay_presentation()` classify `GIVEUP` and `LINK_TIMEUP` as Gameplay, but broad `Game::is_in_game()` excludes both. R7 `GameplayActive()` now explicitly allows **only** these extra host whitelist states after original GAME/GOAL/TIMEUP/WARP/RESTART checks; still excludes TRYAGAIN/OUTRUNMILES and retains START progress==65. Source material `55845904f243c6b5f39cb490ffbad30e780b7fb0`; regression test `a7f832a667efd10b379f4ace38d00149505af707`. Do not call this HMD-proven time fix.
- Two canonical GOAL sprite parents `0xBEA5A->0xBE020` and `0xBEA5F->0xBE150` now have distinct `ProducerToken::GoalTime020` and `GoalTime150` through queue/c64/draw logs. Tokens are **diagnostic only**; both retain `ScreenHud`, original helper ABI and all-sibling tagging. Never authorize world/HUD routes from token or white/alpha evidence.
- Original upstream 15 `DispTimeAttack2D` right-scroll midhooks at `0xBE5CD..0xBE9A3` were **intentionally replaced**, not accidentally dropped: current exact E8 `put_clip_sprite` calls are each redirected into `ExactScreenHudRight_putClipSprite` with original right-side spacing and all-new-node tags, as pinned by `VR_BINARY_CONTRACT.json`/EXE Inspector. Do not install legacy midhooks at the same address on top of current E8 hooks.
- **Correct stale source comments:** `R30BuildScreenSpaceEyeConstants` currently maps accepted shader `ScreenOverlay2D` to a finite recentered HUD plane, NOT FOV-only. Its shader original c64 age/identity and fallbacks are different from fixedfn XYZRHW geometry, not simply different HUD plane policy. HMD-proven R62 FVF=0x142 function was compared line-by-line against `945e4471`: unchanged executable code except added read-only logs; its originally successful car4/5 route is a protected baseline.
- Host may still reject LINK_TIMEUP if `R23` authoritative eye/depth baseline cannot seed, or if `RenderFrameStereoComplete`, source pose or ring generation fail: check host `candidateRejectReason/finalLayerKind` and exact GOAL `VR P0 PRE_RESTART_HUD_FORM` before assigning the observed double timer to that state. Current user's GOAL true state is unconfirmed. `RUNTIME_VALIDATION=UNTESTED` until exact HMD run. One bounded relevant verifier per changed SHA; do not spin HUD 1000/5000.

## Optical issue correction: pre-restart GOAL timer, not 2D restart — 2026-10-09

- User **directly reports the restart/TRYAGAIN screen itself is normal mono 2D**. The twice-rendered time is **immediately preceding it on GOAL/TIMEUP before restart**. Do not claim the Game::is_in_game vs Theater state-parity code fix `8b4a3b0e` solved this observed timer. That remains a separate policy consistency fix.
- Historical user report: **car-attached rank 4th/5th and 6th/6 eventually fused correctly**, after multiple revisions; subsequent known-good lineage left **only transient +TIME** unresolved. R62 specifically proves 4/5 while its own 6th/6 still failed; recover later exact source rather than invent a golden SHA.
- White/semitransparent finish text may travel **(a) VS shader/c64, (b) fixed-function XYZRHW, (c) no-VS indexed D3DXSprite FVF 0x142**. Callers `0x975EE/97727/977FB` stage glyph, `0x97BE4/97DEC` progress, `0xBEA5A/BEA5F` GOAL, and `0x2C808/2C9DB` glyph are *different* producers. Compare strict source token+SpriteNode+no-tick replay+WVP/pose+per-eye draw and live GOAL vs mono Theater state. **Do not infer ScreenHud from alpha/color/blend** or globally change game timer `fn43FA10`.
- Historical R73 `R73OutRunTransientHudActive` GOAL/result generic queue owner is absent from current R84; do NOT blindly re-enable 360-frame global promotion, since R73 still had an unresolved +TIME path. Verify which exact result child loses parent tagging first.
- Review permanent source comparison `docs/automation/reviews/AI2_GOAL_ENDTIME_WHITE_ALPHA_STEREO_CAUSE_REVIEW_20261009.md` and updated `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`. `R30TracePreRestartHudDrawForm` provides per-state/per-original-parent three-route read-only FVF/alpha/VS source identity with one-shot bounds; guard `tools/verify_vr_visual_composition_p0.py` against three source-route losses. An HMD optical pass **requires actual user headset confirmation**; source CI success is not enough.

## Whole-source / result Theater / +TIME recurrence guard — 2026-10-09

- Mandatory read: `docs/automation/reviews/DX9EX_FULL_SOURCE_RESULT_EXTTIME_AUDIT_20261009.md`, `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`. Source inventory 580 GitHub blobs/274 source-like paths, trace **producer + original CALL → registry node + no-tick replay → DX9Ex R7/R23/R26/R29/R30 shader vs FVF0x142 → raw c64/latched pose → OpenXR host projection/theater final layer**. Do not claim a full 274-file line-by-line review when only path inventory is complete.
- Proven host/game **render-mode disagreement**: `Game::is_in_game()` contains `TRYAGAIN/OUTRUNMILES` while shared `Game::is_vr_gameplay_presentation()`, `CurrentPresentationMode()`, F11 and x64 host call them mono Theater. Lower `stereo_renderer_r7.inc::GameplayActive()` must check shared presentation **before broad in_game**, as restored in `8b4a3b0ee808018284a0d9148d96d04c442871bf`; keep GOAL/TIMEUP world stereo and original START/WARP/RESTART restrictions. Verify with `tools/verify_vr_visual_composition_p0.py` two independent mutation guards. Never display raw SBS game frame in one Theater result/continue quad.
- Pinned original result/+TIME direct calls: stage `0x975EE/0x97727/0x977FB`, final progress `0x97BE4/0x97DEC`, GOAL `0xBEA5A/0xBEA5F`, glyph `0x2C808/0x2C9DB`. `ProducerToken` must preserve bounded original parent through all children/no-tick replay and into shader c64 or R62 fixedfn diagnostics; exact `VR P0 RESULT DRAW ROUTE`, `VR R51 C64/DRAW FINGERPRINT`, `VR R62 FIXEDFN KIND0` distinguish queue loss vs GPU transform rejection. Never rewrite original `Game::fn43FA10(numUpdates)` extra-time logic just to hide image diplopia.
- During an **active interactive development session**, commit actual phase checkpoints to the source review GitHub document at approximately 5-minute intervals, with changed file, exact commit, evidence, CI and blockers. Do **not** invent work for elapsed intervals, repeatedly verify unchanged HUD 1000/5000 times, or promise continued autonomous AI review after the session ends. Future recurrent schedules must be explicitly supported by the scheduling system; mere text instructions do not make code run unattended.
- Preserve developer branches DX11/DXVK/FFB/localization from this DX9Ex scope; mark hardware `RUNTIME_VALIDATION=UNTESTED` until an actual matching user HMD report. CI/source parity ≠ HMD fusion proof.

## HUD user-confirmed known-good recovery is mandatory — 2026-10-09

- **FIRST READ** `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`, `docs/automation/reviews/AI2_DX9EX_HMD_HISTORICAL_REGRESSION_20261009.md`, `docs/VR_REGRESSION_KNOWLEDGE.json` and `docs/VR_R58_HMD_FINDINGS_20260926.md` before any DX9Ex HUD, result, rank, F11, world-stereo, rank projection, launcher, or pipeline changes.
- User's authoritative historical HMD report: **all previously broken HUD except result/extra-time had been working before the refactor**. Do not treat these as novel problems; first identify the successful historical path and precisely compare **producer → all queued SpriteNodes → replay → DrawIndexedPrimitive FVF 0x142 / XYZRHW / shader c64 → per-eye transform → launch-installed binary**. Never fix only one class and declare all HUD done.
- Pin the R62 HMD-proven original fixed-function indexed D3DXSprite owner `R62TryFixedFunctionSpriteIndexed` and its dispatcher (restored in `f2153aa263560c6cf24f0faf6b547db6a2e80052`); preserve R57 `0xBAEE7` rank anchor plus head inverse; keep gameplay F11 in a separate external ImGui path. Protect HMD-working rival marker `0xBB6F5/0xBB796` and car-selector DDS. Result/extra-time was the historical exception, lens centre dot remains distinct.
- Verify original Win32 `dinput8.dll` identity against selected `backends/d3d9`, never trust only `SOURCE_SHA.txt`. PowerShell analyzer and GUI selector **MUST be included** in real Windows Parser::ParseFile CI and run `tools/Test-OutRunVRAnalysisContract.ps1` on changed material. False `status=OK` when canonical rank producer ran but projected stereo counter is 0 is a regression.
- Future developers must update the permanent runbook + machine-readable `docs/VR_REGRESSION_KNOWLEDGE.json` + human `docs/VR_PROBLEM_HISTORY.md` for any new root cause and exact recovered SHA. Run targeted verifier, EXE HUD Inspector, Domain Isolation and DX9Ex Active Win32 game + x64 host + full-chain + package **once per changed SHA**, no repeated HUD 1000/5000. HMD remains `RUNTIME_VALIDATION=UNTESTED` until actual Quest 3/VDXR user test. No source-only optical PASS.
- Rebuilding the old R62 path only restores one proven missing seam; **do not stop there**. Audit the full HUD checklist (6th/6 and HudScale, menus arrows/YES/NO, rank 1–5, F11 gameplay, checkpoint/GOAL/result/+TIME, DDS, rival, recenter and lens separately) against prior HMD working implementation.

## HUD static review budget — 2026-10-08 (supersedes 1000/5000-loop requests)

- **Do not run or re-create the old 1000-cycle / 5000-cycle HUD static audit workflows.** The user revoked the need for repeated passes of an unchanged HUD source snapshot. Remove those push/manual CI workflows; preserve prior results as historical evidence only.
- On a real HUD-related material/contract change, validate **once per exact material SHA** with the existing OutRun EXE HUD Inspector and relevant DX9Ex Active gates. Targeted commands include `tools/verify_vr_hud_exact_callsite_contract.py --self-test`, `tools/verify_vr_visual_composition_p0.py`, and relevant DDS/texture validators. Each validator should run once, not 1000 or 5000 times. The 10 unique intentional mutations in the dedicated self-test remain valid and are **not** repeated 1000/5000 times.
- A genuine failure requires a material fix and then revalidation of the new SHA. A fresh commit or new issue may require another run; retrying an unchanged PASS solely to accumulate cycle counts or score points is prohibited.
- The legacy `tools/audit_vr_hud_1000.py` and `tools/audit_vr_hud_5000.py` scripts and `docs/automation/HUD_{1000,5000}_REVIEW_CONTRACT.md` are retained only as historical records, **not active development instructions**.
- Keep actual HUD visual regressions and `RUNTIME_VALIDATION=UNTESTED` separate from static PASS. Prioritize source fixes, CI proof, and one meaningful headset test of a changed candidate over repeated identical checks.

## Execution location and N100 disk budget policy — 2026-10-08

This policy applies to all AI agents, chats, scheduled automation and retries working on this branch. It restricts **where** work happens; it does not supersede backend/domain isolation, exact-SHA validation, GitHub-only job contracts or runtime test requirements.

1. **First priority, GitHub:** use the authenticated GitHub connector/API for source of truth, file reads/edits, history, branches, commits and GitHub Actions CI/artifacts. Do not clone to inspect files that the connected GitHub tool can fetch. For conversion jobs explicitly marked GitHub-only, remain GitHub-only.
2. **First priority, ChatGPT-local:** use the ChatGPT ephemeral local runtime for analysis, temporary files, transformations and supporting tests that can run there. Remove disposable local outputs after use. Do not infer that a GitHub-only job permits local Git state as authority.
3. **Second priority, N100:** use N100 only when GitHub/ChatGPT-local cannot do a necessary task, or the task requires an N100-resident running service, user-owned file, hardware or network context. Keep N100 operations lightweight and scoped; avoid repeated large builds, bulk scans, image conversion and storage duplication.
4. **Default-deny new N100 checkouts:** do not run `git clone`, `git worktree add`, duplicate full trees or download HD DDS/large archives to N100 just to investigate or build. An exception requires a documented `N100_EXCEPTION_REASON`, exact user-owned target path, estimated maximum bytes, necessity, and cleanup condition. Reuse an existing checkout if safe rather than create another.
5. **Temporary checkout cleanup:** after a justified N100 exception, remove temporary copies only after checking (a) owner UID of all affected files, (b) `git status --porcelain` is clean, (c) HEAD and any branch-local commits are preserved on authenticated GitHub or explicitly retained, (d) no active process or worktree depends on them, and (e) source/destination are within the approved account workspace. Prefer `git worktree remove` *without force* for linked worktrees. If any condition is uncertain, preserve and report the blocker.
6. **Never delete:** files owned by other users, uncommitted/unpushed work, credentials, source-of-truth asset masters, production Docker volumes, active queues, persistent artifacts or running service dependencies. Do not run blanket `docker system prune --volumes`, `git clean -fdx`, `git reset --hard` or recursive cleanup without specific verified scope.
7. **Storage evidence:** for necessary N100 work record before/after available disk, paths and bytes added/removed, ownership, retained data and cleanup outcome. Prefer GitHub Actions artifacts for validated build outputs over N100 copies; preserve `RUNTIME_VALIDATION=UNTESTED` until actual hardware testing.
8. **No retroactive deletion authorization:** this policy does not itself authorize removing existing worktrees, clones or data. Future cleanup must independently validate every deletion against the safeguards above.

## DX9Ex HUD P0 static-first testing override — 2026-10-08

- Before any further user Quest 3/VDXR test, verify all 71 canonical HUD CALL producers, disjoint C++ hook install arrays, original x86 CALL destinations, Sumo/menu/result/rank routing, and rank/rival screen-vs-world semantic wrappers through `tools/verify_vr_hud_exact_callsite_contract.py --self-test`. Ten deliberate source/manifest defects must be rejected, including reversed left/right HUD spacing and bypassed semantic forwarding. Run `tools/verify_vr_visual_composition_p0.py` and canonical EXE byte/disassembly checks on the same material commit.
- Do not request repeated HMD trials when source, original upstream, historical fork, canonical binary map, draw ownership, texture lifetime, or deterministic CI still provides actionable evidence. Require the exact material SHA's HUD Inspector + DX9Ex game/host/full-chain CI gates first; never mistake a bookkeeping SHA for tested content.
- A green static gate means source contract consistency, **not** that prior 00519 headset visual regressions are fixed. Keep runtime UNTESTED. After actual remaining static gaps are closed, freeze one candidate and conduct one targeted HMD session; do not re-test identical candidate/symptom sets without new distinguishing evidence.

# P0 visual-composition convergence override — 2026-10-07

Historical P0 optical regression response, superseded for dispatch by the 2026-10-10 effective policy at file start. Optical evidence and headset acceptance are retained.

- P0 is visual composition before any new HMD candidate. DX9Ex 00519 (9a3e08cc62b6a36a8196936eacead8cc08fcc756) is a user-runtime FAIL: menu/car-selection textures disappeared; HUD/rank/rival/+TIME/menu arrows/YES-NO/lens flare were doubled or head-following; 90 Hz pacing was not met.
- Do not package or request another routine Quest 3/VDXR test until tools/verify_vr_visual_composition_p0.py and canonical DX9Ex static/build gates pass on the exact candidate SHA.
- Mandatory evidence order: original emoose/OutRun2006Tweaks hooks -> fork R65-R74/R73-era history -> pinned canonical EXE disassembly/XREF/byte contracts -> current producer/queue/draw ownership -> deterministic static verifier -> HMD last.
- P0 covers menu/car-selection textures, rank/position/6th/6/+TIME/checkpoint/goal/result HUD, menu arrows/YES-NO, vehicle rank/rival markers including 4th/5th, F11 gameplay overlay, lens flare/SceneEffect, visual shadows, and recenter-visible HUD placement while preserving world stereo.
- HISTORICAL/INACTIVE GLOBAL FREEZE: the 2026-10-07 DX11+DXVK+R84 pause has been superseded. A DX11 and C DX9Ex are ACTIVE; only DX9Ex optic/IPC promotion remains gated, and B DXVK is independently FROZEN.
- Generic ScreenOverlay2D, automation PASS, or AUTO_ANALYSIS status=OK are not visual acceptance. Future candidates stay RUNTIME_VALIDATION=UNTESTED until exact-build user HMD evidence.

# OutRun2 VR Development Execution Contract

## DX9Ex R84 production-convergence override — 2026-10-07

Historical R84 development sequence, now a DX9Ex C P1 subtask rather than an exclusive all-backend instruction; 2026-10-10 authority supersedes it.

- **Canonical production/development branch:** `vr-d3d9ex-focus`.
- **R84 donor/reference branch:** `vr-refactor-r84-2000c-20261001` at recovered donor HEAD `40e998500fc758dd3b078d9df2ecc2a57a19bc5d`. Treat it as read-only design/evidence. Do not continue its cycle counter, merge it wholesale, or develop new runtime behavior there.
- R84's purpose was structural improvement. It is not complete until the still-useful structure is reconciled into `vr-d3d9ex-focus` and exact build/validation gates pass.
- Follow `docs/VR_DX9EX_R84_PRODUCTION_CONVERGENCE.md` and the matching `DX9EX-R84-PORT-*` queue items.
- **Gate 0 comes first:** repair the current CONVERSION-DX9EX-00505 exact-SHA validation failure before introducing structural ports.
- After Gate 0 is green, inventory R84-only abstractions and classify each as `APPLIED_EQUIVALENT`, `PORT_REQUIRED`, `SUPERSEDED`, or `DEFERRED_RUNTIME_RISK`.
- Port only `PORT_REQUIRED` structure, one seam at a time, into current focus. Never raw-merge/cherry-pick the divergent R84 branch.
- Target order: R34/R33 -> R33/R32 -> R32/R31 -> R31/R30 -> R30/R29 -> lower Present/Reset/DirectGPU facades -> CMake/textual-include cleanup.
- Every seam requires a deterministic fail-before/pass-after contract where practical, exact GitHub-hosted compile/link validation, Domain Isolation, and current DX9Ex regression gates before the next seam.
- Preserve current DX9Ex runtime semantics: Reset/ResetEx, StateBlock, DirectGPU/ACK/fence/slot ownership, HUD/XYZRHW/SkyGlow, recenter, effects, protected world stereo, and fail-closed fallback.
- `RUNTIME_VALIDATION=UNTESTED` remains mandatory unless the user actually tests the exact build on Quest 3/VDXR.
- Historical DX9Ex v3 live migration still requires its own hardware gate; independent DX11 Native A development is not gated. DXVK B remains user-frozen.
- The production automation executor is the external Docker queue controller. ChatGPT schedule IDs/cadence are not execution authority; GitHub HEAD + queue + this contract are.

This file defines the default execution model for substantial work in this repository, especially the OutRun2 VR/OpenXR backends and build matrix.

## Core rule

Do not run large review/fix/build/package tasks as one unbounded session. Treat work as resumable, bounded transactions with durable checkpoints. A fresh chat, automation run, or worker must be able to continue from repository state without relying on hidden conversation context.

Before substantial work, read:

- `docs/VR_AUTODEV_STATE.json` — machine-readable source of truth.
- `docs/VR_RUN_STATE.md` — concise human handoff, when present.
- `docs/VR_REVIEW_FINDINGS.md` — cumulative deduplicated findings, when present.
- `docs/VR_HOURLY_REVIEW_LOG.txt` and `docs/VR_BUILD_MATRIX_LOG.txt` when relevant.
- `docs/VR_UPSTREAM_REFERENCES.md` and `docs/VR_REFERENCE_HARVEST.md` when the task touches stereo/HUD/effects/frame identity/backend architecture; treat them as design evidence only and re-verify applicability before implementation.

If the human-readable state files do not exist, create them during the next safe checkpoint.

## Upstream and historical evidence-first rule — HUD / UI / effects

For HUD, menu, rank/position markers, lens flare, shadows, billboards, screen-space effects, camera-dependent effects, or similar visual regressions, do **not** start from broad draw heuristics or a fresh runtime test when precise reverse-engineering evidence already exists.

Use this evidence order before implementation:

1. **Original upstream mod first:** inspect `emoose/OutRun2006Tweaks` and treat its reverse-engineered hooks as the first source map. High-value files include `src/hooks_uiscaling.cpp`, `src/hooks_graphics.cpp`, `src/hooks_bugfixes.cpp`, `src/game_addrs.hpp`, and `src/interpolation.cpp`.
2. **Fork history second:** inspect this fork's historical VR branches, commits, `docs/VR_HUD_SEMANTIC_BASELINE.md`, EXE/HUD inspector artifacts, problem history, and checked-in reverse-engineering maps. Reuse previously isolated producer/call-site knowledge rather than rediscovering it.
3. **Canonical EXE proof third:** re-verify every address/call-site that affects a fix against the pinned canonical OR2006C2C.EXE identity, byte signatures, disassembly/XREF evidence, and `docs/VR_BINARY_CONTRACT.json` or equivalent analyzer output. Upstream addresses are strong reverse-engineering evidence, not permission to assume a different binary is identical.
4. **Exact producer ownership:** map the verified producer/call-site into exactly one intended VR semantic/space policy. Do not replace known exact producers with primitive-count, shader-shape, broad WVP, or queue-wide guesses unless contradictory evidence proves the exact map wrong.
5. **Static regression gate before HMD:** add or extend a deterministic fail-closed verifier that pins the relevant source binding, producer ownership, ordering/lifetime rule, and canonical EXE evidence. The canonical GitHub Actions gate must pass before routine HMD testing.
6. **HMD last:** Quest 3/VDXR testing validates hardware-only visual behavior after the source/disassembly/static contract is coherent. Do not use HMD testing as a substitute for available upstream/disassembly/static analysis. An exception is allowed only for an explicitly documented hypothesis that cannot be distinguished statically; such a build must be labeled diagnostic and runtime validation must remain `UNTESTED` until the user supplies evidence.

Known upstream HUD evidence includes the exact rival-rank `Calc3D2D`/rank-marker hooks, the DispRank/POSITION family, Time Attack/result scroll hooks, gear/rev, ghost-gap, goal-time, heart/fruit/rival HUD, control icons, C2C speech bubbles, GF warning, and slipstream paths. Use `docs/VR_HUD_SEMANTIC_BASELINE.md` for the maintained semantic inventory and exact high-value anchors.

This rule is intended to prevent repeated rediscovery and wasted hardware tests: **upstream source map -> fork historical evidence -> canonical disassembly -> current implementation -> deterministic verifier -> HMD**.

## Mandatory checkpoint flow

Use the following sequence by default:

### C0 — RECOVER
- Fetch the current development branch HEAD and every relevant component SHA.
- Read durable state and identify the exact unfinished checkpoint and resume cursor.
- Recover relevant CI runs, artifacts, logs, input hashes, blockers, and frozen package identity.
- Do not repeat completed work when the relevant source/dependency/config hashes are unchanged.

### C1 — REVIEW
- Perform one bounded evidence-driven review batch, normally five genuinely distinct lenses/passes.
- Deduplicate findings against prior evidence.
- Separate confirmed evidence, hypotheses, contrary evidence, and hardware-only validation needs.
- Large review requests such as "review 50 times" mean ten persistent five-pass batches (RB01..RB10), not one monolithic reread and not fifty superficial repetitions.

### C2 — IMPLEMENT
- Apply one small coherent fix set or one isolated experiment at a time.
- Do not mix unrelated risky changes in the same checkpoint.
- Preserve backend isolation and branch safety.

### C3 — VALIDATE
- Run the relevant static checks, regression checks, selector/protocol tests, and changed-input builds.
- Prefer fail-before/pass-after evidence where practical.
- A successful compile alone is not runtime proof.

### C4 — COMMIT
- Commit successful coherent changes to the active development branch with a descriptive message.
- Do not leave validated substantive changes only in ephemeral local state when safe remote publication is possible.
- Never force-publish over unrelated work or a live lease.

### C5 — PACKAGE
- Package only when the current phase requires a candidate.
- Verify actual binary/ZIP contents, manifests, component SHAs, config identity, checksums, selectors, and collectors.
- Frozen evening artifacts remain immutable during user testing.

### C6 — STATE
Before ending any substantial run, update durable continuation state.

At minimum record:
- schema version / run ID
- current checkpoint and status
- resume cursor / exact next action
- branch and integration HEAD
- all relevant component SHAs
- relevant source/dependency/config hashes
- completed review batch IDs
- finding IDs and status
- changed files and commits
- build/test/CI IDs and results
- candidate/artifact hashes
- blockers
- retry count for the same unchanged failure
- timestamp

Use atomic/CAS or equivalent single-writer protection where available.

## Bounded-run rule

A run must not keep expanding simply because more useful work exists. Prefer a complete durable checkpoint over an oversized unfinished session.

If the current batch cannot safely finish in the active execution:
1. persist exact partial status and resume cursor,
2. record what was actually completed,
3. stop cleanly,
4. let the next chat/automation run resume from that point.

Never claim background continuation.

## Failure rule

After two materially distinct failed repair attempts for the same unchanged failure:
- mark the item `BLOCKED`,
- preserve evidence and exact failure signatures,
- update durable state,
- move to independent work on the next run.

New evidence may reopen the item. Do not create unbounded repair loops and do not weaken verification to get a green result.

## Review batching

Use persistent review batch IDs:
- RB01 — full relevant source/build graph
- RB02 — caller/lifetime retrace
- RB03 — regression history
- RB04 — backend isolation
- RB05 — OpenXR / DirectGPU
- RB06 — D3D9 state / WVP / Reset / StateBlock
- RB07 — hot paths / frame pacing / draw amplification
- RB08 — failure paths / cleanup / fallback
- RB09 — build / selector / logging / packaging
- RB10 — adversarial integration review of the actual frozen candidate

Each batch should use five distinct lenses:
1. architecture/integration/build/package/license/regression boundaries
2. ownership/lifetime/synchronization/resource generations
3. stereo correctness (WVP/projection/HUD/sky/effects/recenter/menu/white rank-score/fallback)
4. performance (draw/state/caching/copies/waits/telemetry/XR pacing)
5. adversarial review trying to disprove earlier findings

Do not rerun a completed batch unless a relevant input changed. Mark only affected batches stale.

## Branch and release safety

- Treat `vr-openxr` as stable unless the user explicitly requests modification/merge.
- Current targets explicitly override the historical unified-branch default: DX11 A `vr-dx11-native-r71`, DX9Ex C `vr-d3d9ex-focus`, DXVK B FROZEN.
- Preserve the five-mode architecture and explicit backend isolation.
- Record every component SHA used by a package; integration HEAD alone is not package identity.
- Do not silently substitute fallback backends or fake A-F variants.

## Backend development priority override — 2026-09-29

HISTORICAL ONLY (not executable): 2026-09-29 50/40/10 allocation was superseded by DX11 A + DX9Ex C ACTIVE and DXVK B FROZEN. Following historical bullets must never select new work.

- **DX11 Native is the primary implementation/performance lane** (nominal engineering allocation about 50%).
- **Historical inactive DXVK 40% assignment:** B is currently FROZEN and must not automatically resume.
- **Historical inactive DX9Ex <=10% assignment:** C is currently ACTIVE, 50% engineering-effort target, including P0 FFB, P1 structural, P2 automatic XR resolution and P3 performance.
- **DX12/D3D9On12 is frozen/reference-only.** Do not autonomously implement, build, package, optimize, or promote it unless the user explicitly reopens that lane.
- Distribution performance work must target hardware below the development RTX 4070. Do not claim a minimum GPU until measured; prioritize scalable PERFORMANCE/BALANCED/QUALITY profiles, frame-time stability, transport/copy/wait reduction, and 72 Hz viability on lower-tier hardware.
- Single-pass/multiview remains a later optimization candidate only after graphics, lifecycle, selector and two-pass runtime gates are stable.
- Build/CI success is not runtime or low-end performance proof. Quest 3/VDXR exact-build evidence remains required for visual, pacing and performance claims.
- Stale queue/history text that still describes active DX9Ex performance or DX12 development must not create new autonomous work; preserve it as history until explicitly reconciled.

## Interactive chat default

When a user asks to review, fix, build, package, or continue this OutRun2 VR project in chat, follow this contract automatically.

For long tasks:
- resume from repository state first,
- work in C0-C6 checkpoints,
- surface completed checkpoints as soon as they exist,
- persist enough state that a later chat can continue without the previous transcript,
- do not restart completed unchanged work.

User-provided runtime logs and Quest/VDXR tests remain the authority for hardware-only behavior; offline evidence must be labeled accordingly.


## Mandatory logging for direct chat/manual writes

The durability rules apply to **every production write path**, not only scheduled automation.

When ChatGPT/Codex or a human-driven chat directly edits, commits, builds, packages, or integrates production VR code/config/workflows:

1. Treat the writer as a D-equivalent production writer for that transaction and follow C0 -> C6.
2. At C0 read:
   - `docs/VR_REGRESSION_KNOWLEDGE.json`
   - `docs/VR_PROBLEM_HISTORY.md`
   - GitHub Issue #13 (runtime problem/regression ledger) when diagnosing or fixing a runtime symptom
   - GitHub Issue #14 (production change ledger) for the append-only change record
3. Before implementation, compare the intended changed paths/hypothesis against historical regression `riskPaths`, triggers and symptom fingerprints.
4. After each coherent production commit, append an Issue #14 event with:
   `sourceMode=CHAT_DIRECT`, KST timestamp, base SHA, result SHA, summary, changed paths, reason, related finding/regression keys, validation, runtime-test requirement and exact next action.
5. If the change reopens, fixes, mitigates or validates a runtime problem, also:
   - update the matching case in `docs/VR_REGRESSION_KNOWLEDGE.json`;
   - update `docs/VR_PROBLEM_HISTORY.md` when durable knowledge changed;
   - append the corresponding event to Issue #13 using the existing stable regression key.
6. Do not create a new regression key for a familiar symptom until the existing history has been checked.
7. A direct-chat fix is not exempt from regression revalidation, state persistence, build evidence or HMD-evidence labeling.

If GitHub issue write capability is unavailable, mark the transaction `PUSH_PENDING/CAPABILITY_BLOCKED` in durable repository state; never claim the ledger was written when it was not.

## Opt-in PC fast test path

The repository has an interactive Windows self-hosted fast-build path in .github/workflows/vr-pc-fast-build.yml and tools/Build-OutRunPCFast.ps1.

- The runner label is outrun-pc. It is expected to be started manually and remain offline outside a user-requested test/fix/retest session.
- Never route scheduled A/N100/B/C/D work, ordinary review work, pull requests, or untrusted code to this runner.
- Only during an explicitly started **evening user runtime test/fix/retest session** may a direct test-fix commit to vr-d3d9ex-focus include the marker [pc-build]. The runner merely being online is not sufficient authorization.
- [pc-build] is a build trigger, not a validation claim. The workflow preserves out/pc-fast incremental build state and writes a local package to Desktop\OutRunTestBuilds\LATEST.
- PC-fast output is PC_FAST_INCREMENTAL_NOT_FINAL_CI. It never advances the protected runtime baseline and never replaces canonical hosted validation or final packaging.
- Outside that evening test session, scheduled A/N100/B/C/D work, daytime/manual development, review, CI validation, packaging and ordinary direct-chat edits must not use [pc-build]. When the evening session ends, stop using [pc-build] immediately so the user's PC remains uninvolved.



## Optional installed skills and GitHub-only execution

Development may be performed entirely through the connected GitHub repository and GitHub Actions. A local development PC, RenderDoc capture, or local OpenXR runtime is not required for source/static/CI progress.

Installed Skills are optional helpers, not dependencies or completion authorities. Use them only when they directly reduce uncertainty or accelerate the current checkpoint:
- `outrun-vr-execution-router` for resume/implementation-first routing;
- `outrun-openxr-lifecycle-validator` for OpenXR session/frame/swapchain/recenter state;
- `outrun-stereo-rendering-auditor` for eye/state/HUD/world-marker correctness;
- `outrun-directgpu-sync-auditor` for shared-resource/copy/wait/ACK ownership;
- `reverse-engineering-github-only` for checked-in EXE/disassembly/map evidence;
- `outrun-vr-runtime-log-analyzer` when user runtime logs are supplied;
- `outrun-github-only-build-gate` and `outrun-durable-task-recorder` for exact-SHA validation and durable completion.

If a Skill is unavailable, unsuitable, or would repeat already-completed analysis, continue with the existing repository workflow. Never stop merely because a Skill or local GUI tool is missing.

A state-reconstruction/review/plan-only response is intermediate whenever authorized runnable work exists. Continue C2 IMPLEMENT -> C3 VALIDATE -> C4 COMMIT -> C6 STATE. Runtime-only conclusions remain `UNTESTED` until user Quest 3/VDXR evidence exists.
