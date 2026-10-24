# DX9Ex 01468 isolated GPU census test build — 2026-10-24

## Scope
- Branch `test/dx9ex-review-01468-gpu-census-20261024` created from verified four-way test HEAD `ac26615fe9901afb40f71abf6c7f2fb8b56bf184`. Stable `vr-d3d9ex-focus` remains REVIEW_ONLY and untouched.
- Current published review: `docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01468.md`, whose confirmed static finding is the nested 1/16 and 1/64 alias.
- The 01465 existing opt-in particle ring and 01466 optional late-reflection throttle remain independently A/B testable. No global VR geometry, HUD, depth, alpha, texture, XR, F11, or B9200 hook changed.

## Exactly what changed
- `OUTRUN_VR_GPU_PROFILE=1` continues to gate every profiler call; normal and four existing performance variants run with it off.
- New independently opt-in `OUTRUN_VR_GPU_CENSUS_DEPHASE=1` rotates the diagnostic RT+pixel-shader census using `(logicalDraw+frame*7)&63==0`, nested in the already existing state sample `(logicalDraw+frame*7)&15==0`.
- Default `DEPHASE=0` retains legacy census `logicalDraw&63==0` and its known `frame%16==0` alias. Neither option changes actual game/eye Draw or queried render target.
- New `censusCandidates`, `censusPhaseMode` and `rtOwnership=FIRST_SAMPLED_DIMENSIONS_ONLY` log labels distinguish sampling from physical presence and true COM backbuffer identity. No synchronous readback or GPU FLUSH.
- The corrected opt-in census may perform up to one extra RT/PS COM inspection per 64 logical Draws per frame (vs sparse legacy frames), so never treat instrumentation cost as game speedup.

## Six independent ZIP variants
| Variant | Reflection throttle | WorldParticle ring | GPU profiler | Census dephase |
|---|---|---|---|---|
| R26_REVIEW_CONTROL | OFF | OFF | OFF | OFF |
| R26_REVIEW_LATE_THROTTLE | ON | OFF | OFF | OFF |
| R26_REVIEW_PARTICLE_VB | OFF | ON | OFF | OFF |
| R26_REVIEW_COMBINED | ON | ON | OFF | OFF |
| R26_REVIEW_PROFILE_LEGACY | OFF | OFF | ON | OFF |
| R26_REVIEW_PROFILE_DEPHASE | OFF | OFF | ON | ON |

All six variants package the SAME Win32 game DLL and x64 OpenXR host. The launcher sets environment variables for the process only and writes RUN_ENV.txt plus logs. Extract only one ZIP to the OutRun 2006 game folder after backing up your stable files, then run RUN_DX9EX_TEST.cmd. Do not launch host alone.

## Validation rules
- GitHub Actions on this branch builds Win32 R26+HUD DLL and x64 OpenXR host on hosted Windows and runs the existing portable reflection regression plus a new 01468 C++ exact-phase regression.
- Validate the returned Actions artifact by commit SHA. Runtime/game/Quest3/VDXR remains **UNTESTED**, and the result is not a claimed water/glass material GPU fix.
- Use comparable scenes and 72/90/120Hz refresh while inspecting `VR GPU WATER 5s` records. If RT count remains low/zero, inspect profiler enabled, censusCandidates, real Draw identity, query availability, and scene sampling before inferring absent offscreen work.
