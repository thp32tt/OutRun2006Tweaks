# CONVERSION-DX9EX-01081 — R26+HUD Reset / D3DX batch lifecycle boundary (REVIEW_ONLY)

- DATE: 2026-10-20 KST
- TASK_ID: CONVERSION-DX9EX-01081
- PRODUCTION_ID: CONVERSION-DX9EX-01081
- EVENT_ID: CONVERSION-DX9EX-01081-E001
- EVENT_TYPE: dispatch
- ATTEMPT: 1/3
- LANE: DX9EX
- TARGET_BRANCH: vr-d3d9ex-focus
- SOURCE_HEAD: 7fd9f30732d10ac294c9c791773f2f363693ca1b (immutable GitHub source for this review; branch will advance by docs-only result)
- R26_HUD_BASELINE: 0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 (protected; not moved)
- COMPARISON_ONLY: aab9e02bcb2ad2e6253840e6267e5c5ad5040854 (not Quest3 HMD PASS; not promoted)
- MODE: DX9EX_REVIEW_ONLY
- CONTINUOUS_REVIEW: ON
- DX9EX_REVIEW_ONLY: ON
- CODE_CHANGE: NO
- REVIEW_SCOPE: Original producer/semantic -> queued or direct D3DXSprite batch -> R64 native OnLostDevice/OnResetDevice and Flush/End ownership -> R26/R30 Reset/StateBlock/right-eye resource teardown -> R9/R7 Reset success/failure -> next full-clear/draw -> Present/DirectGPU or SBS -> host OpenXR. Different boundary from 01079 rank post-left identity and 01080 SkyGlow partial-eye Present.
- NEW_FINDING: CONDITIONAL_R64_D3DX_LEDGER_INVALIDATION_NOT_ATOMIC_WITH_DEVICE_RESET (a source-confirmed separate callback boundary; actual broken frame UNPROVEN)
- PATCH_CANDIDATE_ONLY: YES — diagnostic proposal, NOT an applied code patch
- AUTOMATION_VALIDATION: STATIC_GITHUB_SOURCE_REA_POLICY_ISSUE_PREVIOUS_REVIEW_COMPLETE; DOCS_ONLY_EXACT_COMMIT_AUDIT_PENDING
- RUNTIME_VALIDATION: UNTESTED

## 1. Scope separation, observed baseline and prior records

Read current GitHub branch head, AGENTS.md topmost 2026-10-20 R26+HUD override, docs/DX9EX_OPTICAL_ROUTE_PROBE_POLICY_20261020.md, original REA-rendering map, 01077–01080 review records, relevant source and GitHub issues #130/#131. The topmost AGENTS override and current dispatch control over older R84 and source-first paragraphs. CMakeLists.txt:95-110 selects R26+HUD by default; actual installed CMake cache, binary/package SHA and Quest3 session were not available.

Prior 01077 covers R9 DirectGPU producer EVENT publication, 01078 F11 eye-local cant, 01079 R62 projected rank source identity between eyes, and 01080 R30 SkyGlow partial-eye composite return at Present. **None of those is reclassified as a new finding here.** This review inspects D3DX batch lifetime across device Reset, not SkyGlow's separate failed-postprocess return. Historical #130/#131 discuss lifecycle/StateBlock/resource checks but are broad static screenings, not evidence of a matching R26+HUD runtime Reset failure. No B9200 post-CALL/+5, unsafe 0x2D734 midhook, R84 default promotion or external release was attempted.

## 2. EVIDENCE — static producer-to-HMD path and the Reset event seam

| Boundary | Directly inspected GitHub source/REA | Established fact and limitation |
| --- | --- | --- |
| Original producer | docs/automation/OUTRUN_REA_RENDERING_ARCHITECTURE_20261018.md:1-42,84-103; original game loop 0x00417B20 -> scheduler 0x00449050 -> queue consumer 0x0042D710. +TIME original 0x00498670 and GOAL/rank have different producer provenance. D3DX Begin 0x00429C60, Draw 0x0042A0A0, End 0x00429F60; queue type-1/native DrawPrimitiveUP are alternative owners. | Original producer callback is NOT necessarily physical GPU submission. Original REA summary is static disassembly-derived evidence, not an executed GPU trace. |
| Semantic & deferred queue | src/hooks_uiscaling.cpp:3650-3735,3737-3956,4072-4115; src/vr/game/render_semantics.hpp; R64 HudBatch is thread_local at hooks_uiscaling.cpp:3266-3291. ScopedExactProducerSemantic and queue epoch/owner checks isolate proven +TIME/GOAL, rank and native D3DX Flush/End. | A tracked D3DX Draw can stay deferred until Flush/End; an unsubmitted batch must not be carried across an unobserved device generation as if physically submitted. A source token alone is not proof of a draw. |
| D3DX native lifecycle | src/hooks_uiscaling.cpp:3321-3457,3958-4005. R64 BeginDest publishes/invalidate batch on applicable native Begin outcome. LostDeviceDest and ResetDeviceDest compute OwnsLifecycle(self, tracked/live sprite), call the **original** ID3DXSprite slot 12/13 first, then call HudBatch.invalidate() only when that lifecycle object is matched. Hooks install transactionally with Begin/Draw/Flush/End and both lifecycle slots. FlushTracked checks live sprite pointer and rejects replaced sprites. | **Confirmed distinct callback ordering:** the R64 ledger is not invalidated by the D3D9 device Reset callback itself in the inspected R64 class; it is invalidated at the matched D3DXSprite OnLost/OnReset callback, **after** the original method returns. Pointer-mismatch and Begin safeguards already reduce risk. No evidence that original lifecycle methods actually reenter D3DX Draw/Flush or are skipped. |
| R26/R30 per-eye and postprocess | src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:918-933,968-1009,1252-1290,1379-1424. SkyGlow uses default-pool eye textures, D3DSBT_ALL, saves/restores RT/depth/viewport; src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:1505-1515 releases SkyGlow textures and invalidates capture epochs **before** delegating the lower ResetDestR22. R30 Reset hook is installed at :5522-5542. | **Confirmed independent lifetime:** R30 SkyGlow teardown is coupled to a D3D9 Reset callback, not to R64's D3DXSprite lifecycle event. As for 01080, L/R postprocess completeness is separately gated in normal Present; this task makes no new optical failure claim. |
| Base stereo Reset & recovery | src/vr/d3d9/stereo_renderer_r7.inc:1744 and :1456-1462. Game Reset invalidates tracked states, calls NotifyGameReset, releases R/L stereo/transport resources, resets PresentEpoch, publishes StereoDisabled metadata, then calls original Reset or D3D9Ex ResetCompatDevice. Only after SUCCEEDED(hr) does it prime tracked state and EnsureStereoResources. src/vr/d3d9/stereo_renderer.cpp:825-840 R9 resets mono resource/depth identities and full-clear seeds, reacquiring main depth only on successful Reset. | Failed Reset leaves stereo publication disabled and full-clear seeding required again; resource recreation after success is not proof that old D3DX batch generation was invalidated. The source does not establish the game's external OnLost/OnReset call order. |
| Physical draw to L/R and Present | src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5295-5470 (R30 DP/DIP/UP/XYZRHW and R62 guards); src/vr/d3d9/stereo_renderer_r7.inc:1456-1478 (right RT/depth and restore); src/vr/d3d9/stereo_renderer.cpp:685-725,760-822 (R9 frame eligibility, stereo/mono publication). Native game D3DX Flush/End may submit through DP/DIP/UP; R30/R9 then choose safe owner/fallback. | Static path cannot prove which API a post-Reset glyph uses or that any stale owner actually survives to its physical draw. R9's transport fence issue from 01077 remains independent. |
| Host OpenXR | vrhost/src/main_r23.cpp:3160-3265 validates candidate frame/pose and chooses DirectGPU or classic SBS copy; :3568-3595 calls xrEndFrame; vrhost/src/main.cpp:1924-1966 owns independent XR eye extent. | The call chain can reach OpenXR on a later valid frame, but no matching D3DX lifecycle callback -> physical L/R draw -> actual xrEndFrame/HMD image was observed. |

### NEW_FINDING — narrow code-level boundary, not runtime defect

**Source-confirmed:** Two separately hooked APIs own teardown on different events. R30 and R9/R7 clear their resources/frame eligibility when the game D3D9 device Reset hook is called. R64 clears deferred D3DX batch provenance only on a matched ID3DXSprite OnLostDevice/OnResetDevice hook, or via its own Begin/pointer guards. R64's original native lifecycle call precedes invalidation. This is a **cross-callback ordering/provenance verification gap**, not evidence of a failed HMD picture. There is no general conclusion here that a normal Windows D3D9 Reset skips OnLostDevice.

**Conditional optical risk, UNOBSERVED:** A device Reset between a deferred HUD Draw and expected D3DX lifetime invalidation, followed by a skipped/late matched sprite callback or relevant reentrancy, could briefly retain the old HudBatch producer/queue generation. If the same live sprite/ledger is then physically flushed, +TIME/GOAL/ESC or an exact result glyph could be tagged as the wrong producer for a new eye frame; if the sprite pointer changed, R64's existing CanFlush and ownership checks should reject reuse. Another conditional outcome is temporary native no-stereo fallback, not necessarily a visible corrupt frame. No device-loss, D3DX callback omission, pointer reuse or visual symptom was reproduced.

**Disproof requirements:**
1. Verify the actual game's ID3DXSprite OnLostDevice and OnResetDevice order for every Reset/ResetEx attempt, including FAILED Reset and recreate; capture self pointer, global sprite 0x55B218, HudBatch.active/generation/drawCount/queue epoch before original callback, after callback and before first new Begin/Flush.
2. Trace native original lifecycle method reentrancy. If no D3DX Draw/Flush can occur during it, post-callback ledger clearing is sufficient for normal ordering; do not call this a live defect.
3. If every game Reset is preceded by a matched OnLost or every first resumed Draw is guarded by a new Begin/invalidate, with no physical old-epoch Flush, the proposed stale batch pathway is falsified for that scenario.
4. Collect exact parent producer/token, queue ID/epoch, actual final GPU API, game device generation, each left/right RT/depth/viewport/restore HRESULT, PresentEpoch/transport frame ID and host xrEndFrame ID. Compare default R26+HUD and explicit R84_TEST only with same source/settings; no static claim of HMD PASS.
5. For a failed Reset, verify StereoDisabled publication, no old DefaultPool texture access, fresh full-main-clear seed before stereo, and no unsafe replay of deferred sprites. Do not simulate a device-loss PASS from merely calling Reset or checking build status.

## 3. PATCH_CANDIDATE_ONLY (NO implementation)

- **Candidate A / conditional source coherence check:** src/hooks_uiscaling.cpp, R64 class **3266-3457**, especially HudBatch ledger **3281-3288**, BeginDest **3323-3345**, FlushDest/EndDest **3348-3424**, InvalidateForDeviceLifecycle/LostDeviceDest/ResetDeviceDest **3427-3457**, FlushTracked **3459-3477**. If and ONLY if observed Reset ordering skips/late-runs lifecycle callbacks with a stale physical submission, consider a tightly bounded device-generation invalidation contract before any next deferred Flush. It must preserve true native End/Flush, correct sprite pointer lifetime, reentrant generation and the original D3DX HRESULT; no global unconditional Flush, no speculative extra GPU draw.
- **Candidate B / Reset fence review:** src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::ResetDestR30() **1505-1515**, R30ReleaseSkyGlowResources() **918-933**, R30ApplyStereoSkyGlow() restore **1252-1424**; src/vr/d3d9/stereo_renderer_r7.inc::ResetDest() **1744**; src/vr/d3d9/stereo_renderer.cpp::ResetDestR9() **825-840**. Compare event ordering and HRESULT across failed/successful Reset/ResetEx. Do not alter protected StereoDisabled/seed discipline, resource teardown, StateBlock restore, or SkyGlow failure behavior without an exact failure trace.
- **Candidate C / attribution only:** original REA producer/queue and src/vr/game/render_semantics.hpp; src/hooks_uiscaling.cpp **3650-3735,3737-3956,4072-4115**; source final L/R route, frame transport and host XR as table above. Use opt-in bounded telemetry only after separate authorization, preserving original game producer and 0x2D734/B9200+5 exclusions.
- All are **PATCH_CANDIDATE_ONLY**: no game source, C++, HLSL, CMake, workflow, runtime config, verification code, branch, ref, release or package changed.

## 4. REGRESSION_RISK / NEXT_REVIEW

- HIGH correctness: Wrongly clearing a legitimate in-flight D3DX batch at Reset boundary might drop all +TIME/GOAL/ESC sprites; eagerly flushing might submit stale freed D3D9 texture surfaces or misclassify a deferred native draw. Preserve old-session native semantics and exact queue/producer identity.
- HIGH device safety: Preserve D3D9Ex ResetCompatDevice, incomplete-frame mono fallback, resource/StateBlock/RT/depth/viewport restoration, R9 full-clear seed and DirectGPU slot quarantine. Avoid stale COM pointer use, double-release and mutable image publication after failed Reset.
- HIGH optical: Keep immutable R26+HUD baseline 0cff83cf..., GOAL, fixed 6th/6, rank/rival, +TIME sprite/numbers, F11, ESC, central lens/outer halos/SkyGlow and original native input/FFB. Never automatically promote R84 or recent aab9e02 candidate.
- PERFORMANCE: A future proposed invalidation/fence must not introduce global D3DX Flush, blocking GPU waits, per-draw allocation or added texture/video copies without matched p95/p99 and Quest3 evidence.
- NEXT_REVIEW: Choose a DIFFERENT scope: dense sand/particle overdraw and draw/copy/wait/resource-churn budget in R26 world stereo versus direct transport at 72Hz, with semantic scene-particle versus transparent windshield/water distinction and bounded no-HMD static assumptions. Do not refile 01077 DirectGPU EVENT, 01079 rank identity, 01080 SkyGlow partial-eye or this D3DX lifecycle ordering without new runtime evidence.

## 5. GITHUB_RECORD / validation contract

- GITHUB_RECORD: docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01081.md on vr-d3d9ex-focus; single new docs-only result commit, message includes exactly [AUTO:CONVERSION-DX9EX-01081].
- SOURCE_HEAD: 7fd9f30732d10ac294c9c791773f2f363693ca1b (pinned inspected input, not falsely represented as the output SHA).
- AUTOMATION_VALIDATION: GitHub-only source/REA/policy/prior-review/issue static path inspection. Verify this result commit changes this Markdown path alone using its exact GitHub diff. No source build gate for REVIEW_ONLY; no CI-skip marker, CI pass or physical device test claimed.
- CODE_CHANGE=NO.
- RUNTIME_VALIDATION=UNTESTED (no original EXE, D3D9 GPU/HRESULT trace, source-matched installed DLL or Quest 3/VDXR HMD acceptance).
