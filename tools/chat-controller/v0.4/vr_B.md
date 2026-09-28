OutRun 2006 VR B 작업을 진행해줘. 역할은 독립 검토 + 결함 수정 + 회귀검사다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 vr-d3d9ex-focus 브랜치 최신 HEAD 하나뿐이다. N100의 로컬 clone/worktree/작업파일을 작업 기준이나 수정 대상으로 사용하지 마. GitHub를 직접 읽고 수정할 수 있는 현재 사용 가능한 GitHub 연결/도구를 사용해.

시작 즉시 AGENTS.md, docs/VR_AUTODEV_PROTOCOL.md, docs/VR_AUTODEV_STATE.json, docs/VR_RUN_STATE.md, docs/VR_WORK_QUEUE.json, docs/VR_PROBLEM_HISTORY.md 및 관련 최신 검증 문서를 읽어. A의 최신 Git 결과와 현재 미완료 VR 이슈를 검토하고 크래시, 렌더링/HUD, DX9Ex/DXVK/OpenXR 경로, 상태 오염, 회귀 위험을 확인해.

문제를 발견하면 가능한 범위에서 즉시 수정하고 검증 결과와 진행상태를 Git에 기록해. 실제 변경이 있으면 commit/push 후 SHA를 확인해. 이미 완료된 작업은 반복하지 마.

GitHub 읽기/쓰기 권한이 없으면 N100 로컬 저장소로 우회하지 말고 실패 원인을 정확히 보고해. 한글화 파일과 korean-localization-clean 브랜치는 건드리지 마.