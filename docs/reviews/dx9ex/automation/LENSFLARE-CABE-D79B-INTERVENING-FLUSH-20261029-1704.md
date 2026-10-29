# LENSFLARE-CABE-D79B-INTERVENING-FLUSH-20261029-1704 — CABE ordinal1 material cannot survive the normal intervening D79B full-queue flush (REVIEW_ONLY)

- DATE=2026-10-29 KST; TARGET=thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus; SOURCE_HEAD=4f754b0cafdcd6ffb168265c44d92ec6fe3f6b76.
- REVIEW_SCOPE=LENS_FLARE_ONLY; BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE; R84=COMPARISON_ONLY.
- CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY; CI_SKIP=NONE; B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN.
- PRIOR_NON_DUPLICATE=01539/01545 first-deferred/second-immediate, 01574 proposed ordinal1-PMT-during-ordinal2 conditional alias, 01575 scene-flush-family false positive, and prior R19/R24/R85 host/eye gaps.
- DISTINCT_TEST=Falsify the *specific* 01574 ordinal1-PMT-survives-until-ordinal2 counterexample against the actual intervening original D79B full flush and the newly added flush-origin telemetry. This does NOT claim an actual HMD double-flare fix or a newly discovered original emitter.

## NEW_FINDING — normal original queue schedule rules out one prior hypothetical alias

NEW_FINDING=STATIC_NORMAL_PATH_D79B_FULL_FLUSH_BARRIER_REFUTES_01574_P1_QUEUE_SURVIVAL_INTO_ORDINAL2;_CROSS_ORDINAL_SOURCE_LABEL_AMBIGUITY_WITHIN_EACH_MULTI_OBJECT_FLUSH_AND_ACTUAL_EYE_PIXELS_REMAIN_OPEN.

1. The original reconstructed `sun_flare_40cbc0` queues the first CABE `0x570008` among eleven ring children with `immediate_8999b0=0`, calls `render_queue_flush_4052c0`, and **only then** invokes the second `0x570008` with a different scale/alpha coefficient. The exact canonical EXE verification *code* also pins the order `0xD6BA (first CABE) < 0xD79B (4052C0) < 0xD7B4 (second CABE)`. The verifier's assertions were read on GitHub; no fresh retail EXE was executed in this review.
2. Reconstructed `render_queue_flush_4052c0` passes the entire current `opaque` queue to `405890`, restores all colour undo entries, and unconditionally sets `opaque.count=0`, `opaque.matrix_count=0`, `immediate_8999b0=1` before returning normally. Thus an ordinal1 descriptor queued before D79B is either drawn/filtered during D79B or discarded as that queue is cleared; it cannot remain queued to be first consumed by the later ordinal2 call on this normal path.
3. The second original `0x570008` is then admitted with `immediate_8999b0=1`, so the reconstructed `405360` immediately invokes its `4052C0` owner if the descriptor is valid and enqueued. The current mod's `DrawObjectAlphaProjected` closes the ordinal1 deferred receipt at second-entry, then establishes the ordinal2 inline receipt. A physical draw inside this second inline flush is not an unconsumed P1 from before D79B under the preceding full-flush invariant.
4. Consequently the **particular 01574 conditional P1-crossing example** (ordinal1 opaque PMT first drained inside ordinal2's wrapper) is not reachable in the normal reconstructed CABE sequence if D79B returns normally with the stated full-clear semantics. This is a correction to a *hypothetical diagnostic counterexample*, not proof that the 01574 call-stack-vs-PMT distinction is generally safe. A D79B multi-object flush still cannot assign its PMT to ordinal1 merely from `windowAnchorOrdinal=1`, and a later scene flush or re-enqueue requires separate identification.
5. At current HEAD, `TraceLensOpaqueFlush` brackets the D79B and 542A original 4052C0 calls with distinct `opaqueFlushOrigin` and `flushSerial`; the R30/R7 receipts carry that invocation serial but not exact PMT identity. This provides a **future observational falsifier**: on a successful original sun call, first-ordinal deferred physical draws should occur in D79B (or an earlier separately identified inline flush), while ordinal2 immediate physical draws should occur in 542A, not as an old ordinal1 descriptor surviving D79B. Sampling, R30 admission, material skips and alternative paths can suppress receipts, so absence is not a draw-count proof.
6. Neither the normal queue barrier nor the diagnostic serial proves whether one eye receives two RGB writes, whether the original two 570008 layers are visually intentional, or whether R19/R24 OpenXR fresh/cached output duplicates a previously correct game-eye image. No source-matched Quest3 frame or exact PMT/texture/alpha-to-pixel chain exists here.

## HYPOTHESIS_LEDGER

| Axis | Status after this distinct falsification | Required next discriminator |
| --- | --- | --- |
| A extra original emitter | OPEN; canonical two CABE calls are intentional | Authenticate per-sun 0x570002/006/00F/010 and both 570008 emitter counts, exact PMT texture/alpha and same-eye RGB |
| B duplicate queue/D3DX/native draw | SPECIFIC_01574_P1_CROSS_D79B_SURVIVAL_REFUTED_NORMAL_PATH; OTHER_REPLAY_OPEN | Correlate original descriptor ID, D79B/542A flush serial, 405890 pass, R30/R7/R29 physical draw, same-eye RT and RGB delta |
| C wrong WVP/c64/per-eye depth | OPEN_RUNTIME; first deferred vs second inline can still use different semantic routes | Same-frame physical L/R WVP, c64, eye pose/FOV, admitted route and centroid |
| D intended halo layering | OPEN; two different 570008 coefficients and eleven original ring children remain legitimate | Actual per-pass texture/alpha/colour-write, not ordinal or flush count |
| E host OpenXR duplicate/cache | OPEN_RUNTIME | Join pre-host L/R RT RGB to R19 fresh/cached source and accepted R24 xrEndFrame eye slices |
| F head-lock | OPEN_RUNTIME | Two-yaw Quest3 test with matched game camera, sun bearing, source frame and final XR pose |
| G ordinal1 PMT survives D79B to drain under ordinal2 | REFUTED_FOR_NORMAL_RECONSTRUCTED_QUEUE; runtime/binary exceptions UNTESTED | Demonstrate actual D79B non-drain, early exit, queue repopulation or unexpected EXE branch if claiming exception |

## SOURCE_TRACE — inspected GitHub files and lines

- Focus `src/hooks_graphics.cpp::DrawObjectAlphaProjected:911-1052`: ordinal1 deferred ARM after original return; second-entry CLOSE; ordinal2 inline scope. `::TraceLensOpaqueFlush:703-795` and `::apply:1223-1236`: D79B/542A flush origins and diagnostic-only serial. Source blob `3ce44974e26ceb7a127d45f98927aff1f7bf4eb9`.
- Focus `tools/disasm_outrun_goal_flare_p0.py:76-101,151-209`: `LENS_570008_CALLS`, `LENS_FLUSH_EDGES`, exact original E8 verification contract and ordering assertion. Source blob `d2fcd8e7732b63d11ed2a1419a5e0e45b49c80cf`; this run READ the assertion, did NOT rerun its EXE-based verification.
- Original reconstructed `r4dius/outrun2-decomp@e1e1c592b802a6f3f7020a676abd3ba1be479e62/src/platform/race_course_passes.cpp::sun_flare_40cbc0:695-715`: first 570008, D79B-style flush, second 570008.
- Original reconstructed `src/platform/pc_render_queue.cpp::render_object_405360:219-246`: immediate=0 enqueue only; immediate=1 enqueue then flush. `src/platform/pc_render_flush.cpp::render_queue_flush_4052c0:970-980`: full opaque draw/undo/reset, immediate=1. These are reconstructed semantics, not independently measured retail GPU pixels.
- Inherited `docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01545.md` established the first/second immediate asymmetry; `01574.md` proposed the P1-inside-ordinal2 hypothetical without enforcing the intervening D79B full-drain invariant; `01575.md` distinguishes scene flush serial from authentic PMT identity. This review specifically resolves that contradictory hypothetical; no old achievement is re-scored.

## EVIDENCE_GAPS / FALSIFICATION

- EVIDENCE_GAPS=No retail EXE bytes rerun this turn; original reconstruction may differ in exceptional paths; no actual D79B pre/post queue-count runtime receipt, no authenticated PMT node/pass/texture/alpha, no same-eye RT RGB delta, no full R30/R7/R29 physical owner and no accepted OpenXR per-eye frame or HMD yaw experiment.
- POSITIVE_CONTROL=On a valid sun invocation, record ordinal1 enqueue then D79B PRE/POST with `opaqueFlushOrigin=SCENE_D79B`, original opaque queue count before/after, actual DrawEntry IDs, PMT passes and per-eye writes; after POST require queue count zero before ordinal2 entry, then separately record `INLINE_405360_542A` for ordinal2.
- FALSIFIER=Any authenticated original ordinal1 descriptor whose queue entry remains after a normally returning D79B full-clear and is consumed at ordinal2's 542A flush contradicts the reconstructed queue model; inspect original EXE, re-enqueue, identity reuse and diagnostic timing before attributing a double flare.
- NEGATIVE_CONTROL=Multiple D79B PMT children under one `windowAnchorOrdinal=1`, or one PMT's normal L/R pair, does not mean duplicate same-eye optical pixels; first/second distinct material alpha can intentionally overlap.
- PATCH_CANDIDATE_ONLY=NONE_APPLIED. A separately authorized future *read-only* trace may join exact queue generation and PMT descriptor to `opaqueFlushSerial`, source ordinal, native draw and per-eye RGB without changing emitter, alpha, WVP, route, hook ABI, or policy. No B9200 post-CALL/+5 detour.
- REGRESSION=DOCS_ONLY_NONE; hypothetical premature suppression of either CABE 570008, forced whole-queue projected scope, or de-dup keyed by flush serial risks removing intentional halo/ring children. R26+HUD immutable; R84 comparison only.
- NEXT_REVIEW=LENS_FLARE:D79B_PRE_POST_OPAQUE_COUNT_ZERO_AND_ORDINAL2_542A_EXACT_PMT_TEXTURE_ALPHA_LR_RGB_FRESH_XR_TWO_YAW.

CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
GITHUB_RECORD=docs/reviews/dx9ex/automation/LENSFLARE-CABE-D79B-INTERVENING-FLUSH-20261029-1704.md
EXPECTED_COMMIT_MARKER=[AUTO:LENSFLARE-CABE-D79B-INTERVENING-FLUSH-20261029-1704]
EXPECTED_CHANGED_PATHS=ONLY_THIS_NEW_DOC
