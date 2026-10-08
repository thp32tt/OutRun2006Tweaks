# DX9Ex Quest 3 실기 회귀 — 원본·바이너리·전체 소스 교차 검토 (2026-10-08)

> 상태: **IN_PROGRESS / EVIDENCE_RESEARCH_ONLY**. 이 파일은 채팅 중간중간 GitHub에 저장하는 내구성 체크포인트입니다. **이번 작업에서 런타임 소스·빌드 설정은 수정하지 않습니다.**
> 기준: vr-d3d9ex-focus, Quest3/VDXR 실기 회귀. RUNTIME_VALIDATION=UNTESTED. 진단 가설을 수정 완료로 쓰지 않습니다.

## Checkpoint 0 — 조사 범위 및 방법 (persisted)
- 목적: 렌즈플레어, +TIME 연장, 체크포인트·골인기록·결과화면, 흰색 HUD·6th/6, 메뉴/YES-NO/화살표, 라이벌·차량 순위 마커(4~5위), F11 메뉴, 차량선택 텍스처, 시작 그림자, 재중앙정렬과 밀집·모래·연기 프레임 저하 등 기존 실기 오류.
- 증거 우선순위: emoose/OutRun2006Tweaks 원본 hooks/주소 → 포크 과거 브랜치와 의미 계약 → canonical EXE 디스어셈블리/XREF/byte 계약 및 HUD Inspector → 현재 생산자·SpriteNode·queue·R29/R30/R31/R33·OpenXR host → 정확 SHA 정적·빌드 게이트 → 최후 실기.
- 각 결함마다 증상 / 원본 호출자·정확 주소 / 현재 소스 경로 / 최소 가설 / 반증 / 영향 범위 / 정적 재현·결함주입 / 실기에서만 판단할 항목을 기입.
- 기존 VR_REGRESSION_KNOWLEDGE.json, VR_PROBLEM_HISTORY.md, VR_P0_VISUAL_COMPOSITION_CONVERGENCE.md, VR_HUD_SEMANTIC_BASELINE.md, VR_BINARY_CONTRACT.json, 00519 실기 실패/00557·00558 검증 및 Issue #13/#14와 중복 대조.
- 정적 PASS ≠ 실기 PASS. 1000/5000 반복 검사는 재가동하지 않으며 실제 변경 SHA별 관련 검사만.

## Checkpoint 1 — 원본·포크 계보 확인 (EVIDENCE_REVIEWED)

### 원본 훅과 원래 게임 소유권
- **Lens / SceneEffect:** 원본 `emoose/OutRun2006Tweaks/src/hooks_graphics.cpp`의 `FixZBufferPrecision::Clr_SceneEffect_dest` (약 983–1074행)는 RVA `0xBE70`을 감싸며 원래 카메라 `perspective_znear_BC`를 보관하고 near `0.05f`로 설정→`CalcCameraMatrix_dest`→original `Clr_SceneEffect` 호출→near 및 카메라 복원 순서를 수행한다. 이 효과를 일반 screen HUD로 일괄 변환하거나 원본 near-plane/중첩 상태를 무시하는 것은 위험하다. https://github.com/emoose/OutRun2006Tweaks/blob/master/src/hooks_graphics.cpp
- **차량 시작·선택 그림자:** 원본 `RestoreCarBaseShadow::CalcPeraShadow`는 NULL hook 복원 세 호출점 `0x69EB4`, `0x6AC76`, `0x6B766`에서 차량행렬+`mxTranslate(0,0.05,0)`+`DrawObjectAlpha_Internal`을 사용한다(약 116–156행). world-ground shadow이므로 평면 ScreenHud 승격은 근거 없음. https://github.com/emoose/OutRun2006Tweaks/blob/master/src/hooks_graphics.cpp
- **순위·라이벌:** 원본 `hooks_uiscaling.cpp`는 `Calc3D2D=0x49940`, `RankMarker_Truncate=0xBB046`, rival sprani 4호출 `0xBB0FB, 0xBB133, 0xBB16C, 0xBB1A5`, 4위 이상 클립 5호출 `0xBB21F, 0xBB241, 0xBB271, 0xBB2BC, 0xBB2D0`을 정확히 구분한다. 스크린 HUD 숫자와 차량 위 세계 고정 마커를 혼동해서는 안 된다. https://github.com/emoose/OutRun2006Tweaks/blob/master/src/hooks_uiscaling.cpp
- **시간·골인 표시:** 원본 `hooks_uiscaling.cpp`에는 `DispTimeAttack2D` 위치/스케일/scroll 조정 훅과 NaviPub 스프라이트 구간 훅이 따로 있다(약 382행 이후). 원본 고유 `SumoUISpriteReplay`는 _Disp와 _Ctrl 틱 차이로 스프라이트 및 개별 글리프를 재생하고, 원본 `Game::fn43FA10(numUpdates)`은 'extend time' 그래픽의 정상 소멸을 위한 루프 호출로 설명한다(약 120–231, 420–425행). +TIME의 중복 표시는 `expiry tick`, `queue multi-child`, `VR stereo ownership`을 따로 검사해야 한다. https://github.com/emoose/OutRun2006Tweaks/blob/master/src/hooks_framerate.cpp
- **기존 의미 지도:** `docs/VR_HUD_SEMANTIC_BASELINE.md`는 DispRank 8개 `0xB9F3A..0xBA052`, TimeAttack/result scroll 15개 `0xBE5CD..0xBE81C`, HUD_GOAL_TIME/GHOST/RIVAL/GEAR/heart 등 서로 다른 계열을 정리한다. 원본 주소는 *체크인된 canonical EXE 바이트와 매번 대조*해야 하며, primitive-count/광범위 WVP 휴리스틱으로 대체하지 않는다. https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/VR_HUD_SEMANTIC_BASELINE.md

### 현 포크의 기존 조사와 중복 방지
- 같은 날짜 작성된 `docs/automation/reviews/AI2_QUEST3_LENS_TIME_GOAL_SOURCE_REPAIR_20261008.md`는 별도의 렌즈 fixed-function XYZRHW 소유권, 정확 ScreenHud의 stale world veto, glyph sibling tagging 결함을 소스 단위에서 고치고 material SHA `5011d1e7ca53d73b2cffc7e841dc39e5a57aa6c1`을 기록했다. 본 조사에서는 같은 결함을 신규로 발견했다고 주장하지 않는다.
- `docs/automation/reviews/AI2_QUEST3_LENS_TIME_GOAL_DEEP_AUDIT_CONTINUATION_20261008.md`는 lens `0xCABE`가 기존 `0xCAE0..0xD100` 분석창 바깥이라는 디스어셈블리 provenance 오류와 Sumo masked `SPRARGS2::child_B4` shallow-copy lifetime을 후속 보정하고, 통합 material SHA `b14901f8b70b1b6fda8a9aded1e340147a453e68`의 DX9Ex Active `37752619285`, HUD Inspector `37752619496`, Full Source Impact `37752619267`, Domain Isolation `37752619334` SUCCESS를 기록했다. **실기 렌즈/+TIME/골인은 여전히 UNTESTED**.
- 링크: https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/automation/reviews/AI2_QUEST3_LENS_TIME_GOAL_SOURCE_REPAIR_20261008.md / https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/automation/reviews/AI2_QUEST3_LENS_TIME_GOAL_DEEP_AUDIT_CONTINUATION_20261008.md

### 이 체크포인트의 경계
- 소스·원본·기존 리뷰 파일을 직접 열어 읽은 사실까지만 확인. 새 GPU 캡처·게임 실행·전체 바이너리 동적 disassembly를 수행한 것으로 주장하지 않는다. 렌즈와 골인 화면의 눈에 보이는 복시는 '과거 사용자가 확인한 회귀'이지 최신 SHA의 재현 결과가 아니다.


## Checkpoint 2 — canonical EXE / 디스어셈블리 계약 (EVIDENCE_REVIEWED)

- 기준 EXE: `OR2006C2C.EXE` x86/PE32, image base 0x00400000, SHA-256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, 크기 3,674,112 bytes. 원본 emoose v0.1 배포물과 동일 파일을 CI에서 다운로드·SHA 검증하도록 설정; 바이너리 자체는 Git 저장소에 없음. https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/VR_BINARY_CONTRACT.json
- manifest `docs/VR_BINARY_CONTRACT.json`에서 **총 103개 계약** 확인(모두 HUD direct CALL만은 아님). `tools/verify_vr_hud_exact_callsite_contract.py`의 고정 그룹+추가 scalar 계약으로 **71 canonical HUD CALL 위치, 5-byte x86 E8 rel32 목적지, 상호 중복 없는 훅 소유권**을 검증하도록 구성됨. `--self-test` 10종은 동일 소스 1000·5000반복과 다른 의도적 결함 주입이다.
- **렌즈 플레어:** `tools/analyze_outrun_exe.py::PRODUCER_WINDOWS`가 0xCAB0–0xCAE0의 `0xCABE→0x56D0 DrawObjectAlpha_Internal`와 0xCAE0–0xD100의 `0xCF4E→0x49940 Calc3D2D`를 **서로 별개의 CALL producer 창**으로 정의하고 정확 E8 rel32 목적지를 검사한다. 0xCABE가 0xCAE0 이후라고 추정한 과거 창은 이미 수정됐다. 두 producer 간 같은 광원/동일 draw instance 연결은 이 주소 증거만으로 확정 불가.
- **+TIME/골인 글리프:** 0x975EE·0x97727·0x977FB direct CALL→0x2CDD0 `Sumo_Printf`; glyph 내부의 0x2C808·0x2C9DB→0x2CFE0 `put_sprite_ex`. 골인/기록 등과 연결되는 0x97BB7·0x97DA7→0x2D280 `put_clip_sprite`; TimeAttack scroll 0xBE5CD..0xBE9A3 역시 별도 exact right HUD ownership. 하나의 glyph/scroll 래퍼만 고쳐서는 다중 자식·priority·tick 차이를 설명하지 못함.
- **순위 및 옵션:** 4위 이상 `0xBB21F...0xBB2D0→0x2D280` clip, 1~3위 `0xBB0FB...0xBB1A5→0x29580` sprani, 상대 마커 `0xBB796→0x29580`, 메뉴 화살표 12개 exact `0xE358B..0xED7A3→0x2D280`. 동일 원본 함수(`put_clip_sprite`)의 호출점별 ScreenHud/WorldBillboard 소유권 분리가 필요.
- **관련 validator:** `tools/analyze_outrun_exe.py`는 known target 지도·producer windows·CALL RVA 분석을 제공하고, `tools/verify_vr_hud_exact_callsite_contract.py`는 source wrappers/hook arrays 및 manifest 서명검사를 수행한다. https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/tools/analyze_outrun_exe.py / https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/tools/verify_vr_hud_exact_callsite_contract.py
- 증거 수준: **체크인된 정적 분석기·EXE 계약·기록된 CI 성공을 대조**했다. 이번 조사 세션에서 독자적으로 원본 EXE 바이트를 다운로드·새 바이너리 디스어셈블 또는 CI 실행한 것은 아님. 신규 바이너리 증거나 optical PASS로 과대 표기 금지.

### 이미 검증된 소스 상태와 과거 HMD의 간격
- 00558 material `b14901f8b70b1b6fda8a9aded1e340147a453e68`: DX9Ex Active `37752619285`, HUD Inspector `37752619496`, Full Source Impact `37752619267`, Domain Isolation `37752619334` PASS 보고. 이 정적 검증은 00519에서 사용자가 관찰한 복시/헤드락/90Hz pacing 실패를 자동으로 폐쇄하지 않는다.


## Checkpoint 3 — 전 영역 런타임 경로 / 결함별 감별 분석 (SOURCE_CROSS_CHECKED; HMD NOT TESTED)

### 증거 수준 규칙
- **OBSERVED_OLD_HMD_FAIL**: 사용자 실기 00519에서 보고. 해당 실행 자체의 `CONVERSION-DX9EX-00519.json`에는 `runtime_validation=UNTESTED`로 적혀 있으나 사용자 보고·`docs/VR_P0_VISUAL_COMPOSITION_CONVERGENCE.md`에는 USER_RUNTIME_FAIL. 이는 *회계/자동화 레코드와 사용자 시각증거의 분리*다. 00519 실패를 무효화하지 않는다.
- **FIXED_SOURCE_CI / OPTIC_OPEN**: 후속 실제 C++ 보정+exact-SHA CI PASS까지는 인정하되 최신 Quest3 optical 결과는 무조건 미판정.
- **HYPOTHESIS_ONLY**: 소스 수준 가능한 경로이나 당시 문제가 실제로 그 경로를 통과한 데이터 없음. 임의로 결함 확정/코드 패치하지 않는다.

| P | 기존 실기 증상 / 안정성 항목 | 원본→현재 경로와 독립 증거 | 현재 판정 / 다음 판별 증거 |
|---|---|---|---|
| P0 | 렌즈 플레어 2중, 머리 추종·위치 이상 | 원본 `Clr_SceneEffect` RVA `0xBE70`의 카메라 znear 0.05 스코프와 `0xCABE→DrawObjectAlpha`, `0xCF4E→Calc3D2D`를 분리. 현재 `hooks_graphics.cpp::VRLensFlareProjected2D/Clr_SceneEffect_dest`; R30 shader `R30ClassifyScreenSpacePass` + fixed XYZRHW `R30ConfigureXyzrhwWorldEffect` 둘 다 exact SceneEffect 분기 있음. nested near-plane 상태 보존도 00557에 반영. | **FIXED_SOURCE_CI / OPTIC_OPEN.** 0xCABE alpha draw와 0xCF4E projected light가 동일 스테레오 변환/pose를 공유하는지 아직 미증명. 한 frozen SHA의 eye별 FVF, c64 raw WVP, RHW/depth, producer scope, pose epoch와 head yaw에서 플레어 단일성 확인. 공간 빌보드와 평면 flare는 분리. |
| P0 | +TIME·체크포인트·골인·결과 기록/흰 글리프 복시 | 원본 `Sumo_Printf` 0x975EE/0x97727/0x977FB, glyph 0x2C808/0x2C9DB, `put_clip_sprite` 0x97BB7/0x97DA7 및 TimeAttack/NaviPub은 서로 다른 경로. 현재 `TextGlyph_putSprite`/`TagAppendedNodes` 전체 우선순위 자식 전파, `hooks_framerate.cpp::SumoUISpriteReplay` bounded deep masked-chain 복사, R30 `semanticHud` shader 경로의 stale-world gate 우회 반영. | **FIXED_SOURCE_CI / OPTIC_OPEN.** `Game::fn43FA10(numUpdates)` 원본 연장표시 expiry 호출 유지. 재현시 glyph producer→21 priority 큐→no-tick replay→VS/XYZRHW→per-eye owner, 원래 timer tick/skip과 결과 글자 위치 각각 대응. 런타임 double draw인지 halo인지 구분. |
| P0 | 6th/6·HUD 흰 글자·순위 숫자 이중/헤드락·크기 | 원본 `DispRank` 정확 8 call, `ExactScreenHudRight/Left`, `TextGlyph` 직접 호출 분리. 현 `hooks_uiscaling.cpp`와 R30 `ScreenHud`의 원근 평면 경로가 구현됨. HUD scale와 recenter는 별개. | **FIXED_SOURCE_CI / OPTIC_OPEN.** c64 설정 시점이 SpriteNode semantic 활성화 시점보다 앞설 가능성, `R44GetOwnedRawOverlayWvp` shader/age miss 후 live c64를 재사용하는 경로는 source-conditional. shader epoch, raw-vs-injected WVP, queue node/epoch, eye pose, scale 0.82를 구분하는 한 회차 trace; 이전 보고의 `CurrentDrawMatchesVerifiedWorld`에 의한 정확 HUD veto는 현 R30 코드에서 제거된 상태라 재수정 금지. |
| P0 | 상대 차량 위 1~5위/라이벌 마커 미고정·4~5위 중복 | 원본 `Calc3D2D` RVA 0x49940, `RankMarker_Truncate` 0xBB046, sprani 4 calls와 4th+ clip 5 calls, rival 0xBB796. 현재 `RankMarkerSub_dest` 호출별 payload 초기화, `RivalMarker_sprani` consume-once, multi-child tag, `R57ProjectViewPoint` clipW <= 1e-6 후방 거부(00558). | **FIXED_SOURCE_CI / OPTIC OPEN.** 실제 차량별 WorldBillboard anchor가 같은 차량/프레임에서 보존되는지 미증명. car id, Calc return RVA 0xBAEE7/0xBB6F5, interpolation alpha, marker consumption, queue node, projected eye delta를 정합 대조. 정상 stereo world와 무관한 marker 4~5 숫자 다중생성 원인 별도 측정. |
| P0 | F11 게임 중 UI 복시, 옵션 화살표·YES/NO 머리 추종 | 원본/고정 ImGui DX9 backend는 D3DFVF_XYZ+null VS+orthographic(게임 sprite의 XYZ RHW와 다름). 현 `hooks_overlay.cpp` gameplay에서만 `ScopedExternalOverlaySemantic(ScreenOverlay2D)` 사용, R30은 external fixed XYZ/ortho 및 eye별 projection+scissor 별도 경로를 추가; 옵션 12개 exact CALL과 YES/NO는 게임 스프라이트 경로. | **FIXED_SOURCE_CI / OPTIC OPEN.** 메뉴(theater)와 인게임 F11을 별도 테스트하고 projection·scissor·viewport 복원, 좌/우 수, 화면 고정 여부를 분리. ImGui 고정 XYZ를 임의 ScreenHud XYZRHW와 같은 규칙으로 합치지 않는다. |
| P0 | 메뉴·차량선택 DDS 이미지 유실/흰 화면/갈색 사각형 | 원본 `hooks_textures.cpp` D3DX 경유 replacement/legacy allocator. 현재 `UiDdsOriginalState`는 교체 실패 시 원본 bytes/header/scale 복원 후 native D3DX 재시도, fast DDS explicit dimension/mip/row-pitch·fallback 및 출력 포인터 무효화 방어 반영(00547~00555 계열). D3D9Ex `CreateTexture` MANAGED 호환 변환과 R15 partial rectangle upload는 별개의 계층. | **FIXED_SOURCE_CI / OPTIC OPEN.** 실제 선택화면 이미지의 원본/교체 DDS pixel 자료와 GPU frame 미확보. `D3DX` 반환코드, texture ID, `LockRect` HRESULT/pitch, fallback 횟수, Reset epoch, R15 partial `UpdateSurface` 실패 로그 및 실제 스크린샷 한 번 대응. 파일 이름 주소 동일성(PrevXmtName)은 원본 계승 가설일 뿐 확정 원인 아님. |
| P1 | 시작 그림자 2중, 렌더 레이어 불일치 | 원본 car base shadow는 `0x69EB4/0x6AC76/0x6B766` 정확 훅과 `DrawObjectAlpha_Internal` 차량행렬을 사용한다. 현 `hooks_graphics.cpp::RestoreCarBaseShadow` 유지, R30 eye draw/state guard/SceneEffect 구조가 관련. | **OBSERVED_OLD_HMD_FAIL / HYPOTHESIS_ONLY.** 중복이 원본 shadow + stereo replay인지, shadow mask/스텐실 pass인지 source만으로 확정 불가. car selection와 레이스 시작의 `DrawObjectAlpha` callsite·depth/stencil·pass count·eye state를 비교; blanket alpha=ScreenHud 금지. |
| P1 | SkyGlow 과노출/흰색 번짐(이전 원복 요구) | 원본 `RestoreSkyGlow`와 현 `R30CaptureSkyGlowSceneBeforeHud`/`R30ApplyStereoSkyGlow`는 PresentEpoch·eye별 pre-HUD capture를 분리. 현 R30은 **성공한 HUD/F11 draw 이전**에 snapshot을 시도한다. 앞선 모든 UI draw가 fallback이면 scene snapshot이 늦을 가능성. | **HYPOTHESIS_ONLY.** 정확 source SHA, 좌/우 캡처 타임과 최초 HUD draw를 대조; 같은 세션에서 SkyGlowFactor 0 vs 기본값(광원 halo 차이), 눈 움직임 때 양안 복시와 분리. 사용자 동의 없는 SkyGlow 증폭·넓은 alpha 변경 금지. |
| P1 | 재중앙정렬과 머리 추종 HUD, reset 이후 UI 위치 이동 | 현 camera/renderer pose latch, projection and head inverse, `recenter` state, host frame admission 및 R33 Reset/StateBlock 복원은 별도 epoch/lifetime. | **OPTIC OPEN.** recenter 전후 동일 marker/record/head-fixed HUD의 display pose·frame/sourcePoseSequence·session epoch 대조; Reset/ResetEx 후 D3DPOOL_DEFAULT/StateBlock/RT release/rebind 계약과 함께 검토. 원본 D3D9 Reset과 D3D9Ex 호환 ResetEx를 동일 취급하면 안 됨. |
| P1 | 밀집 건물·모래·파티클·모래 튐 90Hz 불안정 | 과거 00519의 90Hz 페이싱 불합격; 이전 R51 자료 peak drawsPerPresent≈3929, lower Present 최대≈16.639ms 보고. `hooks_framerate.cpp`의 CalcNumUpdatesToRun/zero tick, Sumo no-tick replay, R30 R9/R26 stereo duplicate cost, host xrWaitFrame/EndFrame 및 DirectGPU ACK/fence/copy 서로 다른 병목. 60Hz source를 90Hz VR에 재사용하면 headset FPS와 다른 cadence judder 가능. | **OBSERVED_OLD_HMD_FAIL / CURRENT UNMEASURED.** 동일 코스/정확 profile 72Hz 목표 또는 90Hz 환경에서 game simulation tick vs produced eye pair, xrWaitFrame→EndFrame P95/P99, draw amplification, GPU wait/copy vs CPU side를 분리. 빠른 GPU만으로 해결된다고 단정 금지. |

### 현재 생산 코드에서 직접 재확인한 안전 경계
- `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp`는 **실제 R26+HUD** 경로에서 `R30ClassifyScreenSpacePass`(VS)와 `R30ConfigureXyzrhwWorldEffect`(고정함수)를 따로 처리한다. 옛 2026-10-08 오전 리뷰의 'exact HUD보다 World veto가 먼저' 가설은 현재 1770–1813행에서 **semanticHud 우선 및 PerspectiveHud 반환으로 바뀐 상태**. 오래된 소스 위치/번호를 지금의 결함으로 재등록하면 안 됨.
- `src/hooks_framerate.cpp`의 `Entry`는 masked `SPRARGS2::child_B4` 체인을 최대 8개 내부 복사하며 반복/순환/초과면 replay를 거부. 그러나 texture COM 포인터·게임 원본 전체 graph lifetime까지 실기 검증했다는 뜻은 아님.
- `src/overlay/hooks_overlay.cpp`의 F11 외부 소유권, `src/hooks_uiscaling.cpp`의 exact callsite 및 현재 `R57ProjectViewPoint`의 behind-camera W 거부는 이전 지적이 **현 소스에서 보정된** 사례다. 회귀검사로 보호해야지 동일 코드를 재포팅하지 않는다.
- 현재 `docs/VR_REGRESSION_KNOWLEDGE.json`은 총 10 case, 일부 2026-10-08 일어난 00519 개별 시각 증상 분류는 통합 P0 문서에 더 구체적으로 기록됨. 기존 Issue #13 사건 ID를 재사용, 새 실패 시에만 새 fingerprint 추가.

### 외부 API 교차 검증
- Microsoft D3D9: `D3DFVF_XYZ`(untransformed)와 `D3DFVF_XYZRHW`(pre-transformed)는 서로 다른 FVF이며 동시에 지정 불가: https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dfvf . 따라서 ImGui fixed XYZ와 게임 XYZRHW는 다른 stereo 경로가 필요.
- Microsoft D3D9 `Reset` 시 렌더타깃·깊이버퍼·stateblock·D3DPOOL_DEFAULT 리소스 해제 및 장치 상태 복원 필요: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-reset . DX9Ex ResetEx 호환 구현/메모리 정책은 별도 확인 대상.
- Microsoft D3D9 StateBlock은 캡처한 상태만 Apply로 복원하며, 캡처 안 한 상태까지 자동 복원하지 않는다: https://learn.microsoft.com/en-us/windows/win32/direct3d9/state-blocks-save-and-restore-state . scene/lens/ImGui/Reset 상태 추적에서 범위 누락 주의.

### 주 증거
- 현재 hooks: https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/src/hooks_uiscaling.cpp / https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/src/hooks_graphics.cpp / https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/src/hooks_framerate.cpp
- active stereo: https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp / https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/src/overlay/hooks_overlay.cpp
- 이미 수행한 독립 cross-domain screen: https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/automation/reviews/AI2_QUEST3_CROSS_DOMAIN_SOURCE_REVIEW_20261008.md / https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/automation/reviews/AI2_QUEST3_SECOND_30MIN_RENDER_LIFETIME_REVIEW_20261008.md


## Checkpoint 4 — 수정 순서·검증 행렬·최종 인계 (PENDING)

## 변경·출처
- 중간 체크포인트를 동일 파일의 개별 GitHub 커밋으로 업데이트하고 각 파일 URL 또는 SHA를 명시합니다.
- 빌드/실기 수행 없음. 소스 변경 없음.