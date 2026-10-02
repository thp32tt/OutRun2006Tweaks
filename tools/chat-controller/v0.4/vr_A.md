OutRun 2006 VR A 작업을 진행해줘. 역할은 실제 VR 개발/수정이다.

최종 상태와 결과의 SSOT는 GitHub 저장소 thp32tt/OutRun2006Tweaks의 vr-d3d9ex-focus 브랜치 최신 HEAD다. N100 로컬 clone/worktree/작업파일과 Google Drive는 보조 입력, 분석, 빌드, 검증, 전송 수단으로 필요할 때 사용해도 된다. 최종 소스 변경과 진행 결과는 대상 Git 브랜치에 commit/push해.

시작 즉시 AGENTS.md, docs/VR_AUTODEV_PROTOCOL.md, docs/VR_AUTODEV_STATE.json, docs/VR_RUN_STATE.md, docs/VR_WORK_QUEUE.json, docs/VR_PROBLEM_HISTORY.md 및 현재 Git 상태를 읽고 최신 규칙을 적용해. 현재 Git 문서가 이 프롬프트보다 우선한다.

아직 완료되지 않은 VR 작업부터 이어서 진행하고 이미 완료된 작업은 반복하지 마. 실제 변경이 있으면 필요한 정적/자동 검증을 수행하고 진행상태 문서를 갱신한 뒤 같은 VR 작업 흐름에 commit/push하고 SHA를 확인해.

GitHub 읽기/쓰기가 일시적으로 불가하면 N100 로컬 작업공간이나 Google Drive를 보조 작업에 사용할 수 있지만, 대상 Git 브랜치의 실제 commit/push가 성공하기 전에는 완료로 처리하지 마. 한글화 파일, korean-localization-clean 브랜치, localization 진행상태는 수정하지 마.