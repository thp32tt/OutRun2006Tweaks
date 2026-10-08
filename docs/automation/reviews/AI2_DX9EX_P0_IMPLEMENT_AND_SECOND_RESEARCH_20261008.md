# DX9Ex P0 screen-wide repair + second deep research (2026-10-08)

- JOB_ID: DX9EX-P0-VISUAL-REPAIR-SECOND-RESEARCH-20261008
- Start after user request approximately 2026-10-08 20:42 KST (not a completion timestamp).
- Authoritative connected GitHub focus HEAD `28e3de8025e3154feef02292ee1de624715f041c` at first inspection, no local/N100 source truth.
- User asked to fix every **source-proven and safely bounded** visual regression and do another 30-minute deep source research. No speculative broad alpha/WorldBillboard promotion; game runtime remains `RUNTIME_VALIDATION=UNTESTED` until verified Quest 3.
- Read `AGENTS.md`, `docs/VR_P0_VISUAL_COMPOSITION_CONVERGENCE.md`, previous 30m report and active R26+HUD source.
- Pipeline: original call evidence -> minimal producer/queue ownership code -> exact byte/negative contract -> CI exact SHA -> handoff; persist each checkpoint.

## C0 checkpoint
- Prior exact source material 9d01dd3e 4 CI gates success; optical fail 00519 still OPEN.
- Historical R74 four E8 direct CALL identities for GOAL/result with identical EXE SHA, first DispRank sprani 0xB9DA6 and lens CF53 are candidate source gaps.
- Do not call code/source fixed until committed. No legacy HUD 1000/5000 repetitions.

## C1 disassembly and producer safety
- Reviewed emoose original UIScaling/graphics and historical R74 producer hooks vs active focus.
- Same canonical EXE SHA original 16-byte CALL evidence: RESULT 0x97BE4 e81756f9fff30f2c7c245c6a00e8ba50 and 0x97DEC e80f54f9fff30f10872c100000f30f59 both E8->0x2D200.
- GOAL TIME 0xBEA5A e8c1f5ffffe8ecf6ffffb801000000c3 -> 0xBE020; 0xBEA5F e8ecf6ffffb801000000c333c0c3cccc -> 0xBE150.
- Historical R74 result midhooks had callsite enter/leave and all-node tag; Goal helper wrapper uses void() ABI and protects exact sprites. Modern TagAppendedNodes replaces legacy enumeration; direct Sumo glyph and clip producers remain.
- First DispRank kind1 0xB9DA6 lacks source-pinned CALL bytes, lens 0xCF53 old 20% disparity unproven under current R30. Keep these separately open pending actual byte and renderer-path validation.
- No new independent executable binary download in this step: historical same-SHA byte fixture will be tested by canonical inspector CI.
- Historical HMD FAIL OPEN / RUNTIME_VALIDATION=UNTESTED.


## C2 implementation and regression protection
- C++ real source commit bef9d1ff408ceadf98798995470753f1364eca14: src/hooks_uiscaling.cpp restored two historically verified R74 result-progress E8 call windows with bounded callsite enter/leave SpriteNode snapshots + ScreenHud tags, and two zero-argument GOAL sprite-producing helper wrappers which call original helpers before tagging all appended nodes.
- Original EXE contract commit 904e8a9a0fe92bb4548a416bf65d817fa90f1481: docs/VR_BINARY_CONTRACT.json expands 103->107 signatures, pinned same canonical EXE SHA and original 16-byte E8 bytes. Goal/result sourceBindings pin exact constants.
- Validator commits a00aa57c4eeb72cb1dcde60cd657a8d7c4bba2b5 and 38e01cba2636d4cf1aa0ca2fb1b0b2ad47da8f1a: existing 71 exact CALL producer suite untouched, four auxiliary producers verify rel32 destinations, full 16-byte fixtures, unique install ownership, queue begin/end + 4 additional unique mutated negatives. Old 10 mutations preserved; no repeat 1000/5000 audits.
- Current code deliberately retains old world billboard/normal game sprite source; does not force broad generic UI conversions. No Quest3 HMD test or runtime visual guarantee.
- Candidate full source SHA 38e01cba2636d4cf1aa0ca2fb1b0b2ad47da8f1a awaiting exact GitHub Actions CI.


## C3 exact-source CI verdict and adversarial second-pass (IN PROGRESS)

### Second-pass review batch RB01–RB05: distinct evidence
- RB01 exact artifact/build selector: active `.github/workflows/vr-dx9ex-active.yml` builds `ACTIVE_R26_R43_R44` via R30 R26-safe implementation; R33 full-chain compilation is not the shipped D3D9 DLL. Report CODE_SHA per distinct material commit, never infer HMD correctness from static CI.
- RB02 original vs historical vs EXE CALL producer: R74 same-SHA exact 4 E8 fixture CALLs for result/GOAL restored in current UIScaling; R59/R74 first POSITION kind1 at 0xB9DA6 separately restored after actual GitHub original EXE Inspector analysis run `37772663660`, static-exe job `113295795116` SUCCESS `known_call_sites=10/10`, `DispRank_first_kind1_0xB9DA6` producer window E8 destination `0x29530`. New 5-byte canonical signature `e885f7f6ff` pinned in manifest (runtime HMD still untested). Current 8 subsequent kind0 rank clip calls deliberately unchanged.
- RB03 regression and HMD baseline: archived 00519 user HMD FAIL for menu/car DDS, lens, 6th/6, rank/rival 4th+, +TIME/goal/result, F11, 90Hz; source-fix cannot erase those until matching Quest3/VDXR session. R50 world stereo and startup white-screen recovered are protected.
- RB04 backend and source exclusivity: no DX11 or frozen DXVK source changed. All code changes in active DX9Ex HUD, original EXE analyzer, P0 static guard and one XMT bounds source; no generic alpha/unknown-world promotion. Same-SHA 00519 old material HMD failure is not new runtime evidence.
- RB05 host life-cycle: host R23 can emit `projection-cached`, `recovery-left-eye-theater`, `recovery-full-mono-theater` when no fresh valid eye pair, so screen/head motion artifacts from host fallback must be differentiated by `finalLayerKind`, `frameId`, `sourcePoseSequence`, and per-eye draw/c64. Source records host-pipeline Avg/Max/P95 by capture/commit/render/endFrame and reject reasons; no runtime log was imported here.

### Distinct further hypothesis evaluation (do not blindly port)
| Screen symptom | Latest source-backed decision | Why not a broad speculative patch? |
|---|---|---|
| lens flare diplopia | old R73 Calc3D2D projected anchor 0xCF53 is absent in current R30 path; original exact alpha producer at 0xCABE precedes CF4E CALL and does not prove those are the *same* light source or same consumed SpriteNode | Old R73 20%-disparity constant was an optical candidate, not accepted HMD fix; current exact SceneEffect shader and XYZRHW routes have previously material fixes; require actual same-light/eye owner evidence |
| SkyGlow blows out text | Current two-eye scene-before-HUD capture deliberately drops glow when capture is unsafe; retain user requested factor, never enable stock mono double additive pass | A global gain change can overexpose the current safe baseline |
| car shadow at start | Original 0x69EB4 / 0x6AC76 / 0x6B766 are true car/world alpha `DrawObjectAlpha_Internal` producers with depth/stencil ownership | Changing to ScreenHud/world-flat would double or detach shadow; same-eye depth/stencil trace needed |
| 4th/5th place + rival car marker | Rank/rival recovered Calc3D2D view projection already bounded and multiple SpriteNode siblings tagged; behind-eye clipW failclosed installed | Actual carID, pose epoch and per-eye projected marker must correlate; no new parser-only bug proven |
| F11 gameplay overlay | Existing fixed XYZ/orthographic L/R owner is present; Game::is_in_game vs renderer Gameplay mode disagree in some *transition* states but both agree for normal STATE_GAME | Treat transition disagreement separately; no evidence of missing code for ordinary gameplay F11 optical failure |
| car selector white/brown DDS | UI fast decode + native fallback / original DDS rollback previously fixed, R15 partial UpdateSurface failclosed. XMT invalid entry pointer guard used raw cross-object pointer comparisons and unchecked pointer addition | Fixed only independently provable pointer arithmetic (integer offset bounds), preserve failclosed skip to avoid loading corrupt texture pointers; source fix not proof pixels restored |
| recenter/head-lock | Yaw-only recenter preserves pitch/roll, host R23 LOCAL-fixed menu vs VIEW-fixed; renderer marks poseSequence/eyeFov | Need actual fresh projection/frame packet correlation not global head lock changes |
| +TIME/checkpoint/goal vs goal-percent | Distinct direct exact producer groups: Sumo_Printf lower glyph, GOAL two helper CALLs, result progress two parent CALLs | Scoped per-call ownership fixes now exist; no queue-wide HUD promotion, test on one changed candidate |
| 72/90fps drops | host wait/capture/commit/render/endFrame P95 diagnostics and game cadence gate exist | No measured bottleneck currently; no arbitrary speed flag or frame generation without baseline |

### Actual compile failure recovered and repaired
- First generated code material `38e01cba2636d4cf1aa0ca2fb1b0b2ad47da8f1a` had HUD Inspector build job `113294637298` **FAILURE**, MSVC `src/hooks_uiscaling.cpp(445) error C2039: ScopedProducerSemantic is not a member of OutRunVR::GameSemantic` (retired R74 API). It was not misreported as a pass; in production source commit `4b974318c074c2eca6c5ff0df00d8c7646bd7c05` replaced old RAII scope with current `TagAppendedNodes` post-original-call node registry, and validator revised on `93a9ca...`. This is an actual repair informed by CI.
- Later source: exact first DispRank source 3f300eb..., original 5-byte manifest 01755de..., validator 1015aa5...; corrupt/late XMT bounds source 9635b609... and P0 3-negative guard 301c1be...; result midhook partial install rollback source 0a2c240... and 1 additional negative mutation 39d79da...
- Final material validation target in progress `39d79da4c3e1e4d80f6625aff5f3345926d08286`, DX9Ex Active run `37773459499`, OutRun EXE HUD Inspector `37773459468`, Domain Isolation `37773459466`; check exact outcome before final state. P0 verification now: 71 original HUD CALLs + four auxiliary result/GOAL CALLs + first rank CALL (108 canonical contracts total), old 10 fault cases plus 5 result/GOAL and 2 first-rank cases, XMT 3 negative source mutations.
- `RUNTIME_VALIDATION=UNTESTED`; NO test on Quest 3. No 1000/5000 static repetitions.


### Second-pass review RB06–RB10: device/producer/failure/CI adversarial specifics
- RB06 D3D9Ex lifecycle: R15 partial-RECT SYSTEMMEM -> DEFAULT shadow upload correctly uses UpdateSurface(sourceRect,destinationPoint) and if partial upload fails declines whole mip overwrite; ResetEx replays fresh R13 render/stage/sampler and R15 extra baseline while stateblock generation is renewed, not reused across Reset. These are already source-guarded; do NOT re-enable pre-Reset snapshot or turn partial upload into a full-mip retry. Deferred HMD: texture pixel metadata + resource generation after car-select loading.
- RB07 performance and synchronization: existing R23 pipeline provides source frameId/poseSeq, final layer kind, capture/commit/render/endFrame Avg/Max/P95 and rejection reasons. Game ProcessHost cadence waits host request token under a bounded timeout, failopen on stale host; R50 frame-stability baseline protected. No actual 72/90-Hz HMD trace acquired, so no basis to change pacing factors, duplicate draw count or OpenXR transport generation.
- RB08 exact failure paths: original SumoUISpriteReplay no-tick mask nested SPRARGS2 child_B4 copies are already bounded 8 and reject cycles, UIScaling new GOAL/result helpers now call original functions before all-priority scoped sprite tagging. Legacy first Win32 build at 38e failed on retired ScopedProducerSemantic; current source switched to active registry and static checks. XMT old pointer comparisons were mathematically unsafe for malformed headers; corrected using integer offset and maintained intentional skip rather than dereference. Users still need XMT skip log to know whether white DDS was caused by corrupt loader state.
- RB09 build and packaging: canonical active executable selector is ACTIVE_R26_R43_R44; each changed source/manifest is watched by GitHub Actions Active and HUD Inspector. Current canonical EXE pinned SHA 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3, manifest now 108. Analyzer reports 10/10 original known CALL sites with the newly independently verified first DispRank kind1. Original 71 verified direct HUD CALLs remain disjoint, 5 auxiliary result/goal/rank CALL source contracts separately bounded. Do not count 108 manifest entries as 108 HUD direct E8 CALLs.
- RB10 adversarial source change review: historical R73 0.20 lens disparity proposal follows an anchor at 0xCF53 while current 0xCABE alpha producer *precedes* CF4E projection in a different disassembly window. Producer correlation is not established, so copying a sticky latest lens 3D anchor would risk assigning a later light to an earlier sprite; no port. First DispRank 0xB9DA6 has a proved source E8->0x29530 in canonical CI and preserves original 5arg ABI, separate 8 clip siblings. Final result parent R74 exact bytes 0x97BE4/0x97DEC both E8->0x2D200, GOAL helper two E8 to 0xBE020/0xBE150; all group tags bounded by priority head/tail. Source never broadens generic WorldBillboard, scene alpha or ImGui.
- Optic state after second pass remains USER_RUNTIME_FAIL_OPEN(00519) / RUNTIME_VALIDATION=UNTESTED, no Quest3 headset testing, no new frame benchmark, and no claim of lens/shadow/sky/perf regression fully fixed.
### C3 additional material defect: XMT loader partial hook install
- source `src/hooks_bugfixes.cpp::FixFileLoadRace::apply` initialized a critical section then installed five hooks in sequence; previous code returned conjunction without reverting the already-installed subset. If Sumo_FileLoadServiceRequest enter lock hook succeeds but ServiceRequestMoveDone leave hook fails, loader thread may deadlock. Confirmed dangerous partial-install code path, not proof of real HMD event.
- Source commit `15175410f28246c798a5f9903d8a896e728953e0` performs all-or-nothing 5-hook rollback on failure while preserving an initialized critical section to avoid in-flight callback teardown hazard. Static P0 guard `808fa24156ce7af81a58f77f402826e2b92c9e37` checks pairing and injects two distinct missing-rollback faults. This is separate from XPR0 pointer arithmetic fix `9635b6091cecafe6696fc231bdb89311b007d279` and its 3 negatives.
- Final target updated from prior 39d79d test snapshot to current `808fa24156ce7af81a58f77f402826e2b92c9e37`; all earlier automatically superseded/cancelled CIs are NOT valid exact-SHA final proof. Continue from latest SHA, never relabel old static successes as a new build success.
## C4 second independent deep research and handoff
PENDING
