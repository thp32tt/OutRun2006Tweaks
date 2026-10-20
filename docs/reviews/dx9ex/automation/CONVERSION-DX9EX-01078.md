# CONVERSION-DX9EX-01078 — F11 external ImGui eye-local cant versus source viewport (REVIEW_ONLY)

- DATE: 2026-10-20 KST
- TASK_ID: CONVERSION-DX9EX-01078
- PRODUCTION_ID: CONVERSION-DX9EX-01078
- EVENT_ID: CONVERSION-DX9EX-01078-E001
- EVENT_TYPE: dispatch
- ATTEMPT: 1/3
- LANE: DX9EX
- TARGET_BRANCH: vr-d3d9ex-focus
- SOURCE_HEAD: b528d1b8a7e189a1f27a7e415366be099efae954
- R26_HUD_BASELINE: 0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 (immutable user control)
- COMPARISON_ONLY: aab9e02bcb2ad2e6253840e6267e5c5ad5040854 (NOT HMD PASS)
- MODE: DX9EX_REVIEW_ONLY
- DX9EX_REVIEW_ONLY: ON
- CODE_CHANGE: NO
- REVIEW_SCOPE: R26+HUD source/REA/semantic fork between original game D3DX/queue and independent F11 ImGui indexed Draw; F11 orthographic source-pixel/viewport to per-eye finite plane, head-local cant/FOV, original projection+scissor restore, game Present/transport and host OpenXR per-eye extent.
- NEW_FINDING: CONDITIONAL_F11_HEAD_LOCAL_EYE_ROTATION_OMITTED_IN_FINITE_PLANE
- PATCH_CANDIDATE_ONLY: YES (no patch applied)
- AUTOMATION_VALIDATION: STATIC_GITHUB_SOURCE_REA_ISSUE_REVIEW; DOCS_ONLY_DIFF_AUDIT_REQUIRED_ON_RESULT_COMMIT
- RUNTIME_VALIDATION: UNTESTED

## Previous reviews and evidence boundary

- Read `01075.md`: exact +TIME/result cached/live VS shader admission; `01076.md`: x64 host menu projection cache invalidation; `01077.md`: R9 producer EVENT direct-transport publication. This task does not refile any of those three findings, does not fix the producer fence and does not broaden shader ownership.
- The 2026-10-20 cross-review `docs/automation/reviews/R26_RESULT_HUD_RANK_LENS_CROSSREVIEW_20261020.md`, M5, already describes a generic *possible* game presentation-pixel versus D3D viewport disagreement; **not counted as a new finding here**. This review instead checks F11's independent non-XYZRHW GPU route and a separate per-eye pose term.
- Current `AGENTS.md` topmost 2026-10-20 override and `docs/DX9EX_OPTICAL_ROUTE_PROBE_POLICY_20261020.md` establish CURRENT_FOCUS=R26+HUD, R84_TEST comparison-only and require physical fingerprint/Quest3 acceptance. Older AGENTS paragraphs naming R84 mainline are superseded. #119 reports prior F11 apparent legibility and different desktop/XR extents, but is **historical HMD feedback**, not a matching trace for SOURCE_HEAD.
- `docs/automation/OUTRUN_REA_RENDERING_ARCHITECTURE_20261018.md:1-42` maps original Win32 game loop VA 0x00417B20 -> 0x00449050 -> queue consumer 0x0042D710; D3DX Begin 0x00429C60, Draw 0x0042A0A0, End 0x00429F60, and native DrawPrimitiveUP branches. `docs/research/REA_STAGE_EXTENSION_MODE2_SOURCE_SCOPE_20261019.md:1-16` establishes true +TIME sources and 0x00498AC6 mode-2 exclusion. Original EXE SHA-256 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3. These map game-produced queue sprites; they do **not** make the F11 ImGui overlay a game D3DXSprite node.
- The `docs/automation/runs/CHAT-DX9EX-R26-RESULT-HUD-20261020.json` baseline logs document one ResultProgress physical DIP FVF142, VS null, queue epoch; they **do not** provide F11 per-eye GPU captures or the installed binary's final XR event.

## Static producer-to-optical pipeline

1. **Separate producers and semantic admission.** Game +TIME/results/ESC sprites may pass `src/hooks_uiscaling.cpp:1660-1874,3340-3429,3720-3845` and `src/vr/game/render_semantics.hpp` queue/epoch/D3DX-batch proof; GPU submission can occur at D3DX Flush/End, not the earlier Draw callback. F11 settings instead come from `src/overlay/hooks_overlay.cpp` / Dear ImGui DX9 backend. The latter is admitted only with nonzero `ExternalOverlaySemanticDepth` and `EffectiveScope()==ScreenOverlay2D`; it must not borrow any queued +TIME producer or B9200 glyph proof.
2. **Physical API and safety gate.** `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5319-5350` calls `R30TryExternalImGuiIndexed` first in `DrawIndexedPrimitiveDestR30`, ahead of R62 FVF142 and other XYZRHW/shader fallbacks. `R30PrepareExternalImGuiProjection():2740-2805` requires world-stereo seeded frame, duplicated draw, external semantic, live null VS, fixed-function XYZ+DIFFUSE+TEX1, WORLD/VIEW identity, orthographic original projection, Z disabled, scissor enabled, live viewport, and pose-sequence-matched HeadInverse. A rejected gate is not F11 stereo success; it descends to conservative later ownership.
3. **Current F11 optical pose.** `R30PrepareExternalImGuiProjection():2810-2845` averages eye offsets, forms `relative = eyeOffset[eye]-centre`, but passes `noRotation={0,0,0,1}` to `MatrixFromQuaternionTranslation`. It builds `HeadInverse * EyeInverse * ProjectionFromFov(eyeFov)` and then the -2.50 finite recentered HUD plane. There is no `state.stereo.eyeOrientation[eye]` term in this narrow F11 branch.
4. **Different exact result contract.** In the same compiled R26+HUD file `R30ConfigureXyzrhwWorldEffect():3190-3250`, exact result-only owner uses `StageExtensionPlane::BuildStageEyePoses(state.stereo.eyeOffset, state.stereo.eyeOrientation,...)` and passes `resultEyeOrientation[eye]` into its head-local eye pose. This is **a confirmed source-level distinction**, not proof that F11 needs an identical pose policy. General HUD/world-effect protections intentionally differ.
5. **Source pixels and clip.** `R30BuildHudPlaneCoefficients():2660-2713` uses finite HUD plane Z=-2.50 and F11-specific scale=1.0 (no gameplay HUD shrink). `R30PrepareExternalImGuiProjection():2850-2924` composes the stock orthographic pixel-to-NDC matrix with the plane clip map. It transforms each scissor corner into **the original D3D viewport** using X/Y/Width/Height, clamps, and rejects degenerate rectangles. This contradicts a blanket claim that F11 fails to transform its scissor. It also does not prove the original ImGui framebuffer geometry equals a particular game-source pixel size at runtime.
6. **L/R and restore.** `R30TryExternalImGuiIndexed():2928-3030` sets left projection/scissor, calls the real DIP, switches right RT/depth/viewport, sets right projection/scissor, draws right, restores saved RT/depth/viewport and original projection/scissor, poisoning incomplete frames. `src/vr/d3d9/stereo_renderer_r7.inc:1456-1462` creates a full-size right-eye render target from the D3D backbuffer and has bounded right-state restore. The existence of two submitted Draw calls alone does not prove binocular fusion.
7. **Present and XR extent.** `src/vr/d3d9/stereo_renderer.cpp:760-809` routes through actual game Present, guarded frame promotion and stereo transport. R9's separate producer EVENT uncertainty is covered in 01077; not reasserted here. `vrhost/src/main_r23.cpp:2800-2838` locates head and two views with OpenXR and publishes pose. `vrhost/src/main.cpp:1924-1966` creates the separately validated runtime-selected per-eye XR extent (two-slice array). `vrhost/src/main_r23.cpp:3170-3245,3560-3595` validates frame/pose and calls `xrEndFrame`. The game/backbuffer pixel viewport, per-eye D3D9 copy dimensions and OpenXR eye swapchain dimensions are different stages; no current F11-specific same-frame match is available.

## NEW_FINDING — source-confirmed pose-policy difference, conditional optical risk

**Confirmed static fact:** The F11 external-indexed finite HUD construction uses per-eye translation and asymmetric `eyeFov`, but intentionally builds `eyeInverse` with identity rotation; exact result R26+HUD finite plane incorporates the host-published head-local `eyeOrientation`. Both paths share head inverse and finite-plane mapping. The omission means F11 cannot respond *through its virtual eye-view matrix* to non-identity head-local eye rotations, even though FOV asymmetry and compositor projection may still account for part/all of the observed optical geometry.

**Bounded hypothesis:** If the actual Quest3/VDXR `eyeOrientation` has material nonzero cant and final HMD content needs that cant on this finite plane, F11 UI glyph placement/edge clipping/vergence could differ from equivalent source-owned result HUD. If the runtime's FOV/compositor path already compensates (or eye-local rotations are effectively identity), adding a rotation could *double-correct* F11 and worsen the picture. #119's prior small/blurred UI is **not** evidence proving this hypothesis. No demonstrated matching current-F11 frame or HMD PASS/FAIL.

**Falsification / negative cases:** Pair a single F11 DIP with `eyeOrientation[0/1]`, yaw/pitch/roll, eyeFov, poseSeq, original ortho/world/view/scissor, viewport, stock source pixel size, RT/depth IDs, projection/scissor restore HRESULT, Present frame ID, host XR extents and final layer kind. Show (a) both eyeLocal orientations identity within tolerance, (b) both render-space and HMD fused corners align under a nonzero-cant probe, (c) F11 route is never admitted and falls back before building the pose, or (d) experimentally applying cant *worsens* binocular ray-to-plane convergence under matched package/source. Any of these defeats automatic promotion. A static symbolic matrix difference is not a numerical visual measurement.

## PATCH_CANDIDATE_ONLY (implementation prohibited)

- **A / conditional F11 pose inspection:** `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` — `R30PrepareExternalImGuiProjection()`, **lines 2810-2848** (identity eye quaternion, head inverse, per-eye FOV), compared against `R30ConfigureXyzrhwWorldEffect()`, **lines 3190-3250**. Only after real F11 DIP/cant mismatch, investigate a scoped F11 eye-local rotation path with reversible per-fingerprint Native/FiniteHud/ZeroDisparity control. Do not propagate result-GOAL semantics to F11, general HUD or other VS paths.
- **B / projection+scissor closure:** same file, `R30BuildHudPlaneCoefficients()` **2660-2713**, `R30PrepareExternalImGuiProjection()` **2850-2924**, `R30TryExternalImGuiIndexed()` **2928-3030**, `DrawIndexedPrimitiveDestR30()` **5319-5350**. Record both projected scissor bounds and actual viewport/original source geometry. Retain original scissor restoration on every failure, no added mono draw after a successful owner.
- **C / transport-only proof, not modification:** `src/vr/d3d9/stereo_renderer.cpp` `PresentDestR9()` **760-809**; `vrhost/src/main_r23.cpp` **2800-2838,3170-3245,3560-3595**; `vrhost/src/main.cpp` **1924-1966**. Correlate real physical draw, game Present, host frame/pose and final XR layer; avoid equating a GPU L/R pair or a desktop screenshot with Quest 3 acceptance.
- The generic XYZRHW source-game-pixel versus viewport mismatch already covered by the previous cross-review remains **unresolved but NOT a new finding** in this task. `R30TransformXyzrhwVertices():3390-3405,3664-3745` uses one live viewport for source normalization and destination; `EnsureStereoResources():1456-1458` makes equal-sized right surface. No same-draw source-extent mismatch data were newly observed, so no coordinate fix is justified.
- Zero source patches, refactors, CMake/workflow/runtime-config changes, branch/ref changes, merge, release, package or CI-skip. Build gate is not required for this docs-only review.

## REGRESSION_RISK / protected scope

- HIGH: Double application of eye cant or wrong row-vector eye/head multiplication can create F11 binocular splitting, head-follow or false depth. Preserve actual host `ToHeadLocalOrientation` provenance, head-inverse pose-sequence check and true XR view orientation.
- HIGH: A projected scissor mismatch or restore failure can clip F11 button text, bleed into following original draws or create an extra third mono layer. Keep per-eye corner/scissor checks and original projection/scissor restore.
- HIGH: Do not generalize F11 fixed-function XYZ to R62 kind-0 FVF142, general D3DXSprite HUD, rank/rival, GOAL/Result/+TIME queue or lens/SkyGlow. Preserve original REA mode-2 boundary and 19 unsafe B9200 post-CALL/+5 hooks **disabled**.
- HIGH: No automatic R84 promotion. Preserve immutable R26+HUD control 0cff83cf..., compare aab9e02... only as an unaccepted candidate. Keep game input/FFB, menus/ESC, Reset/device-loss, source resolution and GPU frame pacing independent.
- MEDIUM: Do not add a full second scene pass, expensive per-draw GPU sync, forced desktop resizing, fake XR extent or unconditional stereo routing. Revalidate 4:3/16:9/21:9 and nonzero-cant/opposite yaw tests only in a separately authorized implementation.

## EVIDENCE / AUTOMATION_VALIDATION / NEXT_REVIEW

- EVIDENCE: read-only GitHub latest branch HEAD b528d1b8a7e189a1f27a7e415366be099efae954; preceding 01075, 01076, 01077 Markdown; R26 reference/cross-review; source files and line ranges above; checked-in original REA summary and disassembly-derived +TIME source-scope document; #119 historical HUD/F11 complaint; optical-route policy. Actual original binary and fresh physical GPU/HMD trace were **not** executed or obtained in this task.
- AUTOMATION_VALIDATION: Static source, REA, issue and previous-review crosscheck performed. After docs-only result commit, verify that precisely this Markdown path was added and no code/workflow/config changed; no build/CI or CI skip.
- CODE_CHANGE: NO
- RUNTIME_VALIDATION: UNTESTED (no current exact-package game run, Quest 3/VDXR, runtime OpenXR view capture or per-eye optical comparison).
- NEXT_REVIEW: Trace a **different boundary**: R30 projected-world rank/rival queue producer + physical draw versus true per-eye anchor restoration, OR reset/device-loss scissor/viewport lifetime; do not refile identity-cant F11 hypothesis. To resolve this finding later, obtain a matched F11 physical DIP/projection/viewport/eye-pose → Present → XR frame and run opt-in optical routes before requesting code changes.
- GITHUB_RECORD: docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01078.md, docs-only [AUTO:CONVERSION-DX9EX-01078] commit required.
