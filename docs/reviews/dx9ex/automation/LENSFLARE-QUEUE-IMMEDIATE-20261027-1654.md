# LENSFLARE-QUEUE-IMMEDIATE-20261027-1654 — original 0x4056D0 queue/immediate split makes CABE same-handle calls distinct physical submission classes (REVIEW_ONLY)

- DATE=2026-10-27 16:54 KST; RUN_KEY=LENSFLARE-QUEUE-IMMEDIATE-20261027-1654; TARGET=thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus; SOURCE_HEAD=f7834b5468a3b6870bb2da6cb3457f6ac85ce844; REVIEW_SCOPE=LENS_FLARE_ONLY; MODE=DX9EX_REVIEW_ONLY.
- BASELINE=R26+HUD; BASELINE_SHA=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9; R84=COMPARISON_ONLY; B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN.
- PREVIOUS=CONVERSION-DX9EX-01522..01529 and LENSFLARE-POSE-20261027-1546. 01529 established that CABE ordinal logs are original-call counters, not per-eye GPU receipts; THIS run independently traces why two original calls with the SAME handle can have DIFFERENT deferred/immediate submission boundaries, alpha and geometry. 01522's C993 inner-scope/head-ray bypass remains separate.
- EVIDENCE=GitHub pinned current source blobs + independently read r4dius/outrun2-decomp reconstructed original 4056D0/405360/4052C0 and 40CBC0 sources. No new original EXE byte/disassembly, shader, texture readback, Quest3, or GPU capture. RECONSTRUCTION_NOT_RUNTIME_ATTESTATION=YES.
- CODE_CHANGE=NO; PATCH_APPLIED=NO; BUILD=NOT_RUN; CI=NOT_RUN; CI_SKIP=NONE; DOCS_ONLY_BUILD_GATE=NOT_REQUIRED; RUNTIME_VALIDATION=UNTESTED.

## NEW_FINDING — original queue writer, not guaranteed synchronous GPU Draw

NEW_FINDING=SOURCE_GROUNDED_CABE_570008_DEFERRED_FIRST_VS_IMMEDIATE_SECOND_WITH_DISTINCT_TRANSFORM_ALPHA_AND_4052C0_FENCE.
STATIC_PROOF=The game's `DrawObjectAlpha_Internal` resolves to EXE+0x56D0 (VA 0x4056D0), which the independent original-game reconstruction implements as an object colour-override **queue writer** into 405360; it is NOT intrinsically a one-call/one-physical-GPU-draw API. In queued mode 405360 returns after building nodes; in immediate mode it invokes 4052C0 to flush. Current C993/CABE hook semantic scopes are RAII around this 4056D0 call and restore on return, so a deferred physical draw need not inherit the wrapper's `ProjectedScreenEffect2D`/producer token at the actual native Draw. This is a conditional source-lifetime gap, NOT proof that a specific current HMD flare draw was mistagged.

### Independently traced original 40CBC0 call sequence

| Original object call | Reconstructed immediate mode at 4056D0 | Original matrix/alpha distinction | Physical boundary |
| --- | --- | --- | --- |
| C993 0x570002 | entry-dependent; not proven here | visible sun disc, intensity * visibility; near artificial z=-1 plane | may be immediate or deferred; do NOT assume |
| C993 0x570010 and 0x57000F | **queued**: explicit `immediate_8999b0=0` before these calls | far-scaled projected sun/occlusion companions | explicit 4052C0 after both |
| C993 0x570006 | **immediate** after the preceding 4052C0, absent an uninspected intervening mode reset | glow at z=-0.2, alpha intensity * bright * visibility | own 405360 -> 4052C0 |
| CABE 0x570008 ordinal 1 | **queued**: explicit `immediate_8999b0=0` before flare list | along = 0.16*spread, size = 0.09*size, alpha = intensity*flare | grouped 4052C0 after other ring objects |
| CABE 0x570008 ordinal 2 | **immediate**: prior 4052C0 sets mode=1 | along = bitfloat(0xbb449ba6), size = 1.5, alpha = intensity*glow (ring*visible) | own 405360 -> 4052C0, then render-pass defaults |

These are two intentional source instances with the **same object handle** but different transform/scale/alpha and separate queue transactions. Same ID + same Present + same eye + same texture (if confirmed) is still insufficient to call ordinal 2 a duplicate native replay. A duplicate requires repetition of the **same source invocation identity**, not two intended calls. Conversely the original queue split creates a concrete mechanism to test whether current VR semantic/c64 ownership differs between first and second submissions and causes mismatched head/eye projection.

## SOURCE_TRACE — exact checked paths/lines

1. Current `src/game_addrs.hpp:485-486` maps `Game::DrawObjectAlpha_Internal` to EXE+0x56D0; blob `f31e92f6746974db34b2061d86916cf54362ac4a`. Original reconstruction `r4dius/outrun2-decomp/src/platform/pc_render_queue.cpp:288-305` implements 4056D0 colour-override/undo + 405360; blob `95e5709c69e22b5bee653786c85b86024e6fc9d1`.
2. Original reconstruction `src/platform/pc_render_queue.cpp:216-246` makes `immediate_8999b0==0` enqueue-and-return; nonzero makes 405360 walk then 4052C0. `src/platform/pc_render_flush.cpp:970-980` flushes queued opaque nodes, restores colour overrides in reverse, clears queue and sets `immediate_8999b0=1`; blob `e6928a316ee4d503910cbe970b26f137e41c158e`. This is the ORIGINAL OPAQUE OBJECT QUEUE, not proof of D3DXSprite Begin/End.
3. Original `src/platform/race_course_passes.cpp:431-453` routes `draw_40c980/flare_40c9a0` to 4056D0; `:646-685` puts 570010/00F behind mode=0 and explicit 4052C0, then draws 570006; `:695-718` resets mode=0 for ring list, emits first 570008 at :708, flushes at :714, emits second 570008 with different arguments at :715, then defaults. Blob `22985e118c172467c566fe58d5b08f280c565ee2`. `src/platform/pc_render_queue.hpp:46-49,72-73` documents the mode transition.
4. Current `src/hooks_graphics.cpp::DrawObjectAlphaProjected:707-756` and `::DrawObjectAlphaCentre:779-836` scope `ProjectedScreenEffect2D` around 4056D0 and log sampled original calls. Blob `1a8b3acfcf24e2a088b6fb6b7065463abe9be737`. `src/vr/game/render_semantics.hpp::ScopedExactProducerSemantic:1451-1489` restores direct producer/scope when the wrapper returns. This is not a persistent opaque-queue-node tag.
5. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30ClassifyScreenSpacePass:2299-2305` selects projected-screen class only from effective semantic; `::R30BuildScreenSpaceEyeConstants:5092-5144` copies stock c64 to both eyes for non-LensFlareCentre, while exact token branch uses a head inverse. Its physical L/R/restore path and host one-projection-layer source are previously reviewed (01522/01528); a queued original draw whose source RAII ended can select a different route. Blob `81a87e2918a0d76cd17807ae2c70d2ee4ab43a16`.
6. Protected baseline `src/hooks_graphics.cpp@0cff83cf:625-695` already scoped CABE and a narrower C993 world owner around 4056D0, including `ScopedExactLensCentreGpuDraw` for the synchronous portion. The original queue boundary was not introduced by this run or proven newly regressed; baseline HMD optics are unknown.

## HYPOTHESIS_LEDGER / FALSIFICATION

| ID | Status after new queue-source evidence | Decisive falsifier / discriminator |
| --- | --- | --- |
| A extra original emitter | RULED_DOWN for simply seeing two 570008 calls: original intentionally calls same handle twice with different args; other extra source emissions OPEN | Full 40CBC0 source-call serial per Present compared to actual game EXE; show third unexpected call |
| B same-eye native/D3DX replay | OPEN; **4056D0 is not one GPU Draw** | Join each unique source invocation to opaque 405360 node(s), 4052C0 flush ID, native draw IDs, eye/RT. Two different 570008 invocations are NOT replay |
| C C993/CABE eye WVP split | NEW CONDITIONAL MECHANISM: deferred first call may outlive source semantic; stock/head-ray/other route divergence possible | For deferred 570010/00F and first 570008, prove physical native Draw retains exact projected scope and original c64/pose despite wrapper exit, or show no optical difference |
| D intended overlapping alpha | STRONGLY SUPPORTED ORIGINAL DESIGN, actual observed double OPEN | Compare ordinal1 intensity*flare vs ordinal2 intensity*glow, matrix/size, GPU texture and alpha blend at each eye; only one unintended same-source raster is B |
| E host double layer | STANDARD PATH RULED_DOWN by 01528; this queue finding does not revive E | Verify one projection layer/two views and fresh source on affected XR tick |
| F head-lock/pose mismatch | OPEN | Fresh-frame fixed-sun yaw/translation with exact source c64 writer, queue flush, native eye matrices, source/host pose and pixel hashes |

## EVIDENCE_GAPS

- The decomp is a source reconstruction with original-function address mapping, not a fresh disassembly or verified current executable runtime. Actual stage-specific immediate flag on entry to 0x570002, queue capacity/overflow, PMT node counts, native texture bindings, alpha blend, physical per-eye draws, deferred scope re-establishment, D3DX interaction, GPU RT contents, Quest3 head pose and R23 fresh/cached image remain UNTESTED.
- Do not equate original opaque 405360/4052C0 with SpriteNode/D3DXSprite queue or infer that `QueueRenderActive()` tracks this queue. Existing sampled CABE ordinal logs occur at source 4056D0, not necessarily physical Draw.
- No source-only proof that a deferred C993/CABE contribution currently renders with the wrong matrix; the exact visual root cause remains UNRESOLVED.

## PATCH_CANDIDATE_ONLY / REGRESSION

- PATCH_CANDIDATE_ONLY=TRANSACTIONAL_ORIGINAL_OPAQUE_NODE_PROVENANCE_IF_RUNTIME_PROVES_LOSS; APPLY=NO. First test read-only source invocation -> 405360 node/4052C0 flush -> native draw join. Only if a concrete failing physical draw loses its exact C993/CABE origin should a narrowly scoped, generation-fenced source-to-physical-node ownership transfer be designed. Do not widen generic alpha/world or alter original object count, texture, colour override, blend, matrix, queue timing, R26+HUD, host projection, or protected B9200 hooks.
- REGRESSION=HIGH: mislabeling first queued 570008 as duplicate and suppressing it deletes a legitimate ring; conflating original opaque queue with SpriteNode/D3DX causes false stereo promotion; preserving a direct token past 4052C0 without node/epoch fencing leaks into unrelated objects; forcing two-eye world depth on intentional distant sun can create IPD split/head jitter.
- NEXT_REVIEW=LENS_FLARE:ORIGINAL_4056D0_405360_4052C0_PER_OBJECT_QUEUE_NODE_TO_R30_PHYSICAL_SCOPE_C64_EYE_RT_JOIN.
- GITHUB_RECORD=docs/reviews/dx9ex/automation/LENSFLARE-QUEUE-IMMEDIATE-20261027-1654.md; COMMIT_MARKER=[AUTO:LENSFLARE-QUEUE-IMMEDIATE-20261027-1654]; CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED.
