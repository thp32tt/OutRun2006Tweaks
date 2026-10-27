# LENSFLARE-NATIVE-DRAW-MULTIPLICITY-20261027-1815 — original native-draw multiplicity is not automatically a duplicated visible flare

- DATE=2026-10-27 18:15 KST; RUN_KEY=LENSFLARE-NATIVE-DRAW-MULTIPLICITY-20261027-1815; SOURCE_HEAD=f66bd019462c036f19e1da7593001a426492480e; SOURCE_SSOT=GitHub; BRANCH=vr-d3d9ex-focus; MODE=DX9EX_REVIEW_ONLY; REVIEW_SCOPE=LENS_FLARE_ONLY.
- BASELINE=R26+HUD; BASELINE_SHA=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9; R84=COMPARISON_ONLY; B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN.
- INHERITED=CONVERSION-DX9EX-01522..01531, LENSFLARE-QUEUE-IMMEDIATE-20261027-1654, LENSFLARE-ROUTE-DIVERGENCE-20261027-1655, LENSFLARE-OPAQUE-MATRIX-20261027-1722, LENSFLARE-SCENE-SCOPE-FALLBACK-20261027-1730. Prior reviews proved source-call ordinal != physical Draw, 4056D0 queue/undo gates, per-entry original world matrix, and pre-R30/R30 semantic forks. This review independently resolves what **multiple native Draws from one original admitted object** can mean.
- EVIDENCE=PINNED_CURRENT_MOD_GITHUB_PLUS_ORIGINAL_RECONSTRUCTION_GITHUB; ORIGINAL_REPO=r4dius/outrun2-decomp@e1e1c592b802a6f3f7020a676abd3ba1be479e62; ORIGINAL_EXE_NEW_DISASM=NO; ACTUAL_PMT_ASSET=NOT_READ; HMD_QUEST3=NOT_RUN; GPU_TRACE=NONE; CI=NOT_RUN; CI_SKIP=NONE; DOCS_ONLY_SOURCE_BUILD_GATE=NOT_REQUIRED; CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED.

## NEW_FINDING — original 405890 two-pass material traversal and 570010 query-only draw invalidate a simple duplicate-count rule

NEW_FINDING=ORIGINAL_405890_ONE_OPAQUE_DESCRIPTOR_CAN_VISIT_TWO_DIFFERENT_MATERIAL_PASSES_AND_570010_OCCLUSION_QUERY_HAS_AN_INDEPENDENT_ZERO_COLORWRITE_NATIVE_DRAW_PATH.
STATIC_CONFIRMED=EXACT_ORIGINAL_RECONSTRUCTION_BRANCHES_AND_RENDER_STATES; CURRENT_AFFECTED_LENS_ASSET_AND_HMD_PHYSICAL_PATH=UNTESTED; ROOT_CAUSE=UNRESOLVED.

### A. One original 405360 mesh entry may be drawn by two native material passes

1. Reconstructed `src/platform/pc_render_queue.cpp::walk_404d10:169-179` creates one visible mesh descriptor with `d.node`, `d.mesh`, `d.matrix` and queue index. `src/platform/pc_render_flush.cpp::Flush::flush:803-889` first loops backwards over opaque entries if `pass_404600(0)` is enabled, selecting nodes with `flags & 1`; then loops forwards if `pass_404600(1)` is enabled, selecting nodes with `flags & 2`. There is no mutual-exclusion condition between the flags. A PMT node with BOTH flags and both passes enabled can therefore be visited twice **without** a duplicate 405360 descriptor or 4052C0 flush. This is a conditional possibility, NOT a verified flag value for 0x570008.
2. Each visit invokes `draw_404700:761-801` with `e.pass=0` or `e.pass=1`; it selects `prim.draws[e.pass]`, `prim.first_draw[e.pass]`, material, shader, texture and primitive range separately. Thus two native DrawIndexedPrimitive calls can be two *different original material draw records*, not replay of one primitive. `pass_404600:174-181` changes alpha blend, zwrite, colour-write mask and alpha-test state. `render_pass_defaults_404540:1081-1087` normally enables both passes for layer 0 and non-2 layers; layer 2 disables pass 1. Actual sun-flare stage pass enable and PMT flags remain unknown.
3. A previous proposed B-test `same originalSerial+descriptor+eyeRT drawn twice` is too weak: require the SAME `flushID+descriptor+passIndex+primitiveIndex+drawRecordIndex+material+eyeRT` with colour writes enabled to show a true unexpected same-eye replay. A pass0/pass1 pair, even with matching object ID/texture, is an **original** two-pass candidate until material lists and blend state are checked. One original native draw may also intentionally be submitted once to LEFT and once to RIGHT by R30, not a same-eye duplicate.

### B. C993 0x570010 also has a separate original occlusion-query native draw with no colour write

1. Reconstructed `src/platform/race_course_passes.cpp::sun_flare_40cbc0:649-675` records 0x570010 for occlusion at :669, calls `occlusion_411420` at :671, then separately invokes visible `sun.draw_40c980(0x570010,1.0f)` at :672. The visible call uses `Sun::draw:431-437 -> render_object_override_4056d0`, which current `src/hooks_graphics.cpp::DrawObjectAlphaCentre:779-836` wraps. The query call instead uses `occlusion_draw_4114e0:500-513 -> pmt_object_draw_4116f0` (implementation `src/platform/pc_render_flush.cpp:1024-1057`), bypassing the 4056D0 source wrapper and its sampled C993 source-call log.
2. The query draw is conditional: `record_4113e0:493-499` may decline a second record, `occlusion_draw_4114e0:502-506` may skip when query GetData returns 1, and bank/mesh validity can prevent GPU submission. If it executes, `occlusion_411420:520-531` snapshots states `[7,14,15,168]`, sets `[1,0,0,0]` during `pmt_object_draw_4116f0`, then restores. The reconstructed `src/platform/pc_d3d9_state.hpp:17-23` defines **7=ZENABLE, 14=ZWRITEENABLE, 15=ALPHATESTENABLE, 168=COLORWRITEENABLE**; 27 is ALPHABLENDENABLE. Consequently the original query draw has depth test ON, depth writes OFF, alpha test OFF and **colour writes OFF**. The nearby source prose mentions alpha blending, but the actual state setter does not modify D3DRS_ALPHABLENDENABLE; do not infer it from the comment.
3. Therefore seeing 0x570010 native object geometry in an occlusion-query pass and again in its visible 4056D0 path is **not** proof of an extra visible sun or B replay. The query geometry contributes no colour under the original zero-colour-mask state, even if the native Draw executes. This does not prove that the current VR hooks preserve the mask on an affected Quest3 frame; physical state/RT evidence is absent.

### Scope and independence

- This is distinct from 01529 (source logs not physical draws), 01530 (4056D0 admission can skip), 01531 (pre-R30 c64 upload fork), 1722 (original matrix snapshot) and 1730 (R30 eye projection semantic fork): it identifies **two independently source-proven reasons for native Draw multiplicity without a second visible emitter**, including a colour-write-zero query and the separate PMT pass draw lists. No HMD double image, current PMT pass flags, or actual source pixel duplication is claimed.
- The original game's renderer performs these conditional paths independent of the mod; this is NOT a proven regression against immutable R26+HUD baseline. Do not conflate opaque queue, D3DX SpriteNode, R30 L/R duplication or host XR layers.

## HYPOTHESIS_LEDGER

| Hypothesis | Current status | New falsification condition |
| --- | --- | --- |
| A extra source emitter | OPEN; two 570008 calls intentional | One opaque entry visited in pass0/1 or one 570010 query+visible pair does not establish extra 4056D0 emitter; prove an unexpected third original source serial. |
| B same-eye replay | OPEN; NO GPU PROOF | NEW: same descriptor+eyeRT+two Draws is insufficient. Compare **same pass+primitive draw record+material+source serial+eyeRT+colour mask**, excluding normal two-pass, query-only and LEFT/RIGHT. |
| C incorrect per-eye WVP/depth | CONDITIONAL_STATIC; OPTICS UNTESTED | Pass0/1 can use distinct shader/material; compare c64 and per-eye WVP per actual pass. If all match intended pose/eye projection, this cause is falsified for that object. |
| D legitimate alpha overlap | SUPPORTED_ORIGINAL_DESIGN; CURRENT PIXELS UNKNOWN | Two-pass material can add legitimate visible layers IF asset has both flags/draw lists and colour writes. 570010 query colour mask zero cannot create a second visible layer in original state. |
| E host fresh/cached duplication | SAME-TICK_NORMAL_TWO_LAYER_RULED_DOWN; TEMPORAL OPEN | Native passes/query occur upstream; still join one host fresh/cached XR tick and final projection layer/view identity. |
| F head-lock/pose | OPEN | Draw multiplicity alone does not prove head-lock; require source world/c64, headInverse, L/R pixel rays under real head yaw. |
| G original world matrix lost on deferral | REFUTED_NORMAL_RECONSTRUCTION by 1722 | Two original passes share descriptor matrix; material and semantic/pose can still diverge. |
| H two native draws == two visible suns | REFUTED AS AN INFERENCE (new) | Original pass0/1 and zero-colour-write query are concrete alternatives; physical PMT and render-state receipts decide. |

## SOURCE_TRACE

1. Original reconstructed emitter `r4dius/outrun2-decomp@e1e1c592b802a6f3f7020a676abd3ba1be479e62/src/platform/race_course_passes.cpp:431-453,493-531,649-675,695-718`, blob `22985e118c172467c566fe58d5b08f280c565ee2`.
2. Original reconstructed queue `src/platform/pc_render_queue.cpp:169-179,216-246,288-305`, blob `95e5709c69e22b5bee653786c85b86024e6fc9d1`.
3. Original reconstructed native passes/query `src/platform/pc_render_flush.cpp:174-181,761-801,803-889,970-980,1024-1057,1081-1087`, blob `e6928a316ee4d503910cbe970b26f137e41c158e`; state IDs `src/platform/pc_d3d9_state.hpp:17-23`.
4. Current mod C993/CABE source scopes `src/hooks_graphics.cpp:620-655,707-756,766-836,844-874`, blob `1a8b3acfcf24e2a088b6fb6b7065463abe9be737`. R30 actual L/R eye submission and stereo counters `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5445-5528,5660-5731`, blob `b9a7874c36ae2e0bac48bf2cc395b1e092470a3c`. Protected baseline `0cff83cf509c2acd6f3391b3a46c4dec1403a0d9`; R84 nondefault.

## EVIDENCE_GAPS / FALSIFICATION / NEXT_REVIEW

- EVIDENCE_GAPS=actual lens PMT node.flags and prim.draws[0/1], original pass enable and material/texture/alpha, 570010 query GetData/Draw availability, native passIndex/colour mask/RT/eye and shader c64, source opaque descriptor/4052C0 flush serial, exact HMD pixel placement, host fresh/cached pose/layer. No original EXE byte equivalence or new GPU/HMD measurement.
- FALSIFICATION=For ONE reproducible scene, join `sourceCallSerial+C993/CABE+objID+570008Ordinal+4056D0Admission+405360Descriptor+4052C0Flush+nodeFlags+passIndex+prim.draws+first_draw+material+texture+blend+COLORWRITEENABLE+nativeDrawID+eyeRT+originalC64+eyeWVP+poseEpoch` to `hostFrameID+fresh/cached+sourcePose+xrTick+projectionViewCount+eyeImageHash`. Separate 570010 `4116F0 query` from `4056D0 visible`; never join on object ID alone. Only approved read-only evidence; no B9200 post-CALL/+5 hook.
- EXPECT_DUAL_PASS=0x570008 asset flags both 1/2, both pass draw arrays nonempty and pass1 enabled => one original opaque descriptor may produce two distinct material draw records per eye; if flags exclusive or a pass empty/disabled, reject this mechanism for that asset.
- EXPECT_QUERY=0x570010 query executes with COLORWRITEENABLE=0 and later visible draw occurs => native count can exceed visible colour contributions; if query absent or state changes unexpectedly, log actual gate and state, do not assume.
- EXPECT_TRUE_REPLAY=the SAME `flushID+descriptor+passIndex+primitive+drawRecord+material+sourceSerial` emits repeated colour-writing Draws into the SAME eye RT beyond expected per-eye count; only then B becomes supported.
- NEXT_REVIEW=LENS_FLARE:570008_PMT_NODE_FLAGS_AND_PASS_DRAW_LIST_VS_570010_4116F0_QUERY_COLOR_MASK_NATIVE_EYE_RT_JOIN.

## PATCH_CANDIDATE_ONLY / REGRESSION

- PATCH_CANDIDATE_ONLY=NONE_UNTIL_PHYSICAL_PMT_AND_EYE_RECEIPT. Later human-authorized minimal source/pass read-only correlation would inspect `src/hooks_graphics.cpp::DrawObjectAlphaCentre:779-836`, `::DrawObjectAlphaProjected:707-756` and existing `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30TryScreenSpaceFovDraw:5445-5745`; no source changes in this task.
- REGRESSION=HIGH: suppressing original 570008 ordinal2, 570010 query, pass1 material or RIGHT eye destroys legitimate graphics/visibility; changing global colour masks, c64, alpha, depth, queue order, host layer, R26+HUD or R84 default without exact physical proof is forbidden. B9200 unsafe hook prohibited.
- GITHUB_RECORD=docs/reviews/dx9ex/automation/LENSFLARE-NATIVE-DRAW-MULTIPLICITY-20261027-1815.md; COMMIT_MARKER=[AUTO:LENSFLARE-NATIVE-DRAW-MULTIPLICITY-20261027-1815]; CODE_CHANGE=NO; AUTOMATION_VALIDATION=PENDING_REMOTE_READBACK; RUNTIME_VALIDATION=UNTESTED.
