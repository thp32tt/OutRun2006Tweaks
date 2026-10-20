# CONVERSION-DX9EX-01075 — R26 exact result HUD physical VS admission REVIEW_ONLY

- DATE: 2026-10-20 KST
- TASK_ID: CONVERSION-DX9EX-01075
- PRODUCTION_ID: CONVERSION-DX9EX-01075
- EVENT_ID: CONVERSION-DX9EX-01075-E001
- EVENT_TYPE: dispatch
- TARGET_BRANCH: vr-d3d9ex-focus
- SOURCE_HEAD: a92d6b86676337b870e5b84cd86144b7d3ff6498 (latest source-bearing revision reviewed; later a7e996412ceb6c3ab80bcd3ac75ea956c7a02b82 is docs-only task 01076)
- BASELINE: R26+HUD 0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 (preserve user-verified compiled reference)
- COMPARISON_ONLY: aab9e02bcb2ad2e6253840e6267e5c5ad5040854 (NOT HMD PASS)
- MODE: DX9EX_REVIEW_ONLY
- CODE_CHANGE: NO
- REVIEW_SCOPE: +TIME/GOAL/result R26 shader-c64 vs fixed-function physical GPU owner admission across cached VS / live device VS state, semantic/queue, native D3DX, two-eye restore and Present/OpenXR.
- NEW_FINDING: CONDITIONAL_STATIC_GATE_ASYMMETRY_R26_SHADER_VS_CACHE
- PATCH_CANDIDATE_ONLY: YES
- RUNTIME_VALIDATION: UNTESTED
- AUTOMATION_VALIDATION: DOCS_ONLY_REVIEW_RECORDED; check exact resulting commit and changed file list separately (source-build gates not applicable)

## Task disambiguation and earlier evidence

- `docs/automation/runs/CONVERSION-DX9EX-01075.json` **already exists** at source HEAD but is a legacy source-implementation-era checkpoint: `IMPLEMENTED_AWAITING_EXACT_SHA_CI`, material SHA `fa653e442e322baa2fa5047059e260020dacd3e5`. The 2026-10-20 REVIEW_ONLY directive supersedes its `next_action`; do **not** resume its CI/source repair or rewrite the JSON.
- `01074.json` investigated start shadow original c64 serial N-1; `01073.json` investigated R84 GOAL fixed-function/shader physical source. Those are distinct from this **R26+HUD** cached-versus-live shader admission boundary.
- Earlier `docs/automation/reviews/R26_RESULT_HUD_RANK_LENS_CROSSREVIEW_20261020.md` flagged missing shader eye cant at an earlier code SHA. **Current** `stereo_renderer_r30_r26_safe.cpp:4698-4793` now applies `BuildStageEyePoses` for exact result shader HUD. Do not repeat the superseded claim that this current code always uses identity eye orientation. This review isolates a separate **admission** gate.
- Concurrent `01076.md` reviews x64 host menu-projection cache invalidation, not this game's R26 HUD shader owner. No R84 autopromotion.

## Source → draw → Present/OpenXR static walkthrough

1. **Original/REA producer:** Original mode switch VA 0x00498670, exact +TIME calls 0x0049898E and 0x00498A36, and text 0x004989AD/0x00498A10/0x00498A89 are documented in `docs/research/REA_STAGE_EXTENSION_MODE2_SOURCE_SCOPE_20261019.md` (original executable hash pinned there). **Mode 2 0x00498AC6 is NOT +TIME.** GOAL glyph parent original 0x004B9200 has 19 stack-verified E8 return PCs at `src/vr/game/goal_result_parent_provenance.hpp:7-43`; never install +5 post-CALL hooks.
2. **Producer → semantic → original queue:** `src/hooks_uiscaling.cpp:1660-1735` StageExtensionEnter/Leave selects exact `StageExtensionTime`, snapshots stable sprite queue roots/tails, tags eligible appended nodes and shields pending one-shot. GOAL helper 0xBE020/0xBE150 receives distinct tokens at `:1819-1874`. `src/vr/game/render_semantics.hpp:211-245,998-1028,1296-1432` requires ScreenHud + exact named producer and physical queue node/epoch when queued. REA `docs/automation/REA_99_RENDER_FUNCTION_VALIDATION_20261019.md` identifies queue renderer original VA 0x0042D710, D3DXSprite Begin/Draw/End 0x00429C60/0x0042A0A0/0x00429F60 and direct draw 0x0042C0F0 (static partial edges, not an HMD trace).
3. **CPU Draw vs physical native draw:** `src/hooks_uiscaling.cpp:3340-3429,3720-3845` snapshots D3DX `HudBatch` on actual Draw, protects homogeneous per-producer batch at `FlushDest/EndDest`, suppresses unproven direct producer while native driver submits previous mixed work, and preserves native HRESULT. Neither a CPU text callback nor queue label alone establishes the *final* GPU API.
4. **Physical selector:** `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5293-5369` routes DrawIndexedPrimitive through external F11 exclusion, R62 indexed D3DXSprite FVF=0x142, XYZRHW candidate, shader/c64 screen-space route, then R29 original fallback. DP/DPUP/DIPUP are separate entries `:5268+,5372-5433`; do not infer them from one DIP telemetry hit.
5. **Exact finite plane and L/R:** `R30IsExactResultHudDraw():3028-3038` checks physical command exact producer and queued node/epoch. R26 XYZRHW `:3192-3248` and shader c64 `:4698-4793` apply exact `BuildStageEyePoses`; `src/vr/d3d9/stage_extension_eye_plane.hpp:25-46` retains eye-local orientation/relative IPD. R62 `:5058-5206` builds each fixed-function eye projection with a *live* vertex shader getter.
6. **GPU right eye and restore:** `R30ExecuteXyzrhwStereo():3785-3899` submits left, swaps right RT/depth/viewport, submits right, restores state and poisons failed-right/incomplete frames; shader HUD `:4804-5029` similarly handles original c64 and state restore. `R62:5208-5255` restores original projection and logs producer/epoch, left/right HRESULT and incomplete flags. An individual left success is not binocular acceptance.
7. **Present/host:** `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:1486-1506` passes Present down; `src/vr/d3d9/stereo_renderer.cpp:676-818` checks world-seeded pose, both-eye GPU/frame validity and transport, publishes the stereo frame **only** after game Present succeeds, else flags mono/fallback. x64 host's actual xrEndFrame display, pose provenance and Quest3 optics were **not executed**. A source code route cannot certify final HMD output.

## NEW_FINDING — exact R26 shader path retains an asymmetric *admission* precondition

**Confirmed source facts (not a runtime failure report):**

- `R30PrepareXyzrhwState():2434-2472` bypasses potentially stale `CurrentVertexShaderIdentity != 0` cache hint **only for exact result**, and then requires `device->GetVertexShader()==nullptr` and XYZRHW FVF. `R62TryFixedFunctionSpriteIndexed():5058-5085` applies the same exact-result bypass and rejects a *real* non-null shader. Both explicitly mention D3DX StateBlock cache drift.
- **Different shader rule:** `R30BuildScreenSpaceEyeConstants():4454-4463` immediately returns false on `CurrentVertexShaderIdentity == 0` before asking whether the live device actually has a VS. `R44GetOwnedRawOverlayWvp():1921-1939` also rejects zero cached identity before original-game raw c64/epoch lookup. This is a source-level asymmetric rule across exact-result GPU API families; eye-cant math after this point has already been updated.
- Conditional implication: if one **source-proven exact shader result physical draw** ever has cached VS=0 but **live VS != null**, the new R26 shader head-local eye pose cannot be reached through this entry and the original/fallback branch is selected instead. Whether that precondition occurs with the user's installed R26 binary is **UNPROVEN**; StateBlock comments demonstrating stale-positive cache do not establish stale-zero cache.
- This could explain incomplete shader-family coverage/head-follow only if correlated with a real final GPU Draw and frame fallback; **it is not a proven root cause of today's HMD symptom.**

**Contradictory evidence / falsification:** For every exact shader result draw, compare cachedVS, `GetVertexShader` HRESULT and pointer, original game shader/c64 generation, poseSeq, queue node/epoch and actual API. If cache is never zero while a real shader is bound, or all exact result GPU output is FVF142/XYZRHW without shader-c64 draws, classify this hypothesis as `NOT_OBSERVED`. If a cache mismatch exists but original c64/epoch is invalid, the correct behavior is still conservative native fallback, not forced stereo.

## PATCH_CANDIDATE_ONLY (zero modifications this task)

- **Candidate A / conditional review:** `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp`, `R30BuildScreenSpaceEyeConstants()` **lines 4454–4463** and `R44GetOwnedRawOverlayWvp()` **lines 1921–1955**. Only *after* same-draw cached-zero/live-nonzero evidence, evaluate a **narrow exact shader result** live-device identity decision with mandatory original-game c64 shader+epoch+pose+queue proofs. No global shader ownership promotion; never accept injected eye c64 as the original.
- **Candidate B / diagnosis only:** same file, `DrawIndexedPrimitiveDestR30()` **lines 5293–5369**, `R30TryScreenSpaceFovDraw()` **lines 4804–4890**, `R62TryFixedFunctionSpriteIndexed()` **lines 5058–5255**. Correlate per physical Draw ID and queue epoch: producer, DP/DIP/UP API, cache/live VS, FVF, left/right draw HRESULT, projection restore, `FrameStereoIncomplete`, game Present result, host frame ID and XR submit. Existing `RESULT_HUD_REJECT` is DIP-local and is not a complete source-to-HMD trace.
- **No source patch, refactor, branch/ref move, merge, build, package or release** is authorized. Any implementation needs a separate user-directed task.

## REGRESSION_RISK and exclusions

- HIGH: Weakening raw c64 or queue/epoch identity may cause old road/world shader reuse, double head transforms and corrupt rival/rank or SkyGlow. Protect unclassified physical draws' single original fallback.
- HIGH: Do not flush unknown/mixed D3DX batches globally; preserve direct +TIME/GOAL source lifetime, ResultText B9200 stack-only proof and explicit mode-2 exclusion. **No B9200 0x97C57+5 / 0x97E6D+5** hooks.
- HIGH: Keep R26+HUD `0cff83cf` HMD binary baseline. Never automatically select R84 or equate `aab9e02` candidate with runtime PASS.
- MEDIUM: Source game pixels, physical viewport and XR eye extent differ. Evaluate cant in yaw/pitch/roll, asymmetric FOV and ray convergence, rather than identical L/R pixels; preserve F11/ESC and user input/FFB.

## EVIDENCE, status and NEXT_REVIEW

- EVIDENCE: GitHub-pinned source paths/line ranges above, `docs/automation/runs/CONVERSION-DX9EX-01073.json`, `01074.json`, `01075.json`, `docs/automation/reviews/R26_RESULT_HUD_RANK_LENS_CROSSREVIEW_20261020.md`, `DX9EX_HMD_REFERENCE_20261020_0CFF83CF.md`, original executable SHA-pinned REA summaries. No N100/Drive authority substituted for GitHub.
- AUTOMATION_VALIDATION: STATIC_SOURCE_AND_REA_DOCS_REVIEW; verify commit changed paths are **only this Markdown**. Not a Windows build/CI/HMD claim.
- RUNTIME_VALIDATION: UNTESTED (no new actual game/HMD, Quest3/VDXR or xrEndFrame capture).
- CODE_CHANGE: NO
- NEXT_REVIEW: Distinct next run should inspect **per-producer final GPU API and shader epoch/StateBlock transitions** from existing evidence; after that source-game-pixel → XR viewport + non-zero cant matrix. If no new evidence, mark `NEW_FINDING=NONE` without repeating this static cache condition.
