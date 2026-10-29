# CONVERSION-DX9EX-01589 — lens R30 pre-LEFT versus post-LEFT E_NOTIMPL: mono-backup-gap / poisoned-present discriminant (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01589
PRODUCTION_ID=CONVERSION-DX9EX-01589
EVENT_ID=CONVERSION-DX9EX-01589-E001
EVENT_TYPE=dispatch
LANE=DX9EX
ATTEMPT=1/3
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=3f5f92867ba3334d5955f726a4a68907c77476d7
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
RUNTIME_VALIDATION=UNTESTED

## Independent static falsification boundary

INHERITED=CONVERSION-DX9EX-01587 established the conditional original LEFT HRESULT == E_NOTIMPL collision with R30's clean-decline sentinel. CONVERSION-DX9EX-01588 established that the nominal R29 lower callback in default R26+HUD actually hooks R26, not R29; the conditional lower calls R26, then either a write-free query-only single Draw or the R23->R22->R9 route. Older LENSFLARE-QUERY-STEREO-SINGLEEXEC-20261027-1908 already excludes double execution of a *qualified* active write-free 0x570010 occlusion draw: that is not newly credited here.

DISTINCT_TEST=Follow the **mono-backup validity and frame poisoning** introduced on either side of R30's *first physical LEFT* for one authenticated original lens PMT draw, through R26/R23/R22/R9 and Present. In particular, test whether the conditional post-LEFT E_NOTIMPL fallback can be interpreted as another valid stereo pair or a recovered mono shadow. Compare protected baseline placement of the no-mono-backup marker. No physical lens/Quest3 incidence or actual colour write inferred.

NEW_FINDING=STATIC_R30_POST_LEFT_ERROR_POISONS_FRAME_AND_HAS_PREVIOUSLY_MARKED_MONO_BACKUP_GAP_BEFORE_POSSIBLE_R26_LOWER;_NORMAL_R9_FAILED_FRAME_ROUTE_CAN_STILL_DRAW_MONO_SHADOW_THEN_ONE_GAME_TARGET_ORIGINAL_BUT_CANNOT_MAKE_AN_ELIGIBLE_STEREO_PRESENT_OR_VALID_MONO_RESTORE;_CURRENT_PRE_LEFT_WVP_E_NOTIMPL_DOES_NOT_SET_THIS_CALLS_GAP_WHERE_PROTECTED_BASELINE_MARKED_IT_EARLIER;_NO_PROOF_OF_ACTUAL_LEFT_E_NOTIMPL_OR_VISIBLE_DUPLICATE.
NEW_FINDING_TYPE=SOURCE_STATIC_CONDITIONAL_NOT_RUNTIME_ROOT_CAUSE

## SOURCE_TRACE (pinned connected GitHub, 1-based lines)

1. **Actual current R30 boundary**: `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6778-6835` attempts original LEFT WVP upload. On recoverable failure, restored original WVP returns `E_NOTIMPL` *before* a native LEFT call. The native LEFT path at `:6837-6847` calls `R9NoteStereoDrawWithoutMonoBackup()` **only after successful LEFT-WVP setup**, then invokes `actualDraw()`. At `:6848-6935`, a failed raw `leftHr` restores WVP, `R9Poison(StereoFailureLeftDrawFailed,...)`, `R30ArmSafeFallback()` and returns unchanged `leftHr`; the Guard in `:7379-7435` calls the lower callback only if `hr == E_NOTIMPL`. A successful LEFT followed by RIGHT failure returns `leftHr` at `:7362-7375` and does not, solely from that failure, trip the Guard sentinel.
2. **Frame/backup latches are independent**: same R30 file `:71-76`, `R30ArmSafeFallback` always sets `FrameStereoIncomplete = true`, setting `R13ForceMonoShadow` only when `R9MonoSeeded && !R9MonoBackupGap`. `src/vr/d3d9/stereo_renderer.cpp:1066-1070` implements `R9NoteStereoDrawWithoutMonoBackup` as `++R9DrawCalls; R9MonoBackupGap = true;`. `stereo_renderer.cpp:287-294` forwards `R9Poison` to `PoisonFrame`, whose `stereo_renderer_r7.inc:719-728` sets `FrameStereoIncomplete` and first failure reason. Thus a **post-LEFT** error has both gap and incomplete, independent of whether a second native draw ever occurs. Pre-LEFT recovered WVP failure on this path does not itself call the no-backup marker; it can inherit a gap from earlier draws, so a gap=0 is not guaranteed.
3. **Real lower destination & normal route**: `stereo_renderer_r30_r26_safe.cpp:8409-8425,8696-8707` maps DP's named `r29` callback to `DrawPrimitiveDestR26` in default R26+HUD (same for DIP/UP variants at :8508-8525,8560-8578,8621-8639,8696-8707). `stereo_renderer_r26.cpp:337-425,777-842` delegates normal/maybe-colour-writing draws to R23, reserving one actual draw for an *active, state-proven write-free query*; `stereo_renderer_r23.cpp:540-594` enters R23's top-level accounting then passes to R22. `stereo_renderer_r22.cpp:557-559,624-710` either directly calls the original for ineligible/stale replay state or passes the draw onward to R9. A lower HRESULT/nominal `R29_FALLBACK` log alone proves neither branch was taken nor one physical eye colour write.
4. **Normal R9 branch when already poisoned**: `stereo_renderer.cpp::R9ExecuteDraw:616-708` can call `R9ReplayMonoDraw` *before* checking `FrameStereoIncomplete` at :683-688; therefore do **not** assert that a poisoned lower route is necessarily just one total GPU API call. `R9ReplayMonoDraw:340-389` may draw into a **different mono-shadow RT** and restore original target. If the backup path succeeds, `FrameStereoIncomplete` forces **one** original `actualDraw()` against the game target and does not call the normal stereo `legacyDraw()` path for that R9 boundary. If backup fails, :668-676 also returns one original draw after fail-closed poisoning. The R22 direct-original bypass is yet another one original Draw, not a newly completed R9 stereo pair. No assertion here about uninspected exceptional alternative hooks or actual lens-state eligibility.
5. **Present contract and the misleading extra-draw hypothesis**: `stereo_renderer.cpp:758-769` explicitly requires `!FrameStereoIncomplete` for stereo `frameEligible`, so a post-LEFT poisoned *frame* cannot be accepted as a fresh completed stereo Present through that gate. `:827-840` restores mono before Present only if `R9MonoSeeded && !R9MonoBackupGap`; R30's post-LEFT path previously set the gap, so that restore condition is false **for this same frame absent an intervening verified full reset/clear**. A fallback may draw to the mono-shadow target but the source does not license treating that shadow as a complete recovery or as another visible same-eye flare. The actual final host XR mode/cached frame remains unobserved.
6. **Protected baseline differential**: at `stereo_renderer_r30_r26_safe.cpp@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9:4821-4863` the no-mono-backup call was **before** the LEFT WVP upload. After WVP upload rollback returned `E_NOTIMPL` at :4846-4849, the same call had already marked the gap; at current `:6778-6847` it lies **after** successful WVP setup. The baseline already poisoned failed raw LEFT at :4851-4862 and used R9's incomplete gate (baseline `stereo_renderer.cpp:594-627,695-705,761-770`). This is a conditional call-order difference, not verified good/bad lens optics or a new proof of regression.

## HYPOTHESIS_LEDGER

| ID | Status | Previous evidence -> distinct evidence tested here | Falsification condition |
| --- | --- | --- | --- |
| A: additional original 0x570008 emitter | OPEN | Two original CABE ordinals/four C993 centre IDs inherited; current poisoned-fallback route is below producer and adds **no emitter call** by itself. | Exact source ordinal + 405890 PMT + texture/pass and two unexplained source-level emitters beyond original call graph. |
| B1: failed LEFT `E_NOTIMPL` causes another *top-level lower call* | SUPPORTED_CONDITIONAL_STATIC | 01587 sentinel + 01588 R26 hook; current state/backup/Present gate confirms conditional lower may happen on an already poisoned frame, not a fresh completed stereo frame. | Exact hardware original LEFT HRESULT never `E_NOTIMPL`, or linked R30 binary maps native-left failure to a distinct non-decline result. |
| B2: post-LEFT lower creates **two successful colour writes to the same eye** | BLOCKED | Current R9 incomplete branch excludes *R9* normal L/R legacy pair on poisoned call; optional mono-shadow target plus original game target are **different RTs**. Failed first native HRESULT is not proof it wrote zero pixels either. | Authenticated PMT/primitive and texture identity + same-eye RT addresses + PRE/POST RGB deltas proving two unexpected successful writes, as opposed to the intended native-first failed call or separate mono RT. |
| C: projected centre vs deferred CABE stereo/screen-space ownership mismatch | OPEN_STATIC_CONDITIONAL | R30 pre-LEFT admission distinct from post-LEFT failure; source does not show any actual CABE/C993 primitive taking either branch. | Match original PMT source, physical semantic, per-eye WVP/viewport, accepted stereo centroids and two HMD yaw positions. |
| D: original halo/ghost textures make intentional multiple lobes | OPEN | Original multiple family/pass structure inherited; no new texture-level pixel evidence. | Per-texture/per-pass alpha and blend + native per-eye ROI disambiguates distinct intended materials from unexpected duplicate. |
| E: host cached/mono layer reuses source and looks head-locked | OPEN_RUNTIME | Current R9 poisoned Present may not produce eligible fresh stereo, but this does **not** establish what R19/R24 actually selects on such a frame. | Record exact sourceFrameId/QPC, transport fresh/cache, xrEndFrame accepted layer type, arrayIndex, poses/FOV and both source-eye RGB centroids. |
| F: camera/world sun and HMD-relative source bearing error | OPEN_RUNTIME | Source status alone cannot distinguish directional-infinity near-zero disparity from actual head-follow. | Two known headset yaws with source world bearing, effective eye WVP/FOV, game source tick, fresh source-eye and final accepted XR centroids. |
| G: post-LEFT R30 `E_NOTIMPL` fallback necessarily produces a **second completed stereo pair or safely restored mono** | REFUTED_FOR_INSPECTED_NORMAL_R9_PATH_STATIC | New: R30's gap+poison, R9's delayed incomplete check and Present veto together disprove this inference. | Live matching build shows frameIncomplete cleared between same top-level error/delegate/Present, another owner bypassing R9 executes successful stereo, or mono-gap reset by an independently verified complete game frame; verify exact frame identity. |
| H: current pre-LEFT recovered `E_NOTIMPL` necessarily poisons mono-backup gap | REFUTED_FOR_THIS_CALL_STATIC | Protected baseline marked before WVP; current R30 only marks after successful WVP. Other same-frame writers may already have marked gap. | Verified current native path marks gap before the WVP rollback branch despite this pinned source, or a different compiled owner is active. |

## NEXT_FALSIFICATION_TEST / predictions (diagnostics only; no implementation performed)

- Verify linked binary/CMake R26+HUD owner and match **one** original lens material `0x570008 ordinal1/2` or `C993 centre ID` by authenticated sourceCallSerial -> opaqueFlushSerial -> **original 405890 PMT entry** -> native DP/DIP/UP call -> unique topLevelDrawSerial, effective scope, texture0/alpha and RT.
- **PRE_LEFT_CONTROL**: R30 rejected left-WVP upload with successful original-WVP restoration => no native LEFT attempt, `E_NOTIMPL` -> R26. This R30 call does **not** newly set `R9MonoBackupGap` or poison due to left native Draw; other prior frame gap remains possible. Observe R26 query-vs-R23 and R22/R9 path. No first successful colour write is attributable to R30.
- **POST_LEFT_SENTINEL_CONTROL**: R30 leftAttempted=1, raw `leftHr=0x80004001`, `R9MonoBackupGap=1`, `FrameStereoIncomplete=1`, then R26 lower conditional; if R22/R9 active and same-frame, expect no subsequent R9 normal stereo legacy call after incomplete check. There *may* be a mono-shadow API Draw plus a game-target API Draw; differentiate RT0 identities. Expect stereo `frameEligible=0` and no valid R9 mono restore on poisoned Present. Actual RGB/host cannot be inferred from HRESULTs.
- **NON_SENTINEL_CONTROL**: a different failed LEFT HRESULT => no R30 Guard R26 lower on that invocation, still gap+poison.
- **RIGHT_FAILURE_CONTROL**: success LEFT + failed RIGHT => returns successful `leftHr`, no Guard lower; poison/incomplete still forbids fresh eligible frame. No completed pair inference.
- **EYE_PIXEL_CONTROL**: exclude normal LEFT+RIGHT intended source renders and mono-shadow RT from same-eye duplicate counts. Count only source-authenticated *same native eye RT* ROI RGB deltas per original material/pass and pose; compare original game source image to R19 chosen frame and R24 actual xrEndFrame layer/projection at two yaws.

NEXT_FALSIFICATION_TEST=AUTHENTIC_570008_PMT_R30_PRE_LEFT_VS_POST_LEFT_E_NOTIMPL_R9_MONO_GAP_FRAME_POISON_LOWER_R26_R22_R9_SAME_RT_ROI_AND_R19_R24_ACCEPTED_XR_TWO_YAW
EVIDENCE_SOURCE=PINNED_GITHUB_CURRENT: R30 safe blob 6827f864b966ca743dff35725cc9ad9c9e96cc3b; R26 blob 4e486a14c0f180928732419868f5449b6d8759cf; R23 blob 8a80c3220c3571ececbf8218ef4c5f3226985a01; R22 blob dd1cbed902f468166dcf93598ca0b24043584dad; R9 stereo_renderer.cpp blob 2a8aa0325aaeb9b3a2bf8057d9f9a05a1e728c07; R7 inc source and previous 01587/01588/older 570010 query review; baseline R30 blob 0525d1cf53393902b5415bcb139cb55286673aaa and R9 blob eef48e799d75925a08eaefe21478dc40f9b718a3.
EVIDENCE_DISASM=INHERITED_ONLY: previous original CABE/C993/405890/404700 mapping; no new EXE byte or executable disassembly, and no original PMT field-offset authentication.
EVIDENCE_LOG=NONE_NEW: source log strings are not matched frame samples. No real hardware E_NOTIMPL occurrence, no exact eye/mono RT RGB, no real R19/R24 accepted-layer receipts.
EVIDENCE_USER_REPORT=USER_OBSERVED_LENS_SPLIT_DOUBLE_AND_HEAD_FOLLOW; no exact matching SHA or Quest3/VDXR replay in this task.
EVIDENCE_GAPS=Which linked CMake build ran; exact 405890 PMT field authority and original flare ordinal; native left HRESULT incidence; whether native failure modified RGB; actual R26/R22 branch, R9 mono RT attempt and same-eye RGB, earlier gap latch/reset lifetime; stereo host sourceFrameId/fresh/cache/accepted XR pose and two-yaw HMD test.
PATCH_CANDIDATE_ONLY=NONE: No evidence merits optical/renderer patch. IF a source-matched real LEFT E_NOTIMPL shows a second same-eye colour write, propose *only after approval* splitting R30 decision sentinel from raw LEFT failure inside `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6837-6935,7379-7435`, preserving pre-LEFT clean fallback and post-LEFT poisoning; require separately authorized failing-before/passing-after binary test and actual source RT data. Falsifier: no actual native E_NOTIMPL, or additional eye lobe only appears at host after a single native ROI. No code applied.
REGRESSION_RISK=DOCS_ONLY_NONE; future code change may suppress legitimate pre-LEFT fallback, alter frame poison/mono backup, silently drop original CABE halo passes, remove normal L/R stereo, cause invalid depth/RT/WVP restores, or admit partially rendered XR frames. Preserve R26+HUD baseline and R84 as nondefault, no B9200 post-CALL/+5 hook; compare no-physical-pixel conclusions to actual HMD before patching.
NEXT_REVIEW=LENS_FLARE:R30_POST_LEFT_NATIVE_E_NOTIMPL_R26_R22_NORMAL_ORIGINAL_VS_MONO_SHADOW_RT_RGB_POISONED_PRESENT_TO_R24_ACCEPTED_LAYER
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01589.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01589]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01589.md
AUTOMATION_VALIDATION=PENDING_DOCS_ONLY_REMOTE_READBACK
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
