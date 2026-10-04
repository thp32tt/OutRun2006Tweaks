OutRun 2006 DX9Ex VR 개선 자동 작업을 진행해줘.

TARGET_BRANCH는 vr-d3d9ex-focus다. 이 lane은 기존 DX9Ex/OpenXR VR 경로의 품질·성능·안정성 개선 전용이다. vr-dx11-native-r71, vr-dxvk-r71-disasm, korean-localization-clean은 직접 수정하지 마. 시작 즉시 현재 branch HEAD, AGENTS.md, VR 자동화/상태/문제 기록, 최근 검증 결과를 읽고 가장 우선순위가 높은 실행 가능한 DX9Ex 개선 작업 하나를 선택해 끝까지 처리해.

우선순위는 실제 사용자 체감과 회귀 위험을 기준으로 잡아. frame pacing/끊김, 렌더링 동기화, OpenXR pose/recenter/swapchain, stereo/HUD/메뉴 중복, lens flare/shadow/marker 등 시각 오류, resource lifetime/reset/device-loss, 불필요한 copy/wait/lock과 hot path를 우선 검토해.

한 작업은 작게 유지하고 소스 수정·정적 검증·자동 테스트·작업 기록을 같은 branch에 반영해. N100 로컬 clone/worktree/작업파일과 Google Drive는 보조 입력, 분석, 빌드, 검증, 전송 수단으로 필요할 때 사용할 수 있다. 최종 결과와 완료 판정은 vr-d3d9ex-focus의 실제 material commit으로 남겨.

실제 HMD/게임 화면 확인이 필요한 항목은 RUNTIME_VALIDATION=UNTESTED 또는 BLOCKED_RUNTIME으로 남기고 자동 검증 통과와 실기 정상 동작을 혼동하지 마. 구현 가능한 정적/소스 작업이 남아 있으면 런타임 테스트 불가만으로 종료하지 마.

반드시 docs/automation/QUEUE_CONTROLLER_CONTRACT.md를 적용하고 해당 TASK_ID의 자동화 결과 기록을 갱신해. 실제 변경 또는 검토 기록을 남긴 뒤 커밋 메시지에 컨트롤러가 지정한 [AUTO:TASK_ID] 표식을 정확히 포함해.
