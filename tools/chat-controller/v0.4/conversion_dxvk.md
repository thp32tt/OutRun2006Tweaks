OutRun 2006 DXVK 전환 자동 작업을 진행해줘.

GitHub는 연결 플러그인이 보이면 우선 사용하고, 보이지 않으면 CONTROLLER_GITHUB_BROKER로 같은 TASK_ID를 계속해. GitHub 도구 부재를 이유로 중단/BLOCKED 처리하지 마.

TARGET_BRANCH는 vr-dxvk-r71-disasm이다. 기존 검증된 VR 기준은 참조만 하고 vr-d3d9ex-focus를 직접 수정하지 마. 시작 즉시 현재 branch HEAD, docs/reviews/VR_BACKEND_100_REVIEW_INDEX.md, AGENTS.md, VR 자동화/상태 문서를 읽고 가장 우선순위가 높은 실행 가능한 DXVK 전환 작업 하나만 선택해 끝까지 처리해.

한 작업은 작게 유지하고, 소스 수정·정적 검증·자동 테스트·작업 기록을 같은 branch에 반영해. 실제 HMD/게임 화면 확인이 필요한 항목은 RUNTIME_VALIDATION=UNTESTED 또는 BLOCKED_RUNTIME으로 남기고 자동 검증 통과와 실기 정상 동작을 혼동하지 마.

반드시 docs/automation/QUEUE_CONTROLLER_CONTRACT.md를 적용하고 해당 TASK_ID의 자동화 결과 기록을 갱신해. 실제 변경 또는 검토 기록을 남긴 뒤 커밋 메시지에 컨트롤러가 지정한 [AUTO:TASK_ID] 표식을 정확히 포함해.