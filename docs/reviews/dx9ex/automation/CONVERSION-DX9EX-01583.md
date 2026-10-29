# CONVERSION-DX9EX-01583 — R24 cached-quad source provenance: Direct Projection vs mono Theater (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01583
PRODUCTION_ID=CONVERSION-DX9EX-01583
EVENT_ID=CONVERSION-DX9EX-01583-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=707f6cd0321b6d4c534680f90a5cb5a22979f798
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=NONDEFAULT_RESEARCH_ONLY
HUD_COMPARISON=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
AUTOMATION_VALIDATION=PENDING_REMOTE_COMMIT_AND_READBACK
RUNTIME_VALIDATION=UNTESTED

## Question inherited from 01582; independent falsification

User reports a split/doubled centre lens flare and one lobe following the head. These remain user observations, NOT findings reproduced at SOURCE_HEAD. Review 01582 identified a conditional R23 cached **requested** two-eye projection being replaced by an R24 actual `ViewSpace/BOTH/arrayIndex0` quad after verified-bundle eligibility expires. It did not determine **which physical image is in the quad**. This task checks that unproved step and a second, distinct run-identity boundary using actual R24/R19 source. This concerns only CABE 0x570008 / C993 flare pixels in these host images, not other scene defects.

## NEW_FINDING — verified source-static path split, not an HMD/root-cause verdict

NEW_FINDING=R24_CACHED_PROJECTION_QUAD_REQUIRES_VALID_DIRECTGPU_RUN_WHILE_CLASSIC_THEATER_CACHE_CAN_BE_REUSED_WITH_NO_DIRECT_RUN_IDENTITY;_R19_LIVE_THEATER_UV_CROPS_LEFT_SBS_HALF_BEFORE_BOTH_EYE_VIEWSPACE_QUAD;_THEATER_CACHE_IDENTITY_AND_STALE_SOURCE_MUST_BE_SEPARATELY_VERIFIED_BEFORE_ATTRIBUTING_DOUBLE_LOBE.

1. **Projection is not an unconditional cached-stereo fallback.** `vrhost/src/runtime/r24_black_screen_guard.hpp:416-445` first tests `OutRunVrSbsCaptureOverride::Projection`'s handle, extent and two committed-generation guards **AND** `DirectCacheRunMatchesLatest(ProjectionCommittedRun)`. The latter (`:90-111`) requires a valid Direct transport/run-generation/game-PID triple, `DirectTransportRequested()` and an equal complete latest Direct frame. Thus in non-Direct/classic mode that R24 *Projection-as-quad* branch cannot pass even if an earlier R19 projection swapchain exists. This is separate from R23's own `cachedProjectionViews` (the input requested projection in `main_r23.cpp:3732-3823`); identical terminology does NOT establish identical selected swapchain.
2. **Which producer can populate the Direct projection cache?** R24 `RenderSafeProjectionChecked:245-296` renders `SafeEyeSrv[eye]` into `Projection.rtvs[image][eye]`, successfully releases the 2-slice swapchain, then sets `ProjectionCommittedGeneration` (`:282`). `TryBuildDirectSafeProjection:300-330` requires `SourceKind::DirectGpu`, completed frame and SafeEye match before assigning `ProjectionCommittedRun` (`:329`). File-wide pinned source inspection found no other assignments to those two R24 ownership fields beyond reset (`:799-802`). R19's independently rendered classic `Projection` (`sbs_capture_override.hpp:1135-1212`) does not by itself populate these R24 commit/run tokens.
3. **Cached Theater has a deliberately different identity condition.** After the Projection gate, `BuildCachedVisibleQuad:432-444` accepts a committed `Theater` image if `TheaterCommittedDirectRun` is **invalid OR** equals the latest Direct run. `SubmitVisibleFallback:477-575` tries cached before direct-flat, fresh theater, emergency/no layer. When fresh R19 `RenderTheaterOverride` succeeds, R24 `SubmitVisibleFallback:493-499` sets `TheaterCommittedGeneration=Theater.generation` and clears `TheaterCommittedDirectRun={}`; the classic theater cached branch therefore has no current-game-run equality requirement. This is a conditional **same-session stale-source provenance gap**, not proof it happened after a producer restart; swapchain/session reset may invalidate generation (`:789-803`).
4. **Theater is not automatically the raw two-eye SBS image.** R19 `sbs_capture_override.hpp:1374-1435` obtains `GetGameUv(whole)`, then sets `theaterUv=whole; theaterUv.w*=0.5f` and blits **only the first/left SBS half** to `Theater.rtvs[image][0]`. It builds one `ViewSpace`, `XR_EYE_VISIBILITY_BOTH`, array-index-0 quad. R19 `RenderProjectionOverride:1135-1212`, by contrast, separately blits left/right UV halves to two projection slices. This refutes the **general inference** that a successful R19 theater fallback itself stacks both unseparated SBS source eyes side by side in the accepted quad. It can present one already-doubled *left-source* flare flat to both eyes, or preserve one lobe without stereo depth; neither outcome proves source-lobe cardinality or HMD observation.
5. **Other R24 flat paths are also mono-source by code.** `RenderDirectFlatFallback:365-415` checks current Direct SafeEye run, copies only `SafeEyeSrv[0]` to Theater slice 0 and records a Direct run identity; `BuildCachedVisibleQuad` requires that identity to match before reusing it. `BuildEmergencyVisibleQuad:447-477` clears an error-colour target, not a game-flare source. `BuildViewQuad:203-224` always uses `ViewSpace/BOTH/z=-1.5/arrayIndex` supplied by caller, here index 0. The sole fallback quad is one layer, not two lobe producers.
6. **What the logs do and do not authenticate.** `r24_black_screen_guard.hpp:510-573` increments cached/directFlat/liveTheater/emergency counters before `xrEndFrame`; successful final submission records `frameId=0, SourceKind::None, hasLayer=true`, regardless of the underlying Theater/Projection handle or classic versus Direct prior image identity. `main_r23.cpp:4089-4272` has final-kind and R19 receipts but its `XR EYE FULL submittedValid` follows the requested projection. To prove a particular lens lobe came from a cached classic Theater, the real XR tick needs actual fallback-class delta plus committed swapchain handle/generation, Theater source capture QPC/UV, prior source run, and per-eye pre/post ROIs. Counters alone and `submittedValid=1` do not prove those joins.
7. **Bounded counterexamples (static, not actual captured frames).** In *classic* source mode with a previously committed R24 Theater generation and still-live session, but no current verified bundle/classic fallback, R24's Projection cache gate is false; Theater cached branch can be true even if direct-run identity is empty. Its quad displays an older cropped left image to both eyes; no new native flare emitter is needed to make this image head-relative. Conversely, for *DirectGPU* with current matching Projection cache/run the first branch chooses Projection slice0 as flat quad even though its source was built as a binocular 2-slice resource. In neither case can the code alone tell whether the user's visually doubled halo is already present in source eye 0.

## HYPOTHESIS_LEDGER

| ID | Status | Prior evidence / distinct 01583 observation | Falsification |
| --- | --- | --- | --- |
| A — extra original CABE/C993 emitter | OPEN | Source ordinals / centre versus halo already separate; R24 cache/source branch creates no new game emitter | Original call ordinal+actual texture and two same-eye pixel writes beyond intended materials |
| B — original D3DX/PMT queue same-eye resubmit | OPEN | Previous PMT serial not unique post-draw; theater crop is downstream | Source-joined PMT primitive ID, eye RT and same-eye RGB before R19 capture |
| C — native WVP/XYZRHW / zero-depth error | OPEN_RUNTIME | Actual ViewSpace quad can flatten correct native stereo; classic Projection cache gate need not pass | Confirm native wrong per-eye coordinates while final accepted exact stereo projection, not R24 quad |
| D — distinct intended centre/halo materials | OPEN | R19 half-crop does not independently add a CABE material | Texture/blend/pass fingerprints plus lobe ROI on source left-eye pre-host |
| E1 — R24 fallback transforms final lens depth | SUPPORTED_CONDITIONAL_STATIC | 01582 found ViewSpace quad; 01583 separates Direct Projection slice0 vs cropped Theater slice0 from source predicates | On symptomatic tick, fresh accepted binocular projection with no fallback counters |
| E2 — raw *whole SBS* theater caused two side-by-side lobes | REFUTED_FOR_SUCCESSFUL_R19_THEATER_RENDER_PATH | Actual `RenderTheaterOverride` halves game UV width before its one-eye mono quad | A different accepted path/UV or exact source image showing both original eye halves inside Theater slice0 |
| E3 — cached classic Theater reuses stale pre-run lens image | OPEN_CONDITIONAL | R24 classic-invalid run token bypasses run match while generations remain equal; source may be old | On same-session producer run change, prove cache invalidates before subsequent quad, or no cached-classic fallback occurs |
| F — source bearing/HMD-local mismatch | OPEN_RUNTIME | Flat Theater intentionally head-relative; not proof of original sun bearing error | Two yaw pose and source sun/flare ROI with final accepted layer identity |
| G — observed doubled lobe cause | BLOCKED | No source-matched draw→ROI→R24 actual swapchain→Quest3 frame at pinned SHA | Full same-tick source/host and HMD two-yaw record |

## SOURCE_TRACE / provenance

- GITHUB_PINNED_SOURCE_HEAD=`707f6cd0321b6d4c534680f90a5cb5a22979f798` on `vr-d3d9ex-focus`; AGENTS.md most recent 2026-10-20 R26+HUD override and `docs/DX9EX_OPTICAL_ROUTE_PROBE_POLICY_20261020.md` read. Comparison documentation: `docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01579.md`, `01580.md`, `01581.md`, `01582.md`.
- R24 exact function/lines: `vrhost/src/runtime/r24_black_screen_guard.hpp` blob `34d1234ab50f15c39451c39bdb9182f44d62e91c` — `DirectCacheRunMatchesLatest:90-111`, `BuildViewQuad:203-224`, `RenderSafeProjectionChecked:245-296`, `TryBuildDirectSafeProjection:300-330`, `RenderDirectFlatFallback:365-415`, `BuildCachedVisibleQuad:416-445`, `BuildEmergencyVisibleQuad:447-477`, `SubmitVisibleFallback:477-575`, `EndFrame:625-777`, `DestroySession:789-803`.
- R19 exact function/lines: `vrhost/src/runtime/sbs_capture_override.hpp` blob `9ecf3658c260d3a230c788bd69e0a118bc40abb9` — `PublishProductionCapture:538-590`, `GetGameUv:695-805`, `RenderProjectionOverride:1135-1212`, `RenderTheaterOverride:1374-1435`, `EndFrame:1468-1540`. R23 `vrhost/src/main_r23.cpp:3732-3823,4089-4272` plus `runtime/r23_verified_bundle.hpp:113-135` give requested-eye versus final/source eligibility distinction.
- EVIDENCE_SOURCE=CONNECTED_GITHUB_CURRENT_PINNED_STATIC; EVIDENCE_DISASM=NONE_NEW_PREDECESSOR_ONLY; EVIDENCE_LOG=NO_CURRENT_SHA_LENS_CAPTURE; EVIDENCE_USER_REPORT=CENTER_LENS_SPLIT_AND_HEAD_FOLLOW; EVIDENCE_HMD=NONE.
- EVIDENCE_GAPS=Actual current source texture/PMT ordinal/left source ROI not authenticated; no R24 per-tick selected cache handle/source generation/UV/run record, no actual classic-vs-direct branch incidence, no accepted XR quad image content, and no two-yaw Quest3/VDXR record. Normal left+right eye draws remain expected. Source predicate != observed pixel and no true lens cause is yet fixed.

## NEXT_FALSIFICATION_TEST — optical branch signature, not implemented here

1. With a **separately authorized** bounded optical trace, join the exact CABE 0x570008 or centre C993 source ordinal, PMT/texture/pass/primitive, native eye RT colour ROI+frame, transport mode and game PID/run generation, R19 `whole` + `theaterUv` + source capture QPC, R24 cached `Projection/Theater` handle+generation+run-id+array index, R24 final fallback class/submit result, R23 requested-vs-final receipt, and actual Quest3 pose/eye ROI at two yaw positions. Missing proof => UNKNOWN.
2. **Classic theater positive control:** `DirectTransportRequested=0`, Projection cache selection must fail; when R24 live theater succeeds, `theaterUv.w=whole.w/2`, one actual quad with BOTH visibility and slice0. After no source for >1000ms but generation unchanged, a cached Theater can be reused; expected head-relative flat *left source* and no fresh native lens draw. If actual Theater contains two source-eye halves, falsify UV/capture assumptions with measured RGB/UV and exact executed branch.
3. **Direct projection positive control:** fresh matching Direct run and committed Projection => first cached branch can select Projection slice0; require `SafeEye[0]/[1]` provenance and parent `xrEndFrame` result. Both-eye output of slice0 is flat without inventing an extra CABE emitter.
4. **Run-change negative control:** change game producer PID/run in same XR session *in a future authorized test*, hold old Theater cached generation (not programmatically forced by this job), record whether the actual guard uses cached classic Theater before explicit session/capture invalidation. If cache is invalidated upstream first, refute E3 as an observable route. A mere stale handle/gen equality is insufficient for acceptance/pixels proof.
5. **Optical cardinality:** two lobes in captured source eye0 already => A/B/D before host; one source-eye0 lobe but two lobes after actual fresh accepted projection => C/F or other host processing; one lobe but head-relative both eyes only during final Theater/Projection quad => E1, not A. Compare source textures and alpha at the physical draw, not nominal PMT count.

NEXT_FALSIFICATION_TEST=JOIN_R24_CACHED_CLASSIC_THEATER_RUN_IDENTITY_AND_R19_LEFT_HALF_UV_TO_570008_SOURCE_EYE0_ROI_ON_EXACT_ACCEPTED_XR_TICK
PATCH_CANDIDATE_ONLY=DIAGNOSTIC_PROPOSAL_NOT_APPLIED: `vrhost/src/runtime/r24_black_screen_guard.hpp:416-445,477-575` record selected cache family, actual swapchain handle/generation, saved source capture QPC/producer run, and accepted XR result per bounded lens frame; `vrhost/src/runtime/sbs_capture_override.hpp:1374-1435` correlate whole vs left-half theater UV and frame QPC. If same-session stale classic theater is physically demonstrated, only then consider a current-run ownership guard for cached classic Theater. No code change authorized or performed; do NOT change render routing, HMD fallback availability or established lens layers from this static result alone.
REGRESSION_RISK=DOCS_ONLY_NONE; future diagnostic/repair risks losing visible last-known image on producer stalls, DirectGPU run-protection, normal stereo eye pairs, menu/theater aspect and performance. Preserve B9200 prohibition, R26+HUD immutable baseline and R84 nondefault; exact Quest3 two-yaw validation needed.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:R24_CLASSIC_THEATER_INVALID_RUN_TOKEN_VS_SAME_SESSION_STALE_570008_LEFT_EYE_CAPTURE_QPC
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01583.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01583]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01583.md
