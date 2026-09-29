OutRun 2006 한글화 E 작업을 진행해줘. 역할은 탄력적 세 번째 연속 생산 LANE E + self-QA다.

상태·진행·QA의 SSOT는 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 최신 HEAD다. N100 로컬 clone/worktree/작업파일, GPT Library, 과거 대화 진행률은 작업 기준이나 수정 대상으로 사용하지 마. 단, 현재 Git HEAD가 승인한 Google Drive canonical HD source transport는 원본 DDS 취득에 사용해야 하며 GitHub-only라는 이유로 차단하지 마.

시작 즉시 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 localization/controller_roles.json 및 그 문서들이 지정한 최신 기준 파일을 읽어 현재 상태를 재구성해. 현재 Git HEAD 규칙이 이 프롬프트보다 우선한다.

E는 asset_queue.csv의 안정적인 3-way shard에서 index % 3 == 2인 행만 생산한다. A/B shard를 작업하거나 work-steal하지 마. 이미 producer 결과로 C QA 대기 중인 candidate/task, 또는 dependency fingerprint가 바뀌지 않은 SOURCE_ACQUISITION_EXHAUSTED 자산은 다시 선택하지 마.

생산 전략은 candidate-completion-first다. 직접 수정 가능한 C REWORK_REQUIRED -> explicit RENDER_NEXT -> RENDER_READY -> ONE_STAGE_TO_RENDER -> 기존 candidate material rework 순으로 처리하고, ready 자산이 없을 때만 PREFLIGHT_ONLY를 최대 1개 확장해. 마지막 deterministic prerequisite가 해결되면 같은 invocation에서 Korean render -> measure/refit -> exact DDS encode -> decoded-final self-QA -> ENGLISH SOURCE 비교 -> candidate persistence까지 끝내.

E는 lane-local DDS/증거/role_E report와 docs/automation/runs/<TASK_ID>만 commit한다. 공용 progress/resume/worklog/status/asset_queue는 수정하지 말고 C가 병합하게 둬. producer task record는 automation_validation=PENDING, validation_mode=C_BATCH_GATE로 기록한다. commit 직전 최신 HEAD를 다시 읽고 다른 lane 변경을 보존해. 실제 변경 또는 material blocker-resolution만 commit하고 [AUTO:TASK_ID]를 정확히 포함해. 실기 테스트가 없으면 RUNTIME_VALIDATION=UNTESTED를 유지해. VR/FFB/DX9Ex/DX11/DXVK 및 빌드는 하지 마.
