OutRun 2006 한글화 A 작업을 진행해줘. 역할은 병렬 생산 LANE A + self-QA다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 브랜치 최신 HEAD 하나뿐이다. N100 로컬 clone/worktree/작업파일, GPT Library, 과거 대화 진행률을 작업 기준이나 수정 대상으로 사용하지 마.

시작 즉시 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 그 문서가 지정한 최신 기준 파일을 읽어 현재 상태를 재구성해. 현재 Git HEAD 규칙이 이 프롬프트보다 우선한다.

A는 localization/graphics/asset_queue.csv의 홀수 index primary shard만 생산한다. 같은 wave에서 B가 병렬 실행 중이므로 짝수 shard를 작업하거나 work-steal하지 마. 미완료/REWORK 대상을 실제 제작·수정하고, 모든 touched element에 1픽셀 containment 및 DDS/alpha/orientation/self-QA를 수행해.

병렬 안전 규칙: A는 자신의 DDS/증거/role_A report와 docs/automation/runs/<TASK_ID> 같은 lane-local 결과만 commit한다. localization/resume_state.json, localization/WORKLOG.md, localization/progress/progress.json, 호환 미러 localization/progress.json, localization/progress/STATUS.md, asset_queue.csv 등 공용 상태 파일은 수정하지 마. 공용 상태 병합은 C synchronization barrier가 담당한다.

commit 직전 최신 korean-localization-clean HEAD를 다시 읽고 B의 새 커밋을 보존한 상태에서 자신의 disjoint 파일만 반영해. 실제 변경 또는 no-action/blocker 기록을 Git에 남기고 commit 메시지에 컨트롤러가 지정한 [AUTO:TASK_ID]를 정확히 포함해. VR/FFB/DX9Ex/DX11/DXVK 및 빌드는 하지 마.