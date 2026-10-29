# CONVERSION-DX9EX-01580 — Lens 405890→404700 PMT call-site and descriptor-field proof boundary (REVIEW_ONLY)

DATE=2026-10-29 KST
TASK_ID=CONVERSION-DX9EX-01580
PRODUCTION_ID=CONVERSION-DX9EX-01580
EVENT_ID=CONVERSION-DX9EX-01580-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=f632832d5554abd08d8cf790eb19f31934b4ee2c
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
AUTOMATION_VALIDATION=PENDING_DOCS_ONLY_COMMIT_AND_REMOTE_READBACK
RUNTIME_VALIDATION=UNTESTED
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=NONDEFAULT_COMPARISON_ONLY
HUD_COMPARISON=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN

## Inherited boundaries and distinct test

- Inherit 01577: one PMT entry serial means an intercepted 405890→404700 invocation, not a unique emitted visual lobe or successful pixel; pass 0/1 and primitive fan-out can be legitimate. Inherit 01578: R7 pre-DIP has no shared unique post-eye DIP key and excludes other primitive APIs. Inherit 01579: R7 rightFailure is a preselected failure category, and its STEREO_PAIR/duplicated counter is not proof of two successful same-eye colour writes.
- Inherit LENSFLARE-OPAQUE-QUEUE-EXE-PROOF-GAP-20261029-2123: 0x464EF8/0x464EFC/0x464F00 typed queue fields lack matching retail-byte assertions in the inspected verifier; this queue-global mapping is NOT counted again.
- DISTINCT_TEST=Audit a DIFFERENT claimed authority boundary: do inspected source-side and canonical EXE verifiers actually check the two specifically hooked 405890→404700 CALL instruction sites 0x5A41 and 0x5C44, and the claimed retail entry object-id/pass field offsets +0x38/+0x20? Distinguish verified hook location from authenticated PMT objectId=0x570008 before using those labels to count the second halo.
- No retail executable was obtained or newly disassembled. This is a comparison of the current GitHub hook implementation, the named static verifiers and the prior documented source chain, not proof that the two hook addresses or struct offsets are incorrect.

## NEW_FINDING — independent PMT verifier coverage limitation, not optical root cause

NEW_FINDING=STATIC_INSPECTED_RETAIL_BYTE_VERIFIER_DOES_NOT_ASSERT_0x5A41_OR_0x5C44_TO_0x4700_NOR_DESCRIPTOR_PASS_PLUS0x20_OBJECTID_PLUS0x38;_SOURCE_TELEMETRY_TEST_CHECKS_HOOK_AND_FIELD_LITERALS_ONLY;_PMT_CALL_RECEIPT_POTENTIALLY_EXACT_INVOCATION_BUT_570008_FIELD_IDENTITY_RETAINS_PROOF_GAP_IN_THIS_INSPECTED_TEST_CHAIN.

1. Actual hook boundary: src/hooks_graphics.cpp::VRLensFlareProjected2D::apply lines 1315-1323 injects at RVA 0x5A41 and 0x5C44, described as exact original 405890-to-404700 CALLs. TraceLensOpaquePmtEntry lines 689-758 scopes the supplied pointer, records pass=entry[8] (+0x20) and objectId=entry[14] (+0x38), then calls original Module::fn_ptr(0x4700)(entry) once. A positive PRE/POST result therefore attests this instrumentation was executed under its flush/telemetry gate; it does not by itself independently authenticate the fields against original retail instruction operands, the original CABE ordinal, or a physical lens pixel.
2. Claimed layout: src/vr/game/render_semantics.hpp::LensOpaquePmtEntryReceipt lines 921-945 states in a source comment that canonical EXE proves object ID stored at +0x38 by 405360 and pass written at +0x20 by 405890. This is a claim in mod source, and might be supported by separate unpublished/manual evidence, but is not the same as a check executed by the inspected verifier.
3. Checked original-byte script: tools/disasm_outrun_goal_flare_p0.py::verify_lens_original_queue_edges lines 161-218 reads E8+rel32 CALL targets for wrapper/flush edges and specifically 0x5813→0x5360, 0x542A→0x52C0, 0x52C6→0x5890. It separately checks CABE 0x570008 PUSH/CALL ordinals and D79B ordering. Neither 0x5A41 nor 0x5C44 is checked as a CALL to 0x4700; the function does not inspect the +0x20/+0x38 descriptor store or load operands. The script docstring explicitly disclaims descriptor-identity proof. This does NOT establish that the actual retail bytes disagree.
4. Checked source-contract script: tools/verify_vr_lens_physical_telemetry.py::check lines 125-158 asserts text phrases including the two Module::exe_ptr hook sites, receipt.objectId = entry[14], receipt.pass = entry[8], authority string and the R7 target570008 predicate. These are source presence assertions, not retail bytes, calling-convention/pointer validation, pass-field provenance, or an actual successful 0x570008 native colour Draw. Other inspected test files (verify_vr_lens_transaction_trace.py, verify_dx9ex_r26_projected_flare_fusion.py, verify_dx9ex_r84_lens_source.py, verify_vr_e_flare_unhidden.py) contain no corresponding 0x5A41/0x5C44/entry[14]/entry[8] byte assertions.
5. Downstream significance is specific: src/vr/d3d9/stereo_renderer_r7.inc::DrawIndexedPrimitiveDest lines 1916-1944 prints target570008=(pmt.objectId==0x570008); R7TraceVisualEyes lines 1644-1717 and R30TryScreenSpaceFovDraw lines 6397-6437, 6890-6970 propagate pmtObjectId/opaquePmtIdentity via scoped receipt. These logs can be exact with respect to an instrumented PMT CALL while their 0x570008 semantic attribution still depends on descriptor-field provenance. A field equality is not a texture/alpha/RT identity, and the normal L/R pair is not two same-eye writes.
6. Bounded falsification witness, NOT a runtime claim: an EXE whose two 405890 CALL sites are unchanged but whose objectId field at entry[14] has not been byte-validated can produce a syntactically authoritative PMT record; neither current verifier rejects a semantically wrong objectId tag. Conversely, actual retail store/load evidence for +0x38/+0x20 and the two E8 targets would close this precise verifier gap. No hook was installed, modified or run by this task.
7. Scope is only optical diagnostics for the user's second visible lens flare. This result neither proves an extra emitter nor a wrong descriptor mapping, render mismatch, HMD head-lock, or stereo malfunction. Protected R26+HUD stays the baseline. R84/R85 source is comparison evidence, not Quest 3 PASS.

## HYPOTHESIS_LEDGER

| ID / status | Previous evidence | This task and falsifier |
| --- | --- | --- |
| A extra game-origin lens emitter — OPEN | Two intentional original CABE 0x570008 ordinals, C993/centre separate | New PMT field-verifier gap prevents elevating pmtObjectId matches to proven source cardinality; require retail descriptor identity + original source chronology + same-eye RGB |
| B 4052C0/405890 queue/native/D3DX repeat — OPEN | 01577 pass/DIP fan-out and 01578 incomplete post-DIP key | Need original descriptor and material/texture, primitive API, successful same-eye colour ROI; ordinary per-eye stereo pair is negative control |
| C wrong left/right projection or XYZRHW head-lock — OPEN_RUNTIME | R30 WVP/c64 and prior R85 eye-orientation hypotheses | Field mapping test does not alter stereo matrices; require matched original draw and two-yaw physical L/R centroid/pose |
| D glow/halo distinct material or two passes — OPEN | Original object source and possible pass0/pass1 | Field validation + material/alpha/texture and same-eye ROI required to distinguish intended layers from duplicate pixels |
| E R19/R24 host reuse/composition — OPEN_RUNTIME | Source B pixels / incoming A pose, cached frame and accepted-XR receipt joins unresolved | PMT verifier is upstream; retain R19 sourceFrameId, UV, L/R blit and accepted R24 xrEndFrame evidence per actual layer |
| F HMD-local/source-bearing transform — OPEN_RUNTIME | Head-follow report, no current-head accepted eye pose vs game source pair | Two-yaw source bearing against accepted per-eye pose/FOV after physical target identification |
| G inspected source verifier proves 0x5A41/0x5C44 retail CALL targets and +0x20/+0x38 fields — REFUTED_AS_VERIFIER_INFERENCE | Source comment and exact authority labels, but original-byte assertions not inspected | Show exact canonical EXE E8 targets, pointer ABI and original 405360/405890 store/load operands with verified instruction bytes |
| H current doubled second halo cause — BLOCKED | User report only, no source-matched Quest3/VDXR optical capture | One frame: signed evidence chain from original object→queue descriptor→PMT→native eye RGB→R19→accepted XR, repeated at two yaw poses |

## SOURCE_TRACE and EVIDENCE

- Connected GitHub pinned SOURCE_HEAD=f632832d5554abd08d8cf790eb19f31934b4ee2c.
- src/hooks_graphics.cpp blob 982f55dc91c00faf336c06317006fe4aba11db1a: TraceLensOpaquePmtEntry 689-758; VRLensFlareProjected2D::apply 1299-1349.
- src/vr/game/render_semantics.hpp blob 3197360e16febeb6f774a0967c349f7d5c8cf568: LensOpaquePmtEntryReceipt 921-963.
- tools/disasm_outrun_goal_flare_p0.py blob 4076a527de3ea297e944fd3f3bd2ed2a7f7881e2: verify_lens_original_queue_edges 161-218.
- tools/verify_vr_lens_physical_telemetry.py blob 594747ed2b4738b1c7b01fceef2597301117a659: static textual assertions 125-158.
- src/vr/d3d9/stereo_renderer_r7.inc blob 3fe94325528650ac0c1599cef498eab946edf78f: R7TraceVisualEyes 1644-1717; DrawIndexedPrimitiveDest 1916-1944.
- src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp blob cce5bc15dc1314a210ee68a1492a5991dfa06f73: R30 candidate and PMT correlation 6256-6263, 6397-6437; post-eye result 6890-6970.
- Prior reviewed: CONVERSION-DX9EX-01577/01578/01579 and LENSFLARE-OPAQUE-QUEUE-EXE-PROOF-GAP-20261029-2123.
- ORIGINAL_RETAIL_EXE_BYTE_VERIFICATION_IN_THIS_TASK=NONE; original REA/disassembly is inherited reference only, not freshly checked; MATCHED_405360_DESCRIPTOR_RUNTIME=NONE; GAME_LOG=NONE; GPU_PIXEL_RGB=NONE; XR_ACCEPTED_EYE=NONE; HMD_QUEST3_VDXR=NOT_TESTED.
- EVIDENCE_GAPS=The canonical executable's actual bytes at hook sites and original field-write instructions are not newly verified here; whether independent byte evidence already exists elsewhere is unresolved; matching 0x570008 PMT to the doubled second visible halo, exact texture/alpha and per-eye physical RGB remains unresolved.

## NEXT_FALSIFICATION_TEST / expected traces

1. Read-only original EXE discriminator: against the SHA-pinned canonical retail executable, validate 5-byte E8 rel32 at 0x5A41 and 0x5C44 and compute both destinations. Confirm the argument pointer used for 404700. Disassemble authenticated 405360 object-id +0x38 descriptor store and 405890 pass +0x20 store, then confirm 404700 reads/uses the same offsets. Include instruction byte hashes, addresses, operand widths and a negative-control neighbouring field. The existing 0x5813/0x542A/0x52C6 call checks must still pass. No new hooks or executable edits.
2. If the call sites or offsets fail validation, downgrade only the asserted PMT field-identity confidence in a separately authorized diagnostic proposal, inspect the real layout and compare against one original 405360 descriptor. This is NOT permission to patch current C++ or to delete any emitter.
3. If all sites and fields validate, G becomes REFUTED_AS_GAP_CLOSED_FOR_EXACT_BINARY; still collect pmtEntrySerial, flush/source ordinal, pass, pmtObjectId, texture, alpha, native API and successful L/R RT/ROI for the user's second halo. Two PMT passes from one descriptor and one normal L/R pair are separate expected controls, not abnormal duplicates.
4. Same HMD two-yaw discriminator: actual second lobe already doubled within one native eye suggests A/B/D; single native lobe but doubled after accepted R19/R24 image suggests E; correct RGB cardinality but wrong per-eye bearing suggests C/F. Collect sourceFrameId/presentQpc and accepted eye pose; treat missing sparse logs as unknown.

PATCH_CANDIDATE_ONLY=DIAGNOSTIC_VALIDATION_ONLY_NOT_APPLIED: files tools/disasm_outrun_goal_flare_p0.py::verify_lens_original_queue_edges:161-218 and tools/verify_vr_lens_physical_telemetry.py::check:125-158; in a separately authorized future task, add byte-backed PMT call-edge and +0x20/+0x38 field assertions and negative control. No render-source change warranted; do not modify 404700 hook behavior, source producer, 4052C0 flush, eye WVP, RTV, alpha, OXR, B9200 +5 hook or protected baseline.
REGRESSION_RISK=DOCS_ONLY_NONE; future verifier enhancement must fail closed on unsupported EXE versions, avoid changing runtime hook or optical routing, and preserve normal two-eyes-per-primitive semantics.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:ORIGINAL_405890_TO_404700_5A41_5C44_CALL_AND_405360_405890_ENTRY_PLUS38_PLUS20_BYTES_VS_570008_PMT_EYE_RGB
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01580.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01580]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01580.md
