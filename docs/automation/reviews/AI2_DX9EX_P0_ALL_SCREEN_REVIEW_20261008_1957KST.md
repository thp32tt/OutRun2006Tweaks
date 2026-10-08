# DX9Ex Quest 3 전체 화면 문제 — 30분 집중 소스 딥리뷰

- REVIEW_ID: `DX9EX-AI2-P0-ALLSCREEN-20261008-1957KST`
- 요청: 기존에 발생한 실기 화면 문제 **전체**를 원본 모드 / EXE producer / 현재 소스 / CI / 사용자 런타임 증거로 재점검.
- 검토 시작(실측): 2026-10-08 19:57:25 KST. 시간 기록과 실제 진행은 별도 검증하며 30분 진행/완료를 미리 선언하지 않음.
- branch `vr-d3d9ex-focus`; 시작 HEAD `444609d872c2a319d42032b1afbb8b9dcd059472` (docs only); 검사한 최종 변경 소스 SHA `9d01dd3eb871be4a439457247596a60cb5c8f74b`.
- 최초 CI 정합 확인(4/4): DX9Ex Active `37766111828` SUCCESS, EXE HUD Inspector `37766111701` SUCCESS, DX9Ex Full Source Impact `37766111648` SUCCESS, Domain Isolation `37766111726` SUCCESS. 정확 코드 SHA 일치. 이는 **실기 광학 PASS가 아님**.
- `RUNTIME_VALIDATION=UNTESTED`; 이전 00519 USER_RUNTIME_FAIL 유지. 동일 소스에 대한 1000/5000 반복 정적검사 없음.
- 기준: `AGENTS.md`, `docs/VR_P0_VISUAL_COMPOSITION_CONVERGENCE.md`, `docs/VR_REGRESSION_KNOWLEDGE.json`, `docs/VR_HUD_SEMANTIC_BASELINE.md`, 이전 `AI2_DX9EX_RUNTIME_EVIDENCE_DEEP_RESEARCH_20261008.md`, 00519/00557/00558 및 현재 active renderer.

## 진행 체크포인트
- [x] C0: 인증된 GitHub 현재 브랜치, 원본 리그레션 기록, 정확 SHA 4종 CI 완료 재검증.
- [x] C1: 사용자 기존 항목 총목록 및 증상·정확 원본 game producer 소유권 대조.
- [x] C2: SceneEffect/lens/SkyGlow/그림자, WorldBillboard/rank 1~5위, HUD/글리프/+TIME/골인, 메뉴/YES-NO/F11/texture, recenter, 프레임 페이싱 소스 정적 분기 대조.
- [ ] C3: 새로운 소스 위험 여부를 기존 fix·negative test와 대조해 false-positive 배제. 발견 항목은 정확 수정 지점과 재현 가능한 반증 조건 기입.
- [ ] C4: 최종 triage·필수 CI/실기 검증·인계. 별도 요청 또는 확실한 소스 버그 없이는 넓은 휴리스틱 수정 금지.

## C0 상태
- 역사상 실기 오류를 source/static success만으로 지우지 않는다. 기존 결과 재사용 우선.
- 원본 binary manifest: `OR2006C2C.EXE` pinned `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, manifest 계약 103개, explicit HUD CALL 71개.
- GitHub checkpoint: 다음 조사내용은 이 파일을 순차 업데이트해 세션 유실을 방지한다.

## C1 — 원본 증상 전체 비교 (ORIGINAL_SOURCE_CHECKED)

| 증상 | 원본·게임 producer | 현재 소스와 잔여 증거 |
|---|---|---|
| HUD 백색 글씨/6th/6 | DispRank 8 CALL, TextGlyph/ScreenHud | all-node 태그, raw WVP 검증, Quest 실기 미완 |
| +TIME·체크포인트·골인·결과 기록 | Sumo_Printf 0x975EE/0x97727/0x977FB, glyph 0x2C808/0x2C9DB, result 0x97BB7/0x97DA7 | Sumo 마스크 복사·expiry 보존, 원본 행렬 폴백, 광학 미완 |
| 1~5위·라이벌 마커 | Calc3D2D 0x49940; rank 0xBB0FB..0xBB2D0, rival 0xBB6F5/0xBB796 | 00554 finite / 00558 clipW / all children source PASS, 실제 차량 고정 미확인 |
| 화살표·YES/NO | 원본 put_clip_sprite, fork 12 exact option CALL + left/right | ScreenHud ownership CI PASS, 실기 미완 |
| F11 Tweaks 패널 | ImGui XYZ+orthographic, external overlay, R30 per-eye+scissor | static PASS, 게임 중 양안 미검증 |
| 렌즈 플레어 | Clr_SceneEffect 0xBE70 znear 0.05, flare 0xCABE->0x56D0, projection 0xCF4E->0x49940 | R30 shader/XYZRHW, original raw WVP CI PASS, 광학 미확인 |
| SkyGlow 과노출 | upstream RestoreSkyGlow, R30 per-eye independent | prior mono disabled, current pre-HUD capture failclose, brightness 미측정 |
| 시작 그림자 | CalcPeraShadow original 0x69EB4/0x6AC76/0x6B766 | WorldParticle 소유권 유지, 렌더/스텐실 중복 미분리 |
| 메뉴·차량 DDS 누락 | native D3DX/fast DDS, UiDdsOriginalState restore | original bytes/header rollback and pitch-aware decoder, GPU 화소 미확인 |
| 리센터/헤드락 | headPoseSequence, OpenXR camera, R30 HUD finite plane, queue semantics | eye별 frame/pose epoch 미측정 |
| FPS 72/90Hz 불안정 | game tick fn43FA10, Sumo no-tick, DirectGPU/host | 00519 사용자 실기 FAIL, 현재 profiler 미측정 |
| 보호 불변성 | R50 도로/차량 월드 스테레오·startup white recover | broad alpha/primitive shader heuristic 변경 금지 |

원본 파일: https://github.com/emoose/OutRun2006Tweaks/blob/master/src/hooks_graphics.cpp ; https://github.com/emoose/OutRun2006Tweaks/blob/master/src/hooks_uiscaling.cpp ; https://github.com/emoose/OutRun2006Tweaks/blob/master/src/hooks_framerate.cpp

현재 포크: src/hooks_graphics.cpp; src/hooks_uiscaling.cpp; src/hooks_framerate.cpp; src/hooks_textures.cpp; src/overlay/hooks_overlay.cpp; src/vr/game/render_semantics.hpp; src/vr/game/outrun_renderer.cpp.

주의: VR_REGRESSION_KNOWLEDGE.json의 10개 incident key는 최종 광학 합격 숫자가 아님. USER_RUNTIME_FAIL 00519는 OPEN.


## C2 — 현재 코드 경로별 위험 감사 (SOURCE_CROSSCHECKED; OPTIC_UNTESTED)

### C2-A: HUD + Lens 원본 게임 행렬 — 새 조건부 source gap
- ACTIVE stereo: src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp R30GetExtendedRawWvpForExactHud (lines 1540–1565), R30GetExtendedRawWvpForExactSceneEffect (lines 1574–1598), R44GetOwnedRawOverlayWvp, R30ClassifyScreenSpacePass, R30BuildScreenSpaceEyeConstants. Renderer c64 history: src/vr/game/outrun_renderer.cpp RecordGameWvpWrite / GetLastRawGameWvpWrite.
- Correctness already installed: exact Hud/SceneEffect semantic required; match current VS shader identity+serial, original game raw c64 (not GPU injected), monotonic topLevelDrawSerial and age <=128 draws; old R44 remains 12 draws. All these are present in current source and 9d01 four CI gates PASS.
- **Residual source-condition gap (H1, no HMD proof):** the extended source check does not compare PresentEpoch/poseSequence/queue-node identity or a same-frame producer epoch, just matching shader + <=128 draws. Counterexample: a shader and game raw c64 last updated 50 draws before an interleaved Present, then exact HUD draw after Present with no new c64: age 50<=128, shader same, but stale pre-Present matrix may be accepted. Whether game executes that sequence is unknown. Need a source/telemetry testcase of WVP write PresentEpoch vs draw PresentEpoch; do not simply remove 128 reuse (legit +TIME multi-glyph batches).
- Source bound: R30GetExtendedRawWvpForExactHud carries a writeSerial local but only uses shader and draw age. Queue provenance recorded in outrun_renderer.cpp LastGameWvpQueueNodeEpoch/Node is diagnostic, not part of this bounded owner proof.

### C2-B: exact rank/rival, Sumo, queue semantic lifetime
- src/hooks_uiscaling.cpp correctly scopes rank's 0xBAD20 subcall with per-invocation cleared thread_local RankMarkerProjectedInfo, finite Calc3D2D 0xBAEE7/0xBB6F5 recovery, all-node sibling tagging across SpritePriorityCount; R57 behind-eye clipW positive. Vehicle marker world model is protected from generic HUD conversion.
- RivalMarkerProjectedInfo is separately thread_local and consumed/cleared in RivalMarker_sprani 0xBB796, not on every Present. **H2 conditional:** if 0xBB6F5 updates an anchor and its 0xBB796 consumer is skipped, the saved anchor can survive until next consumer. Need original control-flow/disassembly/culling evidence before any expiry patch, especially no-tick Sumo replay semantics.
- src/vr/game/render_semantics.hpp ArmNextDraw(WorldBillboard/WorldParticle) is a thread-local one-shot, consumed at first top-level D3D draw; queue Begin/End do NOT expire NextDrawScope. Sources: src/interpolation.cpp::HeartPulse_dest and src/hooks_bugfixes.cpp::FixParticleRendering::destination. **H3 source-proven missing TTL/clear boundary, optical consequence conditional:** an original hook call followed by a culled/no-draw branch can tag a later unrelated draw. Existing verified-world gate reduces world-promotion exposure but does not prove the token harmless. Require one injected no-draw branch test before changing.
- src/hooks_framerate.cpp SumoUISpriteReplay copies each mask child_B4 chain, rejects cyclic or >8 children, keeps original sprani/glyph priority, and calls original fn43FA10(numUpdates) to retire Extend Time. **H4:** a legitimately >8-mask original sprite will intentionally disappear on a no-tick replay. Prove original max chain length with runtime/analyzer before raising the limit.

### C2-C: DDS, F11 and theater presentation
- src/hooks_textures.cpp UI/scene original DDS header+sprite_scales restore / native D3DX fallback / pitch-aware fast decoded texture confirmed. src/vr/d3d9/ex_device_upgrade_r15.cpp R15UploadLevel uses UpdateSurface sourceRect and destinationPoint; when partial upload fails it refuses a whole-mip overwrite (protects unrelated pixels) and retires invalid shadow. These guards protect source integrity; no Quest GPU pixel acceptance.
- src/hooks_bugfixes.cpp FixFileLoadRace always active; LoadTextures_dest checks XPR0 entry inside block and on failure sets textureIdx to full texture count, **skipping remainder**. The code explicitly logs 'outside xmtset block... skipping its remaining textures'. **H5 significant alternative for disappearing menu/car assets** independent of DDS failure: transient/incomplete XMT pointer state can reach this failclosed branch. Need an actual log signal/texture IDs before treating missing pixels as DDS regression; preserve crash-avoidance behavior.
- Fork F11: src/overlay/hooks_overlay.cpp selects ScopedExternalOverlaySemantic only when Game::is_in_game(); src/vr/game/outrun_renderer.cpp CurrentPresentationMode explicitly selects STATE_START/WARP/RESTART/GAME/GIVEUP/PAUSE/GOAL/TIMEUP as gameplay and all others as Theater. **H6:** the predicates may differ during result/transition, and R30's fixed XYZ/ortho F11 owner requires a valid completed world stereo and pose. Compare exact GameState, Game::is_in_game and presentationMode before labeling F11 head-lock.
- Exact submodule external/imgui gitlink f1cc2ae15e53a861a874c3034aae6798fde194ab; ocornut/imgui/backends/imgui_impl_dx9.cpp lines 355–397 source proves CreateTexture then failed LockRect can still SetTexID+Status(OK), and update branch calls UnlockRect/Status(OK) even on failed lock. **H7 confirmed upstream backend error path / not proven headset trigger.** Distinguish blank F11 font atlas from missing game DDS; do not replace entire upstream submodule absent observed LockRect failure.

### C2-D: light effects, shadow, recenter, cadence, protected world
- src/hooks_graphics.cpp original Clr_SceneEffect scoped camera near 0.05, nested state restore intact; exact DrawObjectAlpha projected lens 0xCABE semantic, original car-ground shadow 0x69EB4/0x6AC76/0x6B766 guarded WorldParticle.
- src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp R30BeforeScreenDrawForSkyGlow marks first exact HUD/overlay draw and tries bilateral clean snapshot, Present skips additive pass when no captured pre-HUD scene exists. **H8 conditional:** generic unclassified UI or rendering outside these exact scopes can still occur before capture, particularly under R30 fallback, while capture checks world-stereo frame completeness; no source proof it has happened. Per-eye before/after producer telemetry needed; retain SkyGlowFactor as user requested, do not brighten globally.
- src/vr/d3d9/stereo_renderer_r33.cpp owns Reset/StateBlock upper hook; ex_device_upgrade_r15.cpp explicit baseline state replay. Need real Reset/resize/recenter/pose epoch from host to distinguish a missing HUD from stale device/camera state.
- src/hooks_framerate.cpp CalcNumUpdatesToRun(60), 0-tick when render unlocked, Sumo queue replay and Interp::AfterTick; 72/90Hz stereo may present repeated simulation states but interpolate. Without host xrWaitFrame/EndFrame and draw amplification timing there is no evidence that GPU overhead alone caused the 00519 FPS complaint.
- Preserve R50 headset-proven world stereo, R50 startup white-screen fix, R50 stability. The 9d01 static/build 4/4 PASS and package do not prove visible stereo convergence.

### Source limitations
- Current C2 is direct source inspection of all 10 focal graphics/UI/frame/queue/texture files plus R14/R15/R26/R29/R30/R33, renderer, upstream and pinned ImGui. Earlier 150-file repository-wide lexical scan was read as prior evidence; *this* checkpoint does not claim a second fresh statement-by-statement 150-file scan.
- All H1-H8 are *conditional source gaps* or original error paths, not new confirmed user HMD optical failures. Distinguish H7 upstream backend error path (source-confirmed) from actual occurrence (unproven).


## C3 — 반증·남은 결함
PENDING

## C4 — 최종 판정과 다음 변경
PENDING
