# CONVERSION-DX9EX-01582 — R23 cached lens projection versus R24 ViewSpace quad final-eye authority (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01582
PRODUCTION_ID=CONVERSION-DX9EX-01582
EVENT_ID=CONVERSION-DX9EX-01582-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=27ecf6cd14f287936c2911b6345431c1467cb03e
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
REVIEW_SCOPE=LENS_FLARE_ONLY
DX9EX_REVIEW_ONLY=ON
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=NONDEFAULT_COMPARISON_ONLY
HUD_COMPARISON=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
RUNTIME_VALIDATION=UNTESTED
AUTOMATION_VALIDATION=PENDING_DOCS_ONLY_REMOTE_READBACK

## Question and inherited hypotheses

User symptom: a central lens flare/halo seems doubled, lacks stereo depth or follows the head. This is a user observation, NOT a reproduced optical verdict on SOURCE_HEAD. Prior 01577-01580 limit PMT pass/primitive/log authority; 01581 refutes R7 SINGLE `leftAttempted` as a general proof of published left-eye pixels; 2026-10-30 R13 forced-mono negative control proves an original native draw can bypass R7 entirely. None establish whether a CABE 0x570008 or C993 flare reached the headset. This review tests a distinct, *downstream* fork: can R23's cached two-eye *requested* projection coexist with an R24 *actual* view-space, both-eye single-slice quad after host bundle expiry? Does the existing `XR EYE FULL submittedValid` log prove the final lens projection in that circumstance?

## NEW_FINDING — conditional host optical-depth discriminator

NEW_FINDING=STATIC_CONDITIONAL_R23_CACHED_TWO_EYE_REQUEST_CAN_BE_REPLACED_BY_R24_VIEWSPACE_BOTH_EYES_ARRAY_SLICE0_QUAD_AFTER_VERIFIED_BUNDLE_EXPIRY;_R23_XR_EYE_FULL_SUBMITTEDVALID_IS_REQUESTED_EYE_METADATA_NOT_A_POST_R24_ACCEPTED_PROJECTION_PROOF.

1. `vrhost/src/main_r23.cpp:3732-3755,3812-3823`: during gameplay, `cachedHold = cachedProjectionValid`; if no fresh stereo source commits, the host does not age out its own cached projection image. The cached branch sets `projection.space=localSpace`, `projection.viewCount=2`, `projection.views=cachedProjectionViews.data()`, `finalLayerKind="projection-cached"`, `frameCachedProjection=true`. A repeated OpenXR tick alone does *not* mean another game emitter, native lens draw or new two-eye GPU blit.
2. `vrhost/src/runtime/r23_verified_bundle.hpp:14-15,113-135`: independent committed-source eligibility is time bounded: `MaxPresentationAgeMs=1000` and `ReadFresh` needs current run and valid source/pose/frame. `vrhost/src/runtime/r24_black_screen_guard.hpp:38-43,154-169,711-777`: R24 first seeks a fresh exact bundle, then a bounded display-only grace snapshot (same 1000-ms age ceiling), then a fresh classic fallback; otherwise it invokes `SubmitVisibleFallback`. Therefore a continuing gameplay R23 cached *request* and expired R24 *submission authority* can coexist after >1000 ms without a new verified bundle, provided no other valid source/grace path intervenes.
3. `r24_black_screen_guard.hpp:416-445,479-573`: `BuildCachedVisibleQuad` preferentially uses a previously committed `Projection.handle` (or a committed theater image) and calls `BuildViewQuad(...,arrayIndex=0,quad)`; later success creates exactly **one** quad layer via `patched.layerCount=1`, not two projection layers. If no reusable image is safe it may instead render another flat fallback or submit no layer. This is a conditional source branch, not observed CABE/C993 incidence.
4. `r24_black_screen_guard.hpp:203-224`: the **actual cached quad** is `quad.space=ViewSpace`, `quad.eyeVisibility=XR_EYE_VISIBILITY_BOTH`, `quad.subImage.imageArrayIndex=0`, `quad.pose.position.z=-1.5f`, with one rectangular image presented to both eyes. This is intentionally head-relative **flat** presentation and cannot preserve the native L/R lens disparity encoded in separate projection eye views. It can *mimic* a head-follow/zero-depth flare during fallback without creating a second game flare emitter. It does NOT prove that the user's doubled lobe occurred during this fallback or that the source image already contained one/two lobes.
5. `vrhost/src/main_r23.cpp:4089-4117,4140-4193,4206-4272`: the code calls intercepted `xrEndFrame` (R24 wrapper), reads `actualFinalLayerKind`, `actualSubmittedFrameId`, `actualSubmittedSourceKind`, `actualSubmittedLayer` and R19 receipt, **but** the separate `VR TRACE XR EYE FULL` block calculates `submittedValid`, `submittedSource=CACHED`, submitted pose/FOV/arrayIndex from the local `frameCachedProjection` and `cachedProjectionViews` flags, not from the post-R24 final layer. It can therefore log two nominal cached projection eyes when R24 actually sent a single head-relative quad (or no layer). `submittedValid=1` in this line is NOT post-`xrEndFrame` proof of accepted binocular lens pixels.
6. `vrhost/src/runtime/r24_black_screen_guard.hpp:525-573` records fallback through `RecordFinalSubmissionResult(result,0,SourceKind::None,true)` after submitting the quad; `vrhost/src/runtime/r23_runtime_hardening.hpp:44-75` owns that post-final frame/kind/layer receipt. `r24_black_screen_guard.hpp:625-777` explicitly decides final submission; R19 `sbs_capture_override.hpp:1462-1525` can also replace inputs in its separate classic path. R19 PRE/POST and XR result must not be treated as identical to R23's requested eye metadata. A successful `xrEndFrame` alone does not attest the user's perceived double image.

**Falsification boundary:** if the accepted final kind for the actual lens frame remains a fresh, source-pose-matched projection and R24 fallback counters do not advance, the specific ViewSpace-quad hypothesis is false for that frame. If R24 flat fallback occurs, it explains possible loss of lens stereo/depth at that moment, not an extra native emitter or automatically the observed two visible lobes. Normal two native eye draws remain expected.

## HYPOTHESIS_LEDGER

| ID | State | Previous evidence / this distinct test | Falsifier |
| --- | --- | --- | --- |
| A extra original CABE/C993 lens emitter | OPEN | Two original 0x570008 source ordinals and PMT pass fan-out; this host branch requires no new emitter | Authenticate source ordinal+texture+same-eye RGB with an unplanned third emitted flare |
| B original queue/D3DX/native duplicate | OPEN | R7/R13 physical receipt gaps persist; cached XR submissions add zero native producer draws | Exact draw/RT/texture/pass plus same-eye pixel ROI before host |
| C bad native stereo WVP/XYZRHW | OPEN_RUNTIME | R24 flat fallback can erase prior eye disparity *after* native stereo | Native L/R eye ROIs/geometry bad even with final fresh accepted stereo projection |
| D distinct intentional flare halo/material passes | OPEN | R24 one quad does not distinguish original two materials | Authenticate original texture/alpha and corresponding same-eye ROI |
| E host layer/composite reuse | SUPPORTED_CONDITIONAL_STATIC | R23 cached requested two-eye projection can be replaced by R24 ViewSpace BOTH slice0 quad after source bundle age expiry | For symptomatic frames, show actual R24 exact valid projection (not fallback), R19 projection receipt, fresh source IDs and correct L/R accepted eye |
| F source/HMD-local bearing mismatch | OPEN_RUNTIME | R24 ViewSpace flat image is intentionally head relative; could mimic head-lock while source geometry was binocular | Two-yaw HMD records where flare head-lock persists in accepted fresh stereo projections |
| G `VR TRACE XR EYE FULL submittedValid=1` proves actual final L/R projection | REFUTED_AS_GENERAL_LOG_INFERENCE | Eye log uses pre-intercept `frameCachedProjection`, while R24 can send quad/no-layer; actualFinal receipt is separately recorded | Only a final layer-type-aware joined receipt can validate this inference for a particular frame |
| H observed doubled lobe root cause | BLOCKED | No exact game PMT→R24 actual final layer→pixel ROI→Quest3 optical trace | One exact-source two-yaw frame with all joins, including zero/flat negative controls |

## SOURCE_TRACE and provenance

- Pinned GitHub source: `27ecf6cd14f287936c2911b6345431c1467cb03e`; AGENTS.md newest 2026-10-20 R26+HUD override, and docs/DX9EX_OPTICAL_ROUTE_PROBE_POLICY_20261020.md supersession read.
- Game upstream (separate existing evidence rechecked): `src/vr/d3d9/stereo_renderer_r13.cpp:467-505,595-652` actual native mono-shadow; `src/vr/d3d9/stereo_renderer.cpp:403-416,765-865` potential mono restoration/final PublishRenderFrame; `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6890-6970` successful native-eye attempt/RT receipt, still not pixel proof. Lens identity from 01580/01581 previous notes, not reauthenticated by EXE bytes in this task.
- Host source new independent fork: `vrhost/src/main_r23.cpp:3087-3091,3732-3823,4089-4272`, `vrhost/src/runtime/r23_verified_bundle.hpp:14-15,113-135`, `vrhost/src/runtime/r24_black_screen_guard.hpp:38-43,154-169,203-224,416-445,479-573,625-777`, `vrhost/src/runtime/r23_runtime_hardening.hpp:44-75`, `vrhost/src/runtime/sbs_capture_override.hpp:1462-1525`.
- EVIDENCE_SOURCE=GITHUB_STATIC_PINNED; EVIDENCE_DISASM=PREDECESSOR_ONLY_NOT_REVALIDATED; EVIDENCE_LOG=NONE_FOR_CURRENT_SHA; EVIDENCE_USER_REPORT=DOUBLED_AND_HEAD_FOLLOW_LENS; EVIDENCE_HMD=NONE.
- EVIDENCE_GAPS=No authenticated 0x570008/C993 physical draw-to-frame ID and native L/R ROI, no actual expired-bundle or R24 cached-flat incidence from Quest3, no post-final accepted projection-vs-quad log joined to the specific flare pixels, no two-yaw capture. Compile-time inclusion is not runtime reachability; conditional negative control is not symptom confirmation.

## NEXT_FALSIFICATION_TEST — exact predicted branches

1. For one user-visible central lens lobe, correlate game `pmtEntrySerial/objectId/pass/texture`, R30/R7/R13 native `eye/RT/HRESULT/pixelROI`, `VR TRACE FRAME PUBLISH FULL pendingFrameId,pendingPose`, host `[VR TRACE XR FRAME FULL] requestedLayer,actualFinal,actualFrameId,actualSourceKind,actualLayer,r19ReceiptSerial,r19Replaced,r19Projection,r19FrameId`, `[VR TRACE XR EYE FULL] submittedSource,sourceFrameId,sourcePoseSequence,submittedPos/Fov`, and R24 final fallback counters on **same XR tick**. Collect actual headset image/pose at two yaw angles; frame ID must match; missing records mean unknown.
2. **Fresh control:** R23 `projection-fresh`, R24 exact accepted projection, actualFrameId=matching source, two different source eye slices and optical disparity appropriate to depth; `VR TRACE XR EYE` is a compatible *candidate* receipt only. If user still sees head-lock in this branch, eliminate the R24 cached flat hypothesis and test C/F against source bearing.
3. **Cached valid control:** R23 `projection-cached`, R24 accepted exact/grace projection while within bundle age; no new game native draw on each XR tick; two views remain. This is not a second flare.
4. **Expired bundle falsifier:** keep gameplay + `cachedProjectionValid=1` + no newly committed stereo bundle for >1000 ms (not a proposed source modification). R23 can request `projection-cached`, but R24 exact/grace fail; if classic fallback unavailable, expect `actualFinal=fallback-cached-image` or another flat fallback with `actualFrameId=0,actualSourceKind=None` (or `actualLayer=0` if no source). A `VR TRACE XR EYE FULL submittedValid=1,submittedSource=CACHED` **alongside a non-projection actual final** is the key false-positive control. The quad uses `ViewSpace/BOTH/arrayIndex0`; a flare inside its sampled flat image cannot provide per-eye depth.
5. **Opposing cause:** two lobe RGB writes already in the same game eye before host => A/B/D; two lobes only in final HMD while R24 actual fresh per-eye projection => inspect C/F and source-to-host scaling; flat-fallback-only depth loss => E conditional. A blank/emergency fallback cannot substantiate an optical-flare observation.

NEXT_FALSIFICATION_TEST=JOIN_R23_REQUESTED_CACHED_EYES_TO_R24_ACTUAL_FINAL_QUAD_VS_PROJECTION_FOR_AUTHENTICATED_CABE_570008_TWO_YAW

PATCH_CANDIDATE_ONLY=DIAGNOSTIC_PROPOSAL_NOT_APPLIED: `vrhost/src/main_r23.cpp:4089-4272` (label `XR EYE FULL` as REQUESTED_OR_CACHED_EYE, print actual post-final layer type and R24 fallback family, never infer acceptance from its `submittedValid`); `vrhost/src/runtime/r24_black_screen_guard.hpp:203-224,416-445,479-573,625-777` (bounded final `Projection/Quad/None` receipt with single-slice identity only after successful xrEndFrame). Requires separate authorization; do not modify renderer, hooks, source producer, R19/R24, R26+HUD package or test launchers now.
REGRESSION_RISK=DOCS_ONLY_NONE; any later diagnostic source change must preserve one true fallback quad for BOTH eyes, legitimate normal 2-eye stereo draws, final XrResult ownership, no B9200 post-CALL/+5, stable host timing and protected R26+HUD fallback.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:R24_VIEWSPACE_BOTH_EYES_ARRAY0_FALLBACK_VS_CABE_570008_PIXEL_AND_ACCEPTED_XR_TICK
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01582.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01582]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01582.md
