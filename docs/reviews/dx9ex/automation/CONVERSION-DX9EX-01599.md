# CONVERSION-DX9EX-01599 — R26 write-free occlusion shortcut cannot itself colour-render the lens flare (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01599
PRODUCTION_ID=CONVERSION-DX9EX-01599
EVENT_ID=CONVERSION-DX9EX-01599-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=635e39acc2002d00910779da035c8cd2b4af4d83
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_READBACK
REVIEW_SCOPE=LENS_FLARE_ONLY
DX9EX_REVIEW_ONLY=ON
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_AB_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
RUNTIME_VALIDATION=UNTESTED
ROOT_CAUSE=UNCONFIRMED

## Narrow independent falsification

01597 proves only a **conditional source-c64 invalidation** for split-only projected C993 shader constants, while 01598 follows the subsequent R30 fallback and describes R29. Importantly, earlier 01588 already establishes that the **default compiled R26+HUD** `R30Draw*R29Hook` hooks actually target `Draw*DestR26`, not R29. Do not repeat 01588 as a new result or use 01598's R29 hypothetical as the default compiled chain.

This review asks a different *downstream, pixel-write-specific* question: when R30 cannot admit a C993/CABE lens primitive, can **R26's tracked-occlusion single-execution shortcut** itself emit a visible mono/headlocked RGB lens lobe? The code-level answer is **NO under the shortcut's declared, valid render-state assumptions**: it is reachable only if the tracked COLORWRITEENABLE is **exactly 0**, ZWRITEENABLE is FALSE and stencil writes are disabled (stencil test off or write mask 0). R26 then executes one original Draw but, with those actual GPU states honored, that Draw cannot write the visible colour lens lobe. This sharpens 01588's general 'R26 may execute once' statement without claiming an actual 0x570002/006/00F/010 or 0x570008 physical sample entered this branch.

**Crucial distinction:** when the original flare can write colour (or any required state read is invalid), R26's write-free predicate returns false and delegates to **R23**; R23 passes into the existing R22 chain. **R13 has a separate unsafe-query/MRT single-execution/mono-shadow decision that does not require colour writes to be disabled.** Therefore 'single execution' and a visible mono lobe cannot be attributed to the R26 write-free counter alone. R22 may also reject stereo and directly call the original, depending on its own eligibility. The final R13/R9 physical RT behaviour and R19/R24 OpenXR acceptance remain *unobserved*.

NEW_FINDING=STATIC_NEGATIVE_CONTROL_R26_QUERY_ONLY_SINGLE_DRAW_REQUIRES_COLORWRITEENABLE_ZERO;_VISIBLY_COLOURED_LENS_DRAW_MUST_TAKE_DIFFERENT_STAGE_OR_UNVERIFIED_STATE_MISMATCH
NEW_FINDING_TYPE=PINNED_R26_R23_R22_R13_CROSS_STAGE_PIXEL_WRITE_INVARIANT
NEW_FINDING_RUNTIME=NONE
NEW_REGRESSION=NOT_ESTABLISHED

## SOURCE_TRACE — actual current GitHub source, 1-based lines

1. `src/hooks_graphics.cpp:1137-1153,1166-1190,1245-1290` — original C993 projected source ID family, source-call serial, nonqueued projected `ProducerToken::None`, `Game::DrawObjectAlpha_Internal`; wrapper/opaque 405360/4052C0 deferral is not a GPU Draw receipt. CABE 0x570008 outer path is distinct.
2. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:14,7606-7666,8638-8654,8930-8942` — compiled TU includes R26; R30 guard `E_NOTIMPL` invokes misleadingly named `r29Draw()`, which is installed on `DrawPrimitiveDestR26` etc. Four Draw variants require independent actual API/physical identity. Logged `resultRoute=R29_FALLBACK` is a nominal label, not an R29 GPU-eye verdict.
3. `src/vr/d3d9/stereo_renderer_r26.cpp:338-351` — single-exec eligibility requires game device, main backbuffer, no aux RT, no forced-mono shadow, query tracking available, stereo wanted/seeded and an active occlusion query.
4. `src/vr/d3d9/stereo_renderer_r26.cpp:354-385` — **new discriminating predicate:** authoritative `ReadTrackedRenderState` must return COLORWRITEENABLE==0 and ZWRITEENABLE==FALSE; STENCILENABLE read must succeed; if enabled, STENCILWRITEMASK must equal 0. Any colour-writing primitive fails R26's special-case admission.
5. `src/vr/d3d9/stereo_renderer_r26.cpp:388-425,777-842,1001-1014` — if the query check fails OR write-free check fails, call saved R23 draw. Only a positive write-free check invokes `NotifyTopLevelDraw`, increments `R26TrackedOcclusionSingleExec`, and calls `actualDraw()` once, bypassing R23/R22/R13/R9 for that primitive.
6. `src/vr/d3d9/stereo_renderer_r23.cpp:539-592` — top-level draw serial/state sampler and forwarding to R22; R26 direct shortcut manually accounts for that top-level draw. Its serial proves draw bookkeeping, not two successful eye pixels.
7. `src/vr/d3d9/stereo_renderer_r22.cpp:624-690` — if stereo callbacks are ineligible or raster replay scope cannot be captured, original draw is invoked directly; otherwise delegate to the existing R9 interception chain. The source does not justify a guaranteed two-eye result.
8. `src/vr/d3d9/stereo_renderer_r13.cpp:592-655` — **separate** unsafe-query or MRT replay policy: `R9Poison`, conditional mono-shadow or original one-draw and `R9MonoBackupGap`, without R26's COLORWRITEENABLE==0 filter. Source conditional, not observed flare behaviour.

PINNED_BLOBS=R26_CURRENT_AND_BASELINE:4e486a14c0f180928732419868f5449b6d8759cf;R23_CURRENT_AND_BASELINE:8a80c3220c3571ececbf8218ef4c5f3226985a01;R22_CURRENT:dd1cbed902f468166dcf93598ca0b24043584dad;R13_CURRENT:4e01217e5e1d9e2b136501a0c28efadfefdc0094;R30_SAFE_CURRENT:83a2821bd53d043d7df0557f46627d0af1205d48;C993_HOOKS_CURRENT:982f55dc91c00faf336c06317006fe4aba11db1a
BASELINE_COMPARISON=R26_AND_R23_BYTE_IDENTICAL_AT_PROTECTED_R26_HUD_BASELINE;_NO_NEW_SOURCE_REGRESSION_INFERRED
EXISTING_REVIEW_ADOPTION=01588_DEFAULT_LOWER_R26_IDENTITY_AND_01597_01598_C993_RAW_C64_PREMISES_REUSED_NOT_RECLAIMED_AS_NEW

## HYPOTHESIS_LEDGER — lens only

| ID / hypothesis | Status | Prior evidence -> 01599 evidence | Exact falsification |
| --- | --- | --- | --- |
| A: unintended extra game-origin lens emitter | OPEN | Multiple original C993 central IDs and CABE 0x570008 outer calls preexist. R26 query shortcut creates no source wrapper. | Original CALL/source object/texture/PMT material fingerprint shows an extra unintended same-source emission. |
| B0: default R26+HUD `R29_FALLBACK` label means actual R29 stereo replay | REFUTED_STATIC_INHERITED | 01588 proves R26 target; 01599 independently pinned current `stereo_renderer_r30_r26_safe.cpp:8930-8942` against R26/R23 chain. Not a new score-worthy finding. | Exact default linked binary contradicts source hook identity. |
| B3: R26 write-free active-query shortcut causes a new *visible* mono flare lobe | REFUTED_UNDER_VALID_GPU_STATE | New: `R26TrackedOcclusionDrawIsWriteFree` requires RT colour mask 0, depth write off and stencil no-write before single actual Draw. It cannot newly colour-render a visible lobe *in that Draw*. | Matched physical draw with successful R26 shortcut shows live COLORWRITEENABLE nonzero or same-draw RT RGB PRE/POST change, after excluding state-shadow divergence, different pass and host cached imagery. |
| B4: R13 unsafe-query single execution could leave a visible mono lens path | OPEN_CONDITIONAL | R26 rejects colour writers to R23; R13's separately classified unsafe query/MRT branch can call mono-shadow/actual without R26's write-free predicate. | Source-matched lens primitive never reaches R13 unsafe branch, stereo/seed/query gate excludes it, or accepted L/R RGB proves correct stereo. |
| C: wrong C993 source c64 or per-eye projected WVP yields head-follow | OPEN | 01596/01597 conditional full-source alias vs split-only invalidation remain. R26 write-free case is colour-inert, cannot prove camera alignment. | Matched physical shader upload/c64 origin, native eye WVP, two-yaw native and accepted XR centroids show correct world bearing. |
| D: intended centre/halo/glow/rays mistaken for duplicate | OPEN | Four C993 IDs plus CABE outer materials not reduced to a unique physical texture/pass. | Exact original source+PMT+texture/alpha/eye ROI separation identifies intended vs extra same-eye colour passes. |
| E: host cache / composite repeats a correct native lens | BLOCKED_RUNTIME | Neither R26 shortcut nor R13 decisions measures R19/R24 accepted XR image/layer. | Fresh frame/QPC, two-eye accepted layer and final ROI prove/no-prove host duplicates over two yaws. |
| F: head-local source/HMD pose mismatch | BLOCKED_RUNTIME | Original source position, pose and eye submission not joined; user has reported double/head-follow only. | Two-yaw same-source world bearing matched to current L/R projection, RT and accepted XR composition. |

## Different next-step falsification, no source edits this task

| Authentic one-source lens draw condition | Predicted R26 decision | Predicted image/log implication |
| --- | --- | --- |
| Active query, true no-write states and no aux RT, stereo seeded | `R26TrackedOcclusionSingleExec++`; exactly one underlying original API draw | RGB delta on its RT0 should be zero; **no claim about other lens materials or preexisting host frame**. Any same-draw colour delta suggests wrong capture/state-shadow/physical identity or unexpected behaviour. |
| Active query but COLORWRITEENABLE != 0, ZWRITEENABLE != FALSE, stencil write enabled or state read fails | `R26OcclusionWriteRejects++`, delegate R23 | Do **not** treat R26 rejection as stereo success. R22 gate and downstream R13 unsafe/legacy decision must be captured separately. |
| Colour-capable lens draw reaches R13 with active query/MRT unsafe | R13 may poison stereo and route mono-shadow or original once, depending on seed/depth history | A single colour-writing primitive is possible in this **distinct** path; need physical RT RGB and accepted XR eyes to determine any visible mono/duplicate. |
| No active occlusion query or R26 other eligibility fails | R26 delegates R23 directly | R26's single counter in other frames cannot explain the target draw. |
| R30 first stage handles fixed-function/XYZRHW or admitted shader | R26 lower chain not entered via this Guard | Must tag actual R30 physical LEFT/RIGHT/restore and XR; never infer R26 from source call alone. |

SOURCE_TRACE=GITHUB_PINNED_C993_TO_R30_NAMED_R26_LOWER_TO_R26_WRITE_FREE_OR_R23_R22_R13;_R9_NATIVE_EYES_AND_HOST_OPENXR_NOT_OBSERVED
EVIDENCE_SOURCE=EXACT_GITHUB_BLOBS_AND_CODE_BRANCHES_ABOVE
EVIDENCE_DISASM=INHERITED_ONLY_405360_4052C0_C993_CABE;_NO_NEW_EXE_DISASSEMBLY_OR_BINARY_EXECUTION
EVIDENCE_LOG=NONE_NEW;_NAMED_COUNTERS_AND_FORMAT_STRINGS_ARE_NOT_RUNTIME_SAMPLES
EVIDENCE_USER_REPORT=EARLIER_CENTRAL_FLARE_DOUBLE_AND_HEAD_FOLLOW;_NOT_REPRODUCED_ON_THIS_SOURCE_SHA
EVIDENCE_GAPS=Actual authenticated C993/CABE PMT/texture/VS/FVF to physical Draw; active-query availability and tracked-vs-live D3DRS state; R26 counter mapped to exact PMT; R22 gate and R13 branch choice; successful per-eye GPU RGB PRE/POST; R19 source frame/QPC and R24 accepted XR layer/pose; Quest3/VDXR two-yaw result; installed CMake cache and binary identity.

NEXT_FALSIFICATION_TEST=Read-only matched `C993 object/sourceCallSerial/lensSequence` OR `CABE ordinal/opaque PMT` -> `physicalDrawSerial,PMTpass,texture0,VS,FVF,API` -> `R30 early/failed/raw stage` -> `R26 queryActive,source RT0,tracked+live COLORWRITEENABLE/ZWRITEENABLE/STENCILENABLE/STENCILWRITEMASK,query-single/reject count` -> `R23/R22 eligible,actual R13 policy/mono-gap, R9 per-eye attempt/HRESULT/RT RGB BEFORE/AFTER` -> `R19 sourceFrameId/QPC,R24 accepted xrEndFrame projection layer/pose,arrayIndex,L/R centroids` for two yaw poses. Positive control: write-free R26 once yields zero same-RT RGB delta; negative control: colour writer R26 forwards and may be R13 unsafe single; false shortcut if live write mask !=0. Distinguish normal L/R two draws from same-eye duplicates by RT identity, blend and original texture/pass.
EXPECTED_SCREEN_BRANCHES=R26_WRITEFREE_ZERO_NEW_RGB;_R13_UNSAFE_MAY_BE_VISIBLE_SINGLE_NOT_AUTOMATIC_STEREO_PASS;_INTENDED_SEPARATE_MATERIALS_MAY_APPEAR_AS_TWO_LOBES;_XR_DUPLICATE_REQUIRES_FRESH_ACCEPTED_FRAME_PIXEL_PROOF
NEXT_REVIEW=LENS_FLARE:R26_COLOUR_WRITE_MASK_NEGATIVE_CONTROL_VS_R13_UNSAFE_QUERY_AND_ACCEPTED_XR_EYE
PATCH_CANDIDATE_ONLY=NONE_NOT_APPLIED;_ONLY_IF_AUTHENTIC_RT_RGB_FALSIFIES_R26_WRITEFREE_INVARIANT_REVIEW_src/vr/d3d9/stereo_renderer_r26.cpp:354-425_FOR_TRACKED_VS_LIVE_STATE_DIVERGENCE;_NO_GLOBAL_FLARE_SUPPRESSION_OR_DRAW_REPLAY_CHANGE;_REGRESS_QUERY_SIDE_EFFECTS_AND_R26_HUD_R84_AB
REGRESSION_RISK=DOCS_ONLY_NONE;_IF_LATER_PATCH_PROPOSED_PROTECT_QUERY_SIDE_EFFECTS_R26_HUD_BASELINE_R23_R22_R13_R9_LEFT_RIGHT_DEPTH_STENCIL_WVP_RESTORE_CABE_DEFERRED_PMT_INTENDED_HALOS_R19_R24_XR_FRESHNESS;_B9200_FORBIDDEN
SCORE_DELTA=0_NO_NEW_RUNTIME_OR_PHYSICAL_DRAW_EVIDENCE;_EXISTING_LOWER_HOOK_IDENTITY_IN_01588_NOT_RESCORED
AUTOMATION_VALIDATION=PENDING_GITHUB_REMOTE_COMMIT_AND_SINGLE_FILE_DIFF_READBACK
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01599.md
