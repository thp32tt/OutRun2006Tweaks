# LENSFLARE-R13-FORCED-MONO-R7-ABSENCE-20261030-0022 — R13 mono-shadow native draw without R7 eye receipt (REVIEW_ONLY)

DATE=2026-10-30 KST
RUN_KEY=LENSFLARE-R13-FORCED-MONO-R7-ABSENCE-20261030-0022
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=388e79d625ba5093159da49bd404256b0e0d7c32
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
REVIEW_SCOPE=LENS_FLARE_ONLY
DX9EX_REVIEW_ONLY=ON
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE

## Inherited evidence / distinct test

Prior 01577-01580 established that PMT invocation, pass fan-out, native PRE-DIP, right-failure sentinel and exact retail field labels are not proof of same-eye colour. 01581 established a different false positive: **when R7 executes**, its SINGLE routes can report `leftAttempted=1` for an original mono/offscreen/fallback draw without an authenticated left eye. Earlier LENSFLARE-R26-LOWER-OWNER-20261027-2042 established the R26/R23 lower owner and missing R30 scope; LENSFLARE-ZENABLE-TWO-ORDINAL-CONTROL-20261028-0725 established original depth-off CABE and inherited R13 zero-disparity policy. This run does **not** re-score those results.

DISTINCT_TEST=Does a successful original D3D9 physical Draw exist on the R13 forced-mono / unsafe fallback branch **without entering R9/R7 at all**, making `R7TraceVisualEyes` absence a false negative for physical drawing? Inspect actual hook trampoline choice, private mono RT binding, fallback conditions and Present restoration. This is the complementary **no-R7-receipt** counterexample, not 01581's positive but misleading R7 SINGLE receipt.

## NEW_FINDING — source-static conditional negative control, not proven headset defect

NEW_FINDING=R13_FORCED_MONO_SHADOW_EXECUTES_ORIGINAL_D3D9_DRAW_DIRECTLY_ON_R9_MONO_SURFACE_AND_BYPASSES_R9_R7_EYE_LOGGING;_UNSAFE_MONO_RESOURCE_FAILURE_CAN_EXECUTE_ORIGINAL_DRAW_ON_REAL_TARGET_WITHOUT_R7_EYE_LOG;_NO_R7_RECEIPT_IS_NOT_A_NEGATIVE_PHYSICAL_DRAW_PROOF_FOR_THIS_ROUTE.

1. `src/vr/d3d9/stereo_renderer_r13.cpp::R13GuardedDraw:595-652` calls `ClassifyDrawReplay` with main-target, `R13ForceMonoShadow`, stereo seed and MRT/query state. On `ForcedMonoShadow` it returns `R13DrawMonoShadowOnce(device, actualDraw, site)`, **not** `legacyDraw()`. On `UnsafeSingleExecution` it poisons the frame, sets `R13ForceMonoShadow=true` if `R9MonoSeeded && !R9MonoBackupGap && R9CurrentDepthCanMirror()`, then also calls `R13DrawMonoShadowOnce`. If mono history is unusable, it calls `actualDraw()` once on the real target and marks the gap.
2. `::DrawIndexedPrimitiveDestR13:665-682` defines `actual` as `DrawIndexedPrimitiveHook.stdcall<HRESULT>(...)` and `legacy` as `R13DrawIndexedPrimitiveR9Hook.stdcall<HRESULT>(...)`. The same direct-vs-R9 distinction holds for `DrawPrimitive` :655-663 and both UP variants :685-715. The R13 install hook explicitly wraps `DrawIndexedPrimitiveDestR9` at :794-815. Therefore the forced-mono `actual` route bypasses R9 and its R7 descendant, while the legacy route can enter R9/R7. This is a conditional control-flow proof, not runtime occurrence.
3. `::R13DrawMonoShadowOnce:467-505` calls `R9BindMonoTarget`, executes `actualDraw()` exactly once while bound to the mono target, restores the game RT/depth/viewport, and increments mono backup counters on success. If binding fails, it poisons and returns `actualDraw()` on the existing target; if the draw or restore fails, it marks a mono backup gap. None of these branches calls `R7TraceVisualEyes`.
4. `src/vr/d3d9/stereo_renderer.cpp::R9BindMonoTarget:301-326` binds private `R9MonoSurface` and mono depth; `::R9RestoreGameTarget:328-337` restores game targets. `::R9RestoreMonoBeforePresent:403-416` can later copy mono surface to game backbuffer, while `::PresentDestR9:826-846` restores a usable mono shadow if no complete SBS stereo frame exists. Thus a physical native colour contribution to the mono backup is not by itself an accepted left/right XR eye or evidence of an extra visible flare.
5. `src/vr/d3d9/vr_pass_policy.hpp::ClassifyDrawReplay:207-221` proves the conditional classification: forceMonoShadow takes precedence; unsafe transition requires stereoWanted, stereoSeeded and MRT/query hazard. `src/vr/d3d9/stereo_renderer_r13.cpp::PresentDestR13:733-749` resets `R13ForceMonoShadow` after game Present. `src/vr/d3d9/stereo_renderer_r26.cpp::R27GuardWorldEffect:638-709` can delegate to legacy R13 when strict world/WVP/depth conditions are not proved; `::R26GuardTrackedOcclusion:387-428` separately bypasses lower layers for proven write-free query-only draws. `stereo_renderer_r30_r26_safe.cpp:12` includes R26, so these paths belong to the R26+HUD source chain, but actual installed/selected lens route is NOT observed.
6. Bounded counterexample: if an authenticated 405890->404700 `pmtEntrySerial>0` is active during a main-target CABE primitive and `R13ForceMonoShadow=true` with usable mono resources, an original native `DrawIndexedPrimitive` can run once against `R9MonoSurface` with **no R7 VISUAL EYES FULL receipt at all**. The lack of R7 record cannot falsify a physical draw or establish zero same-eye colour. This counterexample is not evidence that CABE 0x570008 actually hit forced mono in the user's Quest3 run.

## HYPOTHESIS_LEDGER

| ID | Status | Independent discriminator |
| --- | --- | --- |
| A extra original D3A5/C993/CABE emitter | OPEN | Two 570008 ordinals are original; prove an unexpected source serial/405360 descriptor and same-eye colour delta. R13 absence cannot establish missing emitter. |
| B queue/D3DX/native same-eye duplication | OPEN | A direct R13 mono shadow Draw is neither an R7 L/R pair nor a same-eye double write. Count exact descriptor+pass+primitive+material+API+target RT+successful colour writes; include R13 bypass paths. |
| C wrong WVP/c64 or eye depth | OPEN_RUNTIME | R13 mono fallback may keep original transform, but does not prove that the affected CABE took it. Compare actual R13 policy, WVP/c64, RT and accepted eye pose/FOV. |
| D intended alpha/material overlap | OPEN | Original 570008 ordinal1/2 and pass0/1 may be legitimate. Match second visible lobe to PMT texture, blend, alpha, colour mask and RGB ROI, not R7 receipt count. |
| E R19 fresh/cached source and R24 accepted OpenXR projection | OPEN_RUNTIME | Mono backup can be restored before Present; R13/R9 source trace alone does not identify R19 selected image or R24 accepted XR frame. Join actual source frame, UV, L/R image and final accepted pose/FOV. |
| F head-lock / directional sun | OPEN_RUNTIME | No two-yaw Quest3 frame or accepted-eye angular centroid. Original mono/fallback geometry may be correct failure output; do not infer root cause from route possibility. |
| G no R7 VISUAL EYES FULL => no native physical Draw | REFUTED_AS_GENERAL_INFERENCE | R13 forced-mono `actualDraw` bypasses R9/R7; binding failure also calls `actualDraw`. Conditional source proof, not measured lens incidence. |
| H observed doubled second lobe is caused by R13 mono shadow | UNPROVEN | Requires exact CABE PMT material/texture/alpha -> R13 decision -> RT RGB -> mono restoration -> accepted XR two-yaw evidence. |

## SOURCE_TRACE

- Pinned mod source `388e79d625ba5093159da49bd404256b0e0d7c32`:
  - `src/vr/d3d9/stereo_renderer_r13.cpp` blob `4e01217e5e1d9e2b136501a0c28efadfefdc0094`: `R13DrawMonoShadowOnce:467-505`, `R13GuardedDraw:595-652`, `Draw*DestR13:655-715`, `PresentDestR13:733-749`, hook installation :790-820.
  - `src/vr/d3d9/stereo_renderer.cpp`: `R9BindMonoTarget:301-326`, `R9RestoreGameTarget:328-337`, `R9RestoreMonoBeforePresent:403-416`, `R9ExecuteDraw:615-707`, `PresentDestR9:826-846`.
  - `src/vr/d3d9/vr_pass_policy.hpp` blob `54e6a2cad3c2f60853fc74a72865148df1cf4690`: `ClassifyDrawReplay:207-221`.
  - `src/vr/d3d9/stereo_renderer_r26.cpp` blob `4e486a14c0f180928732419868f5449b6d8759cf`: `R26GuardTrackedOcclusion:387-428`, `R27GuardWorldEffect:638-709`.
  - `src/vr/d3d9/stereo_renderer_r7.inc` blob `3fe94325528650ac0c1599cef498eab946edf78f`: `R7TraceVisualEyes:1644-1717`, `ExecuteStereoDraw:1719-1913`. R7 emits only when that function is entered; this review proves a distinct R13 direct path.
- Original emitter 0x570002/006/00F/010 and 0x570008, original 4056D0/4052C0/405890, PMT/texture/alpha and R19/R24 are inherited context from 01577-01581 and prior lens records, **not reauthenticated or observed** in this run. Original retail EXE byte read, runtime HMD, GPU RGB readback and accepted XR are absent.

## EVIDENCE_GAPS / FALSIFICATION

EVIDENCE_GAPS=No observed CABE 0x570008 or C993 PMT event on R13 forced-mono; no live `R13ForceMonoShadow`, `R9MonoSurface`, original RT, pass/material/texture/alpha, per-eye RGB delta, R19 selected fresh/cached source, R24 accepted XR pose/FOV or Quest3 two-yaw capture. Source route may never be reached by the reported lobe. Source-static bypass is not a proven headset cause.

FALSIFICATION=On a separately authorized future diagnostic run, correlate exact PMT invocation/primitive with R26/R23/R27->R13 policy, `R13ForceMonoShadow`, `R9MonoSeeded`, `R9MonoBackupGap`, `R9BindMonoTarget` result, actual native Draw HRESULT and entry/draw/restore RT. Compare R7 receipt presence **only after establishing whether R13 chose legacy R9 or direct actual**. If affected PMT always takes R30 accepted eye path or R13 Legacy with a complete R7 receipt, reject forced-mono as its explanation. If direct mono occurs, test whether its RGB reaches final accepted XR; do not assume it did. Use two yaw poses and a non-lens draw as negative controls. If same-eye RGB has two identical material writes before transport, prioritize A/B/D; if one native lobe becomes two only after R19/R24, prioritize E; if count preserved but head-relative bearing wrong, prioritize C/F.

PATCH_CANDIDATE_ONLY=NOT_APPLIED. For separately authorized instrumentation, add a bounded `R13GuardedDraw` decision/RT receipt with per-native-primitive ID and `R9BindMonoTarget`/restore result, joined to authenticated PMT serial and R30/R7/host accepted XR. Preserve original draw count, R26 query single-exec, depth/alpha, both CABE ordinals and R26+HUD default; no B9200 post-CALL/+5 hook.
REGRESSION=DOCS_ONLY_NONE; future instrumentation must avoid D3D9 render-thread latency, nested hook recursion, false PMT ownership, altered mono fallback and XR frame timing.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:R13_FORCED_MONO_DIRECT_NATIVE_RT_RECEIPT_VS_570008_EXACT_PMT_TO_R19_R24_ACCEPTED_XR_TWO_YAW
