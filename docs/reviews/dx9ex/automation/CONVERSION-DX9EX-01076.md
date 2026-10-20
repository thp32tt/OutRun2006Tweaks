# CONVERSION-DX9EX-01076 — R26+HUD menu capture/optical aspect invalidation review

- Date: 2026-10-20 KST
- TASK_ID: CONVERSION-DX9EX-01076
- PRODUCTION_ID: CONVERSION-DX9EX-01076
- EVENT_ID: CONVERSION-DX9EX-01076-E001
- EVENT_TYPE: dispatch
- TARGET_BRANCH: vr-d3d9ex-focus
- MODE: DX9EX_REVIEW_ONLY
- CODE_CHANGE: NO
- SOURCE_HEAD: a92d6b86676337b870e5b84cd86144b7d3ff6498
- R26_HUD_BASELINE: 0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 (preserved)
- COMPARISON_ONLY: aab9e02bcb2ad2e6253840e6267e5c5ad5040854 (NOT HMD PASS)
- R84_AUTOPROMOTION: FORBIDDEN
- AUTOMATION_VALIDATION: STATIC_SOURCE_REVIEW_ONLY; docs-only Git verification to be performed against resulting commit
- RUNTIME_VALIDATION: UNTESTED
- REVIEW_SCOPE: Original menu sprite/D3DX producer-to-priority-queue and physical API → R26+HUD game render/restore/Present boundary → x64 host desktop capture → menu aspect/UV and cached projection → D3D11 two-eye projection copy → xrEndFrame. Focus: same-state effective menu layout/config invalidation when capture is not fresh.
- NEW_FINDING: CONDITIONAL_MENU_PROJECTION_CACHE_INVALIDATION_GAP (STATIC, runtime trigger unproven)
- PATCH_CANDIDATE_ONLY: YES, no implementation

## Predecessor and non-duplication

- Checked latest branch tree, AGENTS.md, docs/automation/runs/CONVERSION-DX9EX-01075.json, docs/automation/runs/CONVERSION-DX9EX-01074.json and docs/automation/reviews/R26_RESULT_HUD_RANK_LENS_CROSSREVIEW_20261020.md.
- 01075 is a previous implementation-era +TIME physical owner/foreign c64 validation record, still saying IMPLEMENTED_AWAITING_EXACT_SHA_CI at the observed HEAD; do not repair or complete it from this review-only TASK_ID.
- The 2026-10-20 cross-review M5 already describes possible source game-pixel vs viewport normalization mismatch in R26 XYZRHW. This task does NOT repeat it or assert that XYZRHW is the cause of the main-menu squash. Different seam: the x64 host's cached LOCAL-fixed menu projection may outlive an effective 4:3 menu config decision.
- No docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01076.md existed before this new record.

## Evidence: exact reviewed source positions

1. Original REA architectural reference, docs/automation/OUTRUN_REA_RENDERING_ARCHITECTURE_20261018.md:6-26,33-42. Game loop VA 0x00417B20 → rendering VA 0x00449050 → queue consumer 0x0042D710. Type 0: 0x0042A0A0 D3DXSprite Draw, later 0x00429F60 End/Flush; type 1: 0x0042A3A0 / 0x0042A800 native DrawPrimitiveUP. This is a source-modelled class of sprite paths, NOT proof that a particular main-menu tile takes a specific GPU API. Direct original/indirect REA edges remain partial.
2. src/hooks_uiscaling.cpp:798-804,890 confirms an independent game-resolution-scaled native DrawPrimitiveUP path. src/vr/game/render_semantics.hpp:1112-1131,1306 shows node/epoch-backed semantic instrumentation; a semantic tag is not final GPU ownership on its own.
3. src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:3382-3468 uses the live viewport for XYZRHW transform and :3785-3853 shows conditional left/right D3D9 state, right-eye RT/DS/viewport switch, RestoreRightPassState and fallback/poison guards. These are applicable to qualifying game Draw routes; never assume they prove the host's LOCAL-fixed menu presentation went through R30/R62 stereo.
4. vrhost/src/main_r23.cpp:84-174 reads effective Graphics.UIScalingMode/UILetterboxing from game-adjacent INI + .user.ini, caches per HWND/PID and polls only after 2500 ms when called; :1575-1607 calls this function only during menu render planning. It is NOT sampled on every XR frame.
5. vrhost/src/runtime/menu_content_aspect.hpp:43-69 permits automatic 4:3 crop for exact game states 0x04/0x09 when configured letterboxing is true even with imageMatteVerified=false, excludes 0x0A..0x0C. This is intentional declared layout policy, not runtime pixel-matte proof. :288-305 bases physical aspect on sampled UV; :335-352 refuses to turn an uncropped 3440x1440/1920x1080 capture into a 4:3 optical rectangle.
6. vrhost/src/main_r23.cpp:1516-1717 computes common tangent-FOV, captured-client source UV and aspect, optional matched UV+aspect 4:3 crop; :1719-1736 logs a decision only on game-state change (the logged crop43 is eligibility, not necessarily actual plan.crop); :1767-1835 renders left D3D11 menu plane, copies identical raster to eye 1 when eligible or separately draws second eye, then builds common LOCAL-anchored OpenXR projection views.
7. vrhost/src/main_r23.cpp:3504-3555: in non-gameplay projection branch, the cached menu projection is explicitly invalidated on clientGameState change; a new menu render occurs only when capture.available && menuProjectionAnchorValid && (!cachedMenuProjectionValid || capture.fresh). With cache valid and capture.fresh=false, code reuses cachedMenuProjectionViews. No effective letterbox-config generation or client/UV/aspect signature is included in this gate.
8. vrhost/src/main_r23.cpp:2732-2741,2779-2788,2815-2824,2874-2897 do invalidate the cache for XR session stop, reference-space event, fresh menu anchor, and presentation transition. These existing invalidations limit the hypothesis; do not report an unconditional stale cache.
9. vrhost/src/main_r23.cpp:3562-3589 submits the prepared layer with xrEndFrame and queries final-layer instrumentation. vrhost/src/main.cpp:1924-1966 creates a runtime-recommended two-slice XR projection swapchain, independent of desktop capture dimensions. A successful D3D11 copy alone is not an HMD optical PASS.
10. vrhost/tests/menu_content_aspect_smoke.cpp:42-95 contains compile-time crop/state-policy assertions. The inspected source coverage does not by itself establish a live test for an INI/F11 layout change during a stale desktop capture frame.

## Producer → semantic → physical draw → stereo → final image static walk

- Producer/original: the original menu sprites/animations enter their original type-0 D3DX batched or type-1 native queue per REA. The exact main-menu individual producer VA/callsite-to-physical-draw mapping was not established in this review. The D3DX Draw callback can precede actual Flush/End GPU rasterization; assigning ownership at semantic entry alone is unsafe.
- Queue/physical: the game retains R26+HUD with R30 qualifying HUD/XYZRHW and normal D3D9 fallback/restore. A menu frame can instead be supplied as the ordinary captured game client for host presentation. No claim that any menu Draw was duplicated by R30 or routed through R62 without Draw API/FVF/VS proof.
- Capture/host: the host samples its current game client UV and physical aspect. Under presentation != Gameplay it chooses a LOCAL-fixed common-FOV menu plane; only menu game states 0x04/0x09 are 4:3-crop eligible, whereas car selector 0x0A..0x0C retains wide client.
- L/R: menu left raster is drawn to a D3D11 XR projection image. Identical-slice copy (or separate right draw fallback) publishes both eyes with common source UV, clip and menuAnchor. This means binocular availability does not by itself prove true stereo depth or a corrected captured aspect.
- Restore/Present/OpenXR: qualifying game R30 stereoscopy restores game RT/DS/viewport along its own route. The host menu path releases the XR swapchain image and uses two projection views on xrEndFrame. Source/game Present, host menu projection and final XR submission are different checkpoints; no observed frame-correlated final GPU evidence was supplied.

## New finding: bounded conditional invalidation gap

**Source-confirmed control-flow condition:** If (a) clientGameState is unchanged, (b) a previously valid menu projection exists, (c) no XR session/reference/presentation/anchor invalidation happens, (d) capture remains available but reports fresh=false, and (e) the *effective* game-side UIScalingMode/UILetterboxing or authored menu client geometry changes independently, then main_r23.cpp:3522-3555 does NOT trigger R23RenderWorldLockedMenuProjection. The INI/PID cache is checked only from that function, so its 2500-ms timer cannot by itself invalidate the menu projection. Old source UV, crop decision, aspect, clip and cached projection views can remain submitted.

**Runtime hypothesis, NOT confirmed defect:** An F11 .user.ini change, client/window scaling change, or a capture freshness discontinuity could expose an out-of-date optical rectangle on a static menu and contribute to perceived menu stretching/squash. It is equally plausible that each real game-side setting change emits a fresh captured frame, or that state/anchor invalidation already happens, eliminating the scenario. No Quest 3 evidence establishes the trigger sequence.

**Important counterevidence / safeguards:** The 0x04/0x09 crop policy is deliberate; UV and aspect are changed together in the real crop path. Uncropped wide frames deliberately retain measured aspect. Selector 0x0A..0x0C explicitly forbids the crop. Reference-space and game-state changes invalidate the cache. Therefore do not auto-revert 4:3 behavior, do not label R84 or R26 as broken, and do not treat crop43=1 in the log as proof that actual UV cropping occurred.

## PATCH_CANDIDATE_ONLY (no code edits)

- Candidate seam A (HOST ONLY): vrhost/src/main_r23.cpp::R23GameMenuIsLetterboxed, lines 84-174, and ::R23RenderWorldLockedMenuProjection, lines 1516-1717. When a future human-authorized implementation is warranted, expose a read-only *effective* game-INI/layout revision or changed decision fingerprint without polling INI unboundedly each XR frame. Do not infer valid 4:3 matte from graphics config alone.
- Candidate seam B (HOST ONLY): vrhost/src/main_r23.cpp non-gameplay cachedMenuProjectionValid gate, lines 3504-3555. Consider invalidating when the actual client/UV/source extent or measured effective layout generation changes, even if capture.fresh=false; avoid forced GPU render on every idle XR frame. This is a proposal, not a diagnosed root cause.
- Candidate seam C (DIAGNOSTIC): vrhost/src/main_r23.cpp lines 1719-1736. Separately report crop eligibility (cropCentered43) vs actual crop (plan.crop) and capture freshness, source/client/UV, effective INI layout epoch, final layer kind and XR submission ID to avoid false-positive optical diagnoses. Instrumentation would require explicit approval; no changes in this task.
- Falsification: A matching-source Quest 3/VDXR log where a same-state F11/INI or client-extent transition always yields capture.fresh=true, state change, or cache invalidation before subsequent xrEndFrame refutes the proposed stale-cache symptom. If exact affected menu captures and final submitted images have consistent physical sourceAspect and authored placement, investigate original sprite crop, stage presentation pixels, or install/package mismatch instead.
- Regression boundaries: Preserve R26+HUD 0cff83cf baseline; do not promote R84. Do not touch x86 game/source, R30/R62 projection, shader/WVP, D3DX batching, GOAL/+TIME, rank/rival, lens/SkyGlow, ESC/F11 input, vehicle-selector full-width content, DX11/DXVK, or B9200 post-CALL/+5. Host adjustments must not add extra per-tick capture, per-eye second GPU pass, unsafe XR state reuse or restore changes. No release/package/build in this review.

## Validation and follow-up

- Read-only GitHub branch, original REA summary, current source, and preceding run/crossreview examined. Static if/else simulation only; no local Windows build, CI, disassembly re-execution, runtime GPU capture or Quest 3/VDXR test was performed.
- AUTOMATION_VALIDATION = STATIC_SOURCE_REVIEW_ONLY. GitHub docs-only creation and post-commit diff/marker audit to be performed separately; this review does not require a source-build gate and does not use CI-skip.
- RUNTIME_VALIDATION = UNTESTED. NEW_FINDING is a control-flow risk, not a device-verified root cause.
- NEXT_REVIEW: independently examine final GPU API/FVF/VS + D3DX Flush/End physical ownership for one captured main-menu tile; correlate queued producer, physical draw, game Present frame ID, host CaptureStatus.fresh and final XR submitted frame. Only then distinguish source-pixel squash from cached host-plane layout. If no new evidence, NEW_FINDING=NONE in the next distinct task and avoid repeating this cache hypothesis.

CODE_CHANGE=NO
