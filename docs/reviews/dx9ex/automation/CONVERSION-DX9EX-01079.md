# CONVERSION-DX9EX-01079 — R26+HUD projected rank/rival D3DX fixed-function left/right source-fence review

- DATE: 2026-10-20 KST
- TASK_ID: CONVERSION-DX9EX-01079
- PRODUCTION_ID: CONVERSION-DX9EX-01079
- EVENT_ID: CONVERSION-DX9EX-01079-E001
- EVENT_TYPE: dispatch
- ATTEMPT: 1/3
- MODE: DX9EX_REVIEW_ONLY
- DX9EX_REVIEW_ONLY: ON
- CONTINUOUS_REVIEW: ON
- TARGET_BRANCH: vr-d3d9ex-focus
- SOURCE_HEAD: a0e3a6c12a6a5ad248ac60cbcba7e2cf599ceb52
- R26_HUD_BASELINE: 0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 (unchanged control)
- COMPARISON_ONLY: aab9e02bcb2ad2e6253840e6267e5c5ad5040854 (NOT Quest3 HMD PASS)
- REVIEW_SCOPE: Original vehicle-rank/rival Calc3D2D producer -> exact source/semantic -> queue root/tail and D3DX batch -> R26 R62 fixed-function indexed GPU draw -> left/right render-target/depth/viewport/projection restore -> R9 Present/direct transport -> host OpenXR xrEndFrame. Focus specifically on the R62 **post-left physical command-identity boundary**, not on 01078's F11 rotation or 01077's producer EVENT.
- NEW_FINDING: CONDITIONAL_R26_R62_PROJECTED_RANK_POST_LEFT_SOURCE_IDENTITY_NOT_RECHECKED
- CODE_CHANGE: NO
- PATCH_CANDIDATE_ONLY: YES; no source changes
- AUTOMATION_VALIDATION: STATIC_GITHUB_SOURCE_REA_ISSUE_REVIEW_COMPLETED; DOCS_ONLY_RESULT_SHA_AUDIT_REQUIRED
- RUNTIME_VALIDATION: UNTESTED

## 0. Continuation guard / prior records

Read GitHub latest branch HEAD and existing 01075/01076/01077/01078 review inventory. 01075 addresses exact +TIME/result shader admission; 01076 addresses host menu projection cache; 01077 addresses direct transport GPU producer EVENT; 01078 addresses external F11 ImGui eye-local cant/viewport. This 01079 task **does not recategorize any of those** as a new issue, and does not assert a new hardware failure. The preceding 01078 docs-only commit is a0e3a6c12a6a5ad248ac60cbcba7e2cf599ceb52.

Current `AGENTS.md` first 2026-10-20 override selects R26+HUD rather than legacy R84 default. This dispatch's explicit REVIEW_ONLY policy outranks older implementation-first text. No R84 auto-promotion, source patch, build, feature release or package creation is authorized.

## 1. EVIDENCE — original-to-final simulated call trace

| Stage | Source-backed evidence | Static conclusion / limit |
| --- | --- | --- |
| Original producer | `docs/automation/OUTRUN_REA_RENDERING_ARCHITECTURE_20261018.md:1-42,84-96`: game 0x00417B20 -> renderer 0x00449050; vehicle marker sub_4BAD20 -> Calc3D2D 0x00449940; fixed 6th/6 HUD is different producer 0x004B9D80; rival projected call-return 0xBB6F5 is separate. | Original CPU projected position is mono and cannot by itself prove stereo visual anchor. REA is checked-in disassembly-derived mapping, not a current runtime capture. |
| Capture + exact producer | `src/hooks_uiscaling.cpp:995-1015,1024-1119`: exact ordinal Calc edge 0xBAEE2 and rival 0xBB6F5 capture; `:1916-2066`: projectedAnchor snapshot for `RankMarkerSprani` and clipped-digit siblings; `:2167-2212`: rival anchor is consumed once for direct and queued children. | Preserves a producer-level anchor, distinguishes NaviPub `ScreenHud`/invalid projector from `ProjectedWorldMarker2D` and preserves rival independently. A producer anchor is not yet a final GPU Draw proof. |
| Queue + D3DX physical submission | `src/hooks_uiscaling.cpp:1180-1256` checks live root/tail before tagging siblings; `:3730-3880` snapshots a D3DX command across original `Draw`/possible implicit Flush; `:3923-3965` R64 selectively Flushes queued projected vehicle rank and fixed rank HUD, but not all rival/unknown/mixed batches; `:4072-4115` queue node/end boundaries. Original REA consumer 0x0042D710 and Begin/Draw/End 0x00429C60/0x0042A0A0/0x00429F60; type-1 and special native `DrawPrimitiveUP` also exist. | Logical producer entry != GPU Draw; D3DX may physically submit during Flush/End. R64 producer isolation is a useful upstream fence but is not a per-eye post-left invariant; no assumption that every rival uses the rank-only Flush branch. |
| Semantic + exact R62 admission | `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5000-5155` `R62TryFixedFunctionSpriteIndexed()`: game backbuffer, `D3DPT_TRIANGLELIST`, `CorroboratesProjectedWorldMarker`, live `GetVertexShader()==nullptr`, FVF 0x142, resources and pose sequence, viewport, `R30ConfigureXyzrhwWorldEffect()`. `:3085-3155` projected anchor -> R57 per-eye delta. The separate `src/vr/game/rank_marker_fixedfn_r62.hpp` excludes unproved world/F11/HUD cases. | This admits an exact candidate **only if** its physical API really is fixed-function indexed; it cannot prove that every rank or rival sprite runs this route. Native UP, XYZRHW, nonnull VS and unmatched renderer classes follow other owner/fallback paths. |
| Per-eye optical projection | `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5137-5175`: for projected rank `eyeProjection[eye] = originalProjection * clipShift` with captured `state.projectedDeltaX/Y[eye]`, `projectedBaseX/Y`, marker scale. This is *not* F11 finite-HUD eye orientation or source XYZ/RHW vertex rewriting. | Both eye projections are precomputed from one state. Their mathematical correctness still depends on the selected physical command staying attached to that same anchor/pose. |
| GPU draw, L/R, state restore | `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5207-5281`: `drawEye()` uploads projection then calls `DrawIndexedPrimitiveHook.stdcall`; `R30ExecuteXyzrhwStereo()` draws left, switches RT/depth, restores viewport, draws right, restores previous RT/depth/viewport; separately restores original projection. `:3784-3902`: poisons frame on left/right/restore HRESULT failure and tracks world stereo. | Two physical calls + state restore exist in source; failure handling exists. **The R62 caller and shared R30 executor shown do not compare post-left vs captured queueNode/queueEpoch/producer/drawSerial or shader epoch before right draw.** This is a narrow local code-reading observation, not proof that hooks can actually mutate those fields between eyes. |
| Full frame to HMD | `src/vr/d3d9/stereo_renderer_r7.inc:1452-1468` creates full-size R-eye target, `src/vr/d3d9/stereo_renderer.cpp:760-809` gates Present/published stereo vs mono, `vrhost/src/main_r23.cpp:3160-3265` checks candidate frame/pose, `:3560-3595` calls `xrEndFrame`; `vrhost/src/main.cpp:1924-1966` owns independent XR eye extent. | Static simulated chain ends at OpenXR submission code. No matching rank physical draw-ID -> Present frame-ID -> final XR layer/HMD screenshot evidence in this review. |

## 2. NEW_FINDING / confidence boundary

**Confirmed static distinction:** R26+HUD's `R62TryFixedFunctionSpriteIndexed()` creates left/right projected rank matrices once, and `R30ExecuteXyzrhwStereo()` invokes the provided left and right draw callbacks. No explicit `GameSemantic::CapturePhysicalDrawCommand()` / queue-epoch or anchor identity *after-left comparison* is visible at that callsite or in the shared executor before the right native indexed draw. In contrast, `src/vr/game/rank_marker_physical_source.hpp` defines `PhysicalRankSource`, `SameRankSourceAfterNativeLeft()` (producer, queue node/epoch, marker xyz, pose, draw serial, FVF, shader epoch) and raw-WVP checks for the separate R84-family physical transaction. **This comparison is about different source contracts; it does not prove that the R84 helper is executed on every runtime route.**

**Conditional risk only:** If an original/native indexed submission or state-changing reentrant callback changes the relevant projected SpriteNode/producer/queue or shader ownership between physical left and right, the precomputed R26 rank matrices may belong to an earlier marker while the actual native draw uses newly bound data. Symptoms could be a detached car marker in one eye, a rival ordinal appearing against the wrong car, or misleading two-eye success counters. None was reproduced here. In normal nonreentrant draw/immutable command conditions there may be **no actual bug**. D3DX batch fences, `InternalPassScope` and tracked device state may already make that scenario impossible; no call trace disproves these defenses.

This is intentionally not a finding of incorrect 32-pixel rank-lift, fraction restore, bad `Calc3D2D` math, general eye-cant, duplicate draw, missing scissor, or an observed Quest3 fail. These areas are distinct or previously studied.

**Falsification / counterevidence:**
1. Observe an R62 projected kind-0 physical DIP and capture before-left/after-left queueNode, queueEpoch, producer, projected anchor, poseSequence, draw serial, FVF, shader identity/epoch, actual original index/VB/IB/texture, RT and HRESULT. If values are invariant through native-left and right-state operations on every test incl. texture batch boundary, this suspected seam is unsupported.
2. Prove the actual target renderer and original indexed Draw have no callback/reentrancy path capable of mutating GPU source state, or prove R64/semantic guards enforce the same physical snapshot end-to-end.
3. If R62 never admits rank/rival in the matching R26+HUD binary (actual GPU API is UP/XYZRHW/shader instead), this candidate does not apply; inspect the actually selected owner, not a hypothetical R62 defect.
4. Check markers on multiple vehicles, ordinal 1–3 and 4–6, rival case, FOV asymmetry/nonzero cant, narrow/ultrawide viewport, queue reuse, Reset/recenter, two consecutive races; no right-eye drift or repro under identity stress defeats a claim of current visual breakage.
5. A Quest3 symptom without same binary + physical draw/Present/XR correlation is insufficient; desktop mirror or successful two-DIP count alone is insufficient.

## 3. PATCH_CANDIDATE_ONLY — **no implementation**

**Candidate A, P2 conditional source-coherence fence (requires actual repro):**
- `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp`, `R62TryFixedFunctionSpriteIndexed()` **lines 5000–5285**, especially projected `R30ConfigureXyzrhwWorldEffect` setup **5110–5170**, eye callbacks **5207–5253** and invocation of `R30ExecuteXyzrhwStereo()` **5240–5270**; shared `R30ExecuteXyzrhwStereo()` **3784–3902**.
- Consider a projected-rank-*only* immutable physical-command fence, sampled BEFORE left and rechecked AFTER native left prior to right draw, including queue/marker/pose and physical vertex/index/texture/shader ownership when observed relevant. Preserve existing right/restore behavior and signal incomplete stereo rather than running an unproved right eye. No unconditional global per-draw checks.
- Compare `src/vr/game/rank_marker_physical_source.hpp` `ValidRankSource()/SameRankSourceAfterNativeLeft()` and `src/vr/game/rank_marker_fixedfn_r62.hpp` exact FVF gate as **review references**, not instructions to replace the R26 default or merge R84.
- **Prerequisite evidence:** same exact physical R62 hit + mutable owner/anchor across native left, with a correlated eye defect. No code patch until that condition is met.

**Candidate B, producer/queue provenance only (no patch):**
- `src/hooks_uiscaling.cpp` `Calc3D2D_dest` / `RankMarker_sprani` / `RankMarker_putClipSprite` / `RivalMarker_sprani` **995–1015, 1916–2066, 2167–2212**; `TagAppendedNodes()` **1180–1256**; R64 D3DX `DrawDest/Flush` **3730–3995**, queue callbacks **4072–4115**.
- Distinguish direct Draw from deferred queued D3DX Flush/End and do not consume a later producer's anchor or merge fixed 6th/6 HUD with car rank. Only opt-in trace correlation is justified; never restore the unsafe 0x2D734 queue-entry hook or B9200 post-CALL/+5.

**Candidate C, bounded transport proof only (no patch):**
- `src/vr/d3d9/stereo_renderer.cpp` `PresentDestR9` **760–809**; `vrhost/src/main_r23.cpp` **3160–3265,3560–3595**; `vrhost/src/main.cpp` **1924–1966**.
- Collect per-eye source fingerprint, right draw/restore, final published frame, matched host pose and actual final layer, without treating frame-level stereo completion as proof of every marker's optics.

## 4. REGRESSION_RISK

- HIGH: An eager global native-Draw source check/flush can alter D3DX batch timing, unrelated HUD/sprite animation, result +TIME and GOAL glyph continuity, rival legacy accepted behavior or increase GPU driver calls.
- HIGH: Wrong owner invalidation after LEFT already wrote main framebuffer/depth could produce a third mono draw or broken right eye. Keep fail-closed incomplete-frame and precise rollback; never call an unbounded eye replay.
- HIGH: Rank 1–3 animated sprani, 4–6 clipped-digit sibling set, rival single-use 0xBB6F5 anchor and 6th/6 static HUD are *different* producers. Preserve subpixel fraction, 32px lift policy and queued child-group identity. Do not alter original producer CALL, timing or input/FFB.
- HIGH: Preserve R26+HUD baseline 0cff83cf..., SkyGlow/lens, F11/ESC/menu, B9200 +5 hook exclusion, stereo pose epoch, game/device Reset, original fallback and DX11/DXVK isolation. Do not promote R84/candidate aab9e02... automatically.
- MEDIUM: Adding per-DIP heavy Get* / GPU sync without a real repro can lower p95/p99 framerate. No FPS claim from static audit; guard opt-in telemetry.

## 5. AUTOMATION_VALIDATION, EVIDENCE and NEXT_REVIEW

- GitHub source was read at exact `SOURCE_HEAD`, together with prior 01078 and 01075–01077 review inventory, current topmost AGENTS policy, disassembly-derived REA mapping and GitHub Issue #119 (parent tracker / historical user UI feedback, not a matching R26 physical-HMD pass). Physical GPU tracing was **not** executed, and no original binary was run or modified.
- Static branch-path analysis: producer -> queue -> D3DX indexed/native alternative -> R26 R62 projected -> two eye state passes -> restore -> R9 Present/direct transport -> host xrEndFrame, with uncertain branches marked above.
- DOCS_ONLY_COMMIT_GATE: after creating this file, audit resulting commit diff for **exactly** `docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01079.md`, and ensure message includes `[AUTO:CONVERSION-DX9EX-01079]`. No source build/CI gate is required or claimed, no CI-skip directive.
- CODE_CHANGE=NO. No C++/HLSL/source/CMake/workflow/config edit, no merge, update_ref, branch, release or package.
- RUNTIME_VALIDATION=UNTESTED. No Quest3/VDXR session, physical L/R GPU capture or FPS measurement matching this review's source HEAD.
- NEW_FINDING is a **conditional, source-level verification gap**, not an established end-user defect. Automatic implementation prohibited.
- NEXT_REVIEW: Choose a different boundary than R62 rank and 01078 F11: `StateBlock/Reset/device-loss` lifetime of original projection/viewport/right RT across `D3DXSprite::OnLostDevice/OnResetDevice` and original game Present, or a measured dense-scene CPU/GPU frame pacing gate. Do not repeat the same conditional queue-epoch claim without new physical evidence.
- GITHUB_RECORD: `docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01079.md`; durable docs-only `[AUTO:CONVERSION-DX9EX-01079]` commit.
