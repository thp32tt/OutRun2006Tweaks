# CONVERSION-DX9EX-01588 — R26+HUD lens lower-hook target identity versus misleading R29 fallback receipts (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01588
PRODUCTION_ID=CONVERSION-DX9EX-01588
EVENT_ID=CONVERSION-DX9EX-01588-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=acfd2987f2d21a742805613e30b5dc2d8b0d38ef
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED
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

## Narrow independent falsification — what does R30's `r29Draw()` *really* call in default R26+HUD?

The preceding 01585-01587 reviews trace the 0x570008 CABE deferred opaque-PMT/405890→404700 lens path, distinct C993 centre emitters, limited R30 physical receipts, and the conditional raw native LEFT `E_NOTIMPL` collision with clean pre-LEFT rejection. Their remaining lens multiplicity/eye/host hypotheses are **not** retested in hardware here. This review changes the evidence boundary from *R30 HRESULT* to **compiled translation unit + inline-hook target**, because the phrase `resultRoute=R29_FALLBACK` was being treated as a concrete next renderer. Static result below constrains that inference without modifying any draw code.

NEW_FINDING=STATIC_DEFAULT_R26_HUD_R30_NAMED_R29_LOWER_HOOK_TARGETS_R26_NOT_R29_FOR_ALL_FOUR_NATIVE_APIS;_R30_R29_FALLBACK_LOG_IS_A_NOMINAL_LABEL_NOT_A_PROOF_OF_EXECUTED_R29;_R26_CAN_TAKE_WRITE_FREE_SINGLE_OR_FORWARD_TO_R23;_BASELINE_HAS_SAME_R26_HOOK_TARGET;_ACTUAL_570008_LENS_PATH_AND_VISIBLE_DUPLICATE_REMAIN_UNPROVEN.

### SOURCE_TRACE — exact connected GitHub source, current SOURCE_HEAD (1-based lines)

1. **Build ownership:** `CMakeLists.txt:95-108,218-244` establishes default `OUTRUN_VR_R26_HUD_DEFAULT ON` for a fresh option-free configuration and selects `stereo_renderer_r30_r26_safe.cpp` as the compiled stereo TU when `OUTRUN_VR_R26_HUD_COMPARE=ON`, while `stereo_renderer_r33.cpp` is HEADER_FILE_ONLY. Explicit compare options / an existing CMake cache may differ; this review does **not** attest which binary the Quest3 ran. In `stereo_renderer_r30_r26_safe.cpp:14` the textual implementation include is `stereo_renderer_r26.cpp`, **not** `stereo_renderer_r29.cpp`.
2. **Exact hook target, four APIs:** `stereo_renderer_r30_r26_safe.cpp:8671-8716`, notably :8696-8707: misleadingly named `R30Draw{Primitive,IndexedPrimitive,PrimitiveUP,IndexedPrimitiveUP}R29Hook` are each installed by `safetyhook::create_inline` on corresponding `Draw*DestR26` symbols. This is a source-level hook target identity, not a guess from a log or function variable spelling. Its `r29` lambdas call these handles at :8409-8425 (DP), :8508-8525 (DIP), :8560-8578 (DPUP), :8621-8639 (DIPUP).
3. **Delegation and evidence-label mismatch:** `stereo_renderer_r30_r26_safe.cpp:7379-7440,7480-7520` calls `R30TryScreenSpaceFovDraw`, then, **iff** `hr == E_NOTIMPL`, executes `r29Draw()` at :7434. The lower generic receipt writes `resultRoute=R29_FALLBACK` and `reason=R30_NOT_ADMITTED` despite the R26 hook target. The latter is also semantically incomplete for 01587's conditional post-LEFT native `E_NOTIMPL` collision: that native LEFT was attempted, then R30 may return raw `leftHr` (:6844-6848, :6930-6935), yet Guard labels the delegated branch `R30_NOT_ADMITTED`. The receipt proves entry/return from a delegated call, **not** exact R29 execution, exact physical eye count, or source-eye colour.
4. **What the lower hook actually does:** `stereo_renderer_r26.cpp:777-842` names each `Draw*DestR26`, forwards to `R26GuardTrackedOcclusion`. At :388-425, when there is no qualifying proven write-free active-query proxy it delegates once to the saved `R23` handler; in a special write-free tracked-query proxy it calls the original `actualDraw()` once. Neither conditional proves which branch an actual 0x570008 lens takes. Once forwarded, subsequent R23/R22/R13/R9 outcomes require a separate matched source/primitive/eye trace; do not substitute R29 fast-path counters.
5. **Why R84 comparisons are different:** `src/vr/d3d9/stereo_renderer_r30.cpp:17-19,8694-8713` is a *different* R30 implementation which includes `stereo_renderer_r29.cpp` in its default textual build chain and installs R30 draw hooks using `R29OwnerDraw*Target()`. Do not transpose that R84/nondefault hook identity onto R26+HUD merely because both variants call a lambda `r29`.
6. **Protected source baseline:** `stereo_renderer_r30_r26_safe.cpp@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9:14,5355-5376` already includes R26 and installs R30's named `R29Hook` on `Draw*DestR26`. The nominal-name/target mismatch is therefore inherited from the immutable HMD baseline, **not** proven to be a newly introduced visible defect.

### Falsification matrix — conditional code paths, NOT physical lens observations

| R30 boundary / exact compiled lane | Actual lower route | Predicted discriminator | Inference forbidden |
| --- | --- | --- | --- |
| R26+HUD: R30 EARLY `E_NOTIMPL`, before native LEFT | Named `r29Draw()` -> R26 `Draw*DestR26` | R30 LEFT attempted=0; R26 normal->R23 or eligible occlusion write-free single | “R29 stereo replay happened” from `R29_FALLBACK`; extra game-origin halo |
| R26+HUD: raw original LEFT failed with `E_NOTIMPL` | R30 failure poisons/arms fallback (:6930-6935), then Guard -> R26 | R30 LEFT attempted=1, failed LEFT HRESULT 0x80004001, one R26 hook entry; correlate actual R23/R9 subsequent physical attempts | Successful RGB double write from two calls; R29 fast path (not this compiled TU) |
| R26+HUD: R30 LEFT failed with non-`E_NOTIMPL` | Guard returns raw failure; no R26 delegate **through this Guard** | LEFT attempt=1; no `R30_NOT_ADMITTED` lower receipt for that entry | No other lens draw elsewhere in frame |
| R26+HUD: admitted R30 LEFT success, RIGHT failed | R30 returns successful `leftHr` (01587); no Guard lower | RIGHT failure/poison and incomplete frame; no `r29Draw()` from this Guard | Right-eye success or correct accepted XR image |
| R26+HUD: R26 write-free occlusion-special case | R26 calls original actual draw once | Query-only/write-free proof required at R26 guard | This case actually applies to halo or centre without matched query/state |
| Explicit R84/nondefault `stereo_renderer_r30.cpp` | R29-owner-target hook; distinct compiled path | Compare CMake options, exact binary fingerprint and target pointer first | Generalizing R26+HUD R26 identity to R84 |

**Important evidence discipline:** R30 `R29_FALLBACK` telemetry's pre-delegate `rt0`/`tex0` snapshot and post-delegate `lowerHr` cannot enumerate actual downstream draw attempts, L/R RT writes, or host/XR submission. Two intended L/R calls do not themselves constitute a defect. This result corrects lower-route attribution; it does not prove lens double emission, pixel duplication, head-lock, or a valid R26/R84 performance/optics comparison.

## HYPOTHESIS_LEDGER

| ID / lens-specific hypothesis | State | Prior evidence → **new** evidence | Falsifier / next exact condition |
| --- | --- | --- | --- |
| A unintended extra game emitter/0x570008 source object | OPEN | 01585-01587 inherit two CABE 0x570008 calls, four C993 center IDs. New lower-hook identity does not add another emitter call. | Same-frame verified original emitter ordinal/ID/texture count versus physical primitive fingerprint proves an unplanned third source object. |
| B0 the label `R29_FALLBACK` proves R29 hot-path replay for default R26+HUD lens | REFUTED_STATIC | Prior 01586/01587 use “R29 lower” terminology. Current CMake :230-244 + safe TU :8696-8707 + baseline :5362-5374 identify actual R26 hook; R84 has different target owner. | A matching **option-free R26+HUD** linked binary/ABI proof resolving the hook target to R29 instead of `Draw*DestR26`, contrary to inspected source; verify exact package/config. |
| B1 native LEFT `E_NOTIMPL` may cause lower delegate after an attempted draw | SUPPORTED_CONDITIONAL_STATIC_INHERITED | 01587 established raw HRESULT collision. This audit narrows the actual delegate target to **R26** in default lane, not R29. | Exact native HRESULT never equals E_NOTIMPL on this physical lens, or verified binary maps failure to a distinct sentinel before Guard. |
| B2 two successful colour writes into **the same eye** caused by conditional lower route | BLOCKED | New trace names R26->conditional R23/single; no observed source-linked lower branch, RT RGB or accepted XR frame. | Count successful per-eye native RT ROI deltas keyed by one producer/PMT pass/texture and same top-level hook entry, excluding intended L/R pair and separate original halo materials. |
| C CABE deferred semantic / C993 projected center follows different stereo transforms | SUPPORTED_CONDITIONAL_STATIC_INHERITED | 01585 wrapper lifetime divergence; 01586 PMT/generic versus scope-specific logs. New target identity changes *lower-route attribution* only, not source ownership. | Same native drawing identity, verified effective scope and per-eye WVP/FOV/RT centroid under two headset yaws; compare centre vs halo separately. |
| D separate normal center/halo/rays/ghost pass resembles an erroneous duplicate | OPEN | Known multiple intended lens sources; neither R30 nor R26 hook identity proves unwanted extra source material. | Exact texture0, alpha/blend, primitive fingerprint and per-eye ROI for each original object. |
| E host composite/cached ViewSpace layer repeats or headlocks flare | OPEN_RUNTIME | Prior R19/R24 pending host join; new source-gate result is entirely pre-host. | One correct single native lens ROI per eye vs two/flat in the actual accepted XR frame with matching source frame/QPC, layer type and pose. |
| F HMD-local source-bearing or projection mismatch | OPEN_RUNTIME | User reports split and head-follow; no new matched 2-yaw pose or HMD acceptance. | Per-eye native+accepted XR centroid and source world/light bearing at two known yaws with exact pose/FOV/source tick. |

## EVIDENCE / EVIDENCE_GAPS

EVIDENCE_SOURCE=PINNED_GITHUB_CURRENT: `CMakeLists.txt` blob `389bb4f88304321a368c6da4d43907799fa43e2c`; `stereo_renderer_r30_r26_safe.cpp` blob `6827f864b966ca743dff35725cc9ad9c9e96cc3b`; `stereo_renderer_r26.cpp` blob `4e486a14c0f180928732419868f5449b6d8759cf`; comparison `stereo_renderer_r30.cpp` blob `9f60b273882a816b8e21b854f319161f06c70e33`; protected-baseline safe TU blob `0525d1cf53393902b5415bcb139cb55286673aaa`. Prior 01585/01586/01587 files and `AGENTS.md` override + `docs/DX9EX_OPTICAL_ROUTE_PROBE_POLICY_20261020.md` + `docs/automation/OUTRUN_VR_REA_RESOURCE_EVIDENCE_20261018.md` consulted.
EVIDENCE_DISASM=INHERITED_ONLY: prior 0x570008/C993 and original 405890/404700 mapping from repository REA/reviews; no EXE binary or new Ghidra/disassembly execution; original PMT field-offset verifier gap remains.
EVIDENCE_LOG=NONE_NEW: no same-SHA D3D9 native HRESULT or authentic flare PMT/RT/host acceptance capture; source string `R29_FALLBACK` is not a runtime sample in this task.
EVIDENCE_USER_REPORT=USER_OBSERVED_DOUBLE_SPLIT_AND_HEAD_FOLLOW; exact current source/Quest3 reproduction unverified.
EVIDENCE_GAPS=Exact installed build CMake cache and hooked function address; whether any target flare takes R30 early/post-LEFT failure; actual R26 tracked-query branch or R23/R13/R9 native calls; source 0x570008 opaque PMT ledger field authority and centre C993 distinction; per-eye colour ROI and primitive/texture/RT identities; R19 source image and R24 accepted XR layer/pose; 2-yaw Quest3/VDXR lens behaviour. This is a compile/dispatch source proof, not a linked-binary hook readback or HMD observation.

## NEXT_FALSIFICATION_TEST — disprove “named R29 lower equals executed R29 pair”

1. In a separately authorized bounded diagnostic capture, record the exact binary/SHA, CMake `OUTRUN_VR_R26_HUD_COMPARE`, hook destination address / symbol identity for all four D3D9 Draw variants, and R30 upper hook entry (not the potentially misleading lambda name). Preserve both original CABE 0x570008 ordinal1/ordinal2 and C993 central IDs.
2. Join one **authenticated** lens material and PMT original CALL/queue epoch + `pmtEntrySerial` + texture0/pass/blend → top-level DP/DIP/DPUP/DIPUP ID → R30 admission/leftAttempted/leftHr → **actual R26GuardTrackedOcclusion branch** (normal R23 vs proven write-free single) → subsequent R23/R13/R9 physical LEFT/RIGHT attempt/HRESULT/RT → RGB ROI, then R19 source QPC/frame and R24 accepted XR layer/pose. Do not treat a deferred CABE window as exact PMT ownership.
3. POSITIVE_CONTROL: fresh-cache default R26+HUD + R30 pre-LEFT `E_NOTIMPL` must enter the R26 target and then an actually observed R26 branch; `R29_FALLBACK` string may appear but **cannot** count an R29 fast pair. NEGATIVE_CONTROL: explicitly selected R84 with confirmed separate `stereo_renderer_r30.cpp` must resolve its R29 owner-target route separately.
4. SENTINEL_CONTROL: if original LEFT returns `E_NOTIMPL`, R30 leftAttempted=1 and frame poisoned before any R26 delegate; if returns another failed HRESULT, Guard must not delegate. These are **conditional** probes; a forced fake HRESULT is not evidence of real-game pixels.
5. PIXEL/HOST_CONTROL: two different eye RT writes for one authentic material are expected stereo, not a duplicated flare. Two unexplained successful same-eye colour ROI writes implicate lower/queue B; one native-eye lobe but two accepted XR lobes implicates host E; correct per-eye count but incorrect bearing or yaw implicates C/F; different original textures implicate D. No pass/fail from counters alone.

NEXT_FALSIFICATION_TEST=AUTHENTIC_CABE_570008_PMT_TO_R30_E_NOTIMPL_TO_ACTUAL_R26_QUERY_SINGLE_VS_R23_CHAIN_PHYSICAL_LR_RT_RGB_AND_R19_R24_ACCEPTED_XR_TWO_YAW
PATCH_CANDIDATE_ONLY=DIAGNOSTIC_NAMING_ONLY_NOT_APPLIED: If future exact-source/linked-build validation confirms that the R26+HUD `R29_FALLBACK` receipt is actively misdirecting a lens-specific investigation, a *separately authorized* minimal change in `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:7379-7520,8409-8425,8508-8525,8560-8578,8621-8639,8671-8716` could report `compiledLower=R26` and `entryReason=PRE_LEFT_REJECT|POST_LEFT_NATIVE_ERROR` (plus exact raw HRESULT) without modifying routing, replay, transforms, state, eye pass or restores. Prioritize binary/static cross-check first; changing log labels alone **cannot** cure a visible flare. Falsifier: an exact compiled binary proves the lower target is R29 in a default R26+HUD build, or source-matched proof shows these labels are never used to classify lens failures. No production edit in this job.
REGRESSION_RISK=DOCS_ONLY_NONE; any later telemetry modification risks hot-path overhead or false authority from inferred hook names. Any subsequent optical source change must preserve native single draw safety, both intended source halo layers, legitimate distinct L/R eye renders, RT/depth/WVP restore, R26+HUD baseline, R84 nondefault, avoid B9200 post-CALL/+5 and pass exact-source Quest3/VDXR visual evidence.
NEXT_REVIEW=LENS_FLARE:R30_DEFAULT_R26_HUD_R26_LOWER_TRAMPOLINE_R23_VS_WRITEFREE_SINGLE_NATIVE_EYE_RT_AND_ACCEPTED_XR_JOIN
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01588.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01588]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01588.md
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
