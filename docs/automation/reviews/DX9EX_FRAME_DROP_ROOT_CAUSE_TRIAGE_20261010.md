# DX9Ex Quest 3 frame drops — measured evidence and phase isolation (2026-10-10 KST)

## Source and runtime provenance

- Branch: `vr-d3d9ex-focus`; sources `src/vr/d3d9/stereo_renderer_r7.inc`,
  `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp`,
  `src/vr/d3d9/stereo_renderer_r32.cpp`,
  `src/hooks_framerate.cpp`, `vrhost/src/main_r23.cpp`,
  `src/hooks_graphics.cpp`, launcher `tools/OutRunVR-TestProfiles.ps1`.
- Two uploaded user Quest 3 / VDXR runtime sessions both used code
  `a6f8497c2fbe83959984275c30fbf43aa6a72d55`, **before**
  SkyGlow profile restoration and subsequent active source commits.
  See `DX9EX_HMD_FEEDBACK_20261009_2348_RANK_TIME_PERF_RESOLUTION.md`
  and `DX9EX_DEEPRESEARCH_P0_20261010.md`. New source **HMD UNTESTED**.
- User-visible drops are real, but the exact GPU-vs-CPU blocking
  location is **NOT YET CONFIRMED**.

## Verified contributors / facts — do not turn correlation into causation

1. **Definite erroneous historical graphics override, since corrected:**
   both tested launcher runs forced `-SkyGlowFactor=1`, though game
   `src/hooks_graphics.cpp` ships default `4`. In the VR independent
   dual-eye bloom (`R30EnsureSkyGlowResources` /
   `R30ApplyStereoSkyGlow`), factor 1 allocates full-eye glow surfaces;
   factor 4 uses roughly one quarter of each edge (= **1/16** the
   reduced-buffer pixel area at normal desktop sizes). This is a
   source-confirmed excess workload, **not proof that all stalls
   originate in bloom**. Main test profiles now pass `=4`.
2. **Observed D3D9Ex Present latency spikes:** first HMD session:
   88 R28 sample windows, 63 windows with maximum above the
   90Hz 11.111ms frame budget, maximum **29.917ms**;
   second session: 76 windows, 31 over budget, maximum
   **25.875ms**. These are *window maxima*, **NOT total lost frames
   or GPU render durations**. A device Present can wait/serialize.
   First session host average timing estimate ~80.9Hz,
   second ~89.8Hz; these are telemetry estimates, not exact missed
   display frames.
3. **Resolution/workload pressure:** original game backbuffer in
   HMD logs followed 3440x1440 PC resolution. Stereo renders left
   and right separately; 3440x1440 * 2 = **9,907,200** eye-source
   pixels before multiple world/particle draw passes, bloom,
   VR host projection/composition, or supersampling. Opt-in
   `[VR] RenderWidth/RenderHeight` permits independent resolution,
   but automatic per-eye XR negotiation is **not implemented**.
   Changing resolution requires an A/B hardware test.
4. **DirectGPU is NOT presently the leading fault:** observed frames
   = 27,832 direct/3 fallback and 28,833 direct/1 fallback;
   `fenceTimeout=0` in both sessions. Rare fallback is real, but
   cannot explain broad continuous FPS drops in that trace.
5. **Desktop VSync already bypassed in normal DX9Ex profiles:**
   `[VR] DisableDesktopVsync=true` in current `CORRECTNESS` and
   `PERFORMANCE` profiles; current `src/hooks_graphics.cpp`
   configures `D3DPRESENT_INTERVAL_IMMEDIATE` when active.
   Do not label desktop sync a verified culprit unless the *actual*
   installed command line contradicts this.
6. **60Hz simulation != 90Hz render:** `hooks_framerate.cpp`
   keeps original simulation clock while current OpenXR cadence can
   release one render per `xrWaitFrame`. A 60-to-90 mismatch in
   animation movement can *look* like a dropped render frame even
   when actual display submission cadence is adequate. Separate
   simulation judder, reused/cached frames, and true compositor
   deadlines before optimizing scene shaders.
7. **Particle-like work remains a hypothesis:** user reports
   buildings, sand, spray and smoke as demanding areas.
   `stereo_renderer_r32.cpp::R32FinalizeFramePerf` records
   drawn/primitives/alpha-blended/particle-like counters, where
   `particleLike` explicitly means an alpha+no-Z-write proxy,
   *not* a proven OutRun particle category. Correlate these
   counters with *the same exact frame* before reducing effects.

## Newly identified diagnostic defect — corrected

`tools/Analyze-OutRunVRSession.ps1` previously required every
`VR R32 FRAME SPIKE` log line to include
`fenceWaitUs=...,fencePolls=...`; however active C++ producer
`src/vr/d3d9/stereo_renderer_r32.cpp` emits
`workload[...effectUnknown=...] stereo[...]` with **no such
fence fields**. This mismatch discarded *all* current-format
R32 spike lines and potentially printed `perfSpikeCount=0`
even on a session with genuine frame spikes. Distinct fix and test
commits: `91487fc3fe18366b8525b070b2239c110158bd81` and
`31b079772057f4faa341f26c339fd363004c0948`.
The parser now recognizes current and legacy lines, exports
draw/particle evidence, distinguishes unavailable fence metrics,
and treats recorded R32 spikes as performance warnings.
**Diagnostic repair is not a speed increase.** Validate the
PowerShell fixtures in exact-source CI; do not infer unobserved
fence waits as zero-duration waits.

## Next evidence-driven isolation (single useful run per changed build)

Keep the same race section, full packaged binary/source SHA and
HMD refresh rate, without undoing correct HUD, lens outer rings,
rank 6th/6 or result completion semantics.

- Phase A: control at `SkyGlowFactor=4`,
  `FrameCadenceMode=1`, `DisableDesktopVsync=true`; record
  XR runtime Hz, R28 `lower-Present` max, R32 `frameUs`/
  `presentUs`, [R23 pipeline] fresh/cached/reject reasons and
  `captureMs/commitCopyMs/renderMs/xrWaitFrameMs/xrEndFrameMs`.
- Phase B (diagnosis only): change just `SkyGlowFactor` to 0.
  Improvement confined to bloom means source GPU/effect work likely;
  no change points elsewhere. Restore 4 after comparison.
- Phase C: *opt-in* moderate source resolution reduction, leaving
  other variables untouched; compare same scene and host timing.
  Only reduce default quality after reproducible positive evidence.
- Phase D: 90Hz versus user target 72Hz under identical visuals.
  90Hz has an 11.111ms period, 72Hz 13.889ms; this can improve
  slack but is **not** a code-level root-cause fix.
- Classify: large R32 frameUs+draw/alpha = game workload/CPU/GPU
  candidate; high lower-Present with otherwise low frame workload
  = present queue/synchronization candidate; high host
  `commitCopyMs/renderMs/xrEndFrameMs` or cached projection =
  transport/compositor candidate. `xrWaitFrameMs` alone is **not**
  workload time because OpenXR deliberately throttles there.
  Correlation alone cannot prove GPU stall; use a GPU timestamp/query
  only with safe asynchronous readback if deeper instrumentation is needed.

**Result as of this review:** one confirmed *historical*
avoidable graphics load (`SkyGlowFactor=1`, profile now fixed),
two HMD sessions proving sporadic deadline overruns, and one
confirmed false-negative analyzer bug now fixed. Remaining dominant
bottleneck **unproven** pending an exact patched binary/runtime
correlation. `RUNTIME_VALIDATION=UNTESTED`.
