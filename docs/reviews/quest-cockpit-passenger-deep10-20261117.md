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
