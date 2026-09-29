OutRun 2006 한글화 A 작업을 진행해줘. 역할은 연속 생산 LANE A + self-QA다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 브랜치 최신 HEAD 하나뿐이다. N100 로컬 clone/worktree/작업파일, GPT Library, 과거 대화 진행률을 작업 기준이나 수정 대상으로 사용하지 마.

시작 즉시 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 그 문서가 지정한 최신 기준 파일을 읽어 현재 상태를 재구성해. 현재 Git HEAD 규칙이 이 프롬프트보다 우선한다.

A는 localization/graphics/asset_queue.csv의 홀수 index primary shard만 생산한다. B와 C 완료를 기다리지 말고 자신의 이전 task가 durable Git commit이 되면 개별 Actions Gate를 기다리지 않고 다음 독립 작업을 계속 생산한다. 짝수 shard를 작업하거나 work-steal하지 마.

이미 A/B 생산 결과로 커밋되어 C QA 대기 중인 candidate/task는 다시 만들거나 재검수하지 마. C가 REWORK_REQUIRED로 돌려보냈거나 candidate/source/QA-contract fingerprint가 실제로 바뀐 경우에만 다시 선택해.

미완료/REWORK 대상을 한 invocation에서 가능한 한 묶어 실제 제작·수정하고 self-QA도 후보별로 한 번의 통합 패스로 수행해. 동일 source SHA + candidate SHA + QA contract fingerprint에 대해 DDS header/alpha/orientation/containment/영문원본 비교 같은 무거운 검사를 반복하지 말고 기존 machine-readable PASS 증거를 재사용해. touched element에는 1픽셀 containment 규칙을 엄격히 적용해.

병렬 안전 규칙: A는 자신의 DDS/증거/role_A report와 docs/automation/runs/<TASK_ID> 같은 lane-local 결과만 commit한다. localization/resume_state.json, localization/WORKLOG.md, localization/progress/progress.json, 호환 미러 localization/progress.json, localization/progress/STATUS.md, asset_queue.csv 등 공용 상태 파일은 수정하지 마. 공용 상태는 독립 C QA consumer가 배치 단위로 병합한다.

producer task record에는 automation_validation=PENDING, validation_mode=C_BATCH_GATE를 기록해. 최종 자동 검증은 C batch Gate가 담당한다. commit 직전 최신 korean-localization-clean HEAD를 다시 읽고 다른 lane의 새 커밋을 보존한 상태에서 자신의 disjoint 파일만 반영해. 실제 변경 또는 blocker를 해결하는 material deliverable을 Git에 남기고 commit 메시지에 컨트롤러가 지정한 [AUTO:TASK_ID]를 정확히 포함해. VR/FFB/DX9Ex/DX11/DXVK 및 빌드는 하지 마.