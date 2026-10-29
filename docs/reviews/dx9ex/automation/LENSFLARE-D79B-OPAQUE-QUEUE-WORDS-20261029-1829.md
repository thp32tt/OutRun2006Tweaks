# LENSFLARE-D79B-OPAQUE-QUEUE-WORDS-20261029-1829 — D79B opaque queueWords reconstruction-derived field mapping (REVIEW_ONLY)

DATE=2026-10-29 KST
RUN_KEY=LENSFLARE-D79B-OPAQUE-QUEUE-WORDS-20261029-1829
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=7d19d10a920957add8cf5635de74bf68eb2b0054
REVIEW_SCOPE=LENS_FLARE_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE

## NEW_FINDING / scope

NEW_FINDING=STATIC_RECONSTRUCTION_DERIVED_OPAQUE_QUEUEWORDS_FIELD_CANDIDATES_AND_FALSIFIABLE_D79B_COUNT_TEST; NOT_ORIGINAL_EXE_BYTE_PROOF; NOT_HMD_ROOT_CAUSE.

This is a **new, narrower source-join** resolving a previously *unmapped* diagnostic: the current `TraceLensOpaqueFlush` reads three consecutive 32-bit values at EXE-relative offsets `0x464EF8`, `0x464EFC`, `0x464F00` and prints them as `queueWords`. `Module::exe_ptr` adds the executable's loaded module base. The independent original-game **reconstruction** explicitly labels the opaque queue at **PC VA 0x864EF8** (nominal EXE base 0x400000) and models its first four fields as `count, capacity, matrix_count, matrix_capacity`. Under the reconstruction's layout, the three existing raw words are therefore **candidate opaque-entry count, opaque capacity, and matrix-pool count**, respectively. This is more informative than treating all three as opaque bytes, but **must not be promoted to retail EXE layout proof without checking original instructions and an actual queue-state trace**.

In the reconstruction `render_queues_reset_405160` initializes opaque capacity and matrix capacity to `0x100` and alpha capacities to `0x600`; `render_queue_flush_4052c0` consumes `rc.opaque.count`, then resets `rc.opaque.count=0` and `rc.opaque.matrix_count=0` while leaving capacity unchanged and switching immediate mode to 1. Thus a normal D79B pre/post receipt has a **falsifiable** expectation:
- `queueWords[0]` (candidate opaque.count): nonnegative, at most capacity, POST 0;
- `queueWords[1]` (candidate opaque.capacity): normally `0x100`, unchanged across flush;
- `queueWords[2]` (candidate opaque.matrix_count): at most matrix capacity, POST 0.
The count is a **mesh descriptor count**, not source object count, visible flare-lobe count, material primitive count, successful native eye Draw count or alpha undo patch count. `0x570008` ordinal1 may yield zero or multiple descriptors depending on visibility/LOD; ordinal2 is a separate immediate transaction after D79B.

This does **not** establish that the real retail EXE memory at the above addresses matches the reconstruction, nor prove that the user-visible doubled second flare comes from opaque queue cardinality. It only supplies a specific non-invasive discriminator using values **already logged**. If the POST triple violates the predictions under a normal successful flush, investigate the actual retail layout, hook placement/branch, nested flush, or reconstruction divergence before using the fields as evidence.

## SOURCE_TRACE — checked exact GitHub sources

1. Current `src/plugin.hpp:21-29`, `Module::exe_ptr`: executable loaded base + RVA, not an absolute VA read. The nominal mapping `0x400000 + 0x464EF8 = 0x864EF8` is arithmetic; relocated EXE base is handled by `ExeHandle`.
2. Current `src/hooks_graphics.cpp::TraceLensOpaqueFlush:703-795`: `readU32(0x464EF8/0x464EFC/0x464F00)` before and after `Module::fn_ptr(0x52C0)()`; `0x464F14` is a **separate** patch/undo counter. `queueWords` are currently printed without field names and PMT identity remains `UNVERIFIED`.
3. Reconstructed original `r4dius/outrun2-decomp@e1e1c592b802a6f3f7020a676abd3ba1be479e62`, `src/platform/pc_render_queue.hpp:15-29`: labels `PC 864EF8 opaque / 8612D8 alpha` and the first four logical `PcRenderQueue` fields `count, capacity, matrix_count, matrix_capacity`.
4. Same original reconstruction `src/platform/pc_render_queue.cpp:207-212`: reset initializes opaque capacity and matrix capacity `0x100`, alpha `0x600`; `:171-179` increments opaque/alpha `q.count` **per admitted visible mesh node**, not per 4056D0 source call.
5. Same reconstruction `src/platform/pc_render_flush.cpp:970-980`: `render_queue_flush_4052c0` uses `rc.opaque.count`, calls 405890, clears undo and resets opaque count/matrix_count and immediate flag. It does not drain `rc.alpha`.
6. Same reconstruction `src/platform/race_course_passes.cpp:695-716`: CABE first `0x570008` queued, D79B 4052C0 intervenes, second `0x570008` follows. Current original-EXE contract *script* `tools/disasm_outrun_goal_flare_p0.py:76-103,151-209` contains byte-assertions for D6BA/D79B/D7B4 and the 4056D0→405360→4052C0→405890 CALL edges, but **was not run on retail EXE bytes** this review.
7. Prior `CONVERSION-DX9EX-01576.md` proved `patchCount != opaque draw count` and expressly left all three `queueWords` unmapped; `LENSFLARE-CABE-D79B-INTERVENING-FLUSH-20261029-1704.md` proved the normal opaque flush barrier. This review does not rescore either finding.

## HYPOTHESIS_LEDGER

| ID | Current status and distinct falsifier |
|---|---|
| A extra original emitter | OPEN. First and second CABE `0x570008` are intentional; compare exact 4056D0 source serial with queue mesh-descriptor count, not `queueWords[0]` alone. |
| B duplicate same-eye physical Draw | OPEN. One opaque entry can produce multiple primitives and L/R Draws. Prove repeated **same source descriptor+primitive+eye RT+RGB write**, not just `count>1`. |
| C wrong per-eye WVP/c64 | OPEN. Join each admitted opaque descriptor to 405890 matrix, R30 physical c64, L/R RT and host source pose. Queue count alone does not encode projection. |
| D intended layered alpha versus ghost | OPEN. Two source CABE ordinals use different scale/alpha. Need exact PMT/texture/alpha and per-eye RGB contribution, not mesh count. |
| E R19 fresh/cached and R24 XR submission | OPEN. Require accepted XR invocation ID, actual eye images and pose/FOV, not just R19 pre-Acquire log. |
| F head-lock versus source camera mismatch | OPEN. Need matched Quest3 two-yaw game/XR pose and eye ROI; reconstruction queue fields cannot prove it. |
| G `queueWords` are wholly unknowable | NARROWED: reconstructed address/layout supplies specific **testable candidate mapping**; retail-byte proof remains missing. |
| H `queueWords[0]` equals visible lens-lobe count | REFUTED AS GENERAL INFERENCE by per-visible-mesh descriptor admission and later material/eye draw fan-out. |

## FALSIFICATION / evidence controls

- **Positive normal-flush control:** capture PRE and POST `queueWords` from same `flushSerial` for D79B; candidate capacity stays `0x100`, candidate count/matrix_count POST become zero. A separate first 570008 enqueue must be source-joined to identify whether it contributed descriptors.
- **Negative unrelated scene control:** D44B opaque flush can have descriptors with no lens source serial; `queueWords[0]>0` does not imply lens material. Also compare 542A inline 405360 flush.
- **Negative empty-undo control:** `patchCount=0` can coexist with `queueWords[0]>0` if source has no colour override but visible meshes (previous 01576 counterexample); this task supplies candidate field identification, not a new observation.
- **Counterexample against mapping:** `queueWords[1]` is not `0x100` after a verified 405160 reset, or normal D79B POST `queueWords[0]`/`[2]` remain nonzero. Recheck actual retail EXE disassembly/data offsets and reset timing; do not label a renderer defect on this discrepancy alone.
- **Physical/optical discriminator:** if one source descriptor/primitive writes twice to same eye RT and the second halo ROI changes twice, prioritize B; if native RT has one halo but accepted XR eye has two, prioritize E; if the same lobe is in both with incorrect yaw-parallax, prioritize C/F. No HMD trace supplied.

## EVIDENCE_GAPS

Original retail EXE bytes/disassembly for 405160 and 4052C0 field loads/stores, exact live opaque queue structure, validated `queueWords` PRE/POST values for the current build, original 405890 PMT/texture/alpha, descriptor generation, physical native L/R colour ROI, R19/R24 accepted XR eye join, two-yaw Quest3/VDXR trace. The reconstructed `PcRenderQueue` is a C++ *logical model* with vectors and is **not** a binary ABI definition; only its documented first-field interpretation is being tested.

## PATCH_CANDIDATE_ONLY / REGRESSION

PATCH_CANDIDATE_ONLY=NOT_APPLIED. Once retail-byte validation confirms the offsets, a **future separately authorized diagnostic-only** change may rename the existing three printed fields to `opaqueEntryCountCandidate`, `opaqueCapacityCandidate`, `opaqueMatrixCountCandidate` (or verified names) and add a bounded `count<=capacity` invariant. No additional 405890/B9200 hook, queue mutation, de-duplication, source call suppression, alpha/texture change, stereo route change or unverified hard-coded memory layout.
REGRESSION=DOCS_ONLY_NONE; future instrumentation risks crash from wrong offsets and frame pacing from per-PMT logging. Preserve R26+HUD, R84 comparison-only, both intentional 570008 calls, L/R/RT restore and original fallback.

CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:RETAIL_405160_4052C0_864EF8_FIELD_BYTE_PROOF_THEN_D79B_QUEUEWORDS_COUNT_TO_570008_PMT_TEXTURE_ALPHA_LR_RGB_XR_TWO_YAW
EXPECTED_COMMIT_MARKER=[AUTO:LENSFLARE-D79B-OPAQUE-QUEUE-WORDS-20261029-1829]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/LENSFLARE-D79B-OPAQUE-QUEUE-WORDS-20261029-1829.md
