# R82 performance multi-lens source review — 2026-09-30

Base branch: `vr-d3d9ex-candidate/R81-FRAME-HITCH-TRACE-20260930`  
R81 validated source: `5ea084ba51ecc980f23ce5dd13e7dd4975eb33b8`  
R81 hosted validation: `36647579231` SUCCESS  
R82 branch: `vr-d3d9ex-candidate/R82-PERF-MULTILENS-TRACE-20260930`  
RUNTIME_VALIDATION: `UNTESTED / NEED_HMD_LOG`

This review intentionally rotates independent lenses instead of changing quality/performance knobs by guess.

## Lens 1 — particle interpolation hot path

Finding: `VR-PERF-PARTICLE-INTERP-POOL-001`

Current `InterpolateParticles` runs on rendered frames whenever frame interpolation is active. It:
- calls `RestoreParticles`;
- walks every active source up to `min(particleCount, 512)`;
- tests every slot for live/controller state;
- copies and rewrites each live particle position;
- later restores overridden positions;
- computes `sqrt` for `lastShift` for every moved particle even in release builds although the value is only displayed under `_DEBUG`.

Therefore cost scales with configured active pool slots as well as live particle count. This directly matches the user's sand/dust symptom strongly enough to measure, but not strongly enough to optimize without runtime data.

R82 diagnostic addition:
- `particleInterpUs`
- `particlePoolSlots`
- `particleMoved`
- `particleInterpCalls`

Falsification:
- Current `CORRECTNESS` profile uses `FramerateInterpolation=false`; a reproducible sand hitch there falsifies interpolation as the primary cause.
- `PERFORMANCE` uses `FramerateInterpolation=true`; a hitch that rises with `particleInterpUs/poolSlots` only in this profile supports the interpolation hypothesis.

No particle behavior is changed in R82.

## Lens 2 — telemetry self-interference

Finding: `VR-PERF-HITCH-LOG-SELF-INTERFERENCE-001`

The game logger is a synchronous `spdlog::logger` with a file sink and `flush_on(debug)`. R81 emitted the warning plus PRE/HIT/POST lines while the post window was still being measured.

Because `R81LastPresentEndUs` had already been set before those synchronous writes, logger/file-flush time could be counted in the following POST frame and manufacture a secondary hitch.

R82 fix:
- capture 4 PRE + HIT + 4 POST completely in memory;
- only after all nine samples exist, emit `VR R82 FRAME HITCH` and the samples;
- rebase `R81LastPresentEndUs` after the completed synchronous dump.

This changes diagnostic timing only, not rendering/pacing.

## Lens 3 — dynamic buffer lock accounting

Finding: `VR-PERF-BUFFER-WHOLE-LOCK-ACCOUNTING-001`

D3D9 buffer `Lock(..., SizeToLock=0, ...)` means the remaining buffer rather than zero bytes. R81 counted such calls but added zero to `bufferLockBytes`, which can hide particle/dynamic-geometry traffic.

R82 adds `wholeLocks` without calling `GetDesc` in the lock hot path, so byte accounting remains an explicit lower bound while whole-buffer churn is separately visible.

No buffer policy or lock flags change.

## Lens 4 — dense-stage draw amplification

Finding: `VR-PERF-DENSE-STAGE-CULLING-HYPOTHESIS-001` — NOT_PROVEN

Current shipped graphics defaults include:
- `DisableStageCulling=true`: patches `if (CheckCulling(...))` to no-op;
- `ScreenEdgeCullFix=true`;
- `DisableVehicleLODs=true`;
- `ReflectionResolution=1024` versus the game's 128 default;
- `ReflectionUpdateRate=0.5`.

This can intentionally increase scene work. It is particularly relevant to the user's report that hitches appear where many buildings become visible. It is not safe to switch these globally before the R82 trace shows whether `draw.calls/prims` and/or resource/file-load work actually rise on the hitch frame.

Falsification:
- if building hitches have flat draw/primitives and flat file-loader/resource activity, culling/scene complexity is not the primary owner;
- if draw/primitives jump while Present/host timings remain normal, a bounded A/B profile with stock stage culling is justified.

## Lens 5 — transparent particle fill cost

Finding: `VR-PERF-PARTICLE-SSAA-HYPOTHESIS-001` — NOT_PROVEN

`TransparencySupersampling=true` is the default. On NVIDIA the hook enables the vendor transparency supersampling state. Sand/dust/spray are exactly the kind of alpha-heavy content that can increase transparent fill cost.

Do not disable it globally yet. Use R82 evidence:
- high particles/pool/moved but low interpolation CPU time;
- stable file-loader/resource counters;
- game frame hitch with no host-transport spike;
then run a bounded A/B with transparency supersampling disabled.

## Lens 6 — host transport / OpenXR

Existing host code already provides:
- R23 capture/commit/render/endFrame windows;
- DirectGPU/fallback counters;
- shared-slot cache evidence;
- bounded legacy copy fence (2 ms).

These costs are largely independent of whether a stage contains buildings or sand. They remain a cross-check, not the leading scene-content hypothesis.

Decision rule:
- `presentUs` / R23 host timing spike with flat game-side metrics => transport/runtime path;
- draw/resource/particle/interpolation spike with flat host timing => game/render path.

## Additional telemetry caveat

`RenderScope::WorldParticle` exists, but the reviewed production render paths contain no active producer assigning that semantic. A zero `worldParticle` draw count must not be interpreted as “no particle rendering.” R82 relies on the actual NL particle source counters and interpolation timing instead.

## Next optimization gate

No quality knob or render ownership is changed until one HMD/log session identifies the dominant category.

If `particleInterpUs` is dominant:
1. remove release-only redundant per-particle `sqrt`;
2. replace full-pool restore scans with bounded overridden-index lists;
3. validate no interpolation visual regression.

If dense-scene draw amplification dominates:
1. compare stock stage-culling profile;
2. then isolate reflection resolution/update cost;
3. preserve VR union-FOV correctness separately.

If transparent fill dominates:
1. A/B transparency supersampling only;
2. keep particle semantics/interpolation unchanged.

If transport dominates:
use existing R23/R32 timing and do not touch scene culling/particles.
