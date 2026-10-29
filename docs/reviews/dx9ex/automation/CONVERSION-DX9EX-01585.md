# CONVERSION-DX9EX-01585 — CABE deferred-vs-C993 projected-ray ownership split (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01585
PRODUCTION_ID=CONVERSION-DX9EX-01585
EVENT_ID=CONVERSION-DX9EX-01585-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=52a1fa3aad464a7637242459f9a3eca026353e08
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HEAD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_RESEARCH_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
AUTOMATION_VALIDATION=REMOTE_DOCS_ONLY_COMMIT_AND_READBACK_REQUIRED
RUNTIME_VALIDATION=UNTESTED

## Narrow question and predecessor contrast

The user reports a doubled/split and partly head-following lens flare. The report is an observation, NOT proof of reproduction or cause on SOURCE_HEAD. 01582 checked R24 final quad versus a requested binocular projection; 01583 separated R24 Direct Projection cache from classic Theater; 01584 checked classic Theater cached-image refresh starvation. This task does **not** re-credit those host findings. Instead it follows a different, still unresolved native source boundary: whether CABE's delayed physical **opaque** draws can retain the same *projected-ray ownership* as a current C993 central-family draw, before any host capture, while the two are parts of the same lens flare. Both original 0x570008 calls are preserved; L/R drawing twice is normal and not itself duplication.

## NEW_FINDING — static owner-lifetime asymmetry; optical causality unproved

NEW_FINDING=STATIC_CABE_C993_SOURCE_WRAPPERS_HAVE_DIFFERENT_RENDER_SEMANTIC_LIFETIMES_IN_CURRENT_FOCUS_HEAD;_C993_570002_570006_57000F_570010_USE_EXPLICIT_PROJECTED_SCREEN_EFFECT_SOURCE_OWNER_WHILE_CABE_USES_SCOPED_RENDER_SEMANTIC_THAT_MAY_EXPIRE_BEFORE_OPAQUE_4052C0_PHYSICAL_DRAW;_R30_PROJECTED_RAY_VS_SCENE_EFFECT_FLAT_PERSPECTIVE_HUD_OR_LOWER_FALLBACK_ARE_DISTINCT_POSSIBLE_NATIVE_OPTICAL_ROUTES;_NO_OBSERVED_SAME_FRAME_ROUTE_SPLIT_OR_QUEST3_CAUSAL_PROOF.

1. **Source boundaries, not one generic flare:** original disassembly/decomp citations in the current hook source identify EXE C993 (sub_40C980) for the centre screen-space family and CABE (sub_40C9A0) for outer discs; original 0x570008 occurs twice. Latest `src/hooks_graphics.cpp:1137-1157,1158-1189` explicitly enumerates C993 four objects `0x570002/0x570006/0x57000F/0x570010`. `DrawObjectAlphaCentre:1271-1290` sets `ScopedExactProducerSemantic(ProjectedScreenEffect2D, ..., ProducerToken::None)` plus `ScopedRenderSemantic(ProjectedScreenEffect2D)` and invokes the original alpha draw inside those scopes. It is not a second emitter and does not suppress a source object.
2. **The CABE lifetime is materially different.** `DrawObjectAlphaProjected:997-1135` assigns only `ScopedRenderSemantic(ProjectedScreenEffect2D)` for its original `Game::DrawObjectAlpha_Internal` call at :1107-1113, then tracks a diagnostic `CurrentLensDeferredPhysical` window after ordinal1 returns (:1115-1134). The code itself documents an optional `405360 -> 4052C0` flush **inside** the source call and a later scene `4052C0` flush **after** it (:1225-1232, :1115-1119). Consequently, inline immediate consumption could inherit the wrapper's temporary projected scope, whereas a later opaque-queue physical draw cannot be assumed to inherit that same wrapper scope. The deferred ordinal1 interval is an observational candidate, not object/scope/PMT authority. `render_semantics.hpp:871-886,1434-1441` and `stereo_renderer_r30_r26_safe.cpp:6313-6357,6420-6436` explicitly separate exact call-stack receipt from non-exact deferred physical identity. No observed CABE actual-eye classification is present in this read.
3. **Different R30 paths are real, not synonymous labels.** On current branch, `R30ClassifyScreenSpace` at `stereo_renderer_r30_r26_safe.cpp:2343-2349` returns `ProjectedScreenEffect2D` immediately for current projected scope. The separate `SceneEffect` branch at :2378-2415 requires perspective projection and an owned raw WVP, and classifies `FlatHud` as `PerspectiveHud` (the 2026-10-30 source comment says a prior deferred-ray promotion split the whole flare; this is *historical in-code commentary*, not a runtime test of this SHA). If source ownership is not admitted, `R30TryScreenSpaceFovDraw` can return `E_NOTIMPL`, and `R30Try.../lower` at :7380-7440 takes the R29 path. The exact 0x570008 native physical route must be read from `VR TRACE LENS PHYSICAL RESULT FULL` or `VR TRACE LENS LOWER PHYSICAL RESULT FULL`, not inferred from a CABE source log.
4. **Different optical transform at the projected-ray route:** `R30BuildScreenSpaceEyeConstants:5525-5603` uses a source stock WVP, matching `headSequence == stereo.poseSequence`, `GetLatchedHeadInverse`, identity eye translation (zero IPD translation), and **separately** `ProjectionFromFov(stereo.eyeFov[eye])` followed by `LensCentre::BuildProjectedSunRay`. This does NOT mean byte-identical L/R WVP: asymmetric FOV can produce distinct eye matrices for one ray. `R30TryScreenSpaceFovDraw:6679-6685` requires the exact projected scope. The `SceneEffect/FlatHud -> PerspectiveHud` and lower paths have different WVP admission/correction gates; matching apparent sun position between such branches is therefore NOT guaranteed by sharing a sun sequence or texture.
5. **Protected baseline differential, not automatic promotion:** `R26+HUD@0cff83c` `hooks_graphics.cpp:657-695` restricts the C993 `0x570002` exact source to conditional `WorldBillboard` under matching D3A5 call depth, nonqueue path and `LensFlareCentre` token; other C993 calls do not receive that scope. The same baseline `stereo_renderer_r30_r26_safe.cpp:2205-2235` sends `semanticProjectedScreen || semanticSceneEffect` through owned WVP + `SpatialBillboard/FlatHud` matrix classification, unlike latest's early `ProjectedScreenEffect2D` dispatch. Thus the current code changes **the potential source-to-eye interpretation**, not merely telemetry. R26+HUD remains the immutable HMD baseline; its old behavior is not asserted correct or incorrect for this specific flare. The recent HUD comparison SHA and R84 are NOT HMD PASS.
6. **Host negative control remains required:** R19 `sbs_capture_override.hpp:1374-1437` left-crops an SBS source for a mono `ViewSpace/BOTH` Theater quad; R24 `r24_black_screen_guard.hpp:416-445,479-575` can instead reuse a cached quad before live Theater refresh. Such a downstream mono layer may erase native per-eye differences. This task's CABE/C993 native-path explanation applies **only if** the final accepted XR path was a fresh true binocular projection (or the source-frame L/R RGB already shows distinct flare lobes). It cannot account for an observed HMD split on its own; no exact tick was traced.

### HYPOTHESIS_LEDGER

| ID | State | Inherited evidence and new 01585 discriminator | What would refute / distinguish |
| --- | --- | --- | --- |
| A — extra game-origin 0x570008/C993 source emitter | OPEN | Two original 0x570008 source calls are preserved; latest C993 enumerates four IDs, not extra source emission. Wrapper entry count != GPU primitive count. | Same original frame identifies an unauthorized third source call versus canonical emitted IDs with exact object/PMT fingerprint |
| B — deferred CABE native/PMT/queue resubmit | OPEN | 01580 PMT verification gap inherited. NEW: CABE wrapper scope can end before later opaque physical execution, and time-window does not authorize identity. | Exact 405890->404700 PMT object/pass plus unique native DP/DIP ID and per-eye RT prove each physical primitive executed once |
| C1 — C993 vs CABE native stereo classification divergence | SUPPORTED_CONDITIONAL_STATIC_NOT_RUNTIME | NEW: current exact C993 projected-source admission vs a CABE deferred wrapper scope with unproved persistence; R30 ProjectedScreenEffect2D differs from SceneEffect FlatHud PerspectiveHud and lower owner. | Joined actual CABE + C993 native draws show same projected-ray route, matching source-ray/pose/FOV/RT matrix class on one frame |
| C2 — current C993 per-eye FOV uses identical WVP | REFUTED_AS_GENERAL_SOURCE_INFERENCE | `ProjectionFromFov(stereo.eyeFov[eye])` is computed per eye. A zero-IPD angular ray may legitimately have per-eye WVP differences. | Actual both FOV values equal and projected hashes equal *on the inspected tick* would establish equality for that tick only |
| D — distinct intended center/halo/ghost materials | OPEN | Four C993 IDs and two 0x570008 source calls are independently real source families; source list alone does not distinguish unintended pixel lobes. | Full primitive texture, blend, pass, alpha and pre-host same-eye ROI rule out separate ghost materials |
| E — host R24 cached/live one-quad depth collapse | SUPPORTED_CONDITIONAL_STATIC_INHERITED | 01582-01584 host claims inherited without re-credit. NEW route analysis is pre-host and cannot prove the accepted host layer. | Symptomatic tick carries accepted exact two-eye `xrEndFrame` projection, no cached/live Theater quad |
| F — HMD-local/source-camera double correction | OPEN | C993 projected path uses head-inverse and matched pose, but CABE physical path not joined; matched 2-yaw sun source unavailable. | Joined source ray, camera sync and final two-yaw head orientation prove world-constant angular bearing, or show a single common host ViewSpace quad instead |
| G — reported *entire* split flare root cause is mixed native routing | BLOCKED | A current-source conditional route split is plausible but no same-frame physical CABE/C993 eye route, alpha ROI or final XR identity; do NOT call it repaired/reproduced. | Same-frame exact-source traces demonstrate uniform physical route with correct L/R screen positions while the HMD split persists; or a sole mono host layer explains observed frame |

### SOURCE_TRACE / evidence type

- GitHub pinned latest `52a1fa3aad464a7637242459f9a3eca026353e08`, `AGENTS.md`, optical route policy, predecessors `01580,01581,01582,01583,01584`; no production file modified.
- Current `src/hooks_graphics.cpp` blob `982f55dc91c00faf336c06317006fe4aba11db1a`: `VRLensFlareProjected2D::DrawObjectAlphaProjected:997-1135`, `IsProjectedSunScreenObject:1145-1157`, `DrawObjectAlphaCentre:1158-1290`, hook installs :1300-1340.
- Current `src/vr/game/render_semantics.hpp` blob `f5b2403f59185993930e853edee42d639e1ff454`: `LensOriginalCallReceipt:871-886`, `CurrentRenderProducerToken:1434-1441`, `DrawCommand` C993 owner/XYZRHW restriction :1480-1510.
- Current `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` blob `6827f864b966ca743dff35725cc9ad9c9e96cc3b`: `R30ClassifyScreenSpace:2343-2349,2378-2415`, `R30BuildScreenSpaceEyeConstants:5525-5603`, `R30TryScreenSpaceFovDraw:6650-6710,7050-7255`, `R30Try... lower fallback:7380-7465`, physical trace :7050-7255 and :7280-7330.
- Baseline pinned `0cff83cf509c2acd6f3391b3a46c4dec1403a0d9`: `src/hooks_graphics.cpp` blob `5651e2239ed2c894d65a0d140d0c1d0a170b96e7`, `DrawObjectAlphaCentre:657-695`; `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` blob `0525d1cf53393902b5415bcb139cb55286673aaa`, old semantic SceneEffect/ProjectedScreen branch :2205-2235.
- Downstream comparison only: `vrhost/src/runtime/sbs_capture_override.hpp:1374-1437`; `vrhost/src/runtime/r24_black_screen_guard.hpp:416-445,479-575,625-777`.
- EVIDENCE_SOURCE=GITHUB_PINNED_STATIC_CALLS_BRANCHES; EVIDENCE_DISASM=ORIGINAL_EXE_REA_AND_R4DIUS_REFERENCED_BY_SOURCE_NOT_REEXECUTED_THIS_TASK; EVIDENCE_LOG=NO_EXACT_SHA_FRAME_MATCHED_LENS_LOG_READ; EVIDENCE_USER_REPORT=FULL_FLARE_SPLIT_AND_HEAD_FOLLOWING_IN_QUEST3_REPORT_NO_VERIFIED_SOURCE_JOIN; EVIDENCE_HMD=NONE_THIS_TASK.

### EVIDENCE_GAPS / NEXT_FALSIFICATION_TEST

EVIDENCE_GAPS=No same-exact-SHA CABE ordinal/PMT pass -> native Draw ID + entry/left/right RT -> R30 classification/eye WVP -> original SBS L/R flare ROI -> host accepted XR layer and headset 2-yaw ROI. `CurrentLensDeferredPhysical` is an interval, not exact PMT identity. The 2026-10-30 Quest3 claim in an R30 source comment cannot be assigned to this pinned head without package/eye-tick evidence. Physical draw L/R HRESULT success does not establish displayed pixels, correct depth or host acceptance.

NEXT_FALSIFICATION_TEST=Capture one authentic source-joined sun sequence (the four C993 IDs plus the two 0x570008 CABE ordinal calls) under matching R26+HUD baseline and latest focus source/config. For each sourceCallSerial/opaqueFlushSerial/PMT serial/pass, collect exact 404700 objectId, texture, DP/DIP/primitive, physical R30 `kind`/scope, `VR TRACE LENS R85 BUILD`, `VR LENS R30 PHYSICAL EYES` raw/left/right WVP hashes/FOV, and `VR TRACE LENS LOWER PHYSICAL RESULT FULL`, with framePresentQpc. Positive split discriminator: exact C993 physical draw has kind ProjectedScreenEffect2D + BuildProjectedSunRay and source-matched CABE physical 0x570008 has kind PerspectiveHud or R29 lower fallback, plus differing same-eye flare ROI or eye-ray placement; this supports native route divergence, not necessarily defect. Negative: both physically projected to same angular ray with correct L/R ROI, or final R24 ViewSpace/BOTH flat quad used, rules out this mechanism for that HMD frame. Check source alpha/texture/fingerprints to distinguish two *intended* 0x570008 objects from duplicate emission. Two head yaw poses with stable light bearing and accepted `xrEndFrame` per-eye projection required for optical verdict; unknown IDs/failed PMT joins remain UNKNOWN, not inferred.

PATCH_CANDIDATE_ONLY=DIAGNOSTIC_ONLY_NOT_APPLIED: In a separately authorized change (NOT this REVIEW_ONLY task), `src/hooks_graphics.cpp:997-1135,1158-1290` could label CABE/C993 source timestamp and opaque flush serial without expanding scope; `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2343-2415,5525-5603,6650-6710,7050-7255,7380-7465` could emit a bounded once-per-physical-primitive projected/flat/lower decision and joined PMT+texture+L/R WVP/RT/HRESULT, preserving unknown provenance as UNKNOWN. Only after a *matched native physical draw* exhibits misrouting should an exact object+pass route/lifetime fix be considered; do NOT globally force CABE WorldBillboard or project all alpha/PMT, suppress either legitimate 0x570008, or re-add risky B9200 post-CALL/+5 hooks. Preserve R26+HUD and exact fallback safety.
REGRESSION_RISK=DOCS_ONLY_NONE; future semantic propagation changes could mis-tag multi-object opaque queues, double-apply head correction, lose expected halo/ghost textures, introduce duplicate or missing stereo layers, regress native C993 sky-adjacent rays, poison left/right state and alter cached Theater fallback. Probe only a source-proven lens fingerprint; separate CI/static evidence from Quest3/VDXR HMD verification.
NEW_FINDING_STATUS=SOURCE_STATIC_PLAUSIBLE_MECHANISM_NOT_ROOT_CAUSE
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:CABE_570008_ORDINAL1_OPAQUE_4052C0_PMT_TO_PHYSICAL_R30_PROJECTED_VS_PERSPECTIVEHUD_OR_LOWER_ON_SAME_XR_TICK
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01585.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01585]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01585.md
