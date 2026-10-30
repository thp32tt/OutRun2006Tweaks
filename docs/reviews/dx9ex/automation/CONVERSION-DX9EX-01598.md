# CONVERSION-DX9EX-01598 — projected C993 raw-c64 miss: R30-to-R29 physical-route negative control (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01598
PRODUCTION_ID=CONVERSION-DX9EX-01598
EVENT_ID=CONVERSION-DX9EX-01598-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=b29590667eb7c3eced31ccd7f63669f67b235e55
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED;_HEAD_RECHECKED_BEFORE_COMMIT
MODE=DX9EX_REVIEW_ONLY
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
RUNTIME_VALIDATION=UNTESTED
ROOT_CAUSE=UNCONFIRMED
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_AB_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN

## Narrow, different question from 01596/01597

01596 derived a *conditional* same-shader other-object original-WVP admission when a **complete valid** game c64 is available. 01597 showed a **split-only** projected C993 native (64,2)+(66,2) callback, without an intervening authorized full publisher, cannot republish `LastGameWvpWriteValid`; its R30 shader raw getter then rejects. THIS task traces the **downstream physical dispatcher** instead: does that getter rejection necessarily mean one untouched native mono draw, and can existing fallback logs prove the result? It does not replay the split-writer proof as a new finding. No native PMT, physical GPU sample or headset observation was obtained.

NEW_FINDING=STATIC_CONDITIONAL_PROJECTED_C993_R30_RAW_MISS_IS_NOT_AN_AUTOMATIC_SINGLE_NATIVE_DRAW;_R29_FALLBACK_LOG_LABEL_DOES_NOT_CERTIFY_PHYSICAL_EYE_COUNT
NEW_FINDING_TYPE=INDEPENDENT_PINNED_CROSS_FUNCTION_FALLTHROUGH_AND_TELEMETRY_INTERPRETATION_CONTROL
NEW_FINDING_RUNTIME=NONE
NEW_REGRESSION=NOT_ESTABLISHED

### Source-constrained outcome

- The C993 original call for `0x570002/006/00F/010` installs `ProjectedScreenEffect2D` / producer `None` for a **nonqueued** draw and calls `Game::DrawObjectAlpha_Internal` once. This is source-call receipt, not proof that an original opaque `405360/4052C0` material drew inline, nor a sprite/texture/eye submission.
- In the *conditional* shader case with a failed R44+extended original raw getter, `R30BuildScreenSpaceEyeConstants` returns false before any per-eye shader constants are uploaded by that function. If the candidate passes the earlier R30 scope/pose/depth gates, `R30TryScreenSpaceFovDraw` increments `R30ScreenSpaceBuildFailures` and returns `E_NOTIMPL` at its builder gate. This is a **R30 admission failure**, NOT a proven black pixel, a duplicated emitter, or a final D3D draw count.
- Four public R30 DP/DIP/DPUP/DIPUP dispatches can return earlier from R62 fixed-function or R30 XYZRHW paths; those paths do **not** establish participation in the shader raw-c64 getter. When neither stage handles the draw, `R30GuardScreenSpace` calls the shader R30 attempt; only an `E_NOTIMPL` result then calls its `r29Draw()` callback. The literal log field `resultRoute=R29_FALLBACK` says which callback was invoked, not how many original GPU left/right/mono draws were executed below.
- The invoked R29 code is not an unconditional original native one-draw wrapper: `R29GuardStableDraw` uses `legacyR13Draw()` when stable-stereo or effect-state safety fails; otherwise it may call `R29DirectTwoEye()`, which reaches the R9 eye callback. R29's `zeroDisparity=true` still means a **two-eye callback using stock-WVP behavior**, not evidence of one mono Draw. `R29StableStereoBase`/depth/stencil/pose/hazards and shader/effect classification determine the observed branch.
- A narrower lens-specific discriminator: `ProjectedScreenEffect2D` is **excluded** from R29's `allowVerifiedWorldRebind` (R29's cached road/car WVP continuation is vetoed). However `ForceZeroDisparity` in `render_semantics.hpp` names `SkyGlow` and `ScreenOverlay2D`, **not** `ProjectedScreenEffect2D`. Thus R29's effect-based `fragile` / R27 depth candidate decision still matters; do not claim the separate `PhysicalDrawCommand::DeniesGenericWorldFallback` static predicate alone guarantees one native mono draw at this R29 dispatch. Actual R9/R13 owner and native pixel result remain unverified.
- This does NOT show a defect in R29: an intended screen-projected flare may legitimately use inherited, zero-disparity, or non-shader material. Whether the underlying renderer/host shows doubled or head-locked flare must be decided by source/PMT/texture/RT and accepted XR submission evidence, not by `E_NOTIMPL` or the callback label.

## SOURCE_TRACE — connected GitHub, 1-based line ranges at SOURCE_HEAD

1. `src/hooks_graphics.cpp:1137-1153,1166-1190,1245-1290`: C993 four-ID projected admission, source receipt, nonqueued projected scope, `ProducerToken::None`, original `Game::DrawObjectAlpha_Internal`; comment on opaque `405360 -> 4052C0` deferral. CABE ordinal-1/2 original outer path remains distinct.
2. `src/vr/game/outrun_renderer.cpp:1879-1907,1982-2045,2487-2506` and `src/vr/game/lens_centre_partial_wvp.hpp:30-108`: prior 01597's game c64 invalidation, exact direct-only split publisher and `GetLastRawGameWvpWrite` availability; **input assumption, not newly proven**.
3. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:1971-2044,5530-5587`: `R44GetOwnedRawOverlayWvp` and `R30GetExtendedRawWvpForExactSceneEffect` source eligibility; projected-class builder returns false when neither can supply original game WVP.
4. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6863-6923,6938-6964,6993-7001`: `R30TryScreenSpaceFovDraw` checks semantic/depth/pose then returns `E_NOTIMPL` on eye-builder failure **before** the first left-eye WVP upload; a later failure after a successful left draw is a different physical transaction and must not be merged with this case.
5. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:7605-7662,7671-7744`: `R30GuardScreenSpace` returns handled result directly, but when `E_NOTIMPL` invokes `r29Draw()` and prints `VR TRACE LENS LOWER FALLBACK FULL` / `resultRoute=R29_FALLBACK`; `VR TRACE VISUAL LOWER PHYSICAL RESULT FULL` has lower HRESULT, texture0 and RT0 pointer but not a proven physical left/right pixel count. A PMT identity in this log is a separate receipt, not automatically source-authenticated.
6. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:8610-8653,8661-8753,8757-8869`: the DP/DIP/DPUP/DIPUP dispatches first try suitable R62/XYZRHW handling and only subsequently reach `R30GuardScreenSpace` with `R30Draw*R29Hook` callback. Real API/FVF/VS participation must be logged.
7. `src/vr/d3d9/stereo_renderer_r29.cpp:426-453,456-525,527-556,567-648,650-736,739-806`: R29 stable stereo versus legacy R13/R9 and `R29DirectTwoEye` decision. R29's same-file original and baseline GitHub blob is `29ea5c587c5cd13d1990d57770280f5c572ec73a` in BOTH source HEAD and R26+HUD 0cff83cf.
8. `src/vr/game/render_semantics.hpp:1187-1194,1480-1562`: explicit projected scope denies generic world fallback, while `ForceZeroDisparity` lists only sky/overlay; do not equate this class-level assertion to a measured R29/R9 eye result.

PINNED_BLOBS=R29_CURRENT_AND_BASELINE:29ea5c587c5cd13d1990d57770280f5c572ec73a;R30_CURRENT:83a2821bd53d043d7df0557f46627d0af1205d48;R30_BASELINE:0525d1cf53393902b5415bcb139cb55286673aaa;HOOKS_GRAPHICS_CURRENT:982f55dc91c00faf336c06317006fe4aba11db1a;SEMANTICS_CURRENT:f5b2403f59185993930e853edee42d639e1ff454
BASELINE_COMPARISON=R29_ORIGINAL_FILE_BLOB_IDENTICAL_TO_R26_HUD_BASELINE;_CURRENT_R30_AND_SEMANTICS_DIFFER_FROM_BASELINE;_THIS_REVIEW_DOES_NOT_ATTRIBUTE_A_NEW_HMD_REGRESSION_OR_PROMOTE_R84

## Conditional falsification matrix (predictions; NOT executed)

| Source-authenticated actual C993 primitive | Before shader builder | Predicted downstream | What falsifies this interpretation |
| --- | --- | --- | --- |
| Nonqueued projected VS primitive, split-only valid-native game (64,2)+(66,2), no complete original WVP publisher, R62/XYZRHW did not handle it | Both original raw getters reject; R30 build fails before left WVP write | R30 Guard calls R29; R29 chooses actual stable two-eye/zero-disparity or R13 safety by its own state; not necessarily 1 original draw | Matching physical trace shows raw getter succeeded, a stage handled early, or final lower delegate was not R29 |
| Same scope and shader but valid same-shader complete source WVP | R44/extended may admit; later eye/pixel acceptance separately gated | Possible R30 projected left/right, not automatic PASS | Raw getter/pose/build failure or actual eye HRESULT/RT failure |
| C993 fixed-function/XYZRHW physical primitive accepted by early stage | Shader raw getter not reached | R62/XYZRHW native eye result must be measured on that branch | Stage result `E_NOTIMPL` plus matched shader-builder receipt |
| R30 raw failure + R29 stable eligible, fragile effect | R29 delegated after R30 clean fail | R29DirectTwoEye can call R9 with `zeroDisparity=true` and original state | R29 safety result shows legacy R13 path; no actual eye writes |
| R30 raw failure + R29 unsafe/recovery | R29 delegated | Legacy R13/R9 safety path, physical mono/stereo undecided | Physical source matched R29 stable 2-eye receipts |
| Flare seen twice in Quest3 | Unknown; user report alone | Could be intended lobe, same-eye double material, wrong L/R projection or XR composite | Joined same PMT/texture and same-eye RT RGB PRE/POST plus fresh accepted XR layer show actual cause |

## HYPOTHESIS_LEDGER

| ID | State | Inherited evidence -> 01598 distinct result | Specific falsifier |
| --- | --- | --- | --- |
| A extra game-origin emitter | OPEN | Four C993 ids and CABE outer original calls inherited. R30→R29 wrapper branching is **not** source-call count. | Exact original opaque PMT and C993/CABE material count show an additional unintended emission in same source frame. |
| B queue/D3DX/native same-eye replay | BLOCKED_RUNTIME | A logged R29 callback is not a second submission receipt; R29 two-eye is not extra same-eye. | Texture/pass/RT before-after shows two writes to SAME eye for same single original physical lobe. |
| C6 full original c64 cross-object alias | OPEN_CONDITIONAL | Full valid c64 from 01596 may enter R30; the current study specifically follows failed original raw getter, not a supposed observed alias. | Authenticated original PMT/game c64 source identity matches the target or no shader C993 draw. |
| C8 split-only projected shader raw WVP gap | SUPPORTED_STATIC_CONDITIONAL_NOT_RUNTIME | 01597 input assumption now has a specific R30 builder → clean `E_NOTIMPL` → conditional lower R29 trace. The assumed split-only PMT itself remains unobserved. | Actual source uses full valid c64; fixed-function early stage handles draw; another publisher restores validity; or no physical shader material. |
| C9 R30 raw WVP rejection proves one original mono Draw | REFUTED_STATIC_INFERENCE | NEW: callback `resultRoute=R29_FALLBACK` is not a physical draw counter; R29 can run R9 2-eye or R13/R9 safety, and projected scope blocks the world-rebind fast route without forcing a measured one-draw result. | If a **specific authenticated actual** failure frame contains one native draw under the lower path, that determines that frame, not the universal implication. |
| D centre/halo intended versus unintended two copies | OPEN | No physical material/texture+UV/alpha-lobe joined to the callback; normal 2-eye stereo is not duplication. | Same-eye material proof paired with expected original C993/CABE lobe list. |
| E host/OpenXR stale or flat composite | BLOCKED_RUNTIME | Lower Draw HRESULT/RT0 pointer cannot establish accepted XR layer/swapchain array index or fresh `xrEndFrame`. | Joined sourceFrameId/QPC, L/R eye layers, pose, and accepted compositor call. |
| F world sun bearing versus head-local/camera-sync error | OPEN_RUNTIME | Lower zero-disparity candidate still may be intended; actual source pose + two head yaw angles absent. | Matched source matrix/ray+PMT and L/R eye RT centroid across yaw at accepted XR frame. |

## Evidence gaps and actionable follow-up

EVIDENCE_SOURCE=GITHUB_PINNED_HOOKS_C993_R30_BUILDER_DISPATCH_LOWER_R29_AND_RENDER_SEMANTICS_R26_HUD_BASELINE_BLOB
EVIDENCE_DISASM=INHERITED_D3A5_C993_CABE_405360_4052C0_405890_404700_ONLY;_NO_NEW_GAME_EXE_BYTES_OR_CALLER_DISASSEMBLY
EVIDENCE_LOG=NO_NEW_NATIVE_RUNTIME_CAPTURE;_LENS_LOWER_FALLBACK_AND_VISUAL_PHYSICAL_RESULT_LOG_FORMATS_READ_IN_SOURCE_ONLY
EVIDENCE_USER_REPORT=PREVIOUS_CENTRE_FLARE_DOUBLE_HEAD_FOLLOW_NOT_REPRODUCED_ON_CURRENT_SOURCE_HEAD
EVIDENCE_GAPS=Actual original c64 full/split chronology and successful native HRESULT, exact C993 object/PMT pass/texture/UV/blend/VS/FVF, R62 or XYZRHW early acceptance, R30 builder selected, R29 stable/fragile/legacy branch, R9 actual left/right eye GPU draw+RT0 RGB PRE/POST and state restore, OpenXR accepted layer/frame/pose and two-yaw Quest3 observation.

NEXT_FALSIFICATION_TEST=Read-only single physical C993 lobe trace across `sourceCallSerial+objectId+LensFlareSequence+opaquePmt.serial+mesh/pass+texture0+TopLevelDrawSerial`. Capture original game `SetVertexShaderConstantF(64,count,nativeHRESULT)`, raw WVP getter result, `R62/XYZRHW/SCREEN_FOV` entry+HRESULT, `R30ScreenSpaceBuildFailures`, `VR TRACE LENS LOWER FALLBACK FULL`, `VR TRACE VISUAL LOWER PHYSICAL RESULT FULL` plus an **independent** R29 stable/fragile and R9/R13 actual per-eye draw-attempt/HRESULT/RT0 RGB record. Join final L/R array slice/sourceFrameId/QPC/pose/`xrEndFrame` acceptance at two head yaws. Do not treat callback-only labels as per-eye pixels or accept CI as headset evidence.
EXPECTED_LOG_METRICS=C993_SOURCE_SERIAL_OBJECT_SEQUENCE_PMT;_GAME_C64_START_COUNT_HRESULT_GENERATION;_R44_EXTENDED_RAW_GETTER_BOOL;_R62_XYZRHW_STAGE_HRESULT;_R30_BUILDER_FAILURE_BEFORE_LEFT;_R29_STABLE_FRAGILE_LEGACY_BRANCH;_R9_LEFT_RIGHT_DRAW_ATTEMPT_HRESULT_RT_RGB;_XR_SOURCE_FRAME_FRESHNESS
EXPECTED_PIXEL_OUTCOME=UNDETERMINED;_R29_ZERO_DISPARITY_TWO_EYES_MAY_BE_INTENTIONAL_BUT_DOES_NOT_PROVE_WORLD_DEPTH;_ONLY_SAME_EYE_EXTRA_MATERIAL_OR_WRONG_BEARING_AND_ACCEPTED_HOST_COMPOSITE_CAN_SUPPORT_SYMPTOM_CAUSE

PATCH_CANDIDATE_ONLY=NONE_UNTIL_A_SOURCE_AUTHENTICATED_C993_PRIMITIVE_AND_UNEXPECTED_LOWER_EYE_PIXELS_ARE_CAPTURED. CONDITIONAL_LENS_ONLY_POSSIBLE_FUTURE_REVIEW: `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:7605-7744` (R30GuardScreenSpace) plus `src/vr/d3d9/stereo_renderer_r29.cpp:527-736` (R29GuardStableDraw) for diagnostic-only join of pre-lower rejection reason and completed per-eye branches; ONLY if existing trace cannot correlate; do NOT globally force mono, replay game emitter, change semantics, widen raw-c64, or insert B9200 post-CALL/+5. FALSIFIER=existing exact-SHA recordings already join per-eye physical result correctly; or actual observed lens always uses R30 successful stereo, or original projection/source is intentional.
REGRESSION_RISK=DOCS_ONLY_NONE;_UNAUTHORIZED_FUTURE_FALLBACK_PATCH_COULD_FLATTEN_INTENDED_C993_OR_BREAK_BOTH_EYE_SUBMISSION_DEPTH_STENCIL_RESTORE_CABE_OUTER_LOBES_OR_R26_HUD_BASELINE;_R84_NONDEFAULT_AND_B9200_FORBIDDEN

NEXT_REVIEW=LENS_FLARE:C993_R30_E_NOTIMPL_TO_R29_STABLE_FRAGILE_R9_LEFT_RIGHT_PHYSICAL_DRAW_AND_HOST_XR_RECEIPT
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01598.md
AUTOMATION_VALIDATION=PENDING_REMOTE_DOCS_ONLY_COMMIT_READBACK
RUNTIME_VALIDATION=UNTESTED
CODE_CHANGE=NO
