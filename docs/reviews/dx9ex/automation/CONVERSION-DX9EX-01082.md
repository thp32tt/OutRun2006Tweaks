# CONVERSION-DX9EX-01082 — R26+HUD particle UP bilateral upload and frame-budget review (REVIEW_ONLY)

- DATE: 2026-10-20 KST (review begun 23:05)
- TASK_ID: CONVERSION-DX9EX-01082
- PRODUCTION_ID: CONVERSION-DX9EX-01082
- EVENT_ID: CONVERSION-DX9EX-01082-E001
- EVENT_TYPE: dispatch
- ATTEMPT: 1/3
- LANE: DX9EX
- TARGET_BRANCH: vr-d3d9ex-focus
- SOURCE_HEAD: e2739da84919d93dfdf3553e7e3c86ecaf793481 (pinned GitHub input HEAD, before this docs-only commit)
- R26_HUD_BASELINE: 0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 (immutable control, not switched)
- COMPARISON_ONLY: aab9e02bcb2ad2e6253840e6267e5c5ad5040854 (recent HUD candidate, NOT HMD PASS)
- MODE: DX9EX_REVIEW_ONLY
- CONTINUOUS_REVIEW: ON
- DX9EX_REVIEW_ONLY: ON
- CODE_CHANGE: NO
- REVIEW_SCOPE: Dense sand/smoke/skid WorldParticle producer -> source semantic / queued or direct physical UP -> R26 per-eye XYZRHW CPU reprojection and UP draw -> RT/depth/viewport restore -> Present R9 direct-ring/SBS resolve -> host capture/render/xrEndFrame. Compare R84-only opted-in DynamicVB upload without promoting R84.
- NEW_FINDING: CONFIRMED_R26_WORLD_PARTICLE_UP_BILATERAL_CPU_UPLOAD_PATH_DIFFERS_FROM_R84_OPT_IN_GPU_RING; performance impact is UNMEASURED, not a reproduced defect
- PATCH_CANDIDATE_ONLY: YES (conditional performance experiment only; no code or runtime-config modification)
- AUTOMATION_VALIDATION: STATIC_GITHUB_SOURCE_REA_POLICY_PRIOR_REVIEW_INSPECTION_COMPLETE; RESULT_COMMIT_DIFF_AUDIT_TO_BE_PERFORMED_POST_COMMIT; SOURCE_BUILD_NOT_REQUIRED_FOR_DOCS_ONLY
- RUNTIME_VALIDATION: UNTESTED

## 1. Scope selection / prior-work boundary

GitHub at SOURCE_HEAD contains the separate docs-only 01075–01081 results and the [AUTO:CONVERSION-DX9EX-01081] parent review commit. 01075 checked +TIME/result shader admission; 01076 host menu pose cache; 01077 DirectGPU producer EVENT; 01078 F11 optical eye cant; 01079 R62 projected rank post-left owner; 01080 SkyGlow second-eye failure/Present propagation; 01081 R64 D3DX OnLost/OnReset ledger ordering. No previous result is refiled as a new defect here. 01081 NEXT_REVIEW explicitly selected dense sand/particle overdraw and draw/copy/wait cost as an independent next scope.

AGENTS.md:1-4 is the latest R26+HUD default, overriding contradictory older R84-mainline paragraphs. R26+HUD safe renderer is source file src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp. The active user dispatch explicitly forbids source implementation, workflow/config updates, release/package, branch/ref updates and unsafe B9200 post-CALL/+5 hooks. Issue #129 and #131 are old *static review* evidence for possible frame/particle hotspots, not a current matched GPU profiling trace.

## 2. EVIDENCE — static original producer to final XR simulation

1. **Original producer is not yet uniquely assigned to sand.** docs/automation/OUTRUN_REA_RENDERING_ARCHITECTURE_20261018.md:1-42,88-103 identifies Win32 frame 0x00417B20 -> original scheduling 0x00449050, scene indirect dispatch, sprite queue 0x0042D710, D3DX Begin/Draw/End and distinct native DrawPrimitiveUP alternatives. It explicitly says original particles still require independent producer/semantic-to-real-API identity; generic alpha or a Ghidra zero direct-caller count cannot identify a sand particle. A queue-owned D3DX Draw may not physically submit until Flush/End. No actual sand physical-DPUP fingerprint has been captured in this review.
2. **Scope/queue admission occurs at physical API, not merely producer.** src/vr/game/render_semantics.hpp:1018-1052 defines ConsumeForDraw and WorldParticle/WorldBillboard corroboration, with separate ScreenOverlay/HUD and source scopes. src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5408-5434 consumes next physical draw scope, applies R30 pre-HUD SkyGlow gate, then offers R30TryXyzrhwPrimitiveUP before conservative original/R29 fallback. Direct original scene dispatch, queue-owned sprite classes and native UP must not be conflated. Noneligible/non-XYZRHW GPU draws may bypass this path.
3. **R26 GPU submission details: confirmed source path, conditional eligibility.** R30TryXyzrhwPrimitiveUP():3902-3945 rejects absent state, invalid primitive count, missing reliable world/HUD state and failed transforms. For an admitted UP draw, R30TransformXyzrhwStereo():3750-3782 invokes R30TransformXyzrhwVertices independently for left and right; if exactly one eye accepted full world reprojection, both may be re-transformed with affine-only fallback. The per-eye function :3382-3424 resizes scratch and copies original vertices; :3441-3630 reconstructs per-vertex view position from RHW/inverse projection, applies independent eye inverse/FOV, and preserves game Z if necessary. The bilateral fallback is optical fail-safe; the second pair of transform passes is conditional, not a count asserted for every frame.
4. **R26 physical draw / restore.** R30TryXyzrhwPrimitiveUP():3932-3944 calls the original D3D9 DrawPrimitiveUP twice with separately transformed left/right CPU scratch. R30ExecuteXyzrhwStereo():3784-3900 executes left, switches right RT/depth/viewport, executes right and restores previous RT/depth/viewport, poisoning the frame and safe-falling back on failed right draw/restore. A 'two UP submissions' claim applies only to successfully admitted R30 UP path, not every scene draw or every alpha draw. There is no DynamicVB upload opt-in branch in this R26 safe UP function.
5. **Different inactive comparison path.** src/vr/d3d9/stereo_renderer_r30.cpp:165-179 defines a separate R84 R30ParticleGpuRing gated by OUTRUN_VR_R30_PARTICLE_VB=1 (off absent exact string). :6490-6593 implements *optional* WorldParticle-only and telemetry-reliable DynamicVB upload with first-eye/second-eye raw DrawPrimitive, otherwise retains two UP draws. src/vr/d3d9/r30_particle_upload_policy.hpp:6-56 requires exact WorldParticle, world stereo, reliable effect state, alpha enabled, depth writes disabled, unindexed, no StateBlock recording and bounded stride/bytes. src/vr/d3d9/r30_particle_dual_eye_ring.hpp:10-91 packs both distinct eye vertex byte streams into ONE DynamicVB Lock/Unlock with ring DISCARD/NOOVERWRITE behavior. This is a **compiled-owner/path difference**, not proof R84 opt-in improves FPS, nor a basis to promote it into R26 without separate authorization.
6. **Correctness fences on the comparison route are material.** R84 stereo upload holds a mutex across two physical draw calls (:6532-6557), restores the UP-equivalent stream-0 side effect with finishUp (:6558-6567), and allows native UP replay only if *no* GPU draw was attempted (:6568-6576, MayUseNativeUpAfterGpuAttempt). Broadly transplanting its buffer logic or replaying once after a left-eye blend may cause double-alpha or a partially rendered stereo frame. Default R26 is intentionally untouched.
7. **Game Present / transport costs.** src/vr/d3d9/stereo_renderer.cpp:685-809 gates frame publication on stereo/pose/right-eye completeness, chooses direct transport or SBS fallback, and calls actual device Present. src/vr/d3d9/stereo_renderer_r7.inc:1357-1425 uses bounded four-slot DirectGPU shared eye surfaces and two StretchRect copies + EVENT; :1428-1447 separately describes up-to-1-ms *post*-Present fence grace, not a blanket per-draw GPU wait. Thus any dense-particle cost can coincide with copies/ring backpressure without proving the particle UP path is the bottleneck. This review does not refile the 01077 EVENT sequencing finding.
8. **Host/OpenXR final boundary.** vrhost/src/main_r23.cpp:3165-3215 correlates candidate frameId/pose, capture age and candidate readiness; :3555-3595 calls xrEndFrame and tracks actual layer/source IDs. XR per-eye size is independently configured in vrhost/src/main.cpp:1924-1966. A left/right DPUP submission or published stereo metadata is not equivalent to a Quest 3 binocular optical PASS.

## 3. NEW_FINDING and competing explanations

**Confirmed:** The current default R26+HUD UP stereo owner performs separately transformed eye scratch buffers followed by two original DrawPrimitiveUP calls. The R84 R30 file contains a *different, default-off* DynamicVB optimization for strictly proven unindexed WorldParticle submissions; the R26-safe UP function does not invoke that ring. This is a precise source/compiled-owner gap in available optimization experiments, not a memory leak, missing eye or confirmed slowdown.

**Conditional hypothesis (UNPROVEN):** On dense *confirmed* sand/smoke/skid WorldParticle DPUP streams with meaningful bytes per physical draw, repeated CPU clones/reprojections and two UP driver uploads may consume frame budget. A single bounded dynamic-VB upload could reduce one category of driver submission overhead while preserving two independently transformed eye draws. But Lock/Unlock, driver synchronization, buffer discard stalls, GPU fill-rate/alpha overdraw, scene double-submit, host eye copies, R9 direct-fence backpressure, water/reflection or host capture may instead dominate; the GPU-ring version can be slower. No per-draw/family counters, GPU timestamps, p95/p99, Quest 3 visual test or same-SHA CPU/GPU A/B exists here.

**Falsification and disambiguation:**
- Match same exact active DLL/INI/source, source game extent and VR eye extent; sample sand-heavy vs empty roadway, buildings, water/glass and lens-heavy areas at same settings, capture game CPU render, each DPUP call vertex/stride, CPU bilateral transformation time, driver Draw UP time, alpha overdraw and GPU frame time.
- Prove original particle producer/queue epoch -> actual final API, shader/FVF, texture, Z write, alpha, RT, eye pair and restore before treating it as WorldParticle. If sand draws use another physical API or fail R26 semantic admission, this candidate does not target them.
- Compare fixed R26 control vs a separately compiled explicit research comparison with equal visual quality and optical corrections; R84 opt-in is *not* an A/B performance proof due to renderer-wide differences. Check both eye buffer bytes, Draw/SetStreamSource HRESULT, stream restoration, Reset/device loss, lack of double blend, and final host submitted frame/pose.
- If most eligible calls fall below 1 KiB/eye, are indexed, have depth-writing/StateBlock restrictions, or measured GPU alpha overdraw/copy/wait dominates without UP driver cost, reject prioritizing GPU-ring migration. If a ring has LOCK contention, stalls or p99 tails, reject regardless of theoretical upload count.
- Actual 72Hz cadence and Quest3/VDXR p95/p99 evidence is required to classify an optimization as justified; static inspection cannot declare FPS improvement.

## 4. PATCH_CANDIDATE_ONLY (NOT APPLIED)

- **A — measure only, conditional future opt-in:** src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30TryXyzrhwPrimitiveUP(), lines **3902-3945**, R30TransformXyzrhwStereo() **3750-3782**, R30TransformXyzrhwVertices() **3382-3747**, R30ExecuteXyzrhwStereo() **3784-3900**. If future physical profiling shows a repeatable CPU/UP upload hotspot for an exact WorldParticle DPUP fingerprint, consider a narrowly gated, reversible R26-specific *experiment* using two distinct eye byte spans. Preserve bilateral fallback, native DPUP on true pre-draw rejection and no replay after partial physical draw. No change proposed for indexed/VB, unrelated HUD, world glass or scenery.
- **B — reference implementation only:** src/vr/d3d9/stereo_renderer_r30.cpp::R30ParticleGpuUploadEnabled() **165-179**, R30TryXyzrhwPrimitiveUP() **6490-6593**, r30_particle_upload_policy.hpp **6-56**, r30_particle_dual_eye_ring.hpp **10-91**. Use as a static comparison for exactly gated eligibility and stream-0 restoration only; never turn on OUTRUN_VR_R30_PARTICLE_VB in the default package or auto-promote R84. Explicit source/build/runtime changes are forbidden under this task.
- **C — measure downstream contributors separately:** src/vr/d3d9/stereo_renderer_r7.inc::ResolveDirectTransport **1357-1425**, DirectTransportFrameReadyAfterPresent **1428-1447**; src/vr/d3d9/stereo_renderer.cpp::PresentDestR9 **685-809**; vrhost/src/main_r23.cpp **3165-3215,3555-3595**. Correlate physical draw and downstream copy/fence/host cadence before attributing p99 hitches to the CPU transform route.
- **No implementation:** No game/runtime C++, HLSL, source, CMake, workflow/config, test code, merge, update_ref, new branch, release, package, build or CI-skip touched. No B9200 post-CALL/+5 hook changes.

## 5. REGRESSION_RISK / NEXT_REVIEW

- HIGH optical: WorldParticle with alpha and depth write differs fundamentally from road/windshield/water/sky/lens, fixed rank, +TIME/result, ESC/F11, game sprite and opaque depth. One wrong gate can double-blend transparent fragments, alter particle parallax or suppress a real eye.
- HIGH graphics-state/device: Any new VB must preserve original DPUP stream-0 side effect, RT/depth/viewport and StateBlock state, Reset/ResetEx lifecycle, clean mono fallback, right-eye poison/restore, original FVF/VS and no stale COM references.
- HIGH source integrity: Protect immutable R26+HUD baseline 0cff83cf..., never promote R84 or interpret aab9e02... as HMD PASS; no hidden input/FFB changes, original producer hooks, unsafe B9200 post-CALL/+5 or cross-lane DX11/DXVK work.
- PERFORMANCE: Avoid per-draw logging, blocking GPU queries, force-FLUSH, global transparency culling, resolution reduction, scene-quality loss, speculative allocation/pool contention or additional per-frame copies. CPU and GPU p95/p99 over matched physical scenes decide any later experiment.
- NEXT_REVIEW: Distinct scope: verify **per-Present resource churn and GPU water/reflection profiling** under R26 default against R84-only profiler/pacing hooks, and whether dense buildings/water select non-particle work. Avoid refiling the current UP-vs-opt-in GPU ring difference or earlier 01077–01081 findings absent new physical evidence.

## 6. GITHUB_RECORD / validation and disposition

- GITHUB_RECORD: docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01082.md on vr-d3d9ex-focus via exactly one docs-only [AUTO:CONVERSION-DX9EX-01082] commit.
- SOURCE_HEAD: e2739da84919d93dfdf3553e7e3c86ecaf793481; this SHA is an input review anchor, not the result commit.
- EVIDENCE: GitHub-read R26/compared R84 source + WorldParticle semantic/policy headers, original REA static map, source host/PRESENT call sites, current AGENTS/optical policy, reviews 01078–01081, issues #129/#131. No N100 or public GitHub substitute was used.
- NEW_FINDING is a real source-level route/performance-candidate distinction, not measured runtime loss. No same-frame sand trace or tested physical original game binary was available.
- AUTOMATION_VALIDATION: Static GitHub call-path and document policy inspection complete; a post-create exact commit file-diff check must confirm that this single Markdown path alone changed. Source build gate deliberately NOT RUN for docs-only work.
- CODE_CHANGE=NO
- RUNTIME_VALIDATION=UNTESTED (no Windows game/GPU profiler trace or Quest 3/VDXR matched build/HMD acceptance).
