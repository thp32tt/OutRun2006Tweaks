# CONVERSION-DX9EX-01584 — R24 classic-Theater cache-first refresh starvation (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01584
PRODUCTION_ID=CONVERSION-DX9EX-01584
EVENT_ID=CONVERSION-DX9EX-01584-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=c52f3f4f9da1d03479b2f62855ffe266a1a0864f
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=NONDEFAULT_RESEARCH_ONLY
HUD_COMPARISON=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
CODE_CHANGE=NO
AUTOMATION_VALIDATION=REQUIRES_REMOTE_DOCS_ONLY_COMMIT_READBACK
RUNTIME_VALIDATION=UNTESTED

## Question / separation from predecessor

The user's split/doubled and partially head-following lens flare is a **reported HMD symptom**, not a reproduction at this SHA. CONVERSION-DX9EX-01583 distinguished R24 Direct projection cache from classic mono Theater cache and left classic-Theater stale *producer-run* provenance open. This review tests an **independent same-run temporal mechanism**: once a classic Theater image is cached, does a newer R19 production capture cause the R24 fallback to refresh that image? The inspected scope is CABE 0x570008 / central C993 lens pixels **only** as a potential constituent of those images. No unrelated 2D, sky, performance or HUD issue is evaluated.

## NEW_FINDING — conditional, source-static refresh-starvation boundary

NEW_FINDING=R24_CLASSIC_THEATER_CACHE_FIRST_BYPASSES_R19_RENDER_THEATER_ON_SUBSEQUENT_VISIBLE_FALLBACKS_EVEN_WHEN_R19_SOURCE_IS_NEWLY_PUBLISHED;_R19_500MS_CAPTURE_FRESHNESS_DOES_NOT_RECHECK_CACHED_THEATER_PIXELS;_SAME_RUN_STALE_LENS_IMAGE_IS_CONDITIONALLY_POSSIBLE_WITHOUT_PRODUCER_RESTART_OR_EXTRA_GAME_DRAW.

1. **A current producer capture is a distinct object from the already rendered Theater swapchain.** R19 `PublishProductionCapture` copies a new `productionSource` to `Source` and advances `LastProductionPresentQpc`, `LastProductionPublishMs`, `ProductionPublishes`, `CaptureFresh` (`sbs_capture_override.hpp:538-590`). That method does **not** overwrite `Theater.rtvs[image][0]`, `Theater.committedGeneration` or R24's `TheaterCommittedGeneration`. Fresh game/desktop lens pixels in Source therefore do not establish that the HMD-visible Theater image changed.
2. **The R19 freshness guard protects new blits, not re-submission of a committed old swapchain.** R19 `PublishedSourceMaxAgeMs=500` (:49); `CaptureDesktop:589-606` rejects a published Source older than 500ms; `RenderTheaterOverride:1374-1410` checks that predicate, chooses `GetGameUv(whole)`, halves the UV width and renders left-source pixels into Theater. However, R24 `BuildCachedVisibleQuad:416-445` checks only swapchain handle, extent, generation/commit equality and an invalid-or-matching Direct run token for cached Theater. It does not call `CaptureDesktop`, compare `LastProductionPresentQpc`, inspect `LastProductionPublishMs`, or require a new source frame.
3. **The cache short-circuits the only live Theater refresh call on the R24 visible-fallback path.** `SubmitVisibleFallback:479-503` evaluates `cached=BuildCachedVisibleQuad` first, then `directFlat=!cached && RenderDirectFlatFallback`, then `live=!cached && !directFlat && RenderTheaterOverride`. After the first successful live theater fallback, R24 stores `TheaterCommittedGeneration=Theater.generation` and `TheaterCommittedDirectRun={}` (:493-499). For a later visible-fallback invocation with unchanged valid Theater generation, `BuildCachedVisibleQuad` returns true and **does not execute** `RenderTheaterOverride`, regardless of whether R19 has a newer source QPC. It increments `CachedLayerFallbacks`, not `LiveTheaterFallbacks` (:526-556), and submits a single `ViewSpace/BOTH/arrayIndex0` quad, not a fresh binocular projection.
4. **Even a producer-identity cache reset does not itself reset this Theater image.** R19 `UpdateStereoFrameCache:1046-1073` calls `InvalidateStereoFrameCache` when Frame.v2 run/PID changes or becomes invalid; `InvalidateStereoFrameCache:405-410` clears only `LastStereoFrame`, its valid bit and timestamp, **not** Theater handle/generation/RTV. R24's cached-classic predicate tolerates `!TheaterCommittedDirectRun.Valid()`, which is deliberately set on live Theater commit. Session destruction or swapchain invalidation is a separate boundary: R19 `DestroySession:1545-1575` forgets Theater after successful parent teardown and R24 `DestroySession:780-803` clears its commit/run tokens only after successful downstream teardown. Consequently, a same-session *same-run* gap can keep displaying older lens pixels with no game restart; this is a conditional control-flow property, **not proof** that any actual headset frame did so.
5. **Scope of inference and negative control.** `EndFrame:625-777` can bypass `SubmitVisibleFallback` via validated classic/Direct projection, an exact/grace source, intentional menu mono or fresh classic fallback, and sessions/resources can reset. The finding applies **only** on repeated R24 visible-fallback calls when cached Theater is the selected reusable image. A fresh matching two-eye accepted projection on the user-symptomatic tick falsifies this *route* as the explanation for that tick. A single old left-eye source shown as a head-relative quad can explain apparent absent depth/head-lock, **not** manufacture a second CABE/C993 source emitter or establish why two distinct flare lobes were reported. Two legitimate L/R native draws are not duplication evidence.

### Stepwise falsification matrix (conditional control-flow predictions, NOT executed runtime tests)

| Frame/conditions | Expected branch and receipts | Expected lens image inference | What would refute |
| --- | --- | --- | --- |
| T0: no accepted exact/grace/fresh classic projection; no cached image; R19 Source A age <=500ms; live theater succeeds | `LiveTheaterFallbacks +1`; `TheaterCommittedGeneration` set; final `SourceKind::None/frameId=0/layer=1` | A's **left** SBS half mapped as flat BOTH quad | Evidence R19 Theatre was not executed, or a different accepted layer |
| T1: still same XR session/valid theater generation; R19 Source B newly published with different present QPC; visible fallback again | `CachedLayerFallbacks +1`; `LiveTheaterFallbacks +0`; R19 `RenderTheaterOverride` not called; same cached Theater handle/gen | Old A pixels remain eligible even though Source B contains new flare; a static head-relative lens lobe is possible | Actual new Theater swapchain content generation/RTV write and same-tick accepted image, or cached selection false |
| T2: same Theater valid, Source older than 500ms, visible fallback continues | Cached branch can still succeed despite R19 `CaptureDesktop` being stale; final one mono ViewSpace quad | Cached frame can persist without refreshed native flare pixels | R24 age guard or proactive cache invalidation actually runs on the submitted path |
| T3: successful parent XR session destruction / Theater destroy-recreate | R19 Theater handle/committed generation cleared; R24 commit token cleared after successful downstream DestroySession | Prior cached Theater no longer passes same-generation predicate | Evidence exact same stale handle/gen is still accepted after successful reset |
| N1: fresh verified ClassicSbs two-eye projection matches source/pose | R24 accepted exact projection, no R24 visible fallback | Host cache-first route is not applicable; original native eye WVP/producer and host final submission need direct study | Any same-tick proof of R24 fallback replacing that accepted exact layer |

## HYPOTHESIS_LEDGER

| ID | State | Prior evidence versus this task's distinct verification | Falsifier |
| --- | --- | --- | --- |
| A — duplicate original CABE 0x570008/C993 emitter | OPEN | Prior source ordinals/texture families remain unjoined; repeated R24 Theater quad needs no new game emission | Same-eye source ROI and exact PMT/object/texture/ordinal prove additional native emitter |
| B — original D3DX/queue/native duplicate same-eye draw | OPEN | R24 cached quad is post-draw and does not establish an extra game Draw | Real same-eye RT pre-host RGB and Draw ID/HRESULT/queue epoch on one physical frame |
| C — native L/R WVP or flat XYZRHW depth | OPEN_RUNTIME | R24 can erase earlier native disparity *downstream*; does not prove incorrect game WVP | Head-lock during exact fresh accepted stereo projection with authenticated native L/R geometry |
| D — separate centre/halo/rays materials | OPEN | A cached quad preserves existing source content and cannot classify flare texture count | Actual texture/alpha/material/ROI fingerprint before R19 capture |
| E1 — R24 ViewSpace/BOTH flat presentation | SUPPORTED_CONDITIONAL_STATIC_PREVIOUS | Inherited R24 quad mechanics; not credited again | Exact accepted two-eye lens projection on symptomatic tick |
| E2 — successful R19 Theater displays raw whole SBS | REFUTED_FOR_R19_THEATER_PATH_PREVIOUS | R19 halves `whole.w`; rechecked, not novel | Physical source UV/RTV indicating both uncut halves in selected Theater quad |
| E3 — old classic Theater after game run restart | OPEN_CONDITIONAL | Inherited invalid-run-token issue; run-change invalidates R19 frame cache but not Theater; no actual restarted-game trace | Explicit Theater invalidation before any post-restart cached fallback on same XR session |
| E4 — new R19 capture automatically refreshes a cached classic Theater | REFUTED_CONDITIONALLY_STATIC_NEW | Verified `cached` branch precedes `live`; new Source/PresentQpc does not change committed Theater pixels, and `!cached` blocks live draw | A code path writing newly published B pixels to same accepted Theater RTV despite `cached=true`, or no repeated visible-fallback branch |
| F — world sun bearing / HMD-local error | OPEN_RUNTIME | Flat ViewSpace quad is head-relative; lens original bearing remains unproved | Pose-matched two-yaw exact binocular source and final layer ROI |
| G — user's doubled lens lobe physically due to cache-first starvation | BLOCKED | This mechanism predicts stale/head-relative image, **not** two genuine source lobes; no matched HMD frame | Observe two-source ROI per-eye and exact accepted fresh projection, or show cache not taken during split |

## SOURCE_TRACE

- SOURCE_HEAD `c52f3f4f9da1d03479b2f62855ffe266a1a0864f` pinned from connected GitHub `vr-d3d9ex-focus`; inspected `AGENTS.md`, `docs/DX9EX_OPTICAL_ROUTE_PROBE_POLICY_20261020.md`, prior `CONVERSION-DX9EX-01582.md`, `01583.md`, and `LENSFLARE-DEFERRED-PROMOTION-ADMISSION-GATE-20261030-0216.md`.
- `vrhost/src/runtime/sbs_capture_override.hpp` blob `9ecf3658c260d3a230c788bd69e0a118bc40abb9`: `PublishedSourceMaxAgeMs:49`, `Swapchain::ForgetAfterParentSessionDestroy/Destroy:234-361`, `InvalidateStereoFrameCache:405-410`, `PublishProductionCapture:538-590`, `CaptureDesktop:593-606`, `EnsureSwapchain:825-909`, `Release:1005-1033`, `UpdateStereoFrameCache:1046-1073`, `PublishedSourceMatches:1075-1120`, `RenderTheaterOverride:1374-1437`, `DestroySession:1545-1575`.
- `vrhost/src/runtime/r24_black_screen_guard.hpp` blob `34d1234ab50f15c39451c39bdb9182f44d62e91c`: `DirectCacheRunMatchesLatest:97-111`, `BuildViewQuad:203-224`, `BuildCachedVisibleQuad:416-445`, `SubmitVisibleFallback:479-575`, `EndFrame:625-777`, `DestroySession:780-803`.
- The source-to-flare chain remains *partially inherited only*: original CABE 0x570008 / C993 -> sprite/PMT/texture/queue -> native L/R eye -> source capture -> R19 `Source` -> optional Theater left-half blit -> R24 one ViewSpace quad -> `xrEndFrame` -> Quest3. This review freshly verifies **R19 Source-to-Theater-to-R24 fallback temporal gate** only. It does not newly authenticate original EXE/REA bytes, actual D3DX/native draw, Quest3 pixels or per-eye OpenXR runtime submission.
- EVIDENCE_SOURCE=CONNECTED_GITHUB_SHA_PINNED_STATIC; EVIDENCE_DISASM=PREDECESSOR_ONLY_NOT_REEXECUTED; EVIDENCE_LOG=NO_EXACT_SHA_PER_TICK_FLARE_TRACE; EVIDENCE_USER_REPORT=SPLIT_LENS_AND_ONE_HEAD_FOLLOWING_LOBE; EVIDENCE_HMD=NONE_THIS_TASK.

## EVIDENCE_GAPS / NEXT_FALSIFICATION_TEST

EVIDENCE_GAPS=No exact CABE/C993 primitive/PMT+texture+L/R RGB; R19 source `presentQpc` and texture generation are not joined to the accepted Theater swapchain image timestamp/handle/index; R24 cached family is not exposed per tick by a distinct final receipt; no same-session T0/T1/T2 fallback sequence from live logs; no post-`xrEndFrame` accepted layer identity joined with Quest3 two-yaw pose/ROI. `LiveTheaterFallbacks`/`CachedLayerFallbacks` alone are insufficient to infer specific flare pixels, and static path reachability does not prove user symptom incidence.

NEXT_FALSIFICATION_TEST=For one authenticated same-run CABE/C993 source frame and two subsequent XR ticks, observe `ProductionPublishes`, `LastProductionPresentQpc`, `LastProductionPublishMs`, source lobe ROI, R19 `TheaterAttempts/Success`, Theater `handle/generation/committedGeneration` and actual RTV last-write QPC, R24 `TheaterCommittedGeneration`, `TheaterCommittedDirectRun.Valid()`, `cached` vs `live` selection and final `xrEndFrame` layer/swapchain/arrayIndex, plus two HMD yaw/eye ROIs. Positive control: persistent R24 visible fallback, Source QPC B>A, unchanged Theater generation, no Theater RTV write after A -> cached A. Negative control: accepted fresh exact ClassicSbs L/R projection -> this cause absent. A fresh same-swapchain physical Theater write during `cached=true` or upstream generation invalidation before fallback refutes the predicted path. Independently test original eye0 lobe cardinality: two lobes before host -> A/B/D rather than this mechanism.

PATCH_CANDIDATE_ONLY=NOT_APPLIED_DIAGNOSTIC_FIRST: `vrhost/src/runtime/r24_black_screen_guard.hpp:416-445,479-575` could *in a separately authorized future change* emit bounded per-tick selected cache family, valid generation, accepted image handle/index and last-writing source capture QPC; `vrhost/src/runtime/sbs_capture_override.hpp:538-590,1374-1437` could correlate Source publication QPC to the actual Theater RTV write and distinguish fresh/cached source. Only if a same-run stale-image freeze is physically demonstrated should a narrowly scoped cache refresh/age policy be considered. Do not implement or weaken fallback protections now; preserve safe cached visibility if fresh source absent, normal L/R native stereo draws and R26+HUD baseline.
REGRESSION_RISK=DOCS_ONLY_NONE; future cache refresh may reintroduce black frames on capture gaps, GPU lifetime/Acquire-Release hazards, extra D3D11 work, incorrect display of two raw SBS halves, menu/theater aspect changes and false stereo-depth assumptions. Any future modification requires Quest3/VDXR same-source two-yaw regression; R84 remains nondefault and B9200 post-CALL/+5 is forbidden.
CODE_CHANGE=NO
NEW_FINDING_STATUS=STATIC_CONDITIONAL_NOT_HMD_ROOT_CAUSE
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:R24_CACHED_THEATER_T0_T1_SOURCE_QPC_ADVANCE_VS_THEATER_RTV_LAST_WRITE_AND_ACTUAL_XR_LAYER
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01584.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01584]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01584.md
