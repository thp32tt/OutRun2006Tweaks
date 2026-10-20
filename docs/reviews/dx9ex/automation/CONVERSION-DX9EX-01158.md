# CONVERSION-DX9EX-01158 — Stage transparency draw ordering / SkipQuickSort review

DATE=2026-10-21 KST
TASK_ID=CONVERSION-DX9EX-01158
PRODUCTION_ID=CONVERSION-DX9EX-01158
EVENT_ID=CONVERSION-DX9EX-01158-E001
MODE=DX9EX_REVIEW_ONLY
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=7973123c4b835079ea30104d55c57fd3fd3a0285
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
BUILD=NOT_RUN
CI=NOT_RUN
SOURCE_BUILD_GATE=NOT_APPLICABLE_DOCS_ONLY
R26_HUD_BASELINE=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9
R84_HUD_CANDIDATE=aab9e02bcb2ad2e6253840e6267e5c5ad5040854
R84_AUTOPROMOTION=NO
PATCH_APPLIED=NO

## REVIEW_SCOPE

Original stage model list sorting, opaque/blended ordering, and a per-stage setting ignored by the replacement sort. This differs from 01157 R62 projection restore, 01142 PMT visibility, 01141 WorldParticle UP uploads, 01143 screen-edge projection and 01149 host frame accounting.

## Source-based rendering-path simulation

1. Producer: checked-in REA architecture describes original game loop `0x00417B20`, stage scheduler `0x00449050` and indirect world drawing callbacks, but does not prove one sand/particle physical call. `src/hooks_drawdistance.cpp:481-576` can collect unique collision nodes and call `Game::DrawObject_Internal` when its draw-distance setting enables the associated producer. These are stage model nodes, not D3DX sprite priority nodes.
2. Stage queue: `StableDrawSort::DrawStoredModel_Execute_dest` at `src/hooks_drawdistance.cpp:415-428` sorts `Game::s_AftDrawBuffer`, invokes `Game::DrawStoredModel_Internal`, then resets counts. `SortDrawBuffer:394-413` uses `CenterZ_0 - CullNode.radius` ascending, with stage-entry pointer tie break. Source comments `369-384` describe reverse opaque and forward blended consumption, with blended surfaces depending on list order; unscaled object-space radius is an acknowledged approximation.
3. Independent SpriteNode/semantic/queue and D3DX boundary: original `0x0042D710` sprite queue, kind-0 D3DX Draw/Flush/End and type-1 native UP are separate from this stage DrawBuffer. Stage sort alone does not assign `WorldParticle`, `ScreenHud`, R62 fixed-function, physical Draw API, or texture/material identity. These require a verified physical fingerprint.
4. Actual GPU boundary: selected option-free R26+HUD is documented at `AGENTS.md:1-11` and `CMakeLists.txt:99-150`. Native DP/DIP/UP hooks in `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5339-5480` consume draw semantic and evaluate distinct stereo admission/fallback. XYZRHW UP at `3937-3979` creates separate left/right buffers only on qualifying state; `R30SafeStereoBase:74-92` rejects invalid RT/depth/pose/recovery. R62 fixed-function kind-0 sprite DIP is a separate branch, not an automatic result of stage sort.
5. Eye/restore/final display: qualifying R30 draw uses eye-specific target/state and restores according to `R30ExecuteXyzrhwStereo:3820-3935`. `src/vr/d3d9/stereo_renderer.cpp::PresentDestR9:676-818` accepts eligible stereo or falls back; host `vrhost/src/runtime/d3d9ex_direct_passthrough_r32.hpp:260-325` advances SafeFrameId only after completed copy/publish and `vrhost/src/main_r23.cpp:3565-3610` observes final xrEndFrame. Thus CPU sorted entry, actual native draw, both-eye success, Present and Quest3 image are different evidence layers.

## NEW_FINDING

NEW_FINDING=CONFIRMED_STATIC_PER_STAGE_SKIPQUICKSORT_SETTING_IGNORED_BY_STAGE_SORT_AND_PARSED_BOOLEAN_VALUE_NOT_APPLIED.

Confirmed fact A: `src/hooks_drawdistance.cpp::DrawDist_ReadExclusions:286-306` reads `SkipQuickSort` as a boolean, but on successful parsing sets the stage bit to true without checking the parsed value; thus a successfully parsed false is also marked true.

Confirmed fact B: `src/hooks_drawdistance.cpp::StableDrawSort::DrawStoredModel_Execute_dest:416-423` has its `if (!SkipQuickSortHackStages[*Game::stg_stage_num])` condition commented out, while `SortDrawBuffer` runs unconditionally. **When the replacement hook runs**, the per-stage skip bit cannot bypass its sort. This is a static configuration-path fact, not proof the deployed package enabled the hook or that any graphics are broken.

Potential optical/performance consequence (HYPOTHESIS_ONLY): in a dense stage containing overlapping translucent modeled surfaces, the unscaled single-view sort and unavailable per-stage exclusion could impede A/B isolation of ordering and CPU sort overhead. Actual model/particle identity, world scale, alpha/depth state, texture, per-eye order, frame timing and Quest3 symptom remain unknown.

FALSIFIERS: exact R26 artifact lacks an active replacement hook; stage has no relevant SkipQuickSort config; sorted list has at most one entry or the same original order; affected physical draw is a D3DX HUD sprite rather than stage geometry; both eye outputs are already correct; p95/p99 issues instead match world GPU, Present, copy fence or XR; verified A/B finds no visible or CPU difference. No HMD, profiler, fresh original disassembly or exact matched source GPU trace was available this run.

## PATCH_CANDIDATE_ONLY

PATCH_CANDIDATE_ONLY=YES. No implementation is authorized or applied.

- Candidate 1 (configuration control, later authorization only): `src/hooks_drawdistance.cpp::DrawDist_ReadExclusions:286-306` and `StableDrawSort::DrawStoredModel_Execute_dest:415-428`. Correctly honor parsed skip value and test an exact stage-specific guarded route. Do not blindly skip sort: bypassing the replacement sort may leave insertion order rather than restoring original game's sort. Require an independently proven safe baseline. Reject if the hook/config is inactive or skipped sorting worsens blended order.
- Candidate 2 (opt-in bounded diagnostic, later authorization only): `StableDrawSort::SortDrawBuffer:385-413`, `DrawStoredModel_Execute_dest:415-428`, `stereo_renderer_r30_r26_safe.cpp:5339-5480`, `stereo_renderer.cpp:676-818`. Correlate stage draw-entry identity, sort key, radius/scale, material alpha/Z, actual GPU API/VS/PS/FVF/texture, left/right result and restore, game Present, host SafeFrameId and XR submission. Reject if correlation is not exact or profiling changes frame pacing.

## REGRESSION_RISK / EVIDENCE

REGRESSION_RISK=HIGH_FOR_CHANGING_BLENDED_ORDER_OR_BOTH_EYE_ALPHA_OCCLUSION; HIGH_FOR_GLOBAL_STAGE_NODE_OR_SHADER_RECLASSIFICATION; HIGH_FOR_UNPROVEN_SKIP_SORT_OR_R84_PROMOTION; MEDIUM_FOR_HOTPATH_LOGGING_STUTTER.

Positive controls: exact stage and camera, original R26+HUD package SHA, per-entry order, native draw fingerprint, nonzero eye cant, per-eye pose/extent, restore and final frame ID. Negative controls: 6th/6, rank/rival, +TIME/GOAL/result D3DX batches, F11/ESC, lens/SkyGlow, world particles with no stage DrawBuffer ownership, Reset/device loss. Do not reintroduce unsafe B9200 post-CALL/+5 hooks.

EVIDENCE=Connected GitHub pinned source `AGENTS.md:1-11`, `CMakeLists.txt:99-150`, `src/hooks_drawdistance.cpp:19-26,286-306,365-445,480-597`, `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:74-92,3820-3979,5116-5480`, `src/vr/d3d9/stereo_renderer.cpp:676-818`, `vrhost/src/runtime/d3d9ex_direct_passthrough_r32.hpp:260-325`, `vrhost/src/main_r23.cpp:3565-3610`, `docs/automation/OUTRUN_REA_RENDERING_ARCHITECTURE_20261018.md`, predecessor 01157 and independent 01141-01144. Older frame-drop evidence was not used as present-day exact-build measurements. New original x86 bytes and current runtime/GPU logs were not obtained.

GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01158.md
CHANGED_PATH_ALLOWLIST=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01158.md
COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01158]
AUTOMATION_VALIDATION=PINNED_STATIC_GITHUB_REVIEW_COMPLETE_POSTCOMMIT_DIFF_REQUIRES_CHECK
RUNTIME_VALIDATION=UNTESTED
CODE_CHANGE=NO

NEXT_REVIEW=Identify an original sand/spray producer and actual physical GPU draw with exact bounded source/token/queue/texture/RT/VS/PS; correlate paired-eye restoration and game Present/host copy/XR timing. If no new original or physical evidence exists, record NEW_FINDING=NONE with genuinely distinct inspected boundaries rather than repeating this configuration-path finding.
