# CONVERSION-DX9EX-01578 — lens PMT native-DIP-to-eye join key and non-DIP coverage negative controls (REVIEW_ONLY)

DATE=2026-10-29 KST
TASK_ID=CONVERSION-DX9EX-01578
PRODUCTION_ID=CONVERSION-DX9EX-01578
EVENT_ID=CONVERSION-DX9EX-01578-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=0cb9399d58c442214e2264177b83cc9031cc7df5
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
MODE=DX9EX_REVIEW_ONLY
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
RUNTIME_VALIDATION=UNTESTED
AUTOMATION_VALIDATION=DOCS_ONLY_COMMIT_READBACK_REQUIRED
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=NONDEFAULT_COMPARISON_ONLY
HUD_COMPARISON=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN

## Prior ledger inheritance and DISTINCT_TEST

- Inherited 01575: flush scope/family is not PMT ownership. 01576: original colour-undo patch count is not opaque descriptor count. 01577: one original 405890->404700 PMT invocation can fan out to two passes and many primitive entries; PRE-DIP is not successful eye pixels. Keep these results without re-scoring.
- **Different source-static test this task:** test whether the newly introduced `dipSerial` can join *one specific* native indexed primitive interception to its **post-call** R7 left/right outcome when a PMT invocation produces several primitives. Separately audit whether PMT DIP FULL covers the other three intercepted D3D9 primitive API variants. Use R30 independent admission/eye receipt and C993 centre as negative controls.
- No new original retail EXE disassembly, log ingestion or Quest3/VDXR run occurred. The following is instrumentation control-flow evidence, **not** proof that the actual doubled second visible 570008 lobe took any particular route.

## NEW_FINDING (instrumentation join/completeness boundary, not confirmed visible bug)

NEW_FINDING=SOURCE_STATIC_PMT_DIP_SERIAL_IS_LOCAL_TO_PRE_DRAW_INDEXED_PRIMITIVE_TRACE_AND_ABSENT_FROM_R7_POST_EYE_RECEIPT;_PMT_DIP_FULL_LOG_ONLY_COVERS_DRAW_INDEXED_PRIMITIVE_DEST_NOT_OTHER_NATIVE_PRIMITIVE_API_VARIANTS;_R30_LENS_PHYSICAL_RESULT_IS_INDEPENDENTLY_SCOPE_GATED;_CURRENT_SECOND_FLARE_OPTICAL_ROOT_CAUSE_UNRESOLVED.

1. `src/vr/d3d9/stereo_renderer_r7.inc::DrawIndexedPrimitiveDest:1916-1944` captures `CurrentLensOpaquePmtEntry`, increments a **function-local static atomic** `pmtDipSerial` when telemetry and `pmt.serial` are enabled, and prints `VR TRACE LENS PMT DIP FULL` with `dipSerial`, PMT entry serial, flush serial, object, pass and indexed geometry. It then creates `drawCall` and invokes `ExecuteStereoDraw(device, call)`. `dipSerial` is **not passed** into that call or a scoped per-DIP receipt in the inspected function.
2. `R7CaptureVisualTrace:1621-1642` snapshots PMT/flush/source/producer at native draw entry. `R7TraceVisualEyes:1644-1717` emits a separate incrementing `r7Serial`, the **PMT entry serial** and L/R attempted/HRESULT/route/restore, but **no `dipSerial`, primitive signature, or original DrawIndexedPrimitive call ID**. `ExecuteStereoDraw:1719-1913` calls the eye logger on bypass/reject/fail/pair outcomes. Therefore when *one* PMT entry generates two indexed primitives (the independent 01577 fan-out possibility), the two PRE-DIP records can share `pmtEntrySerial,pass,object` while two post-eye records share that same PMT identity, with no guaranteed one-to-one **explicit key** in the record schema. Timestamps and order might permit inference in a bounded single-thread nonnested trace, but are not an authenticated per-DIP causal join, especially across nested/interleaved/lost logs. This is a **telemetry sufficiency** counterexample, not an observed wrong-eye draw.
3. `DrawPrimitiveDest:1915`, `DrawPrimitiveUPDest:1945`, and `DrawIndexedPrimitiveUPDest:1946` forward via `ExecuteStereoDraw` without printing `VR TRACE LENS PMT DIP FULL`. Thus that message is **not an exhaustive trace of all intercepted native D3D9 primitive API types**. Whether the original retail 0x404700 uses any alternate API for the affected flare is **unverified**; no such real flare call is asserted here. A PMT with eye events but zero PMT DIP FULL logs cannot, on this trace alone, be declared non-drawing, nor attributed to one particular alternate API without an API-class receipt.
4. The `R30TryScreenSpaceFovDraw` physical-result log is also not a universal substitute: at `stereo_renderer_r30_r26_safe.cpp:6256-6263` `lensPhysicalCandidate` is based on an **effective ProjectedScreenEffect2D/SceneEffect scope** and telemetry; a non-admitted or differently scoped draw can lack R30 `VR TRACE LENS PHYSICAL RESULT FULL` even while PMT TLS is present. When it exists (`:6912-6967`), `serial=TopLevelDrawSerial`, `pmtEntrySerial`, left/right result/RT and texture0 are available, but **no R7 `dipSerial`** appears and there is no measured eye colour write in that record.
5. **Centre/other-family negative control:** `hooks_graphics.cpp::apply:1324-1340` installs a separate C993 centre call and D3A5/D3AA guarded source scope. `R7CaptureVisualTrace` can label `ProducerToken::LensFlareCentre` as lens even with `pmtEntrySerial=0`. Conversely the two 405890 PMT CALL wrappers (`hooks_graphics.cpp:1315-1323`) only scope exact original entries **within traced opaque-flush TLS** (`::TraceLensOpaquePmtEntry:686-758`). Hence “no PMT DIP FULL” is neither proof that the whole lens emitter was absent nor a measurement that the second visually doubled component must be CABE 570008. The identified second of ~5–6 visible components has **no authenticated texture/alpha/RT-ROI identity**.
6. `DrawObjectAlphaProjected:1000-1075` preserves both original 570008 source ordinals and warns `physicalDraw=UNOBSERVED` in a source-call receipt. No changed emitter path, game draw suppression, stereo route, native rasterisation or host/OpenXR behaviour is shown by this read. A stereo L/R pair is expected and not itself a same-eye duplicate. Current logs do not prove that R30 or R7 actually handled the user's doubled lobe.

## HYPOTHESIS_LEDGER

| ID / status | Previous evidence | Different current test / falsification |
| --- | --- | --- |
| A game-origin extra emitter — OPEN | Original CABE two 570008 source calls intentional; no exact visible lobe attribution | Even perfect `dipSerial` joins could yield intended two source materials; need original 405360 descriptor, texture/alpha, same-eye colour ROI across exact ordinals. |
| B PMT queue / D3DX / native same-eye resubmission — OPEN | 01577 showed pass0/pass1 and primitive fan-out; PRE-DIP is not a pixel | This task **refutes explicit unique PRE-DIP -> R7-eye join by PMT serial alone** when >1 DIP shares entry; determine per-DIP route/HRESULT with a propagated ID, geometry and eye RT; confirm same primitive/texture contributes unexpectedly twice in one eye. |
| C wrong L/R WVP, XYZRHW head lock — OPEN_RUNTIME | Prior projection diagnostics; no current-head matching headset capture | Match exact physical draw and camera/light sun-bearing with L/R c64/WVP and accepted XR pose/FOV at two yaw positions; no inferred depth from draw count. |
| D separate layered halo/glow versus unintended second lobe — OPEN | Two original 570008 ordinals, multiple ring children and possible two-pass material | Bind second of ~5–6 visible elements to material texture0, blend, colour-write and positive same-eye ROI delta; distinguish intended overlap from repeated pixels. |
| E host R19 cached/incorrect source and R24 composition — OPEN_RUNTIME | R19 may select source frame B with pose/FOV A; no exact accepted-eye chain here | Join actual native eye RT ROI -> R19 selected frame/UV -> accepted R24 xrEndFrame image/pose; if native single, XR double, prioritize E. |
| F source light / HMD-local projection mismatch — OPEN_RUNTIME | Source producer and eye submission unjoined | Two-yaw matched bearing+projection/eye ROI controls; identical eye coordinates with head motion may be expected for some at-infinity/zero-disparity components, so material/depth context required. |
| G “one pmtEntrySerial explicitly joins every DIP to its post-eye result” — REFUTED_AS_GENERAL_INFERENCE | PMT entry serial is per 404700 invocation, 01577 | `dipSerial` is local to DIP PRE log and missing from `R7TraceVisualEyes`; constructible >1-DIP same-PMT counterexample. Falsifier: another **actual inspected** unique causal key exists in both records or demonstrated strict serialization with no lost/mixed entries for the exact capture; neither established here. |
| H “PMT DIP FULL enumerates every original lens physical primitive API” — REFUTED_FOR_INTERCEPTOR_COVERAGE; RUNTIME_INCIDENCE_BLOCKED | 01577 only inspected DIP | Three other hooked primitive entry paths lack PMT DIP FULL pre receipt. Falsify runtime relevance by canonical original-404700 proof + matched live trace that **this specific lens material** only executes indexed-DIP; do not label the other APIs as observed flare. |
| I “exact PMT absent means centre/entire flare absent” — REFUTED_AS_GENERAL_INFERENCE | Centre C993/D3A5 distinct from opaque PMT hook | Lens producer can be classified outside PMT; verify actual centre native API + eye/host ROI before deciding which draw was visually doubled. |
| J actual user-visible second-lobe duplication cause — BLOCKED | User reported doubled/head-follow lens lobe | No matched Quest3 native pixel, material/alpha or accepted XR eye evidence; no root-cause declaration. |

## SOURCE_TRACE / EVIDENCE

PRIMARY_GITHUB_PINNED_MOD_SOURCE=0cb9399d58c442214e2264177b83cc9031cc7df5

- `src/hooks_graphics.cpp::TraceLensOpaquePmtEntry:686-758`: PMT TLS only in traced opaque flush; PRE/POST each invoked original 0x404700 once. `::apply:1301-1340`: original opaque CALL 0x5A41/0x5C44 and separate C993 centre and D3A5/D3AA scope (no new hooks installed). `::DrawObjectAlphaProjected:1000-1075`: two 570008 source ordinals, original physical draw not authenticated by source receipt.
- `src/vr/game/render_semantics.hpp::LensOpaquePmtEntryReceipt/ScopedLensOpaquePmtEntry:921-963`: PMT entry TLS shape has `serial` and `pass`, no per-primitive post-result key.
- `src/vr/d3d9/stereo_renderer_r7.inc::R7CaptureVisualTrace:1621-1642`, `::R7TraceVisualEyes:1644-1717`, `::ExecuteStereoDraw:1719-1913`, `::DrawPrimitiveDest/DrawIndexedPrimitiveDest/DrawPrimitiveUPDest/DrawIndexedPrimitiveUPDest:1915-1946`: actual interception, PRE serial, POST fields, all primitive API variants, and return paths checked at pinned SHA.
- `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30CaptureVisualRouteTrace:4215-4235`, `::R30TryScreenSpaceFovDraw:6256-6263,6912-6967`: independent scope gate and post-native bilateral receipt; no explicit R7 per-DIP join key or eye RGB delta.
- PRIOR_RECONSTRUCTION_ONLY=`r4dius/outrun2-decomp@e1e1c592.../src/platform/pc_render_flush.cpp::draw_404700:761-798`, cited/read by 01577 for primitive fan-out; **not re-fetched or re-run during this review**. Prior original EXE byte-check script not executed. Do not assume source reconstruction proves actual retail native API class.
- USER_REPORT=second visible lens element appears doubled/head-locked; symptoms are not verified at pinned SHA.
- GAME_LOG=NO_CURRENT_HEAD_MATCHED_RUNTIME_LOG; DISASSEMBLY_NEW=NONE; QUEST3_VDXR=NOT_TESTED; ACCEPTED_XR_EYE=NOT_OBSERVED.

## NEXT_FALSIFICATION_TEST (predicted results; no runtime executed)

1. First make a bounded joined **per-API** lens capture in a separately authorized diagnostic build, not this REVIEW_ONLY job. Join `(sourceCallSerial,ordinal,flushSerial,pmtEntrySerial,pass,primitiveCallSerial,API,geometry,texture0,blend,eye,RT,HRESULT,restore)` with a globally/within-frame unique causal key created *before each intercepted API call and preserved to its post-call result*. Preserve independent R30 lower/handled route and its own `TopLevelDrawSerial`. Do **not** infer equality from timestamp ordering.
2. **P1 one-PMT one-indexed-DIP stereo control:** expected one PMT entry, one unique primitive call ID, one PRE receipt and a matching post receipt with `route=STEREO_PAIR`, left and right HRESULT success (subject to preparation) and separate eye RTs. This is normal stereo, not duplicate halo.
3. **N1 one-PMT two-indexed-DIP ambiguity control:** under two admissible primitives, expect two PRE `dipSerial` values sharing `pmtEntrySerial`; existing two R7 EYES logs share the PMT identity but omit those PRE `dipSerial` keys. A future causal ID must yield two separately joined results; do not count two PRE events as two optical flares.
4. **N2 alternate primitive API coverage control:** if a PMT or centre dispatches `DrawPrimitive`, `DrawPrimitiveUP` or `DrawIndexedPrimitiveUP`, expect no `PMT DIP FULL` from those API hooks under current source, but eligible `R7 VISUAL EYES FULL` may still exist. Determine actual incidence with API-labelled physical receipts, not a guessed fallback.
5. **N3 R30 scope/early owner control:** exact PMT TLS present but effective scope not one of the two admitted candidates can yield no R30 `LENS PHYSICAL RESULT FULL`; distinguish R7 native, lower fallback, rejection, no GPU write. PMT presence alone is not an R30 eye receipt.
6. **N4 C993-only centre control:** a lens producer receipt with `pmtEntrySerial=0` must not be counted as absence of flare. Separate C993 centre from CABE 570008 and ring/halo passes using actual texture0/material/eye ROI.
7. **Optical/HMD discriminator:** per-primitive successful L/R return is still not a pixel-write proof. Join native pre/post same-eye RGB ROI for **the authenticated second lobe**, R19 selected image frame/UV and accepted R24 xrEndFrame source+pose/FOV at two yaw positions. Only then rank original/queue duplicate (A/B/D), per-eye projection (C/F) or host re-composition (E).

EVIDENCE_GAPS=No validated original 404700 native API instruction branch for the disputed second-lobe material, no source-matched PMT multi-primitive runtime case, no causal per-API pre/post key, no exact second-lobe texture/alpha and same-eye colour ROI, no R19/R24 accepted source-frame/pose join, no Quest3/VDXR two-yaw captures.

PATCH_CANDIDATE_ONLY=NOT_APPLIED; DIAGNOSTIC_ONLY_FUTURE_AUTHORIZATION_REQUIRED.
- Exact bounded candidate: `src/vr/d3d9/stereo_renderer_r7.inc::DrawIndexedPrimitiveDest:1916-1944` propagate per-invocation `dipSerial` (or new stable primitive-call ID) via a diagnostic scope/argument to `R7TraceVisualEyes:1644-1717` through `ExecuteStereoDraw:1719-1913`. Include `api` and geometry signature in **both** PRE and post results. If verified flare uses alternate native APIs, equivalently instrument `DrawPrimitiveDest:1915`, `DrawPrimitiveUPDest:1945`, `DrawIndexedPrimitiveUPDest:1946`; keep separate `pmtEntrySerial` and R30 `TopLevelDrawSerial` namespaces.
- Falsifiers: fully authenticated existing per-DIP original call ID already present in both pre/post logs at pinned SHA, or canonical byte+matching runtime evidence that the specific flare only executes one indexed primitive per PMT (which narrows the incident but not general API coverage).
- Regression boundary: diagnostic-only, bounded lens scope, keep original primitive call exactly once per eye as before, unchanged callback ABI, no texture/alpha/route/state/depth/restore/OpenXR changes, no extra unsafe original-game hooks; protect R26+HUD, both 570008 original contributions, R84 nondefault, B9200 post-CALL/+5 ban.

REGRESSION_RISK=DOCS_ONLY_NONE; future logging if unbounded may perturb frame pacing and create false timing diagnoses; false join/dedup may hide legitimate multiple primitive passes; any route edit requires separately authorised exact-HMD testing.
NEW_CODE_PATCH=NONE
NEXT_REVIEW=LENS_FLARE:R7_PMT_DIP_SERIAL_TO_POST_EYE_JOIN_AND_ALTERNATE_NATIVE_DRAW_API_NEGATIVE_CONTROL_THEN_570008_SECOND_LOBE_RGB_R19_R24
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01578.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01578]
EXPECTED_CHANGED_PATHS=ONLY_THIS_NEW_DOC
