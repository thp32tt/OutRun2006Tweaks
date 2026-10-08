OutRun 2006 DX9Ex VR 개선 자동 작업을 진행해줘.

TARGET_BRANCH는 vr-d3d9ex-focus다. 이 lane은 기존 DX9Ex/OpenXR VR 경로의 품질·성능·안정성 개선 전용이다. vr-dx11-native-r71, vr-dxvk-r71-disasm, korean-localization-clean은 직접 수정하지 마. 시작 즉시 현재 branch HEAD, AGENTS.md, VR 자동화/상태/문제 기록, 최근 검증 결과를 읽고 가장 우선순위가 높은 실행 가능한 DX9Ex 개선 작업 하나를 선택해 끝까지 처리해.

0순위는 현재 진행 중인 DX9Ex 구조 개선/리팩터링 작업이다. 매 작업 시작 시 docs/VR_REFACTOR_STATE.json과 최신 refactor(vr)/test(vr) 커밋을 먼저 읽고, 아직 이어지는 구조 개선 chain이 있으면 다른 성능·HUD·OpenXR 개선보다 반드시 먼저 그 chain의 다음 미완료 단위를 처리해. 이미 끝난 0~1000 구조 사이클을 반복하지 말고 최신 exact HEAD 이후부터 이어가. 현재 기준 활성 흐름은 R34 physical hook 제거/소유권 정리와 R33 final dispatcher 통합의 후속 구조 개선이며, 이후 HEAD에서 더 진행되어 있으면 그 최신 successor를 이어서 처리해. 구조 개선이 현재 Git 상태에서 명시적으로 완료되었거나 실행 가능한 다음 source/static 단위가 없을 때만 아래 일반 개선 우선순위로 내려가.

일반 개선 우선순위는 실제 사용자 체감과 회귀 위험을 기준으로 잡아. frame pacing/끊김, 렌더링 동기화, OpenXR pose/recenter/swapchain, stereo/HUD/메뉴 중복, lens flare/shadow/marker 등 시각 오류, resource lifetime/reset/device-loss, 불필요한 copy/wait/lock과 hot path를 우선 검토해.

한 작업은 작게 유지하고 소스 수정·정적 검증·자동 테스트·작업 기록을 같은 branch에 반영해. N100 로컬 clone/worktree/작업파일과 Google Drive는 보조 입력, 분석, 빌드, 검증, 전송 수단으로 필요할 때 사용할 수 있다. 최종 결과와 완료 판정은 vr-d3d9ex-focus의 실제 material commit으로 남겨.

실제 HMD/게임 화면 확인이 필요한 항목은 RUNTIME_VALIDATION=UNTESTED 또는 BLOCKED_RUNTIME으로 남기고 자동 검증 통과와 실기 정상 동작을 혼동하지 마. 구현 가능한 정적/소스 작업이 남아 있으면 런타임 테스트 불가만으로 종료하지 마.

반드시 docs/automation/QUEUE_CONTROLLER_CONTRACT.md를 적용하고 해당 TASK_ID의 자동화 결과 기록을 갱신해. 실제 변경 또는 검토 기록을 남긴 뒤 커밋 메시지에 컨트롤러가 지정한 [AUTO:TASK_ID] 표식을 정확히 포함해.

[장시간 채팅 진행·중복 방지]
일반 ChatGPT 채팅에서 개발을 지속한다. 작업 시작과 실제 단계 전환/도구 결과가 나올 때 TASK_ID, C0~C6 단계, 마지막 확인된 GitHub SHA/CI, 다음 행동을 간단히 중간 보고하고, 그 보고만으로 작업을 끝내지 마. 인터페이스에서 가능하면 20~30초 이상 무표시를 피하되 시간 간격을 보장하거나 백그라운드 실행을 주장하지 마. 롤오버·retry·새 채팅은 기존 TASK_ID의 미완료 단계만 이어받는다. 실제 현재 GitHub 결과가 확인되면 이미 수행한 소스 수정/검증을 재실행하지 말고 근거를 재사용한다. 작업 소유권 또는 기존 채팅의 진행 여부가 불명확하면 새 TASK_ID를 독자 생성하거나 같은 변경을 병렬로 수행하지 않는다.
