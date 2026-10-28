# LENSFLARE-XR-BRIGHT-CENTROID-ROI-20261028-1449 — global brightness centroid can conceal real flare disparity (DX9Ex LENS_FLARE_ONLY REVIEW_ONLY)

- DATE=2026-10-28 14:49 KST; RUN_KEY=LENSFLARE-XR-BRIGHT-CENTROID-ROI-20261028-1449; TARGET=thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus; SOURCE_HEAD=38f2d9bcd51a7a880028d4d08cc7f6e48ed86452; SOURCE_SSOT=CONNECTED_GITHUB_PINNED.
- REVIEW_SCOPE=LENS_FLARE_ONLY; CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; CI_SKIP=NONE; DOCS_ONLY_SOURCE_BUILD_GATE=NOT_REQUIRED.
- PROTECTED_BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE; R84=COMPARISON_ONLY; B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN.
- INHERITED_NOT_RESCORED=01547 sparse 5x3 blind regions; 01548 RGBA versus RGB/sRGB transfer; 01549 same-index pairAbs not binocular feature correspondence; 1204 prepublication frame attribution; 1318 mixed and 1414 ordinary R24 fallback stale receipts (now addressed by later source commits); 01546 incomplete physical native Draw/PMT census. No fresh Quest3 log or retail EXE bytes.
- DISTINCT_AXIS=NEW post-01549 17x11 host `brightCentroidL/R` and `brightDisparity` estimator measures global bright grid points without source-flare identity, even with perfect temporal receipt, exact L/R sample coordinates and sufficient grid coverage. This is NOT another pairAbs, alpha hash, or stale-frame finding.

## NEW_FINDING

NEW_FINDING=STATIC_GLOBAL_RELATIVE_LUMINANCE_THRESHOLD_CAN_EXCLUDE_THE_FLARE_AND_REPORT_ZERO_BRIGHT_DISPARITY_WHILE_ONE_FLARE_FEATURE_HAS_NONZERO_LR_DISPARITY.
ROOT_CAUSE_OF_ACTUAL_DOUBLE_FLARE_HEAD_LOCK_DEPTH=UNPROVEN.

1. The current host expanded `R23ProjectionSamplesX=17`, `Y=11` (187 samples per eye), still 100 ms opt-in; `ScheduleProjection` copies the same normalized 17x11 lattice from each eye's distinct OpenXR projection texture array slice into the staging row (`main_r23.cpp:208-217,1294-1340`). This is more dense than the old 5x3 but still not a lens-object mask or PMT/texture identity.
2. `R23AsyncPixelProbe::ConsumeProjection` converts sampled RGB to luminance using `0.2126*r+0.7152*g+0.0722*b` after optional sRGB linearization; `brightMax[eye]` is the **maximum over every valid sampled pixel**, not over C993/CABE pixels (`:1051-1068`).
3. It selects all samples with `lum >= brightMax[eye]*0.65` and computes the luminance-weighted centroid from their grid coordinates (`:1069-1100`). No per-source lens mask, game sun bearing, local background subtraction, texture/alpha, temporal feature tracking or source-to-native-Draw ID enters this selection. `brightDisparity` is simply right centroid minus left centroid (`:1155-1174`).
4. **Constructive static counterexample (NOT GPU/HMD observation)**: initialize both 17x11 sampled eyes to black. Put a fixed white non-flare sample RGB=(1,1,1) at grid `(ix,iy)=(8,5)` in BOTH eyes. Put exactly ONE pure-red flare-like sample RGB=(1,0,0) in L at `(4,5)` and in R at `(12,5)`. Each eye has exactly one displaced red feature; no same-eye duplicate. For each eye, `brightMax=1`, `threshold=0.65`, white luminance=1 and red luminance=0.2126. The red feature is excluded; `brightCentroidL=brightCentroidR=(0.5,0.5)`, so `brightDisparity=(0,0)`. But the deliberately displaced red feature has L x=5/18, R x=13/18, a true sample-grid x separation of 8/18=0.444444..., which the reported bright disparity entirely misses.
5. **Controlled inverse**: remove only the common white sample. Then `brightMax=0.2126`, `threshold=0.13819`, the one red sample is admitted per eye, and `brightDisparity.x=8/18`. The same flare geometry changes from reported zero to nonzero solely because an unrelated bright sample was present. This is a mathematical property of the current estimator, not an assertion that a real flare is pure red or that a particular HUD/sky pixel is white.
6. Even a full-frame dense grid would retain this *photometric source-selection* ambiguity without an emitter-correlated ROI/mask; the older 01547 spatial sampling limit and 01549 same-index RGB metric issue are separate. Conversely, a zero centroid disparity may be optically correct for a genuinely distant or intentionally fused centre-eye source; this test does not infer physical wrong depth from nonzero displacement.
7. Current R24 fallback receipt repairs may improve `finalSubmissionKnown`, but a correctly tagged fresh projection still does not convert a global brightest-point centroid into a C993/CABE flare centroid. The new metric is a **negative control**, not evidence of an extra 405890 draw, an incorrect c64 or a host eye duplication.

## HYPOTHESIS_LEDGER

| ID | Status / new falsification |
| --- | --- |
| A: extra original D3A5/C993/CABE emitter | OPEN. The centroid does not count original 0x570002/006/00F/010 or 0x570008 ordinal1/2 source calls. Require unexpected original emitter plus matched texture/PMT and extra same-eye successful colour write. |
| B: queue/D3DX/native same-eye duplicate | OPEN_PHYSICAL. A global bright centroid can remain identical with a moving lens lobe; it cannot census 405360 descriptors, 4052C0 flush or 405890 native Draw. Require actual PMT/texture/alpha, source serial, eye RT, HRESULT and same-eye ROI. |
| C: wrong WVP/c64 L/R projected depth | OPEN. A zero brightDisparity does not refute a displaced lens feature. Test original c64/WVP, physical eye RT and source-matched L/R flare centroid. |
| D: intended separate centre/halo/ring | SOURCE_SUPPORTED_CONDITIONAL. Distinct original C993/CABE objects and alpha may intentionally overlap. White non-flare sample control cannot label any as duplicate. Require original material/texture/alpha classification. |
| E: host OpenXR fresh/cached eye reuse | OPEN_RUNTIME. Correctly paired 17x11 arrays and a fresh final receipt do not establish which bright pixels are flares. Compare exact game L/R ROI to host L/R projection ROI and actual submitted fresh/cached views. |
| F: HMD head-lock or angular bearing | OPEN_RUNTIME. A stationary global bright centroid can mask moving flare position; it can also represent a legitimate world-fixed far-field image. Compare emitter ray, game pose epoch, OpenXR view pose/FOV, and identified flare centroid during controlled yaw. |
| G: zero brightDisparity proves no flare disparity/head-lock defect | REFUTED_STATIC_THIS_RUN for the global-threshold estimator; the constructed two-eye red feature moves by 8/18 while reported brightDisparity is zero. |

## SOURCE_TRACE

- PINNED_FOCUS `vrhost/src/main_r23.cpp` blob `c4d40b3cef130088cfd70a7be31aea32af55fc3a`: opt-in/17x11 grid `:208-217`; RGB/sRGB decode `:734-795`; global bright maximum/threshold/centroid `:1051-1100`; emitted `brightCentroidL/R` and `brightDisparity` `:1155-1174`; `ScheduleProjection` per-eye 17x11 copy `:1294-1340`; `R23RenderProjection` actual L/R RTV and `sourceViews` `:1836-1918`; `XR FRAME FULL` final receipt and `XR EYE FULL` fresh/cached pose `:4100-4269`.
- PINNED_FOCUS `src/hooks_graphics.cpp` blob `0d2a6fc2ae87d3e9de90f9be2dfeac67fe458a78`: `DrawObjectAlphaProjected:786-913` two CABE 0x570008 ordinals, alpha/flags/source serial and deferred window; `DrawObjectAlphaCentre:936-1060` C993 four original centre objects; original call forwarding. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` blob `dbee3040e206bd7ef10faa666bb4f63b7ac8b2fe`: `R30TryScreenSpaceFovDraw:5778-5835` warns inline serial is not opaque deferred PMT identity.
- ORIGINAL_SECONDARY=Earlier 40CBC0/40C980/405360/4052C0/405890 reconstruction only, not fresh retail-byte-verified evidence in this run.

## EVIDENCE_GAPS / FALSIFICATION / PATCH_CANDIDATE_ONLY / REGRESSION

- EVIDENCE_GAPS=No fresh user HMD/Quest3 logs or captured flare ROI, no original retail EXE byte verification, no exact 405360 descriptor->4052C0 queue->405890 PMT/texture/alpha->successful L/R RT Draw join, no game versus host same-frame flare pixel map, no verified emitter-specific feature mask, no controlled HMD yaw/source-pose sweep. No proof this particular synthetic RGB pattern occurs in gameplay.
- FALSIFICATION_POSITIVE_STATIC=Evaluate the 17x11 two-eye black+white+red arrays above with the source luminance and threshold formulas; predicted reported brightDisparity=(0,0) despite red feature x separation=8/18. No GPU execution claim.
- FALSIFICATION_NEGATIVE_CONTROL=Remove only the white non-flare point; predicted brightDisparity.x=8/18. If a future trace provides source-labelled flare ROI and the centroid follows that ROI despite brighter unrelated pixels, this specific global-bright-selection failure is not active in that trace.
- PATCH_CANDIDATE_ONLY=Keep raw 17x11 samples and `brightCentroid` explicitly labeled global-bright negative control. For future authorized source implementation, derive separate C993/CABE ROI from emitter world ray + game c64/WVP + eye pose/FOV, and compute feature-matched per-eye local-background-subtracted flare centroids with confidence/mask and raw sample-frame ID; do not reinterpret the global metric as flare depth proof.
- REGRESSION=Retain two intended 0x570008 ordinals, C993 0x570002/006/00F/010, original texture/alpha and R26+HUD baseline; no flare hiding, no B9200 post-CALL/+5 hook; no change to game source, HLSL, CMake, workflow, config, branch, release or package; R84 comparison-only.
- CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY; CI_SKIP=NONE.
- NEXT_REVIEW=LENS_FLARE:JOIN_ORIGINAL_C993_CABE_EMITTER_TEXTURE_ALPHA_AND_405890_PHYSICAL_EYE_RT_TO_DENSE_FRESH_GAME_VS_XR_ROI_THEN_COMPARE_WORLD_SUN_YAW_BEARING_NOT_GLOBAL_BRIGHT_CENTROID.
