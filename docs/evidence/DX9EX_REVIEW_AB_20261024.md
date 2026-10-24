# DX9Ex isolated A/B review build, 2026-10-24

## Scope and source of truth
- Branch: `test/dx9ex-reviewed-01454-01467-20261024` (from `b48bf2656cbeb9e0fafe0183a6a26fa0f9323b81`), stable `vr-d3d9ex-focus` never modified.
- Current source: R26+HUD; R84 remains comparison only.
- Input reviews: 01454..01467, GitHub `docs/reviews/dx9ex/automation`.
- The reviews are static source diagnostics, **not** HMD-confirmed bugs.
- No EXE offsets, B9200 +5 hooks, global semantic promotion, shader/RT/c64 or stereo right-eye replay safeguards changed.
- This is NOT an automatic DX9Ex review-lane patch. Explicit isolated user test authorization governs the branch.

## Applied and not applied
| Review | Subject | Result | Evidence/reason |
|---|---|---|---|
| 01454 | ESC pause queue owner | NOT APPLIED | Exact original producer and physical Draw lacking; global ScreenHud risks ESC regressions |
| 01455 | old desktop menu capture rekey | NOT APPLIED | Conditional host cache; no reproduced stale GameState/texture pair |
| 01456 | presentation/GameState publication | NOT APPLIED | Requires generation protocol on both client and host; runtime evidence absent |
| 01457 | cached 1s stereo vs flat XR fallback | NOT APPLIED | Host safety policy; no final XR-side paired trace |
| 01458 | five of six +TIME producers | PRESERVED | Sixth is intended mode=2 negative control; adding hook is unsound |
| 01459 | B9200 End/proven glyph | PRESERVED | Forbidden post-CALL/+5 crash regression; requires physical queue/HRESULT |
| 01460 | logical HUD viewport vs XR extent | NOT APPLIED | Global pixel coordinate normalization risks GOAL/F11/menu |
| 01461 | rank/rival signed W and cant flags | NOT APPLIED | Independently gated A/B, no Quest pose/clip-W samples |
| 01462 | C993/CABE flare ordinal lifetime | NOT APPLIED | Must prove original same-frame source before sequence rekey |
| 01463 | Reset/reseed/reentry | PRESERVED | Fail-closed source protections, no repeatable Reset trace |
| 01464 | SkyGlow pre-HUD capture | NOT APPLIED | No exact source pixel contribution or confirmed glare regression |
| 01465 | optional WorldParticle ring | PRESERVED | Already opt-in; one-lock is not one Draw, no measured GPU benefit |
| 01466 | late 120Hz cubemap face cadence | APPLIED OPT-IN | A/B throttle requests half late-only normalized face budget; healthy/desktop unchanged, no GPU benefit claimed |
| 01467 | depth-off water/glass binocular classification | NOT APPLIED | Original material unproven, global world promotion risks HUD/flare |

## Test contract
- `R26_REVIEW_CONTROL`: exact source build with `-ReflectionLateFrameThrottle=false`.
- `R26_REVIEW_LATE_THROTTLE`: same binaries with `-ReflectionLateFrameThrottle=true`.
- Production default = false; only explicitly launched B variant activates changed face budget. Original 120Hz steady-state 180 faces/s unchanged; detected late frames request fewer. This may create reflection staleness/pop and should not be deployed without matched test.
- One game session at a time. Identical scene/camera/settings, Quest 3/VDXR, 72/90/120 Hz, collect p50/p95/p99 frame-time and reflections, +TIME, GOAL, results, F11, rival/rank, flare and stereo L/R.
- Automated checks: portable C++ reflection regression and GitHub-hosted Win32 R26 DLL/x64 host build, two separate artifacts. HMD runtime remains UNTESTED.
