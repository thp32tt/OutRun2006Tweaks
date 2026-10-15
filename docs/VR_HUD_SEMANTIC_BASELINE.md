# VR HUD Semantic Baseline

Baseline branch: `vr-d3d9ex-focus`

This file defines the source-level HUD policy inherited from the original
`hooks_uiscaling.cpp` reverse engineering. It is intentionally the reference
for scheduled review workers: do not replace these semantic identities with
primitive-count or broad shader/WVP guesses without contrary runtime evidence.

## Evidence hierarchy and original-upstream source map

HUD work must start from the original mod's reverse-engineered map before adding new heuristics. The authoritative upstream source is `emoose/OutRun2006Tweaks`; re-verify all addresses against the pinned canonical EXE before using them as a current binary contract.

High-value upstream anchors currently include:

- `Calc3D2D = 0x49940` and `RankMarker_Truncate = 0xBB046`.
- Rival-car rank `sprani` CALLs: `0xBB0FB, 0xBB133, 0xBB16C, 0xBB1A5`.
- Rival-car rank 4th+ `put_clip_sprite` CALLs: `0xBB21F, 0xBB241, 0xBB271, 0xBB2BC, 0xBB2D0`.
- DispRank/POSITION scroll CALLs: `0xB9F3A, 0xB9F5E, 0xB9F81, 0xB9FD0, 0xB9FFC, 0xBA01E, 0xBA035, 0xBA052`.
- Time Attack/result scroll handoffs: `0xBE5CD, 0xBE603, 0xBE633, 0xBE66D, 0xBE690, 0xBE6B5, 0xBE6D5, 0xBE8D8, 0xBE915, 0xBE94A, 0xBE97A, 0xBE9A3, 0xBE7E8, 0xBE802, 0xBE81C`.
- Additional upstream HUD families are explicitly hooked for gear/rev, ghost gap, Time Attack goal, heart/C2C heart, fruit, rival HUD, control icons, C2C/GF speech bubbles and hearts, Don't Lose GF, and slipstream.
- Original graphics evidence includes car-base-shadow call sites `0x69EB4, 0x6AC76, 0x6B766` using `DrawObjectAlpha_Internal`.
- Lens-flare work must combine original upstream lens-flare path/camera/interpolation knowledge with this fork's later exact producer evidence; do not classify all alpha draws as flare.

The maintained workflow for HUD/effects is:

`original upstream map -> fork historical VR evidence -> canonical EXE disassembly/XREF proof -> exact current semantic ownership -> fail-closed verifier -> HMD validation`.

Do not send a routine HMD candidate merely to discover information already obtainable from these source maps or static/disassembly checks.

## Screen-space HUD

These are common-centre / zero-disparity VR HUD and pass through the existing
R30 screen-space/XYZRHW HUD transform and `VR/HudScale`:

- `HUD_TIME_ATTACK` — Time Attack timer and related scroll elements.
- `HUD_RANK` — race position/rank HUD, including the DispRank family.
- `HUD_GEAR_REV` — REV/gear indicator.
- `HUD_GHOST` — Ghost / You / Diff.
- `HUD_GOAL_TIME` — Time Attack goal time.
- `HUD_HEART_TOTAL` — HUD heart totals / C2C heart counters.
- `HUD_RIVAL` — screen HUD rival indicators.
- `HUD_GF_SPEECH` — C2C girlfriend speech bubble family.
- `HUD_RANK_EMOJI` and `HUD_RANK_TEXT` — ranking emoji and rank text.
- `HUD_GF_WARNING`, `HUD_SLIPSTREAM`, `HUD_FRUIT` — other known C2C HUD.

## World-space exceptions

These must retain true stereo/world attachment and must not be flattened into
the common-centre HUD plane:

- `WORLD_RIVAL_MARKER` — `sub_4BAD20`, rival-car 1st/2nd/etc markers.
- `WORLD_HEART` — `HeartDisp_car_heart`, hearts attached to cars/world.

## Automatic verification

`OutRun2006Tweaks-hudtrace.csv` schema v2 records
`known_area,semantic,space_policy`.

The collector automatically produces:

- `HUD_TRACE_SUMMARY.txt` — detailed observed callers and geometry.
- `HUD_SEMANTIC_COVERAGE.txt` — expected semantic families observed during
  that session. `NOT_OBSERVED_THIS_SESSION` is not a failure; the game mode
  may simply not have displayed that HUD.

`tools/analyze_outrun_exe.py` applies the same semantic ranges to the static
direct-CALL inventory, so CI artifacts and runtime logs use the same names.

## Baseline rule for future scheduled review

Preserve semantic separation first. A source change may refine an exact
call-site or split a category, but broad promotion of screen HUD to world 3D or
world billboards to zero-disparity HUD requires specific runtime evidence.

## P0 exact producer static gate — 2026-10-08

`tools/verify_vr_hud_exact_callsite_contract.py --self-test` checks 71 canonical direct CALL addresses, relative CALL destinations, `VR_BINARY_CONTRACT.json` entries, disjoint physical UIScaling hooks and correct screen/world semantic tag publication. Ten intentionally corrupted cases must FAIL, including reversed right-side spacing and left-side ScreenHud owner bypass. It runs with `tools/verify_vr_visual_composition_p0.py` and exact canonical EXE verification in the GitHub HUD Inspector gate. Do not ask for repeated hardware runs while code/binary evidence can discriminate the fault; CI success remains `RUNTIME_VALIDATION=UNTESTED` until exact Quest 3/VDXR testing.
