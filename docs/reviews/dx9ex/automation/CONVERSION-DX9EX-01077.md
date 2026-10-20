# CONVERSION-DX9EX-01077 — R26+HUD DirectGPU producer-fence publication boundary (REVIEW_ONLY)

- DATE: 2026-10-20 KST
- TASK_ID: CONVERSION-DX9EX-01077
- PRODUCTION_ID: CONVERSION-DX9EX-01077
- EVENT_ID: CONVERSION-DX9EX-01077-E001
- EVENT_TYPE: dispatch
- ATTEMPT: 1/3
- TARGET_BRANCH: vr-d3d9ex-focus
- SOURCE_HEAD: 3b0204bc3b694231576cead79ed9fcd238a610ca (GitHub HEAD re-read before docs-only write; earlier this review began at 1b0e20319644aa74fc5cf79f70c4231e51d17238)
- BASELINE: R26+HUD 0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 (preserve)
- COMPARISON_ONLY: aab9e02bcb2ad2e6253840e6267e5c5ad5040854 (NOT HMD PASS)
- MODE: DX9EX_REVIEW_ONLY
- DX9EX_REVIEW_ONLY: ON
- CODE_CHANGE: NO
- REVIEW_SCOPE: Distinct from 01075 shader admission and 01076 host menu projection: original result/+TIME/render queue → final R30/R62 physical D3D9 draws → left/right surfaces + restore → R9/R13 DirectGPU producer EVENT → game Present → host D3D11 copy/ACK → xrEndFrame. Focus on fence-completion authority and unnecessary hybrid SBS copy.
- NEW_FINDING: R9_DIRECTGPU_PRE_FENCE_STEREO_PUBLICATION_GAP (SOURCE-CONFIRMED CONTROL-FLOW ASYMMETRY; RUNTIME MANIFESTATION UNPROVEN)
- PATCH_CANDIDATE_ONLY: YES (nothing applied)
- AUTOMATION_VALIDATION: STATIC_GITHUB_SOURCE_REA_REVIEW; DOCS_ONLY_COMMIT_PATH_PENDING_RESULT_INSPECTION
- RUNTIME_VALIDATION: UNTESTED

## Prior work / separation

Checked `docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01075.md` (cached shader VS admission) and `.../CONVERSION-DX9EX-01076.md` (menu 4:3 projection cache). Neither analyzed R9's producer EVENT completion versus R7 and host sampling. The active HEAD 3b0204bc changed only bounded R26 result-HUD shader gate telemetry and its Python contract relative to 1b0e2031; this review **does not** infer a runtime fix or replay that shader finding. Source changes on other concurrent tasks are not work authorized by this review. No change was made to B9200/mode-2 or game source.

## EVIDENCE: original → GPU → transport → OpenXR, as static call-path simulation

1. **Original/REA:** `docs/automation/OUTRUN_REA_RENDERING_ARCHITECTURE_20261018.md:1-42` maps original Win32 game loop VA `0x00417B20` → render orchestrator `0x00449050` → queue consumer `0x0042D710`. Original +TIME VA `0x00498670`, ranked markers and queue types 0/1 feed D3DX `Begin/Draw/End` (End/Flush may be the real GPU submission), or native `DrawPrimitiveUP`. This is a **static REA map**, not exact proof of the API chosen for every +TIME glyph. Do not conflate source producer callbacks and physical GPU Draw.
2. **Semantic and physical dispatch:** `src/hooks_uiscaling.cpp:3340-3429,3720-3845` preserves deferred, homogeneous D3DX-batch ownership where proven. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5310-5407` consumes a physical DIP semantic, excludes F11 external ImGui, tries R62 FVF142 indexed sprite, XYZRHW, then conservative R29 original fallback. The latest `RESULT_HUD_REJECT` expressly says `stage=R62_ONLY finalRoute=UNDETERMINED`. Other DP/UP entries are separate; this report does not promote any unspecified result draw.
3. **Left/right and restore:** `stereo_renderer_r30_r26_safe.cpp:3787-3899,5220-5252` shows left draw and right RT/depth/viewport draw, right restoration, failure poisoning and original projection restore. An eligible `FrameHadWorldStereo` plus both-eye metadata is **not** proof of a completed transport fence. `R30PresentDestR30():1486-1504` performs optional SkyGlow work then delegates through the R27/R23 overlays, not a separate host-facing transport.
4. **Compiled owner graph:** `CMakeLists.txt:96-110,225-241` selects `stereo_renderer_r30_r26_safe.cpp` as the R26+HUD compiled stereo TU; it includes `stereo_renderer_r26.cpp:1-17` → R23/R22/R21/R20/R13 → `stereo_renderer.cpp`. `stereo_renderer_r13.cpp:795-803` detours R9 Present and ResolveDirectTransport, while `PresentDestR13():721-745` delegates to R9. `stereo_renderer.cpp:R9InstallCallbackPolicy():836-906` installs `PresentDestR9` over the base Present callback. Thus R7's separate `PresentDest` post-Present completion path is **not interchangeable** with R9's active callback. Actual installed DLL CMake cache/SHA and successful hook registration remain runtime-UNTESTED.
5. **EVENT is queued, not completed:** `src/vr/d3d9/stereo_renderer_r7.inc:1358-1431` `ResolveDirectTransport` chooses a ring slot, issues left+right `StretchDirectEye`, calls `slot.fence->Issue(D3DISSUE_END)`, sets `producerPending=true`, `published=false` and returns true. R13's replacement `ResolveDirectTransportR13():222-375` preserves the same pending/unpublished write after ACK-safe slot choice and EVENT issue. A successful `Issue` is **not** a `GetData()==S_OK` completion.
6. **R7 proof exists:** `stereo_renderer_r7.inc:1433-1453` `DirectTransportFrameReadyAfterPresent(frameId)` runs bounded `WaitForEventQuery(...,1,0)` after Present; only then clears `producerPending` and sets `published=true`. On timeout it preserves quarantine. R7 `PresentDest():1694-1724` explicitly gates `StereoSbsActive` publication on **Present success AND this EVENT proof**, otherwise suppresses direct frame promotion.
7. **NEW R9 asymmetry:** `stereo_renderer.cpp:696-718` treats `ResolveDirectTransport()==true` as `directTransport=true; composedStereo=true` before Present. `:778-797` publishes an in-flight metadata entry with DirectGPU handle, calls real Present and normalizes its HRESULT, then advertises `StereoSbsActive` and completed L/R pose metadata on `SUCCEEDED(hr)` and `!FrameStereoIncomplete`, **without** `DirectTransportFrameReadyAfterPresent` or an equivalent producer EVENT `GetData` on this R9 path. Therefore the static code can label a shared-eye frame complete while its slot still has `producerPending=true, published=false`. D3D9 Present success alone does not establish completion of an independent GPU query.
8. **Host consumer/ACK:** `vrhost/src/main_r23.cpp:3010-3130` selects the latest DirectGPU ring metadata and rejects in-flight, incomplete, wrong-state and already-consumed frames. `:3120-3260` treats a valid DirectGPU candidate as input to `R23CommitDirectAfterValidation`, and `:3236-3290` correctly defers *consumer-side* ACK until projection GPU completion. `:3290-3360` refreshes the XR projection only on new source, then `:3350-3590` can reuse cached projection and eventually submit `xrEndFrame`. Consumer ACK ordering **does not itself prove that the producer's D3D9 EVENT finished before the host started sampling**. A driver/runtime might serialize interop implicitly; this was not proven or disproven in Quest 3/VDXR.
9. **Performance adjacent condition, not a separate confirmed defect:** `stereo_renderer.cpp:707-724` may perform direct copies **and** `ComposeSbs` when `HostDirectTransportReady()==false && !directOnly`. `stereo_renderer_r7.inc:1499-1520` shows SBS uses two `StretchRect` resolves, `CreateStateBlock(D3DSBT_ALL)`, quad draws and restoration. This is an intentional compatibility fallback; quantify how often readiness remains false before calling it wasted work. Do not disable this safety path speculatively.

## NEW_FINDING — exact confirmed invariant mismatch versus unproven symptom

**Source-confirmed:** R7 has a post-Present fence-completion gate; R9's installed callback publishes a success direct frame without calling that gate after successful Present. R13 hardens slot ACK/recycling and partial-copy error quarantine, but its inspected `ResolveDirectTransportR13` still returns after `Issue`, not after completed `GetData`. This is a distinct *producer readiness/publication contract* boundary, independent of result HUD shader pose, D3DX queue epoch and host 4:3 menu cache.

**Conditional visual/performance hypothesis:** If the producer EVENT remains `S_FALSE` after successful D3D9 Present when R9 advertises an active direct frame, the x64 host may receive a premature DirectGPU candidate. Observable consequences could include wait/hitch/stale or incorrect eye copy, depending on driver interop synchronization. This is **not** an observed corruption or established root cause of +TIME/result diplopia. Many ordinary frames may have the event completed already by the time the consumer runs.

**Contrary/falsification conditions:** Demonstrate that an installed R26+HUD build does not activate R9/R13; OR that a different invoked completion guard occurs before every active direct publication; OR that paired per-frame EVENT query is always `S_OK` at R9 metadata publication across transition/hitch/load. In those cases classify as `NOT_OBSERVED` or `NOT_REACHABLE`, and do not propose an implementation. A functioning D3D11 sample or successful xrEndFrame is not by itself proof that the explicit producer fence policy was followed.

## PATCH_CANDIDATE_ONLY (no code edit)

- **Candidate A, HIGH priority, conditional:** `src/vr/d3d9/stereo_renderer.cpp`, `PresentDestR9()` **lines 696-804**, especially the `ResolveDirectTransport` branch **705-724**, pre-Present `PublishRenderFrame` **778-786**, and final `StereoSbsActive` publication **790-798**. Before any modification, measure the R9 path's current slot `pendingFrameId/producerPending/published` and EVENT completion at publication, then review bringing the R7 **post-Present bounded completed-fence gate** into the *R9* decision. Never mark `published=true` at `Issue`; never expose a fresh direct frame before completion.
- **Candidate B, producer-proof review:** `src/vr/d3d9/stereo_renderer_r7.inc`, `ResolveDirectTransport():1358-1431`, `DirectTransportFrameReadyAfterPresent():1433-1453`, `PublishRenderFrame():1491-1495`; and `src/vr/d3d9/stereo_renderer_r13.cpp`, `ResolveDirectTransportR13():222-375`. Preserve GPU ACK and producer EVENT **as two separate proofs** before ring reuse. A failed/timeout query must remain quarantined; no extra FLUSH/poll spin or multi-ms blocking to hide the race.
- **Candidate C, conditional performance telemetry:** `src/vr/d3d9/stereo_renderer.cpp:705-724` and `stereo_renderer_r7.inc:1499-1520`. Record directReady, directResolve, SBSComposeAttempt, SBSComposeMs, ring backpressure and Present wall time per frame. Consider avoiding duplicate SBS only after matching host readiness+optical correctness; never disable classic fallback for R26-safe modes by inference.

## REGRESSION_RISK / mandatory acceptance boundaries

- **CRITICAL transport correctness:** DirectGPU-only transient miss must retain the last completed stereo projection; failed EVENT must not promote direct frame, reassign a non-ACKed shared slot or generate a false `StereoSbsActive`. Do not change shared memory schema, ring generation, or ACK ordering just to satisfy an observation.
- **HIGH performance:** R7's bounded 1-ms post-Present grace exists to prevent 4-ms producer stalls. Any future repair needs frame pacing under 72/90/120 Hz, no unbounded query loop, and source-cadence-to-xrWaitFrame correlation.
- **HIGH visual:** Protect D3DX deferred +TIME and GOAL batches, exact mode-2 exclusions, all 19 B9200 post-CALL/+5 hooks disabled, nonzero eye cant, R62 FVF142 fixed-function, rank/rival, lens/SkyGlow, F11/ESC, mono mirror and normal game/input/FFB.
- **Baseline:** `0cff83cf...` R26+HUD remains unchanged; `aab9e02...` is comparison evidence only. Do not promote R84.
- **Negative fixtures requested for human-run follow-up, NOT executed here:** frame with EVENT returning S_FALSE at post-Present, failure HRESULT, host delayed ACK, four-slot backpressure, DirectGPU-only bootstrap, direct+classic hybrid, Reset/device-loss, two races, high-density sand/particle load. For each, correlate `gamePID, build SHA, frameId, poseSeq, transport slot/generation, query HRESULT, published/producerPending, D3D9 Present hr, host candidate, D3D11 commit/ACK, projectionRefresh, xrEndFrame layer`. Assert no incomplete producer packet marked active and no duplicate original mono D3DX draw. Quest3/VDXR requires actual paired observation.

## AUTOMATION_VALIDATION, RUNTIME_VALIDATION, NEXT_REVIEW

- AUTOMATION_VALIDATION: GitHub pinned-source/REA/static control-flow inspection, predecessor comparison and source graph check; **no build/CI gate required for docs-only**. Inspect resulting commit changed file list to verify this exact Markdown is the only addition; commit SHA itself is not runtime evidence.
- RUNTIME_VALIDATION: UNTESTED. No game, physical Quest3/VDXR, Windows D3D9Ex, actual xrEndFrame or injected EVENT test run in this task.
- NEW_FINDING relation: NEW versus 01075/01076; the same direct-ring hypothesis should not be copied as a new finding in the next task.
- NEXT_REVIEW: Independently inspect R13 producer fence/host direct-interop implicit synchronization and actual slot-ACK fence chain (including R32 deferred event), then choose a distinct path such as viewport→XR eye extent or frame pacing under particle bursts. Use an actual producer/consumer frame trace before promoting this candidate. If evidence is unchanged mark `NEW_FINDING=NONE` rather than repeating.
- GITHUB_RECORD: `docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01077.md` on `vr-d3d9ex-focus`, commit message `[AUTO:CONVERSION-DX9EX-01077]`.
- CODE_CHANGE: NO
- RUNTIME_VALIDATION: UNTESTED
