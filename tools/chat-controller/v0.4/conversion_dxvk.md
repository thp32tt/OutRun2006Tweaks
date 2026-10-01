OutRun 2006 DXVK 전환 자동 작업.
TARGET_BRANCH=vr-dxvk-r71-disasm. vr-d3d9ex-focus 수정 금지.
첫 행동은 BROKER_READ로 AGENTS.md, docs/reviews/VR_BACKEND_100_REVIEW_INDEX.md, docs/automation/QUEUE_CONTROLLER_CONTRACT.md와 현재 TASK 상태를 필요한 범위만 읽기.
가장 우선순위 높은 실행 가능한 1건을 끝까지 처리하고 BROKER_CHANGESET으로 소스+기록을 반영해. 실기 미검증은 RUNTIME_VALIDATION=UNTESTED.
