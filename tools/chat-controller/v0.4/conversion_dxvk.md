OutRun 2006 DXVK 전환 자동 작업을 진행해줘.

TARGET_BRANCH는 vr-dxvk-r71-disasm이다. 기존 검증된 VR 기준은 참조만 하고 vr-d3d9ex-focus를 직접 수정하지 마. 시작 즉시 현재 branch HEAD, docs/reviews/VR_BACKEND_100_REVIEW_INDEX.md, AGENTS.md, VR 자동화/상태 문서를 읽고 가장 우선순위가 높은 실행 가능한 DXVK 전환 작업 하나만 선택해 끝까지 처리해.

[DXVK 독립 구현 우선 / HMD 대기 비차단] DX11이나 DX9Ex의 HMD 테스트를 기다리지 않고 실제 DXVK 렌더링·30FPS 병목 개선 작업을 진행해. 백엔드 정체성·장치 생성·리소스 수명·draw/transport/fence/프레임 페이싱 중 GitHub 소스만으로 안전하게 구현·검증 가능한 독립 코드를 우선 수정해. 새로운 64바이트 디스어셈블 캡처·상태 문서만 끝없이 증가시키지 말고 구현에 직접 필요한 근거인 경우에만 분석하고 다음 코드 변경으로 이어가. HMD 실기 성능·시각 검증 및 DX9Ex 기준 승격은 NEED_HMD_TEST로 보류한다. 같은 HUD 소스의 1000/5000회 반복 정적 검사는 금지하고 실제 변경 관련 검사 1회와 GitHub CI를 사용한다. 한 작업은 작게 유지하고, 소스 수정·정적 검증·자동 테스트·작업 기록을 같은 branch에 반영해. 실제 HMD/게임 화면 확인이 필요한 항목은 RUNTIME_VALIDATION=UNTESTED 또는 BLOCKED_RUNTIME으로 남기고 자동 검증 통과와 실기 정상 동작을 혼동하지 마.

반드시 docs/automation/QUEUE_CONTROLLER_CONTRACT.md를 적용하고 해당 TASK_ID의 자동화 결과 기록을 갱신해. 실제 변경 또는 검토 기록을 남긴 뒤 커밋 메시지에 컨트롤러가 지정한 [AUTO:TASK_ID] 표식을 정확히 포함해.

[장시간 채팅 진행·중복 방지]
일반 ChatGPT 채팅에서 개발을 지속한다. 작업 시작과 실제 단계 전환/도구 결과가 나올 때 TASK_ID, C0~C6 단계, 마지막 확인된 GitHub SHA/CI, 다음 행동을 간단히 중간 보고하고, 그 보고만으로 작업을 끝내지 마. 인터페이스에서 가능하면 20~30초 이상 무표시를 피하되 시간 간격을 보장하거나 백그라운드 실행을 주장하지 마. 롤오버·retry·새 채팅은 기존 TASK_ID의 미완료 단계만 이어받는다. 실제 현재 GitHub 결과가 확인되면 이미 수행한 소스 수정/검증을 재실행하지 말고 근거를 재사용한다. 작업 소유권 또는 기존 채팅의 진행 여부가 불명확하면 새 TASK_ID를 독자 생성하거나 같은 변경을 병렬로 수행하지 않는다.
