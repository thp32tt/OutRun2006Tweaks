# CONVERSION-DX9EX-01586 — CABE deferred-lens PMT → R30 rejection → R29 evidence coverage audit (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01586
PRODUCTION_ID=CONVERSION-DX9EX-01586
EVENT_ID=CONVERSION-DX9EX-01586-E001
EVENT_TYPE=dispatch
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=da0d6dc17f563d0d8c57f8602ac8b3cc351a6f4b
SOURCE_SSOT=CONNECTED_GITHUB_PINNED
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
RUNTIME_VALIDATION=UNTESTED
NEW_FINDING=NONE

## Narrow question / distinction from 01585 and earlier records

The user reports a split/doubled, apparently head-following sun lens flare. This is a **user observation**, not a reproduction on SOURCE_HEAD. The immediate predecessor 01585 compared CABE/C993 source wrapper lifetime and native projected versus SceneEffect/PerspectiveHud routes. 01577 and 01578 **already** identified that the R30 dedicated `VR TRACE LENS PHYSICAL RESULT FULL` is scope-gated independently of PMT. Hence this review does **not** recycle that limitation as an independent discovery or new score.

This task instead checks the **post-rejection observability contract** for the still-open CABE ordinal1 opaque 4052C0 hypothesis: given an intercepted PMT, which precise downstream receipts can distinguish (i) successful admitted R30 stereo, (ii) a rejected R30 branch executing R29 lower, and (iii) a non-exact deferred window? Does the absence of the lens-specific R30 log allow a verdict on the second halo? This is a source-static evidence-coverage test, not a render change.

## SOURCE_TRACE — exact inspected boundaries at pinned HEAD

1. `src/hooks_graphics.cpp:997-1135`, `DrawObjectAlphaProjected`: the original CABE `Game::DrawObjectAlpha_Internal` runs under temporary `ScopedRenderSemantic(ProjectedScreenEffect2D)`. Ordinal1 0x570008 arms `CurrentLensDeferredPhysical` **only after** the original call returns (:1115-1134); ordinal2 clears it on entry (:1016-1035). This is an observation interval, not a mesh/PMT owner. The two original 0x570008 calls are preserved.
2. `src/hooks_graphics.cpp:686-758`, `TraceLensOpaquePmtEntry`: `CurrentLensOpaqueFlush.serial != 0`, VR and telemetry are necessary for the scoped PMT receipt; otherwise it calls original 0x4700 and returns without recording. An admitted receipt captures `pmtEntrySerial,flushSerial,pass=entry[8],objectId=entry[14]` and calls original 0x4700 once. Prior 01580 established that the inspected EXE verifier **does not independently authenticate** these two field offsets or both hook CALL byte sites; this review does not promote their numeric values to proved retail identity.
3. `src/hooks_graphics.cpp:774-900`, `TraceLensOpaqueFlush`: an exact original scene flush (D44B/D79B), an inline original source or an armed deferred window admits a flush trace; its `sourceCallSerial/ordinal` comes from inline-or-window candidate, not one PMT identity. The receipt scopes original 0x52C0. `render_semantics.hpp:871-945` explicitly confines the deferred interval and PMT/flush receipts to diagnostic scope.
4. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:4282-4334`: `R30CaptureVisualRouteTrace` sets `lens` if producer LensFlareCentre, PMT serial, opaque flush serial, inline source receipt, deferred interval, or either of the two lens-like semantic scopes is present. `enabled = Settings::VRTelemetry && (lens || exactFiniteResultHud)`. Therefore a PMT-labeled lens draw may still be recognized as `family=LENS` for generic visual trace even when **not** eligible for the narrower R30 lens physical log.
5. `stereo_renderer_r30_r26_safe.cpp:6275-6405,6420-6436`: `R30TryScreenSpaceFovDraw` captures `visualRoute` **before** `R30SafeStereoBase` and returns `E_NOTIMPL` if the base is not admitted. After classification it sets `lensPhysicalCandidate` based only on `VRTelemetry && EffectiveScope in {ProjectedScreenEffect2D, SceneEffect}` — not the PMT, opaque flush or deferred window. Both the `VR TRACE LENS PHYSICAL RESULT FULL` and `VR LENS R30 PHYSICAL EYES` are thus conditional, not universal native draw counters.
6. `stereo_renderer_r30_r26_safe.cpp:2343-2349,2378-2415,6648-6730`: current **physical** `ProjectedScreenEffect2D` goes to projected classification, while `SceneEffect` with owned `FlatHud` goes to finite `PerspectiveHud`; scope admission and right-depth/pose/eye-WVP resource gates can still return `E_NOTIMPL` before any R30 eye draw. `R30BuildScreenSpaceEyeConstants:5525-5603` requires latched head sequence equal to pose, builds each eye's FOV-projected ray and emits `VR TRACE LENS R85 BUILD` only **after successful construction of both eye matrices**. No `R85 BUILD` record can be treated as proof of absence of a game ray or PMT.
7. `stereo_renderer_r30_r26_safe.cpp:6835-6950,7050-7330`: on admitted R30, left and right Draw attempts/RT/restoration are separately observable. `VR TRACE LENS PHYSICAL LEFT FAILURE` and `VR TRACE LENS PHYSICAL RESULT FULL` are not the same success path; neither HRESULT success nor two-eye attempt establishes source-eye RGB or accepted OpenXR pixels.
8. `stereo_renderer_r30_r26_safe.cpp:7378-7520`, `R30GuardScreenSpace`: `E_NOTIMPL` invokes `r29Draw()`. `VR TRACE LENS LOWER FALLBACK FULL` is narrow-scoped to the same two effective scopes, **but** `VR TRACE VISUAL LOWER PHYSICAL RESULT FULL` is emitted after lower draw when `R30CaptureVisualRouteTrace().enabled`; a still-active exact PMT or deferred receipt can make it enabled without either R30 lens scope. A lower `hr` and `pmtEntrySerial` are a route result, not proof of per-eye pixels, or the deferred 0x570008 source ordinal's ownership.

### Three conditional witness classes — source-static predictions, NOT observed frames

| Case | At the *same physical native call* | Expected evidence | Cannot infer |
| --- | --- | --- | --- |
| P / admitted R30 | Valid exact PMT; SceneEffect with owned perspective FlatHud and R30 base/resources/eye construction admitted | R30 `kind=PerspectiveHud`; lens physical left/result and potential eyes report; generic lower result absent | Source 0x570008 ownership from PMT field alone; correct pixels/head depth |
| L / R30 not admitted | Exact PMT or deferred receipt remains active but effective scope is neither lens candidate, or resources/pose/build reject the R30 route | Dedicated `LENS LOWER FALLBACK` may be **absent** for unscoped case; generic `VISUAL LOWER PHYSICAL RESULT` should report R29 lower when telemetry is enabled and capture remains active | No lens GPU draw merely because dedicated `LENS PHYSICAL` is absent; R29 completed both eyes from one lower HRESULT |
| W / no exact PMT ownership | Ordinal1 deferred time window exists, but PMT is absent or not authenticated | `windowAnchorSerial` can mark a lower/visual receipt; `pmtEntrySerial=0` or unverifiable; never label that physical primitive exact 0x570008 | Duplicate original CABE emitter; source object/texture/pass match; intended halo vs ghost |

All three predictions depend on actually entering the specified source and telemetry branches. The generic lower receipt is **not guaranteed** if no accepted trace source, an alternate API bypasses the watched code, or a different lower owner handles the call. Existing 01577/01578 findings are inherited, not newly scored.

## HYPOTHESIS_LEDGER

| ID | State | Previous evidence → this test | Falsification / outstanding proof |
| --- | --- | --- | --- |
| A — extra game-origin CABE/C993 emitter | OPEN | Preserved two original 0x570008 CABE calls and four C993 central-family IDs; this audit adds no emission evidence | Exact retail source order and PMT/alpha+texture joined to unexpected third emitted object and same-eye RGB |
| B — opaque queue/D3DX/native same-eye duplicate | OPEN | 01577 PMT pass/primitive fan-out; 01585 deferred window uncertainty; current R30/R29 trace coverage audit does not count same-eye GPU writes | Join each PMT pass + native draw API/serial + same-eye RT and pre/post RGB; two normal eyes are not two duplicates |
| C — mixed projected/PerspectiveHud/R29 lens geometry | SUPPORTED_CONDITIONAL_STATIC_INHERITED | 01585 identified potential route difference; this test establishes precise *receipts to inspect* for R30 success versus lower; not a measured split | In one authenticated PMT/pose, both CABE+C993 physical draws have same correct ray/eye reprojection and no lower divergence |
| D — distinct intentional centre/halo/ghost textures | OPEN | C993 and CABE original material families remain distinct; physical texture alpha/ROI absent | Per-object original alpha, 405890 pass, texture0 and per-eye same-frame ROI fingerprint |
| E — R19/R24 cached or flat host layer | SUPPORTED_CONDITIONAL_STATIC_INHERITED | 01582-01584 show final XR path can differ from requested; this audit is solely pre-host and adds no host incidence | Symptomatic exact frame final accepted binocular Projection with correct fresh source eyes rules out the single flat quad for that frame |
| F — source/HMD head/local bearing mismatch | OPEN_RUNTIME | R85 requires pose-matched head inverse, per-eye FOV; lower may not execute R85 | Two tracked head yaw samples, source sun bearing, actual eye orientation/FOV/ROI, accepted XR projection and host mode |
| G — missing dedicated R30 lens log proves no deferred CABE native draw | REFUTED_AS_GENERAL_INFERENCE_INHERITED_01577_01578 | PMT or window can enable generic VISUAL lower even while dedicated lens scope predicate is false; independently traced current post-rejection conditions | Only a complete authoritative original queue→all API draws→both RT/pixel receipts could prove absence on an exact frame |
| H — current Quest3 full flare splitting root cause | BLOCKED | User observation; no current-head exact frame/PMT/ROI/accepted XR join | Same-source R26+HUD vs focus HMD two-yaw material/fingerprint + actual XR evidence |

## EVIDENCE / gaps

EVIDENCE_SOURCE=GITHUB_CURRENT_PINNED_STATIC: hooks_graphics.cpp blob 982f55dc91c00faf336c06317006fe4aba11db1a; render_semantics.hpp blob f5b2403f59185993930e853edee42d639e1ff454; stereo_renderer_r30_r26_safe.cpp blob 6827f864b966ca743dff35725cc9ad9c9e96cc3b.
EVIDENCE_BASELINE=GITHUB_R26_HUD_PINNED: hooks_graphics.cpp blob 5651e2239ed2c894d65a0d140d0c1d0a170b96e7 at 629-695; R30 safe blob 0525d1cf53393902b5415bcb139cb55286673aaa at 2205-2235. The baseline CABE original wrapper is present; baseline C993 0x570002 conditionally used WorldBillboard, and its R30 owned SceneEffect/ProjectedScreen matrix classification differs from current. This is a static comparison, NOT a successful headset optical baseline claim.
EVIDENCE_POLICY=AGENTS.md newest R26+HUD precedence and docs/DX9EX_OPTICAL_ROUTE_PROBE_POLICY_20261020.md; comparison aab9e02 not HMD PASS; R84 never promoted.
EVIDENCE_DISASM=PREVIOUS_01580_RETAIL_BYTE_VERIFIER_COVERAGE_REFERENCED_NOT_REEXECUTED; original EXE PMT field identity not independently authenticated this task.
EVIDENCE_LOG=NONE_NEW_FOR_EXACT_SOURCE_HEAD; no current-head native PMT/eye RT trace, no sample-frame pixel ROI, no host actual XR receipt.
EVIDENCE_USER_REPORT=FLARE_SPLIT_AND_HEAD_FOLLOWING; not a matched SHA/HMD runtime verdict.
EVIDENCE_GAPS=No exact original 570008 ordinal→opaqueFlushSerial→405890 pmtEntrySerial/pass/texture→physical TopLevelDrawSerial/API→R30 admitted or R29 lower→actual L/R RT RGB→R19 transport sourceFrameId/QPC→R24 accepted layer/eye slices→Quest3 pose/two yaw chain. PMT field bytes, original texture/alpha and dropped/sparsely sampled logs remain uncertain.

## NEXT_FALSIFICATION_TEST — bounded single-flare receipt lattice

On separately authorized matching-source capture, preserve the user-protected R26+HUD baseline and compare against current focus *without auto-switching R84*. For an **authenticated** `0x570008` first and second CABE source sequence plus four C993 IDs, record sourceCallSerial/ordinal/sourceQPC, exact 4052C0 flush origin/serial, original 405890 PMT entrySerial/object/pass, original D3D9 physical draw API/TopLevelDrawSerial/texture/alpha/RT and the effective semantic at the actual GPU entry. For each PMT draw determine `R30SafeStereoBase`, screenKind, semantic admission, successful `R85 BUILD` or explicit failure, `VR TRACE LENS PHYSICAL {LEFT FAILURE, RESULT FULL}`, and `VR TRACE VISUAL LOWER PHYSICAL RESULT FULL`. Use the R7/R13 physical-eye receipts to fill missing lower-owner attempts; do not mistake an R29 HRESULT for same-eye RGB.

POSITIVE_C=on one authenticated frame, C993 projected source and CABE physical source have independently proven disjoint R30 projected/PerspectiveHud/lower routes and correspondingly different *same-eye* flare ROI/eye-ray placements; this only supports mixed routing, not necessarily erroneous extra emitter.
NEGATIVE_C=on the same authenticated frame, identical correct optical bearings and no lower divergence for both source families; then reject mixed-route causation **for that frame**.
POSITIVE_E=original source-eye ROI single but accepted final layer is R24 ViewSpace/BOTH/arrayIndex0 cached/flat with head-relative flare; supports host depth collapse, not original duplicate.
NEGATIVE_E=actual accepted fresh R19/R24 two-eye XR projection with distinct correct eye source ROIs and no cached/flat fallback; then that frame cannot be explained by a reused mono quad.
LOG_NEGATIVE_CONTROL=exact PMT but scope not ProjectedScreenEffect2D/SceneEffect: look for generic `VISUAL LOWER PHYSICAL RESULT FULL`; absence of the dedicated `LENS PHYSICAL RESULT FULL` is **expected** and must not be scored as no draw. Missing/retired PMT or different draw API leaves UNKNOWN.
PIXEL_VERDICT=No root-cause conclusion until same-tick original/native/R19/R24 and headset RGB centroids are observed at two head yaw positions, with L/R eye FOV, head and per-eye orientation, pose and source frame IDs.

NEXT_FALSIFICATION_TEST=EXACT_CABE_570008_405890_PMT_ENTRY_TO_R30_NOT_ADMITTED_OR_R29_LOWER_VISUAL_RECEIPT_THEN_NATIVE_LR_RT_ROI_AND_R24_ACTUAL_XR_SAME_TICK

PATCH_CANDIDATE_ONLY=DIAGNOSTIC_ONLY_NOT_APPLIED: for future separately authorized work, if a real PMT-exact 0x570008 draw cannot be causally distinguished across the rejection branch, add one bounded diagnostic route-decision receipt in `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6275-6405,6420-6436,6648-6730,7378-7520` with captured PMT/flush serial, actual GPU call/queue epoch, `R30SafeStereoBase`, screenKind, effective scope, explicit E_NOTIMPL reason and whether R29 lower was actually called; label deferred window `CANDIDATE` only. At `src/hooks_graphics.cpp:686-758,774-900,997-1135` keep PMT-exact versus CABE source-order semantics distinct. Do not expand scope, change CABE/C993 count, suppress 0x570008, reintroduce B9200 post-CALL/+5, or change render/runtime configuration. REQUIRE authenticated original bytes and native RGB before any actual optical route patch.
REGRESSION_RISK=DOCS_ONLY_NONE; future instrumented renderer could affect hot-path overhead, alter multi-object queue scopes, mis-attribute intentional pass 0/1 or stereo L/R draws, corrupt saved D3D state, or break baseline R26+HUD/host fallback. Regression boundary is exact original two CABE ordinals, all four C993 IDs, unchanged DX9Ex state restoration and fresh/cached XR layer identity. No runtime test executed.

CODE_CHANGE=NO
NEW_FINDING=NONE
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:CABE_570008_PMT_EXACT_ENTRY_R30_E_NOTIMPL_TO_R29_GENERIC_VISUAL_LOWER_VS_NATIVE_EYE_RGB_AND_ACCEPTED_XR
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01586.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01586]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01586.md
