# CONVERSION-DX9EX-01597 — C993 projected split-game-c64 negative control (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01597
PRODUCTION_ID=CONVERSION-DX9EX-01597
EVENT_ID=CONVERSION-DX9EX-01597-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=0c344eac3ba8bcc43d09dfe202dc383666bf3ca3
SOURCE_SSOT=CONNECTED_GITHUB_EXACT_SHA_PINNED_WITH_PRECOMMIT_HEAD_CHECK
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
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN

## Distinct question and finding

01596 demonstrated a *possible* cross-object WVP alias after a complete original-game c64 publication, when the projected C993 scope borrows a same-shader/same-epoch matrix within the 12/128-draw window. This review tests a different negative control: **does a projected, nonqueued C993 0x570002/006/00F/010 source that writes c64..c67 as two successful partial native writes create ANY valid last-game WVP publication to which that alias predicate could apply?** This is a source-level conditional case; original EXE bytes and real PMT write pattern were NOT newly observed.

NEW_FINDING=STATIC_PROJECTED_C993_SPLIT_C64_64PLUS2_66PLUS2_CANNOT_REPOPULATE_LAST_GAME_WVP_WITHOUT_A_SEPARATE_FULL_OR_AUTHORIZED_SOURCE_WRITE
NEW_FINDING_TYPE=DIFFERENT_SOURCE_GATE_NEGATIVE_CONTROL_LIMITING_01596_ALIAS_CASE
NEW_FINDING_RUNTIME=NONE
NEW_REGRESSION=NOT_ESTABLISHED;_PROTECTED_BASELINE_CONTAINS_THE_SAME_SPLIT_WRITER_AND_SOURCE_OWNER_GATES

- On each external GAME c64-touching `SetVertexShaderConstantF` callback, `InvalidateGameWvpWrite` clears `LastGameWvpWriteValid` before the native call. This is correct fail-closed behavior even for unsuccessful or partial writes.
- `UploadContainsOutRunWvp(64,2)` and `(66,2)` are both false (neither contains the complete four-register range). This enters the partial path. Its special `LensCentrePartialWvp.Append` publisher requires **direct** `WorldBillboard`, `ProducerToken::LensFlareCentre`, no queue, nonzero direct call epoch, eligible R23 target and shader epoch. The actual projected C993 wrapper deliberately selects `ProjectedScreenEffect2D` + `ProducerToken::None`; thus this exact-direct accumulator cannot publish the projected source.
- The other partial assembler, `HudQueuedPartialWvp.Append`, admits only active queued `ScreenHud` with a non-None producer, live queue node and queue epoch; a nonqueued projected lens cannot publish via it either.
- Consequently, in the isolated scenario “64/2 success, then 66/2 success; no intervening valid full/native WVP publication; same shader/pose/PMT”, the last game WVP remains invalid even though native D3D9 retained the complete four rows. Both R44 12-draw and extended 128-draw getters first call `GetLastRawGameWvpWrite` and therefore fail **before** their shader/age checks. A projected C993 shader-space `R30BuildScreenSpaceEyeConstants` attempt then returns false for missing original raw WVP; the later R30/R26/original lower path is not established by this record. This does **not** prove the game actually issues split writes, missing rays, head-lock, a doubled sprite, or an accepted host composite.
- Contrast the separately eligible **full** native `(64,4)` successful game upload in projected scope: `semanticOverlay` can include a camera-synced projected lens, and the `RecordGameWvpWrite` path may publish a raw matrix (or the ordinary injectable branch can publish the original raw input). Then 01596's same-shader age-window issue remains conditionally relevant. A direct physical `WorldBillboard/LensFlareCentre` split can use its own source-owned assembler, whereas a queued exact `ScreenHud` split uses its separate queue-owned assembler. These are **controls, not claims about actual C993 PMT material**.

## SOURCE_TRACE — pinned current GitHub 1-based locations

1. `src/hooks_graphics.cpp:1137-1153,1166-1190,1230-1290`: four original C993 object IDs; nonqueued path explicitly installs projected-screen scope, `ProducerToken::None`, source-call receipt, and exactly one `Game::DrawObjectAlpha_Internal` call per wrapper invocation; the opaque original 405360/4052C0 path may execute inline or deferred.
2. `src/vr/game/outrun_renderer.cpp:1879-1907,1982-2045`: game-device c64 touch → generation increment + unconditional game-WVP invalidation; partial path checks the direct WorldBillboard/LensFlareCentre ownership, then optionally publishes only a fully assembled exact direct source; a foreign projected source cannot satisfy `exactCentre`.
3. `src/vr/game/outrun_renderer.cpp:1937-1981` and `src/vr/game/queued_hud_partial_wvp.hpp:14-63`: queued HUD partial publication is independently guarded by `queueActive && scope==ScreenHud && producer!=None && node && queueEpoch`, so it cannot rescue the nonqueued projected source.
4. `src/vr/game/outrun_renderer.cpp:2054-2175,2190-2220`: entire four-register native game WVP can publish on a successful semantic-overlay or ordinary injection path, with source-generation and native-result guards; this is the control opposite to split-only source.
5. `src/vr/game/outrun_renderer.cpp:1699-1759,2487-2506`: invalidation resets validity and source provenance; `GetLastRawGameWvpWrite` rejects invalid/zero-identity records before returning the original 16 floats.
6. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:1842-1859,1958-2051,5530-5587`: `R44GetOwnedRawOverlayWvp` and `R30GetExtendedRawWvpForExactSceneEffect` require a valid stored original game record; projected kind chooses the two in order and fails if both reject. The age=2/20 source-alias case from 01596 requires a **published** record and is inapplicable to the isolated split-only case.
7. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5728-5815`: only after original source selection, `BuildProjectedSunRay` can produce separate L/R FOV matrices; two legitimate eye draws do not constitute a duplicate.
8. `src/vr/game/lens_centre_partial_wvp.hpp:30-108`: the direct exact-centre accumulator accepts complete 4-row coverage only when its source call/pose/shader/device/draw identity matches; projected `None` is not implicitly upgraded.
9. Baseline comparison: `src/vr/game/outrun_renderer.cpp@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9` blob `26b9225d2fe4fa4265735cf678cf5a8eec1d9c97` already has `if (!UploadContainsOutRunWvp` and distinct exact `LensCentrePartialWvp.Append` / `HudQueuedPartialWvp.Append` paths. Current blob `9b845778272e59585df8e2ae570f6da260cb8ec9` preserves this structural distinction; no user-tested baseline regression inferred.

PINNED_BLOBS=hooks_graphics.cpp:(READ_AT_SOURCE_HEAD);outrun_renderer.cpp:9b845778272e59585df8e2ae570f6da260cb8ec9;queued_hud_partial_wvp.hpp:58df5a5760012e9e2063e1aff57629ac2c28cc51;lens_centre_partial_wvp.hpp:fb8d155f12dbde96a7c382e83b3695f33b6bc0a6;stereo_renderer_r30_r26_safe.cpp:83a2821bd53d043d7df0557f46627d0af1205d48

## Falsification matrix — symbolic, not executed native tests

| Conditional original source pattern | Last-game c64 after callback | Projected R30 raw getter prediction | Correct interpretation |
| --- | --- | --- | --- |
| Nonqueued projected C993: native success `(64,2)` then `(66,2)`, no other c64 publisher | Invalid after both callbacks | R44 and extended getter both reject before age comparison | Proves the **conditional split-only fail-closed gap**, not a Quest3 missing/doubled ray. |
| Nonqueued projected C993: successful complete `(64,4)` with eligible target and stable callback | Valid when complete `RecordGameWvpWrite` executed | Shader/epoch and 12/128 age can admit record | 01596's cross-object ownership still needs authenticated source/PMT association. |
| Direct exact unqueued `WorldBillboard` / LensFlareCentre, matching call+pose+shader+draw, `(64,2)+(66,2)` success | Can be valid after exact accumulator completes | Exact-owned getter uses stricter pose/call evidence | Positive assembler control; not proof of projected C993 participation. |
| Queued exact `ScreenHud`, live node, `(64,2)+(66,2)` success | Can be valid after HUD assembler completes | Separate HUD authorization | Negative control on accidentally crediting this path to lens flare. |
| Any C993 projected partial with intervening successful authorized full publish | Validity depends on final writer order; next partial invalidates | Cannot infer split-only result without real source timeline | Original-source chronology and physical draw identity required. |
| No live shader/fixed-function XYZRHW | R30 shader projected WVP branch may not execute | No inference from these getters alone | Must separately census R30 XYZ/RHW and R26/native fallback. |

## HYPOTHESIS_LEDGER

| ID | Status | Prior evidence → distinct 01597 check | Falsifier |
| --- | --- | --- | --- |
| A extra original emitter | OPEN | Prior four C993 IDs and two CABE ordinal 0x570008; split setter changes WVP validity, not count of original CALLs. | Original exe source/object/sequence+PMT proves unintended additional emitter. |
| B D3DX/queue/native same-eye replay | BLOCKED_RUNTIME | Neither partial accumulator calls Draw. Original opaque 4052C0/PMT material and actual RT RGB not observed. | Source+PMT+material/texture/UV/eye joined repeated same-eye colour writes beyond intended lobe. |
| C6 projected same-shader wrong-source original c64 admitted | NARROWED_CONDITIONAL | 01596 full-published WVP alias plausible; **split-only/no-full-WVP** invalidation rejects both getters before age2/age20 can matter. | Real C993 projected PMT shows complete independently authorized source upload and cross-object wrong WVP, or actual raw getter is bypassed. |
| C8 nonqueued projected C993 split-only c64 loses shader-space raw source record | SUPPORTED_STATIC_CONDITIONAL | New producer/assembler contrast proves `exactCentre=false` and `queueActive=false` on the isolated projected split branch; no complete record republished. | A documented eligible projected partial accumulator/source record or original whole-c64 publish within the same observed draw; physical fixed-function/nonshader fallback is a separate branch, not a counterexample to the shader predicate. |
| C direct WorldBillboard exact-depth veto | OPEN | 01595 guard scope and 01594 XYZRHW branch remain independent; projected token None cannot be relabelled exact direct. | Physical source/FVF/VS+scope identifies actual alternative branch and veto status. |
| D intended centre/halo/glow/ghost passes | OPEN | Split upload is not evidence of unexpected lobe; source objects/texture-alpha still unauthenticated. | Original 405890→404700 PMT, exact texture/UV/blend, each-eye raw RGB match expected versus extra passes. |
| E reused ViewSpace/flat host layer | BLOCKED_RUNTIME | Producer raw-source negative cannot assert host composite; must identify accepted R24/R32 OpenXR output. | Fresh sourceFrameId/QPC, L/R array indices, valid projection layers and accepted xrEndFrame at two yaw poses. |
| F head-follow from wrong source pose/rotation | OPEN_RUNTIME | Split-only raw failure could force fallback, or full-source alias may permit a ray; neither establishes world-angle error. | Matched source c64/writer/camera-sync and native L/R centroids plus two-yaw accepted XR identifies anchored vs headlocked flare. |

## Evidence and next falsification

EVIDENCE_SOURCE=CONNECTED_GITHUB_PINNED_C993_WRAPPER_GAME_SETTER_TWO_PARTIAL_ASSEMBLERS_R30_GETTERS_AND_BASELINE
EVIDENCE_DISASM=INHERITED_ONLY_ORIGINAL_D3A5_C993_CABE_405360_4052C0_405890_404700;_NO_NEW_BINARY_BYTES
EVIDENCE_LOG=NONE_NEW;_LOG_STRINGS_IN_SOURCE_ARE_NOT_OBSERVED_EVENTS
EVIDENCE_USER_REPORT=EARLIER_CENTRAL_FLARE_DOUBLE_AND_HEAD_FOLLOW;_NOT_REPRODUCED_ON_SOURCE_HEAD

EVIDENCE_GAPS=Whether real original 0x570002/006/00F/010 or CABE 0x570008 uses split-only c64; exact native HRESULT and callback order; unrelated full publisher between writes; shader/FVF/XYZRHW/draw entry; sourceCallSerial-to-PMT-to-texture and original c64 writer relationship; actual both-eye RGB writes, R26 fallback, R19/R24 XR accepted layer/frame/pose, two-yaw Quest3/VDXR.

NEXT_FALSIFICATION_TEST=For a real source-matched C993 projected ID, read-only join `sourceCallSerial,objectId,lensSequence,PMTpass,topLevelDrawSerial` with exact native `SetVertexShaderConstantF(start,count,HRESULT,uploadGeneration)` chronology and `LastGameWvpWriteValid/writeSerial/writerScope/pose/shaderEpoch` immediately before a **physical** shader draw. Split case must have invalid record absent a separate complete write; full case can have a valid record. Then sample selected R44/extended getter outcome, actual R30 or R26 lower owner, both eye RT0 pre/post RGB, and final accepted XR array/layer/QPC for two head yaw poses. Reject C8 as **practical** diagnosis if no lens shader draw ever exhibits this split-only pattern; reject the renderer optics claim if both eyes/host are correct.
EXPECTED_PIXEL_OUTCOME=UNDETERMINED_FOR_SPLIT_UNTIL_LOWER_ROUTE_AND_NATIVE_RGB;_FULL_SOURCE_MAY_BE_WORLD_ANCHORED_OR_MISATTRIBUTED;_NORMAL_LR_PAIR_NOT_DUPLICATE
EXPECTED_LOG_METRICS=C993_SOURCE_SERIAL_AND_OBJECT;_GAME_C64_START_AND_VECTOR_COUNT_AND_HRESULT;_GET_LAST_RAW_VALID_AND_WRITE_SERIAL;_R30_BUILD_SELECTED_GETTER_OR_E_NOTIMPL;_R30_LR_RAW_HRESULT_AND_RESTORE;_R26_FALLBACK_COUNT;_XR_FINAL_LAYER_FRESHNESS

PATCH_CANDIDATE_ONLY=CONDITIONAL_NOT_APPLIED: only if an actual authenticated projected C993 physical shader draw uses successful partial-only game c64 uploads and optically incorrect R26/mono fallback, consider a lens-only **source-owned, complete original c64 4-row accumulator** at `src/vr/game/outrun_renderer.cpp:1879-2045`, with strict projected original source call+object/sequence, native HRESULT, per-draw device/shader/pose epoch, original D3D9 retained rows, and explicit prohibition on cross-object/opaque deferred PMT borrowing. Pair with conservative `R30BuildScreenSpaceEyeConstants` lens getter at `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5530-5587`; never widen generic SceneEffect or substitute live stereo-injected c64. FALSIFIER=no real projected split-only source, currently correct lower-eye pixels, intended original C993 shared WVP, missing physical renderer participation, or host-only duplicate. Do not apply or recommend a global producer/halo suppression.
REGRESSION_RISK=DOCS_ONLY_NONE;_FUTURE_PATCH_CANNOT_BE_ASSUMED_SAFE: possible cross-object shared c64, CABE ordinal1/2 queue delay, c64 partial row ordering, alpha and sun halo pass identity, original D3D9 HRESULT/restore, per-eye RT/DS, shader epoch and pose, correct world angular sun, R26+HUD baseline, R84 nondefault, B9200 forbidden.

NEXT_REVIEW=LENS_FLARE:C993_PROJECTED_SPLIT_VS_FULL_C64_NATIVE_SUCCESS_TO_PMT_SHADER_DRAW_AND_R30_LOWER_XR_PAIR
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01597.md
AUTOMATION_VALIDATION=PENDING_REMOTE_DOCS_ONLY_COMMIT_READBACK
RUNTIME_VALIDATION=UNTESTED
CODE_CHANGE=NO
