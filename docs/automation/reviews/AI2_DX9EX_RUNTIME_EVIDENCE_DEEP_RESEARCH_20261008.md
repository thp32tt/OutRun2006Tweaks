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


## Checkpoint 3 — 런타임 경로와 결함별 원인·반증 (PENDING)

## Checkpoint 4 — 수정 순서·검증 행렬·최종 인계 (PENDING)

## 변경·출처
- 중간 체크포인트를 동일 파일의 개별 GitHub 커밋으로 업데이트하고 각 파일 URL 또는 SHA를 명시합니다.
- 빌드/실기 수행 없음. 소스 변경 없음.