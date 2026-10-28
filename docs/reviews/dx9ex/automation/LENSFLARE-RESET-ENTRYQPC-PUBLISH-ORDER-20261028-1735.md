# LENSFLARE-RESET-ENTRYQPC-PUBLISH-ORDER-20261028-1735 — Reset entry-QPC versus completion-epoch ordering (LENS_FLARE_ONLY / REVIEW_ONLY)

- DATE=2026-10-28 17:35 KST; RUN_KEY=LENSFLARE-RESET-ENTRYQPC-PUBLISH-ORDER-20261028-1735; SOURCE_HEAD=c6b4140f1edfa714c7ef13a1ce261d0c9bd8fb1c; SOURCE_SSOT=CONNECTED_GITHUB_PINNED.
- BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE; R84=COMPARISON_ONLY; B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN.
- SCOPE=LENS_FLARE_ONLY; MODE=DX9EX_REVIEW_ONLY; CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY; CI_SKIP=NONE.
- INHERITED_NOT_RESCORED=01550 optional 0x570002 sequence anchor, 01551 Reset physical/logical extent, 01552 viewport-origin predicate and old seqlock writer hazard, V3 material Reset trace integration, 01547-49 XR pixel probe limitations. This review does not claim new optical or original-emitter evidence.

## NEW_FINDING — independently source-proven diagnostic timestamp semantic mismatch

NEW_FINDING=STATIC_PROOF_RESET_TRACE_QPC_IS_RESET_ENTRY_TIME_NOT_PUBLISH_TIME; COMPLETION_MONOTONIC_RESET_EPOCH_DOES_NOT_IMPLY_MONOTONIC_RESET_QPC. This is a proven timestamp-semantic discrepancy and a conditional causal-join false-positive/false-negative risk, **not** evidence of a live Quest3 lens flare defect.

1. `src/vr/d3d9/ex_device_upgrade.cpp::ResetCompatDest:463-464` calls `QueryPerformanceCounter(&resetQpc)` immediately after obtaining the Ex interface and **before** `ResetEx` at :488-490, optional `RestoreClassicResetState` at :492-501, and backbuffer/viewport/scissor queries at :516-553.
2. At :503-505, `trace.qpc = resetQpc.QuadPart` copies that **entry** timestamp; at :554-555 `D3D9ResetTrace::Publish(trace)` assigns a new reset epoch. The log at :559-574 reports `qpc={}` beside `publishOrder=COMPLETION_MONOTONIC`, but only the epoch allocation is completion-ordered; the QPC is not a publication/finish timestamp.
3. `src/vr/d3d9/reset_trace.hpp::Publish:69-101` serializes writers, allocates `resetSerial=NextSerial+1` inside the writer lock, then stores `snapshot.qpc` unchanged at :83. `Read:104-140` returns stable snapshot fields; the seqlock does not change timestamp semantics. This is distinct from the already-repaired multiwriter-even-generation concern of 01552.
4. **Constructive conditional overlap counterexample, not an observed execution:** Reset A enters at QPC=100, Reset B enters at 200; B completes its state queries and publishes epoch 1 at 300 with stored qpc=200; A completes and publishes epoch 2 at 400 with stored qpc=100. The published reset epochs are 1 then 2, yet their stored QPC values go 200 then 100. Thus `resetEpoch` monotonic does not imply `resetQpc` monotonic. The writer lock serializes publication, not the earlier ResetEx calls.
5. **Single-Reset boundary control:** A enters at QPC=100, a C993/CABE source event at QPC=150 still reads the previously published epoch while A is in ResetEx, and A publishes at QPC=200 carrying `resetQpc=100`. A timeline based on the inherited reset QPC alone could misclassify that source event as post-reset, although its resetEpoch is old. This requires a concurrent source event; no actual concurrency was measured. The QPC field is the start of the *last published Reset*, not the time of the lens source event.
6. `src/hooks_graphics.cpp::DrawObjectAlphaProjected:790-795,847-873` (CABE 0x570008) and `DrawObjectAlphaCentre:971-977,978-1004` (C993 0x570002/006/00F/010) read the last Reset snapshot and log `resetEpoch/resetQpc/resetFlags/resetSnapshotStable`, but do not log a separately sampled source-call QPC in those FULL records. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30TryScreenSpaceFovDraw:6213-6221,6370-6393,6399-6468` logs the inherited Reset QPC alongside physical L/R WVP/RT receipts, not an R30 physical-draw QPC.
7. The existing host `vrhost/src/main_r23.cpp` fresh/cached projection and XR eye/pixel traces cannot resolve this timing ambiguity without a separately recorded game-source/draw QPC and final submitted sourceFrameId/poseSequence. The V3 Reset epoch is useful for coarse state generation, not a proof of same-frame emitter→opaque PMT→colour write→XR eye ROI.

## HYPOTHESIS_LEDGER

| Axis | Status / falsifier |
| --- | --- |
| A extra original D3A5/C993/CABE emitter | OPEN; entry-QPC ambiguity does not create source calls. Falsify with original 40CBC0 invocation count and 0x570002/006/00F/010 + both intended 0x570008 source receipts under one fresh game frame. |
| B opaque 405360/4052C0 queue, D3DX/native double submit | OPEN; source reset epoch does not identify opaque descriptor, flush, PMT or same-eye colour write. Require those exact identities and two successful writes to the **same** eye. |
| C incorrect original c64 / R30 L/R WVP / viewport | OPEN; V3 full viewport+scissor comparisons repair 01552 dimension-only issue, but no optical ROI proof. Compare actual native c64, each eye WVP, RT and physical viewport at draw. |
| D intentional separate centre/halo material | OPEN; two CABE 0x570008 ordinals and C993 family remain intentional source candidates. Require material/texture/alpha and actual same-eye centroid identity. |
| E host fresh/cached XR projection or duplicate composite | OPEN_RUNTIME; the inherited reset QPC is not a source-frame clock. Join actual final submission sourceFrameId/poseSequence, array slice and ROI to source/native physical draw. |
| F head-lock versus world-fixed bearing | OPEN_RUNTIME; reset epoch/QPC alone cannot distinguish head-yaw from world-sun direction. Require paired fixed-world yaw and translation controls on fresh XR frames. |
| G V3 completion-monotonic resetEpoch implies completion-monotonic resetQpc | REFUTED_STATIC; qpc sampled before ResetEx while epoch allocated after it. Overlapping resets can invert timestamp order without violating serialized publisher. |
| H same Reset QPC in C993/CABE and R30 means same physical-frame event time | REFUTED_AS_UNIVERSAL; both sample last Reset's entry timestamp; equality proves only inherited reset snapshot timing, not source/draw simultaneity. |

## SOURCE_TRACE / EVIDENCE_GAPS / FALSIFICATION

- SOURCE_TRACE: connected GitHub pinned `c6b4140f1edfa714c7ef13a1ce261d0c9bd8fb1c`; `src/vr/d3d9/ex_device_upgrade.cpp:453-575` (blob `6866b9928c49bd2bd42ccb3a78997a07d6f69e45`); `src/vr/d3d9/reset_trace.hpp:69-140` (blob `6bcb416bb91ed625f4377c5ea88c893babd735bf`); `src/hooks_graphics.cpp:787-873,943-1004` (blob `9678bed2508fb4dba243e9e82a409128eb3d4a46`); `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6209-6221,6370-6468` (blob `555f8a7d84962c4b16e9f59f6127b9f70c24dd1d`); `vrhost/src/main_r23.cpp:1838-1924,3753-3823,4205-4274` (blob `15c5ea065f4cc2c30ebd2d45aefbaa48581f4ede`).
- EVIDENCE=PINNED_GITHUB_SOURCE_STATIC_ORDER + TWO_EXPLICIT_SYNTHETIC_SCHEDULES. DISASM=NONE_NEW; RETAIL_EXE_BYTE_MATCH=NONE_NEW; LIVE_LOG=NONE_NEW.
- EVIDENCE_GAPS=No demonstrated overlapping Reset calls or simultaneous original-sun draw, no source/draw-time QPC, no opaque descriptor/4052C0 PMT-to-physical L/R colour ROI proof, no actual fresh/cached OpenXR final eye ROI, no Quest3 headset yaw/translation replay. No confirmed optical root cause.
- FALSIFICATION: In one live run, collect Reset entry, ResetEx return, post-replay snapshot, **publish** QPC and serial, then separately C993/CABE source-call QPC and R30 native-draw QPC; compare each event against resetEpoch. A single non-overlapping Reset with all source/draw events outside the Reset window can eliminate this ambiguity for that run. If two Reset calls overlap, confirm whether completion serial and entry QPC invert; absence of overlap does not refute the static timestamp semantics.
- NEXT_REVIEW=LENS_FLARE:RESET_ENTRY_VS_PUBLISH_QPC_WITH_SOURCE_C993_CABE_NATIVE_LR_RT_AND_FRESH_XR_FRAME_ROI_JOIN.

## PATCH_CANDIDATE_ONLY / REGRESSION

- PATCH_CANDIDATE_ONLY=NOT_APPLIED: In a separately authorized source task, distinguish `resetEntryQpc` from `resetPublishQpc`, sample publication time at/inside the serialized publish boundary, and log independent C993/CABE source-call and R30 draw QPC. Keep resetEpoch as the stable generation join; do not repurpose entry QPC as a draw clock. Do not alter source emitter, 4052C0 queue, native draw, c64, viewport admission or XR submission.
- REGRESSION=LOW_FOR_LABEL_ONLY_BUT_HIGH_IF_USED_AS_RENDER_POLICY: never use entry QPC or coarse reset epoch to suppress an original 0x570008/C993 flare or force eye projection. Preserve original two CABE calls, C993 0x570002/006/00F/010, D3DX/opaque flush, alpha/material, physical L/R RT restore, R26+HUD immutable baseline, R84 comparison-only and no unsafe B9200 post-CALL/+5.
- CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; EXPECTED_CHANGED_PATHS=EXACTLY_THIS_ONE_NEW_DOC; COMMIT_MARKER=[AUTO:LENSFLARE-RESET-ENTRYQPC-PUBLISH-ORDER-20261028-1735]; SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY; CI_SKIP=NONE.
