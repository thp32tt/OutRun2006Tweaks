# LENSFLARE-DEFERRED-PROMOTION-ADMISSION-GATE-20261030-0216 — deferred CABE classifier promotion versus R30 physical admission (REVIEW_ONLY)

DATE=2026-10-30 KST
RUN_KEY=LENSFLARE-DEFERRED-PROMOTION-ADMISSION-GATE-20261030-0216
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=342e080dcb9b652b37dcdcbad6b73aebd7d46a5f
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
REVIEW_SCOPE=LENS_FLARE_ONLY
DX9EX_REVIEW_ONLY=ON
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY

## NEW_FINDING — classifier-only deferred ray promotion is blocked by independent physical scope admission

NEW_FINDING=STATIC_CONDITIONAL_R30_DEFERRED_SCENEEFFECT_FLATHUD_PROMOTION_TO_PROJECTED_CLASS_CANNOT_REACH_R85_EYE_WVP_WHILE_EFFECTIVE_SCOPE_REMAINS_SCENEEFFECT;_R30_REJECTS_E_NOTIMPL_AND_DISPATCHES_R29_LOWER_PATH;_QUEST3_SPLIT_COMMENT_IS_NOT_PROOF_OF_R85_PROJECTED_NATIVE_DRAW.

This is a *new cross-commit falsification* of a specific attempted 2026-10-30 CABE optical remedy, NOT a claim that the Quest 3 observation is false and NOT a root-cause verdict. It does not re-credit the prior original multi-object opaque queue, R85 class/producer guards, or R13/R24 fallback findings.

1. The experimental commit `8b9645073d9cf81adfa6f07d232f021645209ad8` changed only the `R30ClassifyScreenSpacePass` `semanticSceneEffect && matrixKind==FlatHud` branch: when diagnostic `CurrentLensDeferredPhysical` carried ordinal1 `0x570008`, it returned `ProjectedScreenEffect2D` instead of `PerspectiveHud`. It did **not** set `CurrentScope`, `CurrentQueueExactScope`, or `EffectiveScope` to projected, and the receipt itself is documented as diagnostic-only.
2. The same experimental SHA still had the independent downstream `R30TryScreenSpaceFovDraw` admission check: when `screenKind==ProjectedScreenEffect2D`, `semanticScope=EffectiveScope()` MUST equal `RenderScope::ProjectedScreenEffect2D`, otherwise it returns `E_NOTIMPL` before `R30BuildScreenSpaceEyeConstants`, before any R85 projected-ray WVP and before native L/R R30 Draw. Current HEAD retains this exact gate. Therefore for the *specific SceneEffect/FlatHud branch* changed by 8b964, while its physical effective scope remains SceneEffect, the experiment cannot directly execute an R85 projected native eye draw.
3. `R30GuardScreenSpace` treats that `E_NOTIMPL` as a lower-owner fallback and calls `r29Draw()`; its log says `reason=R30_NOT_ADMITTED` and `lowerActualDraw=NOT_YET_OBSERVED`. The lower R29/R26/R13/R7 route can be materially different from R30 finite PerspectiveHud handling. The experimental classifier change may therefore alter route selection *through rejection/fallback*, not necessarily through an R85 per-eye matrix. The actual lower route and pixels remain unobserved.
4. The later commit `bc825df81454da148381c64c9e45e1b30db3d0b3` reverted the classifier promotion, retaining `PerspectiveHud`. Its source comment says a Quest3 test split the flare into two binocular images. That is a **developer source comment about a test**, not an independently available frame/PMT/RT/HMD log in this review. It cannot establish that the attempted change reached R85, or identify the split's optical cause. It is compatible with the newly proved admission rejection and a changed lower fallback.
5. Current `render_semantics.hpp::UsesLogicalUiCanvas` expressly excludes `ProjectedScreenEffect2D` and `SceneEffect`; 2026-10-30 virtual HUD canvas changes are not a demonstrated lens depth fix. This is a negative control only, not a new scoring item.
6. Original D3A5/C993 `0x570002/006/00F/010` and CABE `0x570008` remain separate source families. The ordinal1 deferred time-window is not authenticated PMT/texture/alpha ownership; the original D79B multi-object queue and second 542A inline/flush boundary remain predecessor evidence. This finding is conditional on the affected *physical* draw having SceneEffect scope and FlatHud classification; a physical draw with a separately owned projected scope is **not** excluded from R85.

## HYPOTHESIS_LEDGER

| Axis | Status / falsification |
| --- | --- |
| A extra original emitter | OPEN; classifier change adds no original CABE/C993 call; require exact 405360 source and 405890 PMT node/texture. |
| B duplicate native same-eye draw | OPEN; an R30 rejection may route to R29, but is not an extra draw. Need exact API/RT/HRESULT and RGB writes. |
| C wrong WVP/c64/eye depth | NEW_STATIC_NEGATIVE_CONTROL; experimental SceneEffect/FlatHud promotion cannot *by itself* produce R85 projected L/R WVP. If same effective scope persists, compare R29 lower eye matrices rather than claiming R85 executed. |
| D original alpha/material layers | OPEN; first/second CABE and C993 material/texture/alpha/PMT identity not proven. |
| E R19/R24 host fresh/cached/quad | OPEN; downstream R24 fallback can flatten stereo independently; no accepted final frame joined. |
| F head-lock/bearing | OPEN_RUNTIME; no Quest3 two-yaw matched final eye evidence. |
| G experimental classifier promotion guarantees projected R85 physical draw | REFUTED_CONDITIONALLY for SceneEffect/FlatHud with unchanged EffectiveScope; explicit R30 gate rejects. |
| H reported split definitively caused by R85 or R29 | UNPROVEN; rollback comment lacks joined native/host optical receipts. |

## SOURCE_TRACE

- `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` current HEAD `342e080dcb9b652b37dcdcbad6b73aebd7d46a5f`: `R30ClassifyScreenSpacePass` :2330-2420 (semanticProjectedScreen priority and SceneEffect/FlatHud => PerspectiveHud), `R30TryScreenSpaceFovDraw` :6275-6287, :6648-6684 (exact projected-scope gate), :6705-6735 (pose and eye-WVP builder reached only after gate), `R30GuardScreenSpace` :7378-7445 (E_NOTIMPL => R29 lower fallback).
- Experimental `8b9645073d9cf81adfa6f07d232f021645209ad8`: classifier hunk around :2403-2449; its own `R30TryScreenSpaceFovDraw` projected admission gate around :6700-6708 remained present. Source-diff verified directly through GitHub.
- Rollback `bc825df81454da148381c64c9e45e1b30db3d0b3`: removes classifier-only promotion; source comment records a reported Quest3 split, not independently verified HMD evidence.
- `src/vr/game/render_semantics.hpp` :882-894 and :996-1005 diagnostic deferred receipt, :1204-1233 projected semantic and logical-UI exclusions; `src/hooks_graphics.cpp` :1160-1320 C993 source/queue and exact original hooks.
- Inherited only, not rescored: `LENSFLARE-DEFERRED-QUEUE-COLLISION-20261028-0937.md`, `LENSFLARE-R85-CABE-PROJECTION-EXPANSION-20261029-0110.md`, `CONVERSION-DX9EX-01580.md`, `CONVERSION-DX9EX-01581.md`, `CONVERSION-DX9EX-01582.md`, `CONVERSION-DX9EX-01583.md`.
- EVIDENCE_SOURCE=CONNECTED_GITHUB_SOURCE_AND_COMMIT_DIFF; EVIDENCE_RETAIL_EXE=INHERITED_NOT_REVALIDATED; EVIDENCE_HMD=NONE_THIS_RUN; EVIDENCE_PIXEL=NONE; EVIDENCE_RUNTIME=NONE_THIS_RUN.

## EVIDENCE_GAPS / FALSIFICATION

EVIDENCE_GAPS=No same-PMT original object/texture/alpha, current SceneEffect/FlatHud actual admission or lower-route receipt, pre/post native L/R RT RGB, sourceFrameId and R19 fresh/cached UV, post-R24 accepted projection/quad/pose/FOV, or Quest3 two-yaw frame. The rollback comment's runtime assertion is not a substituted test log.

FALSIFICATION=For an authenticated ordinal1 `0x570008` PMT at original D79B flush, record `EffectiveScope`, `R30ClassifyScreenSpacePass`, `R30TryScreenSpaceFovDraw` admission, `R30GuardScreenSpace` fallback, R29/R26/R13/R7 actual native Draw and RT, and eye WVP/c64. If the effective scope is SceneEffect and class was promoted to ProjectedScreenEffect2D in the experimental version, expect R30 E_NOTIMPL and R29 fallback, not R85 eye WVP. If an independently authenticated projected scope exists, this conditional negative control does not apply. Compare the rolled-back current version under identical source/pose with R30 finite PerspectiveHud and lower-route receipt. Then join per-eye RGB to R19 source fresh/cached and R24 actual final layer at two HMD yaw angles; missing joins => UNTESTED.

PATCH_CANDIDATE_ONLY=NOT_APPLIED: future separately authorized, bounded *diagnostic* receipt at R30 class/admission/fallback with physical PMT and eye RT, rather than granting deferred ordinal1 render ownership. Do not reintroduce blanket projected promotion or change alpha, source calls, B9200 hooks, protected baseline, R84, R19/R24 or game renderer during REVIEW_ONLY.
REGRESSION=DOCS_ONLY_NONE; future runtime work risks multi-object queue scope contamination, altered R29/R13 fallback, unintended eye depth, HMD frame pacing and protected R26+HUD.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:CABE_570008_ORDINAL1_SCENEEFFECT_FLATHUD_R30_E_NOTIMPL_R29_FALLBACK_PMT_TEXTURE_ALPHA_TO_LR_RGB_R24_ACTUAL_TWO_YAW
