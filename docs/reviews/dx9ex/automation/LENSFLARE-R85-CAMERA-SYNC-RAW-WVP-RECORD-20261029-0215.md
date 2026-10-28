# LENSFLARE-R85-CAMERA-SYNC-RAW-WVP-RECORD-20261029-0215 — R85 projected CABE raw-WVP / camera-sync record pairing negative control

- DATE=2026-10-29 KST; RUN_KEY=LENSFLARE-R85-CAMERA-SYNC-RAW-WVP-RECORD-20261029-0215; REVIEW_SCOPE=LENS_FLARE_ONLY; MODE=DX9EX_REVIEW_ONLY.
- TARGET=thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus; SOURCE_HEAD=f9b8ba25cc51b768e9c1eb790a472ceec2779dc6; SOURCE_SSOT=CONNECTED_GITHUB_PINNED.
- BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE; R84=COMPARISON_ONLY; R85=CURRENT_POLICY_NOT_HMD_PASS; B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN.
- CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; BUILD_GATE=NOT_REQUIRED_DOCS_ONLY; CI_SKIP=NONE.
- INHERITED_NOT_RESCORED=01540/01545 projected CABE queue split; 01560 R85 per-eye FOV and possible camera-sync provenance mismatch; 01561 CABE source receipt zero-serial verifier mutant; LENSFLARE-R85-CABE-PROJECTION-EXPANSION-20261029-0110 broader R85 admission. No existing finding is credited again.
- DISTINCT_TEST_AXIS=Does R85's `sourceCameraSynced` bit actually come from an unrelated global camera state, or from the SAME stored original-game c64 record used by the admitted CABE projected WVP? Distinguish sequential single-record linkage from missing atomic snapshot and source-PMT identity.

## NEW_FINDING — bounded source-static negative control, not optical root cause

NEW_FINDING=STATIC_R85_PROJECTED_CABE_RAW_WVP_AND_CAMERA_SYNC_BIT_SHARE_ONE_LAST_GAME_WVP_WRITE_RECORD_IF_NO_INTERVENING_PUBLISH;_SEPARATE_GETTERS_DO_NOT_GUARANTEE_ATOMIC_PAIR_OR_ORIGINAL_PMT_IDENTITY.

1. `src/vr/game/outrun_renderer.cpp::RecordGameWvpWrite:1719-1756` publishes `LastRawGameWvpWrite` from `rawConstants`, `LastRawGameWvpCameraSynced=CullingCameraOverridden`, the shader epoch, top-level draw serial, latched pose epoch, and semantic provenance as fields of the same most-recent write record. `InvalidateGameWvpWrite:1701-1717` invalidates both WVP validity and camera-sync bit.
2. `GetLastRawGameWvpWrite:2488-2502` returns the stored raw matrix only while `LastGameWvpWriteValid` and shader/write serial are nonzero. `GetLastRawGameWvpCameraSynced:2474-2477` returns `LastGameWvpWriteValid && LastRawGameWvpCameraSynced`. Thus the flag is NOT an independently sampled current HMD pose or an unrelated *live* `CullingCameraOverridden` read at R30 draw time.
3. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R44GetOwnedRawOverlayWvp:2035-2069` and `R30GetExtendedRawWvpForExactSceneEffect:1944-1980` both recover `original` using `GetLastRawGameWvpWrite`, with same-shader epoch and bounded draw-age gates. `R30BuildScreenSpaceEyeConstants:5079-5110` chooses one of precisely these two recoveries for `ProjectedScreenEffect2D`; it does not take the original WVP from an unrelated live GPU c64 getter on this admitted path.
4. The R85 branch `R30BuildScreenSpaceEyeConstants:5191-5234` then reads `GetLastRawGameWvpCameraSynced()` and supplies it to `BuildProjectedSunRay`, which either retains or suppresses the head inverse rotation. **When no game WVP write/invalidation occurs between the two reads**, the raw WVP and sync bit necessarily refer to the same last published WVP record. This narrows 01560's open provenance concern: a mismatch cannot be asserted solely because the R85 caller uses two differently named getters.
5. The two reads are still **separate operations**; there is no paired `{rawWvp, cameraSynced, writeSerial, poseEpoch}` snapshot returned to this R85 caller. A hypothetical intervening `RecordGameWvpWrite` or `InvalidateGameWvpWrite` could change the flag after the original WVP was copied. Moreover `CullingCameraOverridden` is sampled at record publication, not independently proven to match the original 405360/4052C0 PMT's Calc3D2D camera. No such intervening mutation, wrong flag, incorrect pose, duplicate colour write, or headset head-lock was observed.
6. Read-only static checks against the pinned GitHub blobs verified all seven invariants: common record publication, validity gate, same-record flag getter, both recovery functions using the raw getter, projected-path recovery selection, and the separate R85 flag read. No source, tests, build, workflow or configuration was modified.

## HYPOTHESIS_LEDGER

| Axis | Status / falsifier |
| --- | --- |
| A original C993/CABE extra emitter | OPEN; original D3A5/C993 570002/006/00F/010 and CABE 570008 two ordinals can be intentional. Require exact original source invocation and unexpected PMT/colour-writing count. |
| B 405360/4052C0 opaque queue, D3DX or native same-eye replay | OPEN; a cached WVP record is not a DrawEntry or texture/material identity. Require same opaque descriptor, pass, PMT, texture, alpha and eye RT RGB delta twice beyond intended passes. |
| C WVP/c64/L/R depth or projection | NARROWED_STATIC; sequential R85 recovered WVP and sync bit share one record, but neither per-eye physical WVP nor actual L/R pixels are proven. Falsify using same-draw raw-WVP/writeSerial/poseEpoch, eye FOV, successful RT getters and pixel ROI. |
| D intended centre/halo texture-alpha layers | OPEN; first 570008 flare and second glow have different source alpha, and the original queue can contain eleven distinct objects. Require PMT material+texture and same-eye RGB to separate intended layering from extra draw. |
| E host OpenXR fresh/cached/fallback | OPEN; R85 construction is upstream of R23/R24 actualFinal. Match both eye slices, sourceFrameId, accepted xrEndFrame and fresh pose. |
| F head-lock due to omitted/doubled head rotation | NARROWED_STATIC, ROOT_CAUSE_OPEN; the bit is from the same write record in a noninterleaved execution, but it may still be semantically wrong for original game camera or stale across updates. Falsify with paired WVP+sync publication serial and two controlled HMD yaw poses. |
| G camera-sync bit is always sampled independently from unrelated current global state at R30 draw | REFUTED_FOR_NONINTERLEAVED_CURRENT_SOURCE: it is cached at `RecordGameWvpWrite`. |
| H camera-sync bit is atomically tied to the copied WVP and original PMT on all execution paths | NOT_ESTABLISHED: two getters, no PMT join, no observed interleaving. |

## SOURCE_TRACE

- `src/vr/game/outrun_renderer.cpp` pinned blob `9b845778272e59585df8e2ae570f6da260cb8ec9`: `InvalidateGameWvpWrite:1701-1717`; `RecordGameWvpWrite:1719-1756`; native projected CABE c64 bypass and publication `:2076-2150`; `GetLastRawGameWvpCameraSynced:2474-2477`; `GetLastRawGameWvpWrite:2488-2502`.
- `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` pinned blob `d4d233c6b425c0a12fe2a2c2053b25f236865a4a`: `R30GetExtendedRawWvpForExactSceneEffect:1944-1980`; `R44GetOwnedRawOverlayWvp:2035-2069`; `R30BuildScreenSpaceEyeConstants:5079-5110,5191-5234`.
- `src/vr/d3d9/projected_sun_ray.hpp::BuildProjectedSunRay:11-56`: `sourceCameraSynced` suppresses head rotation but does not identify original CABE PMT.
- `src/hooks_graphics.cpp::DrawObjectAlphaProjected:787-921` CABE source wrapper; `::DrawObjectAlphaCentre:935-1070` C993 source wrapper. Original D3A5/405360/4052C0 source sequence inherited from earlier reconstruction; no fresh retail EXE byte match claimed.
- SOURCE_CHECK=seven pinned-blob static predicate checks PASS; no executable/CI/HMD test performed.

## EVIDENCE_GAPS / FALSIFICATION

- EVIDENCE_GAPS=No atomic versioned rawWVP+cameraSync read, no demonstrated intervening native c64 setter, no original PMT/texture/material alpha identity, no per-eye successful native colour-write/RT pixel, no source-camera-to-pose epoch proof, no host actualFinal/fresh XR submission or Quest3 yaw trial.
- POSITIVE_STATIC_CONTROL=Under unchanged `LastGameWvpWriteValid` and write serial between the projected WVP getter and camera-sync getter, the returned raw matrix and bit are from the same `RecordGameWvpWrite` publication. This refutes the unconditional "unrelated global bit" reading of R85.
- NEGATIVE_CONDITIONAL_CONTROL=If another game c64 write or invalidation occurs between the two reads, the flag can refer to a newer record or false while the copied WVP remains older. Source permits separate reads; **no runtime incidence or concurrent data race is asserted**.
- NEXT_FALSIFICATION_TEST=With separately authorized bounded read-only capture, sample `rawWvpWriteSerial,rawWvpPoseEpoch,rawWvpShaderEpoch,cameraSyncAtPublication` as ONE versioned snapshot and associate it with CABE ordinal1/2's actual original opaque DrawEntry/PMT, physical R30 or lower owner, L/R WVP and RGB, then fresh R23/R24 final XR pose at two yaw angles. Reject F if same-source matched camera sync and world-angular movement are correct; if only host pixels differ, investigate E instead.

## PATCH_CANDIDATE_ONLY / REGRESSION

- PATCH_CANDIDATE_ONLY=NOT_APPLIED. In a separately authorized source task, consider a bounded opt-in getter returning `{rawWvp,sourceCameraSynced,writeSerial,poseEpoch,shaderEpoch}` together for exact lens-only diagnostics, with a single-thread/versioned consistency check and no effect on render admission. Do not change R85 head rotation or suppress either original 570008 until HMD PMT/pixel evidence.
- REGRESSION=NONE_FROM_DOCS_ONLY. Any later code change risks head-rotation duplication, shader-c64 ownership leakage, native callback reentrancy and first/second CABE queue asymmetry; protect original C993 family, eleven queued CABE children, both 570008 ordinals, R26+HUD baseline, R84 comparison, R23/R24 fallback, alpha and texture.
- CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; NEXT_REVIEW=LENS_FLARE:R85_RAW_WVP_CAMERA_SYNC_SINGLE_PUBLICATION_SERIAL_TO_CABE_ORDINAL_PMT_LR_RGB_AND_FRESH_XR_YAW.
- GITHUB_RECORD=docs/reviews/dx9ex/automation/LENSFLARE-R85-CAMERA-SYNC-RAW-WVP-RECORD-20261029-0215.md; COMMIT_MARKER=[AUTO:LENSFLARE-R85-CAMERA-SYNC-RAW-WVP-RECORD-20261029-0215]; EXPECTED_CHANGED_PATHS=ONE_NEW_DOC.
