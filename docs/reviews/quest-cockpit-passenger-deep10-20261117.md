# QuestCockpitV2 passenger: ten independent native call-path debug passes

Date: 2026-11-17 KST. Parent baseline: `6888d425e432536f64151ee76a9cd6c911dcafc6`.
Source scope: native OutRun2006Tweaks test branch, original PC reference at
`r4dius/outrun2-decomp/src/platform/race_robots.cpp`, and the user's
`OutRun2_VR_ANALYZE_UNIFIED_LOCAL_CURRENT_FOCUS_CORRECTNESS_20261116T153439259Z-cb737397.zip`.
This is STATIC/CODE-TRACE evidence, **not Quest 3 visual confirmation**.

| Pass | Exact source path | Observed result | Action |
| --- | --- | --- | --- |
| 01 | PC original `440110` event table → `ROB01/ROB02` → `4879B0` | No synthetic event; original slot 363 owner, original callback pointer checked | Retain native provenance |
| 02 | `0x79FB48+0x16B` event flags → `ExactOriginalCockpitOccupant` | **BUG:** loose bit-1 check falsely admitted `0x03`; game event consumers use `(flags&3)==2` | Compare low two bits; regression for `0x03,0x0A,0x12` |
| 03 | player draw camera=0 vs 2/30 → `PassengerDrawTrace` | **BUG:** all non-1 cameras counted as camera 0; user log predominantly mode 2/30 | Split camera 0, camera 1 and other |
| 04 | camera 0 → original `4879B0` and `514E60` | Neither Follow nor Remove may alter camera 0 | Bypass gate stays mode-1 only |
| 05 | mode 1 / Follow / native car `0xC000` mask equals `0x4000` | Native `4879B0` must call `487880` once | No extra forced draw (avoid duplicates) |
| 06 | mode 1 / Follow / native car gate closed | Exact live slot 363 can invoke `487880`; without native render-frame/paired XR validity this was a risky extra draw | Require `NativeFrameTrace().Active()` and valid stereo pose before forcing |
| 07 | mode 1 / Remove → `ShouldSuppressOriginalPassenger` | Hide only exact live ROB02 during gameplay; driver/NPC unaffected | Retain original suppression path |
| 08 | `STATE_START` progress 65, `STATE_GAME`, GOAL, scene effect | GOAL/scene effects must use original renderer; event `0x0A/0x12` low-state remains valid | Keep race-only bounds |
| 09 | `487880` → `514E60` → pre-F0 snapshot → W×C → PMT `405015/40501D` | The correction and visibility RAII scopes are bounded; existing trace did not reveal whether final passenger model was displaced | Add opt-in original/corrected world-matrix translations |
| 10 | native detour install, recursion, F11 settings, CI and copy-run packaging | Exact original signatures + two exclusive F11 options preserved; no user-HMD display proof | Run exact-SHA isolated smoke and Win32/x64 package CI |

## Grounded user log reading (before the new gate hook)

- Camera mode 1 produced 45 `514E60` passenger callback entries in the first session and another 45 in the second, then no further mode-1 callback entries while `pFlag=0x02` remained live.
- `VR PASSENGER PMT NODE` showed both `nativeVisible=1` initially and `nativeVisible=0` later, with scoped override reported. These are **cull gate reports, not GPU draw confirmation**.
- `QuestCockpitV2OccupantLod0=false` and `QuestCockpitV2PassengerVisible=true` were active. The initial log **did not contain original car flags**. Thus the 4879B0 car-gate hypothesis cannot be declared proven from that session alone.
- Corrected `callbacksCam0` counts must not be compared numerically to old, mislabeled counters.
- The new 4879B0 native bypass's actual HMD results remain **UNTESTED** until a new user session.

## Audit definitions

The existing `tools/verify_quest_cockpit_passenger_static10.py` runs ten independent source-path checks;
the C++17 `tools/tests/quest_cockpit_v2_passenger_event_smoke.cpp` exhausts
64 Remove cases and 256 Follow gate states, plus native event flag edge cases.
Win32 and x64 GitHub Actions must pass on an exact SHA before packaging.
No v0.03 public release should be published from this experimental branch.

## Additional exact-original preflight and scene-mask recovery (2026-11-17)

- Canonical upstream v0.1 EXE SHA256 verified via exact PE32 mapping in a read-only GitHub Actions preflight.
- Exact original display routine `0x43FB40` starts `83 EC 10 83 3D 58 02 78 00 02 53 55 56 57` and takes cdecl mask, first, last. `0x4879B0` starts `A1 18 9D 79 00 ...` and has the stock car `0x4000` gate.
- Critically, the native `ROB01/362` and `ROB02/363` source event descriptors both use `display_scene=0x80`, not `0x40`. The decompiled PC frame renderer calls event_display with `1u<<layer` for layer 7, every game frame. Forcing another layer would be wrong and is prohibited.
- New guarded scene-pass wrapper first invokes original `43FB40`. It only recovers genuine existing `ROB02` after the exact `0x80` pass, only when driver has `0x80` but passenger's current scene mask does not, game/VR/stereo are active, and original real passenger wrapper was **not** reached in that same pass. Draws via the existing, native car-gate-aware passenger path. Does not write the original event table, flags, model or game state.
- If native `ROB02` field_C still has `0x80`, the new path **does not** produce a duplicate. The preexisting `4879B0` closed-car-gate bypass is the only recovery for that case. Original scene hook is signature verified and optional/fail-closed.
- No HMD test has yet shown actual visible passenger pixels; static/CI checks cannot prove visual correctness.

## Final risk closure: no alternate-layer duplication

- A missing `0x80` bit does not by itself mean the passenger has no other valid render scene. The scene recovery gate therefore requires `passengerScene==0` (completely disabled), rather than simply `(passengerScene&0x80)==0`; alternate `0x40` and `0x100` masks are negative regression cases.
- The pre/post original wrapper comparison uses a **thread-local** counter instead of the aggregate cross-thread diagnostic counter. This prevents eye/renderer thread traffic from suppressing a genuinely missing original event in the current scene pass.
- The regular original `0x4879B0` car display gate recovery still applies to any scene where the native event callback actually executes. No cross-layer re-render is attempted when event scenes differ from original `0x80`.

## Final test-debug lane 2026-11-18: missed native guest callback with intact 0x80 scene

- The last uploaded user runtime log predates all subsequent scene-hook builds. It shows a live original `ROB02` (`pFlag=0x02`, callback installed), but no further ROB02 native draw callbacks during a sustained camera-1 interval after the first ~45. That is evidence of a callback gap, not proof of its root cause or Quest 3 pixels.
- The earlier 0x80 scene fallback only admitted `passengerScene==0`. The original EXE descriptor for ROB02 is `0x80`, so a live event with unchanged original `0x80` and a missing callback would never be recovered.
- New narrowly scoped fallback admits the native `0x80` scene with `passengerScene==0x80` **only if** the exact native ROB01/362 `0x4879B0` wrapper was reached on the *same thread* in this same original `0x43FB40` display invocation but the original ROB02/363 wrapper was not. Thus a skipped passenger alone can be replayed exactly once while the original scene's state is live. The previous guestScene==0 recovery remains for a disabled native layer. Other masks, shared-layer masks, missing driver proof, zero XR pose, GOAL/menu, 3rd-person and Remove remain rejected.
- Added bounded `VR PASSENGER SCENE PASS` counters (driver/guest wrapper pair, source scene masks, current native epoch, stereo), useful if Quest3 still fails; does not claim GPU proof.
- The one-shot `RUN-QUEST-APK-PASSENGER-DIAG.cmd` keeps Follow Camera 0 forced on this diagnostic launch and collects logs automatically.
- Scope boundary: no new event, original game files untouched, no public v0.03, no live HMD result yet.

## 2026-11-19 user field-run follow-up: passenger pixel gap and low-speed sky double-image

- Uploaded session `20261118T165428567Z-5fc963ca`, exact source `5a56acf5c858b1e6c360bd6e56dbb8151c09e059`, original EXE SHA `68ceb386...`, correct DLL, game exit=0.
- While cockpit camera1 active the original ROB02 renderer was invoked **6413 times**, car-flag gate recovered **6368** genuine draws, original display-scene driver/guest 0x80, original guest wrapper reached=true, scene restores=0. Current root cause is NOT missing 4879B0/43FB40 callbacks.
- The model-space correction was applied on every observed ROB02 draw but yielded huge off-cockpit translation: native (3.620,-2.379,-254.995) -> W*C (2.931,-44.230,-250.776); later native (821.016,-7.100,-354.080) -> W*C (819.698,+49.760,-354.715). PMT forced-visible=1 LOD0=0 observed, not proof of GPU pixels. New guard rejects only ROB02 W*C displacements over 4 game units and forwards unmodified native work within existing scoped PMT visibility.
- Original `0x4521C0` naturally contains two sky layers. Programmable exact-sky drew using rotation-only head fallback; fixed-function rotationOnly could use the native Quest eye pair or fallback depending on pose readiness, so layers could disagree. Fixed rotation-only sky now ALWAYS uses the same head fallback as programmable sky; non-sky world native pair unchanged. No pixel-level low-speed cause is proven before HMD retest.
- PASSENGER-DIAG one-run enables bounded SKY probe, `VR SKY COHERENT BASIS`, `VR PASSENGER NATIVE MATRIX`, original PMT and game/host evidence. Release v0.03 remains rejected until live confirmation.
