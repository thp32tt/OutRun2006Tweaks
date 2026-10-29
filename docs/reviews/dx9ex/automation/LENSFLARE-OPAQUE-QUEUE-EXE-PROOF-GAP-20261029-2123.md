# LENSFLARE-OPAQUE-QUEUE-EXE-PROOF-GAP-20261029-2123 — D79B queue-layout proof-label regression, lens-only REVIEW_ONLY

DATE=2026-10-29 KST
RUN_KEY=LENSFLARE-OPAQUE-QUEUE-EXE-PROOF-GAP-20261029-2123
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=b7c0dcc0d25112e6566d802895e4bd823659a29c
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
REVIEW_SCOPE=LENS_FLARE_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE

## NEW_FINDING — static diagnostic authority mismatch, NOT a verified optical defect

NEW_FINDING=SOURCE_STATIC_D79B_QUEUE_LAYOUT_EXE_PROVEN_LABEL_NOT_AUTHENTICATED_BY_INSPECTED_RETAIL_BYTE_VERIFIER;_STRING_ASSERTION_ONLY;_RECONSTRUCTION_CANDIDATE_REMAINS_UNPROVEN_IN_THIS_EVIDENCE_CHAIN.

**Distinct current test:** The 2026-10-29 source update `ea6504272` replaced raw `queueWords` with named `queueCount/queueCapacity/matrixCount` and stamped both PRE and POST `VR TRACE LENS OPAQUE FLUSH FULL` with `queueLayout=EXE_PROVEN_405160_4052C0`. Test update `f9ba343db` requires that literal string. However the **actual inspected verifier** `tools/disasm_outrun_goal_flare_p0.py::verify_lens_original_queue_edges` checks original E8 CALL relationships `0x5813->0x5360`, `0x542A->0x52C0`, `0x52C6->0x5890`, two CABE PUSH/CALL sites and D79B ordering; it does **not** assert the memory loads/stores, struct offsets or reset writes for `0x464EF8/0x464EFC/0x464F00` or `0x405160`. The corresponding `tools/verify_vr_lens_physical_telemetry.py` only asserts presence of the authority string in C++ source, not EXE bytes or runtime queue invariants.

The prior `LENSFLARE-D79B-OPAQUE-QUEUE-WORDS-20261029-1829.md` explicitly labels these fields **reconstruction-derived candidates**, noting that the logical reconstructed C++ queue is not a retail binary ABI and calling for retail 405160/4052C0 instruction verification. That earlier mapping and 01576's patchCount-vs-opaque-count counterexample are **not** re-scored here. The new, separate observation is that **later instrumented source/test promotes the candidate mapping to an `EXE_PROVEN` telemetry authority label without a matching field-layout assertion in the inspected canonical verifier**. The log's label cannot itself upgrade evidence to verified original retail layout.

This is a source/verification-contract gap, not proof that the three candidate values are wrong, nor that the second visible lens halo is doubled by queue behavior. A retail-byte proof may exist in an external artifact not examined here; no canonical EXE or live trace was executed this run. The original D79B full opaque flush barrier remains valid **conditionally on reconstructed normal semantics** and must not be confused with an authenticated live count.

## SOURCE_TRACE — pinned GitHub files, functions and lines

1. `src/hooks_graphics.cpp::VRLensFlareProjected2D::TraceLensOpaqueFlush:789-867`: reads `0x464EF8/0x464EFC/0x464F00`, prints typed `queueCount,queueCapacity,matrixCount` and `queueLayout=EXE_PROVEN_405160_4052C0` in PRE/POST, and wraps original `Module::fn_ptr(0x52C0)()`. A logged value is not a verified binary field type.
2. `tools/disasm_outrun_goal_flare_p0.py::verify_lens_original_queue_edges:164-214`: validates E8 CALL edges, CABE two 570008 source calls and D79B ordering, but does not validate `0x405160` reset or opaque count/capacity/matrix offsets. Its lens disassembly windows include queue core, which is **output for inspection**, not an assertion of these field offsets.
3. `tools/verify_vr_lens_physical_telemetry.py::check:125-145`: `assert "queueLayout=EXE_PROVEN_405160_4052C0" in hook`; no executable-memory-layout proof. This is a textual contract only.
4. `src/vr/game/render_semantics.hpp::LensOpaqueFlushReceipt:901-918` and `::LensOpaquePmtEntryReceipt:921-945`: flush serial groups an invocation; PMT serial groups a scoped original 405890->404700 call; neither is a texture/eye pixel or original CABE ordinal proof.
5. `src/vr/d3d9/stereo_renderer_r7.inc::DrawIndexedPrimitiveDest:1916-1944`, `::R7TraceVisualEyes:1644-1717`, and `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30TryScreenSpaceFovDraw:6256-6263,6912-6967`: primitive PRE vs physical eye-result records do not provide the accepted same-eye RGB contribution or final XR submission.
6. Prior review `docs/reviews/dx9ex/automation/LENSFLARE-D79B-OPAQUE-QUEUE-WORDS-20261029-1829.md`: reconstructed PC VA 0x864EF8 candidate `count/capacity/matrix_count`; retail-byte verification outstanding. `CONVERSION-DX9EX-01577.md` and `01578.md` already cover PMT pass fan-out, pre-DIP vs success and absent unique DIP-to-eye key. Those are not new findings here.
7. Source-change commits `ea6504272` (typed/EXE_PROVEN label) and `f9ba343db` (literal assertion) were inspected via connected GitHub diff; no original retail binary disassembly rerun.

## HYPOTHESIS_LEDGER (A/B/C/D/E/F)

| Axis | Status / what this distinct test establishes | Needed optical falsifier |
| --- | --- | --- |
| A extra original emitter | OPEN. Original D3A5/C993 and both CABE 570008 ordinals are distinct source paths; queue label authenticates neither. | Exact original object/ordinal -> queue descriptor -> texture/alpha -> same-eye RGB. |
| B queued/D3DX/native double Draw | OPEN. `EXE_PROVEN` cannot be used to declare a D79B live drain without byte or runtime proof. Prior normal reconstructed D79B barrier is retained conditionally. | Verified original count offsets and D79B PRE/POST values, then PMT/pass/primitive API, per-eye successful Draw+ROI; one L/R pair is normal. |
| C wrong L/R WVP/c64/depth | OPEN_RUNTIME. Queue count is not WVP, c64 or disparity. | Per-PMT L/R WVP/c64 and camera/light direction with accepted XR pose/FOV. |
| D legitimate layered alpha vs extra halo | OPEN. Two source 570008 calls and potential pass fan-out can be intentional; raw count cannot identify the user's second of 5–6 elements. | Exact texture0, blend/alpha/Z, source ordinal and same-eye before/after RGB ROI. |
| E host R19 fresh/cached and R24 final XR | OPEN_RUNTIME. No accepted-eye image or EndFrame causal join in this review. | Native RT -> selected R19 source frame/UV -> accepted R24 per-eye image/pose. |
| F head-lock and wrong yaw parallax | OPEN_RUNTIME. No Quest3 two-yaw result. | Two-yaw game camera, sun bearing, L/R ROI and HMD pose for the same accepted XR frames. |
| G `EXE_PROVEN` string means original queue layout byte-verified by inspected verifier | REFUTED_AS_VERIFIER_INFERENCE. The checked script verifies CALL edges, not these three field offsets; source test checks a literal string. | Show actual SHA-pinned retail EXE instruction load/store assertions and successful run plus matched live queue-state values. |

## FALSIFICATION — safe, specific next test

- **P1 original-byte proof:** In a separately authorized read-only verifier run against the known canonical SHA-256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, disassemble 405160 reset and 4052C0/405890 queue count/capacity/matrix loads and writes. Assert exact PC VA/RVA field offsets, operand widths, reset values and conditional branches; record actual byte-window hashes and instruction offsets. No B9200 +5 hook.
- **P2 positive runtime count control:** One same `flushSerial` D79B PRE/POST with original 570008 ordinal1 candidate; if layout proven and normal flush succeeds, expected POST count=0, matrixCount=0, capacity stable (typically 0x100 after 405160 reset). The PRE count is **multi-object descriptors**, not flare count.
- **N1 negative control:** `patchCount=0` can coexist with admitted opaque PMT; a non-570008 descriptor in D79B must not be labeled second halo by source-window ordinal.
- **N2 layout falsifier:** If verified retail instruction offsets or bounded runtime values contradict the named fields, keep them raw/untrusted and investigate layout/branch; do not infer double Draw from anomalous count.
- **Optical discrimination:** Exact 0x570008 PMT, native API/primitive, texture/alpha/blend and successful L/R RT RGB contribution, R19 fresh/cached selected image and R24 accepted XR eye, two yaw positions. If one native ROI but two accepted XR lobes, prioritize E; if two unexplained same-eye native contributions, prioritize B/D; if correct native multiplicity but yaw/depth mismatch, prioritize C/F.

## EVIDENCE_GAPS

No canonical retail EXE bytes or execution of the disassembler this run; no proof in the **inspected verifier** of the three queue field offsets or 405160 reset writes; no live queue PRE/POST sample for the current HEAD, no actual 570008 PMT texture/alpha, native same-eye RGB delta, accepted OpenXR eye receipt or Quest3 two-yaw capture. Absence of an assertion in the inspected script is not proof that an external original-byte artifact does not exist.

## PATCH_CANDIDATE_ONLY / REGRESSION

PATCH_CANDIDATE_ONLY=NOT_APPLIED. In a future separately authorized diagnostics change, either attach verified retail-byte field-layout receipts and bounded runtime invariant tests before retaining `EXE_PROVEN`, or downgrade the label to `RECONSTRUCTION_CANDIDATE` while preserving the three raw words. Never change game render route, CABE call count, PMT alpha, WVP/c64, L/R targets, OpenXR selection or source baseline based solely on queueCount. No dangerous B9200 post-CALL/+5 detour.
REGRESSION=DOCS_ONLY_NONE. Future changes must avoid false queue-layout authority, loss of intended two-pass/dual-ordinal halos, unbounded telemetry overhead, broken right-eye restore or altered frame pacing; R26+HUD remains immutable and R84 is comparison-only.

CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:CANONICAL_EXE_405160_4052C0_QUEUE_FIELD_OPERAND_BYTE_ASSERT_THEN_D79B_PMT_TEXTURE_ALPHA_TO_LR_RGB_R19_R24_TWO_YAW
EXPECTED_COMMIT_MARKER=[AUTO:LENSFLARE-OPAQUE-QUEUE-EXE-PROOF-GAP-20261029-2123]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/LENSFLARE-OPAQUE-QUEUE-EXE-PROOF-GAP-20261029-2123.md
