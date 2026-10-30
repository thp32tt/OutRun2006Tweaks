# LENSFLARE-R26-UNTRUSTED-STATE-CACHE-20261030-1816 — R26 query-only colour-write guard can trust a stale render-state cache after coverage loss

DATE=2026-10-30 KST
RUN_KEY=LENSFLARE-R26-UNTRUSTED-STATE-CACHE-20261030-1816
REVIEW_SCOPE=LENS_FLARE_ONLY
TARGET=thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus
SOURCE_HEAD=fc56db50df44b5308c62e0e9df23d1982db00faa
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
MODE=DX9EX_REVIEW_ONLY
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
ROOT_CAUSE=UNCONFIRMED
NEW_FINDING=STATIC_CONDITIONAL_UNTRUSTED_TRACKED_RENDER_STATE_CACHE_CAN_MISADMIT_R26_WRITEFREE_OCCLUSION_SINGLE_EXEC
NEW_FINDING_RUNTIME=NONE
NEW_REGRESSION=NOT_ESTABLISHED

## Independent source-level falsification of 01599's stated invariant

The prior C-slot `CONVERSION-DX9EX-01599.md` correctly proves that the **R26 predicate itself** demands `COLORWRITEENABLE==0`, `ZWRITEENABLE==FALSE`, and no stencil writes before bypassing R23/R22/R13. It describes failed state reads as fail-closed. This review traces a **different dependency**: the implementation of `ReadTrackedRenderState` and R22's alternate/unhooked StateBlock Apply coverage-loss path. A valid *cached* render-state value can be returned even when StateBlock tracking is explicitly untrusted, and even after a live `GetRenderState` failure. Therefore a successful R26 predicate does not unconditionally prove that the **physical live GPU** colour-write mask is zero.

This is a bounded conditional source risk, NOT proof that any authentic CABE `0x570008` or C993 `0x570002/006/00F/010` primitive has entered the R26 query shortcut, that the live GPU mask diverged, that it produced lens pixels, or that this explains the Quest 3 head-lock. It is not a new R26+HUD regression: the exact getter logic already exists in the protected baseline, and the R26/R22 source blobs are identical. No source files or runtime settings were changed.

## SOURCE_TRACE — pinned current GitHub, 1-based lines

1. `src/vr/d3d9/stereo_renderer_r26.cpp:337-385` (blob `4e486a14c0f180928732419868f5449b6d8759cf`): query shortcut eligibility and `R26TrackedOcclusionDrawIsWriteFree` use `ReadTrackedRenderState` for colour, depth and stencil, without independently checking `StateBlockTracker::Reliable()` or live GPU values.
2. `src/vr/d3d9/stereo_renderer_r26.cpp:388-425,777-842`: on a *positive* cached-state predicate, R26 invokes the original physical API `actualDraw()` exactly once and bypasses the normal R23/R22/R13 chain; on a negative predicate, it delegates to R23. The shortcut counter is not a physical RGB receipt.
3. `src/vr/d3d9/stereo_renderer_r7.inc:962-1009` (current blob `evidence: fetch_file at SOURCE_HEAD`): `ReadTrackedRenderState` returns cached values when `StateBlockTracker::Reliable()==false` while `++reads < 16`, so the first 15 reads after a zero read-counter can return the cache **without live validation**. On the later live `GetRenderState` failure, it still returns the old cache if `TrackedRenderStateValid[index]` is true. The getter only returns false on that failure if the cache is invalid. The R26 caller cannot distinguish those cases from the boolean return alone.
4. `src/vr/d3d9/stereo_renderer_r7.inc:1011-1052`: `InvalidateTrackedRenderStates` clears validity, `PrimeTrackedRenderStates` reads live state, and intercepted `SetRenderStateDest` updates the cache on successful game setters. This makes a previously valid `COLORWRITEENABLE=0` cache feasible; no claim that a real game trace used it.
5. `src/vr/d3d9/stereo_renderer_r22.cpp:143-176,182-230` (blob `dd1cbed902f468166dcf93598ca0b24043584dad`): a successfully hooked `StateBlock::Apply` invalidates tracked states. In contrast, alternate Apply vtable, missing vtable or hook-install failure mark `StateBlockTracker` unreliable/coverage lost; these failure branches do **not** themselves call `InvalidateTrackedRenderStates`. An unhooked alternate Apply could therefore change physical state without updating the previously valid cache. This is a condition, not a demonstrated installed hook failure.
6. `src/vr/state/state_block_tracker.hpp:24-51`: `Reliable()` combines R22 reliability, event consumer readiness and `!CoverageLost()`; `MarkCoverageLost()` only sets the coverage-loss flag, not the separate R7 render-state validity array.
7. `src/vr/d3d9/stereo_renderer_r13.cpp:592-655`: R13 has its own unsafe-query/MRT mono-shadow or original single-execution branch. The R26 false-positive hypothesis must be distinguished from R13's legitimate fail-closed mono route.
8. `src/hooks_graphics.cpp:997-1135,1137-1190,1245-1290`: CABE source ordinal1 can be deferred, while C993 four source IDs are projected source receipts; neither proves an exact R26 physical Draw. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:7605-7666,8930-8942` invokes the default R26 lower callback on R30 `E_NOTIMPL` (the name `r29Draw` is not an R29 physical-eye receipt). This lower hook identity was already established by C-slot 01588 and is not scored again.

BASELINE_CONTROL=R26_AND_R22_CURRENT_BLOBS_IDENTICAL_TO_PROTECTED_BASELINE;_R7_BASELINE_967_1009_HAS_SAME_16_READ_CACHE_AND_LIVE_FAILURE_FALLBACK
DISTINCT_FROM_PRIOR=01599_PROVED_R26_PREDICATE_WITH_ASSUMED_AUTHORITATIVE_READ;_THIS_REVIEW_PROVES_READ_SUCCESS_DOES_NOT_ALWAYS_MEAN_LIVE_GPU_STATE_UNDER_COVERAGE_LOSS
SOURCE_VERIFICATION=GITHUB_PINNED_CURRENT_AND_PROTECTED_BASELINE
EVIDENCE_DISASM=INHERITED_ONLY;_NO_NEW_RETAIL_EXE_BYTES
EVIDENCE_RUNTIME=NONE

## HYPOTHESIS_LEDGER — A/B/C/D/E/F

| Cause | Status and bounded result |
| --- | --- |
| A original extra emitter | OPEN. The cache path cannot add a D3A5/C993/CABE source call. Compare exact original source ordinals and original PMT material IDs. |
| B duplicate physical Draw / wrong mono execution | NEW CONDITIONAL RISK: with an active occlusion query, valid but stale tracked `COLORWRITEENABLE=0` and live nonzero, R26 could execute a colour-writing lens primitive once on the original target while bypassing R23/R22/R13. This is **not** proof of two same-eye draws, a visible flare or a host-accepted image. |
| C WVP/c64 and binocular depth | OPEN. A false R26 write-free shortcut would skip lower stereo replay; whether that becomes zero-disparity or wrong binocular depth depends on the real target, WVP, R9 seed and host acceptance. No actual CABE/C993 PMT/c64 matched. |
| D material/texture/alpha | OPEN. The original CABE diffuse `m[3]` versus combiner `m[17]` split and two intended glow ordinals are inherited from prior review; no new texture or blend sample. |
| E OpenXR fresh/cached | OPEN. R19 source-frame/QPC and R24 accepted projection or ViewSpace cached fallback are not joined to the query draw; a stale XR layer can mimic visible persistence independently. |
| F head-lock | OPEN. No Quest 3 two-yaw measurement. Neither cache divergence nor a single native Draw proves head-local motion. |

## FALSIFICATION — safe, no game patch

- **Positive normal control:** With intercepted Apply and `InvalidateTrackedRenderStates` called, a fresh `ReadTrackedRenderState` should obtain the live colour mask. A real colour writer with live nonzero must be rejected by R26 and forwarded to R23.
- **Coverage-loss negative control:** On a separate deterministic harness/test only (NOT a game hook), set a previously valid tracked `COLORWRITEENABLE=0`, mark coverage lost without invalidating the R7 array, change the mocked physical state to a nonzero mask through an unobserved Apply, and invoke the getter. Predict cached zero for up to 15 per-state reads before live refresh. At live read failure with valid cache, predict successful stale zero even at the refresh boundary. These are static source predictions; no harness was run.
- **Lens admission control:** For a single authenticated C993 `0x570002/006/00F/010` or CABE `0x570008` physical PMT, record sourceCallSerial/opaque queue node/PMT pass/texture0/alpha, R30 route, actual R26 queryActive and tracked-vs-live colour/Z/stencil, R26 shortcut/reject, R23/R22/R13/R9 outcome, actual L/R RT PRE/POST RGB and final accepted XR layer/frame/QPC. An R26 shortcut with live nonzero and same-draw RGB delta would support this mechanism; if all authentic flare draws have no query, valid intercepted Apply, live zero, or never enter R26, it cannot explain the observed flare.
- **Optical discriminator:** At two HMD yaw poses compare world-bearing flare centroid and left/right RT RGB against accepted OpenXR projection arrayIndex/pose and ViewSpace cached quad. Distinguish two intended CABE materials from duplicate same-eye pixel writes.

## EVIDENCE_GAPS

No observed unhooked alternate StateBlock Apply in the user's game, no live-vs-tracked mismatch receipt, no active-query lens PMT, no physical Draw PRE/POST RGB, no verified original CABE/C993 texture/material pass or per-eye c64, no R19/R24 accepted XR layer trace, no Quest3/VDXR two-yaw capture. A source-only conditional cannot be promoted to root cause or regression. The R7 getter's periodic sampling and Apply interception may be sufficient in the real runtime; this has not been measured.

## PATCH_CANDIDATE_ONLY / REGRESSION

PATCH_CANDIDATE_ONLY=NOT_APPLIED;_IF_AUTHENTIC_LENS_QUERY_AND_STALE_MASK_ARE_PROVEN_REVIEW_R26_SHORTCUT_FAIL_CLOSED_ON_UNRELIABLE_STATEBLOCK_COVERAGE_OR_REQUIRE_SUCCESSFUL_LIVE_COLOR_Z_STENCIL_READS_AT_SHORTCUT_BOUNDARY;_NO_B9200_HOOK_NO_GLOBAL_LENS_SUPPRESSION
REGRESSION=Any later change must preserve valid write-free query side effects, R26+HUD baseline, normal R23/R22/R13/R9 stereo fallback, CABE's two intended ordinals, C993 projected shader/c64, R30 restore, performance, and R19/R24 OpenXR fresh/cached selection. R84 comparison only.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:R26_QUERY_SHORTCUT_TRACKED_VS_LIVE_COLOR_MASK_COVERAGE_LOSS_AUTHENTIC_CABE_C993_PMT_TO_LR_RGB_ACCEPTED_XR_TWO_YAW
