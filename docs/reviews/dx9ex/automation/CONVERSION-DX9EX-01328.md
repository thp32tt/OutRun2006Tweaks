# CONVERSION-DX9EX-01328 — CABE outer lens Calc3D2D anchor versus actual eye-space draw/extent join (REVIEW_ONLY)

- DATE=2026-10-22 KST
- TASK_ID=CONVERSION-DX9EX-01328
- PRODUCTION_ID=CONVERSION-DX9EX-01328
- EVENT_ID=CONVERSION-DX9EX-01328-E001
- EVENT_TYPE=dispatch
- LANE=DX9EX
- ATTEMPT=1/3
- TARGET_BRANCH=vr-d3d9ex-focus
- SOURCE_HEAD=5af84cb5fec934f98f1ee22bd1bf80f2c334db39
- PREVIOUS_REVIEW=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01327.md
- PREVIOUS_RESULT_SHA=5af84cb5fec934f98f1ee22bd1bf80f2c334db39
- AUTHORITY=CONNECTED_GITHUB_PINNED_BRANCH_SOURCE
- N100_DRIVE=NOT_USED
- MODE=DX9EX_REVIEW_ONLY
- DX9EX_REVIEW_ONLY=ON
- CODE_CHANGE=NO
- PATCH_APPLIED=NO
- BUILD=NOT_RUN
- CI=NOT_RUN
- SOURCE_BUILD_GATE=NOT_APPLICABLE_DOCS_ONLY
- CI_SKIP=NONE
- ORIGINAL_BINARY_REDISASSEMBLY=NOT_RUN
- ORIGINAL_REA=EXISTING_GITHUB_NOTES_ONLY
- PHYSICAL_GPU_TRACE=NONE
- QUEST3_VDXR_TEST=NOT_RUN
- RUNTIME_VALIDATION=UNTESTED
- HMD_PASS=NO
- PERFORMANCE_P95_P99=NOT_MEASURED
- R26_PLUS_HUD_BASELINE=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9
- R84_HUD_COMPARISON_ONLY=aab9e02bcb2ad2e6253840e6267e5c5ad5040854
- R84_AUTO_PROMOTION=NO
- B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN

## REVIEW_SCOPE — distinct from 01327 centre-suppression versus outer-call independence

**Specific audit question:** does the outer lens flare's original `Calc3D2D` projected anchor, computed upstream of the `EXE+0xCABE` alpha producer, have a proved one-to-one relationship to the *terminal* D3D9 GPU primitive and the correct game-pixel / per-eye XR projection (including non-zero eye cant)? Unlike 01327, this does not review the C993 centre visibility bypass or assign ownership of the doubled centre. It traces *outer CABE original projected coordinates* to semantic admission, raw-c64, queue/D3DX deferral (if present), R30/R62/native dispatch, per-eye state restoration, Present and host xrEndFrame.

### Pinned, source-based path simulation (not an observed physical frame)

1. **Original producer and CPU-side coordinate boundary.** Existing REA (`docs/automation/OUTRUN_REA_RENDERING_ARCHITECTURE_20261018.md:76-83`) identifies original Calc3D2D-style projection at `0x00449940` as a projection/viewport dependency and distinguishes `0x0040C980` centre, `0x0040C9A0` outer candidates and SkyGlow. `src/hooks_graphics.cpp:580-600` documents outer `EXE+0xCABE` and a separate `EXE+0xCF4E` call to `Calc3D2D`; outer producer calls at `0xD5F5..0xD796` are described. This is existing disassembly-backed *source documentation*, not new binary work or proof that one projected anchor equals one physical quad. The original EXE data and the actual calculated X/Y/viewport values were not captured this run.
2. **CABE semantic, not an eye-coordinate payload.** `src/hooks_graphics.cpp::VRLensFlareProjected2D::DrawObjectAlphaProjected:662-684` samples id/alpha/flags only for decimated telemetry; it encloses the original `Game::DrawObjectAlpha_Internal` in `ScopedRenderSemantic(ProjectedScreenEffect2D)`. It does not in this wrapper capture the preceding `Calc3D2D` output, source game-pixel extent, logical UI viewport, eye extent or the physical-D3D9 draw serial. The hook retains one original call; the number of later primitive submissions is not established. This differs from the C993 centre `LensFlareCentre` token, which must **not** be inherited by CABE.
3. **Queue and D3DX admission must be observed, not assumed.** `src/vr/game/render_semantics.hpp:1246-1283,1290-1325,1419-1432` captures effective scope/producer/queue pointer/queue epoch and a centre-only direct call epoch on each physical command. The inspected record contains no CABE-specific `Calc3D2D` anchor/coordinate tuple in that `PhysicalDrawCommand`; absence of this field is an identity/proof limitation, **not** proof that original geometry lacks its screen coordinates. Existing REA queue type-0 may defer D3DX Sprite Draw until Flush/End, while type-1 can use UP; no verified CABE queue-path evidence was acquired. Record direct vs queue vs mixed/unknown distinctly; never transplant a CABE token into D3DX unrelated batches.
4. **R30 classification is deliberately conditional.** `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30ClassifyScreenSpacePass:2180-2410` only admits `ProjectedScreenEffect2D`/SceneEffect under `Perspective3D` and owned original raw WVP. `R44GetOwnedRawOverlayWvp:1955-2002` checks current shader identity, game-c64 write shader/epoch and <=12-draw age; `R30GetExtendedRawWvpForExactSceneEffect:1933-1954` is another narrowly gated recovery. A proven spatial raw matrix selects `WorldBillboard`; a proven flat raw matrix selects `PerspectiveHud`; unproven/other matrices return `None`. This path does **not** independently verify that the upstream CABE `Calc3D2D` anchor corresponds to the admitted GPU primitive.
5. **Distinct stereo mathematical outcomes.** `R30BuildScreenSpaceEyeConstants:4544-4930` reconstructs the accepted `WorldBillboard` from stock WVP × inverse game base projection, latched head inverse, full per-eye orientation/translation and per-eye FOV. Accepted `PerspectiveHud` instead gets a finite common HUD plane and, for generic effects, identity-eye orientation (special exact +TIME/GOAL eye-cant logic does **not** grant CABE ownership). Source-game pixel origin, original Calc3D2D viewport, `VRUnifiedEyeMenuSource`, logical viewport and XR per-eye extent must be compared before deciding either outcome is optically appropriate for an outer ring. There is no capture here of the exact original CABE anchor-to-eye pixel delta, so no observed sign/scale/asymmetry error can be asserted.
6. **Actual physical draw and owner fallback.** `R30TryScreenSpaceFovDraw:4932-5153` rechecks semantic, game device, stereo resources, depth/stencil availability, latched pose and current frame pose before constructing L/R WVP. It may reject with `E_NOTIMPL`. `DrawPrimitiveDestR30`, `DrawIndexedPrimitiveDestR30`, `DrawPrimitiveUPDestR30` and `DrawIndexedPrimitiveUPDestR30:5398-5573` try applicable XYZRHW/R62 indexed-FVF candidates, then R30 screen-space and finally R29/native path if declined. **R62's exact ScreenHud fixed-function indexed owner is not a generic CABE flare route.** Neither the original CPU CABE call nor an R30 classification proves the terminal physical API/FVF/VS/PS/texture and final owner.
7. **Left/right and state restore boundary.** If screen-space candidate accepts, `R30TryScreenSpaceFovDraw:5038-5153` sets left c64 and calls the native draw, switches to right RT/depth/viewport/c64, calls right native draw and restores original RT/depth/viewport/c64. Right-pass or restore failure poisons/arms fallback; a getter, upload or eligibility failure may preserve R29/native instead. No per-CABE left/right HRESULT, source-to-eye pixel association, non-zero cant or restore-result capture was obtained here.
8. **Present and XR closure.** `src/vr/d3d9/stereo_renderer.cpp::PresentDestR9:678-815` joins global seeded world + duplicated draw, frame pose/metadata, right-eye/incomplete state, DirectGPU or SBS composition and normalized D3D9 Present before an active Frame.v2 publish. `vrhost/src/main_r23.cpp:3558-3615` checks actual `xrEndFrame` and submitted layer/frame identity. These global gates do not directly attest that one CABE source anchor landed at the intended pixel in each eye or that the outer-ring disparity is correct. No Quest3 test and no 72Hz measurement was conducted.

## NEW_FINDING — source-level correlation gap, not a demonstrated optical bug

- NEW_FINDING=CABE_CALC3D2D_ANCHOR_TO_TERMINAL_GPU_DRAW_AND_EYE_PIXEL_EXTENT_JOIN_NOT_PROVEN_IN_INSPECTED_PATH.
- CLASS=SOURCE_CONFIRMED_DIAGNOSTIC_PROOF_GAP; SCREEN_DEFECT=NOT_DEMONSTRATED; WRONG_PARALLAX=HYPOTHESIS_ONLY; PERFORMANCE_REGRESSION=UNKNOWN.
- **Confirmed, narrowly:** the inspected CABE producer wrapper marks the outer effect's semantic but does not carry upstream projected anchor X/Y + logical game viewport, game-source extent or XR eye extent as a typed physical-draw identity; `PhysicalDrawCommand` similarly has no CABE anchor field. R30 relies on exact semantic + shader/c64 provenance and matrix classification, with cautious native fallback. These are distinct from per-pixel binocular proof. Do not claim an upstream projection is missing from the original game's vertex data or that all CABE effects are flat.
- **Conditional hypothesis:** if original Calc3D2D projects an outer halo for a game-space viewport and a later accepted R30 eye transformation treats that *already projected* matrix as spatial world geometry, a non-zero eye-cant/extent-dependent ring offset could be wrong. A separate failure mode would be a different direct/queued native draw retaining original equal-eye raster, but neither is observed; the outcome depends on actual shader, matrix class, final route and rendered pixels.
- **Falsification:** a capped identical-source Quest3/VDXR trace demonstrates for every suspect CABE object/call the source projected (X,Y), game source/viewport, current c64/shader/primitive, L/R viewports/RT/WVP, terminal actual Draw and restore, game Present ID and exact xrEndFrame layer. If they match the expected per-eye projected location with correct optical rings, reject the anchor/extent mismatch hypothesis. If CABE never takes R30 owned-eye route, reject attribution to an R30 per-eye re-projection. If source X/Y is authored in already-correct target space and the physical output is correct, no extra coordinate conversion is warranted.
- **No substitute:** sampled CABE alpha/flags logs, R44 matrix-age counters, an R30 'stereo active' counter, a desktop screenshot, or an XR layerCount without a draw/fingerprint correlation does not prove lens-ring optical success or failure.

## PATCH_CANDIDATE_ONLY — zero source edits

- PATCH_CANDIDATE_ONLY=CAPPED_CABE_ORIGINAL_PROJECTED_ANCHOR_TO_PHYSICAL_EYE_PIXELS_CORRELATION_IF_REAL_REPRO.
- APPLY=NO; CODE_CHANGE=NO; PATCH=FORBIDDEN; BUILD=NOT_RUN; FEATURE_BRANCH=NO; MERGE=NO; PACKAGE=NO.
- **Site A:** `src/hooks_graphics.cpp::VRLensFlareProjected2D::DrawObjectAlphaProjected:662-684`, original `EXE+0xCF4E/0xCABE` REA at :580-602. Potential opt-in diagnostic only: log original call RVA, objectId, raw Calc3D2D output and the *actual logical game viewport/source extent* with a matching bounded source epoch, if and only if their provenance is first independently proved. Do not hook dangerous B9200 post-CALL/+5, suppress outer rings, change alpha, rewrite vertex positions, or promote raw telemetry to an owner.
- **Site B:** `src/vr/game/render_semantics.hpp::CapturePhysicalDrawCommand:1419-1432` plus actual SpriteNode / D3DX Flush/End transition in `src/hooks_uiscaling.cpp::VRProjectedD3DXSpriteIsolationR64::FlushDest/EndDest:3428-3510`. Candidate limited fingerprint joining a *verified* CABE direct/queue source to actual native command (API, primitive, texture, VS/PS, c64 write epoch, draw age, queue generation). Do not tag unknown queued glyphs, inherit C993 parent epochs or force global Flush.
- **Site C:** `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R44GetOwnedRawOverlayWvp:1955-2002`, `::R30ClassifyScreenSpacePass:2180-2410`, `::R30BuildScreenSpaceEyeConstants:4544-4930`, `::R30TryScreenSpaceFovDraw:4932-5153`, and `::Draw*DestR30:5398-5573`. Candidate record which projection class, matrix classification, R30 rejection or R29/native terminal route actually handled the exact CABE primitive; compare game-source and eye viewport, non-zero cant, RT/depth/WVP and restore results. No global SceneEffect/alpha/texture rerouting; preserve flat-vs-spatial fail-closed classification.
- **Site D:** `src/vr/d3d9/stereo_renderer.cpp::PresentDestR9:678-815` and `vrhost/src/main_r23.cpp:3558-3615`. Candidate optional bounded game Present/Frame.v2 to submitted XR frame+layer join and captured pixel landmarks. No blocking per-draw GPU readback or unbounded I/O in normal 72Hz gameplay.

## REGRESSION_RISK / proof and negative boundaries

- REGRESSION_RISK=HIGH_IF_APPLIED. Confusing a 2D projected ring with 3D source geometry can displace halos under asymmetric FOV and non-zero cant, remove original lens discs, double-apply head transforms, corrupt right-eye output or state restore, or create camera-following artifacts. Mistakenly propagating direct ownership across queued D3DX Flush/End can bleed into +TIME/GOAL, 6th/6, ESC native sprites or car-rank markers. Sampling all draws/doing synchronous readback can harm 72Hz CPU/GPU pacing, especially particle-heavy/sandy scenes.
- Negative controls: exact R26+HUD user baseline, identical source/config R84_TEST as A/B only, C993 centre hidden/enabled both ways without collapsing outer CABE, SkyGlow independent, game/menu source extent vs logical UI viewport vs XR eye extent, F11 separate ImGui vs ESC native UI, selector UV/state, rank/rival projected markers, cockpit, lens, sky, opaque/alpha world, reset/device loss, no stale shader/c64, no queue pointer reuse, L/R RT/depth/viewport restore, DirectGPU versus SBS fallback, input/FFB.
- No code, binaries, workflows, CMake, branches, releases or runtime settings changed. No actual GPU capture, modified game, original executable redisassembly, automatic build or Quest3/VDXR performance verification took place.

## EVIDENCE / NEXT_REVIEW / GITHUB_RECORD

- EVIDENCE=CONNECTED_GITHUB_PINNED_HEAD; sources checked: `AGENTS.md:1-18`, `docs/DX9EX_OPTICAL_ROUTE_PROBE_POLICY_20261020.md:1-90`, `docs/automation/OUTRUN_REA_RENDERING_ARCHITECTURE_20261018.md:67-96`, `src/hooks_graphics.cpp:580-684`, `src/vr/game/render_semantics.hpp:1240-1325,1419-1432`, `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:1930-2002,2180-2410,4544-5153,5398-5573`, `src/vr/d3d9/stereo_renderer.cpp:678-815`, `vrhost/src/main_r23.cpp:3558-3615`, and predecessor `CONVERSION-DX9EX-01327.md`.
- AUTOMATION_VALIDATION=REMOTE_DOCS_ONLY_PARENT_DIFF_AND_FILE_READBACK_REQUIRED; PREWRITE_BRANCH_HEAD=5af84cb5fec934f98f1ee22bd1bf80f2c334db39.
- GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01328.md
- EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01328]
- NEXT_REVIEW=Distinct **game-pixel / eye-extent reset/device-loss generation** seam: after a mode/menu resolution or reset, check whether the *current* backbuffer source dimensions, logical 640x480 UI mapping, native viewport and host XR eye extents remain generation-matched through direct transport versus SBS and across the next Present. Avoid repeating CABE anchor, C993 visibility, SkyGlow failure or R62 glyph attribution; keep real device evidence mandatory.
- CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED.
