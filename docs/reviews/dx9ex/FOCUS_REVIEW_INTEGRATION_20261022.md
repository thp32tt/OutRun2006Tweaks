# DX9Ex focus review integration — 2026-10-22 (direct user instruction)

- RUN_KEY=DIRECT-DX9EX-REVIEW-INTEGRATE-20261022
- BASE_HEAD=ea1c705077dd2e1453aac10bad4238d2a595701e
- TARGET=vr-d3d9ex-focus; FOCUS_BUILD=R26+HUD (PC Fast)
- AUTHORITY=Current 2026-10-22 direct user request to recheck Oct 21–22 reviews and selectively integrate safe, source-confirmed guards; this direct/manual task is separate from every automated DX9EX REVIEW_ONLY dispatch. Automated review remains REVIEW_ONLY.
- REVIEW_CATALOG=GitHub commit history for `docs/reviews/dx9ex/automation/` from 2026-10-21 00:00 KST to 2026-10-22 current: ~330 review history entries (two corrected/repeated TASK_ID commits). Catalog titles and sampled high-risk source findings examined; this note does not claim that all ~328 document bodies or HMD behavior received independent full verification.
- RECENT_DUPLICATE=01350 and 01418 both identify pre-HUD SkyGlow capture epoch versus reduced-texture reallocation; 01326 and 01417 cover separate but substantially overlapping postprocess failure propagation. No extra automation TASK_ID or finding score credited for repeated source observations.
- ACTIVE_BUILD=Fresh R26+HUD default in CMakeLists.txt, `vr-pc-fast-build.yml` invokes `tools/Build-OutRunPCFast.ps1`; R84 in `src/vr/d3d9/stereo_renderer_r30.cpp` already invalidates a stale capture on reallocation and fails closed after Ensure. No R84 default promotion.
- SELECTED_SOURCE_CONFIRMED_PARITY_FIX=In `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp`, invalidate `R30SkyGlowSceneCaptureEpoch` only when reduced GPU resources are released/replaced, then skip optional bloom after Ensure when a qualified screen producer already drew in this Present and clean source no longer matches. Preserve the regular successful clean-pair path, original no-UI fallback, Reset epoch sentinel, original game rendering, left/right StateBlock/RT/depth/viewport restore, R7 DirectGPU/SBS, R23 XR.
- REGRESSION_TEST=Extend existing `tools/verify_vr_skyglow_capture_boundary.py` with R26 release/Ensure/capture ordering checks and three negative mutation fixtures; independent R84 and screen-semantic checks retained unchanged.
- DEFERRED_NOT_SAFE_TO_AUTO_APPLY=R69 CABE WVP-to-XR ray remap (01415/01416), unilateral GPU additive failure rollback (01326/01417), XR menu cache/desktop geometry changes (01409), masked GPU ancestry (01403/01410), rank/rival optical retiming, +TIME/GOAL original deferred D3DX queue, particle/performance fastpaths without p95/p99 evidence, scissor/projection and nonzero eye-cant hypotheses. Such findings need runtime same-SHA GPU/Quest3 verification or a separate guarded implementation task; no global heuristics or B9200 +5 unsafe hook.
- BASELINE_PROTECTED=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9; COMPARATOR_ONLY=aab9e02bcb2ad2e6253840e6267e5c5ad5040854.
- CI_PLAN=source-change exact-SHA DX9Ex Active / PC Fast / Domain and changed-area static checks, report actual status rather than declaring success before CI; no CI skip directive.
- RUNTIME_VALIDATION=UNTESTED; Quest 3/VDXR image quality and 72Hz performance remain not proven by GitHub Actions.

## Validation follow-up — inherited R26 F11 assertion repaired

- SOURCE_COMMIT=ab5a4c64c060cedf20a52a4603cfea97150ae82b; first exact-SHA DX9Ex Active run #39724302083 failed in policy at `tools/verify_vr_r30_generic_shader_overlay.py:46`, asserting hardcoded `R30BuildHudPlaneCoefficients(state, true)`.
- Proven pre-existing: original pre-source-change parent `fbe315721c91d0fb4d15e4ed23edf945ccd5b0ac` already uses `R30BuildHudPlaneCoefficients(state, !externalF11)`, which selects the intended external-F11-only smaller plane while retaining gameplay HUD scale. The failing verifier script itself was not touched by initial SkyGlow patch.
- ACTION=update stale invariant to require the exact `ExternalOverlaySemanticDepth && semanticOverlay2D` decision and `!externalF11` invocation, plus three destructive negative mutations. No runtime/C++ edit during this follow-up. Do not treat static repair as headset validation.
- NEXT=rerun exact-SHA DX9Ex Active/PC Fast/Full Source/HUD/Domain gates on final integration SHA, record observed status only. RUNTIME_VALIDATION=UNTESTED.

## HUD Inspector inherited declaration/definition parser correction

- The initial exact-SHA HUD Inspector run #39724302173 failed in `verify_vr_visual_composition_p0.py` because `function_body` selected the forward declaration of `R30ConfigureXyzrhwWorldEffect` and then parsed `R30PrepareXyzrhwState`, where route=1u is intentionally absent. The real R30Configure definition already contains the 1u diagnostic call before this task's runtime source modification.
- Update the verifier to explicitly seek the second `R30ConfigureXyzrhwWorldEffect` occurrence (actual definition) for route=1u, preserving the other two route checks and all three deliberate trace-removal mutation controls. This changes no in-game trace, GPU draw, F11 scale or runtime C++.
- RUNTIME_VALIDATION=UNTESTED; a new exact-SHA test run is still required to claim validation success.
