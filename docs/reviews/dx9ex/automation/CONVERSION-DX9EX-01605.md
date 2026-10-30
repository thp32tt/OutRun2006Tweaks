# CONVERSION-DX9EX-01605 — LENS-positive trace family versus authentic lens PMT

DATE=2026-10-31 KST
TASK_ID=CONVERSION-DX9EX-01605
PRODUCTION_ID=CONVERSION-DX9EX-01605
EVENT_ID=CONVERSION-DX9EX-01605-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
MODE=DX9EX_REVIEW_ONLY
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=5ac6cf7e78f107edf480f12ddb3a32e521ab6c65
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD_PRECOMMIT_RECHECK_MATCHED
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
ROOT_CAUSE=UNCONFIRMED
NEW_FINDING=STATIC_POSITIVE_DIAGNOSTIC_OVERINCLUSION: LENS family and R30 lens physical telemetry can label non-flare PMT transactions under a broad SceneEffect/opaque-flush scope. This is an audit of diagnostic evidence authority, NOT a runtime-proven game defect.
NEW_RUNTIME_FINDING=NONE
AUTOMATION_VALIDATION=DOCS_ONLY_COMMIT_READBACK_PENDING
RUNTIME_VALIDATION=UNTESTED
SCORE_DELTA=0;STATIC_DIAGNOSTIC_BOUNDARY_NOT_AN_INDEPENDENT_OPTICAL_FIX

## Distinct falsification objective

01604 constrained **negative evidence**: after a C993 original source wrapper ends, a late 4052C0 PMT can execute with non-projected effective scope, omitting scope-gated R30 LENS PHYSICAL and LOWER FALLBACK telemetry. This task audits the **opposite inference**: does a positive LENS trace or PHYSICAL CORRELATION line uniquely identify a C993/CABE flare material? The actual R30 boolean has no such object-identity requirement. The result is a precise conditional false-positive risk, not proof that the reported double centre or head-follow occurred on this source SHA.

## SOURCE_TRACE — inspected GitHub code, one-based line ranges

1. src/hooks_graphics.cpp:626-755: VRLensFlareProjected2D original source and TraceLensOpaquePmtEntry. On a traced opaque flush and telemetry, each 405890->404700 entry gets a scoped PMT serial, entry[14] objectId, object/node/mesh/pass, and PRE/POST receipt. The printed sourceCallSerial comes from the enclosing flush, which may be a deferred window, and is NOT equivalent to this PMT's original source creator.
2. src/hooks_graphics.cpp:785-898,1293-1330: TraceLensOpaqueFlush handles 405360 inline 542A and scene D44B/D79B 4052C0. Scene flush has trace eligibility without any lens-source serial. Scoped flush serial persists during original 4052C0; 5A41 and 5C44 wrap each original 405890->404700 callback only. Original CALL is forwarded exactly once.
3. src/hooks_graphics.cpp:997-1128,1137-1290: original CABE outer path retains two 0x570008 ordinals; C993 exact projected family is 0x570002/006/00F/010, source scope/serial is call-lifetime and not a durable opaque queue descriptor.
4. src/vr/game/render_semantics.hpp:880-993: CurrentLensOpaqueFlush and CurrentLensOpaquePmtEntry are thread_local RAII receipts, not a renderer ownership override. PMT receipt exists during the original 404700 call and restores prior value afterwards.
5. src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:4522-4543 (R30CaptureVisualRouteTrace): trace.lens is TRUE on any one of LensFlareCentre producer, PMT serial, opaque flush serial, inline serial, deferred serial, ProjectedScreenEffect2D scope, or SceneEffect scope. Family=LENS and visualRoute.enabled can thus cover non-flare scene PMTs; the boolean has **no objectId or texture equality**.
6. Same R30:6490-6655,6720-6855 (R30TryScreenSpaceFovDraw): lensPhysicalCandidate is separately true after baseAdmitted only if telemetry and effective scope=ProjectedScreenEffect2D OR SceneEffect. The LENS PHYSICAL CLASS sample has first-32/powers-of-two sampling; PHYSICAL CORRELATION includes PMT serial/objectId/mesh/pass if present. Positive family/correlation alone cannot certify a flare-specific source.
7. Same R30:6863-6923,7060-7160,7270-7370,7605-7639: subsequent semantic-route admission, actual L/R Draw HRESULT and restore are separate from PMT log; physical RESULT has conditional sampling, lower fallback depends on scope. Two intentional eye draws are normal.
8. vrhost/src/main_r23.cpp:3860-3942 and vrhost/src/runtime/r24_black_screen_guard.hpp:584-640: host bootstrap/fallback and final R24 EndFrame acceptance can differ from source PMT/native Draw. Not exercised on a headset this task.

CURRENT_SOURCE_BLOBS=hooks_graphics.cpp:982f55dc91c00faf336c06317006fe4aba11db1a;R30:83a2821bd53d043d7df0557f46627d0af1205d48
BASELINE_BLOBS=R26+HUD_hooks_graphics.cpp:5651e2239ed2c894d65a0d140d0c1d0a170b96e7;R30:0525d1cf53393902b5415bcb139cb55286673aaa
BASELINE_COMPARISON=The current named TraceLensOpaqueFlush/TraceLensOpaquePmtEntry and R30CaptureVisualRouteTrace helpers are absent by those exact names in the pinned R26+HUD baseline files. Their addition establishes extra diagnostic categorization, NOT an HMD-certified optical improvement.

## Static gate truth table — predictions ONLY

| Hypothetical entry with telemetry enabled | visualRoute family | R30 lensPhysicalCandidate after baseAdmitted | Inference |
| --- | --- | --- | --- |
| C993 0x570002, qualifying projected scope, inline opaque PMT | LENS | true | Likely source-family candidate; exact original PMT object/tex/native and eye RGB still required. |
| **Non-flare PMT** in a scene D79B 4052C0 flush, effective SceneEffect | **LENS** | **true** | Generic original PMT may emit a LENS-family/PHYSICAL line even though it is not lens artwork. This is a **code-permitted negative control**, not an observed unrelated PMT. |
| Late 0x570002 PMT in traced flush, effective scope None | LENS | false | A LENS-family trace can coexist with absent scope-gated PHYSICAL telemetry; inherited 01604 false-negative boundary. |
| SceneEffect draw without lens source/opaque PMT receipt | LENS | true | Scene semantic alone is sufficient to enable both gates; no authenticated flare object follows. |
| Original opaque PMT outside a traced flush, effective scope None | not necessarily LENS | false | PMT serial absent; missing flare log cannot prove absence of GPU work. |

The original opaque flush is a **multi-object** queue; its receipt serial is flush identity, not PMT identity. PMT callback objectId is independent of flush source-window serial; compare it first. Even a source-authenticated PMT with successful pairComplete L/R is not yet a physical pixel or accepted OpenXR-eye proof.

## HYPOTHESIS_LEDGER

| ID | Status | Previous evidence -> this distinct evidence | Counterexample/falsifier |
| --- | --- | --- | --- |
| A duplicate original flare emitter | OPEN | C993 four IDs and both CABE 570008 original ordinals preserved; positive LENS family cannot count emitter instances. | Prove excess same-source call and actual PMT material beyond canonical fan-out before same-eye RGB. |
| B opaque/D3DX/native replay | OPEN; BLOCKED_RUNTIME | 01604 showed negative scope log gap; now positive LENS family can over-count non-flare SceneEffect PMTs. Neither proves replay. | Exact same PMT+pass makes two successful distinct **same-eye** native RGB writes beyond expected layering. |
| C wrong L/R projection/screen-fixed | OPEN_OPTICS | Scope/family booleans do not show raw c64, projection FOV or depth. | Exact C993 PMT native c64 and L/R optical centroids for two known head yaws. |
| D intended disc/glow layers | OPEN | Source 570008 ordinal1/2 and four C993 objects are not one flat draw; broad LENS logs have no texture/alpha equivalence. | PMT object/mesh/pass/tex0/alpha and same-eye RGB isolate one duplicated material rather than distinct legitimate layers. |
| E host reuse/compositor | BLOCKED_RUNTIME | Host accepted XR layer depends on R19/R24, not the broad renderer LENS label. | Native fresh per-eye ROI joined to accepted XR frame/sourceFrameId/PresentQPC/arrayIndex/pose. |
| F camera/WVP head synchronization | OPEN | No physical source pose/c64 or HMD yaw evidence from the boolean trace. | Same world-sun bearing, two yaw poses, original c64 writeSerial and accepted L/R eye centroids. |
| T positive LENS means authenticated flare PMT | REFUTED_AS_SOURCE_INFERENCE; NOT_RUNTIME_CAUSE | Source OR-gates allow SceneEffect/opaque PMTs with no checked flare ID. | Show a separately verified upstream invariant that all such PMTs necessarily belong to the sun-flare family; the present predicate does not enforce it. |

## EVIDENCE / EVIDENCE_GAPS

EVIDENCE_SOURCE=CONNECTED_GITHUB_CURRENT_BRANCH_PINNED_SHA_AND_PREVIOUS_01604;OR_GATE_AND_PMT_RAII_SOURCE_READ;IMMUTABLE_BASELINE_BLOB_COMPARISON
EVIDENCE_DISASM=INHERITED_REPO_REA_D3A5_C993_CABE_405360_4052C0_405890_404700;NO_FRESH_CANONICAL_RETAIL_BYTES
EVIDENCE_LOG=NO_NEW_CAPTURE;PREDICATE_AND_FORMAT_STRING_REVIEW_ONLY
EVIDENCE_USER_REPORT=HISTORICAL_QUEST3_DOUBLE_CENTRE_HEAD_FOLLOW;NO_CURRENT_SHA_REPRODUCTION
EVIDENCE_GAPS=No canonical EXE byte recheck of PMT entry[14]/pass offsets; no actual non-flare control PMT recorded in one scene flush; no original queue descriptor-to-sourceCallSerial proof, no native per-eye RGB delta, no authenticated same-eye duplicate, no host accepted XR eye/pose/arrayIndex join; no matched Quest3/VDXR two-yaw test.

## NEXT_FALSIFICATION_TEST

1. Read-only exact-game-source run: capture ONE C993 0x570002 plus CABE 0x570008 ordinal1 and ordinal2 in one source frame. Record sourceCallSerial/sequence/QPC and Flush PRE/POST origin/serial/patch ledger; preserve intended call count. A source window is never PMT identity.
2. For D79B (or D44B), capture the actual 405890->404700 entry callbacks of **all** PMTs during one 4052C0. Before trusting entry[14]/pass, independently check canonical EXE operand/layout evidence. Seek an actually observed non-lens control PMT in the same flush. Compare its PMT objectId, mesh/pass and actual LENS family log. Expected if such control exists: trace.lens remains true, even for non-lens ID, because scene/flush/PMT gates are broad.
3. Join PMT entry serial+flush serial to R30 TopLevelDrawSerial, effectiveScope, baseAdmitted, screenKind, tex0, RT and PHYSICAL RESULT or lower chain. Separate diagnostic family from exact PMT and source identity. If all observed scoped PMTs are lens artwork, this specific *observed* false-positive scenario is falsified for the capture; the static broad predicate remains.
4. For exact verified flare PMTs, check L/R actual HRESULT/restore and pre/post same-eye ROI; then join fresh sourceFrameId/QPC and final R19/R24 accepted XR layers/pose/arrayIndex. Two L/R draws alone are expected. Same PMT+pass twice in one eye with two ROI writes supports B; one native ROI yet two final XR lobes prioritizes E; correct multiplicity but yaw mismatch prioritizes C/F.
5. Only a matched exact-SHA Quest3/VDXR two-yaw test can promote head-lock or stereo to a measured result. Otherwise preserve UNTESTED and all runtime hypotheses.

NEXT_REVIEW=LENS_FLARE:SCENE_D79B_405890_NONFLARE_PMT_ENTRY14_CONTROL_VS_C993_LENS_FAMILY_LR_R19_R24
NEXT_FALSIFICATION_TEST=SCENE_D79B_PMT_ENTRY14_NONFLARE_CONTROL_AND_EXACT_SAME_EYE_ROI
PATCH_CANDIDATE_ONLY=CONDITIONAL_READ_ONLY_DIAGNOSTICS_NOT_APPLIED: If actual non-flare PMTs are falsely treated as verified lens draw by a log consumer, separate family candidate from PMT/source-authenticated flare evidence at src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:4522-4543 (R30CaptureVisualRouteTrace), 6490-6655,6720-6855 (R30TryScreenSpaceFovDraw) using existing PMT entry fields from src/hooks_graphics.cpp:700-755 and flush provenance from 785-898. Never change renderer route, PMT replay, two 570008 ordinals or source owner from a diagnostic label. FALSIFIER: no misattribution in bounded existing evidence or offline filtering suffices; then PATCH=NONE.
REGRESSION_RISK=DOCS_ONLY_NONE;POTENTIAL_FUTURE_DIAGNOSTIC_EDIT_MUST_PRESERVE_C993_FOUR_ORIGINAL_OBJECTS_BOTH_CABE_570008_ORDINALS_PMT_ORDER_ALPHA_TEXTURE_R26_HUD_STEREO_DEPTH_RIGHT_EYE_RESTORE_HOST_FRESHNESS
NEW_DEFECT_PROVEN=NO
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01605.md
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
