OutRun 2006 DX9Ex VR 화면·안정화 자동개발 — C 슬롯 (DX11 A와 병행).

TARGET_BRANCH=vr-d3d9ex-focus. **개발 작업자 2개 A(DX11 Native 실구현)+C(DX9Ex 안정화)를 기존처럼 동시에 돌리고 B(DXVK)는 FROZEN**한다. DX11/DXVK/Localization 소스는 수정하지 말고 C의 GitHub HEAD, AGENTS.md, docs/VR_AUTODEV_STATE.json, docs/VR_WORK_QUEUE.json, docs/VR_PROBLEM_HISTORY.md, 원본 포크의 기존 HUD 관련 소스/자료, HUD Inspector, Issue #13/#14와 현재 회귀 기록을 먼저 확인해 기존 실패 가설을 재발명하지 마.

[2026-10-10 확정 개발 우선순위 — 기존 안정화 목록보다 우선]
기준 버전은 dx9ex-baseline-20261010 브랜치의 fcd18ddd89f6dd40a8246fcf8591f086811149f1로 동결되어 있다. 해당 기준 브랜치를 수정하거나 재설정하지 않는다. 개발은 vr-d3d9ex-focus 최신 HEAD에서 수행하고 docs/DX9EX_AUTODEV_PRIORITY_20261010.md를 반드시 읽어 적용한다.
0순위: FFB의 최신 검증된 정식 릴리스 태그/SHA를 확인하고 DX9Ex에 실제 이식 및 회귀 검증한다. 릴리스 확인 없이 HEAD를 최신 릴리스라고 단정하지 않는다.
1순위: DX9Ex 구조 최적화/리팩터링의 남은 작업을 완료하고 HUD, hook, device-loss, OpenXR 및 domain isolation 회귀를 보호한다.
2순위: Virtual Desktop High 화질 설정의 OpenXR 런타임 권장 눈별 렌더 타깃 해상도를 자동으로 따르도록 한다. 고정 픽셀이나 데스크톱 해상도로 대체하지 않는다.
3순위: Quest 3 + Virtual Desktop High + RTX 4070 12GB에서 **네이티브 120FPS/120Hz**를 목표로 프레임 최적화한다. 프레임 예산은 8.33ms이며 SSW/재투영 생성 프레임을 네이티브 FPS로 계산하지 않는다. 게임 렌더 FPS와 VD 전송/디코드/표시 FPS 및 지연·드롭을 분리 측정한다. 건물 밀집, 모래사장, 모래 튐을 우선 분석한다. 실제 HMD 검증 전에는 목표 달성으로 보고하지 않는다.
위 우선순위는 순차 진행하되 각 단계가 런타임 테스트 대기일 경우 다른 독립적인 구현 가능 작업을 계속 수행한다. 기존 화면/HUD 결함은 회귀 방지 및 관련 단계 작업으로 유지한다.

[현재 구현 목표 — 안정화 활성 진행]
DX9Ex는 긴급 크래시 유지보수 전용이 아니다. Quest 3/VDXR 실제 사용에서 남아 있는 화면·입력·복구 결함을 계속 고치는 **활성 안정화 lane**이다. 기존 화면 결함 목록은 다음과 같다(상위 0~3순위 정책을 대체하지 않음): 흰색 HUD/메뉴 글자와 < > 화살표의 복시/헤드락, HUD +TIME·체크포인트·골인 후 기록/결과·4~5등 순위 숫자 중복, 라이벌/순위 마커가 상대 차량 위에 고정되지 않는 문제, F11 메뉴 gameplay 복시, lens flare·시작 그림자 이중 출력, 차량 선택 흰색 텍스처/material, recenter·OpenXR pose·프레임 페이싱·Reset/ResetEx/device-loss·host reconnect 회귀. 정상화된 도로/차량/배경 스테레오 및 SkyGlow baseline 의미는 보호한다.

실제 원본 producer→semantic registry/replay→Draw owner→per-eye 경로와 역어셈블 증거를 연결하여 반증 가능한 원인부터 안전한 최소 패치를 source/tool/test에 적용한다. blanket SpriteNode=HUD, global alpha, 근거 없는 레이어 이동·IPD 수치 튜닝은 하지 않는다. 의미 없는 1000/5000회 동일 HUD 정적 검사는 중단하고, 소스 변경 관련 정적 검사 1회, 기존 HUD Inspector CI, 필요할 경우 결함 주입 자기테스트만 수행해. 검토·계획·상태 커밋만으로 구현 완료 선언하지 않는다.

Quest 3 실기 확인이 필요한 결함은 해당 런타임 검증 또는 보호 기준 승격만 NEED_HMD_TEST/BLOCKED_RUNTIME으로 보류한다. 그 문제 때문에 전체 자동개발을 멈추지 말고, 다른 **독립 실행 가능한 DX9Ex 안정화 소스 수정**으로 넘어가 구현→검증→GitHub 커밋까지 계속해. 빌드/CI PASS를 화면 정상 동작으로 표현하지 않고 RUNTIME_VALIDATION=UNTESTED를 유지한다.

GitHub의 연결된 작업자 claim/lease와 동시 AI work_key 충돌을 확인하고 다른 작업의 소스·상태·TASK_ID를 중복 쓰지 않는다. GitHub 대상 브랜치의 C0→C6 전체 파이프라인, [AUTO:TASK_ID] 실제 구현 커밋, exact-SHA Actions 및 docs/automation/runs/ 기록을 충족한다. 성공한 동일 작업을 retry/rollover 시 재실행하지 않는다. 이번 변경은 **동시 작업 수 유지 + 각 작업의 개발 방향 변경**이며 DX9Ex를 중단하거나 DXVK를 재활성화하는 것이 아니다.


[VR 체크포인트 정책]
작업 중 5분 간격으로 실제로 완성된 소스·테스트 및 docs/automation/runs/ 진행 기록을 대상 브랜치 GitHub에 저장한다. 컨트롤러는 30분마다 같은 TASK_ID로 새 대화에서 재개한다. 새 대화는 chat-controller-downloads 브랜치 tools/chat-controller/checkpoints/vr/<TASK_ID>/ 최신 체크포인트와 게임 브랜치 현재 HEAD·run 기록을 먼저 대조하여 완료한 소스 수정과 검증을 반복하지 마. 최종 [AUTO:TASK_ID] 표식은 실제 material commit에만 넣고, 단순 체크포인트는 구현·실기 검증 성공으로 처리하지 마.
