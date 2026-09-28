OutRun 2006 한글화 C 작업을 진행해줘. 역할은 A+B 병렬 wave의 synchronization barrier + cross-lane final QA + 공용 상태 병합이다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 최신 HEAD 하나뿐이다. N100 로컬 clone/worktree/작업파일, GPT Library, 과거 대화 진행률을 사용하지 마.

시작 즉시 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 최신 기준 파일을 읽고, 현재 WAVE_ID에 해당하는 A/B의 docs/automation/runs 및 role_A/role_B 결과를 최신 HEAD에서 확인해. A/B 둘 다 durable terminal result(PASS/no-action/recorded blocker)가 있어야 한다.

A/B 결과를 원본과 cross-lane 최종 대조하고 의미/문맥/용어, 누락, 한글 깨짐, 글자 잘림, 원본 영역 1픽셀 초과, 해상도, DDS format/mipmap/alpha/투명도, 배경/오교체/고해상도 GUI를 검증해. 필요한 작은 수정은 C가 직접 처리할 수 있고 큰 실패는 REWORK_REQUIRED로 반환해.

C만 이 wave의 공용 상태를 병합한다. 최신 HEAD를 다시 읽은 뒤 localization/resume_state.json, localization/WORKLOG.md, canonical localization/progress/progress.json, localization/progress/STATUS.md, asset_queue.csv 및 필요한 공용 QA 상태를 A/B 결과와 충돌 없이 갱신해. canonical progress를 변경했다면 legacy 호환 경로 localization/progress.json도 canonical 파일과 byte-for-byte 동일한 내용으로 함께 갱신해. 실제 결과를 docs/automation/runs/<TASK_ID>에 기록하고 commit 메시지에 [AUTO:TASK_ID]를 정확히 포함해. 실기 테스트가 없으면 RUNTIME_VALIDATION=UNTESTED를 유지해. VR/FFB 및 빌드는 하지 마.