# DX9Ex Quest 3 — consolidated optical faults, source evidence, and exact-E8 synchronous HUD repair (2026-10-10 KST)

## Authority and no-regression contract

- Source and edits: `thp32tt/OutRun2006Tweaks:vr-d3d9ex-focus`. Original upstream: `emoose/OutRun2006Tweaks`; canonical OutRun 2006 executable SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.
- The latest **actual user HMD optical feedback** covers material `a6f8497c2fbe83959984275c30fbf43aa6a72d55`, sessions `20261009T144836475Z-e86396b3`, `20261009T150616372Z-f33c5859`, and GOAL **93%** still image; newer source changes are **NOT HMD tested**.
- PASS to preserve: stereo world/road/car, 6th/6 indicator, arrows/YES-NO, car DDS, OutRun rival attachment, F11/recenter, GOAL course/time **only at 100% completed**, and all **outer 3–4 lens discs**.
- FAIL: 1st–5th car-relative position still floats despite fused text; stage course-change `+TIME` text doubles/head-locks; course name **and** time during GOAL **0–99%** rise double/head-lock; **central one** lens disc double/head-locks. Previous recordings prove **neither** completed GOAL nor all flare discs are generally broken.
- Performance: two session R28 windows max 29.917ms and 25.875ms, not GPU-only measurements. Correct two test launch profile SkyGlowFactor 1→4 (original factor 4) is source-verified, not yet HMD-benchmarked. Automatic OpenXR per-eye resolution is NOT active and remains opt-in render-width/height only.
- This review is not permission to disable animation, delete original scene children, alter timer logic, change both result helper functions `0xBEA5A -> 0xBE020` and `0xBEA5F -> 0xBE150`, or globally retag translucent/white draws.

## Canonical source roles cross-checked against original EXE and fork

| Visual item | Original exact E8 / callsite | Current scoped owner | Additional work |
|---|---|---|---|
| GOAL 0–99% progress graphics | `0x97BE4/0x97DEC -> 0x2D200` | `ResultProgress` queued `ScreenHud` | Do not conflate percentage with result record; evaluate direct/queued per-eye draw during animation. |
| GOAL 0–99% stage/title/time print | **19** `0x97xxx -> 0xB9200` CALLs `973AF,97422,974D0,97544,97664,97675,9769E,976B2,976F4,9784F,9787D,9788E,978B4,978C8,978EC,97C31,97C57,97E47,97E6D` | `ResultTextB9200` exact caller + actual queued siblings, **new source-time scope** | Check 93% versus 100% HMD optics separately. |
| OutRun course-change +TIME | sprites `0x9898E/0x98A36/0x98AC6 -> 0x29530`; numeric/text `0x989AD/0x98A89 -> 0x973C0`, `0x98A10 -> 0x974E0` | 6-branch atomic `StageExtensionTime` source+queued scope | Do not confuse with final result, stage gameplay timer or unrelated later `0x98Cxx` effects; E8↔optical child identity still needs HMD. |
| Central lens disc | `0xD3A0 object 0x570002`, `0xD3A5 -> 0xC980 -> DrawObjectAlpha_Internal` | exact enter/leave temporary `WorldBillboard` | Preserve upstream temporary SceneEffect near `0.05m`; central only. |
| Outer flare discs | different `0xD5F5..` parents `->0xC9A0`; `0xCABE -> DrawObjectAlpha_Internal` | original projected outer path | Optical PASS; do not flatten to central. |
| Rank 1–5 | `sub_4BAD20`, `Calc3D2D EXE+0xBAEE7`, exact `RankMarkerSubActiveDepth` | `ProjectedWorldMarker2D` with view-anchor attempt; fixedfn FVF `0x142` | Headset vehicle-relative position STILL UNTESTED on new source; preserve rival `0xBB796` and 4/5 R62 path. |

## New material source change and why

Material `958f1cb3be3310e72825c31cc19591848ad159e0` updates `src/hooks_uiscaling.cpp` and `tools/verify_vr_visual_composition_p0.py`.

The prior `StageExtensionEnter/Leave` and `ResultTextEnter/Leave` wrappers only snapped queue tails **before** the original source E8, then `TagAppendedNodes` **after** it. A synchronous graphics call executed *within* the exact original parent therefore would not acquire the `ScreenHud` semantic via the post-call queue. That is a concrete coverage gap in the hook design, but **whether the user's specific failed glyphs execute synchronously is not yet proven by optical tracing**.

- For **only the six** original `+TIME` source E8 calls and **only the nineteen** original B9200 print E8 calls, save prior thread-local `CurrentScope`, set `ScreenHud` during the original E8 call **only when VR enabled**, then restore prior scope unconditionally at original E8+5 on return.
- Retain `TagAppendedNodes` for real queued children and prior `ProducerToken` provenance; preserve all game original code, animation, clock and final GOAL helper invocations.
- Do not globally redirect shared text/glyph functions, shaders, white/alpha or all GOAL screen overlays. Existing exact-source hook installation rollback remains intact.
- New bounded source-negative tests cover (a) missing stage restore, (b) missing result-scope save, (c) stage restore incorrectly gated by VR enablement. Source verification + Win32/x64 compilation CI must all pass at this precise SHA.
- Prior independent lens-scope safety material: `7bc3262df00cde476e51daac7b54885ec668f763`; restores central WorldBillboard even when VR setting changes during the original call.

## Automated review / acceptance boundary

- GitHub native workflow: `.github/workflows/dx9ex-visual-overnight.yml` at `master`; source/handoff audit branch `automation/dx9ex-visual-audit-20261010`. Cron-only */5 was observed **not** to execute reliably (one scheduled run `37995457423` at 06:46 KST after a multi-hour gap). Long-lived 300s loop + refresh DX9Ex source per tick + self-dispatch below 6h limit added in `9b53e47db4c5434580ba2a4992ba77ba554989fa`.
- Actual worklog is `docs/automation/reviews/DX9EX_VISUAL_OVERNIGHT_20261010_11.md` on the separate audit branch. Ten independent source lenses are cached by affected input hash; do not run the same P0 verifier 1000/5000 times on an unchanged input.
- A separate scheduled hourly reasoning review supplements the mechanical five-minute source contract watch. Source patches may occur there **only when evidence supports a safe fix**; do not call static observation a visual fix.
- **Hard deadline**: 2026-10-11 **08:00 KST**. GitHub schedule can be delayed and workflow self-dispatch might fail; verify actual ledger timestamps, not merely workflow configuration. No guarantee of live HMD validation or autonomous code fixes each five minutes.
- New source: `RUNTIME_VALIDATION=UNTESTED`. Static policy, original EXE analysis, build, Domain Isolation and package are independent gates. User Quest 3 session alone establishes actual stereo/headlock PASS/FAIL; no repeated identical-build HMD request.

Authoritative background: `AGENTS.md`, `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`, `docs/automation/reviews/DX9EX_HMD_FEEDBACK_20261009_2348_RANK_TIME_PERF_RESOLUTION.md`, `DX9EX_DEEPRESEARCH_P0_20261010.md`, `DX9EX_P0_GOAL_EXTTIME_LENS_ORIGINAL_DISASSEMBLY_FIX_20261010.md` and original EXE Inspector artifacts.
