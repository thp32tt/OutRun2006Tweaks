OutRun 2006 VR C 작업을 진행해줘. 역할은 최종 통합 QA + 필요한 수정 + 상태 정리다.

최종 상태와 결과의 SSOT는 GitHub 저장소 thp32tt/OutRun2006Tweaks의 vr-d3d9ex-focus 브랜치 최신 HEAD다. N100 로컬 clone/worktree/작업파일과 Google Drive는 보조 입력, 분석, 빌드, 검증, 전송 수단으로 필요할 때 사용해도 된다. 최종 소스 변경과 진행 결과는 대상 Git 브랜치에 commit/push해.

시작 즉시 AGENTS.md, docs/VR_AUTODEV_PROTOCOL.md, docs/VR_AUTODEV_STATE.json, docs/VR_RUN_STATE.md, docs/VR_WORK_QUEUE.json, docs/VR_PROBLEM_HISTORY.md 및 현재 검증/회귀 규칙을 읽어. A/B 최신 Git 결과와 기존 미완료 항목을 최종 점검하고 회귀, 잘못된 통합, 빌드/런타임 계약 위반, 기록 누락을 확인해.

필요한 수정이 있으면 반영하고 작업상태 문서를 최신화해 다음 작업이 Git만 보고 이어질 수 있게 해. 실제 변경이 있으면 commit/push 후 SHA를 확인해. 이미 검증 완료된 작업은 반복하지 마.

GitHub 읽기/쓰기가 일시적으로 불가하면 N100 로컬 작업공간이나 Google Drive를 보조 작업에 사용할 수 있지만, 대상 Git 브랜치의 실제 commit/push가 성공하기 전에는 완료로 처리하지 마. 한글화 파일과 korean-localization-clean 브랜치는 건드리지 마.